"""
Calcul du cashflow annuel (années 1 à N).

Structure (par année) reproduisant l'exemple Excel :

  REVENU
    - Loyer annuel total (indexé au taux d'augmentation loyer)
    - moins Vacance locative (taux_vacance * loyer)
    = Total revenu

  CHARGES
    - Hypothèque (capital + intérêt + assurance hypothécaire)
    - Frais de condo (indexés)
    - Taxes municipales et scolaires (indexées)
    - Assurance habitation (indexée)
    - Travaux (indexés)

  Total charges d'exploitation   = condo + taxes + assur. hab. + travaux + vacance
                                   (= TOTAL DES CHARGES SANS HYPOTHÈQUE)
  Total charges hors capital     = exploitation + (intérêt + assur. hypo.)
  Total charges                  = hors capital + capital
  Total charges déductibles      = hors capital    (le capital n'est pas déductible)

  Cashflow          = Total revenu  - Total charges
  Gain imposable    = Total revenu  - Total charges déductibles
"""
from dataclasses import dataclass
from typing import List
from inputs import PropertyInputs
from mortgage import build_amortization, AmortizationRow


@dataclass
class CashflowYear:
    annee: int
    # Revenu
    loyer_brut_annuel: float
    vacance_annuelle: float
    total_revenu: float
    # Hypothèque
    capital_annuel: float
    interet_assur_hypo_annuel: float
    hypotheque_totale_annuelle: float
    # Valeurs mensuelles issues du 1er mois de l'année (et non moyenne)
    capital_mois1: float
    interet_assur_hypo_mois1: float
    hypotheque_totale_mois1: float
    # Exploitation
    frais_condo_annuel: float
    taxes_annuelles: float
    assurance_habitation_annuelle: float
    travaux_annuel: float
    total_exploitation: float
    # Totaux
    total_charges_hors_capital: float
    total_charges: float
    total_charges_deductibles: float
    # Résultats
    cashflow_annuel: float
    cashflow_mensuel: float
    cashflow_par_personne_annuel: float
    cashflow_par_personne_mensuel: float
    gain_imposable_annuel: float
    gain_imposable_mensuel: float
    gain_imposable_pp_annuel: float
    gain_imposable_pp_mensuel: float


def _agreger_annee(rows: List[AmortizationRow], annee: int):
    """Retourne (capital_annuel, interet_annuel, assurance_hypo_annuelle)
    à partir du tableau d'amortissement. Pour les années au-delà de la durée,
    renvoie des zéros (hypothèque payée)."""
    annee_rows = [r for r in rows if r.annee == annee]
    if not annee_rows:
        return 0.0, 0.0, 0.0
    capital = sum(r.capital for r in annee_rows)
    interet = sum(r.interet for r in annee_rows)
    # assurance hypothécaire = paiement+assur - paiement
    assur_hypo = sum(r.paiement_hypo_assur - r.paiement_hypo for r in annee_rows)
    return capital, interet, assur_hypo


def _premier_mois(rows: List[AmortizationRow], annee: int):
    """Retourne (capital, interet, assurance_hypo) du 1er mois de l'année.
    Utilisé pour afficher la valeur mensuelle 'de début d'année' plutôt
    qu'une moyenne annuelle."""
    for r in rows:
        if r.annee == annee and r.mois == 1:
            assur_hypo = r.paiement_hypo_assur - r.paiement_hypo
            return r.capital, r.interet, assur_hypo
    return 0.0, 0.0, 0.0


