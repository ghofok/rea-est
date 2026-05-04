"""Internationalisation FR / EN.

La langue est stockée dans un cookie ``lang`` (``fr`` ou ``en``).  Comme
``build_layout`` est un callable invoqué par Dash à chaque chargement de
page, ``get_lang()`` lit simplement le cookie de la requête courante.

Usage :
    from i18n import t
    html.H1(t("dashboard"))
"""
from __future__ import annotations
from flask import has_request_context, request
from dash import Output, Input

DEFAULT_LANG = "fr"
SUPPORTED = ("fr", "en")

# --------------------------------------------------------------------- #
# Traductions
# --------------------------------------------------------------------- #
# clé : { "fr": ..., "en": ... }
TRANSLATIONS: dict[str, dict[str, str]] = {
    # Navbar / global
    "app_title":           {"fr": "Analyse immobilière",
                            "en": "Real-estate analysis"},
    "dashboard_subtitle":  {"fr": "Tableau de bord interactif",
                            "en": "Interactive dashboard"},
    "logout":              {"fr": "Déconnexion", "en": "Sign out"},
    "language":            {"fr": "Langue", "en": "Language"},
    "french":              {"fr": "Français", "en": "French"},
    "english":             {"fr": "Anglais",  "en": "English"},

    # Sidebar scénarios
    "scenarios":           {"fr": "Scénarios", "en": "Scenarios"},
    "click_to_switch":     {"fr": "Cliquez pour basculer.",
                            "en": "Click to switch."},
    "new_scenario_ph":     {"fr": "Nom du nouveau scénario…",
                            "en": "New scenario name…"},
    "add_scenario_title":  {"fr": "Ajouter (copie du scénario actif)",
                            "en": "Add (copy of active scenario)"},
    "delete_scenario":     {"fr": "Supprimer ce scénario",
                            "en": "Delete this scenario"},

    # Onglets
    "tab_inputs":          {"fr": "Paramètres",        "en": "Inputs"},
    "tab_downpayment":     {"fr": "Mise de fond",      "en": "Down payment"},
    "tab_cf_y1":           {"fr": "Cashflow an 1",     "en": "Cashflow Y1"},
    "tab_cf_yX":           {"fr": "Cashflow an X",     "en": "Cashflow Yn"},
    "tab_study":           {"fr": "Étude pluriannuelle",
                            "en": "Multi-year study"},
    "tab_amort":           {"fr": "Amortissement",     "en": "Amortization"},
    "tab_sens":            {"fr": "Sensibilité",       "en": "Sensitivity"},

    # Inputs tab — entête
    "inputs_title":        {"fr": "Paramètres de l'investissement",
                            "en": "Investment parameters"},
    "inputs_help":         {"fr": "Tous les onglets se mettent à jour "
                                  "automatiquement lorsque vous modifiez "
                                  "une valeur.",
                            "en": "All tabs update automatically when you "
                                  "change a value."},
    "export_json":         {"fr": "Exporter (JSON)", "en": "Export (JSON)"},
    "import_json":         {"fr": "Importer (JSON)", "en": "Import (JSON)"},
    "inputs_updated":      {"fr": "Paramètres mis à jour ✓",
                            "en": "Parameters updated ✓"},
    "milestones_title":    {"fr": "Jalons étude pluriannuelle",
                            "en": "Multi-year study milestones"},
    "milestones_help":     {"fr": "Années séparées par des virgules",
                            "en": "Years separated by commas"},

    # Login
    "login_title":         {"fr": "Connexion — Analyse immobilière",
                            "en": "Sign in — Real-estate analysis"},
    "login_intro":         {"fr": "Connectez-vous pour accéder au "
                                  "tableau de bord.",
                            "en": "Sign in to access the dashboard."},
    "email":               {"fr": "Email",          "en": "Email"},
    "password":            {"fr": "Mot de passe",   "en": "Password"},
    "sign_in":             {"fr": "Se connecter",   "en": "Sign in"},
    "invalid_credentials": {"fr": "Email ou mot de passe invalide.",
                            "en": "Invalid email or password."},

    # Sections du formulaire
    "sec_property":        {"fr": "Propriété",         "en": "Property"},
    "sec_mortgage":        {"fr": "Hypothèque",        "en": "Mortgage"},
    "sec_rental":          {"fr": "Location",          "en": "Rental"},
    "sec_investors":       {"fr": "Investisseurs",     "en": "Investors"},
    "sec_initial_costs":   {"fr": "Charges initiales d'achat ($)",
                            "en": "Initial purchase costs ($)"},
    "sec_indexation":      {"fr": "Taux d'indexation (% / an)",
                            "en": "Indexation rates (% / yr)"},
    "sec_sale_costs":      {"fr": "Frais de vente",    "en": "Sale costs"},
    "sec_taxes":           {"fr": "Impôts (%)",        "en": "Taxes (%)"},
    "sec_analysis":        {"fr": "Analyse",           "en": "Analysis"},

    # Champs
    "f_prix_immobilier":   {"fr": "Prix immobilier ($)",
                            "en": "Purchase price ($)"},
    "f_prix_marche":       {"fr": "Prix marché ($)",
                            "en": "Market price ($)"},
    "f_est_condo":         {"fr": "Type : condo ?",
                            "en": "Type: condo?"},
    "f_mise_de_fond_pct":  {"fr": "Mise de fond (%)",
                            "en": "Down payment (%)"},
    "f_duree_hypotheque":  {"fr": "Durée (ans)",
                            "en": "Term (years)"},
    "f_taux_interet":      {"fr": "Taux d'intérêt (%)",
                            "en": "Interest rate (%)"},
    "f_loyer_annuel":      {"fr": "Loyer annuel total ($)",
                            "en": "Total annual rent ($)"},
    "f_taux_vacance":      {"fr": "Taux de vacance (%)",
                            "en": "Vacancy rate (%)"},
    "f_appreciation":      {"fr": "Appréciation / an (%)",
                            "en": "Appreciation / yr (%)"},
    "f_frais_condo":       {"fr": "Frais de condo / mois ($)",
                            "en": "Condo fees / month ($)"},
    "f_taxes_mun":         {"fr": "Taxes mun. & scol. / mois ($)",
                            "en": "Municipal & school tax / month ($)"},
    "f_nb_investisseurs":  {"fr": "Nombre d'investisseurs",
                            "en": "Number of investors"},
    "f_inspection":        {"fr": "Inspection", "en": "Inspection"},
    "f_assurance_prime":   {"fr": "Assurance prime initiale",
                            "en": "Initial insurance premium"},
    "f_frais_divers":      {"fr": "Frais", "en": "Fees"},
    "f_autre_travaux":     {"fr": "Autre / Travaux à l'achat",
                            "en": "Other / Purchase-time work"},
    "f_occupation_perso":  {"fr": "Occupation personnelle "
                                  "(crédit taxe bienvenue)",
                            "en": "Personal occupancy "
                                  "(welcome tax credit)"},
    "f_credit_taxe_max":   {"fr": "Crédit max taxe bienvenue ($)",
                            "en": "Max welcome tax credit ($)"},
    "f_taux_loyer":        {"fr": "Loyer", "en": "Rent"},
    "f_taux_taxes":        {"fr": "Taxes", "en": "Taxes"},
    "f_taux_assurance":    {"fr": "Assurance", "en": "Insurance"},
    "f_taux_travaux":      {"fr": "Travaux", "en": "Work"},
    "f_taux_condo":        {"fr": "Frais de condo", "en": "Condo fees"},
    "f_taux_agent":        {"fr": "Frais d'agent (%)",
                            "en": "Agent commission (%)"},
    "f_autres_frais_vente":{"fr": "Autres frais ($)",
                            "en": "Other fees ($)"},
    "f_penalite_banque":   {"fr": "Pénalité banque ($)",
                            "en": "Bank penalty ($)"},
    "f_penalite_avant":    {"fr": "Pénalité avant l'année #",
                            "en": "Penalty before year #"},
    "f_taux_gain_capital": {"fr": "Gain en capital",
                            "en": "Capital gain"},
    "f_taux_marginal":     {"fr": "Taux marginal",
                            "en": "Marginal tax rate"},
    "f_annees_analyse":    {"fr": "Années d'analyse",
                            "en": "Analysis years"},

    # Booléens
    "yes_condo":           {"fr": "Oui (condo)", "en": "Yes (condo)"},
    "no_condo":            {"fr": "Non (maison/plex)",
                            "en": "No (house / plex)"},
    "yes":                 {"fr": "Oui", "en": "Yes"},
    "no":                  {"fr": "Non", "en": "No"},
}


