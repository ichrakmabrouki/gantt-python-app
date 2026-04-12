# backend/solver/input_parser.py

import pandas as pd


def parse_excel_to_dict(excel_file) -> dict:
    xls = pd.ExcelFile(excel_file)

    df_params = pd.read_excel(xls, sheet_name="⚙ PARAMETRES",  header=2)
    df_gammes = pd.read_excel(xls, sheet_name="📋 GAMMES",      header=3)
    df_modes  = pd.read_excel(xls, sheet_name="🔧 MODES & PT",  header=3)
    df_techs  = pd.read_excel(xls, sheet_name="👷 TECHNICIENS", header=3)

    # Nettoyage
    df_gammes = df_gammes.dropna(subset=["op_id", "job_id", "pos"])
    df_modes  = df_modes.dropna(subset=["op_id", "machine_id"])
    df_techs  = df_techs.dropna(subset=["tech_id", "machine_id"])

    # Trouver colonne durée (robuste)
    duree_col = next(
        (c for c in df_modes.columns
         if "dur" in c.lower() or ("min" in c.lower() and "machine" not in c.lower())),
        None
    )
    if duree_col is None:
        raise ValueError("Colonne durée introuvable dans 'MODES & PT'. Vérifiez que la colonne s'appelle 'duree (min)'.")

    df_modes  = df_modes.dropna(subset=[duree_col])
    df_gammes = df_gammes.astype({"op_id": int, "job_id": int, "pos": int})
    df_modes  = df_modes.astype({"op_id": int, "machine_id": int})
    df_modes[duree_col] = df_modes[duree_col].astype(int)
    df_techs  = df_techs.astype({"tech_id": int, "machine_id": int})

    # Paramètres
    param_col = df_params.columns[1]
    def get_param(keyword):
        row = df_params[df_params.iloc[:, 0].str.contains(keyword, na=False, case=False)]
        if row.empty:
            raise ValueError(f"Paramètre introuvable : '{keyword}'")
        return int(row.iloc[0][param_col])

    nb_jobs = get_param("nbJobs")
    nb_mchs = get_param("nbMchs")
    nb_ops  = get_param("nbOps")
    nbtechs = get_param("nbtechs")
    cte     = get_param("cte")

    # OF et désignation pièce (par job_id)
    of_col    = next((c for c in df_gammes.columns if "of" in c.lower()), None)
    piece_col = next((c for c in df_gammes.columns
                      if any(k in c.lower() for k in ["désig", "design", "piè", "piece", "nom"])), None)

    of_map    = {}
    piece_map = {}
    for _, r in df_gammes.iterrows():
        jid = int(r["job_id"])
        if of_col and pd.notna(r.get(of_col)):
            of_map[jid] = str(r[of_col]).strip()
        if piece_col and pd.notna(r.get(piece_col)):
            piece_map[jid] = str(r[piece_col]).strip()

    # Structures solveur
    gammes_raw = [(int(r["op_id"]), int(r["job_id"]), int(r["pos"]))
                  for _, r in df_gammes.iterrows()]

    modes_raw  = [(int(r["op_id"]), int(r["machine_id"]))
                  for _, r in df_modes.iterrows()]

    pt_raw     = {(int(r["op_id"]), int(r["machine_id"])): int(r[duree_col])
                  for _, r in df_modes.iterrows()}

    grp_mchs_raw = [(int(r["tech_id"]), int(r["machine_id"]))
                    for _, r in df_techs.iterrows()]

    return {
        'params':    {'nbJobs': nb_jobs, 'nbMchs': nb_mchs, 'nbOps': nb_ops},
        'nbtechs':   nbtechs,
        'cte':       cte,
        'gammes':    gammes_raw,
        'modes':     modes_raw,
        'pt':        pt_raw,
        'grp_mchs':  grp_mchs_raw,
        'of_map':    of_map,
        'piece_map': piece_map,
    }


def validate_excel_data(data: dict) -> tuple[bool, str]:
    params   = data['params']
    gammes   = data['gammes']
    modes    = data['modes']
    pt       = data['pt']
    grp_mchs = data['grp_mchs']
    nb_ops   = params['nbOps']
    nb_mchs  = params['nbMchs']

    ops_in_gammes = set(g[0] for g in gammes)
    if len(ops_in_gammes) != nb_ops:
        return False, f"nbOps={nb_ops} mais {len(ops_in_gammes)} opérations dans GAMMES."

    missing = ops_in_gammes - set(m[0] for m in modes)
    if missing:
        return False, f"Opérations sans machine définie : {sorted(missing)}"

    mchs_in_modes = set(m[1] for m in modes)
    out = [m for m in mchs_in_modes if m < 1 or m > nb_mchs]
    if out:
        return False, f"IDs machines hors bornes (1..{nb_mchs}) : {sorted(out)}"

    uncovered = mchs_in_modes - set(g[1] for g in grp_mchs)
    if uncovered:
        return False, f"Machines sans technicien : {sorted(uncovered)}"

    for (op, mch) in modes:
        if (op, mch) not in pt:
            return False, f"Durée manquante op={op} machine={mch}."

    return True, "OK"


