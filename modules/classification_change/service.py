"""
Logique du module classification_change : chargement des artefacts, préparation de la saisie, prédiction.

Le prétraitement refait, pour UN patient, les mêmes étapes que le notebook :
  âge -> milieu de tranche (age_num) -> log1p sur les 3 compteurs de visites -> valeurs typiques pour ce qui
  n'est pas saisi -> écrêtage aux bornes (percentiles 1 % et 99 %) -> préprocesseur (StandardScaler + OneHotEncoder)
  -> XGBoost (probabilité que le traitement soit modifié).
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ART = Path(__file__).parent / "artifacts"
_state = {"ready": False, "error": None, "warning": None}

LOG_COLS = ["number_outpatient", "number_emergency", "number_inpatient"]   # transformés par log1p dans le notebook

# Champs numériques du formulaire : (nom, libellé, minimum, maximum)
CHAMPS_NOMBRES = [
    ("age", "Âge (années)", 0, 120),
    ("time_in_hospital", "Durée du séjour (jours)", 1, 14),
    ("num_lab_procedures", "Nombre d'analyses de laboratoire", 0, 150),
    ("num_procedures", "Nombre de procédures", 0, 10),
    ("num_medications", "Nombre de médicaments", 0, 100),
    ("number_diagnoses", "Nombre de diagnostics", 1, 16),
    ("number_outpatient", "Consultations externes (année précédente)", 0, 100),
    ("number_emergency", "Passages aux urgences (année précédente)", 0, 100),
    ("number_inpatient", "Hospitalisations (année précédente)", 0, 100),
]
DEFAUT_AGE = 65

# Champs à choix : (nom, libellé)
CHAMPS_CHOIX = [
    ("race", "Origine"),
    ("gender", "Sexe"),
    ("admission_type", "Type d'admission"),
    ("admission_source", "Provenance à l'admission"),
    ("discharge_disposition", "Destination à la sortie"),
    ("medical_specialty", "Spécialité médicale"),
    ("diag_1", "Diagnostic principal"),
    ("diag_2", "Diagnostic secondaire"),
    ("diag_3", "Diagnostic additionnel"),
    ("max_glu_serum", "Glycémie sérique maximale"),
    ("A1Cresult", "Résultat HbA1c"),
]


def _load():
    try:
        import joblib
        import sklearn
        import xgboost
        cfg = json.loads((ART / "config.json").read_text(encoding="utf-8"))
        # modèle XGBoost au format JSON natif (portable entre Linux/Colab et Windows) + préprocesseur sklearn
        model = xgboost.XGBClassifier()
        model.load_model(str(ART / "model.json"))
        prep = joblib.load(ART / "preprocessor.joblib")
        _state.update(cfg=cfg, model=model, prep=prep, ready=True)

        actuelles = {"sklearn": sklearn.__version__, "xgboost": xgboost.__version__,
                     "pandas": pd.__version__, "numpy": np.__version__}
        differences = [f"{k} : modèle {v}, installé {actuelles.get(k)}"
                       for k, v in cfg.get("versions", {}).items() if actuelles.get(k) != v]
        if differences:
            _state["warning"] = "Versions différentes de l'entraînement (" + " ; ".join(differences) + ")."
    except FileNotFoundError:
        _state["error"] = ("Modèle non trouvé : placez model.json, preprocessor.joblib et config.json "
                           "dans modules/classification_change/artifacts/.")
    except Exception as exc:
        _state["error"] = f"Erreur au chargement du modèle : {exc!r}"


_load()


def is_ready():
    return _state["ready"]


def _defaut_nombre(nom):
    """Valeur par défaut affichée dans le formulaire (entier)."""
    cfg = _state["cfg"]
    if nom == "age":
        return DEFAUT_AGE
    val = cfg["defaults"][nom]
    if nom in LOG_COLS:
        val = np.expm1(val)           # retour à l'échelle d'origine (nombre de visites)
    return int(round(val))


def form_context(error=None, values=None):
    """Données envoyées au template du formulaire."""
    ctx = {"ready": is_ready(), "error": error or _state["error"], "warning": _state["warning"],
           "values": values or {}}
    if is_ready():
        cfg = _state["cfg"]
        ctx["nombres"] = [{"name": n, "label": lib, "lo": lo, "hi": hi, "default": _defaut_nombre(n)}
                          for n, lib, lo, hi in CHAMPS_NOMBRES]
        ctx["choix"] = [{"name": n, "label": lib, "choices": cfg["categories"][n], "default": cfg["modes"][n]}
                        for n, lib in CHAMPS_CHOIX]
    return ctx


# ---------------------------------------------------------------- formulaire -> dictionnaire "saisie"
def form_to_saisie(form):
    """Valide la saisie du formulaire et la convertit en dictionnaire {nom: valeur}."""
    cfg = _state["cfg"]
    saisie = {}
    for nom, libelle, lo, hi in CHAMPS_NOMBRES:
        txt = (form.get(nom) or "").strip()
        try:
            val = int(txt)
        except ValueError:
            raise ValueError(f"« {libelle} » doit être un nombre entier.")
        if not lo <= val <= hi:
            raise ValueError(f"« {libelle} » doit être compris entre {lo} et {hi}.")
        saisie[nom] = val
    for nom, libelle in CHAMPS_CHOIX:
        val = form.get(nom, cfg["modes"][nom])
        if val not in cfg["categories"][nom]:
            raise ValueError(f"Valeur invalide pour « {libelle} ».")
        saisie[nom] = val
    return saisie


# ---------------------------------------------------------------- saisie -> ligne du modèle
def saisie_to_row(saisie):
    """Reproduit le prétraitement du notebook pour un patient. Retourne un DataFrame d'une ligne."""
    cfg = _state["cfg"]
    ligne = dict(cfg["defaults"])
    ligne.update({k: v for k, v in saisie.items() if k != "age"})

    # âge : milieu de la tranche de 10 ans (ex. 67 ans -> 65), comme age_num du notebook
    age = int(saisie["age"])
    ligne["age_num"] = float(min(max((age // 10) * 10 + 5, 5), 95))

    # compteurs de visites : log1p comme dans le notebook
    for col in LOG_COLS:
        ligne[col] = float(np.log1p(float(ligne[col])))

    # écrêtage aux bornes de l'entraînement
    for col in cfg["num_cols"]:
        bas, haut = cfg["caps"][col]
        ligne[col] = min(max(float(ligne[col]), bas), haut)

    for col in cfg["cat_cols"]:
        ligne[col] = str(ligne.get(col, cfg["modes"][col]))

    return pd.DataFrame([[ligne[c] for c in cfg["raw_columns"]]], columns=cfg["raw_columns"])


# ---------------------------------------------------------------- prédiction
def predict(form):
    saisie = form_to_saisie(form)
    ligne = saisie_to_row(saisie)
    X = _state["prep"].transform(ligne)
    p_change = float(_state["model"].predict_proba(X)[0][1])      # classe 1 = traitement modifié
    # niveau en 3 paliers, pour un affichage simple
    if p_change >= 0.5:
        niveau = "probable"
    elif p_change >= 0.35:
        niveau = "possible"
    else:
        niveau = "peu_probable"
    return {
        "p_change_pct": round(p_change * 100, 1),
        "p_no_change_pct": round((1 - p_change) * 100, 1),
        "change": p_change >= 0.5,
        "niveau": niveau,
        "saisie": saisie,
    }
