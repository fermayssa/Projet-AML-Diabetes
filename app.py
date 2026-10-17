"""
Application Flask - point d'entrée COMMUN.

NE PAS MODIFIER ce fichier : il charge automatiquement tous les dossiers
présents dans modules/ (sauf ceux qui commencent par "_").
Un module en erreur est signalé sur la page d'accueil, mais ne bloque
pas les autres modules.
"""
import importlib
import pkgutil
import traceback

from flask import Flask, render_template

import modules

app = Flask(__name__)

loaded_modules = []   # modules chargés correctement
failed_modules = []   # modules en erreur

for info in pkgutil.iter_modules(modules.__path__):
    if not info.ispkg or info.name.startswith("_"):
        continue
    try:
        mod = importlib.import_module(f"modules.{info.name}")
        app.register_blueprint(mod.bp)
        loaded_modules.append({
            "title": getattr(mod, "TITLE", info.name),
            "description": getattr(mod, "DESCRIPTION", ""),
            "url": mod.bp.url_prefix or f"/{info.name}",
        })
    except Exception as exc:  # une erreur dans un module ne doit pas casser l'application
        failed_modules.append({"name": info.name, "error": repr(exc)})
        traceback.print_exc()


@app.route("/")
def home():
    return render_template("index.html", modules=loaded_modules, failed=failed_modules)


if __name__ == "__main__":
    app.run(debug=True)
