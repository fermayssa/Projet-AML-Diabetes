# Module classification_change

Prédit si le traitement antidiabétique d'un patient sera modifié (cible `change` = « Ch »), avec XGBoost.

- `artifacts/model.json` : modèle XGBoost (format JSON natif, portable)
- `artifacts/preprocessor.joblib` : préprocesseur (StandardScaler, OneHotEncoder)
- `artifacts/config.json` : colonnes, bornes d'écrêtage, valeurs par défaut, catégories, versions
- `service.py` : prétraitement d'un patient + prédiction
- `templates/classification_change/` : formulaire et résultat

Versions : scikit-learn 1.8.0, xgboost 3.4.1, pandas 3.0.2, numpy 2.4.4 (Python 3.12 ou plus).
