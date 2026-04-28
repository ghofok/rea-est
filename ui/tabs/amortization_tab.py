"""Onglet 6 — Tableau d'amortissement (mensuel / annuel + graphique)."""
from dash import dcc, html, Input, Output
import dash_bootstrap_components as dbc
import plotly.graph_objects as go

from mortgage import build_amortization
from theme import COLORS, PLOT_TEMPLATE
from components import _kpi, _datatable
from state import build_inputs_from_store, fmt_money, fmt_money0


def render():
    return html.Div([
        html.H4([html.I(className="bi bi-bank me-2"),
                 "Tableau d'amortissement"], className="mb-3"),
        dbc.Row(id="amort-kpis", className="g-3 mb-4"),
        dbc.Tabs([
            dbc.Tab(html.Div(id="amort-monthly", className="pt-3"),
                    label="Mensuel"),
            dbc.Tab(html.Div(id="amort-yearly", className="pt-3"),
                    label="Annuel"),
            dbc.Tab(dcc.Graph(id="amort-graph",
                              config={"displayModeBar": False}),
                    label="Graphique"),
        ]),
    ], className="p-4")


def register_callbacks(app):
    @app.callback(
        Output("amort-monthly", "children"),
        Output("amort-yearly", "children"),
        Output("amort-graph", "figure"),
        Output("amort-kpis", "children"),
        Input("store-inputs", "data"),
    )
    def update_amort(store):
        inp = build_inputs_from_store(store)
        rows = build_amortization(inp)

        # Tableau mensuel
        data = [{
            "Année": r.annee, "Mois": r.mois,
            "Paiement hypo.": fmt_money(r.paiement_hypo),
            "Pmt + assur.": fmt_money(r.paiement_hypo_assur),
            "Capital": fmt_money(r.capital),
            "Intérêt": fmt_money(r.interet),
            "Frais & Taxes": fmt_money(r.frais_taxes),
            "Total mensuel": fmt_money(r.total_paiement_mensuel),
            "Capital cumul": fmt_money(r.capital_cumul),
            "Intérêt cumul": fmt_money(r.interet_cumul),
            "Capital restant": fmt_money(r.capital_restant),
        } for r in rows]
        cols = list(data[0].keys()) if data else []
        monthly = _datatable(
            data, [{"name": c, "id": c} for c in cols], page_size=24,
            style_cell_conditional=[
                {"if": {"column_id": "Année"}, "textAlign": "center"},
                {"if": {"column_id": "Mois"},  "textAlign": "center"},
            ] + [{"if": {"column_id": c}, "textAlign": "right"} for c in cols
                 if c not in ("Année", "Mois")],
        )

        # Résumé annuel
        by_year = {}
        for r in rows:
            d = by_year.setdefault(r.annee, {"capital": 0, "interet": 0,
                                             "frais": 0,
                                             "reste": r.capital_restant})
            d["capital"] += r.capital
            d["interet"] += r.interet
            d["frais"] += r.frais_taxes
            d["reste"] = r.capital_restant
        yearly_rows = [{"Année": a,
                        "Capital remboursé": fmt_money(v["capital"]),
                        "Intérêt payé": fmt_money(v["interet"]),
                        "Frais / Taxes": fmt_money(v["frais"]),
                        "Capital restant": fmt_money(v["reste"])}
                       for a, v in by_year.items()]
        yearly = _datatable(
            yearly_rows,
            [{"name": c, "id": c} for c in
             ["Année", "Capital remboursé", "Intérêt payé",
              "Frais / Taxes", "Capital restant"]],
            page_size=30,
            style_cell_conditional=[
                {"if": {"column_id": "Année"}, "textAlign": "center"},
            ] + [{"if": {"column_id": c}, "textAlign": "right"} for c in
                 ["Capital remboursé", "Intérêt payé",
                  "Frais / Taxes", "Capital restant"]],
        )

        # Graphique
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=[r.annee + r.mois / 12 for r in rows],
            y=[r.capital_restant for r in rows],
            mode="lines", name="Capital restant",
            line=dict(color=COLORS["accent1"], width=2.5),
            fill="tozeroy", fillcolor="rgba(74,144,226,0.10)"))
        fig.add_trace(go.Scatter(
            x=[r.annee + r.mois / 12 for r in rows],
            y=[r.capital_cumul for r in rows],
            mode="lines", name="Capital remboursé cumulé",
            line=dict(color=COLORS["accent3"], width=2.5)))
        fig.add_trace(go.Scatter(
            x=[r.annee + r.mois / 12 for r in rows],
            y=[r.interet_cumul for r in rows],
            mode="lines", name="Intérêt payé cumulé",
            line=dict(color=COLORS["accent2"], width=2.5, dash="dash")))
        fig.update_layout(template=PLOT_TEMPLATE, height=460,
                          margin=dict(t=30, b=40, l=50, r=20),
                          xaxis_title="Années", yaxis_title="$",
                          legend=dict(orientation="h", y=-0.18))

        # KPIs
        pmt = rows[0].paiement_hypo if rows else 0
        total_int = sum(r.interet for r in rows)
        total_cap = sum(r.capital for r in rows)
        kpis = [
            ("Paiement mensuel", fmt_money0(pmt), "bi-cash", "primary"),
            ("Montant emprunté", fmt_money0(inp.montant_hypotheque),
             "bi-bank2", "info"),
            ("Intérêts totaux", fmt_money0(total_int),
             "bi-percent", "warning"),
            ("Capital total remboursé", fmt_money0(total_cap),
             "bi-check2-circle", "success"),
        ]
        kpi_cols = [dbc.Col(_kpi(lab, val, ic, color), md=3)
                    for lab, val, ic, color in kpis]
        return monthly, yearly, fig, kpi_cols

