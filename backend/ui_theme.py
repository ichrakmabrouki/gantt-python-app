"""
ui_theme.py — palette, habillage « Neo-Tactile » et adaptation mobile.

L'application n'a qu'un seul theme, sombre. Ce n'est pas un renoncement mais
une contrainte du framework : les tableaux `st.dataframe` sont dessines dans un
canvas qui suit le theme declare dans `.streamlit/config.toml`, choisi au
demarrage du serveur et identique pour toute la session. Aucune feuille de
style ne peut les repeindre. Proposer une bascule clair / sombre revenait donc
a promettre un mode clair ou les tableaux restaient noirs — et un mode sombre
ou ils restaient blancs. Un theme unique, entierement maitrise, vaut mieux que
deux themes a moitie tenus.

Le style reprend les codes de l'interface dite « neo-tactile » : surfaces en
verre depoli posees sur un fond profond, epaisseur donnee par l'ombre plutot
que par le trait, et un halo orange reserve a ce qui est actif. La regle de
lisibilite prime : le verre habille les panneaux et les cartes, jamais le fond
direct d'un paragraphe ni celui d'un tableau.
"""

# ── Couleurs ──────────────────────────────────────────────────────────────────
# Les valeurs sont pleines (pas de transparence) : elles servent aussi aux
# graphiques Plotly, qui ne savent pas lire une variable CSS.
ORANGE        = "#ff7a1a"   # orange de marque, aplats et halos
ORANGE_CLAIR  = "#ff9a4d"   # survol
ORANGE_PROFOND = "#e0620c"  # appui

PALETTE: dict[str, str] = {
    "fond":         "#070a10",
    "fond2":        "#0b0f17",
    "surface":      "#121724",
    "surface2":     "#1a2130",
    "bordure":      "#2a3346",
    "texteFort":    "#f4f7fb",
    "texte":        "#c6cede",
    "texteFaible":  "#7f8aa0",
    "accent":       ORANGE,
    "accent2":      ORANGE_CLAIR,
    "accent3":      ORANGE,
    "succes":       "#35d07f",
    "succesBord":   "#1f8f57",
    "succesFond":   "#0e2419",
    "info":         "#58a6ff",
    "infoBord":     "#2a6fd8",
    "infoFond":     "#0d1b2e",
    "alerte":       "#ffb020",
    "danger":       "#ff5f6d",
    "ombre":        "rgba(0,0,0,0.55)",
    "voile":        "rgba(255,255,255,0.05)",
    "schema":       "dark",
}

# `palette=` de build_gantt attend un dictionnaire ; on garde la meme forme.
PALETTES = {"sombre": PALETTE}


def css_variables() -> str:
    """Bloc `:root` : toute la feuille de style ne lit que ces variables."""
    lignes = "\n".join(
        f"  --{cle}: {valeur};" for cle, valeur in PALETTE.items() if cle != "schema"
    )
    return f"""<style>
:root {{
{lignes}
  --rayon:        18px;
  --rayon-petit:  12px;
  --verre:        linear-gradient(160deg, rgba(255,255,255,0.065),
                                          rgba(255,255,255,0.022));
  --verre-bord:   rgba(255,255,255,0.085);
  --verre-haut:   inset 0 1px 0 rgba(255,255,255,0.075);
  --relief:       0 18px 42px -26px rgba(0,0,0,0.95);
  --halo:         0 0 0 1px rgba(255,122,26,0.30), 0 10px 30px -12px rgba(255,122,26,0.55);
  --police-titre: 'Rajdhani', sans-serif;
  --police-texte: 'Inter', sans-serif;
}}
html {{ color-scheme: dark; }}
</style>"""


