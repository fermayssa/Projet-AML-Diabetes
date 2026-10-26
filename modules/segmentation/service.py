"""
Logique du module segmentation : chargement du modèle, prétraitement d'un patient, prédiction.

Le prétraitement refait, pour UN patient, exactement les mêmes étapes que le notebook :
  variables dérivées -> log(1+x) -> one-hot -> plafonnement -> normalisation -> sélection -> ACP -> K-Means
"""
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

ART = Path(__file__).parent / "artifacts"
_state = {"ready": False, "error": None, "warning": None}

# (nom, libellé, min, max, valeur par défaut)
NUMERIC_FIELDS = [
    ("age", "Âge (années)", 0, 120, 65),
    ("time_in_hospital", "Durée du séjour (jours)", 1, 14, 4),
    ("num_lab_procedures", "Nombre d'analyses de laboratoire", 0, 150, 40),
    ("num_procedures", "Nombre de procédures (hors laboratoire)", 0, 10, 1),
    ("num_medications", "Nombre total de médicaments administrés", 0, 100, 15),
    ("number_diagnoses", "Nombre de diagnostics", 1, 16, 7),
    ("number_outpatient", "Consultations externes (année précédente)", 0, 100, 0),
    ("number_emergency", "Passages aux urgences (année précédente)", 0, 100, 0),
    ("number_inpatient", "Hospitalisations (année précédente)", 0, 100, 0),
    ("n_other_meds", "Autres antidiabétiques prescrits (nombre)", 0, 20, 0),
    ("n_med_changes", "Médicaments dont la dose a changé (nombre)", 0, 21, 0),
]
NOMINAL_LABELS = {
    "race": "Origine", "admission_type": "Type d'admission", "discharge_group": "Destination à la sortie",
    "admission_source": "Provenance", "medical_specialty": "Spécialité médicale",
    "diag_1_group": "Diagnostic principal (famille)", "A1Cresult": "Résultat HbA1c",
    "max_glu_serum": "Glycémie sérique maximale",
}
COMORBIDITIES = [("any_circulatory", "Maladie circulatoire"), ("any_diabetes_dx", "Diagnostic de diabète"),
                 ("any_respiratory", "Maladie respiratoire"), ("any_genitourinary", "Maladie génito-urinaire")]
LOG_COLS = ["number_outpatient", "number_emergency", "number_inpatient", "total_prior_visits"]
N_MEDS_SHOWN = 6


def _load():
    try:
        import joblib
        import sklearn
        cfg = json.loads((ART / "config.json").read_text(encoding="utf-8"))
        bundle = joblib.load(ART / "model.joblib")
        _state.update(cfg=cfg, km=bundle["km"], pca=bundle["pca"], scaler=bundle["scaler"], ready=True)
        saved = cfg.get("versions", {}).get("sklearn")
        if saved and saved != sklearn.__version__:
            _state["warning"] = (f"Le modèle a été entraîné avec scikit-learn {saved} mais {sklearn.__version__} "
                                 "est installé : alignez la version dans requirements.txt.")
    except FileNotFoundError:
        _state["error"] = ("Modèle non trouvé : exécutez la cellule d'export du notebook et copiez le dossier "
                           "'artifacts' dans modules/segmentation/.")
    except Exception as exc:
        _state["error"] = f"Erreur au chargement du modèle : {exc!r}"


_load()


def is_ready():
    return _state["ready"]


def _clean(name):
    return re.sub(r"[^0-9a-zA-Z_]+", "_", name)


def form_context(error=None, values=None):
    ctx = {"ready": is_ready(), "error": error or _state["error"], "warning": _state["warning"],
           "numeric": NUMERIC_FIELDS, "comorb": COMORBIDITIES, "values": values or {}}
    if is_ready():
        cfg = _state["cfg"]
        ctx["nominal"] = [(k, NOMINAL_LABELS.get(k, k), cfg["categories"][k], cfg["modes"][k])
                          for k in cfg["categories"]]
        ctx["meds"] = [m for m in cfg["med_order"] if m != "insulin"][:N_MEDS_SHOWN]
    return ctx


# ---------------------------------------------------------------- saisie -> dictionnaire "patient"
def form_to_raw(form):
    """Valide la saisie du formulaire et la convertit en dictionnaire 'patient'."""
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
    raw["gender"] = form.get("gender", "Female")
    raw["change"] = 1 if form.get("change") == "1" else 0
    raw["diabetesMed"] = 1 if form.get("diabetesMed") == "1" else 0
    raw["insulin_state"] = form.get("insulin_state", "No")
    if raw["insulin_state"] not in ("No", "Steady", "Up", "Down"):
        raise ValueError("Valeur invalide pour l'insuline.")
    shown = [m for m in cfg["med_order"] if m != "insulin"][:N_MEDS_SHOWN]
    raw["meds"] = {m: 1 if form.get(f"med_{m}") else 0 for m in shown}
    for key, _ in COMORBIDITIES:
        raw[key] = 1 if form.get(key) else 0
    raw["nominal"] = {}
    for var, cats in cfg["categories"].items():
        val = form.get(var, cfg["modes"][var])
        if val not in cats:
            raise ValueError(f"Valeur invalide pour {NOMINAL_LABELS.get(var, var)}.")
        raw["nominal"][var] = val
    return raw


