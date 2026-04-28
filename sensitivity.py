"""
Analyse de sensibilité : variation du cashflow annuel de l'année 1
en fonction du taux d'intérêt hypothécaire (±0,5 % autour du taux de base,
par pas de 0,1 %).
"""
from dataclasses import replace
from typing import List, Tuple
from inputs import PropertyInputs
from cashflow import build_cashflow


def sensibilite_taux_interet(
    inp: PropertyInputs,
    delta_pct: float = 0.5,
    pas_pct: float = 0.1,
    annees: Tuple[int, ...] = (1, 5),
) -> List[dict]:
    """Retourne, pour chaque taux balayé, un dict contenant le cashflow
    annuel et mensuel des années demandées.
    Ex. {"taux": 3.2, "a1": -24285, "m1": -2024, "a5": ..., "m5": ...}
    """
    base = inp.taux_interet
    n_steps = int(round(delta_pct / pas_pct))
    taux_list = [round(base + i * pas_pct, 4)
                 for i in range(-n_steps, n_steps + 1)]

    points: List[dict] = []
    for taux in taux_list:
        inp2 = replace(inp, taux_interet=taux)
        cf = build_cashflow(inp2)
        by_year = {y.annee: y for y in cf}
        entry = {"taux": taux}
        for a in annees:
            y = by_year.get(a)
            entry[f"a{a}"] = y.cashflow_annuel if y else 0.0
            entry[f"m{a}"] = y.cashflow_mensuel if y else 0.0
        points.append(entry)
    return points


def sensibilite_mise_de_fond(
    inp: PropertyInputs,
    valeurs_pct: Tuple[float, ...] = (5, 10, 15, 20),
    annees: Tuple[int, ...] = (1, 5),
) -> List[dict]:
    """Retourne, pour chaque pourcentage de mise de fond, un dict contenant
    le cashflow annuel et mensuel des années demandées.
    La clé "taux" contient ici la valeur de mise de fond (%) — conservée
    pour rester compatible avec l'affichage générique.
    """
    points: List[dict] = []
    for pct in valeurs_pct:
        inp2 = replace(inp, mise_de_fond_pct=float(pct))
        cf = build_cashflow(inp2)
        by_year = {y.annee: y for y in cf}
        entry = {"taux": float(pct)}
        for a in annees:
            y = by_year.get(a)
            entry[f"a{a}"] = y.cashflow_annuel if y else 0.0
            entry[f"m{a}"] = y.cashflow_mensuel if y else 0.0
        points.append(entry)
    return points


def plot_sensibilite(inp: PropertyInputs,
                     delta_pct: float = 0.5,
                     pas_pct: float = 0.1,
                     annees: Tuple[int, ...] = (1, 5),
                     save_path: str | None = None) -> None:
    """Affiche (ou enregistre) un graphique du cashflow annuel et mensuel
    en fonction du taux d'intérêt, pour les années sélectionnées."""
    points = sensibilite_taux_interet(inp, delta_pct, pas_pct, annees)
    taux = [p["taux"] for p in points]

    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("\n" + "=" * 70)
        print("SENSIBILITÉ DU CASHFLOW AU TAUX D'INTÉRÊT")
        print("(matplotlib non installé — affichage texte)")
        print("=" * 70)
        head = f"  {'Taux (%)':>10}"
        for a in annees:
            head += f"{'CF an. A'+str(a):>15}{'CF mens. A'+str(a):>17}"
        print(head)
        for p in points:
            line = f"  {p['taux']:>10.2f}"
            for a in annees:
                line += f"{p[f'a{a}']:>15,.0f}{p[f'm{a}']:>17,.0f}"
            if abs(p["taux"] - inp.taux_interet) < 1e-9:
                line += "  <-- base"
            print(line)
        return

    fig, (ax_a, ax_m) = plt.subplots(1, 2, figsize=(14, 5.5))
    couleurs = ["#1f77b4", "#2ca02c", "#9467bd", "#d62728"]

    for i, a in enumerate(annees):
        col = couleurs[i % len(couleurs)]
        cf_a = [p[f"a{a}"] for p in points]
        cf_m = [p[f"m{a}"] for p in points]
        ax_a.plot(taux, cf_a, marker="o", linewidth=2, color=col,
                  label=f"Année {a}")
        ax_m.plot(taux, cf_m, marker="s", linewidth=2, color=col,
                  label=f"Année {a}")
        # annotations
        for t, va, vm in zip(taux, cf_a, cf_m):
            ax_a.annotate(f"{va:,.0f}".replace(",", " "),
                          xy=(t, va), xytext=(0, 8),
                          textcoords="offset points",
                          ha="center", fontsize=7, color=col)
            ax_m.annotate(f"{vm:,.0f}".replace(",", " "),
                          xy=(t, vm), xytext=(0, 8),
                          textcoords="offset points",
                          ha="center", fontsize=7, color=col)

    for ax, titre, ylab in [
        (ax_a, "Cashflow ANNUEL selon le taux", "Cashflow annuel ($)"),
        (ax_m, "Cashflow MENSUEL selon le taux", "Cashflow mensuel ($)"),
    ]:
        ax.axvline(inp.taux_interet, color="red", linestyle="--", alpha=0.4,
                   label=f"Taux base : {inp.taux_interet:.2f} %")
        ax.axhline(0, color="gray", linestyle=":", alpha=0.5)
        ax.set_title(titre)
        ax.set_xlabel("Taux d'intérêt hypothécaire (%)")
        ax.set_ylabel(ylab)
        ax.grid(True, alpha=0.3)
        ax.legend(loc="best")

    fig.suptitle("Sensibilité du cashflow au taux d'intérêt", fontsize=12)
    fig.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=120)
        print(f"\nGraphique enregistré : {save_path}")
    plt.show()

