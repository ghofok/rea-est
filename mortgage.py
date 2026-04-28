"""
Calcul du tableau d'amortissement hypothécaire mois par mois.

Colonnes produites :
    Année | Mois | Paiement hypothèque (mois)
          | Paiement hypothèque (mois) + assurance
          | Capital | Intérêt | Frais et Taxes
          | Total paiement mensuel | Total non-investie
          | Capital cumulatif | Intérêt cumulatif
          | Capital restant | Non-Investie cumulatif
"""
from dataclasses import dataclass
from typing import List
from inputs import PropertyInputs


def paiement_mensuel(montant: float, taux_mensuel: float, n: int) -> float:
    """Paiement hypothécaire mensuel (formule d'annuité)."""
    if taux_mensuel == 0:
        return montant / n
    return montant * taux_mensuel / (1 - (1 + taux_mensuel) ** (-n))


@dataclass
class AmortizationRow:
    annee: int
    mois: int
    paiement_hypo: float
    paiement_hypo_assur: float
    capital: float
    interet: float
    frais_taxes: float
    total_paiement_mensuel: float
    total_non_investie: float
    capital_cumul: float
    interet_cumul: float
    capital_restant: float
    non_investie_cumul: float


def build_amortization(inp: PropertyInputs) -> List[AmortizationRow]:
    montant = inp.montant_hypotheque
    tm = inp.taux_mensuel
    n = inp.nb_paiements
    pmt = paiement_mensuel(montant, tm, n)
    assur = inp.assurance_hypotheque_mensuelle
    frais_taxes = inp.frais_condo_mensuel + inp.taxes_mun_scol_mensuel
    loyer_mensuel_net = (inp.loyer_annuel_total / 12) * (1 - inp.taux_vacance_ratio)

    rows: List[AmortizationRow] = []
    solde = montant
    cap_cumul = 0.0
    int_cumul = 0.0
    non_inv_cumul = 0.0

    for k in range(1, n + 1):
        interet = solde * tm
        capital = pmt - interet
        solde = max(0.0, solde - capital)
        cap_cumul += capital
        int_cumul += interet

        paiement_total = pmt + assur + frais_taxes
        # "Non-investie" = portion non récupérée (intérêts + frais + assurance − loyer net)
        non_investie = interet + frais_taxes + assur - loyer_mensuel_net
        non_inv_cumul += non_investie

        annee = (k - 1) // 12 + 1
        mois = (k - 1) % 12 + 1

        rows.append(AmortizationRow(
            annee=annee,
            mois=mois,
            paiement_hypo=pmt,
            paiement_hypo_assur=pmt + assur,
            capital=capital,
            interet=interet,
            frais_taxes=frais_taxes,
            total_paiement_mensuel=paiement_total,
            total_non_investie=non_investie,
            capital_cumul=cap_cumul,
            interet_cumul=int_cumul,
            capital_restant=solde,
            non_investie_cumul=non_inv_cumul,
        ))
    return rows

