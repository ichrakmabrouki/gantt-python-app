import streamlit as st
import pandas as pd
import io
import uuid
from datetime import datetime
import streamlit_authenticator as stauth

from backend.converter      import convert_txt_to_df, load_jobs_from_txt
from backend.data_processor import load_file, validate, parse_and_clean, to_csv_bytes
from backend.gantt_builder  import build_gantt
from backend.kpi_calculator import compute_kpis, summary_by_machine, summary_by_job
from backend.database       import (
    init_db,
    save_operations, load_operations,
    save_jobs,       load_jobs,
    save_kpis,       load_kpis,
    save_prix,       load_prix,
    clear_all,
)

init_db()

st.set_page_config(page_title="Gantt Dashboard", layout="wide", page_icon="⚙️")

# ── Authentification ────────────────────────────────────────────────────────
credentials = {
    "usernames": {
        "ichrak": {
            "name": "Ichrak",
            "password": stauth.Hasher(["motdepasse123"]).generate()[0]
        },
        "user2": {
            "name": "User2",
            "password": stauth.Hasher(["motdepasse456"]).generate()[0]
        }
    }
}

authenticator = stauth.Authenticate(
    credentials,
    "gantt_dashboard",
    "auth_key_secret",
    cookie_expiry_days=7
)

name, authentication_status, username = authenticator.login("Connexion", "main")

if authentication_status is False:
    st.error("❌ Identifiant ou mot de passe incorrect")
    st.stop()
if authentication_status is None:
    st.stop()

authenticator.logout("🚪 Se déconnecter", "sidebar")
SID = username

# ══════════════════════════════════════════════════════════════════════════════
# CSS — THÈME INDUSTRIEL (dark mode forcé)
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@400;600;700&family=Share+Tech+Mono:wght@400&display=swap');

html, body,
[data-testid="stAppViewContainer"],
[data-testid="stAppViewContainer"] > div:first-child,
[data-testid="stHeader"],
[data-testid="stMain"],
.main, .block-container {
    background-color: #0d1117 !important;
    color: #c9d1d9 !important;
    color-scheme: dark !important;
}
@media (prefers-color-scheme: light) {
    html, body,
    [data-testid="stAppViewContainer"],
    [data-testid="stHeader"] {
        background-color: #0d1117 !important;
        color: #c9d1d9 !important;
    }
}

[data-testid="stSidebar"] {
    background-color: #161b22 !important;
    border-right: 2px solid #ff6b00 !important;
}
[data-testid="stSidebar"] * {
    font-family: 'Rajdhani', sans-serif !important;
    color: #8b949e !important;
}
[data-testid="stSidebar"] .stRadio label {
    font-size: 13px !important;
    font-weight: 600 !important;
    letter-spacing: 1.5px !important;
    text-transform: uppercase !important;
    color: #8b949e !important;
    padding: 10px 4px !important;
    transition: color 0.15s !important;
}
[data-testid="stSidebar"] .stRadio label:hover { color: #ff6b00 !important; }

*, p, div, span, li,
.stMarkdown p, [data-testid="stMarkdownContainer"] p {
    font-family: 'Share Tech Mono', monospace !important;
    color: #c9d1d9 !important;
    font-size: 13px !important;
    line-height: 1.6 !important;
    letter-spacing: 0.3px !important;
}

h1, h2, h3, h4,
.stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
    font-family: 'Rajdhani', sans-serif !important;
    color: #ff6b00 !important;
    font-weight: 700 !important;
    letter-spacing: 2px !important;
    text-transform: uppercase !important;
}

