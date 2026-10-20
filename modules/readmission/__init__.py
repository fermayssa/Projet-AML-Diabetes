"""Module RÉADMISSION : prédit la catégorie de réadmission d'un patient (<30, >30, NO) avec XGBoost."""
from flask import Blueprint, render_template, request

from . import service

NAME = "readmission"
TITLE = "Réadmission des patients (XGBoost)"
DESCRIPTION = ("Prédit si un patient diabétique sera réadmis en moins de 30 jours, plus tard ou jamais, "
               "et signale les patients à surveiller en priorité.")

bp = Blueprint(NAME, __name__, url_prefix=f"/{NAME}", template_folder="templates")


@bp.route("/")
def form():
    return render_template("readmission/form.html", **service.form_context())


@bp.route("/predict", methods=["POST"])
def predict():
    if not service.is_ready():
        return render_template("readmission/form.html", **service.form_context()), 503
    try:
        result = service.predict(request.form)
    except ValueError as exc:   # saisie invalide : on réaffiche le formulaire avec le message
        return render_template("readmission/form.html", **service.form_context(error=str(exc),
                               values=request.form)), 400
    return render_template("readmission/result.html", r=result)
