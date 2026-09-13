"""
ui_theme.py — palettes clair / sombre et adaptation mobile.

L'application était entièrement figée en sombre : quarante couleurs écrites en
dur dans une feuille de style de 700 lignes. Ce module extrait ces couleurs
dans des variables CSS, ce qui permet de basculer tout l'habillage en changeant
seulement le bloc `:root`.

L'orange de la marque (#ff6b00) est identique dans les deux modes. Ce qui
change, ce sont les fonds, les textes et les bordures.
"""

ORANGE = "#ff6b00"
ORANGE_CLAIR = "#ee8a32"
ORANGE_SOMBRE = "#d87722"

PALETTES = {
    "sombre": {
        "fond":         "#0d1117",
        "fond2":        "#0b1014",
        "surface":      "#161b22",
        "surface2":     "#1c2333",
        "bordure":      "#30363d",
        "texteFort":    "#f3f4f6",
        "texte":        "#c9d1d9",
        "texteFaible":  "#8b949e",
        "accent":       ORANGE,
        "accent2":      ORANGE_CLAIR,
        "accent3":      ORANGE_SOMBRE,
        "succes":       "#3fb950",
        "succesBord":   "#238636",
        "succesFond":   "#0f2a1a",
        "info":         "#58a6ff",
        "infoBord":     "#1f6feb",
        "infoFond":     "#0d1b2a",
        "alerte":       "#d6a536",
        "danger":       "#d85b5b",
        "ombre":        "rgba(0,0,0,0.35)",
        "voile":        "rgba(255,255,255,0.03)",
        "schema":       "dark",
    },
    "clair": {
        "fond":         "#ffffff",
        "fond2":        "#f6f7f9",
        "surface":      "#ffffff",
        "surface2":     "#f1f3f5",
        "bordure":      "#dfe3e8",
        "texteFort":    "#111827",
        "texte":        "#374151",
        "texteFaible":  "#6b7280",
        "accent":       ORANGE,
        "accent2":      ORANGE_SOMBRE,
        "accent3":      "#b45309",
        "succes":       "#128a4d",
        "succesBord":   "#16a34a",
        "succesFond":   "#e8f6ee",
        "info":         "#1d4ed8",
        "infoBord":     "#2563eb",
        "infoFond":     "#eaf1fd",
        "alerte":       "#a16207",
        "danger":       "#b91c1c",
        "ombre":        "rgba(15,23,42,0.10)",
        "voile":        "rgba(15,23,42,0.03)",
        "schema":       "light",
    },
}


def css_variables(mode: str = "sombre") -> str:
    """Bloc `:root` correspondant au mode demandé."""
    p = PALETTES.get(mode, PALETTES["sombre"])
    lignes = "\n".join(
        f"  --{cle}: {valeur};" for cle, valeur in p.items() if cle != "schema"
    )
    return f"""<style>
:root {{
{lignes}
  --police-titre: 'Rajdhani', sans-serif;
  --police-texte: 'Inter', sans-serif;
}}
html {{ color-scheme: {p['schema']}; }}
</style>"""


# ══════════════════════════════════════════════════════════════════════════════
# ADAPTATION MOBILE
# ══════════════════════════════════════════════════════════════════════════════
# Streamlit ne replie pas les colonnes tout seul : sur un téléphone, un
# st.columns([3,1,1]) reste sur une ligne et chaque colonne fait 80 pixels.
# On force l'empilement, on réduit les marges, et on rend les tableaux et le
# Gantt défilables horizontalement plutôt que de laisser la page déborder.
CSS_MOBILE = """<style>
@media (max-width: 820px) {

  /* Colonnes empilées */
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

  /* Marges rendues au contenu */
  .block-container {
      padding: 12px 14px 60px 14px !important;
      max-width: 100% !important;
  }

  /* Titres ramenés à une taille lisible sur petit écran */
  .header-title      { font-size: 1.25rem !important; letter-spacing: 3px !important; }
  .header-banner     { flex-direction: column !important; align-items: flex-start !important;
                       gap: 10px !important; padding: 14px 16px !important; }
  .header-date       { text-align: left !important; }
  .masthead-eyebrow  { font-size: 0.95rem !important; letter-spacing: 3px !important; }
  .page-title        { font-size: 1rem !important; letter-spacing: 2px !important; }
  h1 { font-size: 1.4rem !important; }
  h2 { font-size: 1.15rem !important; }
  h3 { font-size: 1rem !important; }

  /* Boutons pleine largeur et zone tactile suffisante (44 px recommandés) */
  .stButton > button,
  .stDownloadButton > button {
      width: 100% !important;
      min-height: 44px !important;
      padding: 10px 16px !important;
  }
  [data-baseweb="input"] input,
  [data-baseweb="select"] > div {
      min-height: 44px !important;
      font-size: 16px !important;   /* < 16px déclenche le zoom auto sur iOS */
  }

  /* Tableaux et graphiques : défilement horizontal au lieu du débordement */
  [data-testid="stDataFrame"],
  [data-testid="stTable"],
  .js-plotly-plot,
  .stPlotlyChart {
      overflow-x: auto !important;
      max-width: 100% !important;
  }
  .js-plotly-plot .plotly { min-width: 560px !important; }

  /* Métriques en colonne, plus compactes */
  [data-testid="stMetric"]      { padding: 10px 12px !important; }
  [data-testid="stMetricValue"] { font-size: 1.3rem !important; }

  /* La sidebar prend presque tout l'écran une fois ouverte */
  [data-testid="stSidebar"] { min-width: 78vw !important; }
}

@media (max-width: 480px) {
  .header-title { font-size: 1.05rem !important; letter-spacing: 2px !important; }
  .block-container { padding: 10px 10px 60px 10px !important; }
  .js-plotly-plot .plotly { min-width: 480px !important; }
}

/* Le Gantt reste lisible : on ne laisse jamais la page déborder */
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
    border-radius: 4px;
    padding: 10px 14px;
    margin-bottom: 14px;
    font-size: 0.78rem !important;
    color: var(--texteFaible) !important;
    line-height: 1.5;
}
.banniere-mobile strong { color: var(--accent) !important; }
@media (max-width: 820px) { .banniere-mobile { display: block; } }
</style>"""
