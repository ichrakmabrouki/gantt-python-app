"""
mesurer_memoire.py — combien de RAM consomme une résolution ?

Streamlit Community Cloud alloue environ **1 Go de RAM par application**, et
tous les visiteurs partagent ce même conteneur. Avant de publier le lien, mieux
vaut savoir ce qu'une résolution coûte réellement, plutôt que de le deviner.

Le script mesure le pic de mémoire du processus pour chaque jeu de données, et
en déduit combien de visiteurs simultanés l'hébergement peut encaisser.

    pip install psutil
    python mesurer_memoire.py

Produit : RAPPORT_MEMOIRE.md
"""

import gc
import sys
import time
import traceback
from contextlib import redirect_stdout
from datetime import datetime
from io import StringIO
from pathlib import Path

RACINE = Path(__file__).resolve().parent
sys.path.insert(0, str(RACINE))
RAPPORT = RACINE / "RAPPORT_MEMOIRE.md"

BUDGET = 30.0
LIMITE_HEBERGEMENT_MO = 1024      # Streamlit Community Cloud

_lignes: list[str] = []


def ecrire(ligne: str = "") -> None:
    _lignes.append(ligne)
    try:
        print(ligne)
    except Exception:
        print(ligne.encode("ascii", "replace").decode("ascii"))
    try:
        RAPPORT.write_text("\n".join(_lignes) + "\n", encoding="utf-8")
    except Exception:
        pass


def main() -> int:
    try:
        import psutil
    except ImportError:
        print("psutil est requis pour mesurer la memoire :\n\n    pip install psutil\n")
        return 1

    from backend.solver.input_parser import parse_excel_to_dict, validate_excel_data
    from backend.solver.model import solve_flexible_jobshop

    processus = psutil.Process()
    mo = lambda: processus.memory_info().rss / (1024 * 1024)

    ecrire("# Consommation mémoire d'une résolution")
    ecrire()
    ecrire(f"Généré le {datetime.now().strftime('%d/%m/%Y à %H:%M:%S')}")
    ecrire()
    ecrire(f"Mesure du pic de mémoire du processus (RSS) pendant la résolution, "
           f"budget {BUDGET:.0f} s par instance. La référence est la limite de "
           f"**{LIMITE_HEBERGEMENT_MO} Mo** de Streamlit Community Cloud.")
    ecrire()

    base = mo()
    ecrire(f"Mémoire au repos, modules chargés : **{base:.0f} Mo**. "
           f"C'est le coût fixe de Python, Streamlit, pandas, plotly et "
           f"OR-Tools — il est payé une seule fois pour tout le conteneur, "
           f"quel que soit le nombre de visiteurs.")
    ecrire()

    dossiers = ["generated_test_excels", "generated_test_excels_fixed10tech_cte15"]
    fichiers = []
    for dossier in dossiers:
        chemin = RACINE / dossier
        if chemin.exists():
            fichiers.extend(sorted(chemin.glob("*.xlsx")))

    ecrire("| Fichier | Opérations | Pic mémoire | Surcoût vs repos | Temps |")
    ecrire("|---|---|---|---|---|")

    surcouts = []
    for fichier in fichiers:
        try:
            data = parse_excel_to_dict(str(fichier))
            ok, _ = validate_excel_data(data)
            if not ok:
                continue
        except Exception:
            continue

        gc.collect()
        avant = mo()
        pic = avant
        depart = time.time()
        try:
            with redirect_stdout(StringIO()):
                df = solve_flexible_jobshop(data, max_time_seconds=BUDGET,
                                            num_search_workers=4)
            pic = max(pic, mo())
            duree = time.time() - depart
            surcout = pic - base
            surcouts.append(surcout)
            ecrire(f"| {fichier.stem} | {data['params']['nbOps']} | "
                   f"{pic:.0f} Mo | +{surcout:.0f} Mo | {duree:.1f} s |")
            del df
        except Exception as exc:
            ecrire(f"| {fichier.stem} | {data['params']['nbOps']} | — | — | "
                   f"échec : {type(exc).__name__} |")
        gc.collect()

    if not surcouts:
        ecrire()
        ecrire("Aucune mesure exploitable.")
        return 1

    pire = max(surcouts)
    marge = LIMITE_HEBERGEMENT_MO - base
    simultanes = int(marge // pire) if pire > 0 else 99

    ecrire()
    ecrire("## Ce que ça implique pour l'hébergement gratuit")
    ecrire()
    ecrire("| | Mo |")
    ecrire("|---|---|")
    ecrire(f"| Limite Streamlit Community Cloud | {LIMITE_HEBERGEMENT_MO} |")
    ecrire(f"| Coût fixe (Python + bibliothèques), payé une fois | {base:.0f} |")
    ecrire(f"| Marge disponible pour les résolutions | {marge:.0f} |")
    ecrire(f"| Pire résolution mesurée | {pire:.0f} |")
    ecrire()
    ecrire(f"**Environ {simultanes} résolution(s) du plus gros fichier "
           f"peuvent tenir en mémoire simultanément.**")
    ecrire()
    if simultanes <= 1:
        ecrire("> Une seule à la fois : le verrou posé dans `app.py`, qui "
               "sérialise les résolutions, n'est pas une précaution — il est "
               "nécessaire.")
    else:
        ecrire(f"> Le verrou de `app.py` sérialise déjà les résolutions, ce qui "
               f"laisse une marge confortable.")
    ecrire()
    ecrire("Un visiteur qui ne fait que consulter un planning déjà calculé ne "
           "coûte que quelques mégaoctets : le nombre de visiteurs n'est pas "
           "le problème, ce sont les résolutions simultanées.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        ecrire()
        ecrire("```")
        ecrire(traceback.format_exc()[:2000])
        ecrire("```")
        sys.exit(1)
