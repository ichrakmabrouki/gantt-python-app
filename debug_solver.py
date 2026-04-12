# debug_solver.py
# Lance avec : python debug_solver.py

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ortools.sat.python import cp_model
from backend.solver.input_parser import DATA

def test_with_constraints(label, build_fn):
    model = cp_model.CpModel()
    build_fn(model)
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 30.0
    status = solver.Solve(model)
    name = solver.StatusName(status)
    icon = "✅" if status in [cp_model.OPTIMAL, cp_model.FEASIBLE] else "❌"
    print(f"{icon} {label} → {name}")
    return status in [cp_model.OPTIMAL, cp_model.FEASIBLE]

# ── Données ───────────────────────────────────────────────────────────────────
cte      = DATA['cte']
gammes   = DATA['gammes']
modes    = DATA['modes']
pt       = DATA['pt']
grp_mchs = DATA['grp_mchs']
nbOps    = DATA['params']['nbOps']
M_big    = 10000
horizon  = sum(pt.values()) + cte * nbOps * 2

all_ops   = list(set(o for (o, m) in modes))
all_mchs  = list(set(m for (o, m) in modes))
all_techs = list(set(t for (t, m) in grp_mchs))

ops_modes_map  = {o: [m for (o2, m) in modes if o2 == o] for o in all_ops}
ops_on_mch_map = {m: [o for (o, m2) in modes if m2 == m] for m in all_mchs}
tech_mchs_map  = {t: [m for (t2, m) in grp_mchs if t2 == t] for t in all_techs}
mch_tech_map   = {m: [t for (t, m2) in grp_mchs if m2 == m] for m in all_mchs}

job_ops = {}
for (op_id, job_id, pos) in gammes:
    if job_id not in job_ops:
        job_ops[job_id] = []
    job_ops[job_id].append((op_id, pos))

def make_base(model):
    s, e, x = {}, {}, {}
    for (o, m) in modes:
        s[o, m] = model.NewIntVar(0, horizon, f's_{o}_{m}')
        e[o, m] = model.NewIntVar(0, horizon, f'e_{o}_{m}')
        x[o, m] = model.NewBoolVar(f'x_{o}_{m}')
    return s, e, x

# ── TEST 1 : C1 seule ─────────────────────────────────────────────────────────
def build_c1(model):
    s, e, x = make_base(model)
    for o in all_ops:
        model.Add(sum(x[o, m] for m in ops_modes_map[o]) == 1)

test_with_constraints("C1 seule", build_c1)

# ── TEST 2 : C1 + C2 ─────────────────────────────────────────────────────────
def build_c1_c2(model):
    s, e, x = make_base(model)
    for o in all_ops:
        model.Add(sum(x[o, m] for m in ops_modes_map[o]) == 1)
    for (o, m) in modes:
        model.Add(e[o, m] >= s[o, m] + pt.get((o, m), 0) * x[o, m])

test_with_constraints("C1 + C2", build_c1_c2)

# ── TEST 3 : C1 + C2 + C3 ────────────────────────────────────────────────────
def build_c1_c2_c3(model):
    s, e, x = make_base(model)
    for o in all_ops:
        model.Add(sum(x[o, m] for m in ops_modes_map[o]) == 1)
    for (o, m) in modes:
        model.Add(e[o, m] >= s[o, m] + pt.get((o, m), 0) * x[o, m])
    for job_id, ops_list in job_ops.items():
        ops_sorted = sorted(ops_list, key=lambda x: x[1])
        for i in range(len(ops_sorted) - 1):
            o1, _ = ops_sorted[i]
            o2, _ = ops_sorted[i + 1]
            for m1 in ops_modes_map[o1]:
                for m2 in ops_modes_map[o2]:
                    model.Add(
                        s[o2, m2] >= e[o1, m1]
                        - M_big * (1 - x[o1, m1])
                        - M_big * (1 - x[o2, m2])
                    )

test_with_constraints("C1 + C2 + C3", build_c1_c2_c3)

