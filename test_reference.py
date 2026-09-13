"""
test_reference.py — l'ordonnancement de reference est-il valide ?

L'application affiche « l'optimisation fait gagner X % ». Ce chiffre ne vaut
que si le planning auquel on se compare est lui-meme realisable. Un planning de
reference qui violerait une contrainte serait artificiellement long, et le gain
annonce, fabrique.

Ce script rejoue donc les quatre regles de priorite sur des centaines
d'instances generees, et fait relire chaque planning produit par
`verifier_planning.py` — le meme controleur que celui applique aux resultats du
solveur, qui ne connait ni OR-Tools ni ce fichier.

    python test_reference.py

Produit : RAPPORT_REFERENCE.md
"""

import sys
import traceback
from datetime import datetime
from pathlib import Path

RACINE = Path(__file__).resolve().parent
sys.path.insert(0, str(RACINE))
RAPPORT = RACINE / "RAPPORT_REFERENCE.md"

PROFILS = ["aleatoire", "cte_zero", "sans_flexibilite",
           "un_seul_technicien", "un_tech_par_machine", "minimal"]
GRAINES = 40

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
    from stress_test_solveur import generer
    from backend.solver.baseline import ordonnancer_par_regle, REGLES
    from backend.solver.input_parser import parse_excel_to_dict, validate_excel_data
    from verifier_planning import verifier_planning

    ecrire("# Validation de l'ordonnancement de reference")
    ecrire()
    ecrire(f"Genere le {datetime.now().strftime('%d/%m/%Y a %H:%M:%S')}")
    ecrire()
    ecrire("Chaque planning produit par une regle de priorite est relu par "
           "`verifier_planning.py` sur les sept contraintes verifiables "
           "(C1, C2, C3, C6, C7, C8, C9).")
    ecrire()

    # ── Instances generees ───────────────────────────────────────────────────
    ecrire("## Instances generees")
    ecrire()
    ecrire("| Profil | Plannings | Valides | Operations placees |")
    ecrire("|---|---|---|---|")

    total = valides = 0
    echecs: list[str] = []

    for profil in PROFILS:
        n_profil = n_ok = 0
        complets = True
        for graine in range(1, GRAINES + 1):
            data = generer(graine, profil)
            attendu = data["params"]["nbOps"]
            for regle in REGLES:
                planning = ordonnancer_par_regle(data, regle)
                n_profil += 1
                total += 1
                if len(planning) != attendu:
                    complets = False
                    echecs.append(f"{profil}/{graine}/{regle} : "
                                  f"{len(planning)}/{attendu} operations")
                    continue
                violations = verifier_planning(data, planning)
                if violations:
                    echecs.append(f"{profil}/{graine}/{regle} : {violations[0]}")
                else:
                    n_ok += 1
                    valides += 1
        ecrire(f"| {profil} | {n_profil} | {n_ok} | "
               f"{'toutes' if complets else 'INCOMPLET'} |")

    # ── Fichiers Excel du depot ──────────────────────────────────────────────
    fichiers = []
    for dossier in ("generated_test_excels", "generated_test_excels_fixed10tech_cte15"):
        chemin = RACINE / dossier
        if chemin.exists():
            fichiers.extend(sorted(chemin.glob("*.xlsx")))

    if fichiers:
        ecrire()
        ecrire("## Fichiers Excel du depot")
        ecrire()
        ecrire("| Fichier | Operations | FIFO | SPT | LPT | MWKR | Valides |")
        ecrire("|---|---|---|---|---|---|---|")
        for fichier in fichiers:
            try:
                data = parse_excel_to_dict(str(fichier))
                ok, _ = validate_excel_data(data)
                if not ok:
                    continue
            except Exception:
                continue
            makespans, tous_valides = [], True
            for regle in REGLES:
                planning = ordonnancer_par_regle(data, regle)
                total += 1
                if len(planning) != data["params"]["nbOps"] or verifier_planning(data, planning):
                    tous_valides = False
                    echecs.append(f"{fichier.name}/{regle}")
                else:
                    valides += 1
                makespans.append(int(planning.attrs["makespan"]))
            ecrire(f"| {fichier.stem} | {data['params']['nbOps']} | "
                   + " | ".join(str(v) for v in makespans)
                   + f" | {'oui' if tous_valides else 'NON'} |")

    # ── Verdict ──────────────────────────────────────────────────────────────
    ecrire()
    ecrire("## Verdict")
    ecrire()
    ecrire(f"**{valides} / {total} plannings de reference valides.**")
    ecrire()
    if echecs:
        ecrire("Echecs :")
        for e in echecs[:25]:
            ecrire(f"- {e}")
        if len(echecs) > 25:
            ecrire(f"- ... et {len(echecs) - 25} autre(s)")
        return 1

    ecrire("Aucune violation. La comparaison affichee dans l'onglet "
           "Performance porte donc sur des plannings realisables, et le gain "
           "annonce n'est pas un artefact d'une reference invalide.")
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
