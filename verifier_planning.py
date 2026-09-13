"""
verifier_planning.py — controle de validite d'un planning produit par le solveur.

C'est le test le plus important d'un projet de recherche operationnelle : il ne
verifie pas que le solveur "tourne", mais que le planning qu'il produit
RESPECTE REELLEMENT toutes les contraintes du probleme. Un solveur peut rendre
une solution optimale... d'un modele faux.

Usage :
    python verifier_planning.py generated_test_excels/dataset_01_08pieces_cte10.xlsx
    python verifier_planning.py generated_test_excels/*.xlsx

Le script resout puis verifie. Il peut aussi etre importe :
    from verifier_planning import verifier_planning
    violations = verifier_planning(data, df_resultat)
"""

import sys
from pathlib import Path

import pandas as pd


def verifier_planning(data: dict, df: pd.DataFrame) -> list[str]:
    """Verifie un planning contre les donnees d'entree.

    Retourne la liste des violations trouvees. Liste vide = planning valide.
    """
    violations: list[str] = []

    cte = data["cte"]
    pt = data["pt"]
    modes = set(data["modes"])
    gammes = data["gammes"]
    grp_mchs = data.get("grp_mchs", [])

    rows = df.to_dict(orient="records")
    ops_planifiees = [int(r["OperationID"]) for r in rows]
    ops_attendues = {int(g[0]) for g in gammes}

    # ── C1 : chaque operation apparait exactement une fois ────────────────────
    manquantes = ops_attendues - set(ops_planifiees)
    if manquantes:
        violations.append(
            f"C1 assignation : {len(manquantes)} operation(s) absente(s) du "
            f"planning : {sorted(manquantes)[:10]}"
        )
    doublons = [o for o in set(ops_planifiees) if ops_planifiees.count(o) > 1]
    if doublons:
        violations.append(
            f"C1 assignation : {len(doublons)} operation(s) planifiee(s) "
            f"plusieurs fois : {sorted(doublons)[:10]}"
        )

    for r in rows:
        o, m = int(r["OperationID"]), int(r["MachineID"])
        debut, fin = int(r["StartTime"]), int(r["EndTime"])
        duree = int(r["Duration"])

        # ── C1bis : machine autorisee pour cette operation ────────────────────
        if (o, m) not in modes:
            violations.append(
                f"C1 machine : op {o} planifiee sur la machine {m}, "
                f"qui n'est pas dans ses modes autorises"
            )
            continue

        # ── C2 : duree conforme au temps operatoire declare ───────────────────
        duree_attendue = pt.get((o, m), 0)
        if duree != duree_attendue:
            violations.append(
                f"C2 duree : op {o} sur machine {m} -> duree {duree} "
                f"au lieu de {duree_attendue}"
            )
        if fin - debut < duree_attendue:
            violations.append(
                f"C2 intervalle : op {o} dure {fin - debut} min "
                f"({debut} -> {fin}) mais necessite {duree_attendue} min"
            )

        # ── C6 : demarrage au plus tot apres le setup initial ─────────────────
        if debut < cte:
            violations.append(
                f"C6 setup initial : op {o} demarre a {debut}, "
                f"avant le temps de setup cte={cte}"
            )

    # ── C7 : non-chevauchement + setup sur une meme machine ───────────────────
    par_machine: dict[int, list] = {}
    for r in rows:
        par_machine.setdefault(int(r["MachineID"]), []).append(r)

    for m, ops in par_machine.items():
        ops = sorted(ops, key=lambda r: int(r["StartTime"]))
        for precedente, suivante in zip(ops, ops[1:]):
            o1, o2 = int(precedente["OperationID"]), int(suivante["OperationID"])
            fin1, debut2 = int(precedente["EndTime"]), int(suivante["StartTime"])

            if debut2 < fin1:
                violations.append(
                    f"C7 chevauchement : machine {m}, op {o1} finit a {fin1} "
                    f"mais op {o2} demarre a {debut2}"
                )
            elif debut2 - fin1 < cte:
                violations.append(
                    f"C7 setup : machine {m}, seulement {debut2 - fin1} min "
                    f"entre op {o1} et op {o2} (cte={cte} requis)"
                )

    # ── C3 : precedence des operations d'une meme piece ───────────────────────
    planning = {int(r["OperationID"]): r for r in rows}
    par_job: dict[int, list] = {}
    for op_id, job_id, pos in gammes:
        par_job.setdefault(int(job_id), []).append((int(pos), int(op_id)))

    for job_id, sequence in par_job.items():
        sequence.sort()
        for (_, o1), (_, o2) in zip(sequence, sequence[1:]):
            if o1 not in planning or o2 not in planning:
                continue
            fin1 = int(planning[o1]["EndTime"])
            debut2 = int(planning[o2]["StartTime"])
            if debut2 < fin1:
                violations.append(
                    f"C3 precedence : piece {job_id}, op {o2} demarre a "
                    f"{debut2} alors que l'op {o1} qui la precede "
                    f"finit a {fin1}"
                )

    # ── C8 : un technicien ne fait qu'un setup a la fois ──────────────────────
    # Le setup d'une operation occupe le creneau [debut - cte, debut]. Deux
    # setups confies au meme technicien ne peuvent pas se chevaucher, meme sur
    # des machines differentes.
    techs_de_machine: dict[int, list[int]] = {}
    for t, m in grp_mchs:
        techs_de_machine.setdefault(int(m), []).append(int(t))

    setups_par_tech: dict[int, list[tuple[int, int, int, int]]] = {}
    for r in rows:
        o, m = int(r["OperationID"]), int(r["MachineID"])
        debut = int(r["StartTime"])
        for t in techs_de_machine.get(m, []):
            setups_par_tech.setdefault(t, []).append((debut - cte, debut, o, m))

    for t, setups in setups_par_tech.items():
        setups.sort()
        for (_, fin1, o1, m1), (debut2, _, o2, m2) in zip(setups, setups[1:]):
            if debut2 < fin1:
                violations.append(
                    f"C8 technicien : technicien {t}, le setup de l'op {o2} "
                    f"(machine {m2}) demarre a {debut2} alors que celui de "
                    f"l'op {o1} (machine {m1}) finit a {fin1}"
                )

    # ── C9 : changement de machine au sein d'une meme piece ───────────────────
    # Quand deux operations successives d'une piece tournent sur des machines
    # differentes couvertes par un meme technicien, il faut cte entre la fin de
    # l'une et le debut de l'autre.
    for job_id, sequence in par_job.items():
        for (_, o1), (_, o2) in zip(sequence, sequence[1:]):
            if o1 not in planning or o2 not in planning:
                continue
            m1 = int(planning[o1]["MachineID"])
            m2 = int(planning[o2]["MachineID"])
            if m1 == m2:
                continue
            if not set(techs_de_machine.get(m1, [])) & set(techs_de_machine.get(m2, [])):
                continue
            fin1 = int(planning[o1]["EndTime"])
            debut2 = int(planning[o2]["StartTime"])
            if debut2 - fin1 < cte:
                violations.append(
                    f"C9 changement de machine : piece {job_id}, seulement "
                    f"{debut2 - fin1} min entre l'op {o1} (machine {m1}) et "
                    f"l'op {o2} (machine {m2}), cte={cte} requis"
                )

    return violations