# ══════════════════════════════════════════════════════════════════════════════
# CORRECTIF DE CONTRASTE
# ══════════════════════════════════════════════════════════════════════════════
# Streamlit habille lui-meme une partie de l'interface : menus deroulants,
# info-bulles, barre d'outils, fleches des champs numeriques, tableaux. Ces
# elements ne lisent pas le bloc `:root` ci-dessus. On les reprend ici, apres
# la feuille principale, pour qu'aucun texte ni aucune icone ne se retrouve
# sur un fond qui n'a pas ete choisi.
CSS_CORRECTIF = """<style>

/* Fenetres flottantes : listes deroulantes, menus, info-bulles, calendrier */
[data-baseweb="popover"] > div,
[data-baseweb="menu"],
[data-baseweb="tooltip"],
[data-baseweb="calendar"],
[data-baseweb="datepicker"],
[role="listbox"],
[role="tooltip"] {
    background: var(--surface) !important;
    color: var(--texte) !important;
    border: 1px solid var(--verre-bord) !important;
    border-radius: var(--rayon-petit) !important;
    box-shadow: var(--relief) !important;
}
[data-baseweb="menu"] li,
[role="option"] {
    background: transparent !important;
    color: var(--texte) !important;
}
[data-baseweb="menu"] li:hover,
[role="option"]:hover,
[role="option"][aria-selected="true"] {
    background: var(--surface2) !important;
    color: var(--accent) !important;
}

/* Barre d'outils et en-tete de Streamlit */
[data-testid="stHeader"],
[data-testid="stToolbar"],
[data-testid="stDecoration"] { background: transparent !important; }
[data-testid="stToolbar"] button,
[data-testid="stMainMenu"] button { color: var(--texteFaible) !important; }

/* Les icones de Streamlit suivent la couleur de leur texte. On ne force NI
   le remplissage NI le contour : le point d'interrogation des info-bulles,
   dessine en creux, se remplissait alors entierement et devenait une pastille. */
button svg, summary svg, label svg,
[data-testid="stToolbar"] svg,
[data-baseweb="select"] svg,
[data-testid="stExpander"] svg,
[data-testid="stNumberInputStepUp"] svg,
[data-testid="stNumberInputStepDown"] svg {
    color: inherit !important;
}
[data-testid="stTooltipHoverTarget"] svg { opacity: 0.55; }
.stButton > button *,
[data-testid="stFormSubmitButton"] > button *,
.stDownloadButton > button * { color: inherit !important; }

[data-testid="stNumberInputStepUp"],
[data-testid="stNumberInputStepDown"] {
    background: var(--surface2) !important;
    color: var(--texte) !important;
    border-color: var(--bordure) !important;
}

/* Tableaux : la grille est dessinee dans un canvas et se colore par ses
   propres variables. */
[data-testid="stDataFrame"],
[data-testid="stDataFrameResizable"],
[data-testid="stDataFrameResizable"] > div {
    --gdg-bg-cell: var(--surface);
    --gdg-bg-cell-medium: var(--surface2);
    --gdg-bg-header: var(--surface2);
    --gdg-bg-header-hovered: var(--surface2);
    --gdg-bg-header-has-focus: var(--surface2);
    --gdg-text-dark: var(--texte);
    --gdg-text-medium: var(--texte);
    --gdg-text-light: var(--texteFaible);
    --gdg-text-header: var(--texteFaible);
    --gdg-text-header-selected: var(--accent);
    --gdg-border-color: var(--bordure);
    --gdg-horizontal-border-color: var(--bordure);
    --gdg-accent-color: var(--accent);
    --gdg-accent-fg: #140a02;
    --gdg-accent-light: rgba(255,122,26,0.16);
    --gdg-bg-bubble: var(--surface2);
    --gdg-bg-bubble-selected: var(--surface2);
    --gdg-bg-search-result: rgba(255,122,26,0.16);
    --gdg-fg-icon-header: var(--texteFaible);
}

pre, code, [data-testid="stCode"] {
    background: var(--surface2) !important;
    color: var(--texte) !important;
    border-radius: var(--rayon-petit) !important;
}

/* Barre d'outils des graphiques Plotly */
.modebar, .modebar-group { background: transparent !important; }
.modebar-btn path { fill: var(--texteFaible) !important; }
.modebar-btn:hover path { fill: var(--accent) !important; }

[data-testid="stCheckbox"] label span,
[data-testid="stRadio"] label span { color: var(--texte) !important; }

/* Badge de session : orange, pas vert */
.status-badge-accent {
    background: rgba(255,122,26,0.10) !important;
    border-color: rgba(255,122,26,0.35) !important;
    color: var(--accent) !important;
}

/* Icones SVG en ligne */
.ico { opacity: 0.95; }
</style>"""