# ── TEST 4 : + C5 + C6 ───────────────────────────────────────────────────────
def build_c1_c2_c3_c5_c6(model):
    s, e, x = make_base(model)
    tfs = {}
    for (t, m_tech) in grp_mchs:
        for o in ops_on_mch_map.get(m_tech, []):
            tfs[t, o, m_tech] = model.NewIntVar(0, horizon, f'tfs_{t}_{o}_{m_tech}')
    for o in all_ops:
        model.Add(sum(x[o, m] for m in ops_modes_map[o]) == 1)
    for (o, m) in modes:
        model.Add(e[o, m] >= s[o, m] + pt.get((o, m), 0) * x[o, m])
    for job_id, ops_list in job_ops.items():
        ops_sorted = sorted(ops_list, key=lambda x: x[1])
        for i in range(len(ops_sorted) - 1):
            o1, _ = ops_sorted[i]
            o2, _ = ops_sorted[i + 1]
            for m1 in ops_modes_map[o1]:
                for m2 in ops_modes_map[o2]:
                    model.Add(
                        s[o2, m2] >= e[o1, m1]
                        - M_big * (1 - x[o1, m1])
                        - M_big * (1 - x[o2, m2])
                    )
    for (t, o, m) in tfs:
        model.Add(tfs[t, o, m] >= cte).OnlyEnforceIf(x[o, m])
    for (o, m) in modes:
        model.Add(s[o, m] >= cte).OnlyEnforceIf(x[o, m])

test_with_constraints("C1+C2+C3+C5+C6", build_c1_c2_c3_c5_c6)

# ── TEST 5 : + C4 ────────────────────────────────────────────────────────────
def build_c1_c2_c3_c4_c5_c6(model):
    s, e, x = make_base(model)
    tfs = {}
    for (t, m_tech) in grp_mchs:
        for o in ops_on_mch_map.get(m_tech, []):
            tfs[t, o, m_tech] = model.NewIntVar(0, horizon, f'tfs_{t}_{o}_{m_tech}')
    for o in all_ops:
        model.Add(sum(x[o, m] for m in ops_modes_map[o]) == 1)
    for (o, m) in modes:
        model.Add(e[o, m] >= s[o, m] + pt.get((o, m), 0) * x[o, m])
    for job_id, ops_list in job_ops.items():
        ops_sorted = sorted(ops_list, key=lambda x: x[1])
        for i in range(len(ops_sorted) - 1):
            o1, _ = ops_sorted[i]
            o2, _ = ops_sorted[i + 1]
            for m1 in ops_modes_map[o1]:
                for m2 in ops_modes_map[o2]:
                    model.Add(
                        s[o2, m2] >= e[o1, m1]
                        - M_big * (1 - x[o1, m1])
                        - M_big * (1 - x[o2, m2])
                    )
    for (o, m) in modes:
        for t in mch_tech_map.get(m, []):
            if (t, o, m) in tfs:
                model.Add(s[o, m] >= tfs[t, o, m] - M_big * (1 - x[o, m]))
    for (t, o, m) in tfs:
        model.Add(tfs[t, o, m] >= cte).OnlyEnforceIf(x[o, m])
    for (o, m) in modes:
        model.Add(s[o, m] >= cte).OnlyEnforceIf(x[o, m])