def _makespan(df: pd.DataFrame) -> int:
    return int(df["EndTime"].max()) if len(df) else 0


def _rapport(chemin: str, data: dict, df: pd.DataFrame) -> bool:
    violations = verifier_planning(data, df)
    nom = Path(chemin).name

    print(f"\n{'=' * 70}")
    print(f"  {nom}")
    print(f"{'=' * 70}")
    print(f"  Operations : {len(df)} / {data['params']['nbOps']} attendues")
    print(f"  Machines   : {df['MachineID'].nunique()}")
    print(f"  Makespan   : {_makespan(df)} min")
    print(f"  cte        : {data['cte']} min")

    if not violations:
        print("\n  RESULTAT : VALIDE — toutes les contraintes verifiees sont respectees")
        print("  (C1 assignation, C2 durees, C3 precedence, C6 setup initial,")
        print("   C7 non-chevauchement et setup machine)")
        return True

    print(f"\n  RESULTAT : {len(violations)} VIOLATION(S)")
    for v in violations[:25]:
        print(f"    - {v}")
    if len(violations) > 25:
        print(f"    ... et {len(violations) - 25} autre(s)")
    return False


def main(chemins: list[str]) -> int:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from backend.solver.input_parser import parse_excel_to_dict, validate_excel_data
    from backend.solver.model import solve_flexible_jobshop

    total, valides = 0, 0
    for chemin in chemins:
        total += 1
        try:
            data = parse_excel_to_dict(chemin)
            ok, msg = validate_excel_data(data)
            if not ok:
                print(f"\n  {Path(chemin).name} : donnees invalides — {msg}")
                continue
            df = solve_flexible_jobshop(data, max_time_seconds=60.0)
            if _rapport(chemin, data, df):
                valides += 1
        except Exception as exc:
            print(f"\n  {Path(chemin).name} : ECHEC — {type(exc).__name__}: {exc}")

    print(f"\n{'=' * 70}")
    print(f"  BILAN : {valides}/{total} planning(s) valide(s)")
    print(f"{'=' * 70}\n")
    print("  Note : la contrainte C8 (enchainement des setups d'un meme")
    print("  technicien sur des machines differentes) n'est pas verifiee ici,")
    print("  car elle porte sur des variables internes au modele et non sur")
    print("  le planning produit.\n")
    return 0 if valides == total else 1


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    sys.exit(main(sys.argv[1:]))
