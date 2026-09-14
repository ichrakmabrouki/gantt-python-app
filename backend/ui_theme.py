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
# ══════════════════════════════════════════════════════════════════════════════
# RESEAU ANIME DU HAUT DE PAGE
# ══════════════════════════════════════════════════════════════════════════════
# La bande qui surmonte le titre etait vide. On y pose un reseau de noeuds
# relies — une image juste : un atelier est un reseau de machines entre
# lesquelles circulent des pieces.
#
# Le motif est construit en DEUX COUCHES qui derivent a des vitesses et dans
# des sens differents. C'est ce qui donne le mouvement sans disloquer la
# figure : chaque couche se deplace d'un bloc, noeuds et liens ensemble, donc
# aucun lien ne se detache jamais de ses extremites. La couche lointaine est
# plus petite, plus pale et plus lente ; l'ecart entre les deux cree une
# impression de profondeur.
#
# S'y ajoutent trois mouvements qui, eux, ne deplacent rien :
#   - des impulsions lumineuses qui parcourent les liens d'un bout a l'autre ;
#   - un battement lent des noeuds ;
#   - des ondes qui s'echappent des noeuds les plus connectes.
#
# Le motif est servi en `background-image`. Un SVG appele ainsi ne peut pas
# executer de script — ce que Streamlit interdirait de toute facon — mais ses
# animations CSS fonctionnent. C'est aussi ce qui permet de respecter le
# reglage systeme « reduire les animations », via une media query ecrite a
# l'interieur du motif.

import base64
import math
import random