# --------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------- #
def get_lang() -> str:
    """Lit la langue dans le cookie ``lang`` de la requête courante."""
    if has_request_context():
        c = request.cookies.get("lang")
        if c in SUPPORTED:
            return c
    return DEFAULT_LANG


def t(key: str, lang: str | None = None) -> str:
    """Traduction. Retombe sur le français, puis sur la clé brute."""
    lang = lang or get_lang()
    entry = TRANSLATIONS.get(key)
    if not entry:
        return key
    return entry.get(lang) or entry.get(DEFAULT_LANG) or key


def register_callbacks(app):
    """Callback clientside : à chaque changement du sélecteur, on écrit
    un cookie ``lang`` (1 an) puis on recharge la page pour que
    ``build_layout`` soit ré-exécuté avec la nouvelle langue.
    """
    app.clientside_callback(
        """
        function(lang) {
            if (!lang) { return window.dash_clientside.no_update; }
            var current = (document.cookie.match(/(?:^|; )lang=([^;]*)/) || [])[1];
            if (current === lang) { return window.dash_clientside.no_update; }
            document.cookie = "lang=" + lang +
                "; path=/; max-age=" + (60*60*24*365) + "; SameSite=Lax";
            window.location.reload();
            return window.dash_clientside.no_update;
        }
        """,
        # Sortie factice : on cible une propriété inoffensive du dropdown
        # pour satisfaire l'API callback (jamais réellement modifiée).
        Output("lang-select", "className"),
        Input("lang-select", "value"),
        prevent_initial_call=True,
    )


