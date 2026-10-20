"""
Module CLASSIFICATION DIABMED : prédit si un patient diabétique est sous traitement antidiabétique
(variable cible diabetesMed) à partir de ses données d'hospitalisation (modèle XGBoost).
"""
from flask import Blueprint, render_template, request

from . import service

NAME = "Classification_DiabMed"                # = nom du dossier du module
TITLE = "Classification DiabMed (XGBoost)"
DESCRIPTION = "Prédit si un patient diabétique est sous traitement antidiabétique (diabetesMed)."

bp = Blueprint(NAME, __name__, url_prefix=f"/{NAME}", template_folder="templates")


@bp.route("/")
def form():
    return render_template(f"{NAME}/form.html", **service.form_context())


@bp.route("/predict", methods=["POST"])
def predict():
    if not service.is_ready():
        return render_template(f"{NAME}/form.html", **service.form_context()), 503
    try:
        result = service.predict(request.form)
    except ValueError as exc:   # saisie invalide : on réaffiche le formulaire avec le message
        return render_template(f"{NAME}/form.html",
                               **service.form_context(error=str(exc), values=request.form)), 400
    return render_template(f"{NAME}/result.html", r=result)
