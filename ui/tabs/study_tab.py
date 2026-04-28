"""Onglet 5 — Étude pluriannuelle (jalons configurables)."""
from dash import dcc, html, Input, Output
import dash_bootstrap_components as dbc
import plotly.graph_objects as go

from study_20y import build_20y_study, to_table
from theme import COLORS, PLOT_TEMPLATE
from components import _kpi, _section, _datatable
from state import build_inputs_from_store, fmt_money, fmt_money0


def render():
    return html.Div([
        html.H4([html.I(className="bi bi-graph-up-arrow me-2"),
                 "Étude pluriannuelle"], className="mb-3"),
        html.P("Les jalons sont configurables dans l'onglet Paramètres.",
               className="text-muted"),
        dbc.Row(id="study-kpis", className="g-3 mb-4"),
        _section("Tableau par jalon", html.Div(id="study-content"),
                 icon="bi-table"),
        _section("Visualisations",
                 dcc.Graph(id="study-chart",
                           config={"displayModeBar": False}),
                 icon="bi-bar-chart-line"),
    ], className="p-4")


def register_callbacks(app):
    @app.callback(
        Output("study-content", "children"),
        Output("study-chart", "figure"),
        Output("study-kpis", "children"),
        Input("store-inputs", "data"),
    )
    def update_study(store):
        inp = build_inputs_from_store(store)
        results = build_20y_study(inp)
        rows_data = to_table(results)
        jalons = [r.annee for r in results]

        columns = [{"name": "Élément", "id": "lib"}] + \
                  [{"name": f"{j} an" + ("s" if j > 1 else ""), "id": f"j{j}"}
                   for j in jalons]
        table_rows = []
        for libelle, values in rows_data:
            row = {"lib": libelle}
            for j, v in zip(jalons, values):
                row[f"j{j}"] = (f"{int(v)}" if libelle == "Années"
                                else fmt_money(v))
            table_rows.append(row)

        table = _datatable(
            table_rows, columns,
            style_cell_conditional=[
                {"if": {"column_id": "lib"}, "textAlign": "left",
                 "minWidth": "300px", "fontWeight": "500"},
            ] + [{"if": {"column_id": f"j{j}"}, "textAlign": "right"}
                 for j in jalons],
            style_data_conditional=[
                {"if": {"filter_query": '{lib} contains "Gain global absolu"'},
                 "backgroundColor": "#fff4dc", "fontWeight": "600"},
                {"if": {"filter_query": '{lib} contains "Valeur du bien"'},
                 "backgroundColor": "#eaf7ea", "fontWeight": "600"},
                {"if": {"filter_query": '{lib} contains "Total"'},
                 "backgroundColor": "#f7f9fc"},
                {"if": {"filter_query": '{lib} contains "Impôts totaux"'},
                 "backgroundColor": "#fde9e9"},
            ],
        )

        x = [f"{r.annee} an" + ("s" if r.annee > 1 else "") for r in results]
        fig = go.Figure()
        fig.add_trace(go.Bar(name="Cashflow cumulatif", x=x,
                             y=[r.cashflow_cumulatif for r in results],
                             marker_color=COLORS["accent1"]))
        fig.add_trace(go.Bar(name="Capital remboursé", x=x,
                             y=[r.capital_rembourse for r in results],
                             marker_color=COLORS["accent3"]))
        fig.add_trace(go.Bar(name="Gain de valeur immo.", x=x,
                             y=[r.gain_valeur_immo for r in results],
                             marker_color=COLORS["accent2"]))
        fig.add_trace(go.Scatter(name="Gain global absolu", x=x,
                                 y=[r.gain_global_absolu for r in results],
                                 mode="lines+markers",
                                 line=dict(color=COLORS["danger"], width=3)))
        fig.update_layout(template=PLOT_TEMPLATE, barmode="group", height=420,
                          margin=dict(t=30, b=40, l=50, r=20),
                          yaxis_title="$",
                          legend=dict(orientation="h", y=-0.2))

        last = results[-1]
        kpis = [
            ("Dernier jalon", f"{last.annee} ans", "bi-flag", "primary"),
            ("Valeur du bien",
             fmt_money0(last.valeur_bien_vente), "bi-house-check", "success"),
            ("Gain global absolu",
             fmt_money0(last.gain_global_absolu), "bi-trophy",
             "success" if last.gain_global_absolu >= 0 else "danger"),
            ("Gain / an / pers. (après impôt)",
             fmt_money0(last.gain_global_annuel_pp_apres_impot),
             "bi-person-check",
             "success" if last.gain_global_annuel_pp_apres_impot >= 0 else "danger"),
        ]
        kpi_cols = [dbc.Col(_kpi(lab, val, ic, color), md=3)
                    for lab, val, ic, color in kpis]
        return table, fig, kpi_cols

