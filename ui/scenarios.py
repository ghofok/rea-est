"""Gestion des scénarios (colonne latérale gauche).

Chaque scénario contient un jeu de paramètres complet (équivalent à
``store-inputs``).  Le scénario actif alimente tous les onglets de calcul.
L'utilisateur peut ajouter / supprimer un scénario et basculer entre eux.
L'export / import JSON inclut l'ensemble des scénarios.
"""
from __future__ import annotations
import json
import base64

import dash
from dash import dcc, html, Input, Output, State, ALL, ctx, no_update
import dash_bootstrap_components as dbc

from theme import COLORS
from state import default_store_dict
from i18n import t


DEFAULT_NAME = "plex"


# --------------------------------------------------------------------- #
# Données par défaut
# --------------------------------------------------------------------- #
def default_scenarios_dict() -> dict:
    """Structure stockée dans ``dcc.Store(id='store-scenarios')``."""
    return {
        "active": DEFAULT_NAME,
        "scenarios": {DEFAULT_NAME: default_store_dict()},
    }


# --------------------------------------------------------------------- #
# Composants
# --------------------------------------------------------------------- #
def _scenario_row(name: str, active: bool, can_delete: bool):
    color = "primary" if active else "light"
    icon = "bi bi-check2-circle me-2" if active else "bi bi-circle me-2"
    return html.Div(
        dbc.ButtonGroup([
            dbc.Button(
                [html.I(className=icon), name],
                id={"type": "scenario-select", "name": name},
                color=color, size="sm",
                className="text-start flex-grow-1",
                style={"textAlign": "left", "fontWeight": 500},
            ),
            dbc.Button(
                html.I(className="bi bi-x-lg"),
                id={"type": "scenario-delete", "name": name},
                color="danger", outline=True, size="sm",
                disabled=not can_delete,
                title=t("delete_scenario"),
            ),
        ], className="w-100"),
        className="d-flex",
    )


def render_sidebar():
    """Carte sidebar listant les scénarios + bouton d'ajout."""
    return html.Div([
        html.Div([
            html.H6(
                [html.I(className="bi bi-collection me-2"), t("scenarios")],
                className="mb-1", style={"color": COLORS["dark"]},
            ),
            html.Small(
                t("click_to_switch"),
                className="text-muted d-block mb-3",
            ),
            html.Div(id="scenario-list", className="d-grid gap-2 mb-3"),
            dbc.InputGroup([
                dbc.Input(
                    id="scenario-new-name",
                    placeholder=t("new_scenario_ph"),
                    size="sm",
                ),
                dbc.Button(
                    [html.I(className="bi bi-plus-lg")],
                    id="btn-scenario-add", color="primary", size="sm",
                    title=t("add_scenario_title"),
                ),
            ], size="sm"),
            # Store factice : cible des callbacks de persistance disque.
            dcc.Store(id="scenario-save-sink"),
        ], className="p-3", style={
            "background": "#ffffff",
            "borderRadius": "14px",
            "boxShadow": "0 2px 10px rgba(44,62,80,0.06)",
            "position": "sticky",
            "top": "12px",
        }),
    ])


