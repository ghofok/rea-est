"""Layout principal (navbar + tabs)."""
from dash import dcc, html
import dash_bootstrap_components as dbc

from state import default_store_dict
from tabs import (inputs_tab, down_payment_tab, cashflow_tab,
                  study_tab, amortization_tab, sensitivity_tab)


def build_layout():
    navbar = dbc.Navbar(
        dbc.Container([
            dbc.NavbarBrand([html.I(className="bi bi-building me-2"),
                             "Analyse immobilière"], className="fs-4"),
            html.Span("Tableau de bord interactif",
                      style={"color": "rgba(255,255,255,0.75)"}),
        ], fluid=True),
        color="primary", dark=True, className="shadow-sm",
    )

    return html.Div([
        navbar,
        dcc.Store(id="store-inputs", data=default_store_dict()),
        dbc.Container([
            dbc.Tabs(id="tabs", active_tab="tab-inputs", children=[
                dbc.Tab(inputs_tab.render(),         label="Paramètres",
                        tab_id="tab-inputs"),
                dbc.Tab(down_payment_tab.render(),   label="Mise de fond",
                        tab_id="tab-mise"),
                dbc.Tab(cashflow_tab.render_y1(),    label="Cashflow an 1",
                        tab_id="tab-cfy1"),
                dbc.Tab(cashflow_tab.render_yX(),    label="Cashflow an X",
                        tab_id="tab-cfX"),
                dbc.Tab(study_tab.render(),          label="Étude pluriannuelle",
                        tab_id="tab-study"),
                dbc.Tab(amortization_tab.render(),   label="Amortissement",
                        tab_id="tab-amort"),
                dbc.Tab(sensitivity_tab.render(),    label="Sensibilité",
                        tab_id="tab-sens"),
            ], className="mt-3"),
        ], fluid=True),
    ], style={"minHeight": "100vh"})

