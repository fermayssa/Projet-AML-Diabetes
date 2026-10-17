"""
MODÈLE DE MODULE - à copier, ne pas modifier.

Pour créer votre module :
  1. copier le dossier  modules/_modele  ->  modules/votre_nom   (sans "_" au début)
  2. renommer aussi  templates/modele  ->  templates/votre_nom   (même nom que NAME)
  3. changer NAME, TITLE et DESCRIPTION ci-dessous
Rien d'autre à modifier : app.py détecte automatiquement votre module.
"""
from flask import Blueprint, render_template, request

NAME = "modele"                                # = nom du dossier du module (sans espace)
TITLE = "Titre affiché sur la page d'accueil"
DESCRIPTION = "Une phrase qui décrit votre modèle."

bp = Blueprint(NAME, __name__, url_prefix=f"/{NAME}", template_folder="templates")


@bp.route("/")
def form():
    return render_template(f"{NAME}/form.html")


@bp.route("/predict", methods=["POST"])
def predict():
    data = request.form.to_dict()
    result = "TODO : appeler votre modèle ici"
    return render_template(f"{NAME}/result.html", result=result, data=data)