test_with_constraints("C1+C2+C3+C4+C5+C6", build_c1_c2_c3_c4_c5_c6)
# ── TEST 6 : + C7 (non-chevauchement) ────────────────────────────────────────
def build_jusqu_c7(model):
    s, e, x = make_base(model)
    tfs = {}
    for (t, m_tech) in grp_mchs:
        for o in ops_on_mch_map.get(m_tech, []):
            tfs[t, o, m_tech] = model.NewIntVar(0, horizon, f'tfs_{t}_{o}_{m_tech}')

    z = {}
    for m in all_mchs:
        ops = ops_on_mch_map[m]
        for i, o1 in enumerate(ops):
            for o2 in ops[i+1:]:
                z[o1, o2, m] = model.NewBoolVar(f'z_{o1}_{o2}_{m}')
                z[o2, o1, m] = model.NewBoolVar(f'z_{o2}_{o1}_{m}')

    for o in all_ops:
        model.Add(sum(x[o, m] for m in ops_modes_map[o]) == 1)
    for (o, m) in modes:
        model.Add(e[o, m] >= s[o, m] + pt.get((o, m), 0) * x[o, m])
    for job_id, ops_list in job_ops.items():
        ops_sorted = sorted(ops_list, key=lambda x: x[1])
        for i in range(len(ops_sorted) - 1):
            o1, _ = ops_sorted[i]
            o2, _ = ops_sorted[i + 1]
            for m1 in ops_modes_map[o1]:
                for m2 in ops_modes_map[o2]:
                    model.Add(s[o2,m2] >= e[o1,m1] - M_big*(1-x[o1,m1]) - M_big*(1-x[o2,m2]))
    for (o, m) in modes:
        for t in mch_tech_map.get(m, []):
            if (t, o, m) in tfs:
                model.Add(s[o, m] >= tfs[t, o, m] - M_big * (1 - x[o, m]))
    for (t, o, m) in tfs:
        model.Add(tfs[t, o, m] >= cte).OnlyEnforceIf(x[o, m])
    for (o, m) in modes:
        model.Add(s[o, m] >= cte).OnlyEnforceIf(x[o, m])

    # C7
    for m in all_mchs:
        ops = ops_on_mch_map[m]
        techs_m = mch_tech_map.get(m, [])
        for i, o1 in enumerate(ops):
            for o2 in ops[i+1:]:
                if (o1,o2,m) not in z or (o2,o1,m) not in z:
                    continue
                model.Add(z[o1,o2,m] + z[o2,o1,m] >= x[o1,m] + x[o2,m] - 1)
                model.Add(z[o1,o2,m] + z[o2,o1,m] <= 1)
                model.Add(z[o1,o2,m] <= x[o1,m])
                model.Add(z[o1,o2,m] <= x[o2,m])
                model.Add(z[o2,o1,m] <= x[o1,m])
                model.Add(z[o2,o1,m] <= x[o2,m])
                for t in techs_m:
                    if (t,o2,m) in tfs:
                        model.Add(tfs[t,o2,m] >= cte + e[o1,m] - M_big*(1-z[o1,o2,m]))
                    if (t,o1,m) in tfs:
                        model.Add(tfs[t,o1,m] >= cte + e[o2,m] - M_big*(1-z[o2,o1,m]))

test_with_constraints("C1..C6 + C7", build_jusqu_c7)

