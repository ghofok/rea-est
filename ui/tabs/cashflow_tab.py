"""Onglets 3 & 4 — Cashflow détaillé (année 1 et année au choix)."""
from dash import dcc, html, Input, Output
import dash_bootstrap_components as dbc
import plotly.graph_objects as go

from inputs import PropertyInputs
from cashflow import detail_annee, build_cashflow
from theme import COLORS, PLOT_TEMPLATE
from components import _kpi, _section, _datatable
from state import build_inputs_from_store, fmt_money, fmt_money0


# --------------------------------------------------------------------- #
# Helpers internes
# --------------------------------------------------------------------- #
def _render_cashflow_detail(inp: PropertyInputs, annee: int):
    d = detail_annee(inp, annee)
    rows = []
    for section, lignes in d.items():
        rows.append({"Poste": f"▸ {section}", "Mensuel": "", "Annuel": ""})
        for lib, (mens, ann) in lignes.items():
            rows.append({"Poste": "   " + lib,
                         "Mensuel": fmt_money(mens),
                         "Annuel":  fmt_money(ann)})
    return _datatable(
        rows, [{"name": c, "id": c} for c in ["Poste", "Mensuel", "Annuel"]],
        style_cell_conditional=[
            {"if": {"column_id": "Poste"}, "textAlign": "left"},
            {"if": {"column_id": "Mensuel"}, "textAlign": "right"},
            {"if": {"column_id": "Annuel"},  "textAlign": "right"},
        ],
        style_data_conditional=[
            {"if": {"filter_query": '{Poste} contains "▸"'},
             "backgroundColor": "#eaf2ff", "color": "#2c6ecb",
             "fontWeight": "600", "textTransform": "uppercase",
             "fontSize": "0.82rem"},
            {"if": {"filter_query": '{Poste} contains "Total charges"'},
             "backgroundColor": "#f7f9fc", "fontWeight": "600"},
            {"if": {"filter_query": '{Poste} contains "Total revenu"'},
             "backgroundColor": "#f7f9fc", "fontWeight": "600"},
            {"if": {"filter_query": '{Poste} contains "Cashflow"'},
             "backgroundColor": "#fff4dc", "fontWeight": "600"},
        ],
    )


def _cashflow_kpis(inp: PropertyInputs, annee: int):
    cf = build_cashflow(inp)
    y = next(x for x in cf if x.annee == annee)
    cards = [
        ("Revenu annuel", fmt_money0(y.total_revenu),
         "bi-cash-stack", "success"),
        ("Charges annuelles", fmt_money0(y.total_charges),
         "bi-receipt", "warning"),
        ("Cashflow annuel", fmt_money0(y.cashflow_annuel),
         "bi-graph-up-arrow",
         "success" if y.cashflow_annuel >= 0 else "danger"),
        ("Cashflow mensuel / pers.",
         fmt_money0(y.cashflow_par_personne_mensuel),
         "bi-person-circle",
         "success" if y.cashflow_par_personne_mensuel >= 0 else "danger"),
    ]
    return [dbc.Col(_kpi(lab, val, ic, color), md=3)
            for lab, val, ic, color in cards]


def _cashflow_pie(inp: PropertyInputs, annee: int):
    cf = build_cashflow(inp)
    y = next(x for x in cf if x.annee == annee)
    labels = ["Capital hypo.", "Intérêt + assur. hypo.",
              "Frais de condo", "Taxes mun. & scol.",
              "Assurance habitation", "Travaux", "Vacance locative"]
    values = [y.capital_annuel, y.interet_assur_hypo_annuel,
              y.frais_condo_annuel, y.taxes_annuelles,
              y.assurance_habitation_annuelle, y.travaux_annuel,
              y.vacance_annuelle]
    keep = [(l, v) for l, v in zip(labels, values) if v and v > 0]
    if not keep:
        return go.Figure()
    labels, values = zip(*keep)
    fig = go.Figure(go.Pie(labels=list(labels), values=list(values), hole=0.55,
                           marker=dict(line=dict(color="#fff", width=2)),
                           textinfo="percent"))
    fig.update_layout(template=PLOT_TEMPLATE, height=340,
                      margin=dict(t=10, b=10, l=10, r=10),
                      legend=dict(orientation="v", y=0.5, x=1.02))
    return fig


