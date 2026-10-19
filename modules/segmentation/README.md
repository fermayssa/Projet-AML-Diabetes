# Module « Segmentation » (clustering K-Means)

Affecte un patient à l'un des 4 profils de parcours de soins trouvés par K-Means dans le notebook
`Projet_AML_KMeans_Deploiement.ipynb`.

## Fichiers

| Fichier | Rôle |
|---|---|
| `__init__.py` | Blueprint Flask : routes `/segmentation/` (formulaire) et `/segmentation/predict` (résultat) |
| `service.py` | Chargement du modèle, validation de la saisie, prétraitement d'un patient, prédiction |
| `templates/segmentation/form.html` | Formulaire de saisie |
| `templates/segmentation/result.html` | Page de résultat (profil, action suggérée, taux de réadmission) |
| `artifacts/` | **Généré par le notebook** : `model.joblib` (K-Means, ACP, StandardScaler) et `config.json` |

## Mettre en route

1. Exécuter **tout** le notebook dans Colab (« Exécuter tout »). Les dernières cellules (17 à 19) exportent les
   artefacts, vérifient qu'ils redonnent les mêmes clusters que le notebook, puis téléchargent `artifacts.zip`.
2. Dézipper `artifacts.zip` et copier `model.joblib` et `config.json` dans `modules/segmentation/artifacts/`.
3. Installer sur son PC la **même version de scikit-learn** que celle affichée par la cellule 17
   (`pip install scikit-learn==X.Y.Z`).
4. Lancer `python app.py` et ouvrir http://127.0.0.1:5000/segmentation/

Tant que `artifacts/` est vide, le module affiche un message explicite : l'application et les autres modules
continuent de fonctionner.

## Comment fonctionne le prétraitement d'un patient

Le formulaire refait, pour un seul patient, les étapes du notebook dans le même ordre :
variables dérivées (totaux, ratios par jour, comorbidités, HbA1c) → log(1+x) des compteurs de visites →
encodage one-hot → plafonnement (bornes du train) → normalisation (StandardScaler du train) →
sélection des variables → ACP → K-Means.

## Simplifications à mentionner dans le rapport

- Le formulaire ne demande pas toutes les variables : celles qui ne sont pas saisies prennent la **valeur typique du train** (médiane ou mode).
- Seuls les 6 antidiabétiques les plus fréquents (plus l'insuline) sont demandés individuellement ;
  les autres sont résumés par « nombre d'autres antidiabétiques ».
- Les noms et actions des clusters sont des hypothèses à valider par des cliniciens.
- Seul K-Means est déployé.

## Pièges déjà rencontrés

- Les médicaments à trait d'union (`glipizide-metformin`) deviennent `glipizide_metformin` dans les colonnes du modèle.
- Le modèle n'est valable qu'avec la même version de scikit-learn que celle de l'entraînement.
- Si on relance le notebook après un changement, il faut **ré-exporter** les artefacts.
