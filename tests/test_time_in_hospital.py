import json
import math
from pathlib import Path

import pandas as pd
import pytest

from app import app
from modules.time_in_hospital import service
from modules.time_in_hospital.preprocessing import build_features


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_home_and_form_get(client):
    home = client.get('/')
    assert home.status_code == 200
    form = client.get('/time_in_hospital/')
    assert form.status_code == 200
    assert b'form' in form.data.lower() or b'profil' in form.data.lower()


def test_valid_prediction(client):
    payload = {
        'age': '60', 'gender': 'Female', 'race': 'Caucasian', 'admission_type_id': '1',
        'admission_source_id': '7', 'discharge_disposition_id': '1', 'payer_code': 'MC',
        'medical_specialty': 'InternalMedicine', 'num_lab_procedures': '50', 'num_procedures': '2',
        'num_medications': '8', 'number_outpatient': '0', 'number_emergency': '0', 'number_inpatient': '1',
        'diag_1': '428', 'diag_2': '250', 'diag_3': '403', 'number_diagnoses': '4', 'max_glu_serum': 'Norm',
        'A1Cresult': '>7', 'metformin': 'No', 'repaglinide': 'No', 'nateglinide': 'No', 'chlorpropamide': 'No',
        'glimepiride': 'No', 'acetohexamide': 'No', 'glipizide': 'No', 'glyburide': 'No', 'tolbutamide': 'No',
        'pioglitazone': 'No', 'rosiglitazone': 'No', 'acarbose': 'No', 'miglitol': 'No', 'troglitazone': 'No',
        'tolazamide': 'No', 'insulin': 'No', 'glyburide-metformin': 'No', 'glipizide-metformin': 'No',
        'glimepiride-pioglitazone': 'No', 'metformin-rosiglitazone': 'No', 'metformin-pioglitazone': 'No',
        'change': 'Ch', 'diabetesMed': 'Yes', 'readmitted': 'NO'
    }
    response = client.post('/time_in_hospital/predict', data=payload)
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert 'Durée de séjour estimée' in body
    assert 'Classe prédite' in body
    assert 'Probabilités par classe' in body
    assert 'Démonstration pédagogique' in body
    assert body.count('%') > 0


def test_invalid_prediction(client):
    payload = {
        'age': '60', 'gender': 'Female', 'race': 'Caucasian', 'admission_type_id': '1',
        'admission_source_id': '7', 'discharge_disposition_id': '1', 'payer_code': 'MC',
        'medical_specialty': 'InternalMedicine', 'num_lab_procedures': '50', 'num_procedures': '2',
        'num_medications': '999', 'number_outpatient': '0', 'number_emergency': '0', 'number_inpatient': '1',
        'diag_1': 'abc', 'diag_2': '250', 'diag_3': '403', 'number_diagnoses': '4', 'max_glu_serum': 'Norm',
        'A1Cresult': '>7', 'metformin': 'No', 'repaglinide': 'No', 'nateglinide': 'No', 'chlorpropamide': 'No',
        'glimepiride': 'No', 'acetohexamide': 'No', 'glipizide': 'No', 'glyburide': 'No', 'tolbutamide': 'No',
        'pioglitazone': 'No', 'rosiglitazone': 'No', 'acarbose': 'No', 'miglitol': 'No', 'troglitazone': 'No',
        'tolazamide': 'No', 'insulin': 'No', 'glyburide-metformin': 'No', 'glipizide-metformin': 'No',
        'glimepiride-pioglitazone': 'No', 'metformin-rosiglitazone': 'No', 'metformin-pioglitazone': 'No',
        'change': 'Ch', 'diabetesMed': 'Yes', 'readmitted': 'NO'
    }
    response = client.post('/time_in_hospital/predict', data=payload)
    assert response.status_code == 400
    assert b'Erreur' in response.data or b'invalide' in response.data.lower() or b'compris' in response.data.lower()


def test_missing_diag_3_and_optional_fields(client):
    payload = {
        'age': '60', 'gender': 'Female', 'race': 'Caucasian', 'admission_type_id': '1',
        'admission_source_id': '7', 'discharge_disposition_id': '1', 'payer_code': 'MC',
        'medical_specialty': '', 'num_lab_procedures': '50', 'num_procedures': '2',
        'num_medications': '8', 'number_outpatient': '0', 'number_emergency': '0', 'number_inpatient': '1',
        'diag_1': '428', 'diag_2': '250', 'diag_3': '', 'number_diagnoses': '4', 'max_glu_serum': 'Norm',
        'A1Cresult': '>7', 'metformin': 'No', 'repaglinide': 'No', 'nateglinide': 'No', 'chlorpropamide': 'No',
        'glimepiride': 'No', 'acetohexamide': 'No', 'glipizide': 'No', 'glyburide': 'No', 'tolbutamide': 'No',
        'pioglitazone': 'No', 'rosiglitazone': 'No', 'acarbose': 'No', 'miglitol': 'No', 'troglitazone': 'No',
        'tolazamide': 'No', 'insulin': 'No', 'glyburide-metformin': 'No', 'glipizide-metformin': 'No',
        'glimepiride-pioglitazone': 'No', 'metformin-rosiglitazone': 'No', 'metformin-pioglitazone': 'No',
        'change': 'Ch', 'diabetesMed': 'Yes', 'readmitted': 'NO'
    }
    response = client.post('/time_in_hospital/predict', data=payload)
    assert response.status_code == 200


def test_service_matches_model_on_prepared_row():
    with open(Path('modules/time_in_hospital/artifacts/config.json'), encoding='utf-8') as f:
        cfg = json.load(f)

    model = service._load_bundle()[0]
    raw = {}
    for col in cfg['raw_columns']:
        raw[col] = None
    raw.update({
        'race': 'Caucasian', 'gender': 'Female', 'age': 65, 'admission_type_id': '1', 'discharge_disposition_id': '1',
        'admission_source_id': '7', 'payer_code': 'MC', 'medical_specialty': 'InternalMedicine',
        'num_lab_procedures': 50, 'num_procedures': 2, 'num_medications': 8, 'number_outpatient': 0,
        'number_emergency': 0, 'number_inpatient': 1, 'diag_1': '428', 'diag_2': '250', 'diag_3': '403',
        'number_diagnoses': 4, 'max_glu_serum': 'Norm', 'A1Cresult': '>7', 'metformin': 'No', 'repaglinide': 'No',
        'nateglinide': 'No', 'chlorpropamide': 'No', 'glimepiride': 'No', 'acetohexamide': 'No', 'glipizide': 'No',
        'glyburide': 'No', 'tolbutamide': 'No', 'pioglitazone': 'No', 'rosiglitazone': 'No', 'acarbose': 'No',
        'miglitol': 'No', 'troglitazone': 'No', 'tolazamide': 'No', 'insulin': 'No', 'glyburide-metformin': 'No',
        'glipizide-metformin': 'No', 'glimepiride-pioglitazone': 'No', 'metformin-rosiglitazone': 'No',
        'metformin-pioglitazone': 'No', 'change': 'Ch', 'diabetesMed': 'Yes', 'readmitted': 'NO'
    })
    row = pd.DataFrame([raw]).reindex(columns=cfg['raw_columns'])
    X = build_features(row, cfg['cats'])[cfg['features']]
    model_proba = model.predict_proba(X)[0]
    service_proba = service.predict(raw)['probabilites']
    service_values = [p['prob'] for p in service_proba]
    for i in range(3):
        assert math.isclose(service_values[i], model_proba[i], rel_tol=1e-9, abs_tol=1e-9)
