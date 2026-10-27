import pandas as pd

MEDS = [
    'metformin', 'repaglinide', 'nateglinide', 'chlorpropamide', 'glimepiride',
    'acetohexamide', 'glipizide', 'glyburide', 'tolbutamide', 'pioglitazone',
    'rosiglitazone', 'acarbose', 'miglitol', 'troglitazone', 'tolazamide', 'insulin',
    'glyburide-metformin', 'glipizide-metformin', 'glimepiride-pioglitazone',
    'metformin-rosiglitazone', 'metformin-pioglitazone'
]
DROP = ['encounter_id', 'patient_nbr', 'time_in_hospital', 'weight', 'examide', 'citoglipton']
CAT_ID = ['admission_type_id', 'discharge_disposition_id', 'admission_source_id']


def build_features(d, cats=None):
    d = d.copy()
    for c in MEDS:
        if c not in d.columns:
            d[c] = 'No'
    d[MEDS] = d[MEDS].fillna('No')

    if 'age' in d.columns and d['age'].dtype == object:
        d['age'] = d['age'].astype(str).str.extract(r'\[(\d+)-')[0].astype(float) + 5

    for c in ['diag_1', 'diag_2', 'diag_3']:
        if c not in d.columns:
            d[c] = None
        s = d[c].copy()
        s = s.map(lambda v: None if pd.isna(v) else str(v))
        s = s.map(lambda v: None if v is None else v.split('.')[0])
        d[c] = s

    for c in CAT_ID:
        if c not in d.columns:
            d[c] = '0'
        d[c] = d[c].map(lambda v: '0' if pd.isna(v) else str(v))

    d['n_meds_changed'] = d[MEDS].isin(['Up', 'Down']).sum(axis=1)
    d['n_meds_used'] = (d[MEDS] != 'No').sum(axis=1)
    d['n_visits'] = d['number_outpatient'] + d['number_emergency'] + d['number_inpatient']
    d = d.drop(columns=[c for c in DROP if c in d.columns])

    if cats is not None:
        for c, levels in cats.items():
            if c not in d.columns:
                d[c] = None
            d[c] = d[c].map(lambda v: None if pd.isna(v) else str(v))
            d[c] = pd.Categorical(d[c], categories=levels)
    return d
