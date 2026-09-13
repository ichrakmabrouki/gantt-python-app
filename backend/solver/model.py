# backend/solver/model.py
#
# VERSION 2 — reformulation native CP-SAT.
#
# La version 1 (conservee dans model_v1.py) encodait le probleme en style MILP :
# une contrainte "si A alors B" s'ecrivait avec une grande constante M, et
# l'ordre de passage sur une machine avec une variable booleenne PAR PAIRE
# d'operations. Sur 395 operations cela donnait 276 178 variables, dont 98 %
# de booleens de paires, et pres de 4 minutes rien que pour construire le modele.
#
# Cette version exprime les memes contraintes avec les primitives natives du
# solveur :
#
#   - grand M            -> OnlyEnforceIf (reification exacte, aucune constante)
#   - variables de paires -> intervalles optionnels + AddNoOverlap
#
# AddNoOverlap declenche les algorithmes d'ordonnancement dedies de CP-SAT
# (timetabling, edge-finding), qui raisonnent sur l'ensemble des taches d'une
# ressource au lieu de les comparer deux a deux.
#
# ── Correspondance avec les contraintes de la version 1 ──────────────────────
#
#   C1  assignation unique        -> AddExactlyOne
#   C2  duree = temps operatoire  -> porte par la taille de l'intervalle optionnel
#   C3  precedence des gammes     -> S[o2] >= E[o1], une contrainte par arc
#   C4  debut apres fin de setup  -> OnlyEnforceIf
#   C5  setup >= cte              -> OnlyEnforceIf
#   C6  debut >= cte              -> direct
#   C6b disponibilite machine     -> OnlyEnforceIf
#   C7  machine : non-chevauchement + cte -> AddNoOverlap sur intervalles
#                                            [S - cte, E] (le cte reserve
#                                            devant chaque operation impose
#                                            exactement S(o2) >= E(o1) + cte)
#   C8  technicien : setups serialises    -> AddNoOverlap sur les intervalles
#                                            de setup de chaque technicien
#   C9  setup du successeur de gamme      -> OnlyEnforceIf
#   C10 fin >= duree + setup              -> implique par C4 et C2, retire
#
# La semantique est identique a la version 1, y compris le fait qu'un setup est
# exige de CHAQUE technicien rattache a la machine (et non d'un seul). Ce choix
# est probablement involontaire dans le modele d'origine, mais il est conserve
# ici pour que la comparaison avant/apres porte sur la formulation et sur rien
# d'autre.

import pandas as pd
from ortools.sat.python import cp_model


