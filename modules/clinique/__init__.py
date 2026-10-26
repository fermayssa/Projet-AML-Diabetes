"""
Module Clinique - Gestion des patients et rendez-vous
"""
import os
from flask import Blueprint

# Chemin vers le dossier templates du module
template_dir = os.path.join(os.path.dirname(__file__), 'templates_clinique')

bp = Blueprint('clinique', __name__, url_prefix='/clinique', template_folder=template_dir)

TITLE = "Clinique"
DESCRIPTION = "Système de gestion de clinique : patients, rendez-vous, consultations"

from . import routes
