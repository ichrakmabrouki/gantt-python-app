"""
benchmark_solveurs.py — comparaison chiffree des deux formulations du solveur.

  v1  formulation MILP (grand M + variables booleennes de paires)  -> model_v1.py
  v2  formulation native CP-SAT (OnlyEnforceIf + AddNoOverlap)     -> model.py

Protocole : meme machine, memes 10 jeux de donnees, meme budget de temps.
Chaque planning produit est verifie par verifier_planning.py, independant du
solveur.

Lancer avec le bouton Run de VS Code, ou :
    python benchmark_solveurs.py

Produit :
    RAPPORT_COMPARAISON.md      rapport lisible, ecrit au fil de l'eau
    resultats_benchmark.json    donnees brutes
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

RAPPORT = RACINE / "RAPPORT_COMPARAISON.md"
JSON_OUT = RACINE / "resultats_benchmark.json"

BUDGET_SECONDES = 60.0          # identique pour tous les cas et les deux versions

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
_resultats: dict = {"budget_secondes": BUDGET_SECONDES, "cas": {}}


def ecrire(ligne: str = "") -> None:
    _lignes.append(ligne)
    try:
        print(ligne)
    except Exception:
        print(ligne.encode("ascii", "replace").decode("ascii"))
    try:
        RAPPORT.write_text("\n".join(_lignes) + "\n", encoding="utf-8")
        JSON_OUT.write_text(json.dumps(_resultats, indent=2, ensure_ascii=False),
                            encoding="utf-8")
    except Exception:
        pass


# ══════════════════════════════════════════════════════════════════════════════
# TAILLE DES MODELES (calcul analytique, sans construire quoi que ce soit)
# ══════════════════════════════════════════════════════════════════════════════
def taille_v1(data: dict) -> dict:
    modes, grp = data["modes"], data["grp_mchs"]
    mchs = {m for _, m in modes}
    techs = {t for t, _ in grp}
    ops_on_mch = {m: [o for o, m2 in modes if m2 == m] for m in mchs}
    tech_mchs = {t: [m for t2, m in grp if t2 == t] for t in techs}

    n_z = sum(len(o) * (len(o) - 1) for o in ops_on_mch.values())
    n_K = 0
    for t in techs:
        k = len({o for m in tech_mchs[t] for o in ops_on_mch.get(m, [])})
        n_K += k * (k - 1)
    n_tfs = sum(len(ops_on_mch.get(m, [])) for _, m in grp)
    n_base = len(modes) * 3
    return {"base": n_base, "paires_z": n_z, "paires_K": n_K, "tfs": n_tfs,
            "total": n_base + n_z + n_K + n_tfs}


def taille_v2(data: dict) -> dict:
    modes, grp = data["modes"], data["grp_mchs"]
    ops = {o for o, _ in modes}
    mch_tech: dict = {}
    for t, m in grp:
        mch_tech.setdefault(m, []).append(t)
    modes_op: dict = {}
    for o, m in modes:
        modes_op.setdefault(o, []).append(m)

    n_paires_to = 0
    for o in ops:
        techs = {t for m in modes_op[o] for t in mch_tech.get(m, [])}
        n_paires_to += len(techs)

    n_base = len(ops) * 3                 # S, E, S_bloc
    n_x = len(modes)                      # affectation
    n_int_mach = len(modes)               # intervalles machine
    n_tech = n_paires_to * 4              # u, TFS, debut_setup, intervalle
    return {"base": n_base, "affectation": n_x, "intervalles_machine": n_int_mach,
            "technicien": n_tech, "paires_z": 0, "paires_K": 0,
            "total": n_base + n_x + n_int_mach + n_tech + 1}


# ══════════════════════════════════════════════════════════════════════════════
# EXECUTION D'UNE VERSION SUR UN JEU DE DONNEES
# ══════════════════════════════════════════════════════════════════════════════
def executer(fonction, data: dict) -> dict:
    from verifier_planning import verifier_planning

    depart = time.time()
    try:
        with redirect_stdout(StringIO()):
            df = fonction(data, max_time_seconds=BUDGET_SECONDES)
        duree = time.time() - depart
        violations = verifier_planning(data, df)
        return {
            "statut": "resolu",
            "secondes": round(duree, 1),
            "operations": int(len(df)),
            "makespan": int(df["EndTime"].max()) if len(df) else 0,
            "valide": not violations,
            "violations": violations[:5],
            "nb_violations": len(violations),
        }
    except Exception as exc:
        return {
            "statut": "echec",
            "secondes": round(time.time() - depart, 1),
            "erreur": f"{type(exc).__name__}: {str(exc)[:120]}",
        }


def cellule(r: dict) -> str:
    if r["statut"] != "resolu":
        return f"echec — {r['erreur'][:44]}"
    marque = "valide" if r["valide"] else f"**{r['nb_violations']} VIOLATION(S)**"
    return f"{r['makespan']} min · {marque}"


# ══════════════════════════════════════════════════════════════════════════════
def main() -> int:
    from backend.solver.input_parser import parse_excel_to_dict, validate_excel_data
    from backend.solver.model import solve_flexible_jobshop as v2
    from backend.solver.model_v1 import solve_flexible_jobshop_v1 as v1

    debut_total = time.time()
    dossier = RACINE / "generated_test_excels"

    ecrire("# Comparaison des deux formulations du solveur")
    ecrire()
    ecrire(f"Genere le {datetime.now().strftime('%d/%m/%Y a %H:%M:%S')}")
    ecrire()
    ecrire(f"Protocole : meme machine, memes jeux de donnees, "
           f"budget de **{BUDGET_SECONDES:.0f} secondes** par instance pour les "
           f"deux versions. Chaque planning produit est verifie par "
           f"`verifier_planning.py`, independant du solveur.")

    # ── Chargement ────────────────────────────────────────────────────────────
    donnees = {}
    for nom in DATASETS:
        chemin = dossier / nom
        if not chemin.exists():
            continue
        try:
            data = parse_excel_to_dict(str(chemin))
            ok, _ = validate_excel_data(data)
            if ok:
                donnees[nom] = data
        except Exception:
            pass

    # ── Taille des modeles ────────────────────────────────────────────────────
    ecrire()
    ecrire("## 1. Taille des modeles")
    ecrire()
    ecrire("| Jeu de donnees | Operations | Variables v1 | Variables v2 | Facteur |")
    ecrire("|---|---|---|---|---|")
    for nom in DATASETS:
        data = donnees.get(nom)
        if not data:
            continue
        court = nom.replace(".xlsx", "").replace("dataset_", "")
        t1, t2 = taille_v1(data), taille_v2(data)
        facteur = t1["total"] / t2["total"] if t2["total"] else 0
        ecrire(f"| {court} | {data['params']['nbOps']} | {t1['total']:,} | "
               f"{t2['total']:,} | **/{facteur:.0f}** |".replace(",", " "))
        _resultats["cas"].setdefault(court, {})["operations"] = data["params"]["nbOps"]
        _resultats["cas"][court]["taille_v1"] = t1
        _resultats["cas"][court]["taille_v2"] = t2

    ecrire()
    ecrire("La v1 cree une variable booleenne par PAIRE d'operations (ordre sur "
           "une machine, ordre des setups d'un technicien). La v2 remplace ces "
           "paires par des intervalles optionnels confies a `AddNoOverlap`.")

    # ── Executions ────────────────────────────────────────────────────────────
    ecrire()
    ecrire("## 2. Resultats")
    ecrire()
    ecrire("| Jeu de donnees | Op. | v1 — temps | v1 — resultat | v2 — temps | v2 — resultat |")
    ecrire("|---|---|---|---|---|---|")
    ligne_index = len(_lignes)

    # On execute d'abord toutes les v2 (rapides), puis les v1, mais on affiche
    # le tableau par jeu de donnees. Les lignes sont donc reconstruites a la fin.
    mesures: dict = {}

    for nom in DATASETS:
        data = donnees.get(nom)
        if not data:
            continue
        court = nom.replace(".xlsx", "").replace("dataset_", "")
        r2 = executer(v2, data)
        mesures.setdefault(court, {})["v2"] = r2
        _resultats["cas"].setdefault(court, {})["v2"] = r2
        ecrire(f"| {court} | {data['params']['nbOps']} | _en attente_ | _en attente_ | "
               f"{r2['secondes']} s | {cellule(r2)} |")

    for nom in DATASETS:
        data = donnees.get(nom)
        if not data:
            continue
        court = nom.replace(".xlsx", "").replace("dataset_", "")
        r1 = executer(v1, data)
        mesures[court]["v1"] = r1
        _resultats["cas"][court]["v1"] = r1

    # Reconstruction du tableau complet
    nouvelles = []
    for nom in DATASETS:
        data = donnees.get(nom)
        if not data:
            continue
        court = nom.replace(".xlsx", "").replace("dataset_", "")
        r1, r2 = mesures[court]["v1"], mesures[court]["v2"]
        nouvelles.append(
            f"| {court} | {data['params']['nbOps']} | {r1['secondes']} s | "
            f"{cellule(r1)} | {r2['secondes']} s | {cellule(r2)} |"
        )
    _lignes[ligne_index:] = nouvelles

    # ── Synthese ──────────────────────────────────────────────────────────────
    resolus_v1 = sum(1 for c in mesures.values() if c["v1"]["statut"] == "resolu")
    resolus_v2 = sum(1 for c in mesures.values() if c["v2"]["statut"] == "resolu")
    valides_v1 = sum(1 for c in mesures.values()
                     if c["v1"]["statut"] == "resolu" and c["v1"]["valide"])
    valides_v2 = sum(1 for c in mesures.values()
                     if c["v2"]["statut"] == "resolu" and c["v2"]["valide"])
    total = len(mesures)

    ecrire()
    ecrire("## 3. Synthese")
    ecrire()
    ecrire("| Indicateur | v1 (grand M) | v2 (CP-SAT natif) |")
    ecrire("|---|---|---|")
    ecrire(f"| Instances resolues | {resolus_v1}/{total} | **{resolus_v2}/{total}** |")
    ecrire(f"| Plannings valides | {valides_v1}/{resolus_v1 or 1} | **{valides_v2}/{resolus_v2 or 1}** |")
    t1 = sum(c["v1"]["secondes"] for c in mesures.values())
    t2 = sum(c["v2"]["secondes"] for c in mesures.values())
    ecrire(f"| Temps total | {t1:.0f} s | **{t2:.0f} s** |")

    # Comparaison des makespans sur les cas resolus par les deux
    communs = [(k, c) for k, c in mesures.items()
               if c["v1"]["statut"] == "resolu" and c["v2"]["statut"] == "resolu"]
    if communs:
        ecrire()
        ecrire("### Qualite des solutions, sur les instances resolues par les deux")
        ecrire()
        ecrire("| Jeu de donnees | Makespan v1 | Makespan v2 | Ecart |")
        ecrire("|---|---|---|---|")
        for k, c in communs:
            m1, m2 = c["v1"]["makespan"], c["v2"]["makespan"]
            ecart = "identique" if m1 == m2 else (
                f"**v2 meilleur de {m1 - m2} min**" if m2 < m1
                else f"v2 moins bon de {m2 - m1} min")
            ecrire(f"| {k} | {m1} min | {m2} min | {ecart} |")

    ecrire()
    ecrire(f"Campagne terminee en {time.time() - debut_total:.0f} secondes.")
    print(f"\n>>> Rapport : {RAPPORT}\n>>> Donnees : {JSON_OUT}\n")
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
