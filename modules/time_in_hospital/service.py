"""Service TIME_IN_HOSPITAL : charge les artefacts du modèle et prédit la durée de séjour."""
from __future__ import annotations

import json
import re
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from .preprocessing import build_features

ART = Path(__file__).resolve().parent / "artifacts"
MODEL_PATH = ART / "model.joblib"
CONFIG_PATH = ART / "config.json"

_cache = {}

NUMERIC_FIELDS = [
    {"name": "age", "label": "Âge", "min": 0, "max": 100},
    {"name": "num_lab_procedures", "label": "Nombre d'examens de laboratoire", "min": 0, "max": 200},
    {"name": "num_procedures", "label": "Nombre de procédures", "min": 0, "max": 50},
    {"name": "num_medications", "label": "Nombre de médicaments", "min": 0, "max": 200},
    {"name": "number_diagnoses", "label": "Nombre de diagnostics", "min": 0, "max": 50},
    {"name": "number_outpatient", "label": "Nombre de consultations externes", "min": 0, "max": 100},
    {"name": "number_emergency", "label": "Nombre d'urgences", "min": 0, "max": 100},
    {"name": "number_inpatient", "label": "Nombre d'hospitalisations", "min": 0, "max": 100},
]

OPTIONAL_SELECT_FIELDS = [
    "race",
    "gender",
    "admission_type_id",
    "admission_source_id",
    "discharge_disposition_id",
    "payer_code",
    "medical_specialty",
    "A1Cresult",
    "max_glu_serum",
    "readmitted",
    "change",
    "diabetesMed",
]

REQUIRED_SELECT_FIELDS = [
    "gender",
    "admission_type_id",
    "admission_source_id",
    "discharge_disposition_id",
    "A1Cresult",
    "max_glu_serum",
    "readmitted",
    "change",
    "diabetesMed",
]

MODEL_FIELDS = [
    "diag_1",
    "diag_2",
    "diag_3",
    "metformin",
    "repaglinide",
    "nateglinide",
    "chlorpropamide",
    "glimepiride",
    "acetohexamide",
    "glipizide",
    "glyburide",
    "tolbutamide",
    "pioglitazone",
    "rosiglitazone",
    "acarbose",
    "miglitol",
    "troglitazone",
    "tolazamide",
    "insulin",
    "glyburide-metformin",
    "glipizide-metformin",
    "glimepiride-pioglitazone",
    "metformin-rosiglitazone",
    "metformin-pioglitazone",
]


def is_ready():
    return MODEL_PATH.exists() and CONFIG_PATH.exists()


def _load_bundle():
    if "bundle" not in _cache:
        model = joblib.load(MODEL_PATH)
        cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        _cache["bundle"] = model
        _cache["cfg"] = cfg
    return _cache["bundle"], _cache["cfg"]


def _options_for(field, cfg):
    values = cfg.get("cats", {}).get(field, [])
    if not values:
        return []
    return [(value, value) for value in values]


def _default_form_value(field, cfg, values):
    if field in values and values[field] not in (None, ""):
        return values[field]
    if field in cfg.get("cats", {}):
        cats = cfg["cats"][field]
        return cats[0] if cats else ""
    return ""


def _clean_blank(value):
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None


def _validate_diag_code(value, field_name):
    text = _clean_blank(value)
    if text is None:
        if field_name == "diag_3":
            return None
        raise ValueError(f"« {field_name} » : code diagnostique requis.")
    text = text.replace(" ", "").upper()
    if not re.fullmatch(r"(?:[A-Z0-9]+(?:\.[0-9]+)?)|(?:[A-Z][0-9]+)", text):
        raise ValueError(f"« {field_name} » : format invalide (ex. 428, 250.83, V57).")
    if "." in text:
        text = text.split(".", 1)[0]
    return text


def _validate_numeric(value, field):
    text = _clean_blank(value)
    if text is None:
        raise ValueError(f"« {field['label']} » : valeur manquante.")
    try:
        num = float(text)
    except ValueError as exc:
        raise ValueError(f"« {field['label']} » : saisissez un nombre valide.") from exc
    if not field["min"] <= num <= field["max"]:
        raise ValueError(f"« {field['label']} » doit être compris entre {field['min']} et {field['max']}.")
    return int(num) if float(num).is_integer() else num


def _validate_choice(field, value, cfg):
    text = _clean_blank(value)
    if text is None:
        if field in REQUIRED_SELECT_FIELDS:
            raise ValueError(f"« {field} » : veuillez choisir une valeur.")
        return None
    allowed = cfg.get("cats", {}).get(field, [])
    if allowed and text not in allowed:
        raise ValueError(f"« {field} » : valeur invalide.")
    return text


