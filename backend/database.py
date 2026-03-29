"""
database.py — Supabase backend
Adapté exactement à la structure de app.py existant.
Chaque donnée est isolée par session_id pour usage multi-utilisateurs.
"""

import streamlit as st
import pandas as pd
from supabase import create_client, Client


# ── Connexion ──────────────────────────────────────────────────────────────────

@st.cache_resource
def get_client() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)


def init_db():
    """Compatibilité avec l'ancien code — ne fait rien avec Supabase."""
    pass


# ── Helpers internes ───────────────────────────────────────────────────────────

def _upsert(table: str, session_id: str, df: pd.DataFrame) -> tuple[bool, str]:
    try:
        client = get_client()
        client.table(table).delete().eq("session_id", session_id).execute()
        records = df.to_dict(orient="records")
        payload = [{"session_id": session_id, "data": row} for row in records]
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
        rows = [r["data"] for r in res.data]
        return pd.DataFrame(rows)
    except Exception:
        return None


# ── OPERATIONS ─────────────────────────────────────────────────────────────────

def save_operations(df: pd.DataFrame, session_id: str) -> tuple[bool, str]:
    return _upsert("operations", session_id, df)


def load_operations(session_id: str) -> pd.DataFrame | None:
    df = _load("operations", session_id)
    if df is None:
        return None
    for col in ["OperationID", "MachineID", "ProcessingTime",
                "StartTime", "EndTime", "Duration"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="ignore")
    return df


# ── JOBS ───────────────────────────────────────────────────────────────────────

def save_jobs(df: pd.DataFrame, session_id: str) -> tuple[bool, str]:
    return _upsert("jobs", session_id, df)


def load_jobs(session_id: str) -> pd.DataFrame | None:
    df = _load("jobs", session_id)
    if df is None:
        return None
    for col in ["OperationID", "JobID", "OperationOrder"]:
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


# ── PRIX ───────────────────────────────────────────────────────────────────────

def save_prix(prix_dict: dict, session_id: str) -> tuple[bool, str]:
    try:
        client = get_client()
        client.table("prix").delete().eq("session_id", session_id).execute()
        client.table("prix").insert({
            "session_id": session_id,
            "data": prix_dict
        }).execute()
        return True, "OK"
    except Exception as e:
        return False, str(e)


def load_prix(session_id: str) -> dict:
    try:
        client = get_client()
        res = (client.table("prix")
               .select("data")
               .eq("session_id", session_id)
               .limit(1)
               .execute())
        if not res.data:
            return {}
        raw = res.data[0]["data"]
        return {int(k) if str(k).isdigit() else k: v for k, v in raw.items()}
    except Exception:
        return {}


# ── RESET ──────────────────────────────────────────────────────────────────────

def clear_all(session_id: str) -> None:
    client = get_client()
    for table in ("operations", "jobs", "kpis", "prix"):
        try:
            client.table(table).delete().eq("session_id", session_id).execute()
        except Exception:
            pass