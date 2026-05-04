"""Callback d'export JSON (multi-scénarios).

L'import est géré dans ``ui/scenarios.py`` afin de remplir d'un seul coup la
collection complète de scénarios.
"""
import json
from datetime import datetime

import dash
from dash import Input, Output, State

from scenarios import default_scenarios_dict


def register_callbacks(app):
    @app.callback(
        Output("download-json", "data"),
        Input("btn-export", "n_clicks"),
        State("store-scenarios", "data"),
        prevent_initial_call=True,
    )
    def export_json(n_clicks, scn):
        if not n_clicks:
            return dash.no_update
        data = dict(scn) if scn else default_scenarios_dict()
        # Normalisation : tuples → listes
        scenarios = {}
        for name, params in (data.get("scenarios") or {}).items():
            p = dict(params)
            if isinstance(p.get("jalons_etude"), tuple):
                p["jalons_etude"] = list(p["jalons_etude"])
            scenarios[name] = p
        payload = {
            "active": data.get("active") or next(iter(scenarios), "plex"),
            "scenarios": scenarios,
        }
        content = json.dumps(payload, indent=2, ensure_ascii=False)
        filename = (f"scenarios_immobilier_"
                    f"{datetime.now():%Y%m%d_%H%M%S}.json")
        return dict(content=content, filename=filename)


