"""Configuration des champs éditables, conversions de format et helpers
de (dé)sérialisation du `dcc.Store` ↔ `PropertyInputs`."""
from __future__ import annotations
import os
import sys
from dataclasses import fields

# Permet d'importer les modules de calcul du dossier parent
_PARENT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if _PARENT not in sys.path:
    sys.path.insert(0, _PARENT)

from inputs import PropertyInputs  # noqa: E402


# --------------------------------------------------------------------- #
# Formatage
# --------------------------------------------------------------------- #
def fmt_money(x: float) -> str:
    try:
        s = f"{x:,.2f}".replace(",", " ").replace(".", ",")
        return f"{s} $"
    except Exception:
        return str(x)


def fmt_money0(x: float) -> str:
    try:
        s = f"{x:,.0f}".replace(",", " ")
        return f"{s} $"
    except Exception:
        return str(x)


def fmt_int(x: float) -> str:
    return fmt_money0(x)


# --------------------------------------------------------------------- #
# Sections de champs éditables (alimente l'onglet Paramètres)
# --------------------------------------------------------------------- #
FIELD_SECTIONS: list[tuple[str, str, list[tuple[str, str, str]]]] = [
    ("Propriété", "bi-house-door", [
        ("prix_immobilier",            "Prix immobilier ($)",                  "number"),
        ("prix_marche",                "Prix marché ($)",                      "number"),
        ("est_condo",                  "Type : condo ?",                       "bool"),
    ]),
    ("Hypothèque", "bi-bank", [
        ("mise_de_fond_pct",           "Mise de fond (%)",                     "number"),
        ("duree_hypotheque_ans",       "Durée (ans)",                          "number"),
        ("taux_interet",               "Taux d'intérêt (%)",                   "number"),
    ]),
    ("Location", "bi-cash-coin", [
        ("loyer_annuel_total",         "Loyer annuel total ($)",               "number"),
        ("taux_vacance",               "Taux de vacance (%)",                  "number"),
        ("appreciation_annuelle",      "Appréciation / an (%)",                "number"),
        ("frais_condo_mensuel",        "Frais de condo / mois ($)",            "number"),
        ("taxes_mun_scol_mensuel",     "Taxes mun. & scol. / mois ($)",        "number"),
    ]),
    ("Investisseurs", "bi-people", [
        ("nombre_investisseurs",       "Nombre d'investisseurs",               "number"),
    ]),
    ("Charges initiales d'achat ($)", "bi-cash-stack", [
        ("inspection",                 "Inspection",                           "number"),
        ("assurance_prime_initiale",   "Assurance prime initiale",             "number"),
        ("frais_divers",               "Frais",                                "number"),
        ("autre_et_travaux_achat",     "Autre / Travaux à l'achat",            "number"),
        ("occupation_personnelle",     "Occupation personnelle (crédit taxe bienvenue)", "bool"),
        ("credit_taxe_bienvenue_max",  "Crédit max taxe bienvenue ($)",        "number"),
    ]),
    ("Taux d'indexation (% / an)", "bi-graph-up", [
        ("taux_augmentation_loyer",    "Loyer",                                "number"),
        ("taux_augmentation_taxes",    "Taxes",                                "number"),
        ("taux_augmentation_assurance","Assurance",                            "number"),
        ("taux_augmentation_travaux",  "Travaux",                              "number"),
        ("taux_augmentation_condo",    "Frais de condo",                       "number"),
    ]),
    ("Frais de vente", "bi-tag", [
        ("taux_agent_vente",           "Frais d'agent (%)",                    "number"),
        ("autres_frais_vente",         "Autres frais ($)",                     "number"),
        ("penalite_banque",            "Pénalité banque ($)",                  "number"),
        ("penalite_avant_annee",       "Pénalité avant l'année #",             "number"),
    ]),
    ("Impôts (%)", "bi-receipt", [
        ("taux_impot_gain_capital",    "Gain en capital",                      "number"),
        ("taux_impot_marginal",        "Taux marginal",                        "number"),
    ]),
    ("Analyse", "bi-calendar-range", [
        ("annees_analyse",             "Années d'analyse",                     "number"),
    ]),
]

EDITABLE_FIELDS = [f for _, _, flist in FIELD_SECTIONS for f in flist]


