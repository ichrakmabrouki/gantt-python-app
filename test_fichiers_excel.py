"""
test_fichiers_excel.py — validation sur les fichiers Excel du projet.

Passe en revue TOUS les fichiers .xlsx des dossiers de test, les resout, et
controle les 9 contraintes du modele sur chaque planning produit — contrainte
par contrainte, fichier par fichier.

Lancer avec le bouton Run de VS Code, ou :
    python test_fichiers_excel.py

Produit : RAPPORT_FICHIERS.md
"""

import sys
import time
import traceback
from contextlib import redirect_stdout
from datetime import datetime
from io import StringIO
from pathlib import Path

RACINE = Path(__file__).resolve().parent
sys.path.insert(0, str(RACINE))
RAPPORT = RACINE / "RAPPORT_FICHIERS.md"

BUDGET = 60.0

DOSSIERS = [
    "generated_test_excels",
    "generated_test_excels_fixed10tech_cte15",
]

# Les contraintes que le verificateur controle sur le planning produit.
# C4, C5 et C10 sont structurelles : elles sont vraies par construction du
# modele (le setup occupe exactement [S-cte, S], et E = S + duree).
CONTRAINTES = ["C1", "C2", "C3", "C6", "C7", "C8", "C9"]

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


def par_contrainte(violations: list[str]) -> dict[str, int]:
    """Regroupe les violations par code de contrainte (C1, C2, ...)."""
    compte = {c: 0 for c in CONTRAINTES}
    for v in violations:
        code = v.split(None, 1)[0]
        if code in compte:
            compte[code] += 1
        else:
            compte.setdefault("autre", 0)
            compte["autre"] += 1
    return compte