def build_cashflow(inp: PropertyInputs) -> List[CashflowYear]:
    amort = build_amortization(inp)
    n = max(1, inp.nombre_investisseurs)

    loyer0 = inp.loyer_annuel_total
    condo0 = inp.frais_condo_mensuel * 12
    taxes0 = inp.taxes_mun_scol_mensuel * 12
    assur_hab0 = inp.assurance_habitation_mensuelle * 12
    travaux0 = inp.travaux_annuel_base

    results: List[CashflowYear] = []
    for annee in range(1, inp.annees_analyse + 1):
        # Convention : les valeurs indexées sont prises en DÉBUT d'année.
        #   - année 1 : k = 0 → valeurs de base (moment de l'achat)
        #   - année n : k = n-1 → (n-1) indexations annuelles composées
        k = annee - 1

        loyer = loyer0 * (1 + inp.taux_augmentation_loyer_ratio) ** k
        vacance = loyer * inp.taux_vacance_ratio
        # Le revenu est affiché BRUT (loyer potentiel 100 %). La vacance
        # locative est comptabilisée côté CHARGES (dans total_exploitation).
        total_revenu = loyer

        condo = condo0 * (1 + inp.taux_augmentation_condo_ratio) ** k
        taxes = taxes0 * (1 + inp.taux_augmentation_taxes_ratio) ** k
        assur_hab = assur_hab0 * (1 + inp.taux_augmentation_assurance_ratio) ** k
        travaux = travaux0 * (1 + inp.taux_augmentation_travaux_ratio) ** k

        capital, interet, assur_hypo = _agreger_annee(amort, annee)
        interet_assur = interet + assur_hypo
        hypo_totale = capital + interet_assur

        cap_m1, int_m1, assur_hypo_m1 = _premier_mois(amort, annee)
        interet_assur_m1 = int_m1 + assur_hypo_m1
        hypo_totale_m1 = cap_m1 + interet_assur_m1

        total_exploitation = condo + taxes + assur_hab + travaux + vacance
        total_hors_capital = total_exploitation + interet_assur
        total_charges = total_hors_capital + capital
        total_deductibles = total_hors_capital

        cashflow = total_revenu - total_charges
        gain_imp = total_revenu - total_deductibles

        results.append(CashflowYear(
            annee=annee,
            loyer_brut_annuel=loyer,
            vacance_annuelle=vacance,
            total_revenu=total_revenu,
            capital_annuel=capital,
            interet_assur_hypo_annuel=interet_assur,
            hypotheque_totale_annuelle=hypo_totale,
            capital_mois1=cap_m1,
            interet_assur_hypo_mois1=interet_assur_m1,
            hypotheque_totale_mois1=hypo_totale_m1,
            frais_condo_annuel=condo,
            taxes_annuelles=taxes,
            assurance_habitation_annuelle=assur_hab,
            travaux_annuel=travaux,
            total_exploitation=total_exploitation,
            total_charges_hors_capital=total_hors_capital,
            total_charges=total_charges,
            total_charges_deductibles=total_deductibles,
            cashflow_annuel=cashflow,
            cashflow_mensuel=cashflow / 12,
            cashflow_par_personne_annuel=cashflow / n,
            cashflow_par_personne_mensuel=(cashflow / n) / 12,
            gain_imposable_annuel=gain_imp,
            gain_imposable_mensuel=gain_imp / 12,
            gain_imposable_pp_annuel=gain_imp / n,
            gain_imposable_pp_mensuel=(gain_imp / n) / 12,
        ))
    return results


def detail_annee(inp: PropertyInputs, annee: int = 1) -> dict:
    """Retourne la ventilation détaillée (mensuel + annuel) d'une année,
    dans le format du tableau Excel fourni en exemple."""
    cf = build_cashflow(inp)
    y = next(x for x in cf if x.annee == annee)
    return {
        "Revenu": {
            "Total revenu locatif": (y.loyer_brut_annuel / 12, y.loyer_brut_annuel),
            "Total revenu":         (y.total_revenu / 12, y.total_revenu),
        },
        "Charges": {
            "Hypothèque avec assurance hypo.":   (y.hypotheque_totale_mois1,  y.hypotheque_totale_annuelle),
            "  Capital":                         (y.capital_mois1,            y.capital_annuel),
            "  Intérêt + assur. hypothécaire":   (y.interet_assur_hypo_mois1, y.interet_assur_hypo_annuel),
            "Frais de condo":                    (y.frais_condo_annuel / 12, y.frais_condo_annuel),
            "Taxes municipale et scolaire":      (y.taxes_annuelles / 12, y.taxes_annuelles),
            "Assurance habitation":              (y.assurance_habitation_annuelle / 12, y.assurance_habitation_annuelle),
            "Travaux":                           (y.travaux_annuel / 12, y.travaux_annuel),
            "Vacance locative":                  (y.vacance_annuelle / 12, y.vacance_annuelle),
            "Total charge d'exploitation":       (y.total_exploitation / 12, y.total_exploitation),
            "Total charges hors capital":        (y.total_charges_hors_capital / 12, y.total_charges_hors_capital),
            "Total charges":                     (y.total_charges / 12, y.total_charges),
            "Total charges déductibles impôt":   (y.total_charges_deductibles / 12, y.total_charges_deductibles),
        },
        "Résultats": {
            "Cashflow":                  (y.cashflow_mensuel, y.cashflow_annuel),
            "Cashflow par personne":     (y.cashflow_par_personne_mensuel, y.cashflow_par_personne_annuel),
            "Gain imposable":            (y.gain_imposable_mensuel, y.gain_imposable_annuel),
            "Gain imposable par personne": (y.gain_imposable_pp_mensuel, y.gain_imposable_pp_annuel),
        },
    }


