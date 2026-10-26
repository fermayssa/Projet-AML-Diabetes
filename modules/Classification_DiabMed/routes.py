"""
Routes pour le module Classification_DiabMed
"""
import os
import json
import pandas as pd
from flask import render_template, request, jsonify, session, redirect, url_for
from . import bp

# Chemins vers les artefacts
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ARTIFACTS_DIR = os.path.join(BASE_DIR, 'modules', 'Classification_DiabMed', 'artifacts')
CONFIG_PATH = os.path.join(ARTIFACTS_DIR, 'config.json')
MODEL_PATH = os.path.join(ARTIFACTS_DIR, 'model.joblib')
PREPROCESS_PATH = os.path.join(BASE_DIR, 'modules', 'preprocess.py')

@bp.route('/')
def index():
    """Page d'accueil du module de classification"""
    return render_template('index.html')

@bp.route('/form')
def form():
    """Formulaire de classification"""
    # Charger la configuration pour les catégories
    try:
        with open(CONFIG_PATH, 'r') as f:
            config = json.load(f)
        return render_template('form.html', config=config)
    except Exception:
        return render_template('form.html', config=None)

@bp.route('/predict', methods=['POST'])
def predict():
    """Prédiction de classification"""
    try:
        data = request.get_json()
        
        # Charger la configuration
        with open(CONFIG_PATH, 'r') as f:
            config = json.load(f)
        
        # Charger le modèle
        import joblib
        model = joblib.load(MODEL_PATH)
        
        # Charger la fonction de préparation
        import importlib.util
        spec = importlib.util.spec_from_file_location("preprocess", PREPROCESS_PATH)
        preprocess_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(preprocess_module)
        
        # Créer un DataFrame à partir des données
        df = pd.DataFrame([data])
        
        # Préparer les données
        X = preprocess_module.preparer(df, config)
        
        # Prédire la probabilité
        p_yes = model.predict_proba(X)[0, 1]  # P(traité)
        p_no = 1 - p_yes  # P(sans traitement)
        
        # Seuil de décision
        seuil = config.get('seuil', 0.653)
        
        # Déterminer si signalé (sans traitement probable)
        needs_treatment = p_no >= seuil
        
        # Stocker le résultat dans la session
        prediction_result = {
            'needs_treatment': needs_treatment,
            'p_no': round(p_no * 100, 1),
            'p_yes': round(p_yes * 100, 1),
            'seuil': round(seuil * 100, 1),
            'model_type': config.get('modele', 'XGBoost'),
            'label': 'À examiner : sans traitement probable' if needs_treatment else 'Sous traitement antidiabétique probable'
        }
        session['prediction_result'] = prediction_result
        
        return jsonify({'success': True, 'redirect': url_for('classification_diabmed.result')})
        
    except Exception as e:
        return jsonify({'success': False, 'error': 'Une erreur est survenue lors de la prédiction'}), 500

@bp.route('/result')
def result():
    """Affichage du résultat de classification"""
    # Récupérer les résultats de prédiction depuis la session
    prediction_result = session.pop('prediction_result', None)
    return render_template('result.html', prediction_result=prediction_result)
