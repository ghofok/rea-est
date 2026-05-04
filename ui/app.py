"""
Interface Dash / Plotly pour l'analyse immobilière — point d'entrée.

⚠️  AUCUN CALCUL N'EST FAIT DANS L'UI. Tous les chiffres proviennent des
    modules Python du dossier parent (`inputs.py`, `down_payment.py`,
    `mortgage.py`, `cashflow.py`, `study_20y.py`, `sensitivity.py`).

Architecture :
    theme.py            — palette, CSS, template Plotly
    state.py            — sections de champs, formatage, Store ↔ inputs
    components.py       — composants visuels réutilisables (KPI, sections…)
    layout.py           — navbar + tabs principaux
    tabs/
        inputs_tab.py        — Onglet Paramètres + sync vers le Store
        down_payment_tab.py  — Onglet Mise de fond
        cashflow_tab.py      — Onglets Cashflow an 1 / an X
        study_tab.py         — Onglet Étude pluriannuelle
        amortization_tab.py  — Onglet Amortissement
        sensitivity_tab.py   — Onglet Sensibilité
        io_json.py           — Callbacks Export / Import JSON

Lancement :
    cd e:\\rea_est\\ui
    pip install -r requirements.txt
    python app.py
    → http://127.0.0.1:8050
"""
from __future__ import annotations
import os
import sys

# Permet d'importer les modules de calcul du dossier parent
_PARENT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if _PARENT not in sys.path:
    sys.path.insert(0, _PARENT)

import dash
import dash_bootstrap_components as dbc

from theme import INDEX_STRING
from layout import build_layout
import scenarios as scenarios_mod
import auth as auth_mod
import i18n as i18n_mod
from tabs import (inputs_tab, down_payment_tab, cashflow_tab,
                  study_tab, amortization_tab, sensitivity_tab, io_json)


def create_app() -> dash.Dash:
    app = dash.Dash(
        __name__,
        suppress_callback_exceptions=True,
        title="Analyse immobilière",
        external_stylesheets=[
            dbc.themes.FLATLY,
            "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/"
            "bootstrap-icons.css",
        ],
    )
    app.index_string = INDEX_STRING
    app.layout = build_layout

    # Enregistrement des callbacks de chaque onglet
    inputs_tab.register_callbacks(app)
    down_payment_tab.register_callbacks(app)
    cashflow_tab.register_callbacks(app)
    study_tab.register_callbacks(app)
    amortization_tab.register_callbacks(app)
    sensitivity_tab.register_callbacks(app)
    io_json.register_callbacks(app)
    scenarios_mod.register_callbacks(app)
    i18n_mod.register_callbacks(app)

    # Authentification email + mot de passe (users.json)
    auth_mod.init_auth(app)
    return app


app = create_app()
# WSGI entry point — utilisé par gunicorn / Plotly Cloud / Dash Enterprise
# (commande de démarrage : `gunicorn app:server`).
server = app.server


if __name__ == "__main__":
    # En local : python app.py
    # En production : on délègue à un serveur WSGI (gunicorn) qui importe `server`.
    port = int(os.environ.get("PORT", 8050))
    debug = os.environ.get("DASH_DEBUG", "true").lower() == "true"
    app.run( use_reloader=debug)
