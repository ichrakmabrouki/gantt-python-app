import streamlit as st
import pandas as pd
import io
import uuid
from datetime import datetime, date, timedelta
import extra_streamlit_components as stx


from backend.converter      import convert_txt_to_df, load_jobs_from_txt
from backend.data_processor import load_file, validate, parse_and_clean, to_csv_bytes
from backend.gantt_builder  import WORKDAY_MINUTES, build_gantt, minutes_to_time
from backend.kpi_calculator import compute_kpis, summary_by_machine, summary_by_job
from backend.database       import (
    init_db,
    save_operations, load_operations,
    save_jobs,       load_jobs,
    save_kpis,       load_kpis,
    save_prix,       load_prix,
    save_of_piece_maps, load_of_piece_maps,
    save_planning_jour, load_planning_jours, load_planning_jour_detail,
    clear_all,
    create_session_token,
    create_user,
    get_user,
    hash_password,
    needs_password_rehash,
    update_user_password_hash,
    verify_password,
    verify_session_token,
    log_app_access,
    load_access_logs,
    load_access_summary,
)

init_db()

st.set_page_config(page_title="Gantt Dashboard", layout="wide", page_icon="⚙️")

# ══════════════════════════════════════════════════════════════════════════════
# ⚠️ DEBUG — VIDER LE COOKIE (À SUPPRIMER APRÈS TEST)
# ══════════════════════════════════════════════════════════════════════════════
cookie_manager = stx.CookieManager()
# ══════════════════════════════════════════════════════════════════════════════
# FIN DEBUG
# ══════════════════════════════════════════════════════════════════════════════

# ── Initialisation session state ───────────────────────────────────────────
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
if "SID" not in st.session_state:
    st.session_state["SID"] = None
if "user_role" not in st.session_state:
    st.session_state["user_role"] = None
if "force_login" not in st.session_state:
    st.session_state["force_login"] = False


def clear_auth_session() -> None:
    expired_at = datetime.now() - timedelta(days=1)
    for cookie_name in ("gantt_session", "gantt_user"):
        try:
            cookie_manager.delete(cookie_name)
        except Exception:
            pass
        try:
            cookie_manager.set(cookie_name, "", expires_at=expired_at)
        except Exception:
            pass

    keep_force_login = st.session_state.get("force_login", False)
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.session_state["force_login"] = keep_force_login

# ── Vérifie le cookie existant ─────────────────────────────────────────────
session_cookie = cookie_manager.get("gantt_session")
legacy_cookie = cookie_manager.get("gantt_user")

if st.session_state.get("force_login"):
    try:
        cookie_manager.delete("gantt_session")
        cookie_manager.delete("gantt_user")
    except Exception:
        pass
    session_cookie = None
    legacy_cookie = None

if session_cookie and not st.session_state["authenticated"] and not st.session_state.get("force_login"):
    username = verify_session_token(session_cookie)
    if username:
        user = get_user(username)
        if user:
            st.session_state["authenticated"] = True
            st.session_state["SID"] = username
            st.session_state["user_role"] = user.get("role", "user")
        else:
            cookie_manager.delete("gantt_session")
    else:
        cookie_manager.delete("gantt_session")

if legacy_cookie and not st.session_state["authenticated"] and not st.session_state.get("force_login"):
    user = get_user(legacy_cookie)
    if user:
        st.session_state["authenticated"] = True
        st.session_state["SID"] = legacy_cookie.strip().lower()
        st.session_state["user_role"] = user.get("role", "user")
        cookie_manager.set(
            "gantt_session",
            create_session_token(st.session_state["SID"]),
            expires_at=datetime.now() + timedelta(days=7)
        )
    cookie_manager.delete("gantt_user")

# ── Page de connexion ──────────────────────────────────────────────────────
if not st.session_state["authenticated"]:

    st.markdown("""
    <div class="login-hero">
        <p class="login-kicker">Atelier mecanique</p>
        <h1>Gantt Dashboard</h1>
        <p>Planification, suivi de charge, KPI et historiques de production dans un espace securise.</p>
    </div>
    """, unsafe_allow_html=True)

    tab_login, tab_register = st.tabs(["SE CONNECTER", "CRÉER UN COMPTE"])

    with tab_login:
        with st.form("login_form"):
            username_input = st.text_input("Identifiant")
            password_input = st.text_input("Mot de passe", type="password")
            submit_login = st.form_submit_button("Se connecter")

        if submit_login:
            u = username_input.strip().lower()
            p = password_input.strip()

            if not u or not p:
                st.error("❌ Identifiant et mot de passe obligatoires")
            else:
                user = get_user(u)

                if user and verify_password(p, user.get("password")):
                    clear_auth_session()
                    st.session_state["authenticated"] = True
                    st.session_state["SID"] = u
                    st.session_state["user_role"] = user.get("role", "user")
                    st.session_state["force_login"] = False

                    if needs_password_rehash(user.get("password")):
                        update_user_password_hash(u, hash_password(p))

                    cookie_manager.set(
                        "gantt_session",
                        create_session_token(u),
                        expires_at=datetime.now() + timedelta(days=7)
                    )
                    cookie_manager.delete("gantt_user")

                    st.success("✅ Connexion réussie")
                    st.rerun()
                else:
                    st.error("❌ Identifiant ou mot de passe incorrect")

    with tab_register:
        with st.form("register_form"):
            new_user  = st.text_input("Nouvel identifiant")
            new_pass  = st.text_input("Mot de passe", type="password")
            new_pass2 = st.text_input("Confirmer le mot de passe", type="password")
            submit_register = st.form_submit_button("Créer le compte")

        if submit_register:
            u = new_user.strip().lower()
            p = new_pass.strip()
            p2 = new_pass2.strip()

            if not u or not p or not p2:
                st.error("❌ Identifiant et mot de passe obligatoires")

            elif p != p2:
                st.error("❌ Les mots de passe ne correspondent pas")

            elif len(p) < 8:
                st.error("❌ Mot de passe trop court (min 8 caractères)")

            elif not any(ch.isalpha() for ch in p) or not any(ch.isdigit() for ch in p):
                st.error("❌ Le mot de passe doit contenir au moins une lettre et un chiffre")

            else:
                ok, msg = create_user(u, p)

                if ok:
                    st.success(f"✔ Compte '{u}' créé — connecte-toi maintenant")
                else:
                    st.error(f"❌ {msg}")

    st.stop()

# ── SID récupéré après authentification ───────────────────────────────────
SID = st.session_state.get("SID")


def _request_context() -> tuple[str | None, str | None]:
    try:
        headers = st.context.headers
    except Exception:
        headers = {}

    def header(name: str) -> str | None:
        try:
            return headers.get(name)
        except Exception:
            return None

    user_agent = header("user-agent")
    host = header("host") or header("x-forwarded-host")
    proto = header("x-forwarded-proto") or "https"
    app_url = f"{proto}://{host}" if host else None
    return app_url, user_agent


if SID and not st.session_state.get("access_logged"):
    app_url, user_agent = _request_context()
    source = st.query_params.get("src") or st.query_params.get("source") or "direct"
    log_app_access(
        username=SID,
        event="visit",
        page="app",
        app_url=app_url,
        user_agent=user_agent,
        source=source,
    )
    st.session_state["access_logged"] = True

