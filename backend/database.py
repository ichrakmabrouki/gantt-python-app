"""
database.py — Supabase backend
Adapté exactement à la structure de app.py existant.
Chaque donnée est isolée par session_id pour usage multi-utilisateurs.
"""

# backend/database.py
import streamlit as st
import pandas as pd
from supabase import create_client, Client


@st.cache_resource
def get_client() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)


def init_db():
    pass


def _upsert(table: str, session_id: str, df: pd.DataFrame) -> tuple[bool, str]:
    try:
        client = get_client()
        client.table(table).delete().eq("session_id", session_id).execute()
        payload = [{"session_id": session_id, "data": row}
                   for row in df.to_dict(orient="records")]
        client.table(table).insert(payload).execute()
        return True, "OK"
    except Exception as e:
        return False, str(e)


def _load(table: str, session_id: str) -> pd.DataFrame | None:
    try:
        client = get_client()
        res = client.table(table).select("data").eq("session_id", session_id).execute()
        if not res.data:
            return None
        return pd.DataFrame([r["data"] for r in res.data])
    except Exception:
        return None


# ── Operations ─────────────────────────────────────────────────────────────────
def save_operations(df: pd.DataFrame, session_id: str) -> tuple[bool, str]:
    return _upsert("operations", session_id, df)

def load_operations(session_id: str) -> pd.DataFrame | None:
    df = _load("operations", session_id)
    if df is None:
        return None
    for col in ["OperationID", "MachineID", "StartTime", "EndTime", "Duration"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="ignore")
    return df


# ── Jobs ───────────────────────────────────────────────────────────────────────
def save_jobs(df: pd.DataFrame, session_id: str) -> tuple[bool, str]:
    return _upsert("jobs", session_id, df)

def load_jobs(session_id: str) -> pd.DataFrame | None:
    df = _load("jobs", session_id)
    if df is None:
        return None
    for col in ["OperationID", "JobID"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="ignore")
    return df


# ── KPIs ───────────────────────────────────────────────────────────────────────
def save_kpis(df: pd.DataFrame, session_id: str) -> tuple[bool, str]:
    return _upsert("kpis", session_id, df)

def load_kpis(session_id: str) -> pd.DataFrame | None:
    df = _load("kpis", session_id)
    if df is None:
        return None
    for col in ["Profit (€)", "Marge (%)", "Duree_min"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="ignore")
    return df


# ── Prix ───────────────────────────────────────────────────────────────────────
def save_prix(prix_dict: dict, session_id: str) -> tuple[bool, str]:
    try:
        client = get_client()
        client.table("prix").delete().eq("session_id", session_id).execute()
        client.table("prix").insert({"session_id": session_id, "data": prix_dict}).execute()
        return True, "OK"
    except Exception as e:
        return False, str(e)

def load_prix(session_id: str) -> dict:
    try:
        client = get_client()
        res = client.table("prix").select("data").eq("session_id", session_id).limit(1).execute()
        if not res.data:
            return {}
        raw = res.data[0]["data"]
        return {int(k) if str(k).isdigit() else k: v for k, v in raw.items()}
    except Exception:
        return {}


# ── OF map & Pièce map ─────────────────────────────────────────────────────────
def save_of_piece_maps(of_map: dict, piece_map: dict, session_id: str) -> tuple[bool, str]:
    try:
        client = get_client()
        sid = f"{session_id}_maps"
        client.table("prix").delete().eq("session_id", sid).execute()
        client.table("prix").insert({
            "session_id": sid,
            "data": {"of_map": of_map, "piece_map": piece_map}
        }).execute()
        return True, "OK"
    except Exception as e:
        return False, str(e)

def load_of_piece_maps(session_id: str) -> tuple[dict, dict]:
    try:
        client = get_client()
        res = client.table("prix").select("data")\
            .eq("session_id", f"{session_id}_maps").limit(1).execute()
        if not res.data:
            return {}, {}
        raw = res.data[0]["data"]
        of_map    = {int(k) if str(k).isdigit() else k: v
                     for k, v in raw.get("of_map", {}).items()}
        piece_map = {int(k) if str(k).isdigit() else k: v
                     for k, v in raw.get("piece_map", {}).items()}
        return of_map, piece_map
    except Exception:
        return {}, {}


