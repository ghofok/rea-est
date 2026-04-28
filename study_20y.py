"""
Étude pluriannuelle (jalons : 1, 5, 10, 15, 20 ans).

Pour chaque jalon k, on calcule :
  - Cashflow cumulatif                 (somme CF_annuel sur 1..k)
  - Capital remboursé cumulé           (depuis l'amortissement)
  - Mise de fonds initiale             (constante)
  - Charges achat initial              (constantes)
  - Total capital possédé              = Mise de fonds + Capital remboursé
  - Équité totale                      = Capital possédé + Cashflow cumul
  - Gain de valeur immobilière         = Prix × ((1+appr)^k - 1)

  - Gain global avant frais de vente   = CF_cumul + Cap_rembs + Gain_immo − Charges_init
  - Frais d'agent à la vente           = taux_agent × Prix_vente(k)
  - Autres frais                       = constant
  - Pénalité banque                    = penalite si k < penalite_avant_annee, sinon 0
  - Total des frais de vente
  - Gain global absolu                 = Gain_avant_frais − Frais_vente − Mise_fonds
  - Gain global absolu par personne    = / nb_investisseurs
  - Gain global annuel                 = Gain_absolu / k
  - Gain global annuel par personne    = idem / nb_investisseurs

  Impôts :
    - Impôt sur gain en capital à la vente = taux × Gain_immo
    - Gain imposable cumulé                = Σ gain_imposable_annuel (1..k)
    - Impôt gain cumulé                    = taux_marginal × gain_imposable_cumulé
    - Impôts total cumulé                  = Impôt gain capital + Impôt gain cumulé

    - CF annuel par période brut (avant impôt) :
        * période 1 : CF_cumul(1) − Mise_fonds − Charges_init
        * périodes suivantes : (CF_cumul(k) − CF_cumul(k_prev)) / (k − k_prev)
    - CF annuel par période net (après impôt) :
        brut − (Δ impôt_gain_cumul / Δ années de la période)

    - Gain global absolu après impôt = Gain_global_absolu − Impôts_total_cumulé
    - Gain global annuel après impôt = / k
"""
from dataclasses import dataclass
from typing import List
from inputs import PropertyInputs
from down_payment import compute_down_payment
from mortgage import build_amortization
from cashflow import build_cashflow


@dataclass
class MilestoneResult:
    annee: int
    # Bloc équité
    cashflow_cumulatif: float
    capital_rembourse: float
    mise_de_fonds: float
    charges_achat_initial: float
    total_capital_possede: float
    equite_totale: float
    gain_valeur_immo: float
    valeur_bien_vente: float
    # Gain avant frais de vente
    gain_global_avant_frais: float
    gain_global_avant_frais_annuel: float
    gain_global_avant_frais_mensuel: float
    # Frais de vente
    frais_agent_vente: float
    autres_frais: float
    penalite_banque: float
    total_frais_vente: float
    # Gain global absolu
    gain_global_absolu: float
    gain_global_absolu_par_personne: float
    gain_global_annuel: float
    gain_global_annuel_par_personne: float
    gain_global_mensuel: float
    gain_global_mensuel_par_personne: float
    # Impôts
    impot_gain_capital_vente: float
    gain_imposable_cumule: float
    impot_gain_cumule: float
    impots_total_cumule: float
    # Cashflow par période
    cashflow_periode_brut_pp: float
    cashflow_periode_net_pp: float
    # Après impôt
    gain_global_absolu_apres_impot: float
    gain_global_absolu_pp_apres_impot: float
    gain_global_annuel_apres_impot: float
    gain_global_annuel_pp_apres_impot: float


