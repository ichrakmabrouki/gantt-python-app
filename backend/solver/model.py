# backend/solver/model.py

from ortools.sat.python import cp_model
import pandas as pd

def solve_flexible_jobshop(data: dict) -> pd.DataFrame:
    """
    Résout le Job Shop Flexible avec contraintes de setup technicien.
    
    data = {
        'params': {'nbJobs': 13, 'nbMchs': 15, 'nbOps': 30},
        'nbtechs': 6,
        'cte': 15,
        'gammes': [(op_id, job_id, pos), ...],
        'modes': [(op_id, mch), ...],
        'pt': {(op_id, mch): duration, ...},
        'grp_mchs': [(tech_id, mch), ...]
    }
    """
    model = cp_model.CpModel()
    
    params   = data['params']
    cte      = data['cte']
    gammes   = data['gammes']
    modes    = data['modes']
    pt       = data['pt']
    grp_mchs = data['grp_mchs']
    nbtechs  = data['nbtechs']
    
    nbOps  = params['nbOps']
    nbMchs = params['nbMchs']
    M_big  = 10000
    
    # ── Horizon de temps ──────────────────────────────────────────────────────
    horizon = sum(pt.values()) + cte * nbOps * 2
    
    # ── Variables de décision ─────────────────────────────────────────────────
    
    # s[o,m], e[o,m] — start/end pour chaque mode (op, machine)
    s = {}
    e = {}
    for (o, m) in modes:
        s[o, m] = model.NewIntVar(0, horizon, f's_{o}_{m}')
        e[o, m] = model.NewIntVar(0, horizon, f'e_{o}_{m}')
    
    # x[o,m] — choix du mode (binaire)
    x = {}
    for (o, m) in modes:
        x[o, m] = model.NewBoolVar(f'x_{o}_{m}')
    
    # z[o1,o2,m] — séquençage sur même machine
    all_ops = list(set(o for (o, m) in modes))
    all_mchs = list(set(m for (o, m) in modes))
    
    z = {}
    for o1 in all_ops:
        for o2 in all_ops:
            if o1 != o2:
                for m in all_mchs:
                    z[o1, o2, m] = model.NewBoolVar(f'z_{o1}_{o2}_{m}')
    
    # K[t,o1,o2] — séquençage setup technicien
    all_techs = list(set(t for (t, m) in grp_mchs))
    K = {}
    for t in all_techs:
        for o1 in all_ops:
            for o2 in all_ops:
                if o1 != o2:
                    K[t, o1, o2] = model.NewBoolVar(f'K_{t}_{o1}_{o2}')
    
    # Temps_fin_setup[t,o,m]
    tfs = {}
    for (t, m_tech) in grp_mchs:
        for o in all_ops:
            tfs[t, o, m_tech] = model.NewIntVar(0, horizon, f'tfs_{t}_{o}_{m_tech}')
    
    # ── Contraintes ───────────────────────────────────────────────────────────
    
    # C1 : chaque opération assignée à exactement une machine
    for o in all_ops:
        ops_modes = [(o2, m) for (o2, m) in modes if o2 == o]
        model.Add(sum(x[o, m] for (o2, m) in ops_modes) == 1)
    
    # C2 : e >= s + pt * x
    for (o, m) in modes:
        model.Add(e[o, m] >= s[o, m] + pt.get((o, m), 0) * x[o, m])
    
    # C3 : précédence dans le job
    job_ops = {}
    for (op_id, job_id, pos) in gammes:
        if job_id not in job_ops:
            job_ops[job_id] = []
        job_ops[job_id].append((op_id, pos))
    
    for job_id, ops_list in job_ops.items():
        ops_sorted = sorted(ops_list, key=lambda x: x[1])
        for i in range(len(ops_sorted) - 1):
            o1, pos1 = ops_sorted[i]
            o2, pos2 = ops_sorted[i + 1]
            modes_o1 = [m for (op, m) in modes if op == o1]
            modes_o2 = [m for (op, m) in modes if op == o2]
            for m2 in modes_o2:
                for m1 in modes_o1:
                    if (o2, m2) in s and (o1, m1) in e:
                        model.Add(
                            s[o2, m2] >= e[o1, m1] - M_big * (1 - x[o2, m2])
                        )
    
    # C4 : s[o,m] >= tfs[tech, o, m]
    for (o, m) in modes:
        for (t, m_tech) in grp_mchs:
            if m_tech == m and (t, o, m) in tfs:
                model.Add(s[o, m] >= tfs[t, o, m] - M_big * (1 - x[o, m]))
    
    # C5 : tfs[t,o,m] >= cte
    for (t, o, m) in tfs:
        model.Add(tfs[t, o, m] >= cte)
    
    # C6 : s[o,m] >= cte
    for (o, m) in modes:
        model.Add(s[o, m] >= cte)
    
    # C7 : non-chevauchement + setup sur même machine
    for (t, m_tech) in grp_mchs:
        ops_on_m = [o for (o, m) in modes if m == m_tech]
        for o1 in ops_on_m:
            for o2 in ops_on_m:
                if o1 != o2 and (o2, o1, m_tech) in z:
                    if (t, o2, m_tech) in tfs and (o1, m_tech) in e:
                        model.Add(
                            tfs[t, o2, m_tech] >= cte + e[o1, m_tech]
                            - M_big * (1 - z[o2, o1, m_tech])
                        )
    
    # C8 : setup consécutifs par même technicien sur machines différentes
    for t in all_techs:
        techs_mchs = [m for (t2, m) in grp_mchs if t2 == t]
        for m1 in techs_mchs:
            for m2 in techs_mchs:
                if m1 != m2:
                    ops_m1 = [o for (o, m) in modes if m == m1]
                    ops_m2 = [o for (o, m) in modes if m == m2]
                    for o1 in ops_m1:
                        for o2 in ops_m2:
                            if o1 != o2:
                                if (t, o2, o1) in K and (t, o2, m2) in tfs and (t, o1, m1) in tfs:
                                    model.Add(
                                        tfs[t, o2, m2] >= cte + tfs[t, o1, m1]
                                        - M_big * (1 - K[t, o2, o1])
                                    )
    
    # C9 : setup entre opérations successives du même job
    for job_id, ops_list in job_ops.items():
        ops_sorted = sorted(ops_list, key=lambda x: x[1])
        for i in range(len(ops_sorted) - 1):
            o1, _ = ops_sorted[i]
            o2, _ = ops_sorted[i + 1]
            modes_o1 = [m for (op, m) in modes if op == o1]
            modes_o2 = [m for (op, m) in modes if op == o2]
            for m1 in modes_o1:
                for m2 in modes_o2:
                    if m1 != m2:
                        for (t1, mt1) in grp_mchs:
                            for (t2, mt2) in grp_mchs:
                                if mt1 == m1 and mt2 == m2:
                                    if (t2, o2, m2) in tfs and (t1, o1, m1) in tfs:
                                        model.Add(
                                            tfs[t2, o2, m2] >= cte + pt.get((o1, m1), 0) + tfs[t1, o1, m1]
                                            - M_big * (1 - x[o1, m1])
                                        )
    
    # C10 : fin de deux opérations successives du même job
    for job_id, ops_list in job_ops.items():
        ops_sorted = sorted(ops_list, key=lambda x: x[1])
        for i in range(len(ops_sorted) - 1):
            o1, _ = ops_sorted[i]
            o2, _ = ops_sorted[i + 1]
            modes_o2 = [m for (op, m) in modes if op == o2]
            for m2 in modes_o2:
                for (t2, mt2) in grp_mchs:
                    if mt2 == m2 and (t2, o2, m2) in tfs:
                        model.Add(
                            e[o2, m2] >= pt.get((o2, m2), 0) + tfs[t2, o2, m2]
                            - M_big * (1 - x[o2, m2])
                        )
    
    # ── Objectif : minimiser le makespan ─────────────────────────────────────
    makespan = model.NewIntVar(0, horizon, 'makespan')
    for (o, m) in modes:
        model.Add(makespan >= e[o, m])
    model.Minimize(makespan)
    
    # ── Résolution ────────────────────────────────────────────────────────────
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 300.0
    solver.parameters.num_search_workers = 8
    
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
                'OperationID':  o,
                'MachineID':    m,
                'MachineLabel': f'Machine {m}',
                'JobID':        job_id,
                'StartTime':    start,
                'EndTime':      end,
                'Duration':     dur,
                'ProcessingTime': dur,
            })
    
    df = pd.DataFrame(rows)
    print(f"✅ Makespan optimal : {solver.ObjectiveValue()} min")
    return df