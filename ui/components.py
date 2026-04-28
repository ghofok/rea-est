"""Composants visuels réutilisables (KPI cards, sections, DataTable stylé)."""
from dash import dash_table, html
import dash_bootstrap_components as dbc

from theme import COLORS


def _kpi(label, value, icon: str = "bi-cash-stack", color: str = "primary"):
    """Carte KPI à valeur statique."""
    return dbc.Card(dbc.CardBody([
        html.Div([
            html.I(className=f"bi {icon} me-2",
                   style={"fontSize": "1.35rem", "color": COLORS[color]}),
            html.Span(label, className="kpi-label"),
        ]),
        html.Div(value, className="kpi-value",
                 style={"color": COLORS[color]}),
    ]), className="kpi-card h-100")


def _kpi_col(label: str, value_id: str,
             icon: str = "bi-cash-stack", color: str = "primary"):
    """Carte KPI avec valeur dynamique (rendue par callback via id)."""
    return dbc.Col(dbc.Card(dbc.CardBody([
        html.Div([
            html.I(className=f"bi {icon} me-2",
                   style={"fontSize": "1.35rem", "color": COLORS[color]}),
            html.Span(label, className="kpi-label"),
        ]),
        html.Div(id=value_id, className="kpi-value",
                 style={"color": COLORS[color]}),
    ]), className="kpi-card h-100"), md=3)


def _section(title: str, body, icon: str = "bi-bar-chart"):
    """Carte titrée pour regrouper un bloc de contenu."""
    return dbc.Card([
        dbc.CardHeader([html.I(className=f"bi {icon} me-2",
                               style={"color": COLORS["primary"]}), title]),
        dbc.CardBody(body),
    ], className="section-card mb-4")


def _datatable(data, columns, **kwargs):
    """DataTable Dash avec un style cohérent par défaut."""
    defaults = dict(
        style_cell={"padding": "8px 10px", "fontSize": "0.92rem",
                    "border": "none", "borderBottom": "1px solid #eef1f5"},
        style_header={"backgroundColor": "#f7f9fc", "fontWeight": "600",
                      "color": "#2c3e50", "border": "none",
                      "borderBottom": "2px solid #e2e6ec",
                      "textTransform": "uppercase",
                      "fontSize": "0.76rem", "letterSpacing": "0.4px"},
        style_data={"backgroundColor": "#ffffff"},
        style_as_list_view=True,
    )
    defaults.update(kwargs)
    return dash_table.DataTable(data=data, columns=columns, **defaults)

