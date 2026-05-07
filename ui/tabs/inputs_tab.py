"""Onglet 1 — Paramètres (formulaire d'entrées + sync vers le Store)."""
from dash import dcc, html, Input, Output, State
import dash_bootstrap_components as dbc

from inputs import PropertyInputs
from theme import COLORS
from components import _section
from state import (FIELD_SECTIONS, EDITABLE_FIELDS, default_store_dict,
                   field_sections_translated)
from i18n import t


def render(initial_store: dict | None = None):
    inp = PropertyInputs()
    # Si on a des valeurs sauvegardées, on les utilise pour pré-remplir
    if initial_store:
        from dataclasses import fields as dc_fields
        for f in dc_fields(inp):
            if f.name in initial_store and initial_store[f.name] is not None:
                try:
                    val = initial_store[f.name]
                    cur = getattr(inp, f.name)
                    if isinstance(cur, bool):
                        val = bool(val)
                    elif isinstance(cur, int):
                        val = int(val)
                    elif isinstance(cur, float):
                        val = float(val)
                    setattr(inp, f.name, val)
                except Exception:
                    pass
    cols = []
    for title, icon, flist in field_sections_translated():
        rows = []
        for attr, libelle, widget in flist:
            current = getattr(inp, attr)
            if widget == "bool":
                options = ([{"label": t("yes_condo"), "value": True},
                            {"label": t("no_condo"),  "value": False}]
                           if attr == "est_condo" else
                           [{"label": t("yes"), "value": True},
                            {"label": t("no"),  "value": False}])
                ctrl = dcc.Dropdown(id={"type": "inp", "name": attr},
                                    options=options, value=bool(current),
                                    clearable=False)
            else:
                ctrl = dbc.Input(id={"type": "inp", "name": attr},
                                 type="number", value=current, size="sm")
            rows.append(dbc.Row([
                dbc.Col(html.Label(libelle, className="form-label-row"),
                        md=6, className="d-flex align-items-center"),
                dbc.Col(ctrl, md=6),
            ], className="mb-2"))
        cols.append(dbc.Col(_section(title, rows, icon=icon), md=6, lg=4))

    # Jalons étude pluriannuelle
    jalons = inp.jalons_etude
    if initial_store and isinstance(initial_store.get("jalons_etude"), (list, tuple)):
        jalons = initial_store["jalons_etude"]
    jalons_default = ", ".join(str(j) for j in jalons)
    cols.append(dbc.Col(_section(
        t("milestones_title"),
        [dbc.Row([
            dbc.Col(html.Label(t("milestones_help"),
                               className="form-label-row"),
                    md=6, className="d-flex align-items-center"),
            dbc.Col(dbc.Input(id="inp-jalons", type="text",
                              value=jalons_default, size="sm"), md=6),
        ])], icon="bi-flag"), md=6, lg=4))

    return html.Div([
        html.Div([
            html.H4([html.I(className="bi bi-sliders2 me-2"),
                     t("inputs_title")], className="mb-1"),
            html.P(t("inputs_help"), className="text-muted"),
            # Barre d'actions Export / Import
            dbc.Row([
                dbc.Col([
                    dbc.Button([html.I(className="bi bi-download me-2"),
                                t("export_json")],
                               id="btn-export", color="primary",
                               outline=True, size="sm", className="me-2"),
                    dcc.Upload(
                        id="upload-json",
                        children=dbc.Button(
                            [html.I(className="bi bi-upload me-2"),
                             t("import_json")],
                            color="secondary", outline=True, size="sm"),
                        multiple=False, accept=".json",
                        style={"display": "inline-block"},
                    ),
                    dcc.Download(id="download-json"),
                ], md=12),
            ], className="mb-2"),
            html.Div(id="inputs-status",
                     style={"color": COLORS["success"], "fontWeight": 500,
                            "marginBottom": "14px"}),
            html.Div(id="import-status",
                     style={"fontWeight": 500, "marginBottom": "10px"}),
        ]),
        dbc.Row(cols, className="g-3"),
    ], className="p-4")


def register_callbacks(app):
    @app.callback(
        Output("store-inputs", "data"),
        Output("store-scenarios", "data"),
        Output("inputs-status", "children"),
        [Input({"type": "inp", "name": attr}, "value")
         for attr, _, _ in EDITABLE_FIELDS],
        Input("inp-jalons", "value"),
        State("store-inputs", "data"),
        State("store-scenarios", "data"),
        prevent_initial_call=True,
    )
    def sync_inputs(*args):
        *values, jalons_str, current, scn = args
        data = dict(current) if current else default_store_dict()

        changed = False
        for (attr, _, _), v in zip(EDITABLE_FIELDS, values):
            if v is not None and data.get(attr) != v:
                changed = True
            data[attr] = v
        if jalons_str:
            try:
                new_jalons = [int(x.strip())
                              for x in str(jalons_str).split(",")
                              if x.strip()]
                if new_jalons != data.get("jalons_etude"):
                    changed = True
                data["jalons_etude"] = new_jalons
            except Exception:
                pass

        if not changed:
            # Rien n'a réellement changé — ne pas écraser le store
            from dash import no_update
            return no_update, no_update, ""

        # Persistance dans le scénario actif
        from scenarios import default_scenarios_dict
        scn = dict(scn) if scn else default_scenarios_dict()
        scn.setdefault("scenarios", {})
        active = scn.get("active") or next(iter(scn["scenarios"]), "plex")
        scn["active"] = active
        scn["scenarios"][active] = dict(data)
        return data, scn, t("inputs_updated")