def _couche(alea: random.Random, largeur: int, hauteur: int,
            nb_noeuds: int, colonnes: int, portee: float,
            max_liens: int) -> tuple[list, list]:
    """Points repartis sur une grille bruitee, et liens courts entre eux.

    La grille evite deux defauts du tirage purement aleatoire : les paquets de
    points colles et les grands vides. Le bruit evite l'effet quadrillage.
    """
    rangees = max(1, round(nb_noeuds / colonnes))
    points = []
    for i in range(nb_noeuds):
        col, rang = i % colonnes, (i // colonnes) % rangees
        x = (col + 0.5) * largeur / colonnes + alea.uniform(-0.46, 0.46) * largeur / colonnes
        y = (rang + 0.5) * hauteur / rangees + alea.uniform(-0.42, 0.42) * hauteur / rangees
        points.append((round(min(max(x, 6), largeur - 6), 1),
                       round(min(max(y, 6), hauteur - 6), 1)))

    liens = [(i, j)
             for i, a in enumerate(points)
             for j, b in enumerate(points[i + 1:], start=i + 1)
             if math.dist(a, b) < portee]
    alea.shuffle(liens)
    return points, liens[:max_liens]


def _motif_reseau(largeur: int = 1800, hauteur: int = 170, graine: int = 11) -> str:
    """SVG du reseau anime. Graine fixe : le motif ne change pas d'une
    execution a l'autre."""
    alea = random.Random(graine)

    # Couche proche : grosse, nette, rapide. Couche lointaine : fine et pale.
    proche_pts, proche_liens = _couche(alea, largeur, hauteur, 40, 10, 205, 62)
    loin_pts,   loin_liens   = _couche(alea, largeur, hauteur, 30, 8,  245, 40)

    def dessiner(points, liens, prefixe, rayons):
        traits = "".join(
            f'<line class="{prefixe}l v{n % 5}" x1="{points[i][0]}" y1="{points[i][1]}" '
            f'x2="{points[j][0]}" y2="{points[j][1]}"/>'
            for n, (i, j) in enumerate(liens)
        )
        ronds = "".join(
            f'<circle class="{prefixe}n b{n % 6}" cx="{x}" cy="{y}" '
            f'r="{rayons[n % len(rayons)]}"/>'
            for n, (x, y) in enumerate(points)
        )
        return traits + ronds

    # Noeuds les plus connectes : ils emettent une onde.
    degres = {}
    for (i, j) in proche_liens:
        degres[i] = degres.get(i, 0) + 1
        degres[j] = degres.get(j, 0) + 1
    concentrateurs = sorted(degres, key=lambda k: -degres[k])[:4]
    ondes = "".join(
        f'<circle class="o" cx="{proche_pts[i][0]}" cy="{proche_pts[i][1]}" '
        f'r="3" style="animation-delay:{k * 2.6:.1f}s"/>'
        for k, i in enumerate(concentrateurs)
    )

    # Impulsions : des points qui parcourent un lien d'un bout a l'autre.
    impulsions = ""
    for k, (i, j) in enumerate(proche_liens[:14]):
        (x1, y1), (x2, y2) = proche_pts[i], proche_pts[j]
        if k % 2:                      # une fois sur deux, dans l'autre sens
            (x1, y1), (x2, y2) = (x2, y2), (x1, y1)
        impulsions += (
            f'<circle class="p" r="2.5" cx="0" cy="0" '
            f'style="animation-delay:{k * 0.85:.2f}s;'
            f'--x1:{x1}px;--y1:{y1}px;--x2:{x2}px;--y2:{y2}px"/>'
        )

    style = f"""
    .Pl {{ stroke:{ORANGE}; stroke-width:1.15; stroke-opacity:.34;
           stroke-dasharray:6 10; animation:file 7s linear infinite; }}
    .Ll {{ stroke:{ORANGE}; stroke-width:.8; stroke-opacity:.15;
           stroke-dasharray:4 12; animation:file 13s linear infinite; }}
    .v1 {{ animation-duration:9s;  animation-delay:-2s; }}
    .v2 {{ animation-duration:11s; animation-delay:-4s; }}
    .v3 {{ animation-duration:8s;  animation-delay:-6s; }}
    .v4 {{ animation-duration:15s; animation-delay:-9s; }}
    .Pn {{ fill:{ORANGE}; animation:battement 5s ease-in-out infinite; }}
    .Ln {{ fill:{ORANGE}; opacity:.3; animation:battement 8s ease-in-out infinite; }}
    .b1 {{ animation-delay:-.8s; }} .b2 {{ animation-delay:-1.7s; }}
    .b3 {{ animation-delay:-2.6s; }} .b4 {{ animation-delay:-3.5s; }}
    .b5 {{ animation-delay:-4.4s; }}
    .p  {{ fill:{ORANGE_CLAIR}; animation:trajet 7s ease-in-out infinite; }}
    .o  {{ fill:none; stroke:{ORANGE}; stroke-width:1.2;
           animation:onde 6.5s ease-out infinite; }}

    /* Chaque couche derive d'un bloc : les liens ne se detachent jamais. */
    #proche {{ animation:derive_a 26s ease-in-out infinite alternate; }}
    #loin   {{ animation:derive_b 37s ease-in-out infinite alternate; }}

    @keyframes file      {{ to {{ stroke-dashoffset:-64; }} }}
    @keyframes battement {{ 0%,100% {{ opacity:.34; }} 50% {{ opacity:1; }} }}
    @keyframes trajet {{
        0%       {{ transform:translate(var(--x1),var(--y1)); opacity:0; }}
        10%      {{ opacity:.95; }}
        55%,100% {{ transform:translate(var(--x2),var(--y2)); opacity:0; }}
    }}
    @keyframes onde {{
        0%   {{ r:3;  stroke-opacity:.55; }}
        70%  {{ r:34; stroke-opacity:0; }}
        100% {{ r:34; stroke-opacity:0; }}
    }}
    @keyframes derive_a {{ from {{ transform:translate(-22px,-6px); }}
                           to   {{ transform:translate(22px,6px); }} }}
    @keyframes derive_b {{ from {{ transform:translate(16px,5px); }}
                           to   {{ transform:translate(-16px,-5px); }} }}

    @media (prefers-reduced-motion: reduce) {{
        .Pl, .Ll, .Pn, .Ln, .p, .o, #proche, #loin {{ animation: none; }}
        .p, .o {{ opacity: 0; }}
        .Pn {{ opacity: .55; }}
    }}
    """

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {largeur} {hauteur}" '
        f'width="{largeur}" height="{hauteur}" preserveAspectRatio="xMidYMid slice">'
        f'<style>{style}</style>'
        # Le motif s'efface a ses quatre bords : aucune ligne ne s'arrete net,
        # et il se fond dans la page juste avant le titre.
        f'<defs>'
        f'<linearGradient id="h" x1="0" x2="1">'
        f'<stop offset="0" stop-color="#000"/><stop offset=".06" stop-color="#fff"/>'
        f'<stop offset=".94" stop-color="#fff"/><stop offset="1" stop-color="#000"/>'
        f'</linearGradient>'
        f'<linearGradient id="v" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="#666"/><stop offset=".26" stop-color="#fff"/>'
        f'<stop offset=".8" stop-color="#fff"/><stop offset="1" stop-color="#000"/>'
        f'</linearGradient>'
        f'<mask id="mh"><rect width="{largeur}" height="{hauteur}" fill="url(#h)"/></mask>'
        f'<mask id="mv"><rect width="{largeur}" height="{hauteur}" fill="url(#v)"/></mask>'
        f'</defs>'
        f'<g mask="url(#mh)"><g mask="url(#mv)">'
        f'<g id="loin">{dessiner(loin_pts, loin_liens, "L", [1.4, 1.8, 2.2])}</g>'
        f'<g id="proche">{dessiner(proche_pts, proche_liens, "P", [2.2, 2.9, 3.6])}'
        f'{ondes}{impulsions}</g>'
        f'</g></g>'
        f'</svg>'
    )


