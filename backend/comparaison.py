"""
comparaison.py — le planning CP-SAT face aux regles de priorite classiques.

Separe de l'interface pour une raison simple : ces chiffres sont ceux que
l'on montre a un recruteur ou a un chef d'atelier. Ils doivent pouvoir etre
testes sans lancer Streamlit.

Vocabulaire :
    fin_cpsat  — fin du lot (makespan) du planning calcule par le solveur
    par_regle  — {"FIFO": 810, "SPT": 1005, ...} fin du lot de chaque regle
    borne      — borne inferieure prouvee par CP-SAT : aucun planning ne peut
                 finir avant
"""

from __future__ import annotations

# Ordre d'affichage : de la pratique la plus courante a la plus specialisee.
REGLES_INFO: dict[str, dict[str, str]] = {
    "FIFO": {
        "nom": "Premier arrivé, premier servi",
        "principe": "Les pièces sont lancées dans leur ordre d'arrivée.",
    },
    "SPT": {
        "nom": "Plus courte d'abord",
        "principe": "L'opération la plus rapide passe en premier.",
    },
    "LPT": {
        "nom": "Plus longue d'abord",
        "principe": "L'opération la plus longue passe en premier.",
    },
    "MWKR": {
        "nom": "Plus de travail restant",
        "principe": "La pièce à qui il reste le plus à faire passe en premier.",
    },
}

MEILLEURE = "MEILLEURE"   # pseudo-regle : la meilleure des quatre


def gain(fin_reference: int, fin_cpsat: int) -> tuple[int, float]:
    """Minutes et pourcentage gagnes par CP-SAT face a une reference.

    Le pourcentage est rapporte a la reference : « on termine 12 % plus tot
    que ce que l'atelier aurait fait ». Un gain negatif est rendu tel quel —
    le cacher serait tricher.
    """
    minutes = int(fin_reference) - int(fin_cpsat)
    pct = (minutes / fin_reference * 100) if fin_reference else 0.0
    return minutes, pct


def fin_de_reference(par_regle: dict[str, int], choix: str) -> tuple[str, int]:
    """Nom et fin du lot de la reference choisie.

    `choix` vaut une regle ("FIFO"...) ou MEILLEURE. Si la regle demandee
    n'a pas pu etre calculee, on retombe sur FIFO, puis sur la meilleure.
    """
    if not par_regle:
        raise ValueError("Aucune règle de référence n'a été calculée.")
    if choix == MEILLEURE:
        regle = min(par_regle, key=par_regle.get)
        return regle, int(par_regle[regle])
    if choix in par_regle:
        return choix, int(par_regle[choix])
    if "FIFO" in par_regle:
        return "FIFO", int(par_regle["FIFO"])
    regle = min(par_regle, key=par_regle.get)
    return regle, int(par_regle[regle])


def tableau_comparatif(par_regle: dict[str, int], fin_cpsat: int,
                       borne: int | None = None) -> list[dict]:
    """Une ligne par methode, triee du plus long au plus court.

    Les colonnes sont celles que l'on affiche : pas de valeur brute a
    reformater cote interface.
    """
    lignes = []
    for regle, info in REGLES_INFO.items():
        if regle not in par_regle:
            continue
        fin = int(par_regle[regle])
        minutes, pct = gain(fin, fin_cpsat)
        lignes.append({
            "Méthode": regle,
            "Principe": info["nom"],
            "Fin du lot (min)": fin,
            "CP-SAT gagne (min)": minutes,
            "CP-SAT gagne (%)": round(pct, 1),
            "_type": "regle",
        })
    lignes.sort(key=lambda l: -l["Fin du lot (min)"])

    lignes.append({
        "Méthode": "CP-SAT",
        "Principe": "Optimisation sous contraintes (l'application)",
        "Fin du lot (min)": int(fin_cpsat),
        "CP-SAT gagne (min)": None,     # se comparer a soi-meme n'a pas de sens
        "CP-SAT gagne (%)": None,
        "_type": "cpsat",
    })
    if borne:
        lignes.append({
            "Méthode": "Borne",
            "Principe": "Limite prouvée : aucun planning ne peut finir avant",
            "Fin du lot (min)": int(borne),
            "CP-SAT gagne (min)": None,
            "CP-SAT gagne (%)": None,
            "_type": "borne",
        })
    return lignes


def valeur_estimee(minutes_gagnees: int, couts: dict[str, float]) -> tuple[float, float]:
    """Capacite liberee convertie en euros, au cout horaire saisi.

    Rend (valeur en euros, cout horaire utilise). Seuls les couts horaires
    comptent : la matiere est consommee de la meme facon quel que soit
    l'ordre de passage, elle ne varie pas avec le planning.
    """
    horaire = (float(couts.get("cout_machine_h", 0))
               + float(couts.get("cout_mo_h", 0))
               + float(couts.get("cout_indirect_h", 0)))
    return minutes_gagnees / 60 * horaire, horaire


