"""Point d'entrée WSGI pour le déploiement (Plotly Cloud / Dash Enterprise / Render).

Importe l'app depuis `ui/app.py` et expose la variable `server`.

Commande de démarrage (Procfile) :
    gunicorn wsgi:server
"""
import os
import sys

# Ajoute le dossier ui/ au sys.path pour que `import app` fonctionne
_HERE = os.path.dirname(os.path.abspath(__file__))
_UI_DIR = os.path.join(_HERE, "ui")
for p in (_HERE, _UI_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

from app import app, server  # noqa: F401, E402

# `server` (Flask WSGI) est exposé pour gunicorn.

