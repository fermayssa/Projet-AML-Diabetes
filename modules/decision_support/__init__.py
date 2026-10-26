"""
Module Decision Support - Aide à la décision clinique pour patients diabétiques
"""
import os
from flask import Blueprint

# Chemin vers le dossier templates du module
template_dir = os.path.join(os.path.dirname(__file__), 'templates_decision_support')

bp = Blueprint('decision_support', __name__, url_prefix='/decision-support', template_folder=template_dir)

TITLE = "Aide à la Décision"
DESCRIPTION = "Système d'aide à la décision clinique pour patients diabétiques"

from . import routes
