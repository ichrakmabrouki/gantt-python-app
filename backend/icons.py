"""
icons.py — jeu d'icones vectorielles dessinees dans le code.

L'application utilisait 24 fichiers PNG de 800x800 pixels, soit environ 2 Mo
charges a chaque affichage de page, pour des pictogrammes de 18 pixels. Ils
etaient de plus figes en orange : impossible de les faire suivre une couleur de
texte, d'ou des icones illisibles des que le fond changeait.

Ici, chaque icone est un trace SVG de quelques dizaines d'octets. Elle recoit sa
couleur et sa taille au moment de l'appel, reste nette a n'importe quelle
definition d'ecran, et l'ensemble du jeu pese moins qu'un seul des anciens PNG.

Le style est volontairement sobre : trait de 1,7 px, extremites arrondies,
grille de 24x24 — la convention des jeux d'icones d'interface actuels.

    from backend.icons import icone
    st.markdown(icone("planning", 18, "#ff7a1a") + " Planning", ...)
"""

import base64

# ── Traces ────────────────────────────────────────────────────────────────────
# Grille de 24x24. Traits uniquement, sauf pour les formes listees dans PLEINES.
FORMES: dict[str, str] = {
    # Navigation
    "grille":      '<rect x="3.5" y="3.5" width="7" height="7" rx="1.5"/>'
                   '<rect x="13.5" y="3.5" width="7" height="7" rx="1.5"/>'
                   '<rect x="3.5" y="13.5" width="7" height="7" rx="1.5"/>'
                   '<rect x="13.5" y="13.5" width="7" height="7" rx="1.5"/>',
    "donnees":     '<ellipse cx="12" cy="6" rx="7.5" ry="3"/>'
                   '<path d="M4.5 6v6c0 1.66 3.36 3 7.5 3s7.5-1.34 7.5-3V6"/>'
                   '<path d="M4.5 12v6c0 1.66 3.36 3 7.5 3s7.5-1.34 7.5-3v-6"/>',
    "planning":    '<path d="M3 4.5h11"/><path d="M3 9.5h17"/>'
                   '<path d="M3 14.5h8"/><path d="M3 19.5h13"/>',
    "kpi":         '<path d="M4 20V10"/><path d="M10 20V4"/>'
                   '<path d="M16 20v-7"/><path d="M22 20H2"/>',
    "historique":  '<circle cx="12" cy="12" r="8.5"/><path d="M12 7v5l3.5 2"/>',
    "export":      '<path d="M12 15V3"/><path d="M8 7l4-4 4 4"/>'
                   '<path d="M3.5 14v5a2 2 0 0 0 2 2h13a2 2 0 0 0 2-2v-5"/>',

    # Etat et statut
    "utilisateur": '<circle cx="12" cy="8" r="3.75"/>'
                   '<path d="M4.5 20a7.5 7.5 0 0 1 15 0"/>',
    "coche":       '<path d="M4.5 12.5l5 5 10-11"/>',
    "hexagone":    '<path d="M12 2.5l8.5 4.75v9.5L12 21.5l-8.5-4.75v-9.5z"/>',
    "lecture":     '<path d="M7.5 4.5l12 7.5-12 7.5z"/>',
    "fleche":      '<path d="M4 12h15"/><path d="M13.5 6.5L20 12l-6.5 5.5"/>',
    "loupe":       '<circle cx="10.5" cy="10.5" r="6.5"/><path d="M15.5 15.5L21 21"/>',
    "idee":        '<path d="M9 18h6"/><path d="M10 21.5h4"/>'
                   '<path d="M12 2.5a6.5 6.5 0 0 0-3.8 11.8c.5.4.8 1 .8 1.7h6c0-.7.3-1.3.8-1.7'
                   'A6.5 6.5 0 0 0 12 2.5z"/>',
    "document":    '<path d="M14 2.5H6.5a2 2 0 0 0-2 2v15a2 2 0 0 0 2 2h11a2 2 0 0 0 2-2V8z"/>'
                   '<path d="M14 2.5V8h5.5"/><path d="M8.5 13h7"/><path d="M8.5 17h5"/>',
    "graphique":   '<path d="M3 20h18"/><path d="M4 15.5l5-5.5 4 3.5 6.5-7.5"/>',
    "calendrier":  '<rect x="3.5" y="5" width="17" height="16" rx="2"/>'
                   '<path d="M3.5 10h17"/><path d="M8 2.5v5"/><path d="M16 2.5v5"/>',
    "reglages":    '<path d="M4 7h10"/><path d="M18 7h2"/><path d="M4 17h4"/><path d="M12 17h8"/>'
                   '<circle cx="16" cy="7" r="2.2"/><circle cx="10" cy="17" r="2.2"/>',

    # Performance
    "cible":       '<circle cx="12" cy="12" r="8.5"/><circle cx="12" cy="12" r="4.5"/>'
                   '<circle cx="12" cy="12" r="1"/>',
    "eclair":      '<path d="M13 2.5L4.5 13.5H11l-1 8 8.5-11H12z"/>',
    "jeton":       '<circle cx="12" cy="12" r="8.5"/><path d="M15 9h-4.2a1.8 1.8 0 0 0 0 3.6h2.4'
                   'a1.8 1.8 0 0 1 0 3.6H9"/><path d="M12 7v10"/>',
    "horloge":     '<circle cx="12" cy="12" r="8.5"/><path d="M12 7.5V12l3 1.8"/>',
    "balance":     '<path d="M12 3.5v17"/><path d="M5 7h14"/>'
                   '<path d="M5 7L2.5 13h5z"/><path d="M19 7l-2.5 6h5z"/>',

    # Messages
    "avertissement": '<path d="M12 3.5L21.5 20h-19z"/><path d="M12 9.5v5"/><path d="M12 17.5h.01"/>',
    "info":        '<circle cx="12" cy="12" r="8.5"/><path d="M12 11v5.5"/><path d="M12 7.8h.01"/>',
    "croix":       '<path d="M6 6l12 12"/><path d="M18 6L6 18"/>',

    # Puce pleine, utilisee pour les legendes de couleur
    "point":       '<circle cx="12" cy="12" r="6"/>',
}

PLEINES = {"point", "lecture", "eclair"}


def svg(nom: str, taille: int = 18, couleur: str = "currentColor",
        trait: float = 1.7) -> str:
    """Renvoie le code SVG brut de l'icone."""
    trace = FORMES.get(nom)
    if trace is None:
        trace = FORMES["point"]
    if nom in PLEINES:
        peinture = f'fill="{couleur}" stroke="none"'
    else:
        peinture = (f'fill="none" stroke="{couleur}" stroke-width="{trait}" '
                    f'stroke-linecap="round" stroke-linejoin="round"')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
            f'width="{taille}" height="{taille}" {peinture}>{trace}</svg>')


def icone(nom: str, taille: int = 18, couleur: str = "#ff7a1a",
          cale: int = -3, trait: float = 1.7) -> str:
    """Icone prete a inserer dans un bloc HTML de Streamlit.

    Elle est encapsulee dans une balise <img> avec une source `data:` : c'est
    la seule forme que le rendu Markdown de Streamlit laisse passer intacte,
    quelle que soit sa version.
    """
    donnees = base64.b64encode(
        svg(nom, taille, couleur, trait).encode("utf-8")
    ).decode("ascii")
    return (f'<img class="ico" alt="" src="data:image/svg+xml;base64,{donnees}" '
            f'style="width:{taille}px;height:{taille}px;vertical-align:{cale}px;'
            f'display:inline-block" />')