# ── TEST 7 : + C9 ─────────────────────────────────────────────────────────────
def build_jusqu_c9(model):
    s, e, x = make_base(model)
    tfs = {}
    for (t, m_tech) in grp_mchs:
        for o in ops_on_mch_map.get(m_tech, []):
            tfs[t, o, m_tech] = model.NewIntVar(0, horizon, f'tfs_{t}_{o}_{m_tech}')

    z = {}
    for m in all_mchs:
        ops = ops_on_mch_map[m]
        for i, o1 in enumerate(ops):
            for o2 in ops[i+1:]:
                z[o1, o2, m] = model.NewBoolVar(f'z_{o1}_{o2}_{m}')
                z[o2, o1, m] = model.NewBoolVar(f'z_{o2}_{o1}_{m}')

    for o in all_ops:
        model.Add(sum(x[o, m] for m in ops_modes_map[o]) == 1)
    for (o, m) in modes:
        model.Add(e[o, m] >= s[o, m] + pt.get((o, m), 0) * x[o, m])
    for job_id, ops_list in job_ops.items():
        ops_sorted = sorted(ops_list, key=lambda x: x[1])
        for i in range(len(ops_sorted) - 1):
            o1, _ = ops_sorted[i]
            o2, _ = ops_sorted[i + 1]
            for m1 in ops_modes_map[o1]:
                for m2 in ops_modes_map[o2]:
                    model.Add(s[o2,m2] >= e[o1,m1] - M_big*(1-x[o1,m1]) - M_big*(1-x[o2,m2]))
    for (o, m) in modes:
        for t in mch_tech_map.get(m, []):
            if (t, o, m) in tfs:
                model.Add(s[o, m] >= tfs[t, o, m] - M_big * (1 - x[o, m]))
    for (t, o, m) in tfs:
        model.Add(tfs[t, o, m] >= cte).OnlyEnforceIf(x[o, m])
    for (o, m) in modes:
        model.Add(s[o, m] >= cte).OnlyEnforceIf(x[o, m])
    for m in all_mchs:
        ops = ops_on_mch_map[m]
        techs_m = mch_tech_map.get(m, [])
        for i, o1 in enumerate(ops):
            for o2 in ops[i+1:]:
                if (o1,o2,m) not in z or (o2,o1,m) not in z:
                    continue
                model.Add(z[o1,o2,m] + z[o2,o1,m] >= x[o1,m] + x[o2,m] - 1)
                model.Add(z[o1,o2,m] + z[o2,o1,m] <= 1)
                model.Add(z[o1,o2,m] <= x[o1,m])
                model.Add(z[o1,o2,m] <= x[o2,m])
                model.Add(z[o2,o1,m] <= x[o1,m])
                model.Add(z[o2,o1,m] <= x[o2,m])
                for t in techs_m:
                    if (t,o2,m) in tfs:
                        model.Add(tfs[t,o2,m] >= cte + e[o1,m] - M_big*(1-z[o1,o2,m]))
                    if (t,o1,m) in tfs:
                        model.Add(tfs[t,o1,m] >= cte + e[o2,m] - M_big*(1-z[o2,o1,m]))

    # C9
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
                        if (t,o2,m2) in tfs and (t,o1,m1) in tfs:
                            model.Add(
                                tfs[t,o2,m2] >= cte + pt.get((o1,m1),0) + tfs[t,o1,m1]
                                - M_big*(1-x[o1,m1]) - M_big*(1-x[o2,m2])
                            )

test_with_constraints("C1..C7 + C9", build_jusqu_c9)