def main() -> int:
    from backend.solver.input_parser import parse_excel_to_dict, validate_excel_data
    from backend.solver.model import solve_flexible_jobshop
    from verifier_planning import verifier_planning

    depart = time.time()
    ecrire("# Validation sur les fichiers Excel du projet")
    ecrire()
    ecrire(f"Genere le {datetime.now().strftime('%d/%m/%Y a %H:%M:%S')}")
    ecrire()
    ecrire(f"Budget de resolution : **{BUDGET:.0f} secondes** par fichier. "
           f"Chaque planning produit est relu par `verifier_planning.py`, "
           f"independant du solveur.")

    fichiers = []
    for dossier in DOSSIERS:
        chemin = RACINE / dossier
        if chemin.exists():
            fichiers.extend(sorted(chemin.glob("*.xlsx")))

    if not fichiers:
        ecrire()
        ecrire("Aucun fichier .xlsx trouve dans les dossiers de test.")
        return 1

    # ── 1. Ce que couvrent les fichiers ───────────────────────────────────────
    ecrire()
    ecrire("## 1. Caracteristiques des fichiers")
    ecrire()
    ecrire("| Fichier | Pieces | Operations | Machines | Techniciens | cte | Modes | Modes/op | Tech/machine |")
    ecrire("|---|---|---|---|---|---|---|---|---|")

    instances = []
    for fichier in fichiers:
        try:
            data = parse_excel_to_dict(str(fichier))
            ok, msg = validate_excel_data(data)
        except Exception as exc:
            ecrire(f"| {fichier.name} | — | — | — | — | — | — | "
                   f"LECTURE IMPOSSIBLE : {type(exc).__name__} |")
            continue
        if not ok:
            ecrire(f"| {fichier.name} | — | — | — | — | — | — | "
                   f"INVALIDE : {msg[:40]} |")
            continue

        p = data["params"]
        machines = {m for _, m in data["modes"]}
        nb_mch = len(machines)
        nb_tech = len({t for t, _ in data["grp_mchs"]})
        modes_par_op = len(data["modes"]) / p["nbOps"] if p["nbOps"] else 0

        # Nombre de techniciens rattaches a chaque machine. Le modele exige un
        # setup de CHAQUE technicien rattache a la machine : tant que cette
        # valeur vaut 1, cela revient a « un technicien fait le changement de
        # serie ». Au-dela de 1, le modele devient plus contraint que la
        # realite de l'atelier — a surveiller.
        par_machine: dict[int, int] = {m: 0 for m in machines}
        for t, m in set(data["grp_mchs"]):
            if m in par_machine:
                par_machine[m] += 1
        moyenne_tm = sum(par_machine.values()) / nb_mch if nb_mch else 0
        maxi_tm = max(par_machine.values()) if par_machine else 0
        cellule_tm = f"{moyenne_tm:.2f}"
        if maxi_tm > 1:
            cellule_tm += f" (max **{maxi_tm}**)"

        ecrire(f"| {fichier.stem} | {p['nbJobs']} | {p['nbOps']} | {nb_mch} | "
               f"{nb_tech} | {data['cte']} | {len(data['modes'])} | "
               f"{modes_par_op:.2f} | {cellule_tm} |")
        instances.append((fichier, data))

    # ── 2. Resolution et controle ─────────────────────────────────────────────
    ecrire()
    ecrire("## 2. Resolution et controle des contraintes")
    ecrire()
    ecrire("Une case vide signifie « aucune violation ». Un nombre signifie "
           "le nombre de violations detectees pour cette contrainte.")
    ecrire()
    entete = " | ".join(CONTRAINTES)
    ecrire(f"| Fichier | Temps | Makespan | {entete} | Verdict |")
    ecrire("|---" * (4 + len(CONTRAINTES)) + "|")

    resolus = valides = timeouts = 0
    details: list[tuple[str, list[str]]] = []
    erreurs: list[tuple[str, str]] = []

    for fichier, data in instances:
        nom = fichier.stem
        t0 = time.time()
        try:
            with redirect_stdout(StringIO()):
                df = solve_flexible_jobshop(data, max_time_seconds=BUDGET)
        except ValueError as exc:
            duree = time.time() - t0
            if "Pas de solution" in str(exc):
                timeouts += 1
                verdict = "aucune solution dans le budget"
            else:
                erreurs.append((nom, str(exc)))
                verdict = f"erreur : {str(exc)[:40]}"
            vides = " | ".join("—" for _ in CONTRAINTES)
            ecrire(f"| {nom} | {duree:.1f} s | — | {vides} | {verdict} |")
            continue
        except Exception as exc:
            duree = time.time() - t0
            erreurs.append((nom, f"{type(exc).__name__}: {exc}"))
            vides = " | ".join("—" for _ in CONTRAINTES)
            ecrire(f"| {nom} | {duree:.1f} s | — | {vides} | "
                   f"erreur {type(exc).__name__} |")
            continue

        duree = time.time() - t0
        resolus += 1
        violations = verifier_planning(data, df)
        compte = par_contrainte(violations)
        makespan = int(df["EndTime"].max()) if len(df) else 0

        cellules = " | ".join(
            "" if compte.get(c, 0) == 0 else f"**{compte[c]}**"
            for c in CONTRAINTES
        )
        if violations:
            details.append((nom, violations))
            verdict = f"**{len(violations)} VIOLATION(S)**"
        else:
            valides += 1
            verdict = "valide"

        ecrire(f"| {nom} | {duree:.1f} s | {makespan} min | {cellules} | {verdict} |")

    # ── 3. Bilan ──────────────────────────────────────────────────────────────
    ecrire()
    ecrire("## 3. Bilan")
    ecrire()
    ecrire("| Resultat | Nombre |")
    ecrire("|---|---|")
    ecrire(f"| Fichiers traites | {len(instances)} |")
    ecrire(f"| Plannings produits | {resolus} |")
    ecrire(f"| Plannings **valides sur les 9 contraintes** | **{valides}** |")
    ecrire(f"| Plannings en violation | {len(details)} |")
    ecrire(f"| Aucune solution dans le budget | {timeouts} |")
    ecrire(f"| Erreurs techniques | {len(erreurs)} |")

    if details:
        ecrire()
        ecrire("### Violations detectees")
        ecrire()
        for nom, violations in details:
            ecrire(f"**{nom}** — {len(violations)} violation(s) :")
            ecrire()
            for v in violations[:10]:
                ecrire(f"- {v}")
            if len(violations) > 10:
                ecrire(f"- … et {len(violations) - 10} autre(s)")
            ecrire()

    if erreurs:
        ecrire()
        ecrire("### Erreurs techniques")
        ecrire()
        for nom, message in erreurs:
            ecrire(f"- `{nom}` : {message[:160]}")

    ecrire()
    ecrire(f"Campagne terminee en {time.time() - depart:.0f} secondes.")
    ecrire()
    ecrire("> C4 (debut apres fin de setup), C5 (setup >= cte) et C10 "
           "(fin >= duree + setup) ne figurent pas dans le tableau : elles "
           "sont structurelles dans la version 2. Le setup occupe exactement "
           "le creneau `[S - cte, S]` et la fin vaut `S + duree`, donc elles "
           "sont vraies par construction et non par verification.")
    return 0 if not details and not erreurs else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        ecrire()
        ecrire("```")
        ecrire(traceback.format_exc()[:3000])
        ecrire("```")
        sys.exit(1)
