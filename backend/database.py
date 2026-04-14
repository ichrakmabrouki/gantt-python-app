"""
database.py — Supabase backend
Adapté exactement à la structure de app.py existant.
Chaque donnée est isolée par session_id pour usage multi-utilisateurs.
"""

# backend/database.py

import base64
import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone

import pandas as pd
import streamlit as st
from supabase import Client, create_client


PBKDF2_ITERATIONS = 200_000
SESSION_DURATION_DAYS = 7


def _get_secret(name: str) -> str | None:
    try:
        value = st.secrets[name]
        if value:
            return str(value)
    except Exception:
        pass
    value = os.getenv(name)
    return str(value) if value else None


def _normalize_username(username: str) -> str:
    return username.strip().lower()


def _session_secret() -> str:
    secret = _get_secret("SESSION_SECRET") or _get_secret("SUPABASE_KEY")
    if not secret:
        raise RuntimeError("SESSION_SECRET ou SUPABASE_KEY manquant pour signer la session")
    return secret


def _legacy_hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def _coerce_numeric_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    for col in columns:
        if col not in df.columns:
            continue
        try:
            df[col] = pd.to_numeric(df[col])
        except Exception:
            pass
    return df


def hash_password(password: str) -> str:
    salt = os.urandom(16).hex()
    derived = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PBKDF2_ITERATIONS,
    ).hex()
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt}${derived}"


def verify_password(password: str, stored_hash: str | None) -> bool:
    if not stored_hash:
        return False

    if stored_hash.startswith("pbkdf2_sha256$"):
        try:
            _, iterations, salt, expected = stored_hash.split("$", 3)
            derived = hashlib.pbkdf2_hmac(
                "sha256",
                password.encode("utf-8"),
                salt.encode("utf-8"),
                int(iterations),
            ).hex()
            return hmac.compare_digest(derived, expected)
        except Exception:
            return False

    return hmac.compare_digest(_legacy_hash_password(password), stored_hash)


def needs_password_rehash(stored_hash: str | None) -> bool:
    return not bool(stored_hash and stored_hash.startswith("pbkdf2_sha256$"))


def create_session_token(username: str, expires_at: datetime | None = None) -> str:
    user = _normalize_username(username)
    expires = expires_at or (datetime.now(timezone.utc) + timedelta(days=SESSION_DURATION_DAYS))
    timestamp = int(expires.astimezone(timezone.utc).timestamp())
    payload = f"{user}|{timestamp}"
    signature = hmac.new(
        _session_secret().encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    raw = f"{payload}|{signature}".encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("utf-8")


def verify_session_token(token: str | None) -> str | None:
    if not token:
        return None

    try:
        decoded = base64.urlsafe_b64decode(token.encode("utf-8")).decode("utf-8")
        username, expires_ts, signature = decoded.split("|", 2)
        payload = f"{username}|{expires_ts}"
        expected = hmac.new(
            _session_secret().encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(signature, expected):
            return None
        if int(expires_ts) < int(datetime.now(timezone.utc).timestamp()):
            return None
        return _normalize_username(username)
    except Exception:
        return None

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
    return _coerce_numeric_columns(df, ["OperationID", "MachineID", "StartTime", "EndTime", "Duration"])


# ── Jobs ───────────────────────────────────────────────────────────────────────
def save_jobs(df: pd.DataFrame, session_id: str) -> tuple[bool, str]:
    return _upsert("jobs", session_id, df)

def load_jobs(session_id: str) -> pd.DataFrame | None:
    df = _load("jobs", session_id)
    if df is None:
        return None
    return _coerce_numeric_columns(df, ["OperationID", "JobID"])


# ── KPIs ───────────────────────────────────────────────────────────────────────
def save_kpis(df: pd.DataFrame, session_id: str) -> tuple[bool, str]:
    return _upsert("kpis", session_id, df)

def load_kpis(session_id: str) -> pd.DataFrame | None:
    df = _load("kpis", session_id)
    if df is None:
        return None
    return _coerce_numeric_columns(df, ["Profit (€)", "Marge (%)", "Duree_min"])


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
    for table in ("operations", "jobs", "kpis", "prix", "planning_jours"):
        try:
            client.table(table).delete().eq("session_id", session_id).execute()
            client.table(table).delete().eq("session_id", f"{session_id}_maps").execute()
        except Exception:
            pass

def get_user(username: str) -> dict | None:
    try:
        client = get_client()
        u = _normalize_username(username)

        res = client.table("users")\
            .select("username, password, role")\
            .eq("username", u)\
            .limit(1)\
            .execute()

        if not res.data:
            return None

        return res.data[0]

    except Exception:
        return None


def create_user(username: str, password: str, role: str = "user") -> tuple[bool, str]:
    try:
        client = get_client()
        u = _normalize_username(username)

        # Vérifier si existe déjà
        existing = get_user(u)
        if existing:
            return False, f"L'identifiant '{u}' est déjà utilisé"

        # 🔐 HASH PASSWORD (IMPORTANT)
        hashed_password = hash_password(password)

        client.table("users").insert({
            "username": u,
            "password": hashed_password,
            "role": role
        }).execute()

        return True, "OK"

    except Exception as e:
        return False, str(e)


def update_user_password_hash(username: str, new_password_hash: str) -> tuple[bool, str]:
    try:
        client = get_client()
        u = _normalize_username(username)
        client.table("users").update({
            "password": new_password_hash
        }).eq("username", u).execute()
        return True, "OK"
    except Exception as e:
        return False, str(e)