# --------------------------------------------------------------------- #
# Callbacks
# --------------------------------------------------------------------- #
def register_callbacks(app):
    # ---- Re-rendu de la liste -------------------------------------------
    @app.callback(
        Output("scenario-list", "children"),
        Input("store-scenarios", "data"),
    )
    def _render_list(scn):
        scn = scn or default_scenarios_dict()
        active = scn.get("active")
        names = list(scn.get("scenarios", {}).keys())
        can_delete = len(names) > 1
        return [_scenario_row(n, n == active, can_delete) for n in names]

    # ---- Sauvegarde automatique sur disque (par utilisateur) ----------
    @app.callback(
        Output("scenario-save-sink", "data"),
        Input("store-scenarios", "data"),
        prevent_initial_call=True,
    )
    def _save_scenarios(scn):
        try:
            from flask import session
            from user_store import save_scenarios
            save_scenarios(session.get("user"), scn)
        except Exception:
            pass
        return no_update

    # ---- Sélection / Ajout / Suppression / Import -----------------------
    @app.callback(
        Output("store-scenarios", "data", allow_duplicate=True),
        Output("store-inputs",    "data", allow_duplicate=True),
        Output({"type": "inp", "name": ALL}, "value", allow_duplicate=True),
        Output("inp-jalons",        "value", allow_duplicate=True),
        Output("scenario-new-name", "value"),
        Output("import-status",     "children", allow_duplicate=True),
        Input({"type": "scenario-select", "name": ALL}, "n_clicks"),
        Input({"type": "scenario-delete", "name": ALL}, "n_clicks"),
        Input("btn-scenario-add", "n_clicks"),
        Input("upload-json",       "contents"),
        State("upload-json",       "filename"),
        State("scenario-new-name", "value"),
        State("store-scenarios",   "data"),
        State({"type": "inp", "name": ALL}, "id"),
        prevent_initial_call=True,
    )
    def _actions(sel_clicks, del_clicks, add_clicks, upload_contents,
                 upload_filename, new_name, scn, ids):
        scn = dict(scn) if scn else default_scenarios_dict()
        scn.setdefault("scenarios", {})
        if not scn["scenarios"]:
            scn["scenarios"][DEFAULT_NAME] = default_store_dict()
        scn.setdefault("active", next(iter(scn["scenarios"])))

        trig = ctx.triggered_id
        msg = no_update
        noop = (no_update, no_update,
                [no_update] * len(ids), no_update, no_update, no_update)
        if trig is None:
            return noop

        # ----- Sélection ------------------------------------------------
        if isinstance(trig, dict) and trig.get("type") == "scenario-select":
            if not any(sel_clicks or []):
                return noop
            name = trig["name"]
            if name in scn["scenarios"]:
                scn["active"] = name
            else:
                return noop

        # ----- Suppression ---------------------------------------------
        elif isinstance(trig, dict) and trig.get("type") == "scenario-delete":
            if not any(del_clicks or []):
                return noop
            name = trig["name"]
            if name in scn["scenarios"] and len(scn["scenarios"]) > 1:
                scn["scenarios"].pop(name, None)
                if scn["active"] == name:
                    scn["active"] = next(iter(scn["scenarios"]))
            else:
                return noop

        # ----- Ajout ---------------------------------------------------
        elif trig == "btn-scenario-add":
            if not add_clicks:
                return noop
            base = (new_name or "").strip() or "Scénario"
            name = base
            i = 2
            while name in scn["scenarios"]:
                name = f"{base} {i}"
                i += 1
            src = scn["scenarios"].get(scn["active"]) or default_store_dict()
            scn["scenarios"][name] = dict(src)
            scn["active"] = name

        # ----- Import JSON ---------------------------------------------
        elif trig == "upload-json":
            if not upload_contents:
                return noop
            try:
                _, b64 = upload_contents.split(",", 1)
                data = json.loads(base64.b64decode(b64).decode("utf-8"))
            except Exception as e:
                err = html.Span(
                    [html.I(className="bi bi-x-circle me-2"),
                     f"Échec de l'import : {e}"],
                    style={"color": COLORS["danger"]},
                )
                return (no_update, no_update,
                        [no_update] * len(ids), no_update, no_update, err)

            # Format multi-scénarios
            if (isinstance(data, dict)
                    and isinstance(data.get("scenarios"), dict)
                    and data["scenarios"]):
                scn = {
                    "active": data.get("active")
                              or next(iter(data["scenarios"])),
                    "scenarios": {k: dict(v)
                                  for k, v in data["scenarios"].items()},
                }
                if scn["active"] not in scn["scenarios"]:
                    scn["active"] = next(iter(scn["scenarios"]))
            else:
                # Format hérité (dict plat) → un seul scénario "plex"
                scn = {"active": DEFAULT_NAME,
                       "scenarios": {DEFAULT_NAME: dict(data)}}

            msg = html.Span(
                [html.I(className="bi bi-check-circle me-2"),
                 f"Import réussi : {upload_filename} "
                 f"({len(scn['scenarios'])} scénario(s))"],
                style={"color": COLORS["success"]},
            )
        else:
            return noop

        # ----- Propagation du scénario actif vers le formulaire ---------
        active_data = dict(scn["scenarios"][scn["active"]])
        form_values = [active_data.get(i["name"], no_update) for i in ids]
        jalons = active_data.get("jalons_etude")
        if isinstance(jalons, (list, tuple)) and jalons:
            jalons_str = ", ".join(str(int(j)) for j in jalons)
        else:
            jalons_str = no_update

        return scn, active_data, form_values, jalons_str, "", msg