# --------------------------------------------------------------------- #
# Onglet — Cashflow année 1
# --------------------------------------------------------------------- #
def render_y1():
    return html.Div([
        html.H4([html.I(className="bi bi-calendar-event me-2"),
                 "Cashflow détaillé — Année 1"], className="mb-3"),
        dbc.Row(id="cfy1-kpis", className="g-3 mb-4"),
        dbc.Row([
            dbc.Col(_section("Revenus & Charges",
                             html.Div(id="cashflow-y1-content"),
                             icon="bi-table"), lg=7),
            dbc.Col(_section("Répartition des charges",
                             dcc.Graph(id="cfy1-pie",
                                       config={"displayModeBar": False}),
                             icon="bi-pie-chart"), lg=5),
        ], className="g-3"),
    ], className="p-4")


# --------------------------------------------------------------------- #
# Onglet — Cashflow année X
# --------------------------------------------------------------------- #
def render_yX():
    return html.Div([
        html.H4([html.I(className="bi bi-calendar3 me-2"),
                 "Cashflow détaillé — année au choix"], className="mb-3"),
        dbc.Row([
            dbc.Col([
                html.Label("Année affichée", className="form-label-row"),
                dcc.Dropdown(id="cashflow-year-select",
                             options=[{"label": f"Année {a}", "value": a}
                                      for a in range(1, 26)],
                             value=5, clearable=False),
            ], md=3),
        ], className="mb-4"),
        dbc.Row(id="cfX-kpis", className="g-3 mb-4"),
        dbc.Row([
            dbc.Col(_section("Revenus & Charges",
                             html.Div(id="cashflow-yX-content"),
                             icon="bi-table"), lg=7),
            dbc.Col(_section("Évolution du cashflow annuel",
                             dcc.Graph(id="cfX-evolution",
                                       config={"displayModeBar": False}),
                             icon="bi-graph-up"), lg=5),
        ], className="g-3"),
    ], className="p-4")


# --------------------------------------------------------------------- #
# Callbacks
# --------------------------------------------------------------------- #
def register_callbacks(app):
    @app.callback(
        Output("cashflow-y1-content", "children"),
        Output("cfy1-kpis", "children"),
        Output("cfy1-pie", "figure"),
        Input("store-inputs", "data"),
    )
    def update_cfy1(store):
        inp = build_inputs_from_store(store)
        return (_render_cashflow_detail(inp, 1),
                _cashflow_kpis(inp, 1),
                _cashflow_pie(inp, 1))

    @app.callback(
        Output("cashflow-yX-content", "children"),
        Output("cfX-kpis", "children"),
        Output("cfX-evolution", "figure"),
        Output("cashflow-year-select", "options"),
        Input("store-inputs", "data"),
        Input("cashflow-year-select", "value"),
    )
    def update_cfyX(store, annee):
        inp = build_inputs_from_store(store)
        annee = max(1, min(int(annee or 1), inp.annees_analyse))
        opts = [{"label": f"Année {a}", "value": a}
                for a in range(1, inp.annees_analyse + 1)]
        cf = build_cashflow(inp)
        years = [y.annee for y in cf]
        cfs = [y.cashflow_annuel for y in cf]
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=years, y=cfs,
            marker_color=[COLORS["success"] if v >= 0 else COLORS["danger"]
                          for v in cfs]))
        fig.add_vline(x=annee, line_dash="dash", line_color=COLORS["primary"])
        fig.update_layout(template=PLOT_TEMPLATE, height=340,
                          margin=dict(t=20, b=30, l=40, r=20),
                          yaxis_title="$", xaxis_title="Année",
                          showlegend=False)
        return (_render_cashflow_detail(inp, annee),
                _cashflow_kpis(inp, annee), fig, opts)