# --------------------------------------------------------------------- #
# Variante traduite (FR / EN) — les libellés sont résolus à chaque appel
# en lisant le cookie ``lang`` via ``i18n.t``.
# --------------------------------------------------------------------- #
# Mapping : section_title_fr → clé i18n
_SECTION_KEY = {
    "Propriété": "sec_property",
    "Hypothèque": "sec_mortgage",
    "Location": "sec_rental",
    "Investisseurs": "sec_investors",
    "Charges initiales d'achat ($)": "sec_initial_costs",
    "Taux d'indexation (% / an)": "sec_indexation",
    "Frais de vente": "sec_sale_costs",
    "Impôts (%)": "sec_taxes",
    "Analyse": "sec_analysis",
}
# Mapping : nom d'attribut → clé i18n
_FIELD_KEY = {
    "prix_immobilier": "f_prix_immobilier",
    "prix_marche": "f_prix_marche",
    "est_condo": "f_est_condo",
    "mise_de_fond_pct": "f_mise_de_fond_pct",
    "duree_hypotheque_ans": "f_duree_hypotheque",
    "taux_interet": "f_taux_interet",
    "loyer_annuel_total": "f_loyer_annuel",
    "taux_vacance": "f_taux_vacance",
    "appreciation_annuelle": "f_appreciation",
    "frais_condo_mensuel": "f_frais_condo",
    "taxes_mun_scol_mensuel": "f_taxes_mun",
    "nombre_investisseurs": "f_nb_investisseurs",
    "inspection": "f_inspection",
    "assurance_prime_initiale": "f_assurance_prime",
    "frais_divers": "f_frais_divers",
    "autre_et_travaux_achat": "f_autre_travaux",
    "occupation_personnelle": "f_occupation_perso",
    "credit_taxe_bienvenue_max": "f_credit_taxe_max",
    "taux_augmentation_loyer": "f_taux_loyer",
    "taux_augmentation_taxes": "f_taux_taxes",
    "taux_augmentation_assurance": "f_taux_assurance",
    "taux_augmentation_travaux": "f_taux_travaux",
    "taux_augmentation_condo": "f_taux_condo",
    "taux_agent_vente": "f_taux_agent",
    "autres_frais_vente": "f_autres_frais_vente",
    "penalite_banque": "f_penalite_banque",
    "penalite_avant_annee": "f_penalite_avant",
    "taux_impot_gain_capital": "f_taux_gain_capital",
    "taux_impot_marginal": "f_taux_marginal",
    "annees_analyse": "f_annees_analyse",
}


def field_sections_translated():
    """Retourne ``FIELD_SECTIONS`` avec libellés traduits selon la langue
    courante (cookie ``lang``)."""
    from i18n import t
    out = []
    for title, icon, flist in FIELD_SECTIONS:
        new_title = t(_SECTION_KEY.get(title, title))
        new_flist = []
        for attr, libelle, widget in flist:
            new_lib = t(_FIELD_KEY.get(attr, libelle))
            new_flist.append((attr, new_lib, widget))
        out.append((new_title, icon, new_flist))
    return out


# --------------------------------------------------------------------- #
# Conversion Store ↔ PropertyInputs
# --------------------------------------------------------------------- #
def build_inputs_from_store(store: dict | None) -> PropertyInputs:
    """Reconstruit un `PropertyInputs` à partir du dict du `dcc.Store`."""
    inp = PropertyInputs()
    if not store:
        return inp
    for f in fields(inp):
        if f.name in store and store[f.name] is not None:
            val = store[f.name]
            try:
                cur = getattr(inp, f.name)
                if isinstance(cur, bool):
                    val = bool(val)
                elif isinstance(cur, int):
                    val = int(val)
                elif isinstance(cur, float):
                    val = float(val)
            except Exception:
                pass
            setattr(inp, f.name, val)
    if "jalons_etude" in store and store["jalons_etude"]:
        try:
            jalons = tuple(sorted(int(j) for j in store["jalons_etude"]
                                  if j is not None))
            if jalons:
                inp.jalons_etude = jalons
        except Exception:
            pass
    return inp


def default_store_dict() -> dict:
    inp = PropertyInputs()
    d = {f.name: getattr(inp, f.name) for f in fields(inp)}
    d["jalons_etude"] = list(inp.jalons_etude)
    return d

