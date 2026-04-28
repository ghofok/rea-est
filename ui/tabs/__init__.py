"""Sous-modules d'onglets de l'interface Dash.

Chaque module expose au minimum :
    - render() : retourne le contenu de l'onglet
    - register_callbacks(app) : enregistre les callbacks associés
"""
import os
import sys

# Permet aux sous-modules d'importer `theme`, `state`, `components`
# qui se trouvent dans le dossier parent `ui/`, indépendamment du
# répertoire courant lors de l'exécution.
_UI_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if _UI_DIR not in sys.path:
    sys.path.insert(0, _UI_DIR)

# Permet d'importer aussi les modules de calcul (parent du dossier ui/)
_PROJECT_DIR = os.path.abspath(os.path.join(_UI_DIR, os.pardir))
if _PROJECT_DIR not in sys.path:
    sys.path.insert(0, _PROJECT_DIR)