# ── TEST 8 : + C10 ────────────────────────────────────────────────────────────
def build_jusqu_c10(model):
    s, e, x = make_base(model)
    tfs = {}
    for (t, m_tech) in grp_mchs:
        for o in ops_on_mch_map.get(m_tech, []):
            tfs[t, o, m_tech] = model.NewIntVar(0, horizon, f'tfs_{t}_{o}_{m_tech}')

    z = {}
    for m in all_mchs:
        ops = ops_on_mch_map[m]
        for i, o1 in enumerate(ops):
            for o2 in ops[i+1:]:
                z[o1, o2, m] = model.NewBoolVar(f'z_{o1}_{o2}_{m}')
                z[o2, o1, m] = model.NewBoolVar(f'z_{o2}_{o1}_{m}')

    for o in all_ops:
        model.Add(sum(x[o, m] for m in ops_modes_map[o]) == 1)
    for (o, m) in modes:
        model.Add(e[o, m] >= s[o, m] + pt.get((o, m), 0) * x[o, m])
    for job_id, ops_list in job_ops.items():
        ops_sorted = sorted(ops_list, key=lambda x: x[1])
        for i in range(len(ops_sorted) - 1):
            o1, _ = ops_sorted[i]
            o2, _ = ops_sorted[i + 1]
            for m1 in ops_modes_map[o1]:
                for m2 in ops_modes_map[o2]:
                    model.Add(s[o2,m2] >= e[o1,m1] - M_big*(1-x[o1,m1]) - M_big*(1-x[o2,m2]))
    for (o, m) in modes:
        for t in mch_tech_map.get(m, []):
            if (t, o, m) in tfs:
                model.Add(s[o, m] >= tfs[t, o, m] - M_big * (1 - x[o, m]))
    for (t, o, m) in tfs:
        model.Add(tfs[t, o, m] >= cte).OnlyEnforceIf(x[o, m])
    for (o, m) in modes:
        model.Add(s[o, m] >= cte).OnlyEnforceIf(x[o, m])
    for m in all_mchs:
        ops = ops_on_mch_map[m]
        techs_m = mch_tech_map.get(m, [])
        for i, o1 in enumerate(ops):
            for o2 in ops[i+1:]:
                if (o1,o2,m) not in z or (o2,o1,m) not in z:
                    continue
                model.Add(z[o1,o2,m] + z[o2,o1,m] >= x[o1,m] + x[o2,m] - 1)
                model.Add(z[o1,o2,m] + z[o2,o1,m] <= 1)
                model.Add(z[o1,o2,m] <= x[o1,m])
                model.Add(z[o1,o2,m] <= x[o2,m])
                model.Add(z[o2,o1,m] <= x[o1,m])
                model.Add(z[o2,o1,m] <= x[o2,m])
                for t in techs_m:
                    if (t,o2,m) in tfs:
                        model.Add(tfs[t,o2,m] >= cte + e[o1,m] - M_big*(1-z[o1,o2,m]))
                    if (t,o1,m) in tfs:
                        model.Add(tfs[t,o1,m] >= cte + e[o2,m] - M_big*(1-z[o2,o1,m]))
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
                        if (t,o2,m2) in tfs and (t,o1,m1) in tfs:
                            model.Add(
                                tfs[t,o2,m2] >= cte + pt.get((o1,m1),0) + tfs[t,o1,m1]
                                - M_big*(1-x[o1,m1]) - M_big*(1-x[o2,m2])
                            )

    # C10
    for (o, m) in modes:
        for t in mch_tech_map.get(m, []):
            if (t, o, m) in tfs:
                model.Add(
                    e[o, m] >= pt.get((o, m), 0) + tfs[t, o, m]
                    - M_big * (1 - x[o, m])
                )

test_with_constraints("C1..C9 + C10", build_jusqu_c10)

print("\n" + "="*50)
print("Diagnostic complet terminé !")

