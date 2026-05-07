"""Gestion des scénarios (colonne latérale gauche).

Chaque scénario contient un jeu de paramètres complet (équivalent à
``store-inputs``).  Le scénario actif alimente tous les onglets de calcul.
L'utilisateur peut ajouter / supprimer un scénario et basculer entre eux.
L'export / import JSON inclut l'ensemble des scénarios.
"""
from __future__ import annotations
import json
import base64
import io

import dash
from dash import dcc, html, Input, Output, State, ALL, ctx, no_update
import dash_bootstrap_components as dbc

from theme import COLORS
from state import default_store_dict, build_inputs_from_store, fmt_money0, fmt_money
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
                html.I(className="bi bi-pencil"),
                id={"type": "scenario-rename", "name": name},
                color="info", outline=True, size="sm",
                title="Renommer",
            ),
            dbc.Button(
                html.I(className="bi bi-file-earmark-pdf"),
                id={"type": "scenario-pdf", "name": name},
                color="success", outline=True, size="sm",
                title="Exporter PDF",
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
            dcc.Store(id="scenario-rename-target", data=""),
            dcc.Download(id="scenario-pdf-download"),
        ], className="p-3", style={
            "background": "#ffffff",
            "borderRadius": "14px",
            "boxShadow": "0 2px 10px rgba(44,62,80,0.06)",
            "position": "sticky",
            "top": "12px",
        }),
        # Modal renommage
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle("Renommer le scénario")),
            dbc.ModalBody(
                dbc.Input(id="scenario-rename-input", placeholder="Nouveau nom…", size="sm"),
            ),
            dbc.ModalFooter([
                dbc.Button("Annuler", id="btn-rename-cancel", color="secondary", outline=True),
                dbc.Button("Confirmer", id="btn-rename-confirm", color="primary", className="ms-2"),
            ]),
        ], id="modal-rename-scenario", is_open=False),
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
    _last_saved_hash = {}  # email → hash du dernier scénario sauvegardé

    @app.callback(
        Output("scenario-save-sink", "data"),
        Input("store-scenarios", "data"),
        prevent_initial_call=True,
    )
    def _save_scenarios(scn):
        from flask import session, has_request_context
        from user_store import save_scenarios
        import mongo_store
        import hashlib as _hl

        if not has_request_context():
            print("[scenarios] Pas de contexte Flask — sauvegarde ignorée.")
            return no_update

        email = session.get("user")
        if not email:
            print("[scenarios] Pas d'utilisateur en session — sauvegarde ignorée.")
            return no_update

        # Éviter les sauvegardes en double (même données)
        try:
            sig = _hl.md5(json.dumps(scn, sort_keys=True,
                                      default=str).encode()).hexdigest()
            if _last_saved_hash.get(email) == sig:
                return no_update
        except Exception:
            sig = None

        try:
            save_scenarios(email, scn)
            if sig:
                _last_saved_hash[email] = sig
            print(f"[scenarios] Sauvegardé pour {email} "
                  f"(actif={scn.get('active') if scn else '?'}, "
                  f"nb={len((scn or {}).get('scenarios') or {})})")
        except Exception as exc:
            print(f"[scenarios] ERREUR sauvegarde: {exc}")

        try:
            mongo_store.log_activity(
                email, "save_scenarios",
                active=(scn or {}).get("active"),
                n_scenarios=len((scn or {}).get("scenarios") or {}),
            )
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

    # ---- Renommage : ouvrir la modale ----------------------------------
    @app.callback(
        Output("modal-rename-scenario", "is_open", allow_duplicate=True),
        Output("scenario-rename-target", "data", allow_duplicate=True),
        Output("scenario-rename-input", "value", allow_duplicate=True),
        Input({"type": "scenario-rename", "name": ALL}, "n_clicks"),
        prevent_initial_call=True,
    )
    def _open_rename(n_clicks):
        if not any(n_clicks or []):
            return no_update, no_update, no_update
        trig = ctx.triggered_id
        if not isinstance(trig, dict):
            return no_update, no_update, no_update
        name = trig["name"]
        return True, name, name

    # ---- Renommage : confirmer ou annuler --------------------------------
    @app.callback(
        Output("modal-rename-scenario", "is_open"),
        Output("store-scenarios", "data", allow_duplicate=True),
        Output("store-inputs", "data", allow_duplicate=True),
        Input("btn-rename-confirm", "n_clicks"),
        Input("btn-rename-cancel", "n_clicks"),
        State("scenario-rename-target", "data"),
        State("scenario-rename-input", "value"),
        State("store-scenarios", "data"),
        prevent_initial_call=True,
    )
    def _do_rename(n_confirm, n_cancel, old_name, new_name, scn):
        trig = ctx.triggered_id
        if trig == "btn-rename-cancel" or not n_confirm:
            return False, no_update, no_update
        new_name = (new_name or "").strip()
        if not new_name or not old_name:
            return False, no_update, no_update

        scn = dict(scn) if scn else default_scenarios_dict()
        scenarios = scn.get("scenarios", {})
        if old_name not in scenarios or (new_name != old_name and new_name in scenarios):
            return False, no_update, no_update

        new_scenarios = {}
        for k, v in scenarios.items():
            new_scenarios[new_name if k == old_name else k] = v
        scn["scenarios"] = new_scenarios
        if scn.get("active") == old_name:
            scn["active"] = new_name
        active_data = dict(scn["scenarios"][scn["active"]])
        return False, scn, active_data

    # ---- Génération PDF récapitulatif -----------------------------------
    @app.callback(
        Output("scenario-pdf-download", "data"),
        Input({"type": "scenario-pdf", "name": ALL}, "n_clicks"),
        State("store-scenarios", "data"),
        prevent_initial_call=True,
    )
    def _export_pdf(n_clicks, scn):
        if not any(n_clicks or []):
            return no_update
        trig = ctx.triggered_id
        if not isinstance(trig, dict):
            return no_update
        name = trig["name"]
        scn = scn or default_scenarios_dict()
        scenario_data = scn.get("scenarios", {}).get(name)
        if not scenario_data:
            return no_update

        pdf_bytes = _generate_scenario_pdf(name, scenario_data)
        encoded = base64.b64encode(pdf_bytes).decode()
        safe_name = "".join(c if c.isalnum() or c in " _-" else "_" for c in name)
        return dict(
            content=encoded,
            filename=f"scenario_{safe_name}.pdf",
            base64=True,
        )


