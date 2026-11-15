"""Module CLASSIFICATION_CHANGE : prédit si le traitement antidiabétique d'un patient sera modifié."""
from flask import Blueprint, redirect, render_template, request, session, url_for

from . import service

NAME = "classification_change"
TITLE = "Changement de traitement"
DESCRIPTION = ("Prédit si le traitement antidiabétique d'un patient sera modifié pendant son séjour "
               "à partir des informations connues à l'hôpital.")

bp = Blueprint(NAME, __name__, url_prefix=f"/{NAME}", template_folder="templates")


@bp.before_request
def require_login():
    if "user" not in session:
        return redirect(url_for("login"))


@bp.route("/")
def form():
    return render_template("classification_change/form.html", **service.form_context())


@bp.route("/predict", methods=["POST"])
def predict():
    if not service.is_ready():
        return render_template("classification_change/form.html", **service.form_context()), 503
    try:
        result = service.predict(request.form)
    except ValueError as exc:
        return render_template("classification_change/form.html",
                               **service.form_context(error=str(exc), values=request.form)), 400
    return render_template("classification_change/result.html", r=result)
