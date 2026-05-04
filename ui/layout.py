"""Layout principal (navbar + sidebar scénarios + tabs)."""
from dash import dcc, html
import dash_bootstrap_components as dbc
from flask import session, has_request_context

from state import default_store_dict
from scenarios import default_scenarios_dict, render_sidebar
from user_store import load_scenarios
from i18n import t, get_lang
from admin import is_admin
from tabs import (inputs_tab, down_payment_tab, cashflow_tab,
                  study_tab, amortization_tab, sensitivity_tab)


def _initial_scenarios() -> dict:
    """Récupère les scénarios sauvegardés de l'utilisateur connecté ; sinon
    renvoie les valeurs par défaut."""
    if has_request_context():
        email = session.get("user")
        saved = load_scenarios(email)
        if saved:
            return saved
    return default_scenarios_dict()


def _initial_inputs(scn: dict) -> dict:
    """Le store-inputs reflète le scénario actif au chargement."""
    try:
        return dict(scn["scenarios"][scn["active"]])
    except Exception:
        return default_store_dict()


def build_layout():
    scn = _initial_scenarios()
    inputs0 = _initial_inputs(scn)
    lang = get_lang()
    current_email = session.get("user") if has_request_context() else None
    show_admin = is_admin(current_email)
    navbar = dbc.Navbar(
        dbc.Container([
            dbc.NavbarBrand([html.I(className="bi bi-building me-2"),
                             t("app_title")], className="fs-4"),
            html.Div([
                html.Span(t("dashboard_subtitle"),
                          style={"color": "rgba(255,255,255,0.75)"},
                          className="me-3"),
                # Sélecteur de langue
                dcc.Dropdown(
                    id="lang-select",
                    options=[{"label": "🇫🇷 " + t("french"), "value": "fr"},
                             {"label": "🇬🇧 " + t("english"), "value": "en"}],
                    value=lang, clearable=False, searchable=False,
                    style={"width": "150px",
                           "color": "#212529",
                           "marginRight": "1rem"},
                ),
                *([html.A([html.I(className="bi bi-shield-lock me-1"),
                           "Admin"],
                          href="/admin",
                          style={"color": "rgba(255,255,255,0.9)",
                                 "textDecoration": "none",
                                 "fontWeight": 500,
                                 "marginRight": "1rem"})]
                  if show_admin else []),
                html.A([html.I(className="bi bi-box-arrow-right me-1"),
                        t("logout")],
                       href="/logout",
                       style={"color": "rgba(255,255,255,0.9)",
                              "textDecoration": "none",
                              "fontWeight": 500}),
            ], className="d-flex align-items-center"),
        ], fluid=True),
        color="primary", dark=True, className="shadow-sm",
    )

    tabs = dbc.Tabs(id="tabs", active_tab="tab-inputs", children=[
        dbc.Tab(inputs_tab.render(),         label=t("tab_inputs"),
                tab_id="tab-inputs"),
        dbc.Tab(down_payment_tab.render(),   label=t("tab_downpayment"),
                tab_id="tab-mise"),
        dbc.Tab(cashflow_tab.render_y1(),    label=t("tab_cf_y1"),
                tab_id="tab-cfy1"),
        dbc.Tab(cashflow_tab.render_yX(),    label=t("tab_cf_yX"),
                tab_id="tab-cfX"),
        dbc.Tab(study_tab.render(),          label=t("tab_study"),
                tab_id="tab-study"),
        dbc.Tab(amortization_tab.render(),   label=t("tab_amort"),
                tab_id="tab-amort"),
        dbc.Tab(sensitivity_tab.render(),    label=t("tab_sens"),
                tab_id="tab-sens"),
    ], className="mt-3")

    return html.Div([
        navbar,
        dcc.Store(id="store-inputs",    data=inputs0),
        dcc.Store(id="store-scenarios", data=scn),
        dbc.Container([
            dbc.Row([
                dbc.Col(render_sidebar(), md=3, lg=2,
                        className="pt-3 pe-md-2"),
                dbc.Col(tabs, md=9, lg=10),
            ], className="g-2"),
        ], fluid=True),
    ], style={"minHeight": "100vh"})

