"""
Routes pour le module Decision Support - Aide à la décision clinique
"""
from flask import render_template, redirect, url_for, request, session
from . import bp
import joblib
import json
import pandas as pd
import numpy as np
import os
from pathlib import Path
import xgboost as xgb
import db_config

# Chemin vers les artifacts du modèle
ARTIFACTS_PATH = Path(os.path.join(os.path.dirname(__file__), '..', 'Classification_DiabMed', 'artifacts'))
MODEL_PATH = ARTIFACTS_PATH / 'model.json'
CONFIG_PATH = ARTIFACTS_PATH / 'config.json'

# État du chargement du modèle
_diabmed_state = {"ready": False, "error": None, "warning": None, "cfg": None, "model": None, "threshold": None}

def load_diabmed_model():
    """Charge le modèle Classification_DiabMed depuis le fichier JSON"""
    global _diabmed_state
    try:
        cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        model = xgb.Booster()
        model.load_model(str(MODEL_PATH))
        _diabmed_state.update(cfg=cfg, model=model,
                             threshold=float(cfg["seuil"]), ready=True)
    except FileNotFoundError:
        _diabmed_state["error"] = f"Modèle non trouvé : {ARTIFACTS_PATH}"
    except Exception as exc:
        _diabmed_state["error"] = f"Erreur au chargement du modèle : {exc!r}"

load_diabmed_model()

# Fonctions utilitaires pour le formulaire (inspirées de service.py)
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

CODE_LABELS = {
    "race": {
        "AfricanAmerican": "Africain Américain",
        "Asian": "Asiatique",
        "Caucasian": "Caucasien",
        "Hispanic": "Hispanique",
        "Inconnu": "Inconnu",
        "Other": "Autre"
    },
    "gender": {
        "Female": "Femme",
        "Male": "Homme"
    },
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
    "max_glu_serum": {
        ">200": ">200 mg/dL",
        ">300": ">300 mg/dL",
        "Non mesure": "Non mesuré",
        "Norm": "Normal"
    },
    "A1Cresult": {
        ">7": ">7%",
        ">8": ">8%",
        "Non mesure": "Non mesuré",
        "Norm": "Normal"
    },
}

def _options(var, categories):
    """Liste (valeur, texte affiché) pour une variable nominale."""
    names = CODE_LABELS.get(var, {})
    return [(c, f"{c} - {names[c]}" if c in names else c) for c in categories]

def get_form_context(error=None, values=None):
    """Retourne le contexte pour le formulaire"""
    ctx = {"ready": _diabmed_state["ready"], "error": error or _diabmed_state["error"],
           "warning": _diabmed_state["warning"], "numeric": NUMERIC_FIELDS, "values": values or {}, "nominal": []}
    if _diabmed_state["ready"]:
        cfg = _diabmed_state["cfg"]
        ctx["nominal"] = [(k, NOMINAL_LABELS.get(k, k), _options(k, cfg["categories"][k]), cfg["modes"][k])
                          for k in cfg["nominal"]]
    return ctx

def form_to_raw(form):
    """Valide la saisie du formulaire et la convertit en un patient 'brut'"""
    cfg = _diabmed_state["cfg"]
    raw = {}
    for name, label, lo, hi, _ in NUMERIC_FIELDS:
        txt = (form.get(name) or "").strip()
        try:
            val = int(float(txt)) if txt else lo
        except (ValueError, TypeError):
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

def preparer(df_in, cfg):
    """Prépare les données pour le modèle (inspiré de preprocess.py)"""
    df = pd.DataFrame(df_in).copy()
    for c in cfg['num_cols']:
        if c not in df.columns:
            df[c] = cfg['defaults'][c]
        df[c] = pd.to_numeric(df[c], errors='coerce').fillna(cfg['defaults'][c])
    for c in cfg['nominal']:
        if c not in df.columns:
            df[c] = cfg['modes'][c]
        df[c] = df[c].astype(str)
        df.loc[~df[c].isin(cfg['categories'][c]), c] = cfg['modes'][c]
    X = pd.get_dummies(df[cfg['num_cols'] + cfg['nominal']])
    X = X.reindex(columns=cfg['columns'], fill_value=0)
    dummies = [c for c in X.columns if c not in cfg['num_cols']]
    X[dummies] = X[dummies].astype(cfg['dummies_dtype'])
    return X