def build_20y_study(inp: PropertyInputs) -> List[MilestoneResult]:
    amort = build_amortization(inp)
    cf = build_cashflow(inp)
    dp = compute_down_payment(inp)

    mise_fonds = dp.mise_de_fond
    charges_init = dp.total_charges_initiales
    n_inv = max(1, inp.nombre_investisseurs)

    # Pré-calculs cumulés par année
    cf_cumul = {}
    gain_imp_cumul = {}
    cap_rembs_cumul = {}
    cumul_cf = 0.0
    cumul_gi = 0.0
    for y in cf:
        cumul_cf += y.cashflow_annuel
        cumul_gi += y.gain_imposable_annuel
        cf_cumul[y.annee] = cumul_cf
        gain_imp_cumul[y.annee] = cumul_gi

    cumul_cap = 0.0
    for r in amort:
        cumul_cap += r.capital
        if r.mois == 12 or r is amort[-1]:
            cap_rembs_cumul[r.annee] = cumul_cap
    # Compléter si annees_analyse > durée d'hypothèque
    last_cap = cumul_cap
    for annee in range(1, inp.annees_analyse + 1):
        cap_rembs_cumul.setdefault(annee, last_cap)

    jalons = sorted(inp.jalons_etude)
    results: List[MilestoneResult] = []

    prev_k = 0
    prev_cf_cumul = 0.0
    prev_impot_gain_cumul = 0.0

    for k in jalons:
        cf_cum_k = cf_cumul.get(k, 0.0)
        gi_cum_k = gain_imp_cumul.get(k, 0.0)
        cap_k = cap_rembs_cumul.get(k, 0.0)

        # La valeur marchande croît à partir du prix de MARCHÉ (input),
        # pas du prix payé. Le gain réel = prix de vente - prix d'achat.
        prix_vente = inp.prix_marche * (1 + inp.appreciation_annuelle_ratio) ** k
        gain_immo = prix_vente - inp.prix_immobilier

        total_cap_possede = mise_fonds + cap_k
        equite = total_cap_possede + cf_cum_k

        # Gain global AVANT frais de vente
        #   = Capital remboursé + Gain valeur immo. − Charges achat initial
        #     + Cashflow cumulatif (positif ou négatif)
        gain_avant_frais = cap_k + gain_immo - charges_init + cf_cum_k

        frais_agent = inp.taux_agent_vente_ratio * prix_vente
        autres = inp.autres_frais_vente
        penalite = inp.penalite_banque if k < inp.penalite_avant_annee else 0.0
        total_frais = frais_agent + autres + penalite

        gain_absolu = gain_avant_frais - total_frais
        gain_annuel = gain_absolu / k

        # Impôts
        impot_gain_cap = inp.taux_impot_gain_capital_ratio * gain_immo
        impot_gain_cumul = inp.taux_impot_marginal_ratio * gi_cum_k
        impots_total = impot_gain_cap + impot_gain_cumul

        # Cashflow par période
        if prev_k == 0:
            cf_periode_brut = cf_cum_k - mise_fonds - charges_init
            d_impot = impot_gain_cumul
            cf_periode_net = cf_periode_brut - d_impot
        else:
            n_ans = k - prev_k
            cf_periode_brut = (cf_cum_k - prev_cf_cumul) / n_ans
            d_impot_moyen = (impot_gain_cumul - prev_impot_gain_cumul) / n_ans
            cf_periode_net = cf_periode_brut - d_impot_moyen

        gain_absolu_ap = gain_absolu - impots_total
        gain_annuel_ap = gain_absolu_ap / k

        results.append(MilestoneResult(
            annee=k,
            cashflow_cumulatif=cf_cum_k,
            capital_rembourse=cap_k,
            mise_de_fonds=mise_fonds,
            charges_achat_initial=charges_init,
            total_capital_possede=total_cap_possede,
            equite_totale=equite,
            gain_valeur_immo=gain_immo,
            valeur_bien_vente=prix_vente,
            gain_global_avant_frais=gain_avant_frais,
            gain_global_avant_frais_annuel=gain_avant_frais / k,
            gain_global_avant_frais_mensuel=gain_avant_frais / k / 12,
            frais_agent_vente=frais_agent,
            autres_frais=autres,
            penalite_banque=penalite,
            total_frais_vente=total_frais,
            gain_global_absolu=gain_absolu,
            gain_global_absolu_par_personne=gain_absolu / n_inv,
            gain_global_annuel=gain_annuel,
            gain_global_annuel_par_personne=gain_annuel / n_inv,
            gain_global_mensuel=gain_annuel / 12,
            gain_global_mensuel_par_personne=(gain_annuel / n_inv) / 12,
            impot_gain_capital_vente=impot_gain_cap,
            gain_imposable_cumule=gi_cum_k,
            impot_gain_cumule=impot_gain_cumul,
            impots_total_cumule=impots_total,
            cashflow_periode_brut_pp=cf_periode_brut / n_inv,
            cashflow_periode_net_pp=cf_periode_net / n_inv,
            gain_global_absolu_apres_impot=gain_absolu_ap,
            gain_global_absolu_pp_apres_impot=gain_absolu_ap / n_inv,
            gain_global_annuel_apres_impot=gain_annuel_ap,
            gain_global_annuel_pp_apres_impot=gain_annuel_ap / n_inv,
        ))

        prev_k = k
        prev_cf_cumul = cf_cum_k
        prev_impot_gain_cumul = impot_gain_cumul

    return results


