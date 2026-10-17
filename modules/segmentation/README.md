# Module « Segmentation » (clustering K-Means)

Affecte un patient à l'un des profils de parcours de soins trouvés par K-Means dans le notebook
`Projet_AML_Clustering_Diabetes.ipynb`.

## Fichiers

| Fichier | Rôle |
|---|---|
| `__init__.py` | Blueprint Flask : routes `/segmentation/` (formulaire) et `/segmentation/predict` (résultat) |
| `service.py` | Chargement du modèle, validation de la saisie, prétraitement d'un patient, prédiction |
| `templates/segmentation/form.html` | Formulaire de saisie |
| `templates/segmentation/result.html` | Page de résultat (profil, action suggérée, taux de réadmission) |
| `artifacts/` | **À générer depuis le notebook** : `model.joblib` (K-Means, ACP, StandardScaler) et `config.json` |
| `export_cell.py` | Cellule à copier à la fin du notebook pour générer `artifacts/` |

## Mettre en route (une fois le notebook exécuté)

1. Ouvrir le notebook (Colab) et exécuter **toutes** les cellules jusqu'à la partie 16.
2. Ajouter à la fin du notebook une cellule contenant le contenu de `export_cell.py` et l'exécuter.
   - Vérifier / adapter le dictionnaire `CLUSTER_INFO` (nom, description, action de chaque cluster) :
     les numéros doivent correspondre à ceux de **votre** tableau de profils.
3. Récupérer le fichier `artifacts.zip` téléchargé et copier son contenu dans `modules/segmentation/artifacts/`.
4. Mettre dans `requirements.txt` la version de scikit-learn affichée par la cellule d'export.
5. Lancer `python app.py` et ouvrir http://127.0.0.1:5000/segmentation/

Tant que `artifacts/` est vide, le module affiche un message explicite : l'application et les autres modules fonctionnent.

## Comment fonctionne le prétraitement d'un patient

Le formulaire refait, pour un seul patient, les étapes du notebook dans le même ordre :
variables dérivées (totaux, ratios par jour, comorbidités, HbA1c) → log(1+x) des compteurs de visites →
encodage one-hot → plafonnement (bornes du train) → normalisation (StandardScaler du train) →
sélection des variables → ACP → K-Means.

Le module a été vérifié sur des données de même schéma : pour 1 500 patients du jeu de test, le vecteur de
variables et le cluster obtenus par l'application sont **identiques** à ceux du notebook.

## Simplifications à mentionner dans le rapport

- Le formulaire ne demande pas les ~50 variables : celles qui ne sont pas saisies prennent la **valeur typique du train** (médiane ou mode).
- Seuls les 6 antidiabétiques les plus fréquents (plus l'insuline) sont demandés individuellement ;
  les autres sont résumés par « nombre d'autres antidiabétiques ».
- Les noms et actions des clusters sont des hypothèses à valider par des cliniciens.
- Seul K-Means est déployé (K-Prototypes nécessiterait un prétraitement différent, pour un gain très faible).

## Pièges déjà rencontrés

- Les médicaments à trait d'union (`glipizide-metformin`) deviennent `glipizide_metformin` dans les colonnes du modèle.
- Le modèle n'est valable qu'avec la même version de scikit-learn que celle de l'entraînement.