def _make_default_data():
    return {
        'params':   {'nbJobs': 13, 'nbMchs': 15, 'nbOps': 30},
        'nbtechs':  6,
        'cte':      15,
        'of_map': {
            1:"OF-2024-001", 2:"OF-2024-001",
            3:"OF-2024-002", 4:"OF-2024-002",
            5:"OF-2024-003", 6:"OF-2024-003", 7:"OF-2024-003",
            8:"OF-2024-004", 9:"OF-2024-004",
            10:"OF-2024-005",11:"OF-2024-005",
            12:"OF-2024-006",13:"OF-2024-006",
        },
        'piece_map': {
            1:"Bride moteur A",    2:"Bride moteur A",
            3:"Carter pompe",      4:"Carter pompe",
            5:"Vilebrequin",       6:"Vilebrequin", 7:"Vilebrequin",
            8:"Arbre transmission",9:"Arbre transmission",
            10:"Flasque avant",    11:"Flasque avant",
            12:"Couvercle",        13:"Couvercle",
        },
        'gammes': [
            (1,1,0),(2,1,1),(3,1,2),(4,1,3),
            (5,2,0),(6,2,1),(7,2,2),(8,2,3),(9,3,0),
            (10,4,0),(11,4,1),(12,4,2),
            (13,5,0),(14,5,1),(15,5,2),(16,5,3),
            (17,6,0),(18,7,0),
            (19,8,0),(20,8,1),(21,8,2),(22,8,3),
            (23,9,0),(24,9,1),(25,9,2),(26,9,3),
            (27,10,0),(28,11,0),(29,12,0),(30,13,0),
        ],
        'modes': [
            (1,1),(1,2),(1,3),(1,4),(2,5),(3,12),(3,13),
            (4,1),(4,2),(4,3),(4,4),(5,1),(5,2),(5,3),(5,4),
            (6,5),(7,12),(7,13),(8,10),(8,11),
            (9,1),(9,2),(9,3),(9,4),(10,1),(10,2),(10,3),(10,4),
            (11,5),(12,12),(12,13),(13,1),(13,2),(13,3),(13,4),
            (14,5),(15,12),(15,13),(16,1),(16,2),(16,3),(16,4),
            (17,1),(17,2),(17,3),(17,4),(18,1),(18,2),(18,3),(18,4),
            (19,1),(19,2),(19,3),(19,4),(20,5),(21,12),(21,13),
            (22,1),(22,2),(22,3),(22,4),(23,1),(23,2),(23,3),(23,4),
            (24,5),(25,12),(25,13),(26,1),(26,2),(26,3),(26,4),
            (27,1),(27,2),(27,3),(27,4),(28,1),(28,2),(28,3),(28,4),
            (29,1),(29,2),(29,3),(29,4),(30,1),(30,2),(30,3),(30,4),
        ],
        'pt': {
            (1,1):90,(1,2):90,(1,3):90,(1,4):90,
            (2,5):20,(3,12):80,(3,13):80,
            (4,1):30,(4,2):30,(4,3):30,(4,4):30,
            (5,1):180,(5,2):180,(5,3):180,(5,4):180,
            (6,5):40,(7,12):40,(7,13):40,(8,10):80,(8,11):80,
            (9,1):240,(9,2):240,(9,3):240,(9,4):240,
            (10,1):180,(10,2):180,(10,3):180,(10,4):180,
            (11,5):120,(12,12):120,(12,13):120,
            (13,1):240,(13,2):240,(13,3):240,(13,4):240,
            (14,5):120,(15,12):120,(15,13):120,
            (16,1):120,(16,2):120,(16,3):120,(16,4):120,
            (17,1):40,(17,2):40,(17,3):40,(17,4):40,
            (18,1):30,(18,2):30,(18,3):30,(18,4):30,
            (19,1):80,(19,2):80,(19,3):80,(19,4):80,
            (20,5):40,(21,12):40,(21,13):40,
            (22,1):60,(22,2):60,(22,3):60,(22,4):60,
            (23,1):80,(23,2):80,(23,3):80,(23,4):80,
            (24,5):40,(25,12):40,(25,13):40,
            (26,1):60,(26,2):60,(26,3):60,(26,4):60,
            (27,1):180,(27,2):180,(27,3):180,(27,4):180,
            (28,1):60,(28,2):60,(28,3):60,(28,4):60,
            (29,1):60,(29,2):60,(29,3):60,(29,4):60,
            (30,1):40,(30,2):40,(30,3):40,(30,4):40,
        },
        'grp_mchs': [
            (1,1),(1,2),(2,3),(2,4),(3,5),
            (4,6),(4,7),(4,8),(4,9),
            (5,10),(5,11),(6,12),(6,13),(6,14),(6,15),
        ],
    }

DATA = _make_default_data()