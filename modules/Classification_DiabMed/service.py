"""
Logique du module Classification DiabMed : chargement du modèle, validation de la saisie, prédiction.

Le modèle (XGBoost) prédit la variable cible diabetesMed.
Classe positive (classe 1) = "No" = patient SANS traitement antidiabétique.
Décision : probabilité de la classe 1 >= seuil optimisé (enregistré dans le modèle) -> "No", sinon "Yes".
"""
import json
from pathlib import Path

import pandas as pd

from . import preprocess

ART = Path(__file__).parent / "artifacts"
_state = {"ready": False, "error": None, "warning": None}

# (nom, libellé, min, max, valeur par défaut) - les valeurs par défaut sont celles du notebook (config.json)
NUMERIC_FIELDS = [
    ("age", "Âge (années)", 0, 120, 65),
    ("time_in_hospital", "Durée du séjour (jours)", 1, 14, 3),
    ("num_lab_procedures", "Nombre d'analyses de laboratoire", 0, 150, 44),
    ("num_procedures", "Nombre de procédures (hors laboratoire)", 0, 10, 1),
    ("num_medications", "Nombre total de médicaments administrés", 0, 100, 14),
    ("number_outpatient", "Consultations externes (année précédente)", 0, 100, 0),
    ("number_emergency", "Passages aux urgences (année précédente)", 0, 100, 0),
    ("number_inpatient", "Hospitalisations (année précédente)", 0, 100, 0),
    ("number_diagnoses", "Nombre de diagnostics", 1, 16, 8),
]

NOMINAL_LABELS = {
    "race": "Origine",
    "gender": "Sexe",
    "admission_type_id": "Type d'admission",
    "discharge_disposition_id": "Destination à la sortie",
    "admission_source_id": "Provenance",
    "max_glu_serum": "Glycémie sérique maximale",
    "A1Cresult": "Résultat HbA1c",
}

# Libellés des codes (fichier IDs_mapping du jeu de données UCI). Un code absent est affiché tel quel.
CODE_LABELS = {
    "admission_type_id": {
        "1": "Urgence", "2": "Urgent", "3": "Programmée", "4": "Nouveau-né", "5": "Non disponible",
        "6": "Non renseigné", "7": "Centre de traumatologie", "8": "Non associé"},
    "discharge_disposition_id": {
        "1": "Retour à domicile", "2": "Transfert vers un autre hôpital de courte durée",
        "3": "Transfert vers un établissement de soins infirmiers", "4": "Transfert vers un établissement de soins intermédiaires",
        "5": "Transfert vers une autre institution de soins", "6": "Domicile avec soins à domicile",
        "7": "Départ contre avis médical", "8": "Domicile avec perfusions à domicile",
        "9": "Admis comme patient hospitalisé dans cet hôpital", "10": "Nouveau-né transféré",
        "12": "Toujours patient ou retour prévu", "15": "Lit d'hospitalisation de transition (Medicare)",
        "16": "Soins ambulatoires", "17": "Soins ambulatoires (même établissement)", "18": "Non renseigné",
        "22": "Centre de rééducation", "23": "Hôpital de soins de longue durée",
        "24": "Établissement de soins infirmiers (Medicaid)", "25": "Non associé",
        "27": "Établissement de santé fédéral", "28": "Hôpital psychiatrique"},
    "admission_source_id": {
        "1": "Orientation par un médecin", "2": "Orientation par une clinique", "3": "Orientation par une HMO",
        "4": "Transfert depuis un hôpital", "5": "Transfert depuis un établissement de soins infirmiers",
        "6": "Transfert depuis un autre établissement de santé", "7": "Urgences", "8": "Justice / forces de l'ordre",
        "9": "Non disponible", "10": "Transfert depuis un hôpital d'accès critique", "11": "Accouchement normal",
        "13": "Nouveau-né malade", "14": "Naissance hors établissement", "17": "Non renseigné",
        "20": "Non associé", "22": "Transfert depuis un hôpital (même établissement)",
        "25": "Transfert depuis un centre de chirurgie ambulatoire"},
}

# Libellé des deux issues possibles
LABEL_NO = "Sans traitement antidiabétique (diabetesMed = No)"
LABEL_YES = "Sous traitement antidiabétique (diabetesMed = Yes)"


