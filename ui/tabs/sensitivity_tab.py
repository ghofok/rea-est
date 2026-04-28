"""Onglet 7 — Sensibilité (taux d'intérêt OU mise de fond)."""
from dash import dcc, html, Input, Output
import dash_bootstrap_components as dbc
import plotly.graph_objects as go

from sensitivity import sensibilite_taux_interet, sensibilite_mise_de_fond
from theme import COLORS, PLOT_TEMPLATE
from components import _section, _datatable
from state import build_inputs_from_store, fmt_money


def render():
    return html.Div([
        html.H4([html.I(className="bi bi-activity me-2"),
                 "Analyse de sensibilité"], className="mb-3"),
        html.P("Variation du cashflow (mensuel & annuel) en fonction d'un "
               "paramètre choisi.", className="text-muted"),
        dbc.Row([
            dbc.Col([
                html.Label("Variable", className="form-label-row"),
                dcc.Dropdown(
                    id="sens-mode",
                    options=[
                        {"label": "Taux d'intérêt (%)", "value": "taux"},
                        {"label": "Mise de fond (%)",   "value": "mdf"},
                    ],
                    value="taux", clearable=False),
            ], md=3),
            dbc.Col([
                html.Label("± Delta (%)", className="form-label-row"),
                dbc.Input(id="sens-delta", type="number", value=0.5,
                          step=0.1, min=0.1, size="sm"),
            ], md=2, id="sens-col-delta"),
            dbc.Col([
                html.Label("Pas (%)", className="form-label-row"),
                dbc.Input(id="sens-pas", type="number", value=0.1,
                          step=0.05, min=0.01, size="sm"),
            ], md=2, id="sens-col-pas"),
            dbc.Col([
                html.Label("Valeurs MDF (%)", className="form-label-row"),
                dbc.Input(id="sens-mdf-values", type="text",
                          value="5, 10, 15, 20", size="sm"),
            ], md=4, id="sens-col-mdf"),
            dbc.Col([
                html.Label("Années affichées (séparées par virgules)",
                           className="form-label-row"),
                dbc.Input(id="sens-years", type="text", value="1",
                          size="sm"),
            ], md=4),
        ], className="g-3 mb-4"),
        dbc.Row([
            dbc.Col(_section("Cashflow mensuel",
                             dcc.Graph(id="sens-graph-m",
                                       config={"displayModeBar": False}),
                             icon="bi-graph-up"), lg=6),
            dbc.Col(_section("Cashflow annuel",
                             dcc.Graph(id="sens-graph-a",
                                       config={"displayModeBar": False}),
                             icon="bi-graph-up-arrow"), lg=6),
        ], className="g-3"),
        _section("Tableau des valeurs",
                 html.Div(id="sens-table"), icon="bi-table"),
    ], className="p-4")


