"""
Logique du module réadmission : chargement du modèle XGBoost, préparation de la saisie d'un patient, prédiction.

Le prétraitement refait, pour UN patient, les mêmes étapes que le notebook :
  valeurs typiques pour ce qui n'est pas saisi -> limitation des valeurs extrêmes -> encodage des catégories
  -> XGBoost (une probabilité par classe : <30, >30, NO)
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ART = Path(__file__).parent / "artifacts"
_state = {"ready": False, "error": None, "warning": None}

# bornes de saisie acceptées pour les champs numériques (par défaut : de 0 à 100)
LIMITES = {
    "time_in_hospital": (1, 14),
    "num_lab_procedures": (0, 150),
    "num_procedures": (0, 10),
    "num_medications": (0, 100),
    "number_diagnoses": (1, 16),
}
LIMITE_DEFAUT = (0, 100)


def _load():
    try:
        import joblib
        import sklearn
        import xgboost
        cfg = json.loads((ART / "config.json").read_text(encoding="utf-8"))
        bundle = joblib.load(ART / "model.joblib")
        _state.update(cfg=cfg, model=bundle["model"], ready=True)

        ecarts = []
        for nom, installee in (("sklearn", sklearn.__version__), ("xgboost", xgboost.__version__)):
            entrainee = cfg.get("versions", {}).get(nom)
            if entrainee and entrainee != installee:
                ecarts.append(f"{nom} {entrainee} (installé : {installee})")
        if ecarts:
            _state["warning"] = ("Le modèle a été entraîné avec " + ", ".join(ecarts)
                                 + " : alignez les versions dans requirements.txt.")
    except FileNotFoundError:
        _state["error"] = ("Modèle non trouvé : exécutez la cellule d'export du notebook et copiez le dossier "
                           "'artifacts' dans modules/readmission/.")
    except Exception as exc:
        _state["error"] = f"Erreur au chargement du modèle : {exc!r}"


_load()


def is_ready():
    return _state["ready"]


def form_context(error=None, values=None):
    """Données envoyées au template du formulaire."""
    ctx = {"ready": is_ready(), "error": error or _state["error"], "warning": _state["warning"],
           "values": values or {}}
    if is_ready():
        champs = []
        for f in _state["cfg"]["form_fields"]:
            champ = dict(f)
            if f["type"] == "nombre":
                lo, hi = LIMITES.get(f["name"], LIMITE_DEFAUT)
                champ.update(lo=lo, hi=hi, default=int(round(f["default"])))
            else:
                champ["default"] = str(f["default"])
            champs.append(champ)
        ctx["fields"] = champs
    return ctx


# ---------------------------------------------------------------- formulaire -> dictionnaire "saisie"
def form_to_saisie(form):
    """Valide la saisie du formulaire et la convertit en dictionnaire {colonne: valeur}."""
    saisie = {}
    for f in _state["cfg"]["form_fields"]:
        nom = f["name"]
        if f["type"] == "nombre":
            lo, hi = LIMITES.get(nom, LIMITE_DEFAUT)
            txt = (form.get(nom) or "").strip()
            try:
                val = int(txt)
            except ValueError:
                raise ValueError(f"« {f['label']} » doit être un nombre entier.")
            if not lo <= val <= hi:
                raise ValueError(f"« {f['label']} » doit être compris entre {lo} et {hi}.")
            saisie[nom] = val
        else:
            val = form.get(nom, str(f["default"]))
            if val not in [c["value"] for c in f["choices"]]:
                raise ValueError(f"Valeur invalide pour « {f['label']} ».")
            saisie[nom] = val
    return saisie


# ---------------------------------------------------------------- saisie -> ligne du modèle
def saisie_to_row(saisie):
    """Reproduit le prétraitement du notebook pour un patient. Retourne un DataFrame d'une ligne."""
    cfg = _state["cfg"]

    # 1) valeurs typiques pour tout ce qui n'est pas saisi
    ligne = dict(cfg["defaults"])
    ligne.update(saisie)

    # 2) compteurs : on limite aux bornes (évite les valeurs extrêmes)
    for col in cfg["num_cols"]:
        bas, haut = cfg["caps"][col]
        ligne[col] = min(max(float(ligne[col]), bas), haut)

    # 3) catégories : texte -> code (la position de la modalité dans la liste = son code)
    for col in cfg["cat_cols"]:
        modalites = cfg["categories"][col]
        valeur = str(ligne[col])
        if valeur not in modalites:
            valeur = str(cfg["defaults"][col])
        ligne[col] = modalites.index(valeur)

    # 4) DataFrame dans l'ordre exact des colonnes du modèle
    return pd.DataFrame([[ligne[c] for c in cfg["columns"]]], columns=cfg["columns"])


# ---------------------------------------------------------------- prédiction
def predict(form):
    cfg = _state["cfg"]
    saisie = form_to_saisie(form)
    proba = _state["model"].predict_proba(saisie_to_row(saisie))[0]

    idx = int(np.argmax(proba))                      # classe la plus probable
    alerte = cfg["alert"]
    p30 = float(proba[alerte["class_index"]])        # probabilité d'être réadmis en moins de 30 jours

    return {
        "info": cfg["classes"][str(idx)],
        "probas": [{"name": cfg["classes"][str(i)]["name"], "label": cfg["classes"][str(i)]["label"],
                    "pct": round(float(p) * 100, 1), "best": i == idx} for i, p in enumerate(proba)],
        "p30_pct": round(p30 * 100, 1),
        "alerte": p30 >= alerte["threshold"],
        "seuil_pct": round(alerte["threshold"] * 100, 1),
        "stats": alerte,
        "metrics": cfg["metrics"],
    }