def _load_model(cfg):
    """Charge le modèle : d'abord model.json (format natif XGBoost, indépendant des versions),
    sinon model.joblib (pickle). Retourne (modèle, seuil)."""
    import joblib
    import xgboost
    json_path, joblib_path = ART / "model.json", ART / "model.joblib"
    errors = []
    if json_path.exists():
        try:
            model = xgboost.XGBClassifier()
            model.load_model(str(json_path))
            return model, float(cfg["seuil"])
        except Exception as exc:
            errors.append(f"model.json : {exc!r}")
    if joblib_path.exists():
        try:
            bundle = joblib.load(joblib_path)
            return bundle["model"], float(bundle.get("threshold", cfg["seuil"]))
        except Exception as exc:
            errors.append(f"model.joblib : {exc!r}")
    if not errors:
        raise FileNotFoundError("aucun fichier de modèle")
    raise RuntimeError(" | ".join(errors))


def _load():
    try:
        import sklearn
        import xgboost
        cfg = json.loads((ART / "config.json").read_text(encoding="utf-8"))
        model, threshold = _load_model(cfg)
        _state.update(cfg=cfg, model=model, threshold=threshold, ready=True)
        saved = cfg.get("versions", {})
        problems = []
        if saved.get("sklearn") and saved["sklearn"] != sklearn.__version__:
            problems.append(f"scikit-learn {saved['sklearn']} (installé : {sklearn.__version__})")
        if saved.get("xgboost") and saved["xgboost"] != xgboost.__version__:
            problems.append(f"xgboost {saved['xgboost']} (installé : {xgboost.__version__})")
        if problems:
            _state["warning"] = ("Le modèle a été entraîné avec " + " et ".join(problems)
                                 + " : alignez les versions dans requirements.txt.")
    except FileNotFoundError:
        _state["error"] = ("Modèle non trouvé : placez config.json et model.json (ou model.joblib) dans "
                           "modules/Classification_DiabMed/artifacts/.")
    except Exception as exc:
        _state["error"] = f"Erreur au chargement du modèle : {exc!r}"


_load()


def is_ready():
    return _state["ready"]


def _options(var, categories):
    """Liste (valeur, texte affiché) pour une variable nominale."""
    names = CODE_LABELS.get(var, {})
    return [(c, f"{c} - {names[c]}" if c in names else c) for c in categories]


def form_context(error=None, values=None):
    ctx = {"ready": is_ready(), "error": error or _state["error"], "warning": _state["warning"],
           "numeric": NUMERIC_FIELDS, "values": values or {}, "nominal": []}
    if is_ready():
        cfg = _state["cfg"]
        ctx["nominal"] = [(k, NOMINAL_LABELS.get(k, k), _options(k, cfg["categories"][k]), cfg["modes"][k])
                          for k in cfg["nominal"]]
    return ctx


# ---------------------------------------------------------------- saisie -> dictionnaire "patient"
def form_to_raw(form):
    """Valide la saisie du formulaire et la convertit en un patient 'brut' pour preprocess.preparer()."""
    cfg = _state["cfg"]
    raw = {}
    for name, label, lo, hi, _ in NUMERIC_FIELDS:
        txt = (form.get(name) or "").strip()
        try:
            val = int(txt)
        except ValueError:
            raise ValueError(f"« {label} » doit être un nombre entier.")
        if not lo <= val <= hi:
            raise ValueError(f"« {label} » doit être compris entre {lo} et {hi}.")
        raw[name] = val
    # Dans les données d'entraînement, l'âge est le centre de la tranche de 10 ans (5, 15, ..., 95)
    raw["age"] = min(95, (raw["age"] // 10) * 10 + 5)
    for var in cfg["nominal"]:
        val = form.get(var, cfg["modes"][var])
        if val not in cfg["categories"][var]:
            raise ValueError(f"Valeur invalide pour « {NOMINAL_LABELS.get(var, var)} ».")
        raw[var] = val
    return raw


# ---------------------------------------------------------------- prédiction
def predict(form):
    cfg = _state["cfg"]
    raw = form_to_raw(form)
    X = preprocess.preparer(pd.DataFrame([raw]), cfg)           # même prétraitement que le notebook
    for col, (lo, hi) in cfg["bornes"].items():                 # plafonnement des valeurs extrêmes
        X[col] = X[col].clip(lo, hi)
    p_no = float(_state["model"].predict_proba(X)[0][1])        # classe 1 = "No" (sans traitement)
    seuil = _state["threshold"]
    is_no = p_no >= seuil
    return {
        "is_no": is_no,
        "label": LABEL_NO if is_no else LABEL_YES,
        "p_no": round(p_no * 100, 1),
        "p_yes": round((1 - p_no) * 100, 1),
        "seuil": round(seuil * 100, 1),
        "modele": cfg.get("modele", "XGBoost"),
        "metrics": cfg.get("metriques_test", {}),
    }
