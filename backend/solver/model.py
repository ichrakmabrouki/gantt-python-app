# backend/solver/model.py

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
    cte      = data['cte']
    gammes   = data['gammes']
    modes    = data['modes']
    pt       = data['pt']
    grp_mchs = data['grp_mchs']
    machine_ready_times = {
        int(machine_id): int(ready_time)
        for machine_id, ready_time in data.get("machine_ready_times", {}).items()
    }

    nbOps  = params['nbOps']
    M_big  = 10000

    # ── Horizon ───────────────────────────────────────────────────────────────
    horizon = sum(pt.values()) + cte * nbOps * 2 + max(machine_ready_times.values(), default=0)

    # ── Index utiles ──────────────────────────────────────────────────────────
    all_ops   = list(set(o for (o, m) in modes))
    all_mchs  = list(set(m for (o, m) in modes))
    all_techs = list(set(t for (t, m) in grp_mchs))

    ops_modes_map  = {o: [m for (o2, m) in modes if o2 == o] for o in all_ops}
    ops_on_mch_map = {m: [o for (o, m2) in modes if m2 == m] for m in all_mchs}
    tech_mchs_map  = {t: [m for (t2, m) in grp_mchs if t2 == t] for t in all_techs}
    mch_tech_map   = {m: [t for (t, m2) in grp_mchs if m2 == m] for m in all_mchs}

    # ── Variables ─────────────────────────────────────────────────────────────
    s, e, x = {}, {}, {}
    for (o, m) in modes:
        s[o, m] = model.NewIntVar(0, horizon, f's_{o}_{m}')
        e[o, m] = model.NewIntVar(0, horizon, f'e_{o}_{m}')
        x[o, m] = model.NewBoolVar(f'x_{o}_{m}')

    # z[o1,o2,m] — o1 avant o2 sur machine m
    z = {}
    for m in all_mchs:
        ops = ops_on_mch_map[m]
        for i, o1 in enumerate(ops):
            for o2 in ops[i+1:]:
                z[o1, o2, m] = model.NewBoolVar(f'z_{o1}_{o2}_{m}')
                z[o2, o1, m] = model.NewBoolVar(f'z_{o2}_{o1}_{m}')

    # K[t,o1,o2] — o1 avant o2 pour technicien t
    K = {}
    for t in all_techs:
        mchs_t = tech_mchs_map[t]
        ops_t  = list(set(o for m in mchs_t for o in ops_on_mch_map.get(m, [])))
        for i, o1 in enumerate(ops_t):
            for o2 in ops_t[i+1:]:
                K[t, o1, o2] = model.NewBoolVar(f'K_{t}_{o1}_{o2}')
                K[t, o2, o1] = model.NewBoolVar(f'K_{t}_{o2}_{o1}')

    # tfs[t,o,m] — temps fin setup technicien t pour op o sur machine m
    tfs = {}
    for (t, m_tech) in grp_mchs:
        for o in ops_on_mch_map.get(m_tech, []):
            tfs[t, o, m_tech] = model.NewIntVar(0, horizon, f'tfs_{t}_{o}_{m_tech}')

    # ── C1 : chaque opération assignée à exactement une machine ───────────────
    for o in all_ops:
        model.Add(sum(x[o, m] for m in ops_modes_map[o]) == 1)

    # ── C2 : fin = début + durée si op assignée ───────────────────────────────
    for (o, m) in modes:
        model.Add(e[o, m] >= s[o, m] + pt.get((o, m), 0) * x[o, m])

    # ── C3 : précédence dans le job ───────────────────────────────────────────
    job_ops = {}
    for (op_id, job_id, pos) in gammes:
        if job_id not in job_ops:
            job_ops[job_id] = []
        job_ops[job_id].append((op_id, pos))

    for job_id, ops_list in job_ops.items():
        ops_sorted = sorted(ops_list, key=lambda x: x[1])
        for i in range(len(ops_sorted) - 1):
            o1, _ = ops_sorted[i]
            o2, _ = ops_sorted[i + 1]
            for m1 in ops_modes_map[o1]:
                for m2 in ops_modes_map[o2]:
                    # Si o1 assigné à m1 ET o2 assigné à m2 :
                    # o2 commence après la fin de o1
                    model.Add(
                        s[o2, m2] >= e[o1, m1]
                        - M_big * (1 - x[o1, m1])
                        - M_big * (1 - x[o2, m2])
                    )

    # ── C4 : début op >= fin setup technicien ────────────────────────────────
    for (o, m) in modes:
        for t in mch_tech_map.get(m, []):
            if (t, o, m) in tfs:
                model.Add(
                    s[o, m] >= tfs[t, o, m] - M_big * (1 - x[o, m])
                )

    # ── C5 : setup >= cte (si op assignée) ───────────────────────────────────
    for (t, o, m) in tfs:
        model.Add(tfs[t, o, m] >= cte).OnlyEnforceIf(x[o, m])

    # ── C6 : début >= cte (si op assignée) ───────────────────────────────────
    for (o, m) in modes:
        model.Add(s[o, m] >= cte).OnlyEnforceIf(x[o, m])

    # ── C6bis : continuité selon disponibilité machine ───────────────────────
    for (o, m) in modes:
        ready_time = machine_ready_times.get(m, 0)
        if ready_time > 0:
            model.Add(s[o, m] >= ready_time + cte).OnlyEnforceIf(x[o, m])

    # ── C7 : non-chevauchement + setup sur même machine ──────────────────────
    for m in all_mchs:
        ops     = ops_on_mch_map[m]
        techs_m = mch_tech_map.get(m, [])
        for i, o1 in enumerate(ops):
            for o2 in ops[i+1:]:
                if (o1, o2, m) not in z or (o2, o1, m) not in z:
                    continue

                # Exactement un ordre si les deux ops assignées à m
                model.Add(
                    z[o1, o2, m] + z[o2, o1, m] >= x[o1, m] + x[o2, m] - 1
                )
                model.Add(
                    z[o1, o2, m] + z[o2, o1, m] <= 1
                )

                # z actif seulement si les deux ops sur m
                model.Add(z[o1, o2, m] <= x[o1, m])
                model.Add(z[o1, o2, m] <= x[o2, m])
                model.Add(z[o2, o1, m] <= x[o1, m])
                model.Add(z[o2, o1, m] <= x[o2, m])

                # Non-chevauchement avec setup pour chaque technicien de m
                for t in techs_m:
                    if (t, o2, m) in tfs:
                        model.Add(
                            tfs[t, o2, m] >= cte + e[o1, m]
                            - M_big * (1 - z[o1, o2, m])
                        )
                    if (t, o1, m) in tfs:
                        model.Add(
                            tfs[t, o1, m] >= cte + e[o2, m]
                            - M_big * (1 - z[o2, o1, m])
                        )

    # ── C8 : setup consécutifs par même technicien sur machines différentes ───
    for t in all_techs:
        mchs_t = tech_mchs_map[t]
        ops_t  = list(set(o for m in mchs_t for o in ops_on_mch_map.get(m, [])))

        for i, o1 in enumerate(ops_t):
            for o2 in ops_t[i+1:]:
                if (t, o1, o2) not in K:
                    continue

                x_o1_on_t = [x[o1, m] for m in mchs_t if (o1, m) in x]
                x_o2_on_t = [x[o2, m] for m in mchs_t if (o2, m) in x]

                if not x_o1_on_t or not x_o2_on_t:
                    continue

                active_o1  = model.NewBoolVar(f'active_{t}_{o1}')
                active_o2  = model.NewBoolVar(f'active_{t}_{o2}')
                both_active = model.NewBoolVar(f'both_{t}_{o1}_{o2}')

                model.Add(sum(x_o1_on_t) >= 1).OnlyEnforceIf(active_o1)
                model.Add(sum(x_o1_on_t) == 0).OnlyEnforceIf(active_o1.Not())
                model.Add(sum(x_o2_on_t) >= 1).OnlyEnforceIf(active_o2)
                model.Add(sum(x_o2_on_t) == 0).OnlyEnforceIf(active_o2.Not())

                model.AddBoolAnd([active_o1, active_o2]).OnlyEnforceIf(both_active)
                model.AddBoolOr([active_o1.Not(), active_o2.Not()]).OnlyEnforceIf(both_active.Not())

                # Exactement un ordre si les deux actives
                model.Add(K[t, o1, o2] + K[t, o2, o1] == 1).OnlyEnforceIf(both_active)
                model.Add(K[t, o1, o2] == 0).OnlyEnforceIf(both_active.Not())
                model.Add(K[t, o2, o1] == 0).OnlyEnforceIf(both_active.Not())

                # Propagation du setup entre machines différentes
                for m1 in mchs_t:
                    for m2 in mchs_t:
                        if m1 == m2:
                            continue
                        if (t, o1, m1) in tfs and (t, o2, m2) in tfs:
                            model.Add(
                                tfs[t, o2, m2] >= cte + tfs[t, o1, m1]
                                - M_big * (1 - K[t, o1, o2])
                                - M_big * (1 - x[o1, m1])
                                - M_big * (1 - x[o2, m2])
                            )
                        if (t, o2, m2) in tfs and (t, o1, m1) in tfs:
                            model.Add(
                                tfs[t, o1, m1] >= cte + tfs[t, o2, m2]
                                - M_big * (1 - K[t, o2, o1])
                                - M_big * (1 - x[o2, m2])
                                - M_big * (1 - x[o1, m1])
                            )

    # ── C9 : setup entre opérations successives du même job ──────────────────
    for job_id, ops_list in job_ops.items():
        ops_sorted = sorted(ops_list, key=lambda x: x[1])
        for i in range(len(ops_sorted) - 1):
            o1, _ = ops_sorted[i]
            o2, _ = ops_sorted[i + 1]
            for m1 in ops_modes_map[o1]:
                for m2 in ops_modes_map[o2]:
                    if m1 == m2:
                        continue
                    for t in mch_tech_map.get(m2, []):
                        if (t, o2, m2) in tfs and (t, o1, m1) in tfs:
                            model.Add(
                                tfs[t, o2, m2] >= cte + pt.get((o1, m1), 0) + tfs[t, o1, m1]
                                - M_big * (1 - x[o1, m1])
                                - M_big * (1 - x[o2, m2])
                            )

    # ── C10 : fin op >= durée + tfs ───────────────────────────────────────────
    for (o, m) in modes:
        for t in mch_tech_map.get(m, []):
            if (t, o, m) in tfs:
                model.Add(
                    e[o, m] >= pt.get((o, m), 0) + tfs[t, o, m]
                    - M_big * (1 - x[o, m])
                )

    # ── Objectif : minimiser le makespan ─────────────────────────────────────
    makespan = model.NewIntVar(0, horizon, 'makespan')
    for (o, m) in modes:
        model.Add(makespan >= e[o, m] - M_big * (1 - x[o, m]))
    model.Minimize(makespan)

    # ── Résolution ────────────────────────────────────────────────────────────
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = max_time_seconds
    solver.parameters.num_search_workers = max(1, int(num_search_workers))
    solver.parameters.log_search_progress = log_search_progress
    solver.parameters.relative_gap_limit = max(0.0, float(relative_gap_limit))

    status = solver.Solve(model)

    if status not in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
        raise ValueError(f"Pas de solution trouvée. Status: {solver.StatusName(status)}")

    # ── Extraction des résultats ──────────────────────────────────────────────
    rows = []
    for (o, m) in modes:
        if solver.Value(x[o, m]) == 1:
            start  = solver.Value(s[o, m])
            end    = solver.Value(e[o, m])
            dur    = pt.get((o, m), 0)
            job_id = next((g[1] for g in gammes if g[0] == o), 0)
            rows.append({
                'OperationID':    o,
                'MachineID':      m,
                'MachineLabel':   f'Machine {m}',
                'JobID':          job_id,
                'JobLabel':       f'Job {job_id}',
                'StartTime':      start,
                'EndTime':        end,
                'Duration':       dur,
                'ProcessingTime': dur,
            })

    df = pd.DataFrame(rows).sort_values(['JobID', 'StartTime']).reset_index(drop=True)
    print(f"Makespan : {solver.ObjectiveValue()} min")
    print(f"Status   : {solver.StatusName(status)}")
    return df
