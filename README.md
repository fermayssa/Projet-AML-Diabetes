# Projet AML — Patients diabétiques (Diabetes 130-US Hospitals, 1999-2008)

Application web **Flask** qui regroupe les modèles développés par chaque membre du groupe.
Chaque membre a **son propre module** (son modèle, son prétraitement, ses pages). Les modules sont
détectés **automatiquement** : personne n'a besoin de modifier les fichiers communs.

## Membres et modules

| Membre | Objectif | Dossier du module | Branche Git |
|---|---|---|---|
| (nom) | Segmentation des patients (clustering, K-Means) | `modules/segmentation` | `feature/segmentation` |
| (nom) | (objectif) | `modules/...` | `feature/...` |
| (nom) | (objectif) | `modules/...` | `feature/...` |
| (nom) | (objectif) | `modules/...` | `feature/...` |
| (nom) | (objectif) | `modules/...` | `feature/...` |

## Structure du projet

```
projet-aml-diabetes/
├── app.py                 # COMMUN - charge automatiquement les modules (ne pas modifier)
├── requirements.txt       # COMMUN - dépendances (une seule personne le modifie)
├── README.md              # COMMUN
├── .gitignore             # COMMUN
├── templates/
│   ├── base.html          # COMMUN - cadre des pages (les pages des modules l'étendent)
│   └── index.html         # COMMUN - accueil : liste des modules
├── static/style.css       # COMMUN - style
└── modules/
    ├── _modele/           # MODÈLE de module à copier (jamais chargé par l'application)
    └── <votre_module>/    # PERSONNEL - un dossier par membre
```

**Règle d'or : chacun ne modifie que SON dossier `modules/<son_module>/`.**

## Installation (une fois par personne)

```bash
git clone https://github.com/<compte>/projet-aml-diabetes.git
cd projet-aml-diabetes
python -m venv venv
venv\Scripts\activate            # Windows
source venv/bin/activate         # Mac / Linux
pip install -r requirements.txt
```

## Lancer l'application

```bash
python app.py
```
Puis ouvrir http://127.0.0.1:5000 dans le navigateur. Si un module a un problème, il est listé sur la
page d'accueil sous « Modules en erreur », et les autres modules continuent de fonctionner.

## Créer son module

1. Copier le dossier `modules/_modele` en `modules/<votre_nom>` (sans « _ » au début, sans espace ni accent).
2. Renommer `modules/<votre_nom>/templates/modele` en `modules/<votre_nom>/templates/<votre_nom>`.
3. Dans `modules/<votre_nom>/__init__.py`, changer `NAME` (même nom que le dossier), `TITLE` et `DESCRIPTION`.
4. Ajouter votre modèle sauvegardé (joblib) et votre prétraitement **dans votre dossier**.
5. Tester : `python app.py` puis ouvrir `http://127.0.0.1:5000/<votre_nom>/`.

Règles pour éviter les conflits :
- Les pages HTML de votre module sont rangées dans `templates/<votre_nom>/` (jamais directement dans `templates/`).
- Vos pages commencent par `{% extends "base.html" %}`.
- Pas de variable globale partagée entre modules ; vos fichiers (modèle, JSON...) restent dans votre dossier.

## Prétraitement : commun ou personnel ?

Chacun garde **son prétraitement** dans son module (cible, variables exclues, normalisation, etc. diffèrent).
Une fonction n'est déplacée vers un dossier commun **qu'après accord de tout le groupe** et vérification que
chaque modèle donne toujours les mêmes résultats.

## Versions des bibliothèques (important)

Un modèle sauvegardé avec une version de scikit-learn peut ne pas se recharger correctement avec une autre.
- Dans Colab : `import sklearn; print(sklearn.__version__)`
- Écrire la même version dans `requirements.txt` (ex. `scikit-learn==1.6.1`).
- Une seule personne modifie `requirements.txt` ; prévenir le groupe avant d'ajouter une bibliothèque.

## Travail avec Git

- **Ne jamais** pousser directement sur `main`.
- Une branche par personne : `feature/<module>`.
- Commits fréquents, avec un message clair (ex. `Segmentation : ajout du formulaire`).

```bash
git checkout -b feature/<module>          # créer sa branche
git add .
git commit -m "Message clair"
git push -u origin feature/<module>       # 1er envoi
git push                                  # envois suivants
git pull origin main                      # récupérer les nouveautés de main dans sa branche
```

Pour intégrer son travail : ouvrir sur GitHub une **Pull Request** de `feature/<module>` vers `main`,
la faire relire par un autre membre, puis fusionner.

## Avant d'ouvrir une Pull Request (checklist)

- [ ] `python app.py` démarre sans erreur et mon module apparaît sur l'accueil
- [ ] Je n'ai modifié aucun fichier hors de `modules/<mon_module>/`
- [ ] Mes pages sont dans `templates/<mon_module>/`
- [ ] Mon module explique clairement les erreurs de saisie (pas de plantage)
- [ ] `git pull origin main` fait sans conflit

## Avertissement

Cette application est une **démonstration pédagogique** réalisée dans le cadre d'un cours.
Elle ne constitue pas un outil médical. Les données (UCI, 1999-2008, hôpitaux américains) ne reflètent pas
nécessairement la pratique actuelle. N'utiliser aucune donnée réelle de patient.
