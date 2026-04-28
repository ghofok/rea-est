"""
Module de définition des entrées (paramètres) pour l'analyse immobilière.
Reproduit la feuille 'Input--Output' du fichier Excel.

⚠️ Convention : toutes les valeurs exprimées en % sont saisies EN POURCENT
   (ex. 20 pour 20 %, 3.20 pour 3,20 %). Les propriétés `*_ratio` renvoient
   la valeur décimale (0–1) utilisée dans les calculs.
"""
from dataclasses import dataclass


@dataclass
class PropertyInputs:
    # --- Prix ---
    prix_immobilier: float = 750000
    prix_marche: float = 750000

    # --- Hypothèque (valeurs en %) ---
    mise_de_fond_pct: float = 10
    duree_hypotheque_ans: int = 25
    taux_interet: float = 3.80
    # L'assurance hypothécaire (prime SCHL) est calculée automatiquement
    # via la propriété `assurance_hypotheque_mensuelle`. Barème en % du
    # montant emprunté, selon la quotité de financement (LTV = 1 - mise de fond) :
    taux_schl_ltv_90: float = 4.00   # LTV > 90 %
    taux_schl_ltv_85: float = 3.10   # 85 % < LTV <= 90 %
    taux_schl_ltv_80: float = 2.80   # 80 % < LTV <= 85 %
    # LTV <= 80 % → 0 % (pas d'assurance obligatoire)

    # --- Type de propriété ---
    # True  → condo (copropriété)  : travaux à 0 par défaut, assurance réduite
    # False → maison / plex         : travaux = 1 % de la valeur / an (an 1),
    #                                 puis indexés selon taux_augmentation_travaux
    est_condo: bool = False
    taux_travaux_maison_plex: float = 1.00  # % du prix d'achat par an (année 1)

    # --- Location (valeurs en %) ---
    taux_vacance: float = 3
    appreciation_annuelle: float = 3.5
    frais_condo_mensuel: float = 0
    taxes_mun_scol_mensuel: float = 382
    loyer_annuel_total: float = 54204

    # --- Meta-données ---
    nombre_investisseurs: int = 3
    taux_occupation_personnel: float = 0.0
    annees_occupation_personnel: int = 0
    # Si True : crédit "premier acheteur / occupation personnelle" qui réduit
    # la taxe de bienvenue jusqu'à concurrence de 4 500 $ (plafond fixe).
    occupation_personnelle: bool = False
    credit_taxe_bienvenue_max: float = 4_500.0

    # --- Frais initiaux fixes ---
    inspection: float = 1_000.0
    assurance_prime_initiale: float = 1_500.0
    frais_divers: float = 400.0
    # "Autre / Travaux à l'achat" : un seul montant unique (au lieu de
    # 1,5 %·prix + travaux séparés). Valeur par défaut 51 125 $.
    autre_et_travaux_achat: float = 51125

    # --- Exploitation ---
    # L'assurance habitation est calculée automatiquement via la propriété
    # `assurance_habitation_mensuelle` (voir plus bas). Ces taux sont
    # exprimés en % du prix d'achat, par an.
    #   - Si frais de condo > 0 (copropriété) : taux réduit (0,057 %)
    #   - Sinon (maison individuelle)         : taux plein  (0,3 %)
    taux_assurance_habitation_condo: float = 0.057   # si frais_condo > 0
    taux_assurance_habitation_maison: float = 0.300  # sinon
    travaux_mensuel: float = 0.0

    # --- Taux d'indexation annuels composés (en %) ---
    taux_augmentation_loyer: float = 2.50
    taux_augmentation_taxes: float = 2.50
    taux_augmentation_assurance: float = 2.50
    taux_augmentation_travaux: float = 2.50
    taux_augmentation_condo: float = 2.50

    # --- Horizon d'analyse du cashflow ---
    annees_analyse: int = 25

    # --- Frais de vente (en %) ---
    taux_agent_vente: float = 5.00
    autres_frais_vente: float = 1_000.0
    penalite_banque: float = 4_000.0
    penalite_avant_annee: int = 5

    # --- Impôts (en %) ---
    taux_impot_gain_capital: float = 25.0
    taux_impot_marginal: float = 35.0

    # --- Jalons d'étude pluriannuelle ---
    jalons_etude: tuple = (1, 5, 15, 20)

    # ------------------------------------------------------------------
    # Conversions % -> ratio décimal (utilisées par les calculs)
    # ------------------------------------------------------------------
    @property
    def mise_de_fond_ratio(self) -> float: return self.mise_de_fond_pct / 100

    @property
    def taux_interet_ratio(self) -> float: return self.taux_interet / 100

    @property
    def taux_vacance_ratio(self) -> float: return self.taux_vacance / 100

    @property
    def appreciation_annuelle_ratio(self) -> float: return self.appreciation_annuelle / 100

    @property
    def taux_occupation_personnel_ratio(self) -> float: return self.taux_occupation_personnel / 100

    @property
    def taux_augmentation_loyer_ratio(self) -> float: return self.taux_augmentation_loyer / 100

    @property
    def taux_augmentation_taxes_ratio(self) -> float: return self.taux_augmentation_taxes / 100

    @property
    def taux_augmentation_assurance_ratio(self) -> float: return self.taux_augmentation_assurance / 100

    @property
    def taux_augmentation_travaux_ratio(self) -> float: return self.taux_augmentation_travaux / 100

    @property
    def taux_augmentation_condo_ratio(self) -> float: return self.taux_augmentation_condo / 100

    @property
    def taux_agent_vente_ratio(self) -> float: return self.taux_agent_vente / 100

    @property
    def taux_impot_gain_capital_ratio(self) -> float: return self.taux_impot_gain_capital / 100

    @property
    def taux_impot_marginal_ratio(self) -> float: return self.taux_impot_marginal / 100

    # ------------------------------------------------------------------
    # Dérivés financiers
    # ------------------------------------------------------------------
    @property
    def mise_de_fond(self) -> float:
        return self.prix_immobilier * self.mise_de_fond_ratio

    @property
    def montant_hypotheque(self) -> float:
        return self.prix_immobilier - self.mise_de_fond

    @property
    def taux_mensuel(self) -> float:
        return self.taux_interet_ratio / 12

    @property
    def nb_paiements(self) -> int:
        return self.duree_hypotheque_ans * 12

    @property
    def assurance_habitation_annuelle(self) -> float:
        """Taux réduit si condo, taux plein si maison/plex."""
        if self.est_condo:
            taux = self.taux_assurance_habitation_condo / 100
        else:
            taux = self.taux_assurance_habitation_maison / 100
        return self.prix_immobilier * taux

    @property
    def assurance_habitation_mensuelle(self) -> float:
        return self.assurance_habitation_annuelle / 12

    @property
    def travaux_annuel_base(self) -> float:
        """Travaux annuels de l'année 1.
        - Condo          : valeur saisie (travaux_mensuel * 12), 0 par défaut
        - Maison / plex  : 1 % du prix d'achat (taux_travaux_maison_plex)
          Les années suivantes sont indexées via taux_augmentation_travaux.
        """
        if self.est_condo:
            return self.travaux_mensuel * 12
        return self.prix_immobilier * (self.taux_travaux_maison_plex / 100)

    # ------------------------------------------------------------------
    # Assurance hypothécaire (prime SCHL)
    # ------------------------------------------------------------------
    @property
    def ltv_ratio(self) -> float:
        """Loan-to-Value = 1 - mise de fond (en ratio décimal)."""
        return 1 - self.mise_de_fond_ratio

    @property
    def taux_schl_ratio(self) -> float:
        """Taux de prime SCHL (ratio décimal) selon la quotité de financement.
        Reproduit la formule Excel :
            SI((1-B6)>0,9 ; 0,04 ;
               SI((1-B6)>0,85; 0,031;
                  SI((1-B6)>0,8 ; 0,028; 0)))
        """
        ltv = self.ltv_ratio
        if ltv > 0.90:
            return self.taux_schl_ltv_90 / 100
        if ltv > 0.85:
            return self.taux_schl_ltv_85 / 100
        if ltv > 0.80:
            return self.taux_schl_ltv_80 / 100
        return 0.0

    @property
    def prime_schl_totale(self) -> float:
        """Prime SCHL totale = montant emprunté × taux SCHL."""
        return self.montant_hypotheque * self.taux_schl_ratio

    @property
    def assurance_hypotheque_mensuelle(self) -> float:
        """Formule Excel :
            =((1-B6)*B4) * taux_SCHL / 12 / B7
        → prime totale répartie uniformément sur toute la durée
          (en nombre de mois = 12 × durée en années).
        """
        if self.duree_hypotheque_ans <= 0:
            return 0.0
        return self.prime_schl_totale / (12 * self.duree_hypotheque_ans)


DEFAULT_INPUTS = PropertyInputs()