def to_table(results: List[MilestoneResult]) -> list:
    """Transforme les résultats en tableau (libellé, valeur_k1, valeur_k2, ...).

    Les libellés sont harmonisés et regroupés en sections logiques :
        1. Équité & capital
        2. Valeur du bien & gain immobilier
        3. Gain global avant frais de vente
        4. Frais de vente
        5. Gain global absolu (avant impôt)
        6. Impôts
        7. Cashflow par période
        8. Gain global absolu (après impôt)

    Conventions :
        - "Cashflow cumulatif"        (et non "Cashflow Cumulatif")
        - "par personne"              (jamais "/pers")
        - "après impôt"               (jamais "ap. impôt")
        - "annuel" / "mensuel"        en suffixe explicite
    """
    labels = [
        ("Années",                                              "annee"),

        # 1) Équité & capital
        ("Cashflow cumulatif",                                  "cashflow_cumulatif"),
        ("Capital remboursé",                                   "capital_rembourse"),
        ("Mise de fonds initiale",                              "mise_de_fonds"),
        ("Charges initiales d'achat",                           "charges_achat_initial"),
        ("Total capital possédé",                               "total_capital_possede"),

        # 2) Valeur du bien & gain immobilier
        ("Valeur du bien à la vente",                           "valeur_bien_vente"),
        ("Gain de valeur immobilière",                          "gain_valeur_immo"),

        # 3) Gain global avant frais de vente
        ("Gain global avant frais de vente",                    "gain_global_avant_frais"),
        ("Gain global avant frais de vente — annuel",           "gain_global_avant_frais_annuel"),
        ("Gain global avant frais de vente — mensuel",          "gain_global_avant_frais_mensuel"),

        # 4) Frais de vente
        ("Frais d'agent à la vente",                            "frais_agent_vente"),
        ("Autres frais de vente",                               "autres_frais"),
        ("Pénalité banque",                                     "penalite_banque"),
        ("Total des frais de vente",                            "total_frais_vente"),

        # 5) Gain global absolu (avant impôt)
        ("Gain global absolu",                                  "gain_global_absolu"),
        ("Gain global absolu par personne",                     "gain_global_absolu_par_personne"),
        ("Gain global annuel",                                  "gain_global_annuel"),
        ("Gain global annuel par personne",                     "gain_global_annuel_par_personne"),
        ("Gain global mensuel",                                 "gain_global_mensuel"),
        ("Gain global mensuel par personne",                    "gain_global_mensuel_par_personne"),

        # 6) Impôts
        ("Impôt sur gain en capital à la vente",                "impot_gain_capital_vente"),
        ("Gain imposable cumulé",                               "gain_imposable_cumule"),
        ("Impôt sur gain imposable cumulé",                     "impot_gain_cumule"),
        ("Impôts totaux cumulés",                               "impots_total_cumule"),

        # 7) Cashflow par période
        ("Cashflow par période brut par personne (avant impôt)", "cashflow_periode_brut_pp"),
        ("Cashflow par période net par personne (après impôt)",  "cashflow_periode_net_pp"),

        # 8) Gain global absolu (après impôt)
        ("Gain global absolu après impôt",                      "gain_global_absolu_apres_impot"),
        ("Gain global absolu par personne après impôt",         "gain_global_absolu_pp_apres_impot"),
        ("Gain global annuel après impôt",                      "gain_global_annuel_apres_impot"),
        ("Gain global annuel par personne après impôt",         "gain_global_annuel_pp_apres_impot"),
    ]
    rows = []
    for libelle, attr in labels:
        values = [getattr(r, attr) for r in results]
        rows.append((libelle, values))
    return rows