BANDEAU_RESEAU = "<div class='bandeau-reseau'></div>"


def css_reseau() -> str:
    """Pose le reseau dans la bande vide du haut de page.

    Il occupait d'abord le fond du bandeau de titre, ou il devait s'effacer
    sous le texte : la moitie du motif etait perdue. Il occupe desormais la
    bande vide qui le surmonte, sur toute la largeur de la zone de contenu —
    le seul endroit de la page ou un motif ne gene personne.

    Les marges negatives le font deborder de la colonne de texte pour aller
    d'un bord a l'autre ; `overflow-x: hidden` sur la zone principale le coupe
    net a ses limites, sinon il passerait par-dessus la barre laterale.
    """
    motif = base64.b64encode(_motif_reseau().encode("utf-8")).decode("ascii")
    return f"""<style>
[data-testid="stMain"] {{ overflow-x: hidden; }}
.bandeau-reseau {{
    height: 168px;
    margin: -30px -7rem -10px -7rem;
    background-image: url("data:image/svg+xml;base64,{motif}");
    background-repeat: no-repeat;
    background-position: center;
    background-size: cover;
    pointer-events: none;
}}
@media (max-width: 820px) {{
    /* Le bouton MENU se pose en haut a gauche : on decale le motif pour
       qu'il ne passe pas derriere. */
    .bandeau-reseau {{ height: 66px; margin: 30px -14px -6px -14px; }}
}}
</style>"""


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

/* ── Bouton d'ouverture du menu ──────────────────────────────────────────── */
/* Une fois la barre laterale repliee, Streamlit ne laisse qu'une fleche grise
   de la taille d'un ongle : rien n'indique qu'elle ramene Planning, KPI et
   Historique. Elle porte donc son nom, sur telephone comme sur ordinateur.
   Seul le bouton d'OUVERTURE est concerne : celui qui referme la barre, a
   l'interieur, garde sa fleche — il ne mene nulle part. */