def solve_flexible_jobshop(
    data: dict,
    max_time_seconds: float = 60.0,
    num_search_workers: int = 8,
    log_search_progress: bool = False,
    relative_gap_limit: float = 0.05,
) -> pd.DataFrame:
    model = cp_model.CpModel()

    params   = data['params']
    cte      = int(data['cte'])
    gammes   = data['gammes']
    modes    = data['modes']
    pt       = data['pt']
    grp_mchs = data['grp_mchs']
    machine_ready_times = {
        int(machine_id): int(ready_time)
        for machine_id, ready_time in data.get("machine_ready_times", {}).items()
    }

    nbOps = params['nbOps']

    # ── Horizon ───────────────────────────────────────────────────────────────
    horizon = (sum(pt.values()) + cte * nbOps * 2
               + max(machine_ready_times.values(), default=0))

    # ── Index ─────────────────────────────────────────────────────────────────
    all_ops  = sorted({o for (o, m) in modes})
    all_mchs = sorted({m for (o, m) in modes})

    ops_modes_map  = {o: [] for o in all_ops}
    ops_on_mch_map = {m: [] for m in all_mchs}
    for (o, m) in modes:
        ops_modes_map[o].append(m)
        ops_on_mch_map[m].append(o)

    mch_tech_map: dict[int, list[int]] = {m: [] for m in all_mchs}
    for (t, m) in grp_mchs:
        if m in mch_tech_map:
            mch_tech_map[m].append(t)

    # Techniciens pouvant intervenir sur une operation = techniciens de ses
    # machines candidates.
    op_techs: dict[int, set[int]] = {}
    for o in all_ops:
        techs = set()
        for m in ops_modes_map[o]:
            techs.update(mch_tech_map.get(m, []))
        op_techs[o] = techs

    # ══════════════════════════════════════════════════════════════════════════
    # VARIABLES
    # ══════════════════════════════════════════════════════════════════════════

    # Debut et fin PAR OPERATION (et non par mode) : c'est ce qui fait tomber
    # la precedence de O(modes x modes) a O(1) par arc de gamme.
    S, E, S_bloc = {}, {}, {}
    for o in all_ops:
        S[o]      = model.NewIntVar(0, horizon, f'S_{o}')
        E[o]      = model.NewIntVar(0, horizon, f'E_{o}')
        S_bloc[o] = model.NewIntVar(0, horizon, f'Sb_{o}')
        # Le bloc machine commence cte avant le debut de l'operation.
        model.Add(S_bloc[o] == S[o] - cte)

    x = {}
    intervalles_machine: dict[int, list] = {m: [] for m in all_mchs}
    for (o, m) in modes:
        x[o, m] = model.NewBoolVar(f'x_{o}_{m}')
        duree = int(pt.get((o, m), 0))
        # C2 + C7 : l'intervalle occupe la machine de S - cte a E, soit le
        # temps de setup reserve puis le temps operatoire.
        intervalles_machine[m].append(
            model.NewOptionalIntervalVar(
                S_bloc[o], cte + duree, E[o], x[o, m], f'bloc_{o}_{m}'
            )
        )

    # Setup par technicien.
    #
    # Le setup occupe exactement le creneau [S - cte, S], c'est-a-dire le prefixe
    # du bloc machine. C'est ce qui reproduit la contrainte C7 de la v1 : comme
    # ce creneau fait partie du bloc soumis a AddNoOverlap, le setup d'une
    # operation ne peut pas commencer avant la fin de l'operation precedente sur
    # la meme machine.
    #
    # Une premiere version laissait le setup flotter librement avant S. Elle
    # produisait des plannings ou le technicien preparait l'operation suivante
    # pendant que la machine tournait encore — un relachement par rapport a la
    # v1, qui faussait la comparaison. Le creneau est donc fixe.
    presence_tech = {}
    intervalles_tech: dict[int, list] = {}
    for o in all_ops:
        for t in op_techs[o]:
            machines_communes = [m for m in ops_modes_map[o]
                                 if t in mch_tech_map.get(m, [])]
            if not machines_communes:
                continue

            u = model.NewBoolVar(f'u_{t}_{o}')
            presence_tech[t, o] = u
            # u <=> l'operation est affectee a une machine couverte par t
            model.Add(sum(x[o, m] for m in machines_communes) == 1).OnlyEnforceIf(u)
            model.Add(sum(x[o, m] for m in machines_communes) == 0).OnlyEnforceIf(u.Not())

            intervalles_tech.setdefault(t, []).append(
                model.NewOptionalIntervalVar(
                    S_bloc[o], cte, S[o], u, f'setup_{t}_{o}'
                )
            )

    # ══════════════════════════════════════════════════════════════════════════
    # CONTRAINTES
    # ══════════════════════════════════════════════════════════════════════════

    # ── C1 : une operation sur exactement une machine ─────────────────────────
    for o in all_ops:
        model.AddExactlyOne(x[o, m] for m in ops_modes_map[o])

    # ── C6 : aucun demarrage avant le setup initial ───────────────────────────
    for o in all_ops:
        model.Add(S[o] >= cte)

    # ── C6bis : disponibilite initiale de la machine ──────────────────────────
    for (o, m) in modes:
        pret = machine_ready_times.get(m, 0)
        if pret > 0:
            model.Add(S[o] >= pret + cte).OnlyEnforceIf(x[o, m])

    # ── C7 : machine — non-chevauchement + cte entre deux operations ──────────
    for m in all_mchs:
        if len(intervalles_machine[m]) > 1:
            model.AddNoOverlap(intervalles_machine[m])

    # ── C8 : technicien — les setups ne se chevauchent pas ────────────────────
    for t, intervalles in intervalles_tech.items():
        if len(intervalles) > 1:
            model.AddNoOverlap(intervalles)

    # C4 (debut apres la fin du setup) et C5 (setup >= cte) sont desormais
    # portees par la geometrie du creneau [S - cte, S] et par S >= cte.

    # ── C3 : precedence des operations d'une meme piece ───────────────────────
    ops_par_job: dict[int, list] = {}
    for (op_id, job_id, pos) in gammes:
        ops_par_job.setdefault(int(job_id), []).append((int(pos), int(op_id)))

    arcs_gamme = []
    for job_id, sequence in ops_par_job.items():
        sequence.sort()
        for (_, o1), (_, o2) in zip(sequence, sequence[1:]):
            if o1 in S and o2 in S:
                model.Add(S[o2] >= E[o1])
                arcs_gamme.append((o1, o2))

    # ── C9 : setup du successeur de gamme sur une autre machine ───────────────
    #
    # v1 : tfs[t,o2,m2] >= cte + pt[o1,m1] + tfs[t,o1,m1]
    # Avec le setup cale sur [S - cte, S], tfs[t,o] vaut S[o] et pt[o1,m1] vaut
    # E[o1] - S[o1], donc la contrainte devient S[o2] >= E[o1] + cte : un
    # technicien qui suit une piece d'une machine a l'autre a besoin de cte
    # entre la fin d'une operation et le debut de la suivante.
    for (o1, o2) in arcs_gamme:
        for m1 in ops_modes_map[o1]:
            techs_m1 = set(mch_tech_map.get(m1, []))
            for m2 in ops_modes_map[o2]:
                if m1 == m2:
                    continue
                # v1 n'appliquait C9 que si un technicien couvrait les deux
                # machines : on garde exactement la meme condition.
                if not techs_m1 & set(mch_tech_map.get(m2, [])):
                    continue
                model.Add(
                    S[o2] >= E[o1] + cte
                ).OnlyEnforceIf([x[o1, m1], x[o2, m2]])

    # ── Objectif : minimiser le makespan ──────────────────────────────────────
    makespan = model.NewIntVar(0, horizon, 'makespan')
    model.AddMaxEquality(makespan, [E[o] for o in all_ops])
    model.Minimize(makespan)

    # ══════════════════════════════════════════════════════════════════════════
    # RESOLUTION
    # ══════════════════════════════════════════════════════════════════════════
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = max_time_seconds
    solver.parameters.num_search_workers = max(1, int(num_search_workers))
    solver.parameters.log_search_progress = log_search_progress
    solver.parameters.relative_gap_limit = max(0.0, float(relative_gap_limit))

    status = solver.Solve(model)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        raise ValueError(f"Pas de solution trouvée. Status: {solver.StatusName(status)}")

    # ── Extraction ────────────────────────────────────────────────────────────
    job_de_op = {int(g[0]): int(g[1]) for g in gammes}

    lignes = []
    for (o, m) in modes:
        if solver.Value(x[o, m]) != 1:
            continue
        debut = solver.Value(S[o])
        fin   = solver.Value(E[o])
        duree = int(pt.get((o, m), 0))
        job_id = job_de_op.get(o, 0)
        lignes.append({
            'OperationID':    o,
            'MachineID':      m,
            'MachineLabel':   f'Machine {m}',
            'JobID':          job_id,
            'JobLabel':       f'Job {job_id}',
            'StartTime':      debut,
            'EndTime':        fin,
            'Duration':       duree,
            'ProcessingTime': duree,
        })

    df = (pd.DataFrame(lignes)
          .sort_values(['JobID', 'StartTime'])
          .reset_index(drop=True))

    # ── Ecart a l'optimum ─────────────────────────────────────────────────────
    # Un planning valide n'est pas forcement un bon planning. CP-SAT connait
    # une borne inferieure sur le makespan : aucune solution ne peut faire
    # mieux. L'ecart entre la solution trouvee et cette borne dit de combien
    # on peut encore esperer progresser — 0 % signifie optimum prouve.
    valeur = solver.ObjectiveValue()
    borne = solver.BestObjectiveBound()
    ecart = (valeur - borne) / valeur if valeur > 0 else 0.0

    df.attrs.update({
        "makespan": int(valeur),
        "borne_inferieure": int(borne),
        "ecart_optimalite": float(ecart),
        "statut": solver.StatusName(status),
        "secondes": float(solver.WallTime()),
    })

    print(f"Makespan : {valeur} min")
    print(f"Borne    : {borne} min  (ecart {ecart:.1%})")
    print(f"Status   : {solver.StatusName(status)}")
    return df