def register_callbacks(app):
    @app.callback(
        Output("sens-col-delta", "style"),
        Output("sens-col-pas",   "style"),
        Output("sens-col-mdf",   "style"),
        Input("sens-mode", "value"),
    )
    def toggle_sens_inputs(mode):
        show, hide = {}, {"display": "none"}
        if mode == "mdf":
            return hide, hide, show
        return show, show, hide

    @app.callback(
        Output("sens-graph-m", "figure"),
        Output("sens-graph-a", "figure"),
        Output("sens-table", "children"),
        Input("store-inputs", "data"),
        Input("sens-mode", "value"),
        Input("sens-delta", "value"),
        Input("sens-pas", "value"),
        Input("sens-mdf-values", "value"),
        Input("sens-years", "value"),
    )
    def update_sensitivity(store, mode, delta, pas, mdf_values_str, years_str):
        inp = build_inputs_from_store(store)

        # Années
        try:
            annees = tuple(sorted({int(x.strip())
                                   for x in str(years_str).split(",")
                                   if x.strip()}))
            if not annees:
                annees = (1,)
        except Exception:
            annees = (1, 5)
        annees = tuple(a for a in annees
                       if 1 <= a <= inp.annees_analyse) or (1,)

        palette = [COLORS["primary"], COLORS["accent3"], COLORS["accent2"],
                   COLORS["danger"], COLORS["info"]]

        # Génération des points selon le mode
        if mode == "mdf":
            try:
                valeurs = tuple(sorted({float(x.strip())
                                        for x in str(mdf_values_str).split(",")
                                        if x.strip()}))
                if not valeurs:
                    valeurs = (5, 10, 15, 20)
            except Exception:
                valeurs = (5, 10, 15, 20)
            points = sensibilite_mise_de_fond(inp, valeurs_pct=valeurs,
                                              annees=annees)
            # Base fixée à 10 %
            base_value = 10.0
            x_label = "Mise de fond (%)"
            var_col_name = "MDF (%)"
        else:
            try:
                delta = float(delta or 0.5)
                pas = float(pas or 0.1)
                if pas <= 0 or delta <= 0:
                    raise ValueError
            except Exception:
                delta, pas = 0.5, 0.1
            points = sensibilite_taux_interet(inp, delta_pct=delta,
                                              pas_pct=pas, annees=annees)
            base_value = inp.taux_interet
            x_label = "Taux d'intérêt (%)"
            var_col_name = "Taux (%)"

        xs = [p["taux"] for p in points]
        base_idx = min(range(len(points)),
                       key=lambda i: abs(points[i]["taux"] - base_value))
        base_point = points[base_idx]

        def _fmt_delta(v: float) -> str:
            sign = "+" if v > 0 else ("" if v == 0 else "−")
            return f"{sign}{abs(v):,.0f}".replace(",", " ") + " $"

        def _mk_fig(key_prefix: str, ylabel: str):
            fig = go.Figure()
            for i, a in enumerate(annees):
                col = palette[i % len(palette)]
                ys = [p[f"{key_prefix}{a}"] for p in points]
                base_val = base_point[f"{key_prefix}{a}"]
                deltas = [y - base_val for y in ys]
                labels = []
                for y, d in zip(ys, deltas):
                    val_str = f"{y:,.0f}".replace(",", " ")
                    if abs(d) < 1e-9:
                        labels.append(val_str)
                    else:
                        labels.append(f"{val_str}<br>({_fmt_delta(d)})")
                fig.add_trace(go.Scatter(
                    x=xs, y=ys, mode="lines+markers+text",
                    name=f"Année {a}",
                    line=dict(color=col, width=2.5),
                    marker=dict(size=8),
                    text=labels,
                    textposition="top center",
                    textfont=dict(size=10, color=col),
                    hovertemplate=(f"{x_label} %{{x:.2f}}<br>"
                                   "Valeur : %{y:,.0f} $<br>"
                                   "Δ vs base : %{customdata:+,.0f} $"
                                   "<extra></extra>"),
                    customdata=deltas,
                ))
            fig.add_vline(x=base_value, line_dash="dash",
                          line_color=COLORS["danger"],
                          annotation_text=f"Base {base_value:.2f}",
                          annotation_position="top")
            fig.add_hline(y=0, line_color="#bbb", line_width=1)
            fig.update_layout(template=PLOT_TEMPLATE, height=420,
                              margin=dict(t=40, b=40, l=55, r=20),
                              xaxis_title=x_label, yaxis_title=ylabel,
                              legend=dict(orientation="h", y=-0.22))
            return fig

        fig_m = _mk_fig("m", "Cashflow mensuel ($)")
        fig_a = _mk_fig("a", "Cashflow annuel ($)")

        # Tableau
        cols = [{"name": var_col_name, "id": "taux"}]
        for a in annees:
            cols.append({"name": f"CF mensuel A{a}", "id": f"m{a}"})
            cols.append({"name": f"Δ mensuel A{a}",  "id": f"dm{a}"})
            cols.append({"name": f"CF annuel A{a}",  "id": f"a{a}"})
            cols.append({"name": f"Δ annuel A{a}",   "id": f"da{a}"})
        rows = []
        for p in points:
            is_base = abs(p["taux"] - base_value) < 1e-9
            row = {"taux": f"{p['taux']:.2f}"
                          + ("  ← base" if is_base else "")}
            for a in annees:
                m_val = p[f"m{a}"]; a_val = p[f"a{a}"]
                dm = m_val - base_point[f"m{a}"]
                da = a_val - base_point[f"a{a}"]
                row[f"m{a}"]  = fmt_money(m_val)
                row[f"dm{a}"] = "—" if is_base else _fmt_delta(dm)
                row[f"a{a}"]  = fmt_money(a_val)
                row[f"da{a}"] = "—" if is_base else _fmt_delta(da)
            rows.append(row)

        delta_col_ids = [f"dm{a}" for a in annees] + [f"da{a}" for a in annees]
        delta_color_rules = []
        for cid in delta_col_ids:
            delta_color_rules += [
                {"if": {"filter_query": f'{{{cid}}} contains "+"',
                        "column_id": cid},
                 "color": COLORS["success"], "fontWeight": "600"},
                {"if": {"filter_query": f'{{{cid}}} contains "−"',
                        "column_id": cid},
                 "color": COLORS["danger"], "fontWeight": "600"},
            ]

        table = _datatable(
            rows, cols,
            style_cell_conditional=[{"if": {"column_id": "taux"},
                                     "textAlign": "center",
                                     "fontWeight": "600"}]
            + [{"if": {"column_id": c["id"]}, "textAlign": "right"}
               for c in cols[1:]],
            style_data_conditional=[
                {"if": {"filter_query": '{taux} contains "base"'},
                 "backgroundColor": "#fff4dc", "fontWeight": "600"},
            ] + delta_color_rules,
        )
        return fig_m, fig_a, table