# ── Cartes explicatives (onglet Performance) ────────────────────────────────
# Une carte par methode : ce qu'elle fait, dit simplement, et ce qu'elle donne
# sur l'atelier en cours. Le texte vise quelqu'un qui n'a jamais entendu parler
# d'ordonnancement.
CARTES_METHODES = [
    ("FIFO", "fifo", "Premier arrivé, premier servi",
     "Les pièces partent dans leur ordre d'arrivée. C'est la pratique la plus "
     "courante quand l'atelier n'a pas d'outil."),
    ("SPT", "spt", "Plus courte d'abord",
     "L'opération la plus rapide passe en premier. La file se vide vite, mais "
     "les pièces longues attendent."),
    ("LPT", "lpt", "Plus longue d'abord",
     "L'opération la plus longue passe en premier : on attaque tôt ce qui "
     "prendra du temps."),
    ("MWKR", "mwkr", "Plus de travail restant",
     "La pièce à qui il reste le plus d'opérations passe en premier, pour "
     "qu'elle ne termine pas en dernier."),
    ("CP-SAT", "cpsat", "L'application",
     "Le solveur explore les enchaînements possibles et garde celui qui "
     "termine le lot au plus tôt, en respectant toutes les contraintes."),
    ("Borne", "borne", "Limite théorique",
     "Aucun planning, quel qu'il soit, ne peut finir avant. L'écart avec "
     "CP-SAT dit ce qu'il reste à gagner."),
]


def _nb(v, dec=0):
    t = f"{v:,.{dec}f}"
    return t.replace(",", " ").replace(".", ",")


def cartes_methodes_html(par_regle: dict[str, int], fin_cpsat: int,
                         borne: int | None, regle_reference: str,
                         icones: dict[str, str], ecart_optimalite: float | None = None) -> str:
    """HTML des six cartes. `icones` : {nom: base64 webp}. Les methodes non
    calculees (ou la borne absente) sont simplement omises."""
    import html as _html
    cartes = []
    for sigle, icone, nom, texte in CARTES_METHODES:
        classes = ["methode-carte"]
        badge = ""
        if sigle in REGLES_INFO:
            if sigle not in par_regle:
                continue
            fin = int(par_regle[sigle])
            minutes, pct = gain(fin, fin_cpsat)
            ecart = (f"CP-SAT gagne {_nb(minutes)} min ({_nb(pct, 1)} %)" if minutes >= 0
                     else f"Fait mieux que CP-SAT de {_nb(-minutes)} min")
            if sigle == regle_reference:
                classes.append("reference")
                badge = "<span class='methode-badge'>RÉFÉRENCE CHOISIE</span>"
        elif sigle == "CP-SAT":
            fin = int(fin_cpsat)
            ecart = "Le planning affiché dans le Gantt"
            classes.append("cpsat")
            badge = "<span class='methode-badge'>RETENU</span>"
        else:
            if not borne:
                continue
            fin = int(borne)
            ecart = (f"Reste à gagner : au plus {_nb(ecart_optimalite * 100, 1)} %"
                     if ecart_optimalite is not None else "Prouvée par le solveur")
        img = icones.get(icone, "")
        img_html = (f"<img class='methode-icone' alt='' src='data:image/webp;base64,{img}'>"
                    if img else "<div class='methode-icone'></div>")
        # En-tete (icone + sigle + nom), puis le texte sur toute la largeur de
        # la carte : dans une colonne etroite a cote de l'icone, il s'etirait
        # sur dix lignes. Le badge est dans le flux, au-dessus du sigle, pour
        # ne plus chevaucher le sigle quand la carte est etroite.
        cartes.append(
            f"<div class='{' '.join(classes)}'>"
            f"<div class='methode-tete'>{img_html}"
            f"<div class='methode-titres'>{badge}"
            f"<div class='methode-sigle'>{_html.escape(sigle)}</div>"
            f"<div class='methode-nom'>{_html.escape(nom)}</div>"
            f"</div></div>"
            f"<div class='methode-texte'>{_html.escape(texte)}</div>"
            f"<div class='methode-resultat'><span class='methode-minutes'>{_nb(fin)} min</span>"
            f"<span class='methode-ecart'>{_html.escape(ecart)}</span></div>"
            f"</div>")
    return "<div class='methodes-grille'>" + "".join(cartes) + "</div>"
