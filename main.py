"""
Point d'entrée : assemble les entrées, calcule la mise de fond,
l'amortissement hypothécaire et affiche les résultats.
"""
from inputs import PropertyInputs
from down_payment import compute_down_payment
from mortgage import build_amortization
from cashflow import build_cashflow, detail_annee
from study_20y import build_20y_study, to_table
from sensitivity import plot_sensibilite


def fmt_money(x: float) -> str:
    return f"{x:,.2f} $".replace(",", " ").replace(".", ",")


def print_inputs(inp: PropertyInputs) -> None:
    print("=" * 70)
    print("ENTRÉES")
    print("=" * 70)
    lignes = [
        ("Prix immobilier",                    fmt_money(inp.prix_immobilier)),
        ("Prix marché",                        fmt_money(inp.prix_marche)),
        ("Mise de fond (%)",                   f"{inp.mise_de_fond_pct:.2f} %"),
        ("Durée hypothèque (ans)",             inp.duree_hypotheque_ans),
        ("Taux d'intérêt",                     f"{inp.taux_interet:.2f} %"),
        ("Assurance hypothèque mensuelle",     fmt_money(inp.assurance_hypotheque_mensuelle)),
        ("Taux de vacance locative",           f"{inp.taux_vacance:.2f} %"),
        ("Appréciation immobilière / an",      f"{inp.appreciation_annuelle:.2f} %"),
        ("Frais de condo / mois",              fmt_money(inp.frais_condo_mensuel)),
        ("Taxes municipales & scolaires / mois", fmt_money(inp.taxes_mun_scol_mensuel)),
        ("Loyer annuel total",                 fmt_money(inp.loyer_annuel_total)),
        ("Nombre investisseurs",               inp.nombre_investisseurs),
    ]
    for lib, val in lignes:
        print(f"  {lib:<42} {val}")


def print_down_payment(inp: PropertyInputs) -> None:
    dp = compute_down_payment(inp)
    print("\n" + "=" * 70)
    print("MISE DE FOND & CHARGES INITIALES")
    print("=" * 70)
    print(f"  {'Élément':<32}{'Total':>18}{'Par personne':>18}")
    print("  " + "-" * 68)
    for lib, total, par_pers in dp.to_table():
        print(f"  {lib:<32}{fmt_money(total):>18}{fmt_money(par_pers):>18}")


def print_amortization(inp: PropertyInputs, max_rows: int = 24) -> None:
    rows = build_amortization(inp)
    print("\n" + "=" * 70)
    print(f"TABLEAU D'AMORTISSEMENT (premiers {max_rows} mois sur {len(rows)})")
    print("=" * 70)
    header = ("An", "Mo", "Pmt", "Pmt+Ass", "Capital", "Intérêt",
              "Frais/Tx", "Total", "Non-Inv", "Cap.cum", "Int.cum", "Cap.rest")
    print(("{:>3}{:>3}" + "{:>11}" * 10).format(*header))
    for r in rows[:max_rows]:
        print(("{:>3}{:>3}" + "{:>11.2f}" * 10).format(
            r.annee, r.mois,
            r.paiement_hypo, r.paiement_hypo_assur,
            r.capital, r.interet, r.frais_taxes,
            r.total_paiement_mensuel, r.total_non_investie,
            r.capital_cumul, r.interet_cumul, r.capital_restant,
        ))

    print("\n  Résumé annuel :")
    print("  {:>4}{:>14}{:>14}{:>14}{:>14}".format(
        "An", "Capital", "Intérêt", "Frais/Tx", "Cap.restant"))
    for annee in range(1, inp.duree_hypotheque_ans + 1):
        annee_rows = [r for r in rows if r.annee == annee]
        cap = sum(r.capital for r in annee_rows)
        intr = sum(r.interet for r in annee_rows)
        ft = sum(r.frais_taxes for r in annee_rows)
        reste = annee_rows[-1].capital_restant
        print(f"  {annee:>4}{cap:>14.2f}{intr:>14.2f}{ft:>14.2f}{reste:>14.2f}")


def print_cashflow_detail(inp: PropertyInputs, annee: int = 1) -> None:
    d = detail_annee(inp, annee)
    print("\n" + "=" * 70)
    print(f"CASHFLOW DÉTAILLÉ - ANNÉE {annee}")
    print("=" * 70)
    print(f"  {'Poste':<42}{'Mensuel':>12}{'Annuel':>14}")
    print("  " + "-" * 68)
    for section, lignes in d.items():
        print(f"  [{section}]")
        for lib, (mens, ann) in lignes.items():
            print(f"  {lib:<42}{fmt_money(mens):>12}{fmt_money(ann):>14}")