# ---------------------------------------------------------------- patient -> vecteur du modèle
def raw_to_row(raw):
    """Reproduit le prétraitement du notebook pour un patient. Retourne un DataFrame d'une ligne."""
    cfg = _state["cfg"]
    cols = cfg["columns"]
    row = {c: cfg["defaults"][c] for c in cols}         # valeurs typiques pour ce qui n'est pas saisi

    def put(name, value):
        if name in row:
            row[name] = float(value)

    # --- variables de base
    put("age", min(95, (int(raw["age"]) // 10) * 10 + 5))      # centre de la tranche d'âge
    put("gender_male", 1 if raw["gender"] == "Male" else 0)
    put("change", raw["change"])
    put("diabetesMed", raw["diabetesMed"])
    for c in ("time_in_hospital", "num_lab_procedures", "num_procedures", "num_medications", "number_diagnoses"):
        put(c, raw[c])

    # --- médicaments
    insulin_on = 0 if raw["insulin_state"] == "No" else 1
    insulin_changed = 1 if raw["insulin_state"] in ("Up", "Down") else 0
    for med in cfg["med_cols"]:
        if med == "insulin":
            put("insulin", insulin_on)
        elif med in raw["meds"]:
            put(_clean(med), raw["meds"][med])      # ex. 'glipizide-metformin' -> colonne 'glipizide_metformin'
    n_meds = insulin_on + sum(raw["meds"].values()) + raw["n_other_meds"]
    put("n_meds_prescribed", n_meds)
    put("n_med_changes", max(raw["n_med_changes"], insulin_changed))
    put("insulin_changed", insulin_changed)

    # --- visites antérieures (calculées sur les comptes bruts, puis log(1+x))
    total = raw["number_outpatient"] + raw["number_emergency"] + raw["number_inpatient"]
    put("has_prior_inpatient", 1 if raw["number_inpatient"] > 0 else 0)
    put("number_outpatient", raw["number_outpatient"])
    put("number_emergency", raw["number_emergency"])
    put("number_inpatient", raw["number_inpatient"])
    put("total_prior_visits", total)
    for c in LOG_COLS:
        if c in row:
            row[c] = float(np.log1p(row[c]))

    # --- intensité de prise en charge
    days = raw["time_in_hospital"]
    put("labs_per_day", raw["num_lab_procedures"] / days)
    put("meds_per_day", raw["num_medications"] / days)
    put("procs_per_day", raw["num_procedures"] / days)

    # --- comorbidités, HbA1c
    for key, _ in COMORBIDITIES:
        put(key, raw[key])
    a1c = raw["nominal"].get("A1Cresult", "None")
    put("hba1c_high_no_change", 1 if (a1c in (">7", ">8") and raw["change"] == 0) else 0)
    put("a1c_tested", 1 if a1c != "None" else 0)

    # --- variables nominales : one-hot (la modalité de référence = toutes les colonnes à 0)
    for var, val in raw["nominal"].items():
        prefix = _clean(var) + "_"
        for c in cols:
            if c.startswith(prefix):
                row[c] = 0.0
        target = _clean(f"{var}_{val}")
        if target in row:
            row[target] = 1.0

    return pd.DataFrame([row], columns=cols)


def row_to_cluster(df_row):
    """Plafonnement -> normalisation -> sélection -> ACP -> K-Means."""
    cfg = _state["cfg"]
    x = df_row.copy()
    for c, (lo, hi) in cfg["caps"].items():
        x[c] = x[c].clip(lo, hi)
    x[cfg["num_cols"]] = _state["scaler"].transform(x[cfg["num_cols"]])
    z = _state["pca"].transform(x[cfg["features_cl"]])
    km = _state["km"]
    cluster = int(km.predict(z)[0])
    dist = km.transform(z)[0]
    return cluster, dist


def predict(form):
    raw = form_to_raw(form)
    cluster, dist = row_to_cluster(raw_to_row(raw))
    info = _state["cfg"]["clusters"][str(cluster)]
    return {"cluster": cluster, "info": info,
            "distances": [(i, round(float(d), 2)) for i, d in enumerate(dist)],
            "clusters": _state["cfg"]["clusters"]}


def clusters():
    """Description des groupes (nom, action, taux de réadmission…) ; {} si le modèle n'est pas chargé."""
    return _state["cfg"]["clusters"] if is_ready() else {}


def dashboard_data():
    """Nuage de points ACP et centres, pour le graphique ; {} si le modèle n'est pas chargé."""
    return _state["cfg"].get("dashboard", {}) if is_ready() else {}


_stats_cache = {}


def dashboard_stats():
    """Lit config.json seul (sans charger le modèle) : le dashboard marche même si scikit-learn diffère."""
    if "v" not in _stats_cache:
        try:
            _stats_cache["v"] = json.loads((ART / "config.json").read_text(encoding="utf-8"))
        except Exception:
            _stats_cache["v"] = None
    cfg = _stats_cache["v"]
    if not cfg:
        return None
    return {"clusters": cfg["clusters"], "dashboard": cfg.get("dashboard", {})}