def form_context(error=None, values=None):
    ctx = {"ready": is_ready(), "error": error, "numeric_fields": [], "select_fields": []}
    if not ctx["ready"]:
        return ctx
    cfg = _load_bundle()[1]
    values = values or {}
    for field in NUMERIC_FIELDS:
        raw_value = values.get(field["name"])
        default = raw_value if raw_value not in (None, "") else field["min"]
        ctx["numeric_fields"].append({**field, "value": default})
    for field_name in sorted(cfg.get("cats", {}).keys()):
        if field_name not in set(f["name"] for f in NUMERIC_FIELDS):
            options = _options_for(field_name, cfg)
            if field_name in OPTIONAL_SELECT_FIELDS and not options:
                continue
            if field_name in OPTIONAL_SELECT_FIELDS:
                opt_list = [("", "Non renseigné")] + options
            else:
                opt_list = options
            default_value = _default_form_value(field_name, cfg, values)
            ctx["select_fields"].append({
                "name": field_name,
                "label": field_name,
                "options": opt_list,
                "value": values.get(field_name, default_value),
            })
    return ctx


def _to_raw_row(form_values, cfg):
    row = {name: None for name in cfg.get("raw_columns", [])}
    for name in cfg.get("raw_columns", []):
        if name in form_values:
            row[name] = form_values.get(name)

    if "age" in form_values and form_values.get("age") not in (None, ""):
        row["age"] = form_values["age"]

    row["diag_1"] = _validate_diag_code(form_values.get("diag_1"), "diag_1")
    row["diag_2"] = _validate_diag_code(form_values.get("diag_2"), "diag_2")
    row["diag_3"] = _validate_diag_code(form_values.get("diag_3"), "diag_3")

    for field in NUMERIC_FIELDS:
        row[field["name"]] = _validate_numeric(form_values.get(field["name"]), field)

    for field_name in cfg.get("cats", {}).keys():
        if field_name in {"diag_1", "diag_2", "diag_3"}:
            continue
        if field_name in form_values:
            row[field_name] = _validate_choice(field_name, form_values.get(field_name), cfg)

    for name in ["metformin", "repaglinide", "nateglinide", "chlorpropamide", "glimepiride",
                 "acetohexamide", "glipizide", "glyburide", "tolbutamide", "pioglitazone",
                 "rosiglitazone", "acarbose", "miglitol", "troglitazone", "tolazamide",
                 "insulin", "glyburide-metformin", "glipizide-metformin",
                 "glimepiride-pioglitazone", "metformin-rosiglitazone", "metformin-pioglitazone"]:
        val = _clean_blank(form_values.get(name))
        row[name] = val if val is not None else "No"
        if val not in (None, "No", "Steady", "Up", "Down"):
            raise ValueError(f"« {name} » : valeur invalide.")

    if row["gender"] is None:
        row["gender"] = "Female"
    if row["race"] is None:
        row["race"] = "Other"
    if row["medical_specialty"] is None:
        row["medical_specialty"] = "PhysicianNotFound"
    if row["payer_code"] is None:
        row["payer_code"] = "MC"
    if row["admission_type_id"] is None:
        row["admission_type_id"] = "1"
    if row["admission_source_id"] is None:
        row["admission_source_id"] = "7"
    if row["discharge_disposition_id"] is None:
        row["discharge_disposition_id"] = "1"
    if row["max_glu_serum"] is None:
        row["max_glu_serum"] = "Norm"
    if row["A1Cresult"] is None:
        row["A1Cresult"] = "Norm"
    if row["readmitted"] is None:
        row["readmitted"] = "NO"
    if row["change"] is None:
        row["change"] = "No"
    if row["diabetesMed"] is None:
        row["diabetesMed"] = "Yes"

    return row


def predict(form_values):
    model, cfg = _load_bundle()
    row = pd.DataFrame([_to_raw_row(form_values, cfg)]).reindex(columns=cfg["raw_columns"])
    X = build_features(row, cfg["cats"])[cfg["features"]]
    proba = model.predict_proba(X)[0]
    idx = int(np.argmax(proba))
    label = cfg["labels"][idx]
    expected_days = float(np.dot(proba, cfg["class_means"]))
    return {
        "classe": label,
        "classe_index": idx,
        "probabilites": [
            {"label": cfg["labels"][i], "prob": float(proba[i]), "pourcentage": round(float(proba[i]) * 100.0, 1)}
            for i in range(len(cfg["labels"]))
        ],
        "duree_attendue_jours": round(expected_days, 2),
        "metrics": cfg["metrics"],
    }
