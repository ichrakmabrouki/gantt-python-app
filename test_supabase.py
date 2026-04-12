# test_supabase.py
from backend.database import init_db, save_operations, load_operations
from backend.database import save_planning_jour, load_planning_jours
import pandas as pd
from datetime import date

print("=" * 50)
print("TEST CONNEXION SUPABASE")
print("=" * 50)

# Test 1 — init
try:
    init_db()
    print("✅ init_db() — OK")
except Exception as e:
    print(f"❌ init_db() — {e}")

# Test 2 — écriture planning_jours
try:
    df_test = pd.DataFrame([{
        'OperationID': 1, 'MachineID': 1, 'MachineLabel': 'Machine 1',
        'JobID': 1, 'JobLabel': 'Pièce 1', 'StartTime': 15,
        'EndTime': 105, 'Duration': 90
    }])
    df_jobs_test = pd.DataFrame([{'OperationID': 1, 'JobID': 1}])
    
    ok, msg = save_planning_jour(
    session_id="test_user",
    jour=str(date.today()),   # ← str() car database.py attend une string
    label=str(date.today()),  # ← paramètre obligatoire manquant
    df_ops=df_test,           # ← bon nom
    df_jobs=df_jobs_test,
    of_map={},                # ← paramètre obligatoire manquant
    piece_map={},             # ← paramètre obligatoire manquant
    makespan=105              # ← paramètre obligatoire manquant
)
    )
    if ok:
        print(f"✅ save_planning_jour() — OK")
    else:
        print(f"❌ save_planning_jour() — {msg}")
except Exception as e:
    print(f"❌ save_planning_jour() — {e}")

# Test 3 — lecture planning_jours
try:
    jours = load_planning_jours("test_user")
    print(f"✅ load_planning_jours() — {len(jours)} jour(s) trouvé(s)")
    for j in jours:
        print(f"   📅 {j['jour']} — {len(j['operations'])} opérations")
except Exception as e:
    print(f"❌ load_planning_jours() — {e}")

print("=" * 50)