# ── Planning jours ─────────────────────────────────────────────────────────────
def save_planning_jour(session_id: str, jour: str, label: str,
                       df_ops: pd.DataFrame, df_jobs: pd.DataFrame,
                       of_map: dict, piece_map: dict,
                       makespan: int) -> tuple[bool, str]:
    try:
        client = get_client()
        client.table("planning_jours").delete()\
            .eq("session_id", session_id).eq("jour", jour).execute()
        client.table("planning_jours").insert({
            "session_id": session_id,
            "jour":       jour,
            "label":      label,
            "operations": df_ops.to_dict(orient="records"),
            "jobs":       df_jobs.to_dict(orient="records"),
            "of_map":     of_map,
            "piece_map":  piece_map,
            "makespan":   makespan,
        }).execute()
        return True, "OK"
    except Exception as e:
        return False, str(e)

def load_planning_jours(session_id: str) -> list[dict]:
    try:
        client = get_client()
        res = client.table("planning_jours")\
            .select("jour, label, makespan, created_at")\
            .eq("session_id", session_id)\
            .order("jour", desc=True).execute()
        return res.data if res.data else []
    except Exception:
        return []

def load_planning_jour_detail(session_id: str, jour: str) -> dict | None:
    try:
        client = get_client()
        res = client.table("planning_jours").select("*")\
            .eq("session_id", session_id).eq("jour", jour).limit(1).execute()
        if not res.data:
            return None
        row = res.data[0]
        return {
            "jour":      row["jour"],
            "label":     row["label"],
            "makespan":  row["makespan"],
            "df_ops":    pd.DataFrame(row["operations"]),
            "df_jobs":   pd.DataFrame(row["jobs"]),
            "of_map":    {int(k) if str(k).isdigit() else k: v
                          for k, v in (row.get("of_map") or {}).items()},
            "piece_map": {int(k) if str(k).isdigit() else k: v
                          for k, v in (row.get("piece_map") or {}).items()},
        }
    except Exception:
        return None


# ── Reset ──────────────────────────────────────────────────────────────────────
def clear_all(session_id: str) -> None:
    client = get_client()
    for table in ("operations", "jobs", "kpis", "prix"):
        try:
            client.table(table).delete().eq("session_id", session_id).execute()
            client.table(table).delete().eq("session_id", f"{session_id}_maps").execute()
        except Exception:
            pass

def get_user(username: str) -> dict | None:
    """Récupère un utilisateur depuis Supabase."""
    try:
        client = get_client()
        res = client.table("users") \
                    .select("username, password, role") \
                    .eq("username", username) \
                    .execute()
        if res.data:
            return res.data[0]
        return None
    except Exception:
        return None

def create_user(username: str, password: str, role: str = "user"):
    """Crée un nouvel utilisateur dans Supabase."""
    try:
        existing = get_user(username)
        if existing:
            return False, "Cet identifiant existe déjà"
        client = get_client()
        client.table("users").insert({
            "username": username,
            "password": password,
            "role":     role
        }).execute()
        return True, "OK"
    except Exception as e:
        return False, str(e)
        # ── Utilisateurs ───────────────────────────────────────────────────────────────
def get_user(username: str) -> dict | None:
    try:
        client = get_client()
        res = client.table("users")\
            .select("username, password, role")\
            .eq("username", username.strip().lower())\
            .limit(1).execute()
        if not res.data:
            return None
        return res.data[0]
    except Exception:
        return None

def create_user(username: str, password: str, role: str = "user") -> tuple[bool, str]:
    try:
        u = username.strip().lower()
        # Vérifie si l'utilisateur existe déjà
        existing = get_user(u)
        if existing:
            return False, f"L'identifiant '{u}' est déjà utilisé"
        client = get_client()
        client.table("users").insert({
            "username": u,
            "password": password,
            "role":     role
        }).execute()
        return True, "OK"
    except Exception as e:
        return False, str(e)