# --------------------------------------------------------------------- #
# Génération PDF
# --------------------------------------------------------------------- #
def _generate_scenario_pdf(name: str, data: dict) -> bytes:
    """Génère un PDF récapitulatif complet pour un scénario donné."""
    from fpdf import FPDF
    from down_payment import compute_down_payment
    from cashflow import build_cashflow
    from study_20y import build_20y_study

    inp = build_inputs_from_store(data)

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 12, f"Scenario : {name}", ln=True)
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 6, "Analyse immobiliere - Recapitulatif", ln=True)
    pdf.ln(6)

    # --- 1. Paramètres ---
    _pdf_section(pdf, "Parametres d'entree")
    params = [
        ("Prix immobilier", fmt_money0(inp.prix_immobilier)),
        ("Prix marche", fmt_money0(inp.prix_marche)),
        ("Mise de fond", f"{inp.mise_de_fond_pct}%"),
        ("Duree hypotheque", f"{inp.duree_hypotheque_ans} ans"),
        ("Taux interet", f"{inp.taux_interet}%"),
        ("Loyer annuel total", fmt_money0(inp.loyer_annuel_total)),
        ("Taux vacance", f"{inp.taux_vacance}%"),
        ("Appreciation / an", f"{inp.appreciation_annuelle}%"),
        ("Frais condo / mois", fmt_money0(inp.frais_condo_mensuel)),
        ("Taxes mun. & scol. / mois", fmt_money0(inp.taxes_mun_scol_mensuel)),
        ("Nb investisseurs", str(inp.nombre_investisseurs)),
        ("Type", "Condo" if inp.est_condo else "Maison/Plex"),
    ]
    _pdf_key_value_table(pdf, params)

    # --- 2. Mise de fond ---
    dp = compute_down_payment(inp)
    _pdf_section(pdf, "Mise de fond")
    dp_rows = [
        ("Mise de fond", fmt_money0(dp.mise_de_fond)),
        ("Taxe bienvenue", fmt_money0(dp.taxe_bienvenue)),
        ("Notaire", fmt_money0(dp.notaire)),
        ("Inspection", fmt_money0(dp.inspection)),
        ("Assurance prime initiale", fmt_money0(dp.assurance_prime_initiale)),
        ("Frais", fmt_money0(dp.frais)),
        ("Autre / Travaux", fmt_money0(dp.autre_et_travaux)),
        ("Total charges initiales", fmt_money0(dp.total_charges_initiales)),
        ("Total depense a l'achat", fmt_money0(dp.total_depense_achat)),
    ]
    if inp.nombre_investisseurs > 1:
        dp_rows.append(("Total par personne",
                        fmt_money0(dp.total_depense_achat / inp.nombre_investisseurs)))
    _pdf_key_value_table(pdf, dp_rows)

    # --- 3. Cashflow année 1 et 5 ---
    cf_all = build_cashflow(inp)
    cf_by_year = {c.annee: c for c in cf_all}
    for yr in [1, 5]:
        cf = cf_by_year.get(yr)
        if not cf:
            continue
        _pdf_section(pdf, f"Cashflow - Annee {yr}")
        cf_rows = [
            ("Revenu locatif (mensuel)", fmt_money(cf.total_revenu / 12)),
            ("Revenu locatif (annuel)", fmt_money0(cf.total_revenu)),
            ("Hypotheque + assurance (mensuel)", fmt_money(cf.hypotheque_totale_mois1)),
            ("Capital (mensuel)", fmt_money(cf.capital_mois1)),
            ("Interet + assurance hyp. (mensuel)", fmt_money(cf.interet_assur_hypo_mois1)),
            ("Frais condo (mensuel)", fmt_money(cf.frais_condo_annuel / 12)),
            ("Taxes (mensuel)", fmt_money(cf.taxes_annuelles / 12)),
            ("Assurance habitation (mensuel)", fmt_money(cf.assurance_habitation_annuelle / 12)),
            ("Travaux (mensuel)", fmt_money(cf.travaux_annuel / 12)),
            ("Vacance locative (mensuel)", fmt_money(cf.vacance_annuelle / 12)),
            ("Total charges (mensuel)", fmt_money(cf.total_charges / 12)),
            ("Total charges (annuel)", fmt_money0(cf.total_charges)),
            ("Cashflow (mensuel)", fmt_money(cf.cashflow_mensuel)),
            ("Cashflow (annuel)", fmt_money0(cf.cashflow_annuel)),
            ("Cashflow / personne (mensuel)", fmt_money(cf.cashflow_par_personne_mensuel)),
            ("Cashflow / personne (annuel)", fmt_money0(cf.cashflow_par_personne_annuel)),
        ]
        _pdf_key_value_table(pdf, cf_rows)

    # --- 4. Étude pluriannuelle ---
    study_rows = build_20y_study(inp)
    if study_rows:
        _pdf_section(pdf, "Etude pluriannuelle")
        pdf.set_font("Helvetica", "B", 8)
        cols = ["Annee", "Cashflow cumul.", "Capital remb.", "Gain val. immo.",
                "Gain avant frais", "Gain global absolu", "Gain/an/pers."]
        col_w = (pdf.w - 20) / len(cols)
        for c in cols:
            pdf.cell(col_w, 6, c, border=1, align="C")
        pdf.ln()
        pdf.set_font("Helvetica", "", 8)
        for s in study_rows:
            vals = [
                str(s.annee),
                fmt_money0(s.cashflow_cumulatif),
                fmt_money0(s.capital_rembourse),
                fmt_money0(s.gain_valeur_immo),
                fmt_money0(s.gain_global_avant_frais),
                fmt_money0(s.gain_global_absolu),
                fmt_money0(s.gain_global_annuel_par_personne),
            ]
            for v in vals:
                pdf.cell(col_w, 5, v, border=1, align="R")
            pdf.ln()

    buf = io.BytesIO()
    pdf.output(buf)
    return buf.getvalue()


def _pdf_section(pdf, title: str):
    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_fill_color(240, 244, 248)
    pdf.cell(0, 8, f"  {title}", ln=True, fill=True)
    pdf.ln(2)


def _pdf_key_value_table(pdf, rows: list[tuple[str, str]]):
    pdf.set_font("Helvetica", "", 9)
    for label, value in rows:
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(90, 6, label, border=0)
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(70, 6, value, border=0, align="R")
        pdf.ln()