# ── TEST 9 : + C8 ─────────────────────────────────────────────────────────────
def build_jusqu_c8(model):
    s, e, x = make_base(model)
    tfs = {}
    for (t, m_tech) in grp_mchs:
        for o in ops_on_mch_map.get(m_tech, []):
            tfs[t, o, m_tech] = model.NewIntVar(0, horizon, f'tfs_{t}_{o}_{m_tech}')

    z = {}
    for m in all_mchs:
        ops = ops_on_mch_map[m]
        for i, o1 in enumerate(ops):
            for o2 in ops[i+1:]:
                z[o1, o2, m] = model.NewBoolVar(f'z_{o1}_{o2}_{m}')
                z[o2, o1, m] = model.NewBoolVar(f'z_{o2}_{o1}_{m}')

    K = {}
    for t in all_techs:
        mchs_t = tech_mchs_map[t]
        ops_t  = list(set(o for m in mchs_t for o in ops_on_mch_map.get(m, [])))
        for i, o1 in enumerate(ops_t):
            for o2 in ops_t[i+1:]:
                K[t, o1, o2] = model.NewBoolVar(f'K_{t}_{o1}_{o2}')
                K[t, o2, o1] = model.NewBoolVar(f'K_{t}_{o2}_{o1}')

    for o in all_ops:
        model.Add(sum(x[o, m] for m in ops_modes_map[o]) == 1)
    for (o, m) in modes:
        model.Add(e[o, m] >= s[o, m] + pt.get((o, m), 0) * x[o, m])
    for job_id, ops_list in job_ops.items():
        ops_sorted = sorted(ops_list, key=lambda x: x[1])
        for i in range(len(ops_sorted) - 1):
            o1, _ = ops_sorted[i]
            o2, _ = ops_sorted[i + 1]
            for m1 in ops_modes_map[o1]:
                for m2 in ops_modes_map[o2]:
                    model.Add(s[o2,m2] >= e[o1,m1] - M_big*(1-x[o1,m1]) - M_big*(1-x[o2,m2]))
    for (o, m) in modes:
        for t in mch_tech_map.get(m, []):
            if (t, o, m) in tfs:
                model.Add(s[o, m] >= tfs[t, o, m] - M_big * (1 - x[o, m]))
    for (t, o, m) in tfs:
        model.Add(tfs[t, o, m] >= cte).OnlyEnforceIf(x[o, m])
    for (o, m) in modes:
        model.Add(s[o, m] >= cte).OnlyEnforceIf(x[o, m])
    for m in all_mchs:
        ops = ops_on_mch_map[m]
        techs_m = mch_tech_map.get(m, [])
        for i, o1 in enumerate(ops):
            for o2 in ops[i+1:]:
                if (o1,o2,m) not in z or (o2,o1,m) not in z:
                    continue
                model.Add(z[o1,o2,m] + z[o2,o1,m] >= x[o1,m] + x[o2,m] - 1)
                model.Add(z[o1,o2,m] + z[o2,o1,m] <= 1)
                model.Add(z[o1,o2,m] <= x[o1,m])
                model.Add(z[o1,o2,m] <= x[o2,m])
                model.Add(z[o2,o1,m] <= x[o1,m])
                model.Add(z[o2,o1,m] <= x[o2,m])
                for t in techs_m:
                    if (t,o2,m) in tfs:
                        model.Add(tfs[t,o2,m] >= cte + e[o1,m] - M_big*(1-z[o1,o2,m]))
                    if (t,o1,m) in tfs:
                        model.Add(tfs[t,o1,m] >= cte + e[o2,m] - M_big*(1-z[o2,o1,m]))

    # C8
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
                active_o1   = model.NewBoolVar(f'active_{t}_{o1}')
                active_o2   = model.NewBoolVar(f'active_{t}_{o2}')
                both_active = model.NewBoolVar(f'both_{t}_{o1}_{o2}')
                model.Add(sum(x_o1_on_t) >= 1).OnlyEnforceIf(active_o1)
                model.Add(sum(x_o1_on_t) == 0).OnlyEnforceIf(active_o1.Not())
                model.Add(sum(x_o2_on_t) >= 1).OnlyEnforceIf(active_o2)
                model.Add(sum(x_o2_on_t) == 0).OnlyEnforceIf(active_o2.Not())
                model.AddBoolAnd([active_o1, active_o2]).OnlyEnforceIf(both_active)
                model.AddBoolOr([active_o1.Not(), active_o2.Not()]).OnlyEnforceIf(both_active.Not())
                model.Add(K[t,o1,o2] + K[t,o2,o1] == 1).OnlyEnforceIf(both_active)
                model.Add(K[t,o1,o2] == 0).OnlyEnforceIf(both_active.Not())
                model.Add(K[t,o2,o1] == 0).OnlyEnforceIf(both_active.Not())
                for m1 in mchs_t:
                    for m2 in mchs_t:
                        if m1 == m2:
                            continue
                        if (t,o1,m1) in tfs and (t,o2,m2) in tfs:
                            model.Add(
                                tfs[t,o2,m2] >= cte + tfs[t,o1,m1]
                                - M_big*(1-K[t,o1,o2])
                                - M_big*(1-x[o1,m1])
                                - M_big*(1-x[o2,m2])
                            )
                        if (t,o2,m2) in tfs and (t,o1,m1) in tfs:
                            model.Add(
                                tfs[t,o1,m1] >= cte + tfs[t,o2,m2]
                                - M_big*(1-K[t,o2,o1])
                                - M_big*(1-x[o2,m2])
                                - M_big*(1-x[o1,m1])
                            )

test_with_constraints("C1..C10 + C8", build_jusqu_c8)

print("\n" + "="*50)
print("Diagnostic C8 terminé !")





print("\n" + "="*50)
print("Diagnostic terminé — la première ❌ indique quelle contrainte bloque")