# Module `time_in_hospital`

Estime la durée de séjour d'un patient diabétique (Diabetes 130-US Hospitals, 1999-2008).

## Contenu
- `__init__.py` : blueprint Flask (`NAME`, `TITLE`, `DESCRIPTION`, routes `/` et `/predict`).
- `service.py` : charge les artefacts, valide le formulaire, reconstruit les variables du modèle et prédit.
- `templates/time_in_hospital/form.html` et `result.html`.
- `artifacts/` : `config.json` et `model.joblib`, produits par le Lab 4 du notebook `Lab4_Export_Deploiement_time_in_hospital.ipynb`.

## Installation
1. Exécuter le notebook dans Google Colab (réglage `MODE` en haut) et télécharger `artifacts.zip`.
2. Copier `config.json` et `model.joblib` dans `modules/time_in_hospital/artifacts/`.
3. Installer sur le PC les mêmes versions que celles affichées par le notebook :
   `scikit-learn`, `xgboost`, `pandas`, `numpy`, `joblib`.
4. Lancer `python app.py`, ouvrir la page principale puis le bouton du module.

## Limites à connaître
- Le type de sortie et les nombres d'examens, de procédures et de médicaments ne sont connus qu'en cours ou en fin de séjour : l'estimation sert au suivi d'un séjour, pas à une prédiction dès l'admission.
- Régression : R² ≈ 0,38 sur le test ; les longs séjours sont sous-estimés. La fourchette affichée vient des quantiles 10 % et 90 % des résidus sur le jeu de test.
- Les champs absents du formulaire prennent la valeur typique du jeu d'entraînement.