# ══════════════════════════════════════════════════════════════════════════════
# HABILLAGE NEO-TACTILE
# ══════════════════════════════════════════════════════════════════════════════
# Injecte en dernier. Trois principes :
#   1. la profondeur vient de l'ombre, pas du trait ;
#   2. le verre depoli habille les panneaux, jamais le fond d'un texte dense ;
#   3. l'orange ne sert qu'a ce qui est actif — sinon il ne veut plus rien dire.
CSS_NEO = """<style>

/* ── Fond : deux halos tres larges, pour que la page ne soit pas un aplat ── */
[data-testid="stAppViewContainer"] {
    background:
        radial-gradient(1100px 620px at 12% -12%, rgba(255,122,26,0.10), transparent 62%),
        radial-gradient(900px 520px at 102% 4%, rgba(88,166,255,0.07), transparent 58%),
        var(--fond) !important;
}
.block-container { padding-top: 2.2rem !important; }

/* ── Barre laterale en verre ─────────────────────────────────────────────── */
[data-testid="stSidebar"] > div:first-child,
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, rgba(255,255,255,0.055),
                                        rgba(255,255,255,0.015)) !important;
    backdrop-filter: blur(22px) saturate(140%);
    -webkit-backdrop-filter: blur(22px) saturate(140%);
    border-right: 1px solid var(--verre-bord) !important;
}

/* ── Panneaux ────────────────────────────────────────────────────────────── */
/* Le cadre est reserve a ce qui delimite vraiment quelque chose : l'en-tete
   de page, un formulaire, un bloc depliable, une carte de telechargement.
   Une premiere version encadrait CHAQUE bloc de la page, chiffres compris :
   l'oeil ne savait plus ou regarder, puisque tout avait le meme poids. */
[data-testid="stExpander"],
[data-testid="stForm"],
[data-testid="stFileUploaderDropzone"],
[data-testid="stFileUploader"] section,
.dl-card,
.accueil-bloc,
.header-banner {
    background: var(--verre) !important;
    border: 1px solid var(--verre-bord) !important;
    border-radius: var(--rayon) !important;
    backdrop-filter: blur(16px) saturate(130%);
    -webkit-backdrop-filter: blur(16px) saturate(130%);
    box-shadow: var(--relief), var(--verre-haut) !important;
}

/* Les chiffres ne sont pas dans des boites : ils sont poses sur la page, et
   separes par un simple filet. C'est plus calme, et ils se lisent mieux. */
[data-testid="stMetric"] {
    background: transparent !important;
    border: 0 !important;
    box-shadow: none !important;
    padding: 4px 20px 4px 0 !important;
}
[data-testid="stHorizontalBlock"] [data-testid="stMetric"] {
    border-left: 1px solid var(--verre-bord) !important;
    padding-left: 20px !important;
}
[data-testid="stHorizontalBlock"] > div:first-child [data-testid="stMetric"] {
    border-left: 0 !important;
    padding-left: 0 !important;
}

/* Les messages : un filet a gauche, pas un cadre complet. */
[data-testid="stAlert"] {
    background: rgba(255,255,255,0.03) !important;
    border: 0 !important;
    border-left: 3px solid var(--accent) !important;
    border-radius: 0 var(--rayon-petit) var(--rayon-petit) 0 !important;
    box-shadow: none !important;
}

.dl-card { transition: all .18s ease; }
.dl-card:hover {
    transform: translateY(-2px);
    border-color: rgba(255,122,26,0.28) !important;
}

/* ── Boutons ─────────────────────────────────────────────────────────────── */
.stButton > button,
[data-testid="stFormSubmitButton"] > button {
    background: linear-gradient(180deg, var(--accent2), var(--accent)) !important;
    border: 1px solid rgba(255,255,255,0.20) !important;
    color: #150900 !important;
    border-radius: var(--rayon-petit) !important;
    font-weight: 700 !important;
    box-shadow: 0 12px 26px -14px rgba(255,122,26,0.95),
                inset 0 1px 0 rgba(255,255,255,0.40) !important;
    transition: transform .15s ease, box-shadow .15s ease, filter .15s ease;
}
.stButton > button:hover,
[data-testid="stFormSubmitButton"] > button:hover {
    transform: translateY(-1px);
    filter: brightness(1.06);
    box-shadow: 0 16px 34px -14px rgba(255,122,26,1),
                inset 0 1px 0 rgba(255,255,255,0.45) !important;
}
.stButton > button:active,
[data-testid="stFormSubmitButton"] > button:active {
    transform: translateY(0);
    filter: brightness(0.95);
}

/* Bouton secondaire : verre, pas d'orange — il ne doit pas concurrencer
   l'action principale. */
.stDownloadButton > button {
    background: rgba(255,255,255,0.05) !important;
    border: 1px solid var(--verre-bord) !important;
    color: var(--texte) !important;
    border-radius: var(--rayon-petit) !important;
    box-shadow: var(--verre-haut) !important;
}
.stDownloadButton > button:hover {
    background: rgba(255,255,255,0.09) !important;
    border-color: rgba(255,122,26,0.40) !important;
    color: var(--accent) !important;
}

/* ── Navigation laterale ─────────────────────────────────────────────────── */
/* Page courante = bouton "primary" ; les autres restent en retrait. */
[data-testid="stSidebar"] .stButton > button {
    background: transparent !important;
    border: 1px solid transparent !important;
    color: var(--texteFaible) !important;
    justify-content: flex-start !important;
    text-align: left !important;
    font-weight: 600 !important;
    letter-spacing: 0.04em !important;
    box-shadow: none !important;
    border-radius: var(--rayon-petit) !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(255,255,255,0.06) !important;
    color: var(--texteFort) !important;
    transform: none;
    filter: none;
}
/* La specificite doit depasser celle de la regle generique ci-dessus, sans
   quoi le bouton de la page courante resterait transparent. */
[data-testid="stSidebar"] .stButton > button[data-testid="stBaseButton-primary"],
[data-testid="stSidebar"] .stButton > button[kind="primary"] {
    background: rgba(255,122,26,0.13) !important;
    border: 1px solid rgba(255,122,26,0.38) !important;
    color: var(--accent) !important;
    box-shadow: inset 3px 0 0 var(--accent), 0 8px 22px -16px rgba(255,122,26,0.9) !important;
}

/* ── Champs ──────────────────────────────────────────────────────────────── */
.stNumberInput > div > div > input,
.stTextInput > div > div > input,
[data-baseweb="input"],
[data-baseweb="base-input"],
[data-baseweb="select"] > div,
textarea, input {
    background: rgba(255,255,255,0.045) !important;
    border: 1px solid var(--verre-bord) !important;
    border-radius: var(--rayon-petit) !important;
    color: var(--texteFort) !important;
}
[data-baseweb="input"]:focus-within,
[data-baseweb="select"] > div:focus-within,
input:focus, textarea:focus {
    border-color: rgba(255,122,26,0.55) !important;
    box-shadow: 0 0 0 3px rgba(255,122,26,0.14) !important;
}

/* ── Interrupteurs, cases et curseurs ────────────────────────────────────── */
[data-baseweb="checkbox"] [role="checkbox"][aria-checked="true"],
[data-testid="stCheckbox"] [aria-checked="true"],
[data-baseweb="checkbox"] input:checked + div {
    background: var(--accent) !important;
    border-color: var(--accent) !important;
    box-shadow: 0 0 14px -2px rgba(255,122,26,0.75) !important;
}
[data-testid="stSlider"] [role="slider"] {
    background: var(--accent) !important;
    border: 2px solid rgba(255,255,255,0.85) !important;
    box-shadow: 0 0 16px -2px rgba(255,122,26,0.9) !important;
}
[data-testid="stSlider"] [data-baseweb="slider"] div[style*="background"] {
    border-radius: 999px !important;
}

/* ── Onglets ─────────────────────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
    gap: 6px !important;
    background: rgba(255,255,255,0.035) !important;
    border: 1px solid var(--verre-bord) !important;
    border-radius: 999px !important;
    padding: 5px !important;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 999px !important;
    padding: 6px 16px !important;
    color: var(--texteFaible) !important;
    font-weight: 600 !important;
}
.stTabs [data-baseweb="tab"]:hover { color: var(--texteFort) !important; }
.stTabs [data-baseweb="tab"][aria-selected="true"] {
    background: rgba(255,122,26,0.14) !important;
    color: var(--accent) !important;
    box-shadow: inset 0 0 0 1px rgba(255,122,26,0.35) !important;
}
.stTabs [data-baseweb="tab-highlight"],
.stTabs [data-baseweb="tab-border"] { display: none !important; }

/* ── En-tete de page ─────────────────────────────────────────────────────── */
.header-banner {
    padding: 18px 22px !important;
    margin-bottom: 18px !important;
}
.header-title {
    background: linear-gradient(92deg, var(--texteFort) 15%, var(--accent) 95%);
    -webkit-background-clip: text;
    background-clip: text;
    -webkit-text-fill-color: transparent;
}
.masthead-accent {
    height: 2px !important;
    background: linear-gradient(90deg, var(--accent), rgba(255,122,26,0)) !important;
    border-radius: 2px;
}
.divline {
    height: 1px !important;
    background: linear-gradient(90deg, var(--verre-bord), transparent) !important;
}

/* ── Graphiques ──────────────────────────────────────────────────────────── */
/* Plotly dessine deja son propre fond : un cadre par-dessus ferait double. */
.stPlotlyChart, [data-testid="stPlotlyChart"] {
    background: transparent !important;
    border: 0 !important;
    box-shadow: none !important;
    padding: 0 !important;
}
.js-plotly-plot .plot-container { border-radius: var(--rayon); overflow: hidden; }

/* ── Ecriture ────────────────────────────────────────────────────────────── */
/* L'interface etait ecrite trop petit : titres de section a 11 px, libelles de
   chiffres a 10 px, messages a 12 px, le tout en majuscules espacees de 3 px.
   Les majuscules et l'interlettrage large font perdre a l'oeil les reperes de
   forme des mots ; a cette taille, la lecture devient un effort. Tout est
   remonte d'un cran, et l'interlettrage ramene a une valeur raisonnable. */

html, body, [data-testid="stAppViewContainer"] { font-size: 16px !important; }

[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] li,
[data-testid="stText"] {
    font-size: 0.95rem !important;
    line-height: 1.65 !important;
    color: var(--texte) !important;
}

/* Titre de la fenetre */
.header-title {
    font-size: 2.1rem !important;
    letter-spacing: 0.06em !important;
    line-height: 1.15 !important;
}
.masthead-eyebrow { font-size: 0.82rem !important; letter-spacing: 0.18em !important; }
.header-page-active { font-size: 1rem !important; letter-spacing: 0.06em !important; }
.header-date { font-size: 0.82rem !important; }

/* Titre de la page et de ses sections */
.page-title {
    font-size: 1.5rem !important;
    letter-spacing: 0.06em !important;
    color: var(--accent) !important;
}
.page-subtitle { font-size: 0.95rem !important; line-height: 1.6 !important; }
.section-title {
    color: var(--texteFort) !important;
    font-size: 1.05rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.05em !important;
    padding-bottom: 10px !important;
    margin-bottom: 14px !important;
    border-bottom: 1px solid var(--verre-bord) !important;
}
h1 { font-size: 1.85rem !important; }
h2 { font-size: 1.45rem !important; }
h3 { font-size: 1.15rem !important; }

/* Chiffres */
[data-testid="stMetricValue"] {
    color: var(--texteFort) !important;
    font-size: 2rem !important;
    font-weight: 700 !important;
    line-height: 1.2 !important;
}
[data-testid="stMetricLabel"],
[data-testid="stMetricLabel"] p {
    color: var(--texteFaible) !important;
    font-size: 0.8rem !important;
    letter-spacing: 0.07em !important;
    font-weight: 600 !important;
}
/* Hauteur reservee au libelle : sans elle, un libelle qui passe sur deux
   lignes decale son chiffre vers le bas et la rangee n'est plus alignee. */
[data-testid="stMetricLabel"] {
    min-height: 2.6em !important;
    align-items: flex-start !important;
}
[data-testid="stMetricDelta"] { font-size: 0.9rem !important; }

/* Libelles de champs, boutons, onglets, messages */
label, [data-testid="stWidgetLabel"] p {
    font-size: 0.82rem !important;
    letter-spacing: 0.05em !important;
}
.stButton > button, .stDownloadButton > button,
[data-testid="stFormSubmitButton"] > button {
    font-size: 0.85rem !important;
    letter-spacing: 0.05em !important;
}
[data-testid="stSidebar"] .stButton > button { font-size: 0.9rem !important; }
.stTabs [data-baseweb="tab"] { font-size: 0.85rem !important; letter-spacing: 0.05em !important; }
[data-testid="stAlert"] p { font-size: 0.92rem !important; line-height: 1.6 !important; }
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p {
    font-size: 0.88rem !important;
    line-height: 1.65 !important;
    color: var(--texteFaible) !important;
}
.status-badge { font-size: 0.8rem !important; }
.sidebar-section-title { font-size: 0.78rem !important; letter-spacing: 0.14em !important; }

hr { border-color: var(--verre-bord) !important; }

/* Mouvement retire pour qui l'a demande au niveau du systeme. */
@media (prefers-reduced-motion: reduce) {
    * { transition: none !important; animation: none !important; }
    [data-testid="stMetric"]:hover, .dl-card:hover,
    .stButton > button:hover { transform: none !important; }
}
</style>"""


