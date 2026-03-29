import sqlite3
import pandas as pd

DB_PATH = "gantt_dashboard.db"

# Colonnes attendues par table (référence fixe)
EXPECTED_COLS = {
    "operations": {"OperationID", "MachineID", "MachineLabel",
                   "ProcessingTime", "StartTime", "EndTime", "Duration"},
    "jobs":       {"OperationID", "JobID", "OperationOrder"},
    "kpis":       {"OperationID", "MachineLabel", "JobID",
                   "JobLabel", "Duration", "Profit"},
}


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Crée les tables avec la structure fixe si elles n'existent pas encore."""
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS operations (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            OperationID    INTEGER NOT NULL,
            MachineID      INTEGER NOT NULL,
            MachineLabel   TEXT    NOT NULL,
            ProcessingTime INTEGER,
            StartTime      INTEGER,
            EndTime        INTEGER,
            Duration       INTEGER,
            uploaded_at    TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS jobs (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            OperationID    INTEGER NOT NULL,
            JobID          INTEGER NOT NULL,
            OperationOrder INTEGER,
            uploaded_at    TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS kpis (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            OperationID  INTEGER,
            MachineLabel TEXT,
            JobID        INTEGER,
            JobLabel     TEXT,
            Duration     REAL,
            Profit       REAL,
            computed_at  TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS prix_jobs (
            JobID      INTEGER PRIMARY KEY,
            Prix       REAL,
            updated_at TEXT DEFAULT (datetime('now'))
        );
    """)
    conn.commit()
    conn.close()


def _validate_columns(df: pd.DataFrame, table: str) -> tuple[bool, str]:
    """Vérifie que le DataFrame contient exactement les colonnes attendues."""
    expected = EXPECTED_COLS[table]
    actual   = set(df.columns)
    missing  = expected - actual
    extra    = actual - expected
    if missing:
        return False, f"Colonnes manquantes dans '{table}': {missing}"
    if extra:
        return False, f"Colonnes inattendues dans '{table}': {extra}"
    return True, "OK"


# ─── OPERATIONS ────────────────────────────────────────────────────────────────

def save_operations(df: pd.DataFrame) -> tuple[bool, str]:
    ok, msg = _validate_columns(df, "operations")
    if not ok:
        return False, msg
    cols = list(EXPECTED_COLS["operations"])
    conn = get_connection()
    conn.execute("DELETE FROM operations")
    df[cols].to_sql("operations", conn, if_exists="append", index=False)
    conn.commit()
    conn.close()
    return True, "OK"


def load_operations() -> pd.DataFrame | None:
    conn = get_connection()
    try:
        df = pd.read_sql(
            "SELECT OperationID, MachineID, MachineLabel, "
            "ProcessingTime, StartTime, EndTime, Duration FROM operations",
            conn
        )
        conn.close()
        return df if not df.empty else None
    except Exception:
        conn.close()
        return None


# ─── JOBS ──────────────────────────────────────────────────────────────────────

def save_jobs(df: pd.DataFrame) -> tuple[bool, str]:
    ok, msg = _validate_columns(df, "jobs")
    if not ok:
        return False, msg
    cols = list(EXPECTED_COLS["jobs"])
    conn = get_connection()
    conn.execute("DELETE FROM jobs")
    df[cols].to_sql("jobs", conn, if_exists="append", index=False)
    conn.commit()
    conn.close()
    return True, "OK"


def load_jobs() -> pd.DataFrame | None:
    conn = get_connection()
    try:
        df = pd.read_sql(
            "SELECT OperationID, JobID, OperationOrder FROM jobs",
            conn
        )
        conn.close()
        return df if not df.empty else None
    except Exception:
        conn.close()
        return None


# ─── KPIs ──────────────────────────────────────────────────────────────────────

def save_kpis(df: pd.DataFrame) -> tuple[bool, str]:
    ok, msg = _validate_columns(df, "kpis")
    if not ok:
        return False, msg
    cols = list(EXPECTED_COLS["kpis"])
    conn = get_connection()
    conn.execute("DELETE FROM kpis")
    df[cols].to_sql("kpis", conn, if_exists="append", index=False)
    conn.commit()
    conn.close()
    return True, "OK"


def load_kpis() -> pd.DataFrame | None:
    conn = get_connection()
    try:
        df = pd.read_sql(
            "SELECT OperationID, MachineLabel, JobID, "
            "JobLabel, Duration, Profit FROM kpis",
            conn
        )
        conn.close()
        return df if not df.empty else None
    except Exception:
        conn.close()
        return None


# ─── PRIX PAR JOB ──────────────────────────────────────────────────────────────

def save_prix(prix: dict):
    conn = get_connection()
    for job_id, val in prix.items():
        conn.execute("""
            INSERT INTO prix_jobs (JobID, Prix)
            VALUES (?, ?)
            ON CONFLICT(JobID) DO UPDATE SET Prix=excluded.Prix,
                                             updated_at=datetime('now')
        """, (int(job_id), float(val)))
    conn.commit()
    conn.close()


def load_prix() -> dict:
    conn = get_connection()
    try:
        rows = conn.execute("SELECT JobID, Prix FROM prix_jobs").fetchall()
        conn.close()
        return {int(r["JobID"]): float(r["Prix"]) for r in rows}
    except Exception:
        conn.close()
        return {}


# ─── RESET ─────────────────────────────────────────────────────────────────────

def clear_all():
    conn = get_connection()
    conn.executescript("""
        DELETE FROM operations;
        DELETE FROM jobs;
        DELETE FROM kpis;
        DELETE FROM prix_jobs;
    """)
    conn.commit()
    conn.close()