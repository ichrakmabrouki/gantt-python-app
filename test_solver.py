# test_solver.py
# Lance avec : python test_solver.py
# Vérifie toutes les contraintes du modèle après résolution

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.solver.input_parser import DATA
from backend.solver.model        import solve_flexible_jobshop

# ══════════════════════════════════════════════════════════════════════════════
# RÉSOLUTION
# ══════════════════════════════════════════════════════════════════════════════
print("=" * 60)
print("LANCEMENT DU SOLVEUR")
print("=" * 60)

try:
    df = solve_flexible_jobshop(DATA)
except Exception as e:
    print(f"❌ ERREUR SOLVEUR : {e}")
    sys.exit(1)

print(f"\n📋 DataFrame résultat : {len(df)} lignes")
print(df[['OperationID','JobID','MachineID','StartTime','EndTime','Duration']].to_string())

# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════
errors   = []
warnings = []

def check(condition, msg_ok, msg_fail):
    if condition:
        print(f"  ✅ {msg_ok}")
    else:
        print(f"  ❌ {msg_fail}")
        errors.append(msg_fail)

def warn(condition, msg_ok, msg_warn):
    if condition:
        print(f"  ✅ {msg_ok}")
    else:
        print(f"  ⚠️  {msg_warn}")
        warnings.append(msg_warn)

# ══════════════════════════════════════════════════════════════════════════════
# TEST 1 — Une machine par opération
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("TEST 1 — Chaque opération assignée à exactement 1 machine")
print("=" * 60)

ops_in_result = df['OperationID'].tolist()
ops_expected  = list(set(o for (o, m) in DATA['modes']))

check(
    len(ops_in_result) == len(set(ops_in_result)),
    "Pas de doublons d'opérations",
    f"Doublons détectés : {[o for o in ops_in_result if ops_in_result.count(o) > 1]}"
)

missing = set(ops_expected) - set(ops_in_result)
check(
    len(missing) == 0,
    f"Toutes les {len(ops_expected)} opérations sont planifiées",
    f"Opérations manquantes : {sorted(missing)}"
)

# ══════════════════════════════════════════════════════════════════════════════
# TEST 2 — Durées respectées
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("TEST 2 — Durées respectées (EndTime = StartTime + Duration)")
print("=" * 60)

for _, row in df.iterrows():
    dur_expected = DATA['pt'].get((row['OperationID'], row['MachineID']), 0)
    actual_dur   = row['EndTime'] - row['StartTime']
    check(
        actual_dur >= dur_expected,
        f"Op {row['OperationID']} sur M{row['MachineID']} : durée {actual_dur} >= {dur_expected}",
        f"Op {row['OperationID']} sur M{row['MachineID']} : durée {actual_dur} < {dur_expected} !"
    )

# ══════════════════════════════════════════════════════════════════════════════
# TEST 3 — Précédence dans les jobs
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("TEST 3 — Précédence des opérations dans chaque job")
print("=" * 60)

gammes_map = {g[0]: (g[1], g[2]) for g in DATA['gammes']}  # op_id -> (job_id, pos)
df['pos'] = df['OperationID'].map(lambda o: gammes_map[o][1])

for job_id in df['JobID'].unique():
    df_job = df[df['JobID'] == job_id].sort_values('pos')
    ops_job = df_job.to_dict('records')
    for i in range(len(ops_job) - 1):
        o1 = ops_job[i]
        o2 = ops_job[i + 1]
        check(
            o2['StartTime'] >= o1['EndTime'],
            f"Job {job_id} : Op {o1['OperationID']} (fin={o1['EndTime']}) "
            f"<= Op {o2['OperationID']} (début={o2['StartTime']})",
            f"Job {job_id} : VIOLATION précédence Op {o1['OperationID']} "
            f"(fin={o1['EndTime']}) > Op {o2['OperationID']} (début={o2['StartTime']})"
        )

# ══════════════════════════════════════════════════════════════════════════════
# TEST 4 — Non-chevauchement sur les machines
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("TEST 4 — Non-chevauchement des opérations sur chaque machine")
print("=" * 60)

for mch_id in df['MachineID'].unique():
    df_m = df[df['MachineID'] == mch_id].sort_values('StartTime')
    ops_m = df_m.to_dict('records')
    for i in range(len(ops_m) - 1):
        for j in range(i + 1, len(ops_m)):
            o1 = ops_m[i]
            o2 = ops_m[j]
            overlap = not (o1['EndTime'] <= o2['StartTime'] or
                           o2['EndTime'] <= o1['StartTime'])
            check(
                not overlap,
                f"M{mch_id} : Op {o1['OperationID']} [{o1['StartTime']}-{o1['EndTime']}] "
                f"et Op {o2['OperationID']} [{o2['StartTime']}-{o2['EndTime']}] — pas de chevauchement",
                f"M{mch_id} : CHEVAUCHEMENT Op {o1['OperationID']} "
                f"[{o1['StartTime']}-{o1['EndTime']}] et Op {o2['OperationID']} "
                f"[{o2['StartTime']}-{o2['EndTime']}]"
            )