def print_cashflow_summary(inp: PropertyInputs) -> None:
    cf = build_cashflow(inp)
    print("\n" + "=" * 70)
    print(f"CASHFLOW ANNUEL - ANNÉES 1 à {inp.annees_analyse}")
    print("=" * 70)
    header = ("An", "Revenu", "Hypo tot.", "Exploit.", "Charges",
              "Cashflow", "CF/pers", "Gain imp.", "Cap.rembs")
    print(("{:>3}" + "{:>12}" * 8).format(*header))
    for y in cf:
        print(("{:>3}" + "{:>12.0f}" * 8).format(
            y.annee,
            y.total_revenu,
            y.hypotheque_totale_annuelle,
            y.total_exploitation,
            y.total_charges,
            y.cashflow_annuel,
            y.cashflow_par_personne_annuel,
            y.gain_imposable_annuel,
            y.capital_annuel,
        ))
    # Totaux cumulés
    tot_cf = sum(y.cashflow_annuel for y in cf)
    tot_gain = sum(y.gain_imposable_annuel for y in cf)
    tot_cap = sum(y.capital_annuel for y in cf)
    print("  " + "-" * 68)
    print(f"  Cumul cashflow        : {fmt_money(tot_cf)}")
    print(f"  Cumul gain imposable  : {fmt_money(tot_gain)}")
    print(f"  Cumul capital remboursé: {fmt_money(tot_cap)}")


def print_20y_study(inp: PropertyInputs) -> None:
    results = build_20y_study(inp)
    rows = to_table(results)
    col_w = 15
    print("\n" + "=" * 70)
    print(f"ÉTUDE PLURIANNUELLE - JALONS {list(inp.jalons_etude)} ANS")
    print("=" * 70)
    header = "  {:<42}".format("") + "".join(f"{r.annee:>{col_w}} an" for r in results)
    print(header)
    print("  " + "-" * (42 + (col_w + 3) * len(results)))
    for libelle, values in rows:
        line = f"  {libelle:<42}"
        for v in values:
            if libelle == "Années":
                line += f"{int(v):>{col_w}}   "
            else:
                line += f"{fmt_money(v):>{col_w}}   "
        print(line)


def print_highlight_cashflow(inp: PropertyInputs,
                             annees=(1, 5, 10)) -> None:
    """Résumé en tête : cashflow mensuel absolu et par personne
    pour les années clés (par défaut 1, 5 et 10)."""
    cf = build_cashflow(inp)
    by_year = {y.annee: y for y in cf}
    n = max(1, inp.nombre_investisseurs)

    print("=" * 70)
    print("RÉSUMÉ — CASHFLOW MENSUEL (années clés)")
    print("=" * 70)
    print(f"  {'Année':<10}{'CF mensuel absolu':>22}{'CF mensuel / personne':>26}")
    print("  " + "-" * 58)
    for annee in annees:
        y = by_year.get(annee)
        if y is None:
            continue
        cf_abs = y.cashflow_mensuel
        cf_pp = cf_abs / n
        print(f"  Année {annee:<4}{fmt_money(cf_abs):>22}{fmt_money(cf_pp):>26}")
    print()


def print_gain_global_summary(inp: PropertyInputs) -> None:
    """Résumé final : gain global absolu (total, annuel, par personne)
    pour chaque jalon de l'étude pluriannuelle."""
    results = build_20y_study(inp)
    n = max(1, inp.nombre_investisseurs)

    print("\n" + "=" * 70)
    print("RÉSUMÉ — GAIN GLOBAL ABSOLU (par jalon)")
    print("=" * 70)
    print(f"  {'Jalon':<10}{'Gain absolu':>18}{'Gain / an':>18}"
          f"{'Gain / personne':>20}{'Gain / an / pers':>20}")
    print("  " + "-" * 86)
    for r in results:
        print(
            f"  {str(r.annee) + ' an':<10}"
            f"{fmt_money(r.gain_global_absolu):>18}"
            f"{fmt_money(r.gain_global_annuel):>18}"
            f"{fmt_money(r.gain_global_absolu_par_personne):>20}"
            f"{fmt_money(r.gain_global_annuel_par_personne):>20}"
        )

    print("\n  Après impôt :")
    print(f"  {'Jalon':<10}{'Gain absolu':>18}{'Gain / an':>18}"
          f"{'Gain / personne':>20}{'Gain / an / pers':>20}")
    print("  " + "-" * 86)
    for r in results:
        print(
            f"  {str(r.annee) + ' an':<10}"
            f"{fmt_money(r.gain_global_absolu_apres_impot):>18}"
            f"{fmt_money(r.gain_global_annuel_apres_impot):>18}"
            f"{fmt_money(r.gain_global_absolu_pp_apres_impot):>20}"
            f"{fmt_money(r.gain_global_annuel_pp_apres_impot):>20}"
        )
    print()


def main() -> None:
    inp = PropertyInputs()
    print_highlight_cashflow(inp, annees=(1, 5, 10))
    print_inputs(inp)
    print_down_payment(inp)
    print_amortization(inp)
    print_cashflow_detail(inp, annee=1)
    print_cashflow_summary(inp)
    print_20y_study(inp)
    print_gain_global_summary(inp)
    plot_sensibilite(inp, delta_pct=0.5, pas_pct=0.1)


if __name__ == "__main__":
    main()