.masthead-eyebrow {
    font-family: 'Rajdhani', sans-serif !important;
    font-size: 1.15rem !important;
    font-weight: 700 !important;
    color: #ff6b00 !important;
    letter-spacing: 5px !important;
    text-transform: uppercase !important;
    margin: 0 0 6px 0 !important;
    text-shadow: 0 0 30px rgba(255,107,0,0.3) !important;
}
.masthead-accent {
    width: 60px;
    height: 2px;
    background: linear-gradient(90deg, #ff6b00, transparent);
    margin: 0 0 12px 0;
    border-radius: 2px;
}
.header-banner {
    background: linear-gradient(90deg, #161b22 0%, #1c2333 50%, #161b22 100%);
    border: 1px solid #ff6b00;
    border-radius: 4px;
    padding: 18px 28px;
    margin-bottom: 24px;
    display: flex;
    align-items: center;
    justify-content: space-between;
}
.header-left { display: flex; flex-direction: column; gap: 6px; }
.header-title {
    font-family: 'Rajdhani', sans-serif !important;
    font-size: 1.9rem !important;
    font-weight: 700 !important;
    color: #ff6b00 !important;
    letter-spacing: 7px !important;
    text-transform: uppercase !important;
    margin: 0 !important;
    line-height: 1 !important;
}
.header-page-active {
    font-family: 'Rajdhani', sans-serif !important;
    font-size: 0.95rem !important;
    font-weight: 700 !important;
    color: #c9d1d9 !important;
    letter-spacing: 4px !important;
    text-transform: uppercase !important;
    margin: 0 !important;
    padding-left: 10px !important;
    border-left: 3px solid #ff6b00 !important;
    display: block !important;
}
.header-date {
    font-family: 'Share Tech Mono', monospace !important;
    font-size: 0.8rem !important;
    color: #8b949e !important;
    text-align: right;
    line-height: 1.9;
}
.divline {
    height: 1px;
    background: linear-gradient(90deg, transparent, #ff6b0066, transparent);
    margin: 0 0 20px 0;
    border: none;
}
.sim-card {
    background: linear-gradient(135deg, #0d1117 0%, #111827 100%);
    border: 1px solid #ff6b0044;
    border-left: 4px solid #ff6b00;
    border-radius: 6px;
    padding: 24px 24px 20px 24px;
    margin-top: 28px;
    position: relative;
    overflow: hidden;
}
.sim-card::before {
    content: '';
    position: absolute;
    top: 0; right: 0;
    width: 180px; height: 180px;
    background: radial-gradient(circle at top right, rgba(255,107,0,0.06), transparent 70%);
    pointer-events: none;
}
.sim-card-header {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 20px;
    padding-bottom: 14px;
    border-bottom: 1px solid #21262d;
}
.sim-card-icon { font-size: 20px; line-height: 1; }
.sim-card-title {
    font-family: 'Rajdhani', sans-serif !important;
    font-size: 0.85rem !important;
    font-weight: 700 !important;
    color: #ff6b00 !important;
    letter-spacing: 3px !important;
    text-transform: uppercase !important;
    margin: 0 !important;
}
.sim-card-badge {
    margin-left: auto;
    background: rgba(255,107,0,0.12);
    border: 1px solid rgba(255,107,0,0.3);
    border-radius: 2px;
    padding: 2px 8px;
    font-family: 'Share Tech Mono', monospace !important;
    font-size: 10px !important;
    color: #ff6b00 !important;
    letter-spacing: 1px !important;
}
.sim-result-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 10px 14px;
    margin-bottom: 8px;
    background: rgba(255,255,255,0.02);
    border: 1px solid #21262d;
    border-radius: 4px;
}
.sim-result-label {
    font-family: 'Share Tech Mono', monospace !important;
    font-size: 11px !important;
    color: #8b949e !important;
    letter-spacing: 0.5px !important;
}
.sim-result-value {
    font-family: 'Rajdhani', sans-serif !important;
    font-size: 1.1rem !important;
    font-weight: 700 !important;
    color: #c9d1d9 !important;
}
.sim-result-value.positive { color: #3fb950 !important; }
.sim-result-value.negative { color: #f85149 !important; }
.sim-result-value.neutral  { color: #f59e0b !important; }
.page-header-bar {
    background: #161b22;
    border: 1px solid #30363d;
    border-left: 3px solid #ff6b00;
    border-radius: 4px;
    padding: 14px 20px;
    margin-bottom: 20px;
}
.page-title {
    font-family: 'Rajdhani', sans-serif !important;
    font-size: 1.1rem !important;
    font-weight: 700 !important;
    color: #ff6b00 !important;
    letter-spacing: 3px !important;
    text-transform: uppercase !important;
    margin: 0 0 4px 0 !important;
}
.page-subtitle {
    font-family: 'Share Tech Mono', monospace !important;
    font-size: 0.72rem !important;
    color: #8b949e !important;
    margin: 0 !important;
    letter-spacing: 0.5px !important;
}
.section-title {
    font-family: 'Rajdhani', sans-serif !important;
    font-size: 0.72rem !important;
    font-weight: 700 !important;
    color: #ff6b00 !important;
    letter-spacing: 3px !important;
    text-transform: uppercase !important;
    margin-bottom: 10px;
    padding-bottom: 8px;
    border-bottom: 1px solid #30363d;
}
[data-testid="stMetric"] {
    background: #161b22 !important;
    border: 1px solid #30363d !important;
    border-top: 3px solid #ff6b00 !important;
    border-radius: 4px !important;
    padding: 14px 16px !important;
}
[data-testid="stMetricValue"] {
    font-family: 'Rajdhani', sans-serif !important;
    color: #ff6b00 !important;
    font-size: 1.6rem !important;
    font-weight: 700 !important;
}
[data-testid="stMetricLabel"] {
    font-family: 'Share Tech Mono', monospace !important;
    color: #8b949e !important;
    font-size: 0.62rem !important;
    letter-spacing: 2px !important;
    text-transform: uppercase !important;
}
.stButton > button {
    background: transparent !important;
    border: 1px solid #ff6b00 !important;
    color: #ff6b00 !important;
    font-family: 'Rajdhani', sans-serif !important;
    font-weight: 700 !important;
    font-size: 13px !important;
    letter-spacing: 2px !important;
    text-transform: uppercase !important;
    border-radius: 2px !important;
    padding: 8px 22px !important;
    transition: all 0.15s ease !important;
}
.stButton > button:hover {
    background: #ff6b00 !important;
    color: #0d1117 !important;
}
.stDownloadButton > button {
    background: transparent !important;
    border: 1px solid #30363d !important;
    color: #c9d1d9 !important;
    font-family: 'Rajdhani', sans-serif !important;
    font-size: 13px !important;
    font-weight: 600 !important;
    letter-spacing: 1.5px !important;
    text-transform: uppercase !important;
    border-radius: 2px !important;
    width: 100% !important;
    transition: all 0.15s ease !important;
}
.stDownloadButton > button:hover {
    border-color: #ff6b00 !important;
    color: #ff6b00 !important;
}
.stNumberInput > div > div > input,
.stTextInput > div > div > input {
    background-color: #0d1117 !important;
    border: 1px solid #30363d !important;
    color: #c9d1d9 !important;
    font-family: 'Share Tech Mono', monospace !important;
    font-size: 13px !important;
    border-radius: 2px !important;
}
.stNumberInput > div > div > input:focus {
    border-color: #ff6b00 !important;
    box-shadow: 0 0 0 1px #ff6b0044 !important;
}
[data-testid="stSelectbox"] > div > div {
    background: #161b22 !important;
    border: 1px solid #30363d !important;
    color: #c9d1d9 !important;
    font-family: 'Share Tech Mono', monospace !important;
    border-radius: 2px !important;
}
[data-testid="stFileUploader"] {
    background: #161b22 !important;
    border: 1px dashed #30363d !important;
    border-radius: 4px !important;
}
[data-testid="stFileUploader"]:hover { border-color: #ff6b00 !important; }
.stTabs [data-baseweb="tab-list"] {
    background: #161b22 !important;
    border: 1px solid #30363d !important;
    border-radius: 2px !important;
    padding: 4px !important;
    gap: 2px !important;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    border-radius: 2px !important;
    color: #8b949e !important;
    font-family: 'Rajdhani', sans-serif !important;
    font-weight: 600 !important;
    font-size: 12px !important;
    letter-spacing: 2px !important;
    text-transform: uppercase !important;
    padding: 7px 16px !important;
    border: 1px solid transparent !important;
    transition: all 0.15s !important;
}
.stTabs [aria-selected="true"] {
    background: #ff6b0012 !important;
    color: #ff6b00 !important;
    border-color: #ff6b00 !important;
}
.stTabs [data-baseweb="tab-panel"] {
    background: #161b22 !important;
    border: 1px solid #30363d !important;
    border-top: none !important;
    border-radius: 0 0 4px 4px !important;
    padding: 20px !important;
}
[data-testid="stDataFrame"] {
    border: 1px solid #30363d !important;
    border-radius: 4px !important;
    overflow: hidden !important;
    background: #161b22 !important;
}
[data-testid="stAlert"] {
    background: #161b22 !important;
    border-radius: 2px !important;
    border-left-width: 3px !important;
}
[data-testid="stAlert"] p {
    color: #c9d1d9 !important;
    font-size: 12px !important;
}
.status-badge {
    background: #0f2a1a;
    border: 1px solid #238636;
    border-radius: 2px;
    padding: 5px 10px;
    font-family: 'Share Tech Mono', monospace !important;
    font-size: 11px !important;
    color: #3fb950 !important;
    margin: 4px 0;
    display: block;
    letter-spacing: 0.5px;
}
.status-badge-teal {
    background: #0d1b2a;
    border: 1px solid #1f6feb;
    color: #58a6ff !important;
}
.dl-card {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 4px;
    padding: 28px 20px 20px;
    text-align: center;
    height: 150px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 10px;
}
.dl-icon { font-size: 26px; }
.dl-label {
    font-family: 'Rajdhani', sans-serif !important;
    font-size: 12px !important;
    font-weight: 700 !important;
    color: #8b949e !important;
    letter-spacing: 2px;
    text-transform: uppercase;
}
label {
    font-family: 'Rajdhani', sans-serif !important;
    font-size: 12px !important;
    font-weight: 600 !important;
    color: #8b949e !important;
    letter-spacing: 1px !important;
    text-transform: uppercase !important;
}
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: #0d1117; }
::-webkit-scrollbar-thumb { background: #30363d; border-radius: 2px; }
::-webkit-scrollbar-thumb:hover { background: #ff6b00; }

/* Fix login form - stop vibration */
div[data-testid="stForm"] input {
    animation: none !important;
    transition: none !important;
}
div[data-testid="stForm"] .stTextInput > div > div > input {
    animation: none !important;
    transition: none !important;
    border: 1px solid #30363d !important;
}
</style>
""", unsafe_allow_html=True)

# ── Chargement depuis Supabase ─────────────────────────────────────────────────
if "data" not in st.session_state:
    df_ops = load_operations(SID)
    if df_ops is not None:
        st.session_state["data"] = df_ops

if "df_jobs" not in st.session_state:
    df_jobs = load_jobs(SID)
    if df_jobs is not None:
        st.session_state["df_jobs"] = df_jobs

if "data_kpi" not in st.session_state:
    df_kpi = load_kpis(SID)
    if df_kpi is not None:
        st.session_state["data_kpi"] = df_kpi

if "prix_db" not in st.session_state:
    st.session_state["prix_db"] = load_prix(SID)

# ── Sidebar ────────────────────────────────────────────────────────────────────
st.sidebar.markdown("""
<p style='font-family:Rajdhani,sans-serif;font-size:0.65rem;font-weight:700;
   color:rgba(255,255,255,0.25);letter-spacing:3px;text-transform:uppercase;
   border-bottom:1px solid #30363d;padding-bottom:10px;margin-bottom:8px'>
   ⚙ NAVIGATION
</p>""", unsafe_allow_html=True)

menu = st.sidebar.radio("", [
    "📂 Upload Data",
    "📅 Gantt Diagram",
    "📈 KPI's",
    "⬇️ Download"
])

st.sidebar.markdown("<hr style='border-color:#30363d;margin:16px 0'>", unsafe_allow_html=True)

st.sidebar.markdown("<div style='margin-top:4px'>", unsafe_allow_html=True)
if "data" in st.session_state:
    st.sidebar.markdown(
        f"<span class='status-badge'>✔ {len(st.session_state['data'])} OPÉRATIONS</span>",
        unsafe_allow_html=True)
if "df_jobs" in st.session_state:
    n = st.session_state["df_jobs"]["JobID"].nunique()
    st.sidebar.markdown(
        f"<span class='status-badge status-badge-teal'>⬡ {n} JOBS MAPPÉS</span>",
        unsafe_allow_html=True)
if "data_kpi" in st.session_state:
    st.sidebar.markdown(
        "<span class='status-badge'>▶ KPIs CALCULÉS</span>",
        unsafe_allow_html=True)
st.sidebar.markdown("</div>", unsafe_allow_html=True)

st.sidebar.markdown("<hr style='border-color:#30363d;margin:16px 0'>", unsafe_allow_html=True)
if st.sidebar.button("🗑 RÉINITIALISER", key="reset_btn"):
    clear_all(SID)
    for key in ["data", "df_jobs", "data_kpi", "prix_db", "df_cout",
                "kpi_params", "profit_calculated"]:
        st.session_state.pop(key, None)
    st.rerun()

PAGE_LABELS = {
    "📂 Upload Data":   "Upload Data",
    "📅 Gantt Diagram": "Gantt Diagram",
    "📈 KPI's":         "KPI's",
    "⬇️ Download":      "Download",
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

# ── Helper charts ──────────────────────────────────────────────────────────────
def chart_layout(**kwargs):
    base = dict(
        paper_bgcolor="#161b22",
        plot_bgcolor="#0d1117",
        font=dict(color="#c9d1d9", family="Share Tech Mono", size=11),
        margin=dict(l=10, r=10, t=30, b=10),
        yaxis=dict(gridcolor="#21262d"),
        xaxis=dict(gridcolor="#21262d"),
    )
    base.update(kwargs)
    return base

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 1 — UPLOAD
# ══════════════════════════════════════════════════════════════════════════════
if menu == "📂 Upload Data":
    st.markdown("""
    <div class='page-header-bar'>
        <p class='page-title'>⬆ UPLOAD DATA</p>
        <p class='page-subtitle'>Importez les fichiers de planification machine et de mapping jobs.
        Les données sont automatiquement persistées en base.</p>
    </div>""", unsafe_allow_html=True)

    col1, col2 = st.columns(2, gap="large")

    with col1:
        st.markdown("<p class='section-title'>◈ Fichier Machines</p>", unsafe_allow_html=True)
        mchs_file = st.file_uploader("mchs_CP.txt · CSV · Excel",
                                     type=["txt", "csv", "xlsx", "xls"])
        if mchs_file:
            try:
                if mchs_file.name.endswith(".txt"):
                    content = mchs_file.read().decode("utf-8")
                    df_raw  = convert_txt_to_df(content)
                else:
                    df_raw = load_file(mchs_file)
                ok, msg = validate(df_raw)
                if not ok:
                    st.error(f"❌ {msg}")
                else:
                    df_clean = parse_and_clean(df_raw)
                    st.session_state["data"] = df_clean
                    ok_db, msg_db = save_operations(df_clean, SID)
                    if not ok_db:
                        st.error(f"❌ Erreur DB : {msg_db}")
                    else:
                        st.success(f"✔ {len(df_clean)} opérations chargées et sauvegardées")
                    st.dataframe(df_clean, use_container_width=True)
            except Exception as e:
                st.error(f"Erreur : {e}")
        elif "data" in st.session_state:
            st.markdown("<span class='status-badge'>⬡ DONNÉES EN MÉMOIRE</span>",
                        unsafe_allow_html=True)
            st.dataframe(st.session_state["data"], use_container_width=True)

    with col2:
        st.markdown("<p class='section-title'>◈ Fichier Jobs (opts.txt)</p>",
                    unsafe_allow_html=True)
        opts_file = st.file_uploader("opts.txt — mapping opération → job",
                                     type=["txt"], key="opts")
        if opts_file:
            content = opts_file.read().decode("utf-8")
            df_jobs = load_jobs_from_txt(content)
            st.session_state["df_jobs"] = df_jobs
            ok_db, msg_db = save_jobs(df_jobs, SID)
            if not ok_db:
                st.error(f"❌ Erreur DB : {msg_db}")
            else:
                st.success(f"✔ {df_jobs['JobID'].nunique()} jobs · {len(df_jobs)} opérations sauvegardés")
            st.dataframe(df_jobs, use_container_width=True)
        elif "df_jobs" in st.session_state:
            st.markdown("<span class='status-badge status-badge-teal'>⬡ JOBS EN MÉMOIRE</span>",
                        unsafe_allow_html=True)
            st.dataframe(st.session_state["df_jobs"], use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 2 — GANTT
# ══════════════════════════════════════════════════════════════════════════════
elif menu == "📅 Gantt Diagram":
    st.markdown("""
    <div class='page-header-bar'>
        <p class='page-title'>◈ GANTT DIAGRAM</p>
        <p class='page-subtitle'>Visualisation de l'ordonnancement des opérations sur les machines.</p>
    </div>""", unsafe_allow_html=True)

    if "data" not in st.session_state:
        st.info("⚠ Chargez d'abord vos données dans Upload Data")
    else:
        df_ops  = st.session_state["data"]
        df_jobs = st.session_state.get("df_jobs", None)

        col_sel, _ = st.columns([2, 5])
        with col_sel:
            machines = ["Toutes"] + sorted(
                df_ops["MachineLabel"].unique().tolist(),
                key=lambda x: int(x.split()[-1])
            )
            sel = st.selectbox("FILTRER PAR MACHINE", machines)

        df_f = df_ops if sel == "Toutes" else df_ops[df_ops["MachineLabel"] == sel]
        fig  = build_gantt(df_f, df_jobs)
        fig.update_layout(**chart_layout())
        fig.update_xaxes(color="#8b949e")
        fig.update_yaxes(color="#8b949e")
        st.plotly_chart(fig, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 3 — KPIs
# ══════════════════════════════════════════════════════════════════════════════
elif menu == "📈 KPI's":
    st.markdown("""
    <div class='page-header-bar'>
        <p class='page-title'>◈ KPI'S</p>
        <p class='page-subtitle'>KPIs d'ordonnancement, coûts et rentabilité par OF et par machine.</p>
    </div>""", unsafe_allow_html=True)

    if "data" not in st.session_state:
        st.info("⚠ Chargez d'abord vos données dans Upload Data")
    else:
        df      = st.session_state["data"].copy()
        df_jobs = st.session_state.get("df_jobs", None)

        if df_jobs is not None:
            df = pd.merge(df, df_jobs[["OperationID", "JobID"]],
                          on="OperationID", how="left")
            df["JobID"]    = df["JobID"].fillna(0).astype(int)
            df["JobLabel"] = "Job " + df["JobID"].astype(str)
        else:
            df["JobID"]    = df["OperationID"]
            df["JobLabel"] = "OP-" + df["OperationID"].astype(str)

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
        cycle_moyen    = round(job_cycle["CycleTime"].mean(), 1)

        prix_saved = st.session_state.get("prix_db", {})

        tab1, tab2, tab3, tab4 = st.tabs([
            "ORDONNANCEMENT", "COÛTS PAR OF", "PROFIT & MARGE", "VISUALISATION"
        ])

        with tab1:
            due_date = int(df["EndTime"].max())

            col_p1, col_p2 = st.columns(2)
            with col_p1:
                start_time_day = st.number_input(
                    "DÉBUT JOURNÉE (MIN DEPUIS 00H00)",
                    min_value=0, value=360, step=10, help="Ex: 360 = 06h00",
                    key="start_time_day")
            with col_p2:
                nb_operateurs = st.number_input(
                    "NOMBRE D'OPÉRATEURS", min_value=1, value=3, step=1,
                    key="nb_operateurs_input")
            st.session_state["nb_operateurs_val"] = nb_operateurs

            st.info(f"📅 Makespan calculé automatiquement : **{due_date} min**")

            jobs_en_retard = (job_cycle["Fin"] > due_date).sum()
            taux_retard    = round(jobs_en_retard / len(job_cycle) * 100, 1)

            st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("MAKESPAN",          f"{makespan} min")
            c2.metric("TAUX UTILISATION",  f"{taux_util_moyen} %")
            c3.metric("CYCLE MOYEN",       f"{cycle_moyen} min")
            c4.metric("TAUX RETARD",       f"{taux_retard} %")
            c5.metric("IDLE TIME",         f"{taux_idle} %")

            st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
            st.markdown("<p class='section-title'>🔍 Insights automatiques</p>",
                        unsafe_allow_html=True)

            if taux_util_moyen < 60:
                st.warning("⚠ Sous-utilisation globale des machines")
            if taux_util_moyen > 85:
                st.error("🚨 Risque de saturation des machines")
            if taux_retard > 20:
                st.warning("⚠ Taux de retard élevé → revoir ordonnancement")
            if taux_idle > 30:
                st.info("💡 Opportunité d'optimisation des ressources")

            st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
            st.markdown("<p class='section-title'>🧠 Recommandations</p>",
                        unsafe_allow_html=True)

            if taux_idle > 25:
                st.write("➡️ Réduire le nombre de machines ou regrouper les tâches")
            if taux_util_moyen < 50:
                st.write("➡️ Augmenter la charge ou revoir planification")
            if jobs_en_retard > 0:
                st.write("➡️ Prioriser les jobs critiques ou ajuster séquencement")

            score = max(0, min(100, round((taux_util_moyen - taux_idle - taux_retard), 1)))
            st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
            st.markdown("<p class='section-title'>Performance globale</p>",
                        unsafe_allow_html=True)
            st.metric("SCORE", f"{score}/100")

            st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
            st.markdown("<p class='section-title'>Utilisation par machine</p>",
                        unsafe_allow_html=True)
            df_util = pd.DataFrame({
                "Machine":        machine_util.index,
                "Charge (min)":   machine_util.values,
                "Taux util. (%)": (machine_util.values / makespan * 100).round(1),
                "Idle (min)":     makespan - machine_util.values,
            })
            st.dataframe(df_util, use_container_width=True, hide_index=True)

            st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
            st.markdown("<p class='section-title'>Temps de cycle par job</p>",
                        unsafe_allow_html=True)
            jcd = job_cycle.reset_index()[["JobLabel", "Debut", "Fin", "CycleTime"]]
            jcd.columns = ["Job", "Début", "Fin", "Cycle (min)"]
            jcd["En retard"] = jcd["Fin"].apply(lambda x: "⚠ OUI" if x > due_date else "✔ NON")
            st.dataframe(jcd, use_container_width=True, hide_index=True)

        with tab2:
            st.markdown("<p class='section-title'>Paramètres de coût</p>",
                        unsafe_allow_html=True)
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
                "cout_machine_h":   cout_machine_h,
                "cout_mo_h":        cout_mo_h,
                "cout_indirect_h":  cout_indirect_h,
                "prix_matiere_unit": prix_matiere_unit,
            }

            cout_machine_min  = cout_machine_h  / 60
            cout_mo_min       = cout_mo_h       / 60
            cout_indirect_min = cout_indirect_h / 60

            df_cout = df.groupby("JobLabel").agg(
                Nb_Ops=("OperationID", "count"), Duree_min=("Duration", "sum")
            ).reset_index()
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
            st.dataframe(df_cout, use_container_width=True, hide_index=True)

            st.markdown("<div class='sim-card'>", unsafe_allow_html=True)
            st.markdown("""
            <div class='sim-card-header'>
                <span class='sim-card-icon'>🎛️</span>
                <span class='sim-card-title'>Simulation — Nombre d'opérateurs</span>
                <span class='sim-card-badge'>READ ONLY · NE MODIFIE PAS LES COÛTS</span>
            </div>
            """, unsafe_allow_html=True)

            nb_op_default = int(st.session_state.get("nb_operateurs_val", 3))
            nb_op_sim = st.slider("Nombre d'opérateurs (simulation)", 1, 10, nb_op_default,
                                  key="nb_op_sim")

            cout_machine_total  = df_cout["Coût machine (€)"].sum()
            cout_indirect_total = df_cout["Coût indirect (€)"].sum()
            cout_matiere_total  = df_cout["Coût matière (€)"].sum()
            cout_mo_actuel      = df_cout["Coût MO (€)"].sum()
            cout_mo_simule = cout_mo_h * nb_op_sim * (makespan / 60)

            if "data_kpi" in st.session_state and "Revenu (€)" in st.session_state["data_kpi"].columns:
                revenu_total  = st.session_state["data_kpi"]["Revenu (€)"].sum()
                profit_actuel = revenu_total - cout_machine_total - cout_mo_actuel \
                                - cout_indirect_total - cout_matiere_total
                profit_simule = revenu_total - cout_machine_total - cout_mo_simule \
                                - cout_indirect_total - cout_matiere_total
                delta_profit  = profit_simule - profit_actuel
                delta_class = "positive" if delta_profit > 0 else "negative" if delta_profit < 0 else "neutral"
                delta_icon  = "▲" if delta_profit > 0 else "▼" if delta_profit < 0 else "▶"

                st.markdown(f"""
                <div class='sim-result-row'>
                    <span class='sim-result-label'>💰 Coût MO simulé</span>
                    <span class='sim-result-value neutral'>{cout_mo_simule:,.2f} €</span>
                </div>
                <div class='sim-result-row'>
                    <span class='sim-result-label'>📈 Profit simulé</span>
                    <span class='sim-result-value {"positive" if profit_simule >= 0 else "negative"}'>{profit_simule:,.2f} €</span>
                </div>
                <div class='sim-result-row'>
                    <span class='sim-result-label'>{delta_icon} Variation du profit</span>
                    <span class='sim-result-value {delta_class}'>{delta_profit:+,.2f} €</span>
                </div>
                """, unsafe_allow_html=True)

                st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
                if delta_profit < 0:
                    st.warning("⚠ Augmentation du nombre d'opérateurs réduit la marge")
                elif delta_profit > 0:
                    st.success("✅ Augmentation du nombre d'opérateurs améliore la marge")
                else:
                    st.info("ℹ Pas de changement par rapport à la situation actuelle")
            else:
                st.markdown(f"""
                <div class='sim-result-row'>
                    <span class='sim-result-label'>💰 Coût MO simulé</span>
                    <span class='sim-result-value neutral'>{cout_mo_simule:,.2f} €</span>
                </div>
                """, unsafe_allow_html=True)
                st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
                st.info("ℹ️ Calculez d'abord le Profit & Marge (onglet 3) pour voir l'impact sur le profit.")

            st.markdown("</div>", unsafe_allow_html=True)

        with tab3:
            st.markdown("<p class='section-title'>Prix de vente par job</p>",
                        unsafe_allow_html=True)
            job_ids    = sorted(df["JobID"].unique())
            cols_prix  = st.columns(min(len(job_ids), 5))
            prix_vente = {}
            for i, jid in enumerate(job_ids):
                with cols_prix[i % 5]:
                    saved_val = prix_saved.get(jid, prix_saved.get(str(jid), 10.0))
                    prix_vente[jid] = st.number_input(
                        f"JOB {jid} (€/U)", min_value=0.0,
                        value=float(saved_val),
                        step=1.0, key=f"pv_{jid}"
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
                        ) + params["prix_matiere_unit"], 2
                    )
                    st.session_state["df_cout"] = df_fallback
                    df_profit = pd.merge(df_profit,
                        df_fallback[["JobLabel", "Qté", "Coût total (€)"]],
                        on="JobLabel", how="left")
                    st.warning("⚠ Coûts calculés avec les paramètres par défaut.")

                df_profit["Prix vente (€/u)"] = df_profit["JobID"].map(prix_vente).fillna(0)
                df_profit["Revenu (€)"]  = round(df_profit["Qté"] * df_profit["Prix vente (€/u)"], 2)
                df_profit["Profit (€)"]  = round(df_profit["Revenu (€)"] - df_profit["Coût total (€)"], 2)
                df_profit["Marge (%)"]   = round(
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
                    df_profit[["JobLabel", "Qté", "Revenu (€)", "Coût total (€)",
                               "Profit (€)", "Marge (%)"]].style.applymap(
                        color_marge, subset=["Marge (%)"]),
                    use_container_width=True, hide_index=True)

                jobs_deficit = df_profit[df_profit["Profit (€)"] < 0]
                if not jobs_deficit.empty:
                    st.warning(f"⚠ {len(jobs_deficit)} job(s) déficitaire(s) : "
                               f"{', '.join(jobs_deficit['JobLabel'].tolist())}")
                else:
                    st.success("✔ Tous les jobs sont rentables")

        with tab4:
            import plotly.graph_objects as go

            st.markdown("<p class='section-title'>Visualisation des KPIs</p>",
                        unsafe_allow_html=True)

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
                " &nbsp;<span style='font-family:Share Tech Mono,monospace;font-weight:400;"
                "font-size:10px;color:#8b949e;text-transform:none;letter-spacing:0'>"
                "🟢 ≥75% · 🔵 50-75% · 🟠 25-50% · 🔴 &lt;25%"
                "</span></p>", unsafe_allow_html=True)

            fig_util = go.Figure()
            fig_util.add_trace(go.Bar(
                name="Utilisation (%)",
                x=machine_util.index.tolist(), y=taux_par_machine,
                marker_color=colors_util, marker_line=dict(width=0),
                text=[f"{v}%" for v in taux_par_machine],
                textposition="inside",
                textfont=dict(color="#ffffff", size=11, family="Share Tech Mono")
            ))
            fig_util.add_trace(go.Bar(
                name="Idle (%)",
                x=machine_util.index.tolist(), y=idle_par_machine,
                marker_color="rgba(48,54,61,0.6)", marker_line=dict(width=0),
                text=[f"{v}%" for v in idle_par_machine],
                textposition="inside",
                textfont=dict(color="#8b949e", size=10)
            ))
            fig_util.add_hline(y=75, line_dash="dot", line_color="#3fb950", line_width=1.2,
                annotation_text="Seuil 75%",
                annotation_font_color="#3fb950", annotation_font_size=10)
            fig_util.update_layout(**chart_layout(
                barmode="stack", height=320,
                legend=dict(orientation="h", y=1.1,
                            font=dict(color="#c9d1d9", size=11)),
                yaxis=dict(range=[0, 110], title="% Makespan",
                           gridcolor="#21262d", color="#8b949e"),
                xaxis=dict(gridcolor="#21262d", color="#8b949e")
            ))
            st.plotly_chart(fig_util, use_container_width=True)

            col_g1, col_g2 = st.columns(2)

            with col_g1:
                st.markdown("<p class='section-title'>Utilisation globale</p>",
                            unsafe_allow_html=True)
                fig_pie = go.Figure(go.Pie(
                    labels=["Temps productif", "Temps idle"],
                    values=[duree_totale, idle_total],
                    hole=0.58,
                    marker=dict(
                        colors=["#ff6b00", "rgba(48,54,61,0.5)"],
                        line=dict(color="#161b22", width=3)
                    ),
                    textinfo="label+percent",
                    textfont=dict(size=11, color="#c9d1d9", family="Share Tech Mono"),
                ))
                center_color = ("#3fb950" if taux_util_moyen >= 75
                                else "#ff6b00" if taux_util_moyen >= 50 else "#f59e0b")
                fig_pie.add_annotation(
                    text=f"<b>{taux_util_moyen}%</b>", x=0.5, y=0.5,
                    font=dict(size=22, color=center_color, family="Rajdhani"),
                    showarrow=False
                )
                fig_pie.update_layout(**chart_layout(height=300, showlegend=False))
                st.plotly_chart(fig_pie, use_container_width=True)

            with col_g2:
                st.markdown("<p class='section-title'>Temps de cycle par job</p>",
                            unsafe_allow_html=True)
                cycle_mean   = job_cycle["CycleTime"].mean()
                colors_cycle = [
                    "#58a6ff" if v <= cycle_mean else "#f59e0b"
                    for v in job_cycle["CycleTime"]
                ]
                fig_cycle = go.Figure()
                fig_cycle.add_trace(go.Bar(
                    x=job_cycle.index.tolist(), y=job_cycle["CycleTime"].tolist(),
                    marker_color=colors_cycle, marker_line=dict(width=0),
                    text=[f"{v} min" for v in job_cycle["CycleTime"].tolist()],
                    textposition="outside",
                    textfont=dict(color="#c9d1d9", size=10, family="Share Tech Mono")
                ))
                fig_cycle.add_hline(
                    y=cycle_mean, line_dash="dash",
                    line_color="#f59e0b", line_width=1.5,
                    annotation_text=f"Moy : {cycle_mean:.0f} min",
                    annotation_font_color="#f59e0b", annotation_font_size=10
                )
                fig_cycle.update_layout(**chart_layout(
                    height=300,
                    yaxis=dict(title="Minutes", gridcolor="#21262d", color="#8b949e"),
                    xaxis=dict(gridcolor="#21262d", color="#8b949e")
                ))
                st.plotly_chart(fig_cycle, use_container_width=True)

            if "data_kpi" in st.session_state:
                df_kpi = st.session_state["data_kpi"]

                if "Revenu (€)" in df_kpi.columns:
                    st.markdown(
                        "<p class='section-title' style='margin-top:8px'>Profit & Marge par job</p>",
                        unsafe_allow_html=True)

                    col_g3, col_g4 = st.columns(2)

                    with col_g3:
                        colors_profit = [
                            "#3fb950" if v >= 0 else "#f85149"
                            for v in df_kpi["Profit (€)"]
                        ]
                        fig_profit = go.Figure()
                        fig_profit.add_trace(go.Bar(
                            x=df_kpi["JobLabel"].tolist(), y=df_kpi["Profit (€)"].tolist(),
                            marker_color=colors_profit, marker_line=dict(width=0),
                            text=[f"{v:.1f}€" for v in df_kpi["Profit (€)"]],
                            textposition="outside",
                            textfont=dict(size=10, color="#c9d1d9", family="Share Tech Mono")
                        ))
                        fig_profit.add_hline(y=0, line_color="#30363d", line_width=1.2)
                        fig_profit.update_layout(**chart_layout(
                            height=300,
                            title=dict(text="Profit (€) par job",
                                       font=dict(color="#ff6b00", size=12,
                                                 family="Rajdhani"), x=0.01),
                            yaxis=dict(title="Profit (€)", gridcolor="#21262d", color="#8b949e"),
                            xaxis=dict(gridcolor="#21262d", color="#8b949e")
                        ))
                        st.plotly_chart(fig_profit, use_container_width=True)

                    with col_g4:
                        colors_marge = [
                            "#3fb950" if v >= 20 else "#f59e0b" if v >= 0 else "#f85149"
                            for v in df_kpi["Marge (%)"]
                        ]
                        fig_marge = go.Figure()
                        fig_marge.add_trace(go.Bar(
                            x=df_kpi["JobLabel"].tolist(), y=df_kpi["Marge (%)"].tolist(),
                            marker_color=colors_marge, marker_line=dict(width=0),
                            text=[f"{v:.1f}%" for v in df_kpi["Marge (%)"]],
                            textposition="outside",
                            textfont=dict(size=10, color="#c9d1d9", family="Share Tech Mono")
                        ))
                        max_marge = df_kpi["Marge (%)"].max()
                        fig_marge.add_hrect(
                            y0=20, y1=max(max_marge * 1.3, 25),
                            fillcolor="rgba(63,185,80,0.06)", line_width=0)
                        fig_marge.add_hline(y=20, line_dash="dash",
                            line_color="#3fb950", line_width=1.2,
                            annotation_text="Seuil 20%",
                            annotation_font_color="#3fb950", annotation_font_size=10)
                        fig_marge.add_hline(y=0, line_color="#30363d", line_width=1)
                        fig_marge.update_layout(**chart_layout(
                            height=300,
                            title=dict(text="Marge (%) par job",
                                       font=dict(color="#ff6b00", size=12,
                                                 family="Rajdhani"), x=0.01),
                            yaxis=dict(title="Marge (%)", gridcolor="#21262d", color="#8b949e"),
                            xaxis=dict(gridcolor="#21262d", color="#8b949e")
                        ))
                        st.plotly_chart(fig_marge, use_container_width=True)

                if "df_cout" in st.session_state:
                    st.markdown(
                        "<p class='section-title' style='margin-top:8px'>Décomposition des coûts par job</p>",
                        unsafe_allow_html=True)
                    dc = st.session_state["df_cout"]
                    fig_cout = go.Figure()
                    cost_items = [
                        ("Coût machine (€)",  "#58a6ff"),
                        ("Coût MO (€)",       "#8b49ff"),
                        ("Coût indirect (€)", "#f59e0b"),
                        ("Coût matière (€)",  "#f0883e"),
                    ]
                    for col_name, col_color in cost_items:
                        if col_name in dc.columns:
                            fig_cout.add_trace(go.Bar(
                                name=col_name.replace(" (€)", ""),
                                x=dc["JobLabel"].tolist(),
                                y=dc[col_name].tolist(),
                                marker_color=col_color,
                                marker_line=dict(width=0),
                            ))
                    fig_cout.update_layout(**chart_layout(
                        barmode="stack", height=320,
                        legend=dict(orientation="h", y=1.1,
                                    font=dict(color="#c9d1d9", size=11)),
                        yaxis=dict(title="Coût (€)", gridcolor="#21262d", color="#8b949e"),
                        xaxis=dict(gridcolor="#21262d", color="#8b949e")
                    ))
                    st.plotly_chart(fig_cout, use_container_width=True)
            else:
                st.info("⚠ Calculez d'abord le Profit & Marge dans l'onglet correspondant")

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 4 — DOWNLOAD
# ══════════════════════════════════════════════════════════════════════════════
elif menu == "⬇️ Download":
    st.markdown("""
    <div class='page-header-bar'>
        <p class='page-title'>⬇ DOWNLOAD</p>
        <p class='page-subtitle'>Exportez vos résultats en CSV, Excel ou Gantt interactif HTML.</p>
    </div>""", unsafe_allow_html=True)

    if "data_kpi" not in st.session_state:
        st.info("⚠ Calculez d'abord les KPIs (onglet Profit & Marge)")
    else:
        df_kpi  = st.session_state["data_kpi"]
        df_ops  = st.session_state.get("data")
        df_jobs = st.session_state.get("df_jobs")

        c1, c2, c3 = st.columns(3, gap="large")

        with c1:
            st.markdown("""<div class='dl-card'>
                <span class='dl-icon'>📄</span>
                <span class='dl-label'>Export CSV — KPIs</span>
            </div>""", unsafe_allow_html=True)
            st.download_button("⬇ TÉLÉCHARGER CSV", to_csv_bytes(df_kpi),
                               "kpi_data.csv", "text/csv", use_container_width=True)

        with c2:
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine="openpyxl") as w:
                df_kpi.to_excel(w, sheet_name="KPIs", index=False)
                if "JobLabel" in df_kpi.columns and "Duree_min" in df_kpi.columns:
                    try:
                        summary_by_job(df_kpi).to_excel(w, sheet_name="Par Job", index=False)
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
            st.download_button("⬇ TÉLÉCHARGER EXCEL", buf.getvalue(), "rapport.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True)

        with c3:
            if df_ops is not None:
                import plotly.io as pio
                fig        = build_gantt(df_ops, df_jobs)
                gantt_html = pio.to_html(fig, full_html=True, include_plotlyjs="cdn")
                st.markdown("""<div class='dl-card'>
                    <span class='dl-icon'>📅</span>
                    <span class='dl-label'>Gantt HTML interactif</span>
                </div>""", unsafe_allow_html=True)
                st.download_button("⬇ TÉLÉCHARGER GANTT", gantt_html.encode("utf-8"),
                                   "gantt.html", "text/html", use_container_width=True)
            else:
                st.info("⚠ Chargez d'abord vos données pour exporter le Gantt")