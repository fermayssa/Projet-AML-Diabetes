"""
Routes pour le module Classification_DiabMed
"""
from flask import render_template, request, jsonify, session, redirect, url_for
from . import bp

@bp.route('/')
def index():
    """Page d'accueil du module de classification"""
    return render_template('index.html')

@bp.route('/form')
def form():
    """Formulaire de classification"""
    return render_template('form.html')

@bp.route('/predict', methods=['POST'])
def predict():
    """Prédiction de classification"""
    data = request.get_json()
    # TODO: Implémenter la logique de prédiction
    return jsonify({'result': 'success'})

@bp.route('/result')
def result():
    """Affichage du résultat de classification"""
    # Récupérer les résultats de prédiction depuis la session
    prediction_result = session.pop('prediction_result', None)
    return render_template('result.html', prediction_result=prediction_result)
