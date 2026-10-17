"""Module SEGMENTATION : affecte un patient à l'un des profils trouvés par K-Means."""
from flask import Blueprint, render_template, request

from . import service

NAME = "segmentation"
TITLE = "Segmentation des patients (clustering)"
DESCRIPTION = "Affecte un patient à l'un des profils de parcours de soins identifiés par K-Means."

bp = Blueprint(NAME, __name__, url_prefix=f"/{NAME}", template_folder="templates")


@bp.route("/")
def form():
    return render_template("segmentation/form.html", **service.form_context())


@bp.route("/predict", methods=["POST"])
def predict():
    if not service.is_ready():
        return render_template("segmentation/form.html", **service.form_context()), 503
    try:
        result = service.predict(request.form)
    except ValueError as exc:   # saisie invalide : on réaffiche le formulaire avec le message
        return render_template("segmentation/form.html", **service.form_context(error=str(exc),
                               values=request.form)), 400
    return render_template("segmentation/result.html", r=result)