if st.session_state.get("authenticated") and st.session_state.get("user_role") == "admin":
    with st.sidebar:
        if st.button("Effacer ma session admin", key="debug_clear_cookie"):
            st.session_state["force_login"] = True
            clear_auth_session()
            st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# CSS — THÈME INDUSTRIEL
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@400;600;700&family=Inter:wght@400;500;600&display=swap');
html, body,
[data-testid="stAppViewContainer"],
[data-testid="stAppViewContainer"] > div:first-child,
[data-testid="stHeader"], [data-testid="stMain"],
.main, .block-container {
    background-color: #0d1117 !important; color: #c9d1d9 !important; color-scheme: dark !important;
}
[data-testid="stSidebar"] { background-color: #161b22 !important; border-right: 2px solid #ff6b00 !important; }
[data-testid="stSidebar"] * { font-family: 'Rajdhani', sans-serif !important; color: #8b949e !important; }
[data-testid="stSidebar"] .stRadio label {
    font-size: 13px !important; font-weight: 600 !important; letter-spacing: 1.5px !important;
    text-transform: uppercase !important; color: #8b949e !important; padding: 10px 4px !important;
    transition: color 0.15s !important;
}
[data-testid="stSidebar"] .stRadio label:hover { color: #ff6b00 !important; }
*, p, div, span, li, .stMarkdown p, [data-testid="stMarkdownContainer"] p {
    font-family: 'Inter', sans-serif !important; color: #c9d1d9 !important;
    font-size: 13px !important; line-height: 1.6 !important; letter-spacing: 0.2px !important;
}
h1, h2, h3, h4, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
    font-family: 'Rajdhani', sans-serif !important; color: #ff6b00 !important;
    font-weight: 700 !important; letter-spacing: 2px !important; text-transform: uppercase !important;
}
.masthead-eyebrow {
    font-family: 'Rajdhani', sans-serif !important; font-size: 1.15rem !important;
    font-weight: 700 !important; color: #ff6b00 !important; letter-spacing: 5px !important;
    text-transform: uppercase !important; margin: 0 0 6px 0 !important;
    text-shadow: 0 0 30px rgba(255,107,0,0.3) !important;
}
.masthead-accent { width: 60px; height: 2px; background: linear-gradient(90deg, #ff6b00, transparent); margin: 0 0 12px 0; border-radius: 2px; }
.header-banner {
    background: linear-gradient(90deg, #161b22 0%, #1c2333 50%, #161b22 100%);
    border: 1px solid #ff6b00; border-radius: 4px; padding: 18px 28px; margin-bottom: 24px;
    display: flex; align-items: center; justify-content: space-between;
}
.header-left { display: flex; flex-direction: column; gap: 6px; }
.header-title {
    font-family: 'Rajdhani', sans-serif !important; font-size: 1.9rem !important;
    font-weight: 700 !important; color: #ff6b00 !important; letter-spacing: 7px !important;
    text-transform: uppercase !important; margin: 0 !important; line-height: 1 !important;
}
.header-page-active {
    font-family: 'Rajdhani', sans-serif !important; font-size: 0.95rem !important;
    font-weight: 700 !important; color: #c9d1d9 !important; letter-spacing: 4px !important;
    text-transform: uppercase !important; margin: 0 !important; padding-left: 10px !important;
    border-left: 3px solid #ff6b00 !important; display: block !important;
}
.header-date {
    font-family: 'Inter', sans-serif !important; font-size: 0.8rem !important;
    color: #8b949e !important; text-align: right; line-height: 1.9;
}
.divline { height: 1px; background: linear-gradient(90deg, transparent, #ff6b0066, transparent); margin: 0 0 20px 0; border: none; }
.page-header-bar { background: #161b22; border: 1px solid #30363d; border-left: 3px solid #ff6b00; border-radius: 4px; padding: 14px 20px; margin-bottom: 20px; }
.page-title { font-family: 'Rajdhani', sans-serif !important; font-size: 1.1rem !important; font-weight: 700 !important; color: #ff6b00 !important; letter-spacing: 3px !important; text-transform: uppercase !important; margin: 0 0 4px 0 !important; }
.page-subtitle { font-family: 'Inter', sans-serif !important; font-size: 0.72rem !important; color: #8b949e !important; margin: 0 !important; letter-spacing: 0.3px !important; }
.section-title { font-family: 'Rajdhani', sans-serif !important; font-size: 0.72rem !important; font-weight: 700 !important; color: #ff6b00 !important; letter-spacing: 3px !important; text-transform: uppercase !important; margin-bottom: 10px; padding-bottom: 8px; border-bottom: 1px solid #30363d; }
[data-testid="stMetric"] { background: #161b22 !important; border: 1px solid #30363d !important; border-top: 3px solid #ff6b00 !important; border-radius: 4px !important; padding: 14px 16px !important; }
[data-testid="stMetricValue"] { font-family: 'Rajdhani', sans-serif !important; color: #ff6b00 !important; font-size: 1.6rem !important; font-weight: 700 !important; }
[data-testid="stMetricLabel"] { font-family: 'Inter', sans-serif !important; color: #8b949e !important; font-size: 0.62rem !important; letter-spacing: 2px !important; text-transform: uppercase !important; }
.stButton > button { background: transparent !important; border: 1px solid #ff6b00 !important; color: #ff6b00 !important; font-family: 'Rajdhani', sans-serif !important; font-weight: 700 !important; font-size: 13px !important; letter-spacing: 2px !important; text-transform: uppercase !important; border-radius: 2px !important; padding: 8px 22px !important; transition: all 0.15s ease !important; }
.stButton > button:hover { background: #ff6b00 !important; color: #0d1117 !important; }
.stDownloadButton > button { background: transparent !important; border: 1px solid #30363d !important; color: #c9d1d9 !important; font-family: 'Rajdhani', sans-serif !important; font-size: 13px !important; font-weight: 600 !important; letter-spacing: 1.5px !important; text-transform: uppercase !important; border-radius: 2px !important; width: 100% !important; transition: all 0.15s ease !important; }
.stDownloadButton > button:hover { border-color: #ff6b00 !important; color: #ff6b00 !important; }
.stNumberInput > div > div > input,
.stTextInput > div > div > input,
[data-testid="stDateInputField"],
[data-baseweb="input"] input,
[data-baseweb="base-input"] input,
textarea,
input {
    background-color: #0d1117 !important;
    border: 1px solid #30363d !important;
    color: #f3f4f6 !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 13px !important;
    border-radius: 2px !important;
    caret-color: #f3f4f6 !important;
}
.stNumberInput > div > div > input:focus,
.stTextInput > div > div > input:focus,
[data-testid="stDateInputField"]:focus,
[data-baseweb="input"] input:focus,
[data-baseweb="base-input"] input:focus,
textarea:focus,
input:focus {
    border-color: #ff6b00 !important; box-shadow: 0 0 0 1px #ff6b0044 !important;
}
[data-testid="stSelectbox"] > div > div,
[data-baseweb="select"] > div,
[data-baseweb="popover"] [role="listbox"],
[data-baseweb="select"] *,
.stMultiSelect div[data-baseweb="select"] {
    background: #161b22 !important; border: 1px solid #30363d !important; color: #c9d1d9 !important; font-family: 'Inter', sans-serif !important; border-radius: 2px !important;
}
[data-testid="stSelectbox"] label { color: #c9d1d9 !important; }
[data-testid="stPills"] button {
    background: #161b22 !important;
    border: 1px solid #30363d !important;
    color: #c9d1d9 !important;
    border-radius: 999px !important;
    font-family: 'Rajdhani', sans-serif !important;
    font-size: 12px !important;
    letter-spacing: 1px !important;
    min-height: 34px !important;
}
[data-testid="stPills"] button[aria-pressed="true"] {
    background: #ff6b001a !important;
    border-color: #ff6b00 !important;
    color: #ff6b00 !important;
}
[data-testid="stPills"] button:hover {
    border-color: #ff6b00 !important;
    color: #ff6b00 !important;
}
[data-baseweb="select"] {
    min-height: 46px !important;
}
[data-baseweb="select"] > div {
    min-height: 46px !important;
    display: flex !important;
    align-items: center !important;
    padding-top: 2px !important;
    padding-bottom: 2px !important;
    padding-left: 10px !important;
    padding-right: 36px !important;
}
[data-baseweb="select"] span,
[data-baseweb="select"] div {
    color: #f3f4f6 !important;
    line-height: 1.35 !important;
}
[data-baseweb="select"] input {
    color: #f3f4f6 !important;
}
[data-baseweb="menu"] li,
[role="option"] {
    background: #161b22 !important;
    color: #f3f4f6 !important;
    min-height: 38px !important;
    display: flex !important;
    align-items: center !important;
}
[role="option"][aria-selected="true"] {
    background: #222b36 !important;
}
[data-baseweb="tag"] { background: #0d1117 !important; color: #f3f4f6 !important; border: 1px solid #30363d !important; }
[data-baseweb="select"] svg,
[data-testid="stDateInputField"] svg,
[data-baseweb="input"] svg { fill: #f3f4f6 !important; color: #f3f4f6 !important; }
[data-testid="stFileUploader"] {
    background: #161b22 !important;
    border: 1px dashed #30363d !important;
    border-radius: 4px !important;
    color: #f3f4f6 !important;
}
[data-testid="stFileUploader"]:hover { border-color: #ff6b00 !important; }
[data-testid="stFileUploader"] * { color: #f3f4f6 !important; }
[data-testid="stFileUploaderDropzone"] {
    background: #0d1117 !important;
    border: 1px dashed #30363d !important;
}
[data-testid="stFileUploaderDropzone"] section {
    background: #0d1117 !important;
    color: #f3f4f6 !important;
}
[data-testid="stFileUploaderDropzone"] button {
    background: #161b22 !important;
    color: #f3f4f6 !important;
    border: 1px solid #30363d !important;
}
[data-testid="stFileUploaderDropzoneInstructions"] span,
[data-testid="stFileUploaderDropzoneInstructions"] small,
[data-testid="stFileUploaderFileName"] {
    color: #f3f4f6 !important;
}
[data-testid="stFileUploader"] svg,
[data-testid="stFileUploaderDropzone"] svg { fill: #f3f4f6 !important; color: #f3f4f6 !important; }
.stTabs [data-baseweb="tab-list"] { background: #161b22 !important; border: 1px solid #30363d !important; border-radius: 2px !important; padding: 4px !important; gap: 2px !important; }
.stTabs [data-baseweb="tab"] { background: transparent !important; border-radius: 2px !important; color: #8b949e !important; font-family: 'Rajdhani', sans-serif !important; font-weight: 600 !important; font-size: 12px !important; letter-spacing: 2px !important; text-transform: uppercase !important; padding: 7px 16px !important; border: 1px solid transparent !important; transition: all 0.15s !important; }
.stTabs [aria-selected="true"] { background: #ff6b0012 !important; color: #ff6b00 !important; border-color: #ff6b00 !important; }
.stTabs [data-baseweb="tab-panel"] { background: #161b22 !important; border: 1px solid #30363d !important; border-top: none !important; border-radius: 0 0 4px 4px !important; padding: 20px !important; }
[data-testid="stDataFrame"] { border: 1px solid #30363d !important; border-radius: 4px !important; overflow: hidden !important; background: #161b22 !important; }
[data-testid="stForm"] { background: #161b22 !important; border: 1px solid #30363d !important; border-radius: 4px !important; padding: 18px !important; }
[data-testid="stExpander"] { background: #161b22 !important; border: 1px solid #30363d !important; border-radius: 4px !important; }
[data-testid="stExpander"] * { color: #c9d1d9 !important; }
[data-testid="stExpander"] details summary {
    min-height: 70px !important;
    display: flex !important;
    align-items: center !important;
    line-height: 1.4 !important;
    padding-top: 8px !important;
    padding-bottom: 8px !important;
    padding-right: 24px !important;
}
[data-testid="stExpander"] details summary p,
[data-testid="stExpander"] details summary span {
    line-height: 1.4 !important;
    white-space: normal !important;
    font-size: 12px !important;
}
[data-testid="stAlert"] { background: #161b22 !important; border-radius: 2px !important; border-left-width: 3px !important; }
[data-testid="stAlert"] p { color: #c9d1d9 !important; font-size: 12px !important; }
.status-badge { background: #0f2a1a; border: 1px solid #238636; border-radius: 2px; padding: 5px 10px; font-family: 'Inter', sans-serif !important; font-size: 11px !important; color: #3fb950 !important; margin: 4px 0; display: block; letter-spacing: 0.5px; }
.status-badge-teal { background: #0d1b2a; border: 1px solid #1f6feb; color: #58a6ff !important; }
.dl-card { background: #161b22; border: 1px solid #30363d; border-radius: 4px; padding: 28px 20px 20px; text-align: center; height: 150px; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 10px; }
.dl-icon { font-size: 26px; }
.dl-label { font-family: 'Rajdhani', sans-serif !important; font-size: 12px !important; font-weight: 700 !important; color: #8b949e !important; letter-spacing: 2px; text-transform: uppercase; }
label { font-family: 'Rajdhani', sans-serif !important; font-size: 12px !important; font-weight: 600 !important; color: #8b949e !important; letter-spacing: 1px !important; text-transform: uppercase !important; }
[data-testid="stWidgetLabel"] p,
[data-testid="stMarkdownContainer"] label,
[data-testid="stFileUploaderDropzoneInstructions"] div,
[data-testid="stTextInput"] label,
[data-testid="stNumberInput"] label,
[data-testid="stDateInput"] label {
    color: #c9d1d9 !important;
}
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: #0d1117; }
::-webkit-scrollbar-thumb { background: #30363d; border-radius: 2px; }
::-webkit-scrollbar-thumb:hover { background: #ff6b00; }

:root {
    --bg: #0b1014;
    --panel: #111820;
    --panel-2: #151f28;
    --line: #27323d;
    --line-soft: #1c2731;
    --text: #e5edf3;
    --muted: #9aa8b4;
    --accent: #d87722;
    --accent-soft: rgba(216, 119, 34, 0.14);
    --ok: #2fa872;
    --info: #4f8fcf;
    --warn: #d6a536;
    --danger: #d85b5b;
}

html, body,
[data-testid="stAppViewContainer"],
[data-testid="stAppViewContainer"] > div:first-child,
[data-testid="stHeader"], [data-testid="stMain"],
.main, .block-container {
    background: var(--bg) !important;
    color: var(--text) !important;
}

.block-container {
    max-width: 1480px !important;
    padding-top: 1.2rem !important;
    padding-bottom: 2.5rem !important;
}

*, p, div, span, li, .stMarkdown p, [data-testid="stMarkdownContainer"] p {
    color: var(--text) !important;
    font-size: 13px !important;
    line-height: 1.55 !important;
    letter-spacing: 0 !important;
}

h1, h2, h3, h4, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
    color: var(--text) !important;
    letter-spacing: 0.04em !important;
}

[data-testid="stSidebar"] {
    background: #0f161d !important;
    border-right: 1px solid var(--line) !important;
}

[data-testid="stSidebar"] .stRadio label {
    border-radius: 6px !important;
    padding: 9px 10px !important;
    color: var(--muted) !important;
    letter-spacing: 0.06em !important;
}

[data-testid="stSidebar"] .stRadio label:hover {
    background: rgba(255,255,255,0.035) !important;
    color: var(--text) !important;
}

.masthead-eyebrow {
    color: var(--muted) !important;
    font-size: 0.72rem !important;
    letter-spacing: 0.18em !important;
    text-shadow: none !important;
    margin-bottom: 8px !important;
}

.masthead-accent {
    display: none !important;
}

.header-banner {
    background: linear-gradient(135deg, #121b24 0%, #17232d 100%) !important;
    border: 1px solid var(--line) !important;
    border-left: 4px solid var(--accent) !important;
    border-radius: 8px !important;
    padding: 18px 22px !important;
    margin-bottom: 18px !important;
    box-shadow: 0 16px 40px rgba(0,0,0,0.18) !important;
}

.header-title {
    color: var(--text) !important;
    font-size: 1.55rem !important;
    letter-spacing: 0.12em !important;
}

.header-page-active {
    border-left: 0 !important;
    padding-left: 0 !important;
    color: var(--accent) !important;
    font-size: 0.78rem !important;
    letter-spacing: 0.14em !important;
}

.header-date {
    color: var(--muted) !important;
}

.header-date span {
    color: var(--accent) !important;
}

.divline {
    display: none !important;
}

.page-header-bar {
    background: var(--panel) !important;
    border: 1px solid var(--line) !important;
    border-left: 4px solid var(--accent) !important;
    border-radius: 8px !important;
    padding: 16px 18px !important;
    margin: 8px 0 18px !important;
}

.page-title {
    color: var(--text) !important;
    font-size: 1rem !important;
    letter-spacing: 0.11em !important;
}

.page-subtitle {
    color: var(--muted) !important;
    font-size: 0.78rem !important;
}

.section-title {
    color: var(--accent) !important;
    letter-spacing: 0.08em !important;
    border-bottom: 1px solid var(--line-soft) !important;
    padding-bottom: 7px !important;
}

[data-testid="stMetric"] {
    background: var(--panel) !important;
    border: 1px solid var(--line) !important;
    border-top: 0 !important;
    border-radius: 8px !important;
    padding: 14px 16px !important;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.03) !important;
}

[data-testid="stMetricValue"] {
    color: var(--text) !important;
    font-size: 1.42rem !important;
}

[data-testid="stMetricLabel"] {
    color: var(--muted) !important;
    letter-spacing: 0.08em !important;
}

.stButton > button,
.stDownloadButton > button,
[data-testid="stFileUploaderDropzone"] button {
    border-radius: 6px !important;
    min-height: 40px !important;
    letter-spacing: 0.08em !important;
}

.stButton > button {
    background: var(--accent) !important;
    border: 1px solid var(--accent) !important;
    color: #101820 !important;
}

.stButton > button:hover {
    background: #ee8a32 !important;
    border-color: #ee8a32 !important;
    color: #101820 !important;
    transform: translateY(-1px);
}

.stDownloadButton > button {
    background: var(--panel-2) !important;
    border-color: var(--line) !important;
    color: var(--text) !important;
}

.stDownloadButton > button:hover {
    border-color: var(--accent) !important;
    color: var(--accent) !important;
}

.stNumberInput > div > div > input,
.stTextInput > div > div > input,
[data-testid="stDateInputField"],
[data-baseweb="input"] input,
[data-baseweb="base-input"] input,
textarea,
input {
    background: #0e151c !important;
    border-color: var(--line) !important;
    border-radius: 6px !important;
    min-height: 40px !important;
}

[data-baseweb="select"] > div,
[data-testid="stFileUploader"],
[data-testid="stFileUploaderDropzone"],
[data-testid="stForm"],
[data-testid="stExpander"],
[data-testid="stDataFrame"],
.stTabs [data-baseweb="tab-list"],
.stTabs [data-baseweb="tab-panel"],
.dl-card {
    background: var(--panel) !important;
    border-color: var(--line) !important;
    border-radius: 8px !important;
}

.stTabs [data-baseweb="tab-list"] {
    padding: 5px !important;
}

.stTabs [data-baseweb="tab"] {
    border-radius: 6px !important;
    letter-spacing: 0.07em !important;
    color: var(--muted) !important;
}

.stTabs [aria-selected="true"] {
    background: var(--accent-soft) !important;
    border-color: rgba(216,119,34,0.35) !important;
    color: var(--accent) !important;
}

[data-testid="stAlert"] {
    background: var(--panel) !important;
    border-radius: 8px !important;
    border: 1px solid var(--line) !important;
}

.status-badge {
    background: rgba(47,168,114,0.12) !important;
    border-color: rgba(47,168,114,0.35) !important;
    border-radius: 999px !important;
    color: #6fd39e !important;
    padding: 5px 11px !important;
    display: inline-block !important;
}

.status-badge-teal {
    background: rgba(79,143,207,0.13) !important;
    border-color: rgba(79,143,207,0.35) !important;
    color: #8fc1f2 !important;
}

.dl-card {
    height: 132px !important;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.03) !important;
}

.dl-label {
    color: var(--text) !important;
    letter-spacing: 0.08em !important;
}

.login-hero {
    max-width: 760px;
    margin: 8vh auto 28px;
    padding: 28px 30px;
    background: linear-gradient(135deg, #121b24 0%, #17232d 100%);
    border: 1px solid var(--line);
    border-left: 4px solid var(--accent);
    border-radius: 8px;
    box-shadow: 0 16px 48px rgba(0,0,0,0.22);
}

.login-hero h1 {
    margin: 0 0 8px !important;
    color: var(--text) !important;
    font-family: 'Rajdhani', sans-serif !important;
    font-size: 2rem !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
}

.login-hero p {
    max-width: 620px;
    margin: 0 !important;
    color: var(--muted) !important;
}

.login-kicker {
    color: var(--accent) !important;
    font-family: 'Rajdhani', sans-serif !important;
    font-size: 0.78rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.16em !important;
    margin-bottom: 8px !important;
    text-transform: uppercase !important;
}

label,
[data-testid="stWidgetLabel"] p {
    color: var(--muted) !important;
    letter-spacing: 0.07em !important;
}

::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-track { background: #0b1014; }
::-webkit-scrollbar-thumb { background: #34424f; border-radius: 999px; }
::-webkit-scrollbar-thumb:hover { background: var(--accent); }

@media (max-width: 800px) {
    .block-container {
        padding-left: 0.9rem !important;
        padding-right: 0.9rem !important;
        padding-top: 0.8rem !important;
    }
    .header-banner {
        align-items: flex-start !important;
        flex-direction: column !important;
        gap: 12px !important;
        padding: 16px !important;
    }
    .header-title {
        font-size: 1.18rem !important;
        letter-spacing: 0.08em !important;
    }
    .header-date {
        text-align: left !important;
    }
    .page-header-bar {
        padding: 14px !important;
    }
    .login-hero {
        margin-top: 2vh !important;
        padding: 20px !important;
    }
    .login-hero h1 {
        font-size: 1.35rem !important;
        letter-spacing: 0.07em !important;
    }
    .stButton > button,
    .stDownloadButton > button {
        width: 100% !important;
    }
    [data-testid="stMetric"] {
        margin-bottom: 8px !important;
    }
    .stTabs [data-baseweb="tab-list"] {
        overflow-x: auto !important;
        flex-wrap: nowrap !important;
    }
    .stTabs [data-baseweb="tab"] {
        min-width: max-content !important;
    }
}

[data-testid="collapsedControl"],
[data-testid="stSidebarCollapseButton"],
[data-testid="stSidebarCollapsedControl"],
button[title*="sidebar" i],
button[aria-label*="sidebar" i] {
    background: var(--accent) !important;
    border: 1px solid #ee8a32 !important;
    border-radius: 999px !important;
    color: #101820 !important;
    min-width: 42px !important;
    min-height: 42px !important;
    box-shadow: 0 10px 28px rgba(216,119,34,0.35) !important;
}

[data-testid="collapsedControl"] svg,
[data-testid="stSidebarCollapseButton"] svg,
[data-testid="stSidebarCollapsedControl"] svg,
button[title*="sidebar" i] svg,
button[aria-label*="sidebar" i] svg {
    color: #101820 !important;
    fill: #101820 !important;
    stroke: #101820 !important;
}

[data-testid="stSidebar"] [role="radiogroup"] label {
    min-height: 38px !important;
    display: flex !important;
    align-items: center !important;
}

[data-testid="stMultiSelect"] [data-baseweb="tag"] {
    background: var(--accent-soft) !important;
    border-color: rgba(216,119,34,0.35) !important;
    color: var(--accent) !important;
    border-radius: 999px !important;
}

[data-testid="stMultiSelect"] [data-baseweb="tag"] span {
    color: var(--accent) !important;
}
</style>
""", unsafe_allow_html=True)

# ── Chargement depuis Supabase ─────────────────────────────────────────────────
if SID and "data" not in st.session_state:
    df_ops = load_operations(SID)
    if df_ops is not None:
        st.session_state["data"] = df_ops

if SID and "df_jobs" not in st.session_state:
    df_jobs = load_jobs(SID)
    if df_jobs is not None:
        st.session_state["df_jobs"] = df_jobs

if SID and "data_kpi" not in st.session_state:
    df_kpi = load_kpis(SID)
    if df_kpi is not None:
        st.session_state["data_kpi"] = df_kpi

if SID and "prix_db" not in st.session_state:
    st.session_state["prix_db"] = load_prix(SID)

if SID and "of_map" not in st.session_state:
    of_map_db, piece_map_db = load_of_piece_maps(SID)
    st.session_state["of_map"]    = of_map_db
    st.session_state["piece_map"] = piece_map_db


def planning_makespan(df: pd.DataFrame) -> int:
    if df is None or df.empty:
        return 0
    return int(df["EndTime"].max() - df["StartTime"].min())


# ── Sidebar ────────────────────────────────────────────────────────────────────
st.sidebar.markdown("""
<p style='font-family:Rajdhani,sans-serif;font-size:0.65rem;font-weight:700;
   color:rgba(255,255,255,0.25);letter-spacing:3px;text-transform:uppercase;
   border-bottom:1px solid #30363d;padding-bottom:10px;margin-bottom:8px'>
   ⚙ NAVIGATION
</p>""", unsafe_allow_html=True)

MENU_OPTIONS = [
    "🗂 Données",
    "🗓 Planning",
    "📈 KPI",
    "🕘 Historique",
    "⤓ Export",
]
if st.session_state.get("user_role") == "admin":
    MENU_OPTIONS.append("📊 Analytics")
if st.session_state.get("main_menu_v2") not in MENU_OPTIONS:
    st.session_state.pop("main_menu_v2", None)
menu = st.sidebar.radio(
    "Navigation principale",
    MENU_OPTIONS,
    key="main_menu_v2",
    label_visibility="collapsed",
)

st.sidebar.markdown("<hr style='border-color:#30363d;margin:16px 0'>", unsafe_allow_html=True)

# ── Statuts ────────────────────────────────────────────────────────────────────
st.sidebar.markdown("<div style='margin-top:4px'>", unsafe_allow_html=True)
st.sidebar.markdown(
    f"<span class='status-badge' style='background:#1a1200;border-color:#ff6b00;"
    f"color:#ff6b00'>👤 {SID}</span>",
    unsafe_allow_html=True)
if "data" in st.session_state:
    st.sidebar.markdown(
        f"<span class='status-badge'>✔ {len(st.session_state['data'])} OPÉRATIONS</span>",
        unsafe_allow_html=True)
if "df_jobs" in st.session_state:
    n = st.session_state["df_jobs"]["JobID"].nunique()
    st.sidebar.markdown(
        f"<span class='status-badge status-badge-teal'>⬡ {n} PIÈCES MAPPÉES</span>",
        unsafe_allow_html=True)
if "data_kpi" in st.session_state:
    st.sidebar.markdown(
        "<span class='status-badge'>▶ KPIs CALCULÉS</span>",
        unsafe_allow_html=True)
st.sidebar.markdown("</div>", unsafe_allow_html=True)

st.sidebar.markdown("<hr style='border-color:#30363d;margin:16px 0'>", unsafe_allow_html=True)

# ── Clôture journée ────────────────────────────────────────────────────────────
if "data" in st.session_state:
    st.sidebar.markdown("""
    <p style='font-family:Rajdhani,sans-serif;font-size:0.6rem;font-weight:700;
       color:rgba(255,255,255,0.25);letter-spacing:2px;text-transform:uppercase;
       margin-bottom:6px'>📅 PLANIFICATION MULTI-JOURS</p>""", unsafe_allow_html=True)
    jour_cloture = st.sidebar.date_input("Date du planning", value=date.today(),
                                          key="jour_cloture_date")
    if st.sidebar.button("ARCHIVER LE JOUR", key="cloture_btn"):
        try:
            df_ops_cl    = st.session_state["data"]
            df_jobs_cl   = st.session_state.get("df_jobs", pd.DataFrame())
            of_map_cl    = st.session_state.get("of_map", {})
            piece_map_cl = st.session_state.get("piece_map", {})
            makespan_cl  = planning_makespan(df_ops_cl)
            label_cl     = f"Planning {jour_cloture.strftime('%d/%m/%Y')}"
            ok, msg = save_planning_jour(
                session_id=SID, jour=str(jour_cloture), label=label_cl,
                df_ops=df_ops_cl, df_jobs=df_jobs_cl,
                of_map=of_map_cl, piece_map=piece_map_cl, makespan=makespan_cl,
            )
            if ok:
                st.sidebar.success(f"✔ Jour {jour_cloture} sauvegardé")
            else:
                st.sidebar.error(f"❌ {msg}")
        except Exception as ex:
            st.sidebar.error(f"❌ {ex}")

st.sidebar.markdown("<hr style='border-color:#30363d;margin:16px 0'>", unsafe_allow_html=True)

# ── Boutons réinitialiser et déconnecter (verticaux) ──────────────────────────
if st.sidebar.button("RÉINITIALISER", key="reset_btn", use_container_width=True):
    clear_all(SID)
    for key in ["data", "df_jobs", "data_kpi", "prix_db", "df_cout",
                "kpi_params", "of_map", "piece_map"]:
        st.session_state.pop(key, None)
    st.rerun()

if st.sidebar.button("COMPTE", key="switch_account_btn", use_container_width=True):
    st.session_state["force_login"] = True
    clear_auth_session()
    st.rerun()

if st.sidebar.button("DÉCONNEXION", key="logout_btn", use_container_width=True):
    st.session_state["force_login"] = True
    clear_auth_session()
    st.rerun()


# ── Page labels ────────────────────────────────────────────────────────────────
PAGE_LABELS = {
    "🗂 Données":    "Données",
    "🗓 Planning":   "Planning",
    "📈 KPI":        "KPI",
    "🕘 Historique": "Historique",
    "⤓ Export":     "Export",
    "📊 Analytics":  "Analytics",
}

# ── Header ─────────────────────────────────────────────────────────────────────
now = datetime.now()
st.markdown(f"""
<p class="masthead-eyebrow">⚙ SYSTÈME DE PILOTAGE INDUSTRIEL</p>
<div class="masthead-accent"></div>
<div class="header-banner">
    <div class="header-left">
        <p class="header-title">GANTT DASHBOARD</p>
        <span class="header-page-active">▸ {PAGE_LABELS[menu]}</span>
    </div>
    <div class="header-date">
        {now.strftime('%A').upper()}<br>
        <span style="font-size:1rem;font-weight:700;color:#ff6b00">
            {now.strftime('%d %b %Y').upper()}
        </span><br>
        {now.strftime('%H:%M')}
    </div>
</div>
<div class="divline"></div>
""", unsafe_allow_html=True)

# ── Helpers ────────────────────────────────────────────────────────────────────
def chart_layout(**kwargs):
    base = dict(
        paper_bgcolor="#161b22", plot_bgcolor="#0d1117",
        font=dict(color="#c9d1d9", family="Inter", size=11),
        margin=dict(l=10, r=10, t=30, b=10),
        yaxis=dict(gridcolor="#21262d"), xaxis=dict(gridcolor="#21262d"),
    )
    base.update(kwargs)
    return base

def piece_label(job_id: int) -> str:
    piece_map = st.session_state.get("piece_map", {})
    if piece_map and job_id in piece_map:
        return f"P{job_id} — {piece_map[job_id]}"
    return f"Pièce {job_id}"


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 1 — UPLOAD
# ══════════════════════════════════════════════════════════════════════════════
if menu == "🗂 Données":
    st.markdown("""
    <div class='page-header-bar'>
        <p class='page-title'>DONNÉES DE PLANIFICATION</p>
        <p class='page-subtitle'>Uploadez votre fichier Excel template et lancez l'optimisation.</p>
    </div>""", unsafe_allow_html=True)

    col_upload, col_btn = st.columns([3, 1])
    with col_upload:
        excel_file = st.file_uploader(
            "📎 Fichier Excel (template_gantt.xlsx)",
            type=["xlsx"], key="excel_solver",
            help="Utilisez le template fourni. Les 4 feuilles doivent être complètes."
        )
    with col_btn:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        run_solver = st.button("CALCULER LE PLANNING", key="run_solver_btn")

    solve_profiles = {
        "Rapide": {"max_time_seconds": 20.0, "relative_gap_limit": 0.15},
        "Standard": {"max_time_seconds": 60.0, "relative_gap_limit": 0.08},
        "Approfondi": {"max_time_seconds": 180.0, "relative_gap_limit": 0.03},
    }
    solve_mode = st.selectbox(
        "MODE DE RÉSOLUTION",
        list(solve_profiles.keys()),
        index=0,
        help="Rapide renvoie une bonne solution plus vite. Approfondi cherche plus longtemps."
    )

    use_previous_planning = False
    selected_base_day = None
    archived_days = load_planning_jours(SID) if SID else []
    if archived_days:
        archived_days_sorted = sorted(archived_days, key=lambda x: x["jour"], reverse=True)
        archived_options = {
            f"{item.get('label', item['jour'])} | {item['jour']}": str(item["jour"])
            for item in archived_days_sorted
        }
        use_previous_planning = st.checkbox(
            "Continuer depuis un planning archive",
            key="continue_last_planning",
            help="Les nouvelles operations seront planifiees en tenant compte de la disponibilite des machines du planning historique choisi."
        )
        if use_previous_planning:
            selected_label = st.selectbox(
                "PLANNING HISTORIQUE DE BASE",
                list(archived_options.keys()),
                index=0,
                key="planning_base_day",
            )
            selected_base_day = archived_options[selected_label]
            st.caption(f"Base de continuation : {selected_base_day}")

    if excel_file is not None:
        try:
            from backend.solver.input_parser import parse_excel_to_dict, validate_excel_data
            excel_bytes  = excel_file.read()
            data_preview = parse_excel_to_dict(io.BytesIO(excel_bytes))
            ok_val, msg_val = validate_excel_data(data_preview)
            if not ok_val:
                st.error(f"❌ Erreur dans le fichier : {msg_val}")
            else:
                p = data_preview['params']
                c1p, c2p, c3p, c4p, c5p = st.columns(5)
                c1p.metric("PIÈCES",      p['nbJobs'])
                c2p.metric("MACHINES",    p['nbMchs'])
                c3p.metric("OPÉRATIONS",  p['nbOps'])
                c4p.metric("TECHNICIENS", data_preview['nbtechs'])
                c5p.metric("SETUP (min)", data_preview['cte'])
                st.success("✔ Fichier valide — prêt pour l'optimisation")
                st.session_state["excel_data_cache"] = excel_bytes
                st.session_state["cte"] = int(data_preview.get("cte", 0))
        except Exception as e:
            st.error(f"❌ Impossible de lire le fichier : {e}")
    else:
        st.markdown("""
        <p style='color:#8b949e;font-size:12px;font-family:Inter,sans-serif'>
        ▸ Sans fichier uploadé, le solveur utilise les
        <b style='color:#ff6b00'>données de test intégrées</b>
        (13 pièces · 15 machines · 30 opérations · 6 techniciens · cte=15 min).
        </p>""", unsafe_allow_html=True)

    if "data" in st.session_state:
        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        st.markdown("<span class='status-badge'>⬡ DONNÉES EN MÉMOIRE</span>",
                    unsafe_allow_html=True)
        st.dataframe(st.session_state["data"], use_container_width=True)

    if run_solver:
        from backend.solver.input_parser import (parse_excel_to_dict,
                                                  validate_excel_data,
                                                  DATA as DEFAULT_DATA)
        from backend.solver.model import solve_flexible_jobshop

        if "excel_data_cache" in st.session_state:
            try:
                solver_data = parse_excel_to_dict(
                    io.BytesIO(st.session_state["excel_data_cache"]))
            except Exception as e:
                st.error(f"❌ Erreur lecture Excel : {e}")
                st.stop()
        else:
            solver_data = DEFAULT_DATA
            st.info("ℹ Aucun fichier uploadé — utilisation des données de test.")

        ok_val, msg_val = validate_excel_data(solver_data)
        if not ok_val:
            st.error(f"❌ Données invalides : {msg_val}")
            st.stop()

        st.session_state["cte"] = int(solver_data.get("cte", 0))

        if use_previous_planning and selected_base_day:
            detail_prev = load_planning_jour_detail(SID, selected_base_day)
            if detail_prev is not None and not detail_prev["df_ops"].empty:
                machine_ready_times = (
                    detail_prev["df_ops"]
                    .groupby("MachineID")["EndTime"]
                    .max()
                    .astype(int)
                    .to_dict()
                )
                solver_data["machine_ready_times"] = machine_ready_times
                st.info(
                    f"Continuation activee depuis {selected_base_day} "
                    f"sur {len(machine_ready_times)} machine(s)."
                )

        profile = solve_profiles[solve_mode]

        with st.spinner(
            f"⚙ Résolution en cours — mode {solve_mode.lower()} "
            f"({int(profile['max_time_seconds'])} s max)..."
        ):
            try:
                df_result  = solve_flexible_jobshop(
                    solver_data,
                    max_time_seconds=profile["max_time_seconds"],
                    num_search_workers=8,
                    log_search_progress=False,
                    relative_gap_limit=profile["relative_gap_limit"],
                )
                gammes_map = {g[0]: g[1] for g in solver_data["gammes"]}
                df_result["JobID"] = df_result["OperationID"].map(
                    gammes_map).fillna(0).astype(int)

                of_map    = solver_data.get("of_map", {})
                piece_map = solver_data.get("piece_map", {})
                st.session_state["of_map"]    = of_map
                st.session_state["piece_map"] = piece_map
                save_of_piece_maps(of_map, piece_map, SID)

                st.session_state["data"] = df_result
                save_operations(df_result, SID)

                rows_jobs    = [{"OperationID": g[0], "JobID": g[1]}
                                for g in solver_data["gammes"]]
                df_jobs_auto = pd.DataFrame(rows_jobs)
                st.session_state["df_jobs"] = df_jobs_auto
                save_jobs(df_jobs_auto, SID)
                st.session_state.pop("excel_data_cache", None)

                makespan  = planning_makespan(df_result)
                nb_pieces = df_result["JobID"].nunique()

                st.success(
                    f"✔ Solution trouvée — Makespan : **{makespan} min** · "
                    f"{len(df_result)} opérations · {nb_pieces} pièces planifiées"
                )
                col_r1, col_r2 = st.columns([3, 1])
                with col_r1:
                    st.dataframe(df_result, use_container_width=True)
                with col_r2:
                    st.markdown("<p class='section-title'>Résumé</p>", unsafe_allow_html=True)
                    st.metric("MAKESPAN",   f"{makespan} min")
                    st.metric("OPÉRATIONS", len(df_result))
                    st.metric("PIÈCES",     nb_pieces)
                    st.metric("MACHINES",   df_result["MachineID"].nunique())

            except Exception as e:
                st.error(f"❌ Erreur solveur : {e}")

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 2 — GANTT
# ══════════════════════════════════════════════════════════════════════════════
elif menu == "🗓 Planning":
    st.markdown("""
    <div class='page-header-bar'>
        <p class='page-title'>DIAGRAMME DE GANTT</p>
        <p class='page-subtitle'>Visualisation de l'ordonnancement des opérations sur les machines.</p>
    </div>""", unsafe_allow_html=True)

    if "data" not in st.session_state:
        st.info("⚠ Chargez d'abord vos données dans Upload Data")
    else:
        df_ops    = st.session_state["data"].copy()
        df_jobs   = st.session_state.get("df_jobs", None)
        of_map    = st.session_state.get("of_map", {})
        piece_map = st.session_state.get("piece_map", {})

        if "JobID" not in df_ops.columns:
            if df_jobs is not None and not df_jobs.empty:
                df_ops = pd.merge(df_ops, df_jobs[["OperationID", "JobID"]],
                                  on="OperationID", how="left")
            df_ops["JobID"] = df_ops.get("JobID", 0)
        df_ops["JobID"] = df_ops["JobID"].fillna(0).astype(int)
        start_time_day = int(st.session_state.get("start_time_day", 360))
        cte_value = int(st.session_state.get("cte", 0))
        max_end_time = int(df_ops["EndTime"].max())
        day_count = max(1, (max_end_time + WORKDAY_MINUTES - 1) // WORKDAY_MINUTES)

        col_machine, col_day, col_job = st.columns([3, 2, 3])
        with col_machine:
            machines = sorted(
                df_ops["MachineLabel"].unique().tolist(),
                key=lambda x: int(x.split()[-1])
            )
            selected_machines = st.multiselect(
                "FILTRER PAR MACHINE",
                machines,
                default=machines,
                key="planning_machine_filter",
                help="Selectionnez une ou plusieurs machines a afficher."
            )
        with col_day:
            all_day_options = [f"Jour {idx}" for idx in range(1, day_count + 1)]
            day_options = all_day_options[-2:] if len(all_day_options) >= 2 else all_day_options
            default_days = day_options
            selected_days = st.multiselect(
                "FILTRER PAR JOUR",
                day_options,
                default=default_days,
                key="planning_day_filter",
                help="Selectionnez les jours visibles dans le diagramme."
            )
        with col_job:
            jobs = sorted(df_ops["JobID"].dropna().astype(int).unique().tolist())
            job_options = {piece_label(job_id): job_id for job_id in jobs}
            selected_job_labels = st.multiselect(
                "FILTRER PAR PIECE / JOB",
                list(job_options.keys()),
                default=list(job_options.keys()),
                key="planning_job_filter",
                help="Selectionnez les pieces/jobs a afficher."
            )
            selected_jobs = [job_options[label] for label in selected_job_labels]

        df_f = df_ops if not selected_machines else df_ops[df_ops["MachineLabel"].isin(selected_machines)]
        if selected_jobs:
            df_f = df_f[df_f["JobID"].isin(selected_jobs)]
        x_range = None
        if selected_days:
            selected_day_indexes = sorted(int(day.split()[-1]) - 1 for day in selected_days)
            day_ranges = [
                (day_index * WORKDAY_MINUTES, (day_index + 1) * WORKDAY_MINUTES)
                for day_index in selected_day_indexes
            ]
            day_mask = False
            for day_start, day_end in day_ranges:
                current_mask = (df_f["StartTime"] < day_end) & (df_f["EndTime"] > day_start)
                day_mask = current_mask if isinstance(day_mask, bool) else (day_mask | current_mask)
            df_f = df_f[day_mask]
            x_range = (day_ranges[0][0], day_ranges[-1][1])
        fig  = build_gantt(
            df_f,
            df_jobs,
            of_map=of_map,
            piece_map=piece_map,
            start_time_day=start_time_day,
            cte=cte_value,
            x_range=x_range,
        )
        fig.update_layout(**chart_layout())
        st.plotly_chart(fig, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 3 — KPIs
# ══════════════════════════════════════════════════════════════════════════════
elif menu == "📈 KPI":
    st.markdown("""
    <div class='page-header-bar'>
        <p class='page-title'>INDICATEURS DE PERFORMANCE</p>
        <p class='page-subtitle'>KPIs d'ordonnancement, coûts et rentabilité par OF et par pièce.</p>
    </div>""", unsafe_allow_html=True)

    if "data" not in st.session_state:
        st.info("⚠ Chargez d'abord vos données dans Upload Data")
    else:
        df      = st.session_state["data"].copy()
        df_jobs = st.session_state.get("df_jobs", None)

        if "JobID" not in df.columns:
            if df_jobs is not None and not df_jobs.empty:
                df = pd.merge(df, df_jobs[["OperationID", "JobID"]],
                              on="OperationID", how="left")
            else:
                df["JobID"] = df["OperationID"]

        df["JobID"]    = df["JobID"].fillna(0).astype(int)
        df["JobLabel"] = df["JobID"].apply(piece_label)

        makespan        = int(df["EndTime"].max() - df["StartTime"].min())
        nb_machines     = df["MachineID"].nunique()
        duree_totale    = df["Duration"].sum()
        machine_util    = df.groupby("MachineLabel")["Duration"].sum()
        idle_total      = (makespan * nb_machines) - duree_totale
        taux_util_moyen = round(machine_util.sum() / (makespan * nb_machines) * 100, 1)
        taux_idle       = round(idle_total / (makespan * nb_machines) * 100, 1)

        job_cycle = df.groupby("JobLabel").agg(
            Debut=("StartTime", "min"), Fin=("EndTime", "max"))
        job_cycle["CycleTime"] = job_cycle["Fin"] - job_cycle["Debut"]
        cycle_moyen = round(job_cycle["CycleTime"].mean(), 1)

        prix_saved = st.session_state.get("prix_db", {})

        tab1, tab2, tab3, tab4 = st.tabs([
            "ORDONNANCEMENT", "COÛTS PAR OF", "PROFIT & MARGE", "VISUALISATION"
        ])

        with tab1:
            due_date = int(df["EndTime"].max())
            col_p1, _ = st.columns([2, 5])
            with col_p1:
                start_time_day = st.number_input(
                    "DÉBUT JOURNÉE (MIN DEPUIS 6H00)",
                    min_value=0, value=360, step=10, key="start_time_day")
                st.caption(f"Heure affichee : {minutes_to_time(0, int(start_time_day))}")

            st.info(f"📅 Makespan du lot courant : **{makespan} min**")

            jobs_en_retard = (job_cycle["Fin"] > due_date).sum()
            taux_retard    = round(jobs_en_retard / len(job_cycle) * 100, 1)

            st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("MAKESPAN",         f"{makespan} min")
            c2.metric("TAUX UTILISATION", f"{taux_util_moyen} %")
            c3.metric("CYCLE MOYEN",      f"{cycle_moyen} min")
            c4.metric("TAUX RETARD",      f"{taux_retard} %")
            c5.metric("IDLE TIME",        f"{taux_idle} %")

            st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
            st.markdown("<p class='section-title'>🔍 Insights automatiques</p>", unsafe_allow_html=True)
            if taux_util_moyen < 60: st.warning("⚠ Sous-utilisation globale des machines")
            if taux_util_moyen > 85: st.error("🚨 Risque de saturation des machines")
            if taux_retard > 20:     st.warning("⚠ Taux de retard élevé → revoir ordonnancement")
            if taux_idle > 30:       st.info("💡 Opportunité d'optimisation des ressources")

            st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
            st.markdown("<p class='section-title'>🧠 Recommandations</p>", unsafe_allow_html=True)
            if taux_idle > 25:       st.write("➡️ Réduire le nombre de machines ou regrouper les tâches")
            if taux_util_moyen < 50: st.write("➡️ Augmenter la charge ou revoir planification")
            if jobs_en_retard > 0:   st.write("➡️ Prioriser les pièces critiques ou ajuster séquencement")

            score = max(0, min(100, round((taux_util_moyen - taux_idle - taux_retard), 1)))
            st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
            st.markdown("<p class='section-title'>Performance globale</p>", unsafe_allow_html=True)
            st.metric("SCORE", f"{score}/100")

            st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
            st.markdown("<p class='section-title'>Utilisation par machine</p>", unsafe_allow_html=True)
            df_util = pd.DataFrame({
                "Machine":        machine_util.index,
                "Charge (min)":   machine_util.values,
                "Taux util. (%)": (machine_util.values / makespan * 100).round(1),
                "Idle (min)":     makespan - machine_util.values,
            })
            st.dataframe(df_util, use_container_width=True, hide_index=True)

            st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
            st.markdown("<p class='section-title'>Temps de cycle par pièce</p>", unsafe_allow_html=True)
            jcd = job_cycle.reset_index()[["JobLabel", "Debut", "Fin", "CycleTime"]]
            jcd.columns = ["Pièce", "Début", "Fin", "Cycle (min)"]
            jcd["En retard"] = jcd["Fin"].apply(lambda x: "⚠ OUI" if x > due_date else "✔ NON")
            st.dataframe(jcd, use_container_width=True, hide_index=True)

        with tab2:
            st.markdown("<p class='section-title'>Paramètres de coût</p>", unsafe_allow_html=True)
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                cout_machine_h = st.number_input("COÛT MACHINE (€/H)", min_value=0.0,
                                                  value=50.0, step=5.0, key="cout_machine")
            with col2:
                cout_mo_h = st.number_input("COÛT MAIN-D'ŒUVRE (€/H)", min_value=0.0,
                                             value=20.0, step=2.0, key="cout_mo")
            with col3:
                cout_indirect_h = st.number_input("COÛT INDIRECT (€/H)", min_value=0.0,
                                                   value=10.0, step=1.0, key="cout_indirect")
            with col4:
                prix_matiere_unit = st.number_input("MATIÈRE (€/UNITÉ)", min_value=0.0,
                                                     value=5.0, step=0.5, key="prix_matiere")

            st.session_state["kpi_params"] = {
                "cout_machine_h":    cout_machine_h,
                "cout_mo_h":         cout_mo_h,
                "cout_indirect_h":   cout_indirect_h,
                "prix_matiere_unit": prix_matiere_unit,
            }

            cout_machine_min  = cout_machine_h  / 60
            cout_mo_min       = cout_mo_h       / 60
            cout_indirect_min = cout_indirect_h / 60

            df_cout = df.groupby("JobLabel").agg(
                Nb_Ops=("OperationID", "count"), Duree_min=("Duration", "sum")
            ).reset_index()
            df_cout["Pièce"]             = df_cout["JobLabel"]
            df_cout["Qté"]               = 1
            df_cout["Coût machine (€)"]  = round(df_cout["Duree_min"] * cout_machine_min, 2)
            df_cout["Coût MO (€)"]       = round(df_cout["Duree_min"] * cout_mo_min, 2)
            df_cout["Coût indirect (€)"] = round(df_cout["Duree_min"] * cout_indirect_min, 2)
            df_cout["Coût matière (€)"]  = round(df_cout["Qté"] * prix_matiere_unit, 2)
            df_cout["Coût total (€)"]    = round(
                df_cout["Coût machine (€)"] + df_cout["Coût MO (€)"] +
                df_cout["Coût indirect (€)"] + df_cout["Coût matière (€)"], 2)
            st.session_state["df_cout"] = df_cout

            st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("COÛT MACHINE",  f"{df_cout['Coût machine (€)'].sum():,.1f} €")
            c2.metric("COÛT MO",       f"{df_cout['Coût MO (€)'].sum():,.1f} €")
            c3.metric("COÛT MATIÈRE",  f"{df_cout['Coût matière (€)'].sum():,.1f} €")
            c4.metric("COÛT GLOBAL",   f"{df_cout['Coût total (€)'].sum():,.1f} €")

            st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
            st.dataframe(
                df_cout[["Pièce", "Nb_Ops", "Duree_min", "Coût machine (€)",
                          "Coût MO (€)", "Coût indirect (€)",
                          "Coût matière (€)", "Coût total (€)"]],
                use_container_width=True, hide_index=True)

        with tab3:
            st.markdown("<p class='section-title'>Prix de vente par pièce</p>", unsafe_allow_html=True)
            job_ids   = sorted(df["JobID"].unique())
            cols_prix = st.columns(min(len(job_ids), 7))
            prix_vente = {}
            for i, jid in enumerate(job_ids):
                with cols_prix[i % max(1, min(len(job_ids), 7))]:
                    saved_val = prix_saved.get(jid, prix_saved.get(str(jid), 10.0))
                    prix_vente[jid] = st.number_input(
                        f"P{jid}", min_value=0.0,
                        value=float(saved_val), step=1.0, key=f"pv_{jid}"
                    )

            if st.button("▶ CALCULER PROFIT & MARGE"):
                save_prix(prix_vente, SID)
                st.session_state["prix_db"] = prix_vente

                df_profit = df.groupby(["JobLabel", "JobID"]).agg(
                    Duree_min=("Duration", "sum")).reset_index()

                if "df_cout" in st.session_state:
                    df_profit = pd.merge(df_profit,
                        st.session_state["df_cout"][["JobLabel", "Qté", "Coût total (€)"]],
                        on="JobLabel", how="left")
                else:
                    params = st.session_state.get("kpi_params", {
                        "cout_machine_h": 50.0, "cout_mo_h": 20.0,
                        "cout_indirect_h": 10.0, "prix_matiere_unit": 5.0
                    })
                    cout_min = {k: params[k] / 60 for k in
                                ["cout_machine_h", "cout_mo_h", "cout_indirect_h"]}
                    df_fallback = df.groupby("JobLabel").agg(
                        Duree_min=("Duration", "sum")).reset_index()
                    df_fallback["Qté"] = 1
                    df_fallback["Coût total (€)"] = round(
                        df_fallback["Duree_min"] * (
                            cout_min["cout_machine_h"] + cout_min["cout_mo_h"] +
                            cout_min["cout_indirect_h"]
                        ) + params["prix_matiere_unit"], 2)
                    st.session_state["df_cout"] = df_fallback
                    df_profit = pd.merge(df_profit,
                        df_fallback[["JobLabel", "Qté", "Coût total (€)"]],
                        on="JobLabel", how="left")
                    st.warning("⚠ Coûts calculés avec les paramètres par défaut.")

                df_profit["Pièce"]            = df_profit["JobLabel"]
                df_profit["Prix vente (€/u)"] = df_profit["JobID"].map(prix_vente).fillna(0)
                df_profit["Revenu (€)"]        = round(df_profit["Qté"] * df_profit["Prix vente (€/u)"], 2)
                df_profit["Profit (€)"]        = round(df_profit["Revenu (€)"] - df_profit["Coût total (€)"], 2)
                df_profit["Marge (%)"]         = round(
                    df_profit["Profit (€)"] / df_profit["Revenu (€)"].replace(0, 1) * 100, 1)

                st.session_state["data_kpi"] = df_profit
                save_kpis(df_profit[["JobLabel", "Duree_min", "Profit (€)", "Marge (%)"]], SID)

                st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("REVENU TOTAL",  f"{df_profit['Revenu (€)'].sum():,.1f} €")
                c2.metric("COÛT TOTAL",    f"{df_profit['Coût total (€)'].sum():,.1f} €")
                c3.metric("PROFIT TOTAL",  f"{df_profit['Profit (€)'].sum():,.1f} €")
                c4.metric("MARGE MOY.",    f"{df_profit['Marge (%)'].mean():.1f} %")

                def color_marge(val):
                    if val >= 20:  return "color: #3fb950; font-weight: 700"
                    elif val >= 0: return "color: #f59e0b; font-weight: 700"
                    else:          return "color: #f85149; font-weight: 700"

                st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
                st.dataframe(
                    df_profit[["Pièce", "Qté", "Revenu (€)", "Coût total (€)",
                               "Profit (€)", "Marge (%)"]].style.applymap(
                        color_marge, subset=["Marge (%)"]),
                    use_container_width=True, hide_index=True)

                pieces_deficit = df_profit[df_profit["Profit (€)"] < 0]
                if not pieces_deficit.empty:
                    st.warning(f"⚠ {len(pieces_deficit)} pièce(s) déficitaire(s) : "
                               f"{', '.join(pieces_deficit['Pièce'].tolist())}")
                else:
                    st.success("✔ Toutes les pièces sont rentables")

        with tab4:
            import plotly.graph_objects as go

            st.markdown("<p class='section-title'>Visualisation des KPIs</p>", unsafe_allow_html=True)

            taux_par_machine = (machine_util.values / makespan * 100).round(1)
            idle_par_machine = (100 - taux_par_machine).round(1)

            def color_util(taux):
                if taux >= 75:   return "#3fb950"
                elif taux >= 50: return "#58a6ff"
                elif taux >= 25: return "#f59e0b"
                else:            return "#f85149"

            colors_util = [color_util(v) for v in taux_par_machine]

            st.markdown(
                "<p class='section-title'>Taux d'utilisation par machine"
                " &nbsp;<span style='font-family:Inter,sans-serif;font-weight:400;"
                "font-size:10px;color:#8b949e;text-transform:none;letter-spacing:0'>"
                "🟢 ≥75% · 🔵 50-75% · 🟠 25-50% · 🔴 &lt;25%"
                "</span></p>", unsafe_allow_html=True)

            fig_util = go.Figure()
            fig_util.add_trace(go.Bar(
                name="Utilisation (%)", x=machine_util.index.tolist(), y=taux_par_machine,
                marker_color=colors_util, marker_line=dict(width=0),
                text=[f"{v}%" for v in taux_par_machine], textposition="inside",
                textfont=dict(color="#ffffff", size=11, family="Inter")
            ))
            fig_util.add_trace(go.Bar(
                name="Idle (%)", x=machine_util.index.tolist(), y=idle_par_machine,
                marker_color="rgba(48,54,61,0.6)", marker_line=dict(width=0),
                text=[f"{v}%" for v in idle_par_machine], textposition="inside",
                textfont=dict(color="#8b949e", size=10)
            ))
            fig_util.add_hline(y=75, line_dash="dot", line_color="#ffffff", line_width=1.8,
                annotation_text="Seuil 75%",
                annotation_font_color="#ffffff", annotation_font_size=10)
            fig_util.update_layout(**chart_layout(
                barmode="stack", height=440,
                legend=dict(orientation="h", y=1.1, font=dict(color="#c9d1d9", size=11)),
                yaxis=dict(range=[0, 110], title="% Makespan", gridcolor="#21262d", color="#8b949e"),
                xaxis=dict(gridcolor="#21262d", color="#8b949e")
            ))
            st.plotly_chart(fig_util, use_container_width=True)

            col_g1, col_g2 = st.columns(2)
            with col_g1:
                st.markdown("<p class='section-title'>Utilisation globale</p>", unsafe_allow_html=True)
                fig_pie = go.Figure(go.Pie(
                    labels=["Temps productif", "Temps idle"],
                    values=[duree_totale, idle_total], hole=0.58,
                    marker=dict(colors=["#ff6b00", "rgba(48,54,61,0.5)"],
                                line=dict(color="#161b22", width=3)),
                    textinfo="label+percent",
                    textfont=dict(size=11, color="#c9d1d9", family="Inter"),
                ))
                center_color = ("#3fb950" if taux_util_moyen >= 75
                                else "#ff6b00" if taux_util_moyen >= 50 else "#f59e0b")
                fig_pie.add_annotation(
                    text=f"<b>{taux_util_moyen}%</b>", x=0.5, y=0.5,
                    font=dict(size=22, color=center_color, family="Rajdhani"), showarrow=False)
                fig_pie.update_layout(**chart_layout(height=420, showlegend=False))
                st.plotly_chart(fig_pie, use_container_width=True)

            with col_g2:
                st.markdown("<p class='section-title'>Temps de cycle par pièce</p>", unsafe_allow_html=True)
                cycle_mean   = job_cycle["CycleTime"].mean()
                colors_cycle = ["#58a6ff" if v <= cycle_mean else "#f59e0b"
                                for v in job_cycle["CycleTime"]]
                fig_cycle = go.Figure()
                fig_cycle.add_trace(go.Bar(
                    x=job_cycle.index.tolist(), y=job_cycle["CycleTime"].tolist(),
                    marker_color=colors_cycle, marker_line=dict(width=0),
                    text=[f"{v} min" for v in job_cycle["CycleTime"].tolist()],
                    textposition="outside",
                    textfont=dict(color="#c9d1d9", size=10, family="Inter")
                ))
                fig_cycle.add_hline(y=cycle_mean, line_dash="dash",
                    line_color="#ffffff", line_width=2,
                    annotation_text=f"Moy : {cycle_mean:.0f} min",
                    annotation_font_color="#ffffff", annotation_font_size=10)
                fig_cycle.update_layout(**chart_layout(
                    height=420,
                    yaxis=dict(title="Minutes", gridcolor="#21262d", color="#8b949e"),
                    xaxis=dict(gridcolor="#21262d", color="#8b949e")
                ))
                st.plotly_chart(fig_cycle, use_container_width=True)

            if "data_kpi" in st.session_state:
                df_kpi = st.session_state["data_kpi"]
                if "Revenu (€)" in df_kpi.columns:
                    st.markdown(
                        "<p class='section-title' style='margin-top:8px'>Profit & Marge par pièce</p>",
                        unsafe_allow_html=True)
                    col_g3, col_g4 = st.columns(2)
                    piece_labels_list = df_kpi["Pièce"].tolist() if "Pièce" in df_kpi.columns \
                                        else df_kpi["JobLabel"].tolist()

                    with col_g3:
                        colors_profit = ["#3fb950" if v >= 0 else "#f85149"
                                         for v in df_kpi["Profit (€)"]]
                        fig_profit = go.Figure()
                        fig_profit.add_trace(go.Bar(
                            x=piece_labels_list, y=df_kpi["Profit (€)"].tolist(),
                            marker_color=colors_profit, marker_line=dict(width=0),
                            text=[f"{v:.1f}€" for v in df_kpi["Profit (€)"]],
                            textposition="outside",
                            textfont=dict(size=10, color="#c9d1d9", family="Inter")
                        ))
                        fig_profit.add_hline(y=0, line_color="#30363d", line_width=1.2)
                        fig_profit.update_layout(**chart_layout(
                            height=440,
                            title=dict(text="Profit (€) par pièce",
                                       font=dict(color="#ff6b00", size=12, family="Rajdhani"), x=0.01),
                            yaxis=dict(title="Profit (€)", gridcolor="#21262d", color="#8b949e"),
                            xaxis=dict(gridcolor="#21262d", color="#8b949e")
                        ))
                        st.plotly_chart(fig_profit, use_container_width=True)

                    with col_g4:
                        colors_marge = ["#3fb950" if v >= 20 else "#f59e0b" if v >= 0
                                        else "#f85149" for v in df_kpi["Marge (%)"]]
                        fig_marge = go.Figure()
                        fig_marge.add_trace(go.Bar(
                            x=piece_labels_list, y=df_kpi["Marge (%)"].tolist(),
                            marker_color=colors_marge, marker_line=dict(width=0),
                            text=[f"{v:.1f}%" for v in df_kpi["Marge (%)"]],
                            textposition="outside",
                            textfont=dict(size=10, color="#c9d1d9", family="Inter")
                        ))
                        max_marge = df_kpi["Marge (%)"].max()
                        fig_marge.add_hrect(y0=20, y1=max(max_marge * 1.3, 25),
                            fillcolor="rgba(0,188,212,0.05)", line_width=0)
                        fig_marge.add_hline(y=20, line_dash="dash",
                            line_color="#00bcd4", line_width=1.8,
                            annotation_text="Seuil 20%",
                            annotation_font_color="#00bcd4", annotation_font_size=10)
                        fig_marge.add_hline(y=0, line_color="#30363d", line_width=1)
                        fig_marge.update_layout(**chart_layout(
                            height=440,
                            title=dict(text="Marge (%) par pièce",
                                       font=dict(color="#ff6b00", size=12, family="Rajdhani"), x=0.01),
                            yaxis=dict(title="Marge (%)", gridcolor="#21262d", color="#8b949e"),
                            xaxis=dict(gridcolor="#21262d", color="#8b949e")
                        ))
                        st.plotly_chart(fig_marge, use_container_width=True)

                if "df_cout" in st.session_state:
                    st.markdown(
                        "<p class='section-title' style='margin-top:8px'>Décomposition des coûts par pièce</p>",
                        unsafe_allow_html=True)
                    dc = st.session_state["df_cout"]
                    fig_cout = go.Figure()
                    cost_items = [
                        ("Coût machine (€)",  "#58a6ff"),
                        ("Coût MO (€)",       "#8b49ff"),
                        ("Coût indirect (€)", "#f59e0b"),
                        ("Coût matière (€)",  "#f0883e"),
                    ]
                    x_labels = dc["Pièce"].tolist() if "Pièce" in dc.columns else dc["JobLabel"].tolist()
                    for col_name, col_color in cost_items:
                        if col_name in dc.columns:
                            fig_cout.add_trace(go.Bar(
                                name=col_name.replace(" (€)", ""),
                                x=x_labels, y=dc[col_name].tolist(),
                                marker_color=col_color, marker_line=dict(width=0),
                            ))
                    fig_cout.update_layout(**chart_layout(
                        barmode="stack", height=440,
                        legend=dict(orientation="h", y=1.1, font=dict(color="#c9d1d9", size=11)),
                        yaxis=dict(title="Coût (€)", gridcolor="#21262d", color="#8b949e"),
                        xaxis=dict(gridcolor="#21262d", color="#8b949e")
                    ))
                    st.plotly_chart(fig_cout, use_container_width=True)
            else:
                st.info("⚠ Calculez d'abord le Profit & Marge dans l'onglet correspondant")

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 4 — HISTORIQUE
# ══════════════════════════════════════════════════════════════════════════════
elif menu == "🕘 Historique":
    st.markdown("""
    <div class='page-header-bar'>
        <p class='page-title'>HISTORIQUE DES PLANIFICATIONS</p>
        <p class='page-subtitle'>Consultez et rechargez les plannings des jours précédents.</p>
    </div>""", unsafe_allow_html=True)

    try:
        jours = load_planning_jours(SID)

        if not jours:
            st.info("⚠ Aucun planning sauvegardé. Utilisez 'ARCHIVER LE JOUR' dans la barre latérale.")
        else:
            count_label = "PLANNING SAUVEGARDÉ" if len(jours) == 1 else "PLANNINGS SAUVEGARDÉS"
            st.markdown(f"<p class='section-title'>{len(jours)} {count_label}</p>",
                        unsafe_allow_html=True)

            for idx, jour_data in enumerate(
                    sorted(jours, key=lambda x: x['jour'], reverse=True)):
                jour_str   = str(jour_data['jour'])
                label      = jour_data.get('label', jour_str)
                makespan_h = jour_data.get('makespan', '—')

                expander_title = f"{label} • {makespan_h} min"
                with st.expander(expander_title,
                                 expanded=(idx == 0)):
                    detail = load_planning_jour_detail(SID, jour_str)
                    if detail is None:
                        st.warning("Impossible de charger le détail.")
                        continue

                    df_hist = detail["df_ops"]
                    df_j_h  = detail["df_jobs"]
                    pm_h    = detail.get("piece_map", {})
                    of_h    = detail.get("of_map", {})

                    if "JobID" in df_hist.columns:
                        df_hist["JobID"] = df_hist["JobID"].fillna(0).astype(int)
                        df_hist["Pièce"] = df_hist["JobID"].apply(
                            lambda x: f"P{x} — {pm_h[x]}" if pm_h and x in pm_h
                            else f"Pièce {x}")

                    col_info, col_actions = st.columns([4, 1])

                    with col_info:
                        nb_pieces_h = df_hist["JobID"].nunique() if "JobID" in df_hist.columns else "—"
                        nb_mchs_h   = df_hist["MachineID"].nunique() if "MachineID" in df_hist.columns else "—"
                        m1, m2, m3  = st.columns(3)
                        m1.metric("PIÈCES",   nb_pieces_h)
                        m2.metric("MACHINES", nb_mchs_h)
                        m3.metric("MAKESPAN", f"{makespan_h} min")

                        cols_show = [c for c in
                            ["OperationID", "Pièce", "MachineLabel",
                             "StartTime", "EndTime", "Duration"]
                            if c in df_hist.columns]
                        st.dataframe(df_hist[cols_show],
                                     use_container_width=True, hide_index=True)

                    with col_actions:
                        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
                        if st.button(f"RECHARGER", key=f"reload_{jour_str}"):
                            if "JobID" in df_hist.columns:
                                df_hist["JobLabel"] = df_hist["JobID"].apply(
                                    lambda x: f"Pièce {x}")
                            st.session_state["data"]      = df_hist
                            st.session_state["of_map"]    = of_h
                            st.session_state["piece_map"] = pm_h
                            save_operations(df_hist, SID)
                            if not df_j_h.empty:
                                st.session_state["df_jobs"] = df_j_h
                                save_jobs(df_j_h, SID)
                            st.success(f"✔ Planning du {jour_str} rechargé")
                            st.rerun()

                        try:
                            import plotly.io as pio
                            fig_h = build_gantt(
                                df_hist,
                                df_j_h if not df_j_h.empty else None,
                                of_map=of_h,
                                piece_map=pm_h,
                                start_time_day=int(st.session_state.get("start_time_day", 360)),
                                cte=int(st.session_state.get("cte", 0)),
                            )
                            gantt_html = pio.to_html(fig_h, full_html=True, include_plotlyjs="cdn")
                            st.download_button(
                                f"TÉLÉCHARGER GANTT", gantt_html.encode("utf-8"),
                                f"gantt_{jour_str}.html", "text/html",
                                key=f"dl_{jour_str}"
                            )
                        except Exception:
                            pass

    except Exception as e:
        st.error(f"❌ Erreur chargement historique : {e}")
        st.info("Vérifiez que la table 'planning_jours' existe dans Supabase.")

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 5 — DOWNLOAD
# ══════════════════════════════════════════════════════════════════════════════
elif menu == "📊 Analytics":
    if st.session_state.get("user_role") != "admin":
        st.error("Acces reserve aux administrateurs.")
        st.stop()

    st.markdown("""
    <div class='page-header-bar'>
        <p class='page-title'>ANALYTICS</p>
        <p class='page-subtitle'>Suivi des acces a l'application et des utilisateurs connectes.</p>
    </div>""", unsafe_allow_html=True)

    summary = load_access_summary()
    c1, c2, c3 = st.columns(3, gap="large")
    c1.metric("Acces enregistres", summary["total"])
    c2.metric("Utilisateurs uniques", summary["users"])
    c3.metric("Dernier acces", summary["last_access"] or "-")

    st.markdown("### Acces par utilisateur")
    if summary["by_user"].empty:
        st.info("Aucun acces enregistre pour le moment. Verifiez aussi que la table Supabase 'app_access_logs' existe.")
    else:
        st.dataframe(summary["by_user"], use_container_width=True, hide_index=True)

    st.markdown("### Derniers acces")
    logs = load_access_logs(limit=200)
    if logs.empty:
        st.info("Aucun journal disponible.")
    else:
        st.dataframe(logs, use_container_width=True, hide_index=True)

elif menu == "⤓ Export":
    st.markdown("""
    <div class='page-header-bar'>
        <p class='page-title'>EXPORT DES RÉSULTATS</p>
        <p class='page-subtitle'>Exportez vos résultats en CSV, Excel ou Gantt interactif HTML.</p>
    </div>""", unsafe_allow_html=True)

    if "data_kpi" not in st.session_state:
        st.info("⚠ Calculez d'abord les KPIs (onglet Profit & Marge)")
    else:
        df_kpi    = st.session_state["data_kpi"]
        df_ops    = st.session_state.get("data")
        df_jobs   = st.session_state.get("df_jobs")
        of_map    = st.session_state.get("of_map", {})
        piece_map = st.session_state.get("piece_map", {})

        c1, c2, c3 = st.columns(3, gap="large")

        with c1:
            st.markdown("""<div class='dl-card'>
                <span class='dl-icon'>📄</span>
                <span class='dl-label'>Export CSV — KPIs</span>
            </div>""", unsafe_allow_html=True)
            st.download_button("TÉLÉCHARGER CSV", to_csv_bytes(df_kpi),
                               "kpi_data.csv", "text/csv", use_container_width=True)

        with c2:
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine="openpyxl") as w:
                df_kpi.to_excel(w, sheet_name="KPIs", index=False)
                if "JobLabel" in df_kpi.columns and "Duree_min" in df_kpi.columns:
                    try:
                        summary_by_job(df_kpi).to_excel(w, sheet_name="Par Pièce", index=False)
                    except Exception:
                        pass
                if df_ops is not None:
                    try:
                        summary_by_machine(df_ops).to_excel(w, sheet_name="Par Machine", index=False)
                    except Exception:
                        pass
                if "df_cout" in st.session_state:
                    st.session_state["df_cout"].to_excel(w, sheet_name="Coûts", index=False)
            st.markdown("""<div class='dl-card'>
                <span class='dl-icon'>📊</span>
                <span class='dl-label'>Rapport Excel complet</span>
            </div>""", unsafe_allow_html=True)
            st.download_button("TÉLÉCHARGER EXCEL", buf.getvalue(), "rapport.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True)

        with c3:
            if df_ops is not None:
                import plotly.io as pio
                df_ops_exp = df_ops.copy()
                if "JobID" not in df_ops_exp.columns and df_jobs is not None:
                    job_map = df_jobs.set_index("OperationID")["JobID"].to_dict()
                    df_ops_exp["JobID"] = df_ops_exp["OperationID"].map(
                        job_map).fillna(0).astype(int)
                fig        = build_gantt(
                    df_ops_exp,
                    df_jobs,
                    of_map=of_map,
                    piece_map=piece_map,
                    start_time_day=int(st.session_state.get("start_time_day", 360)),
                    cte=int(st.session_state.get("cte", 0)),
                )
                gantt_html = pio.to_html(fig, full_html=True, include_plotlyjs="cdn")
                st.markdown("""<div class='dl-card'>
                    <span class='dl-icon'>📅</span>
                    <span class='dl-label'>Gantt HTML interactif</span>
                </div>""", unsafe_allow_html=True)
                st.download_button("TÉLÉCHARGER GANTT", gantt_html.encode("utf-8"),
                                   "gantt.html", "text/html", use_container_width=True)
            else:
                st.info("⚠ Chargez d'abord vos données pour exporter le Gantt")
