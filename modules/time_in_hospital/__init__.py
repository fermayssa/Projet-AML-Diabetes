"""Module TIME_IN_HOSPITAL : estime la durée de séjour d'un patient diabétique."""
from flask import Blueprint, render_template, request

from . import service

NAME = "time_in_hospital"
TITLE = "Durée de séjour hospitalier"
DESCRIPTION = "Estime la durée de séjour d'un patient diabétique à partir de son profil clinique."

bp = Blueprint(NAME, __name__, url_prefix=f"/{NAME}", template_folder="templates")


@bp.route("/")
def form():
    return render_template("time_in_hospital/form.html", **service.form_context())


@bp.route("/predict", methods=["POST"])
def predict():
    if not service.is_ready():
        return render_template("time_in_hospital/form.html", **service.form_context()), 503
    try:
        result = service.predict(request.form.to_dict())
    except ValueError as exc:
        return render_template(
            "time_in_hospital/form.html",
            **service.form_context(error=str(exc), values=request.form.to_dict()),
        ), 400
    return render_template("time_in_hospital/result.html", result=result)
