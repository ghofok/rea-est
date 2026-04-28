"""
Calcul de la mise de fond et des charges initiales à l'achat.
Inclut le calcul de la taxe de bienvenue (droits de mutation, Québec)
et des frais de notaire selon barèmes par paliers.
"""
from dataclasses import dataclass
from inputs import PropertyInputs


# ---------- Barèmes ----------

def calcul_notaire(prix: float) -> float:
    """Frais de notaire (barèmes par paliers)."""
    if prix <= 300_000:
        return 2_000.0
    if prix <= 500_000:
        return 2_500 + (prix - 300_000) * 0.0025
    if prix <= 800_000:
        return 3_000 + (prix - 500_000) * 0.003
    return 3_500 + (prix - 800_000) * 0.004


def calcul_taxe_bienvenue(prix: float) -> float:
    """Droits de mutation immobilière (taxe de bienvenue, Québec)."""
    paliers = [
        (58_900,    0.005),
        (294_600,   0.010),
        (552_300,   0.015),
        (1_104_700, 0.020),
        (2_136_500, 0.025),
        (3_113_000, 0.035),
        (float("inf"), 0.040),
    ]
    taxe = 0.0
    borne_inf = 0.0
    for borne_sup, taux in paliers:
        if prix <= borne_sup:
            taxe += (prix - borne_inf) * taux
            return taxe
        taxe += (borne_sup - borne_inf) * taux
        borne_inf = borne_sup
    return taxe


# ---------- Résultat ----------

@dataclass
class DownPaymentBreakdown:
    mise_de_fond: float
    taxe_bienvenue: float
    notaire: float
    inspection: float
    assurance_prime_initiale: float
    frais: float
    autre_et_travaux: float
    nombre_investisseurs: int = 1

    @property
    def total_charges_initiales(self) -> float:
        return (self.taxe_bienvenue + self.notaire + self.inspection
                + self.assurance_prime_initiale + self.frais
                + self.autre_et_travaux)

    @property
    def total_depense_achat(self) -> float:
        return self.mise_de_fond + self.total_charges_initiales

    def par_personne(self, montant: float) -> float:
        return montant / self.nombre_investisseurs if self.nombre_investisseurs else 0.0

    def to_table(self) -> list[tuple[str, float, float]]:
        """Retourne (libellé, total, total par personne)."""
        rows = [
            ("Mise de fond",                self.mise_de_fond),
            ("Total Mise de Fond",          self.mise_de_fond),
            ("Taxe Bienv total",            self.taxe_bienvenue),
            ("Notaire total",               self.notaire),
            ("Inspection",                  self.inspection),
            ("Assurance prime initiale",    self.assurance_prime_initiale),
            ("Frais",                       self.frais),
            ("Autre / Travaux à l'achat",   self.autre_et_travaux),
            ("Total charges initiales",     self.total_charges_initiales),
            ("Total dépense à l'achat",     self.total_depense_achat),
        ]
        return [(lib, m, self.par_personne(m)) for lib, m in rows]


def compute_down_payment(inp: PropertyInputs) -> DownPaymentBreakdown:
    prix = inp.prix_immobilier
    taxe_bv = calcul_taxe_bienvenue(prix)
    # Crédit "occupation personnelle" : réduit la taxe de bienvenue
    # jusqu'à concurrence du plafond (par défaut 4 500 $), sans devenir négative.
    if inp.occupation_personnelle:
        taxe_bv = max(0.0, taxe_bv - inp.credit_taxe_bienvenue_max)
    return DownPaymentBreakdown(
        mise_de_fond=inp.mise_de_fond,
        taxe_bienvenue=taxe_bv,
        notaire=calcul_notaire(prix),
        inspection=inp.inspection,
        assurance_prime_initiale=inp.assurance_prime_initiale,
        frais=inp.frais_divers,
        autre_et_travaux=inp.autre_et_travaux_achat,
        nombre_investisseurs=inp.nombre_investisseurs,
    )