def predict_from_form(form):
    """Prédit à partir du formulaire"""
    cfg = _diabmed_state["cfg"]
    raw = form_to_raw(form)
    print(f"DEBUG - Raw data: {raw}")
    X = preparer(pd.DataFrame([raw]), cfg)
    print(f"DEBUG - Prepared features shape: {X.shape}")
    print(f"DEBUG - Prepared features columns: {X.columns.tolist()}")
    for col, (lo, hi) in cfg["bornes"].items():
        X[col] = X[col].clip(lo, hi)
    # XGBoost Booster utilise predict() qui retourne les probabilités
    dmatrix = xgb.DMatrix(X)
    p_no = float(_diabmed_state["model"].predict(dmatrix)[0])
    seuil = _diabmed_state["threshold"]
    print(f"DEBUG - p_no (probabilité sans traitement): {p_no}")
    print(f"DEBUG - seuil: {seuil}")
    print(f"DEBUG - is_no (p_no >= seuil): {p_no >= seuil}")
    is_no = p_no >= seuil
    return {
        "is_no": is_no,
        "label": "Sans traitement antidiabétique" if is_no else "Sous traitement antidiabétique",
        "p_no": round(p_no * 100, 1),
        "p_yes": round((1 - p_no) * 100, 1),
        "seuil": round(seuil * 100, 1),
        "modele": cfg.get("modele", "XGBoost"),
        "metrics": cfg.get("metriques_test", {}),
    }

@bp.route('/')
def dashboard():
    """Tableau de bord global - Fiche patient unifiée"""
    patient_id = request.args.get('patient_id', 1, type=int)
    
    try:
        conn = db_config.get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM patients WHERE id = %s", (patient_id,))
                patient = cursor.fetchone()
                cursor.execute("SELECT * FROM clusters")
                clusters = cursor.fetchall()
                cursor.execute("SELECT * FROM patients")
                patients = cursor.fetchall()
        finally:
            conn.close()
    except Exception as e:
        print(f"Erreur de connexion DB: {e}")
        # Fallback: données de démonstration
        patient = {
            'id': 1, 'nom': 'Martin', 'prenom': 'Jean', 'age': 68, 'sexe': 'M',
            'readmitted_risk': 0.5, 'change_risk': 0.45, 'cluster_id': 1,
            'diabetes_med': 'No', 'time_in_hospital': 3
        }
        patients = [patient]
        clusters = [{
            'id': 1, 'nom': 'Patients âgés avec comorbidités',
            'description': 'Patients de plus de 65 ans avec multiples comorbidités',
            'taille': 234, 'age_moyen': 72.0, 'duree_sejour_moyenne': 8.5,
            'readmission_rate': 0.35, 'change_rate': 0.42,
            'conditions_frequentes': '["Hypertension", "Maladies cardiovasculaires"]'
        }]
    
    if not patient:
        patient = patients[0] if patients else {
            'id': 1, 'nom': 'Martin', 'prenom': 'Jean', 'age': 68, 'sexe': 'M',
            'readmitted_risk': 0.5, 'change_risk': 0.45, 'cluster_id': 1,
            'diabetes_med': 'No', 'time_in_hospital': 3
        }
    
    cluster = next((c for c in clusters if c['id'] == patient.get('cluster_id')), {})
    
    # Si cluster est vide, utiliser le premier cluster ou un cluster par défaut
    if not cluster and clusters:
        cluster = clusters[0]
    if not cluster:
        cluster = {
            'id': 1, 'nom': 'Cluster par défaut',
            'description': 'Aucune donnée de cluster disponible',
            'taille': 0, 'age_moyen': 0, 'duree_sejour_moyenne': 0,
            'readmission_rate': 0, 'change_rate': 0,
            'conditions_frequentes': '[]'
        }
    
    # Ajouter les attributs manquants pour le patient
    if patient:
        patient['readmitted_risk'] = patient.get('readmitted_risk', 0.5)
        patient['change_risk'] = patient.get('change_risk', 0.45)
        patient['diabetes_med'] = patient.get('diabetes_med', 'No')
        patient['time_in_hospital'] = patient.get('time_in_hospital', 3)
    
    # Ensure values are not None
    if patient.get('readmitted_risk') is None:
        patient['readmitted_risk'] = 0.5
    if patient.get('change_risk') is None:
        patient['change_risk'] = 0.45
    if patient.get('time_in_hospital') is None:
        patient['time_in_hospital'] = 3
    
    # Ajouter caracteristiques pour le cluster
    if cluster:
        cluster['caracteristiques'] = {
            'âge_moyen': cluster.get('age_moyen', 0),
            'duree_sejour_moyenne': cluster.get('duree_sejour_moyenne', 0),
            'readmission_rate': cluster.get('readmission_rate', 0),
            'change_rate': cluster.get('change_rate', 0)
        }
        if cluster.get('conditions_frequentes'):
            import json
            try:
                cluster['conditions_frequentes'] = json.loads(cluster['conditions_frequentes'])
            except (json.JSONDecodeError, TypeError):
                cluster['conditions_frequentes'] = []
        else:
            cluster['conditions_frequentes'] = []
    
    return render_template('dashboard.html',
                         patient=patient,
                         cluster=cluster,
                         patients=patients,
                         clusters=clusters)

