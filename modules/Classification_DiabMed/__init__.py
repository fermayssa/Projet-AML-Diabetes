"""
Module Classification_DiabMed - Classification de patients diabétiques
"""
import os
from flask import Blueprint

# Chemin vers le dossier templates du module
template_dir = os.path.join(os.path.dirname(__file__), 'templates_classification_diabMed')

bp = Blueprint('classification_diabmed', __name__, url_prefix='/classification-diabmed', template_folder=template_dir)

TITLE = "Classification DiabMed"
DESCRIPTION = "Système de classification de patients diabétiques"

from . import routes