# ══════════════════════════════════════════════════════════════════════════════
# TEST 5 — Respect du setup time cte entre opérations sur même machine
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print(f"TEST 5 — Setup time cte={DATA['cte']} min respecté entre ops sur même machine")
print("=" * 60)

cte = DATA['cte']
for mch_id in df['MachineID'].unique():
    df_m = df[df['MachineID'] == mch_id].sort_values('StartTime')
    ops_m = df_m.to_dict('records')
    for i in range(len(ops_m) - 1):
        o1 = ops_m[i]
        o2 = ops_m[i + 1]
        gap = o2['StartTime'] - o1['EndTime']
        check(
            gap >= cte,
            f"M{mch_id} : gap entre Op {o1['OperationID']} et Op {o2['OperationID']} "
            f"= {gap} >= cte={cte}",
            f"M{mch_id} : VIOLATION setup — gap {gap} < cte={cte} "
            f"entre Op {o1['OperationID']} (fin={o1['EndTime']}) "
            f"et Op {o2['OperationID']} (début={o2['StartTime']})"
        )

# ══════════════════════════════════════════════════════════════════════════════
# TEST 6 — Machine assignée est dans les modes autorisés
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("TEST 6 — Machine assignée est dans les modes autorisés")
print("=" * 60)

modes_set = set(DATA['modes'])
for _, row in df.iterrows():
    check(
        (row['OperationID'], row['MachineID']) in modes_set,
        f"Op {row['OperationID']} → M{row['MachineID']} est un mode valide",
        f"Op {row['OperationID']} → M{row['MachineID']} N'EST PAS un mode valide !"
    )

# ══════════════════════════════════════════════════════════════════════════════
# TEST 7 — Début >= cte pour toutes les opérations
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print(f"TEST 7 — StartTime >= cte={cte} pour toutes les opérations")
print("=" * 60)

for _, row in df.iterrows():
    check(
        row['StartTime'] >= cte,
        f"Op {row['OperationID']} : StartTime={row['StartTime']} >= cte={cte}",
        f"Op {row['OperationID']} : StartTime={row['StartTime']} < cte={cte} !"
    )

# ══════════════════════════════════════════════════════════════════════════════
# TEST 8 — Makespan et statistiques
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("TEST 8 — Statistiques générales")
print("=" * 60)

makespan     = int(df['EndTime'].max())
nb_jobs      = df['JobID'].nunique()
nb_machines  = df['MachineID'].nunique()
duree_totale = df['Duration'].sum()
taux_util    = round(duree_totale / (makespan * nb_machines) * 100, 1)

print(f"  📊 Makespan       : {makespan} min")
print(f"  📊 Jobs planifiés : {nb_jobs}")
print(f"  📊 Machines util. : {nb_machines}")
print(f"  📊 Durée totale   : {duree_totale} min")
print(f"  📊 Taux util. moy : {taux_util} %")

warn(taux_util >= 30, f"Taux utilisation {taux_util}% OK",
     f"Taux utilisation très faible : {taux_util}% — vérifier les données")
warn(makespan <= sum(DATA['pt'].values()),
     f"Makespan {makespan} raisonnable",
     f"Makespan {makespan} très élevé")

# ══════════════════════════════════════════════════════════════════════════════
# RÉSUMÉ FINAL
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("RÉSUMÉ")
print("=" * 60)

if errors:
    print(f"\n❌ {len(errors)} ERREUR(S) CRITIQUE(S) :")
    for e in errors:
        print(f"   • {e}")
else:
    print("\n✅ TOUTES LES CONTRAINTES SONT RESPECTÉES")

if warnings:
    print(f"\n⚠️  {len(warnings)} AVERTISSEMENT(S) :")
    for w in warnings:
        print(f"   • {w}")

print("\n" + "=" * 60)
sys.exit(1 if errors else 0)

# ══════════════════════════════════════════════════════════════════════════════
# Test de faisabilité progressive
# ══════════════════════════════════════════════════════════════════════════════

from ortools.sat.python import cp_model
from backend.solver.input_parser import DATA


def test_feasibility():
    import backend.solver.model as m_module
    
    # Test 1 : juste C1 + C2 (assignement + durées)
    print("Test C1+C2 uniquement...")
    # Modifie temporairement max_time
    import backend.solver.model as mod
    original = mod.solve_flexible_jobshop
    
test_feasibility()