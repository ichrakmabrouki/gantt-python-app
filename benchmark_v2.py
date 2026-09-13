"""
benchmark_v2.py — mesure la version 2 du solveur seule.

La version 1 etant inchangee, ses mesures proviennent de la campagne
benchmark_solveurs.py (meme machine, meme budget, memes jeux de donnees).
Ce script rejoue uniquement la v2 apres correction du creneau de setup.

Lancer avec le bouton Run de VS Code, ou :
    python benchmark_v2.py

Produit : resultats_v2.json  et  RAPPORT_V2.md
"""

import json
import sys
import time
import traceback
from contextlib import redirect_stdout
from datetime import datetime
from io import StringIO
from pathlib import Path

RACINE = Path(__file__).resolve().parent
sys.path.insert(0, str(RACINE))

RAPPORT = RACINE / "RAPPORT_V2.md"
JSON_OUT = RACINE / "resultats_v2.json"

BUDGET_SECONDES = 60.0

DATASETS = [
    "dataset_01_08pieces_cte10.xlsx",
    "dataset_02_12pieces_cte12.xlsx",
    "dataset_03_20pieces_cte15.xlsx",
    "dataset_04_25pieces_cte15.xlsx",
    "dataset_05_35pieces_cte18.xlsx",
    "dataset_06_45pieces_cte20.xlsx",
    "dataset_07_60pieces_cte22.xlsx",
    "dataset_08_75pieces_cte25.xlsx",
    "dataset_09_90pieces_cte28.xlsx",
    "dataset_10_100pieces_cte30.xlsx",
]

_lignes: list[str] = []
_res: dict = {"budget_secondes": BUDGET_SECONDES, "version": "v2", "cas": {}}


def ecrire(ligne: str = "") -> None:
    _lignes.append(ligne)
    try:
        print(ligne)
    except Exception:
        print(ligne.encode("ascii", "replace").decode("ascii"))
    try:
        RAPPORT.write_text("\n".join(_lignes) + "\n", encoding="utf-8")
        JSON_OUT.write_text(json.dumps(_res, indent=2, ensure_ascii=False),
                            encoding="utf-8")
    except Exception:
        pass


def taille_v2(data: dict) -> int:
    modes, grp = data["modes"], data["grp_mchs"]
    ops = {o for o, _ in modes}
    mch_tech: dict = {}
    for t, m in grp:
        mch_tech.setdefault(m, []).append(t)
    modes_op: dict = {}
    for o, m in modes:
        modes_op.setdefault(o, []).append(m)
    n_to = sum(len({t for m in modes_op[o] for t in mch_tech.get(m, [])})
               for o in ops)
    return len(ops) * 3 + len(modes) * 2 + n_to * 2 + 1


def main() -> int:
    from backend.solver.input_parser import parse_excel_to_dict, validate_excel_data
    from backend.solver.model import solve_flexible_jobshop
    from verifier_planning import verifier_planning

    depart_total = time.time()
    dossier = RACINE / "generated_test_excels"

    ecrire("# Version 2 du solveur — mesures")
    ecrire()
    ecrire(f"Genere le {datetime.now().strftime('%d/%m/%Y a %H:%M:%S')}")
    ecrire()
    ecrire(f"Budget : **{BUDGET_SECONDES:.0f} secondes** par instance. "
           f"Chaque planning est verifie par `verifier_planning.py`.")
    ecrire()
    ecrire("| Jeu de donnees | Operations | Variables | Temps | Makespan | Borne inf. | Ecart | Planning valide |")
    ecrire("|---|---|---|---|---|---|---|---|")

    for nom in DATASETS:
        chemin = dossier / nom
        if not chemin.exists():
            continue
        court = nom.replace(".xlsx", "").replace("dataset_", "")
        try:
            data = parse_excel_to_dict(str(chemin))
            ok, msg = validate_excel_data(data)
            if not ok:
                ecrire(f"| {court} | — | — | — | — | donnees invalides : {msg[:40]} |")
                continue
        except Exception as exc:
            ecrire(f"| {court} | — | — | — | — | lecture impossible : {type(exc).__name__} |")
            continue

        nb_var = taille_v2(data)
        depart = time.time()
        try:
            with redirect_stdout(StringIO()):
                df = solve_flexible_jobshop(data, max_time_seconds=BUDGET_SECONDES)
            duree = time.time() - depart
            violations = verifier_planning(data, df)
            makespan = int(df["EndTime"].max()) if len(df) else 0
            verdict = "oui" if not violations else f"**NON — {len(violations)}**"
            infos = getattr(df, "attrs", {}) or {}
            borne = infos.get("borne_inferieure", "—")
            ecart = infos.get("ecart_optimalite")
            cel_ecart = "—" if ecart is None else (
                "**optimal**" if ecart <= 0.0001 else f"{ecart:.1%}")
            ecrire(f"| {court} | {data['params']['nbOps']} | {nb_var:,} | "
                   f"{duree:.1f} s | {makespan} min | {borne} min | {cel_ecart} | "
                   f"{verdict} |".replace(",", " "))
            _res["cas"][court] = {
                "operations": data["params"]["nbOps"],
                "variables": nb_var,
                "statut": "resolu",
                "secondes": round(duree, 1),
                "makespan": makespan,
                "borne_inferieure": infos.get("borne_inferieure"),
                "ecart_optimalite": infos.get("ecart_optimalite"),
                "statut_solveur": infos.get("statut"),
                "valide": not violations,
                "nb_violations": len(violations),
                "violations": violations[:5],
            }
        except Exception as exc:
            duree = time.time() - depart
            ecrire(f"| {court} | {data['params']['nbOps']} | {nb_var:,} | "
                   f"{duree:.1f} s | — | — | — | echec : {type(exc).__name__}: "
                   f"{str(exc)[:50]} |".replace(",", " "))
            _res["cas"][court] = {
                "operations": data["params"]["nbOps"],
                "variables": nb_var,
                "statut": "echec",
                "secondes": round(duree, 1),
                "erreur": f"{type(exc).__name__}: {str(exc)[:120]}",
            }

    resolus = sum(1 for c in _res["cas"].values() if c["statut"] == "resolu")
    valides = sum(1 for c in _res["cas"].values()
                  if c["statut"] == "resolu" and c["valide"])
    ecrire()
    ecrire(f"**{resolus}/{len(_res['cas'])} instances resolues, "
           f"{valides}/{resolus or 1} plannings valides.** "
           f"Campagne terminee en {time.time() - depart_total:.0f} secondes.")
    print(f"\n>>> {RAPPORT}\n>>> {JSON_OUT}\n")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        ecrire()
        ecrire("```")
        ecrire(traceback.format_exc()[:3000])
        ecrire("```")
        sys.exit(1)
