"""Onglet 2 — Mise de fond & charges initiales."""
from dash import dcc, html, Input, Output
import dash_bootstrap_components as dbc
import plotly.graph_objects as go

from down_payment import compute_down_payment
from theme import PLOT_TEMPLATE
from components import _kpi_col, _section, _datatable
from state import build_inputs_from_store, fmt_money, fmt_money0


def render():
    return html.Div([
        html.H4([html.I(className="bi bi-wallet2 me-2"),
                 "Mise de fond & charges initiales"], className="mb-3"),
        dbc.Row([
            _kpi_col("Mise de fond",     "kpi-mf",      "bi-piggy-bank", "primary"),
            _kpi_col("Charges initiales","kpi-charges", "bi-receipt",    "warning"),
            _kpi_col("Dépense totale",   "kpi-total",   "bi-cash-coin",  "danger"),
            _kpi_col("Par personne",     "kpi-pp",      "bi-people",     "info"),
        ], className="g-3 mb-4"),
        dbc.Row([
            dbc.Col(_section("Détail", html.Div(id="mise-fond-table"),
                             icon="bi-list-ul"), lg=7),
            dbc.Col(_section("Répartition des charges initiales",
                             dcc.Graph(id="mise-fond-pie",
                                       config={"displayModeBar": False}),
                             icon="bi-pie-chart"), lg=5),
        ], className="g-3"),
    ], className="p-4")


def register_callbacks(app):
    @app.callback(
        Output("mise-fond-table", "children"),
        Output("mise-fond-pie", "figure"),
        Output("kpi-mf", "children"),
        Output("kpi-charges", "children"),
        Output("kpi-total", "children"),
        Output("kpi-pp", "children"),
        Input("store-inputs", "data"),
    )
    def update_mise_fond(store):
        inp = build_inputs_from_store(store)
        dp = compute_down_payment(inp)

        rows = [{"Élément": lib, "Total": fmt_money(total),
                 "Par personne": fmt_money(pp)}
                for lib, total, pp in dp.to_table()]
        table = _datatable(
            rows,
            [{"name": c, "id": c} for c in ["Élément", "Total", "Par personne"]],
            style_cell_conditional=[
                {"if": {"column_id": "Élément"}, "textAlign": "left"},
                {"if": {"column_id": "Total"}, "textAlign": "right"},
                {"if": {"column_id": "Par personne"}, "textAlign": "right"},
            ],
            style_data_conditional=[
                {"if": {"filter_query": '{Élément} contains "Total"'},
                 "backgroundColor": "#eef6ff", "fontWeight": "600"},
            ],
        )

        labels, values = [], []
        for lib, tot, _ in dp.to_table():
            if lib in ("Mise de fond", "Total Mise de Fond",
                       "Total charges initiales", "Total dépense à l'achat"):
                continue
            if tot and tot > 0:
                labels.append(lib); values.append(tot)
        fig = go.Figure(go.Pie(labels=labels, values=values, hole=0.55,
                               marker=dict(line=dict(color="#fff", width=2)),
                               textinfo="percent"))
        fig.update_layout(template=PLOT_TEMPLATE, height=340,
                          margin=dict(t=10, b=10, l=10, r=10),
                          legend=dict(orientation="v", y=0.5, x=1.02))

        return (table, fig,
                fmt_money0(dp.mise_de_fond),
                fmt_money0(dp.total_charges_initiales),
                fmt_money0(dp.total_depense_achat),
                fmt_money0(dp.par_personne(dp.total_depense_achat)))