# ══════════════════════════════════════════════════════════════════════════════
# ADAPTATION MOBILE
# ══════════════════════════════════════════════════════════════════════════════
# Streamlit ne replie pas les colonnes tout seul : sur un telephone, un
# st.columns([3,1,1]) reste sur une ligne et chaque colonne fait 80 pixels.
# On force l'empilement, on reduit les marges, et on rend les tableaux et le
# Gantt defilables horizontalement plutot que de laisser la page deborder.
CSS_MOBILE = """<style>
@media (max-width: 820px) {

  [data-testid="stHorizontalBlock"] {
      flex-direction: column !important;
      gap: 10px !important;
  }
  [data-testid="stHorizontalBlock"] > div,
  [data-testid="column"] {
      width: 100% !important;
      flex: 1 1 100% !important;
      min-width: 0 !important;
  }

  .block-container {
      padding: 12px 14px 60px 14px !important;
      max-width: 100% !important;
  }

  .header-title      { font-size: 1.25rem !important; letter-spacing: 3px !important; }
  .header-banner     { flex-direction: column !important; align-items: flex-start !important;
                       gap: 10px !important; padding: 14px 16px !important; }
  .header-date       { text-align: left !important; }
  .masthead-eyebrow  { font-size: 0.95rem !important; letter-spacing: 3px !important; }
  .page-title        { font-size: 1rem !important; letter-spacing: 2px !important; }
  h1 { font-size: 1.4rem !important; }
  h2 { font-size: 1.15rem !important; }
  h3 { font-size: 1rem !important; }

  /* Zone tactile : 44 px, la valeur recommandee */
  .stButton > button,
  .stDownloadButton > button {
      width: 100% !important;
      min-height: 44px !important;
      padding: 10px 16px !important;
  }
  [data-baseweb="input"] input,
  [data-baseweb="select"] > div {
      min-height: 44px !important;
      font-size: 16px !important;   /* < 16px declenche le zoom auto sur iOS */
  }

  [data-testid="stDataFrame"],
  [data-testid="stTable"],
  .js-plotly-plot,
  .stPlotlyChart {
      overflow-x: auto !important;
      max-width: 100% !important;
  }
  .js-plotly-plot .plotly { min-width: 560px !important; }

  [data-testid="stMetric"]      { padding: 12px 14px !important; }
  [data-testid="stMetricValue"] { font-size: 1.3rem !important; }

  .stTabs [data-baseweb="tab-list"] { overflow-x: auto !important; flex-wrap: nowrap !important; }
  .stTabs [data-baseweb="tab"]      { min-width: max-content !important; }

  [data-testid="stSidebar"] { min-width: 78vw !important; }

  /* Le verre depoli coute cher en calcul sur telephone : on l'allege. */
  [data-testid="stMetric"], [data-testid="stExpander"], [data-testid="stForm"],
  .dl-card, .accueil-bloc, .header-banner {
      backdrop-filter: none !important;
      -webkit-backdrop-filter: none !important;
      background: var(--surface) !important;
  }
}

@media (max-width: 480px) {
  .header-title { font-size: 1.05rem !important; letter-spacing: 2px !important; }
  .block-container { padding: 10px 10px 60px 10px !important; }
  .js-plotly-plot .plotly { min-width: 480px !important; }
}

[data-testid="stAppViewContainer"] { overflow-x: hidden !important; }
</style>"""


BANNIERE_MOBILE = """
<div class="banniere-mobile">
  <strong>Écran étroit détecté.</strong>
  L'application reste utilisable, mais le diagramme de Gantt se lit beaucoup
  mieux sur un écran large. Sur téléphone, fais défiler le graphique
  horizontalement.
</div>
<style>
.banniere-mobile {
    display: none;
    background: var(--surface2);
    border: 1px solid var(--bordure);
    border-left: 3px solid var(--accent);
    border-radius: 12px;
    padding: 10px 14px;
    margin-bottom: 14px;
    font-size: 0.78rem !important;
    color: var(--texteFaible) !important;
    line-height: 1.5;
}
.banniere-mobile strong { color: var(--accent) !important; }
@media (max-width: 820px) { .banniere-mobile { display: block; } }
</style>"""
