"""Palette de couleurs, template Plotly et CSS de l'application."""

COLORS = {
    "primary":   "#2c6ecb",
    "secondary": "#6c757d",
    "success":   "#2fa86b",
    "warning":   "#f0ad4e",
    "danger":    "#d9534f",
    "info":      "#4aa3df",
    "light":     "#f7f9fc",
    "dark":      "#2c3e50",
    "accent1":   "#4a90e2",
    "accent2":   "#e2884a",
    "accent3":   "#43a047",
}

PLOT_TEMPLATE = "plotly_white"

INDEX_STRING = """
<!DOCTYPE html>
<html>
<head>
    {%metas%}<title>{%title%}</title>{%favicon%}{%css%}
    <style>
      body { background: linear-gradient(180deg, #eef3fb 0%, #f7f9fc 300px);
             font-family: Inter, 'Segoe UI', Arial, sans-serif; }
      .kpi-card { border: none; border-radius: 14px;
                  box-shadow: 0 4px 14px rgba(44,62,80,0.08); }
      .kpi-label { color: #6c757d; font-size: 0.82rem; text-transform: uppercase;
                   letter-spacing: 0.5px; }
      .kpi-value { font-size: 1.55rem; font-weight: 600; margin-top: 2px; }
      .section-card { border: none; border-radius: 14px;
                      box-shadow: 0 2px 10px rgba(44,62,80,0.06); }
      .section-card .card-header { background: #fff; border-bottom: 1px solid #eef1f5;
                                   font-weight: 600; color: #2c3e50;
                                   border-radius: 14px 14px 0 0 !important;}
      .nav-tabs .nav-link { color: #495057; font-weight: 500; border: none;
                            padding: 12px 18px; }
      .nav-tabs .nav-link.active { color: #2c6ecb; background: transparent;
                                   border-bottom: 3px solid #2c6ecb; }
      .form-label-row { color: #495057; font-size: 0.92rem; margin-bottom: 2px;}
      table { font-variant-numeric: tabular-nums; }
    </style>
</head>
<body>{%app_entry%}<footer>{%config%}{%scripts%}{%renderer%}</footer></body>
</html>
"""