@bp.route('/clustering')
def clustering():
    """Profilage des patients - Clustering non supervisé"""
    try:
        conn = db_config.get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM clusters")
                clusters = cursor.fetchall()
                cursor.execute("SELECT * FROM patients")
                patients = cursor.fetchall()
        finally:
            conn.close()
    except Exception as e:
        print(f"Erreur de connexion DB: {e}")
        # Fallback: données de démonstration
        clusters = [{
            'id': 1, 'nom': 'Patients âgés avec comorbidités',
            'description': 'Patients de plus de 65 ans avec multiples comorbidités',
            'taille': 234, 'age_moyen': 72.0, 'duree_sejour_moyenne': 8.5,
            'readmission_rate': 0.35, 'change_rate': 0.42,
            'conditions_frequentes': '["Hypertension", "Maladies cardiovasculaires"]'
        }]
        patients = []
    
    # Ajouter les attributs manquants pour les templates
    for cluster in clusters:
        cluster['caracteristiques'] = {
            'âge_moyen': cluster.get('age_moyen', 0),
            'duree_sejour_moyenne': cluster.get('duree_sejour_moyenne', 0),
            'readmission_rate': cluster.get('readmission_rate', 0),
            'change_rate': cluster.get('change_rate', 0)
        }
        if cluster.get('conditions_frequentes'):
            import json
            try:
                cluster['conditions_frequentes'] = json.loads(cluster['conditions_frequentes'])
            except (json.JSONDecodeError, TypeError):
                cluster['conditions_frequentes'] = []
        else:
            cluster['conditions_frequentes'] = []
    
    return render_template('clustering.html',
                         clusters=clusters,
                         patients=patients,
                         data_quality_score=87)

@bp.route('/clusters/add', methods=['POST'])
def add_cluster():
    """Ajouter un nouveau cluster"""
    conn = db_config.get_db_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
                INSERT INTO clusters (nom, description, taille, age_moyen, duree_sejour_moyenne, readmission_rate, change_rate, conditions_frequentes)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (
                request.form.get('nom'),
                request.form.get('description'),
                request.form.get('taille', 0),
                request.form.get('age_moyen', 0),
                request.form.get('duree_sejour_moyenne', 0),
                request.form.get('readmission_rate', 0),
                request.form.get('change_rate', 0),
                request.form.get('conditions_frequentes', '[]')
            ))
        conn.commit()
    except Exception as e:
        conn.rollback()
        return str(e), 400
    finally:
        conn.close()
    
    return redirect(url_for('decision_support.clustering'))