[data-testid="stSidebarCollapsedControl"],
[data-testid="collapsedControl"] {
    display: inline-flex !important;
    align-items: center !important;
    gap: 7px !important;
    background: rgba(255,122,26,0.13) !important;
    border: 1px solid rgba(255,122,26,0.40) !important;
    border-radius: 999px !important;
    min-height: 38px !important;
    padding: 6px 15px 6px 11px !important;
    box-shadow: 0 8px 22px -14px rgba(255,122,26,0.9) !important;
    transition: background .15s ease, border-color .15s ease;
}
[data-testid="stSidebarCollapsedControl"]:hover,
[data-testid="collapsedControl"]:hover {
    background: rgba(255,122,26,0.22) !important;
    border-color: rgba(255,122,26,0.65) !important;
}
[data-testid="stSidebarCollapsedControl"]::after,
[data-testid="collapsedControl"]::after {
    content: "MENU";
    font-family: 'Inter', sans-serif;
    font-size: 0.76rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    color: var(--accent);
    white-space: nowrap;
}
[data-testid="stSidebarCollapsedControl"] svg,
[data-testid="collapsedControl"] svg {
    width: 20px !important; height: 20px !important;
}

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

  /* Les tailles restent genereuses : un telephone se tient plus pres de
     l'oeil, mais un texte de 11 px n'y est pas plus lisible qu'ailleurs. */
  .header-title      { font-size: 1.6rem !important; letter-spacing: 0.05em !important; }
  .header-banner     { flex-direction: column !important; align-items: flex-start !important;
                       gap: 10px !important; padding: 16px 18px !important; }
  .header-date       { text-align: left !important; }
  .masthead-eyebrow  { font-size: 0.78rem !important; letter-spacing: 0.14em !important; }
  .page-title        { font-size: 1.25rem !important; letter-spacing: 0.05em !important; }
  .section-title     { font-size: 1rem !important; }
  h1 { font-size: 1.5rem !important; }
  h2 { font-size: 1.25rem !important; }
  h3 { font-size: 1.1rem !important; }

  /* Zone tactile : 44 px, la valeur recommandee */
  .stButton > button,
  .stDownloadButton > button {
      width: 100% !important;
      min-height: 44px !important;
      padding: 10px 16px !important;
  }
  /* En dessous de 16 px, l'iPhone zoome automatiquement a chaque saisie et
     la page se retrouve de travers. La regle vise donc large. */
  [data-baseweb="input"], [data-baseweb="input"] input,
  [data-baseweb="base-input"] input,
  [data-testid="stNumberInput"] input,
  [data-testid="stTextInput"] input,
  [data-baseweb="select"] > div,
  textarea, input, select {
      min-height: 44px !important;
      font-size: 16px !important;
  }

  [data-testid="stDataFrame"],
  [data-testid="stTable"] {
      overflow-x: auto !important;
      max-width: 100% !important;
  }

  /* Les graphiques occupent toute la largeur de l'ecran au lieu d'etre
     enfermes dans un cadre defilant de 560 px. Le Gantt se parcourt au doigt
     (Plotly gere le glisser et le pincement), ce qui vaut mieux qu'une barre
     de defilement horizontale sur un telephone. */
  .js-plotly-plot, .stPlotlyChart {
      max-width: 100% !important;
      overflow: visible !important;
  }
  .js-plotly-plot .plotly { min-width: 0 !important; width: 100% !important; }
  .block-container .stPlotlyChart { margin-left: -6px; margin-right: -6px; }

  [data-testid="stMetric"]      { padding: 10px 0 !important; }
  [data-testid="stMetricValue"] { font-size: 1.65rem !important; }
  [data-testid="stMetricLabel"] { min-height: 0 !important; }
  /* Empilees, les mesures se separent par un filet horizontal, plus vertical. */
  [data-testid="stHorizontalBlock"] [data-testid="stMetric"] {
      border-left: 0 !important;
      padding-left: 0 !important;
      border-top: 1px solid var(--verre-bord) !important;
      padding-top: 12px !important;
  }

  .stTabs [data-baseweb="tab-list"] { overflow-x: auto !important; flex-wrap: nowrap !important; }
  .stTabs [data-baseweb="tab"]      { min-width: max-content !important; }

  [data-testid="stSidebar"] { min-width: 84vw !important; }

  /* Zone tactile portee a 44 px sur telephone. */
  [data-testid="stSidebarCollapsedControl"],
  [data-testid="collapsedControl"] {
      min-height: 44px !important;
      padding: 8px 16px 8px 12px !important;
  }

  /* Navigation en pastilles : elles doivent tenir sur deux lignes et rester
     cliquables au pouce. */
  [data-testid="stPills"] { margin-bottom: 14px !important; }
  [data-testid="stPills"] div[role="group"] {
      display: flex !important;
      flex-wrap: wrap !important;
      gap: 8px !important;
  }
  [data-testid="stPills"] button {
      min-height: 40px !important;
      padding: 8px 16px !important;
      font-size: 0.88rem !important;
      flex: 1 1 auto !important;
  }

  /* Le verre depoli coute cher en calcul sur telephone : on l'allege.
     Les mesures en sont exclues — elles n'ont plus de cadre nulle part, et
     leur redonner un fond ici les aurait transformees en cartes. */
  [data-testid="stExpander"], [data-testid="stForm"],
  .dl-card, .accueil-bloc, .header-banner {
      backdrop-filter: none !important;
      -webkit-backdrop-filter: none !important;
      background: var(--surface) !important;
  }
  .header-banner { background-image: none !important; }
  [data-testid="stMetric"] {
      background: transparent !important;
      border-radius: 0 !important;
  }
}

@media (max-width: 480px) {
  .header-title { font-size: 1.35rem !important; letter-spacing: 0.04em !important; }
  .block-container { padding: 10px 10px 60px 10px !important; }
  /* Surtout PAS de largeur minimale ici : c'est elle qui debordait de
     l'ecran et rendait le Gantt illisible sur un telephone. */
  .js-plotly-plot .plotly { min-width: 0 !important; width: 100% !important; }
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
