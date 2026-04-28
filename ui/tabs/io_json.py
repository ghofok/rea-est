"""Callbacks d'export / import des paramètres au format JSON."""
import json
import base64
from datetime import datetime

import dash
from dash import html, Input, Output, State, ALL

from theme import COLORS
from state import default_store_dict


def register_callbacks(app):
    @app.callback(
        Output("download-json", "data"),
        Input("btn-export", "n_clicks"),
        State("store-inputs", "data"),
        prevent_initial_call=True,
    )
    def export_json(n_clicks, store):
        if not n_clicks:
            return dash.no_update
        data = dict(store) if store else default_store_dict()
        if isinstance(data.get("jalons_etude"), tuple):
            data["jalons_etude"] = list(data["jalons_etude"])
        content = json.dumps(data, indent=2, ensure_ascii=False)
        filename = f"inputs_immobilier_{datetime.now():%Y%m%d_%H%M%S}.json"
        return dict(content=content, filename=filename)

    @app.callback(
        Output({"type": "inp", "name": ALL}, "value"),
        Output("inp-jalons", "value"),
        Output("import-status", "children"),
        Input("upload-json", "contents"),
        State("upload-json", "filename"),
        State({"type": "inp", "name": ALL}, "id"),
        prevent_initial_call=True,
    )
    def import_json(contents, filename, ids):
        if not contents:
            return [dash.no_update] * len(ids), dash.no_update, ""
        try:
            _, b64 = contents.split(",", 1)
            raw = base64.b64decode(b64).decode("utf-8")
            data = json.loads(raw)
        except Exception as e:
            msg = html.Span([html.I(className="bi bi-x-circle me-2"),
                             f"Échec de l'import : {e}"],
                            style={"color": COLORS["danger"]})
            return [dash.no_update] * len(ids), dash.no_update, msg

        new_values = []
        for i in ids:
            v = data.get(i["name"], dash.no_update)
            new_values.append(v if v is not None else dash.no_update)

        jalons = data.get("jalons_etude")
        if isinstance(jalons, (list, tuple)) and jalons:
            jalons_str = ", ".join(str(int(j)) for j in jalons)
        else:
            jalons_str = dash.no_update

        msg = html.Span([html.I(className="bi bi-check-circle me-2"),
                         f"Import réussi : {filename}"],
                        style={"color": COLORS["success"]})
        return new_values, jalons_str, msg