@bp.route('/clusters/<int:cluster_id>/edit', methods=['GET', 'POST'])
def edit_cluster(cluster_id):
    """Modifier un cluster"""
    conn = db_config.get_db_connection()
    try:
        if request.method == 'POST':
            with conn.cursor() as cursor:
                sql = """
                    UPDATE clusters SET
                        nom = %s, description = %s, taille = %s,
                        age_moyen = %s, duree_sejour_moyenne = %s,
                        readmission_rate = %s, change_rate = %s,
                        conditions_frequentes = %s
                    WHERE id = %s
                """
                cursor.execute(sql, (
                    request.form.get('nom'),
                    request.form.get('description'),
                    request.form.get('taille'),
                    request.form.get('age_moyen'),
                    request.form.get('duree_sejour_moyenne'),
                    request.form.get('readmission_rate'),
                    request.form.get('change_rate'),
                    request.form.get('conditions_frequentes'),
                    cluster_id
                ))
            conn.commit()
            return redirect(url_for('decision_support.clustering'))
        else:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM clusters WHERE id = %s", (cluster_id,))
                cluster = cursor.fetchone()
    finally:
        conn.close()
    
    if not cluster:
        return redirect(url_for('decision_support.clustering'))
    
    return render_template('edit_cluster.html', cluster=cluster)

@bp.route('/clusters/<int:cluster_id>/delete', methods=['POST'])
def delete_cluster(cluster_id):
    """Supprimer un cluster"""
    conn = db_config.get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM clusters WHERE id = %s", (cluster_id,))
        conn.commit()
    except Exception as e:
        conn.rollback()
        return str(e), 400
    finally:
        conn.close()
    
    return redirect(url_for('decision_support.clustering'))

@bp.route('/readmission')
def readmission():
    """Prédiction du risque de réadmission"""
    patient_id = request.args.get('patient_id', 1, type=int)
    
    try:
        conn = db_config.get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM patients WHERE id = %s", (patient_id,))
                patient = cursor.fetchone()
                cursor.execute("SELECT * FROM patients")
                patients = cursor.fetchall()
        finally:
            conn.close()
    except Exception as e:
        print(f"Erreur de connexion DB: {e}")
        # Fallback: données de démonstration
        patient = {
            'id': 1, 'nom': 'Martin', 'prenom': 'Jean', 'age': 68, 'sexe': 'M',
            'readmitted_risk': 0.5, 'change_risk': 0.45, 'time_in_hospital': 3,
            'admission_type': 'Urgence', 'number_emergency': 0, 'number_inpatient': 0, 'number_diagnoses': 5
        }
        patients = [patient]
    
    if not patient:
        patient = patients[0] if patients else {
            'id': 1, 'nom': 'Martin', 'prenom': 'Jean', 'age': 68, 'sexe': 'M',
            'readmitted_risk': 0.5, 'change_risk': 0.45, 'time_in_hospital': 3,
            'admission_type': 'Urgence', 'number_emergency': 0, 'number_inpatient': 0, 'number_diagnoses': 5
        }
    
    # Ensure values are not None
    if patient.get('readmitted_risk') is None:
        patient['readmitted_risk'] = 0.5
    if patient.get('change_risk') is None:
        patient['change_risk'] = 0.45
    if patient.get('time_in_hospital') is None:
        patient['time_in_hospital'] = 3
    
    # Calculer le risque de réadmission basé sur les données du patient
    age = patient.get('age') or 0
    time_in_hospital = patient.get('time_in_hospital') or 0
    admission_type = patient.get('admission_type') or ''
    
    # Calcul simple du risque
    risk_score = 0
    if age > 65:
        risk_score += 0.3
    if time_in_hospital > 7:
        risk_score += 0.3
    if 'Urgence' in admission_type:
        risk_score += 0.2
    if (patient.get('number_emergency') or 0) > 0:
        risk_score += 0.1
    if (patient.get('number_inpatient') or 0) > 0:
        risk_score += 0.1
    
    patient['readmitted_risk'] = min(risk_score, 1.0)
    
    # Ajouter change_risk aussi
    patient['change_risk'] = patient['readmitted_risk'] * 0.9
    
    # Facteurs explicatifs
    factors = [
        {"name": "Âge", "value": f"{age} ans", "importance": 0.25},
        {"name": "Durée de séjour", "value": f"{time_in_hospital} jours", "importance": 0.22},
        {"name": "Type d'admission", "value": admission_type, "importance": 0.18},
        {"name": "Cluster de risque", "value": "Haut risque" if patient.get('readmitted_risk', 0) > 0.5 else "Risque modéré", "importance": 0.20},
        {"name": "Comorbidités", "value": "Multiples" if (patient.get('number_diagnoses') or 0) > 5 else "Peu", "importance": 0.15}
    ]
    
    return render_template('readmission.html',
                         patient=patient,
                         patients=patients,
                         factors=factors)

