"""
i18n.py — traduction français / anglais de l'interface.

L'application est écrite en français, mais le dépôt vise des lecteurs
internationaux. Ce module couvre les surfaces que voit un visiteur qui découvre
l'application : navigation, écran d'accueil, import, boutons principaux,
messages d'aide.

Les écrans internes (historique détaillé, analytics) restent en français pour
l'instant : les traduire demanderait de reprendre les 2 000 lignes de `app.py`,
et ce n'est pas ce qui décide un visiteur à rester.

Usage :
    from backend.i18n import traduire
    t = lambda cle: traduire(cle, st.session_state.get("langue", "fr"))
    st.button(t("calculer"))
"""

TRADUCTIONS: dict[str, dict[str, str]] = {
    # ── Navigation ────────────────────────────────────────────────────────────
    "nav_data":      {"fr": "Données",     "en": "Data"},
    "nav_planning":  {"fr": "Planning",    "en": "Schedule"},
    "nav_kpi":       {"fr": "KPI",         "en": "KPIs"},
    "nav_history":   {"fr": "Historique",  "en": "History"},
    "nav_export":    {"fr": "Export",      "en": "Export"},
    "nav_analytics": {"fr": "Analytics",   "en": "Analytics"},

    # ── Écran d'accueil ───────────────────────────────────────────────────────
    "accueil_titre": {
        "fr": "Ordonnancement d'atelier mécanique",
        "en": "Mechanical workshop scheduling",
    },
    "accueil_intro": {
        "fr": "Cette application calcule l'ordre de passage optimal des pièces "
              "sur les machines d'un atelier, en tenant compte des changements "
              "de série et de la disponibilité des techniciens.",
        "en": "This application computes the optimal sequence of parts across "
              "the machines of a workshop, accounting for series changeovers "
              "and technician availability.",
    },
    "accueil_etape1_titre": {"fr": "1 · Importer",   "en": "1 · Import"},
    "accueil_etape1_texte": {
        "fr": "Pars du modèle Excel : gammes, machines possibles, techniciens.",
        "en": "Start from the Excel template: routings, eligible machines, technicians.",
    },
    "accueil_etape2_titre": {"fr": "2 · Optimiser",  "en": "2 · Optimise"},
    "accueil_etape2_texte": {
        "fr": "Le solveur cherche l'ordonnancement qui termine au plus tôt.",
        "en": "The solver looks for the schedule that finishes earliest.",
    },
    "accueil_etape3_titre": {"fr": "3 · Analyser",   "en": "3 · Analyse"},
    "accueil_etape3_texte": {
        "fr": "Gantt par machine, charge, profit et marge par pièce.",
        "en": "Gantt per machine, load, profit and margin per part.",
    },
    "accueil_essayer": {
        "fr": "ESSAYER AVEC UN EXEMPLE",
        "en": "TRY WITH SAMPLE DATA",
    },
    "accueil_essayer_aide": {
        "fr": "Charge un atelier d'exemple et lance l'optimisation — aucun "
              "fichier à préparer.",
        "en": "Loads a sample workshop and runs the optimisation — no file needed.",
    },
    "accueil_ou": {"fr": "ou importe ton propre fichier ci-dessous",
                   "en": "or import your own file below"},

    # ── Import ────────────────────────────────────────────────────────────────
    "import_titre":    {"fr": "DONNÉES DE PLANIFICATION", "en": "PLANNING DATA"},
    "import_sous":     {"fr": "Importe ton fichier Excel puis lance l'optimisation.",
                        "en": "Import your Excel file, then run the optimisation."},
    "import_champ":    {"fr": "Fichier Excel (template_gantt.xlsx)",
                        "en": "Excel file (template_gantt.xlsx)"},
    "import_aide":     {"fr": "Pars du modèle ci-contre. Les 4 feuilles doivent être complètes.",
                        "en": "Start from the template. All 4 sheets must be filled in."},
    "telecharger_modele": {"fr": "TÉLÉCHARGER LE MODÈLE", "en": "DOWNLOAD TEMPLATE"},
    "telecharger_modele_aide": {
        "fr": "Classeur prêt à remplir, avec un exemple de 3 pièces sur "
              "4 machines et 2 techniciens.",
        "en": "Ready-to-fill workbook with a 3-part, 4-machine, 2-technician example.",
    },
    "calculer":        {"fr": "CALCULER LE PLANNING", "en": "COMPUTE SCHEDULE"},

    # ── Résolution ────────────────────────────────────────────────────────────
    "mode_resolution": {"fr": "MODE DE RÉSOLUTION", "en": "SOLVER MODE"},
    "mode_aide": {
        "fr": "Rapide renvoie une bonne solution en 20 s. Approfondi cherche "
              "jusqu'à 3 minutes et se rapproche de l'optimum. La qualité "
              "obtenue est affichée après le calcul.",
        "en": "Fast returns a good solution in 20 s. Thorough searches up to "
              "3 minutes and gets closer to the optimum. The quality reached "
              "is shown after the run.",
    },
    "occupe": {
        "fr": "Une optimisation est déjà en cours pour un autre visiteur. "
              "L'hébergement gratuit ne dispose que de quelques cœurs : les "
              "calculs sont traités un par un. Réessaie dans une minute.",
        "en": "Another visitor's optimisation is already running. The free "
              "hosting only has a couple of cores, so runs are processed one "
              "at a time. Try again in a minute.",
    },

    # ── Apparence ─────────────────────────────────────────────────────────────
    "theme_clair":  {"fr": "☀ CLAIR",  "en": "☀ LIGHT"},
    "theme_sombre": {"fr": "☾ SOMBRE", "en": "☾ DARK"},
    "theme_aide":   {"fr": "Basculer entre le mode clair et le mode sombre",
                     "en": "Switch between light and dark mode"},
    "langue_aide":  {"fr": "Switch to English", "en": "Passer en français"},
}


def traduire(cle: str, langue: str = "fr") -> str:
    """Renvoie la chaîne traduite ; retombe sur le français puis sur la clé."""
    entree = TRADUCTIONS.get(cle)
    if not entree:
        return cle
    return entree.get(langue) or entree.get("fr") or cle
