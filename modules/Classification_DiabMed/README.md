# Module Classification DiabMed

Prédit la variable `diabetesMed` (patient sous traitement antidiabétique ou non) avec un modèle XGBoost.
Classe positive du modèle = « No » (sans traitement), seuil de décision optimisé enregistré dans `model.joblib`.

| Fichier | Rôle |
|---|---|
| `__init__.py` | Blueprint Flask : pages `/Classification_DiabMed/` (formulaire) et `/predict` (résultat) |
| `service.py` | Chargement du modèle, validation de la saisie, prédiction |
| `preprocess.py` | Prétraitement (identique à celui du notebook) |
| `artifacts/config.json`, `model.json`, `model.joblib` | Exportés depuis le notebook |
| `templates/Classification_DiabMed/` | `form.html` et `result.html` |

Le modèle est chargé depuis `artifacts/model.json` (format natif XGBoost, robuste aux changements de version
et de fins de ligne) ; `artifacts/model.joblib` sert de secours.