@bp.route('/instabilite')
def instabilite():
    """Détection de l'instabilité thérapeutique"""
    patient_id = request.args.get('patient_id', 1, type=int)
    
    try:
        conn = db_config.get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM patients WHERE id = %s", (patient_id,))
                patient = cursor.fetchone()
                cursor.execute("SELECT * FROM patients")
                patients = cursor.fetchall()
        finally:
            conn.close()
    except Exception as e:
        print(f"Erreur de connexion DB: {e}")
        # Fallback: données de démonstration
        patient = {
            'id': 1, 'nom': 'Martin', 'prenom': 'Jean', 'age': 68, 'sexe': 'M',
            'readmitted_risk': 0.5, 'change_risk': 0.45
        }
        patients = [patient]
    
    # Si patient est None, utiliser le premier patient ou un dict vide
    if not patient:
        patient = patients[0] if patients else {'readmitted_risk': 0.5, 'change_risk': 0.45}
    
    # Ajouter les attributs manquants pour le patient
    if 'readmitted_risk' not in patient:
        patient['readmitted_risk'] = 0.5
    if 'change_risk' not in patient:
        patient['change_risk'] = 0.45
    
    # Ensure values are not None
    if patient.get('readmitted_risk') is None:
        patient['readmitted_risk'] = 0.5
    if patient.get('change_risk') is None:
        patient['change_risk'] = 0.45
    
    return render_template('instabilite.html',
                         patient=patient,
                         patients=patients)

@bp.route('/traitement', methods=['GET'])
def traitement():
    """Identification des patients sans traitement médicamenteux"""
    patient_id = request.args.get('patient_id', 1, type=int)
    
    try:
        conn = db_config.get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM patients WHERE id = %s", (patient_id,))
                patient = cursor.fetchone()
                cursor.execute("SELECT * FROM patients")
                patients = cursor.fetchall()
                cursor.execute("SELECT * FROM patients WHERE diabetes_med = 'No'")
                patients_no_med = cursor.fetchall()
        finally:
            conn.close()
    except Exception as e:
        print(f"Erreur de connexion DB: {e}")
        # Fallback: données de démonstration
        patient = {
            'id': 1, 'nom': 'Martin', 'prenom': 'Jean', 'age': 68, 'sexe': 'M',
            'diabetes_med': 'No'
        }
        patients = [patient]
        patients_no_med = [patient]
    
    if not patient:
        patient = patients[0] if patients else {
            'id': 1, 'nom': 'Martin', 'prenom': 'Jean', 'age': 68, 'sexe': 'M',
            'diabetes_med': 'No'
        }
    
    # Contexte du formulaire Classification_DiabMed
    form_context = get_form_context()
    
    return render_template('traitement.html',
                         patient=patient,
                         patients=patients,
                         patients_no_med=patients_no_med,
                         prediction_result=None,
                         form_ready=form_context.get('ready', False),
                         form_error=form_context.get('error'),
                         form_warning=form_context.get('warning'),
                         form_numeric=form_context.get('numeric', []),
                         form_nominal=form_context.get('nominal', []),
                         form_values={})

@bp.route('/traitement/predict', methods=['POST'])
def traitement_predict():
    """Traite le formulaire de prédiction de traitement et redirige vers Classification_DiabMed"""
    conn = db_config.get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM patients")
            patients = cursor.fetchall()
            cursor.execute("SELECT * FROM patients WHERE diabetes_med = 'No'")
            patients_no_med = cursor.fetchall()
    finally:
        conn.close()
    
    if not _diabmed_state["ready"]:
        return render_template('traitement.html',
                             patient=patients[0] if patients else {},
                             patients=patients,
                             patients_no_med=[],
                             prediction_result=None,
                             form_ready=False,
                             form_error="Le modèle Classification_DiabMed n'est pas disponible.",
                             form_warning=None,
                             form_numeric=[],
                             form_nominal=[],
                             form_values={}), 503
    
    try:
        result = predict_from_form(request.form)
    except ValueError as exc:
        form_context = get_form_context(error=str(exc), values=request.form)
        return render_template('traitement.html',
                             patient=patients[0] if patients else {},
                             patients=patients,
                             patients_no_med=[],
                             prediction_result=None,
                             form_ready=form_context.get('ready', False),
                             form_error=form_context.get('error'),
                             form_warning=form_context.get('warning'),
                             form_numeric=form_context.get('numeric', []),
                             form_nominal=form_context.get('nominal', []),
                             form_values=request.form), 400
    
    prediction_result = {
        'predicted_class': 1 if result['is_no'] else 0,
        'probability': [1 - result['p_no']/100, result['p_no']/100],
        'threshold': result['seuil']/100,
        'model_type': result['modele'],
        'needs_treatment': not result['is_no'],
        'label': result['label'],
        'p_no': result['p_no'],
        'p_yes': result['p_yes'],
        'seuil': result['seuil']
    }
    
    # Stocker les résultats dans la session pour Classification_DiabMed
    session['prediction_result'] = prediction_result
    
    # Rediriger vers la page de résultat de Classification_DiabMed
    return redirect(url_for('classification_diabmed.result'))

@bp.route('/duree_sejour')
def duree_sejour():
    """Prévision de la durée de séjour"""
    patient_id = request.args.get('patient_id', 1, type=int)
    
    try:
        conn = db_config.get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM patients WHERE id = %s", (patient_id,))
                patient = cursor.fetchone()
                cursor.execute("SELECT * FROM patients")
                patients = cursor.fetchall()
        finally:
            conn.close()
    except Exception as e:
        print(f"Erreur de connexion DB: {e}")
        # Fallback: données de démonstration
        patient = {
            'id': 1, 'nom': 'Martin', 'prenom': 'Jean', 'age': 68, 'sexe': 'M',
            'time_in_hospital': 3
        }
        patients = [patient]
    
    if not patient:
        patient = patients[0] if patients else {
            'id': 1, 'nom': 'Martin', 'prenom': 'Jean', 'age': 68, 'sexe': 'M',
            'time_in_hospital': 3
        }
    
    # Ensure time_in_hospital has a value
    if patient.get('time_in_hospital') is None:
        patient['time_in_hospital'] = 3
    
    model_metrics = {
        "mae": 1.2,
        "rmse": 1.8,
        "r2": 0.78,
        "baseline_mae": 2.5,
        "baseline_rmse": 3.2,
        "improvement": 44
    }
    
    return render_template('duree_sejour.html',
                         patient=patient,
                         patients=patients,
                         metrics=model_metrics)
