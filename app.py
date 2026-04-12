import streamlit as st
import pandas as pd
import io
import uuid
from datetime import datetime, date
import extra_streamlit_components as stx

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

# ── Authentification avec cookie ───────────────────────────────────────────
USERS = {
    "ichrak": "motdepasse123",
    "user2":  "motdepasse456"
}

cookie_manager = stx.CookieManager()

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
if "SID" not in st.session_state:
    st.session_state["SID"] = None

sid_cookie = cookie_manager.get("gantt_user")
if sid_cookie and sid_cookie in USERS and not st.session_state["authenticated"]:
    st.session_state["authenticated"] = True
    st.session_state["SID"] = sid_cookie

if not st.session_state["authenticated"]:
    st.markdown("### 🔐 Connexion")
    username_input = st.text_input("Identifiant", key="username")
    password_input = st.text_input("Mot de passe", type="password", key="password")
    if st.button("Se connecter", key="login_btn"):
        u = username_input.strip().lower()
        p = password_input.strip()
        if u in USERS and USERS[u] == p:
            cookie_manager.set("gantt_user", u)
            st.session_state["authenticated"] = True
            st.session_state["SID"] = u
            st.rerun()
        else:
            st.error("❌ Identifiant ou mot de passe incorrect")
            st.stop()
    else:
        st.stop()

SID = st.session_state["SID"]

if st.sidebar.button("🚪 Se déconnecter"):
    cookie_manager.delete("gantt_user")
    st.session_state["authenticated"] = False
    st.session_state["SID"] = None
    st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# CSS — THÈME INDUSTRIEL
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@400;600;700&family=Share+Tech+Mono:wght@400&display=swap');
html, body,
[data-testid="stAppViewContainer"],
[data-testid="stAppViewContainer"] > div:first-child,
[data-testid="stHeader"], [data-testid="stMain"],
.main, .block-container {
    background-color: #0d1117 !important; color: #c9d1d9 !important; color-scheme: dark !important;
}
@media (prefers-color-scheme: light) {
    html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
        background-color: #0d1117 !important; color: #c9d1d9 !important;
    }
}
[data-testid="stSidebar"] { background-color: #161b22 !important; border-right: 2px solid #ff6b00 !important; }
[data-testid="stSidebar"] * { font-family: 'Rajdhani', sans-serif !important; color: #8b949e !important; }
[data-testid="stSidebar"] .stRadio label {
    font-size: 13px !important; font-weight: 600 !important; letter-spacing: 1.5px !important;
    text-transform: uppercase !important; color: #8b949e !important; padding: 10px 4px !important; transition: color 0.15s !important;
}
[data-testid="stSidebar"] .stRadio label:hover { color: #ff6b00 !important; }
*, p, div, span, li, .stMarkdown p, [data-testid="stMarkdownContainer"] p {
    font-family: 'Share Tech Mono', monospace !important; color: #c9d1d9 !important;
    font-size: 13px !important; line-height: 1.6 !important; letter-spacing: 0.3px !important;
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
    font-family: 'Share Tech Mono', monospace !important; font-size: 0.8rem !important;
    color: #8b949e !important; text-align: right; line-height: 1.9;
}
.divline { height: 1px; background: linear-gradient(90deg, transparent, #ff6b0066, transparent); margin: 0 0 20px 0; border: none; }
.page-header-bar { background: #161b22; border: 1px solid #30363d; border-left: 3px solid #ff6b00; border-radius: 4px; padding: 14px 20px; margin-bottom: 20px; }
.page-title { font-family: 'Rajdhani', sans-serif !important; font-size: 1.1rem !important; font-weight: 700 !important; color: #ff6b00 !important; letter-spacing: 3px !important; text-transform: uppercase !important; margin: 0 0 4px 0 !important; }
.page-subtitle { font-family: 'Share Tech Mono', monospace !important; font-size: 0.72rem !important; color: #8b949e !important; margin: 0 !important; letter-spacing: 0.5px !important; }
.section-title { font-family: 'Rajdhani', sans-serif !important; font-size: 0.72rem !important; font-weight: 700 !important; color: #ff6b00 !important; letter-spacing: 3px !important; text-transform: uppercase !important; margin-bottom: 10px; padding-bottom: 8px; border-bottom: 1px solid #30363d; }
[data-testid="stMetric"] { background: #161b22 !important; border: 1px solid #30363d !important; border-top: 3px solid #ff6b00 !important; border-radius: 4px !important; padding: 14px 16px !important; }
[data-testid="stMetricValue"] { font-family: 'Rajdhani', sans-serif !important; color: #ff6b00 !important; font-size: 1.6rem !important; font-weight: 700 !important; }
[data-testid="stMetricLabel"] { font-family: 'Share Tech Mono', monospace !important; color: #8b949e !important; font-size: 0.62rem !important; letter-spacing: 2px !important; text-transform: uppercase !important; }
.stButton > button { background: transparent !important; border: 1px solid #ff6b00 !important; color: #ff6b00 !important; font-family: 'Rajdhani', sans-serif !important; font-weight: 700 !important; font-size: 13px !important; letter-spacing: 2px !important; text-transform: uppercase !important; border-radius: 2px !important; padding: 8px 22px !important; transition: all 0.15s ease !important; }
.stButton > button:hover { background: #ff6b00 !important; color: #0d1117 !important; }
.stDownloadButton > button { background: transparent !important; border: 1px solid #30363d !important; color: #c9d1d9 !important; font-family: 'Rajdhani', sans-serif !important; font-size: 13px !important; font-weight: 600 !important; letter-spacing: 1.5px !important; text-transform: uppercase !important; border-radius: 2px !important; width: 100% !important; transition: all 0.15s ease !important; }
.stDownloadButton > button:hover { border-color: #ff6b00 !important; color: #ff6b00 !important; }
.stNumberInput > div > div > input, .stTextInput > div > div > input { background-color: #0d1117 !important; border: 1px solid #30363d !important; color: #c9d1d9 !important; font-family: 'Share Tech Mono', monospace !important; font-size: 13px !important; border-radius: 2px !important; }
.stNumberInput > div > div > input:focus { border-color: #ff6b00 !important; box-shadow: 0 0 0 1px #ff6b0044 !important; }
[data-testid="stSelectbox"] > div > div { background: #161b22 !important; border: 1px solid #30363d !important; color: #c9d1d9 !important; font-family: 'Share Tech Mono', monospace !important; border-radius: 2px !important; }
[data-testid="stFileUploader"] { background: #161b22 !important; border: 1px dashed #30363d !important; border-radius: 4px !important; }
[data-testid="stFileUploader"]:hover { border-color: #ff6b00 !important; }
.stTabs [data-baseweb="tab-list"] { background: #161b22 !important; border: 1px solid #30363d !important; border-radius: 2px !important; padding: 4px !important; gap: 2px !important; }
.stTabs [data-baseweb="tab"] { background: transparent !important; border-radius: 2px !important; color: #8b949e !important; font-family: 'Rajdhani', sans-serif !important; font-weight: 600 !important; font-size: 12px !important; letter-spacing: 2px !important; text-transform: uppercase !important; padding: 7px 16px !important; border: 1px solid transparent !important; transition: all 0.15s !important; }
.stTabs [aria-selected="true"] { background: #ff6b0012 !important; color: #ff6b00 !important; border-color: #ff6b00 !important; }
.stTabs [data-baseweb="tab-panel"] { background: #161b22 !important; border: 1px solid #30363d !important; border-top: none !important; border-radius: 0 0 4px 4px !important; padding: 20px !important; }
[data-testid="stDataFrame"] { border: 1px solid #30363d !important; border-radius: 4px !important; overflow: hidden !important; background: #161b22 !important; }
[data-testid="stAlert"] { background: #161b22 !important; border-radius: 2px !important; border-left-width: 3px !important; }
[data-testid="stAlert"] p { color: #c9d1d9 !important; font-size: 12px !important; }
.status-badge { background: #0f2a1a; border: 1px solid #238636; border-radius: 2px; padding: 5px 10px; font-family: 'Share Tech Mono', monospace !important; font-size: 11px !important; color: #3fb950 !important; margin: 4px 0; display: block; letter-spacing: 0.5px; }
.status-badge-teal { background: #0d1b2a; border: 1px solid #1f6feb; color: #58a6ff !important; }
.dl-card { background: #161b22; border: 1px solid #30363d; border-radius: 4px; padding: 28px 20px 20px; text-align: center; height: 150px; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 10px; }
.dl-icon { font-size: 26px; }
.dl-label { font-family: 'Rajdhani', sans-serif !important; font-size: 12px !important; font-weight: 700 !important; color: #8b949e !important; letter-spacing: 2px; text-transform: uppercase; }
label { font-family: 'Rajdhani', sans-serif !important; font-size: 12px !important; font-weight: 600 !important; color: #8b949e !important; letter-spacing: 1px !important; text-transform: uppercase !important; }
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: #0d1117; }
::-webkit-scrollbar-thumb { background: #30363d; border-radius: 2px; }
::-webkit-scrollbar-thumb:hover { background: #ff6b00; }
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
    "📋 Historique",
    "⬇️ Download"
])

st.sidebar.markdown("<hr style='border-color:#30363d;margin:16px 0'>", unsafe_allow_html=True)

# ── Statuts en sidebar ─────────────────────────────────────────────────────────
st.sidebar.markdown("<div style='margin-top:4px'>", unsafe_allow_html=True)
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

# ── Clôture de journée ─────────────────────────────────────────────────────────
if "data" in st.session_state:
    st.sidebar.markdown("""
    <p style='font-family:Rajdhani,sans-serif;font-size:0.6rem;font-weight:700;
       color:rgba(255,255,255,0.25);letter-spacing:2px;text-transform:uppercase;
       margin-bottom:6px'>📅 PLANIFICATION MULTI-JOURS</p>""", unsafe_allow_html=True)
    jour_cloture = st.sidebar.date_input("Date du planning", value=date.today(),
                                          key="jour_cloture_date")
    if st.sidebar.button("💾 CLÔTURER CE JOUR", key="cloture_btn"):
        try:
            from backend.database import save_planning_jour
            ok, msg = save_planning_jour(
                SID, jour_cloture,
                st.session_state["data"],
                st.session_state.get("df_jobs", pd.DataFrame())
            )
            if ok:
                st.sidebar.success(f"✔ Jour {jour_cloture} sauvegardé")
            else:
                st.sidebar.error(f"❌ {msg}")
        except Exception as ex:
            st.sidebar.error(f"❌ {ex}")

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
    "📋 Historique":    "Historique",
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
        paper_bgcolor="#161b22", plot_bgcolor="#0d1117",
        font=dict(color="#c9d1d9", family="Share Tech Mono", size=11),
        margin=dict(l=10, r=10, t=30, b=10),
        yaxis=dict(gridcolor="#21262d"), xaxis=dict(gridcolor="#21262d"),
    )
    base.update(kwargs)
    return base

# ── Helper label Pièce ─────────────────────────────────────────────────────────
def piece_label(job_id):
    return f"Pièce {job_id}"

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 1 — UPLOAD
# ══════════════════════════════════════════════════════════════════════════════
if menu == "📂 Upload Data":
    st.markdown("""
    <div class='page-header-bar'>
        <p class='page-title'>⬆ UPLOAD DATA</p>
        <p class='page-subtitle'>Importez les fichiers de planification machine et de mapping pièces.
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
        st.markdown("<p class='section-title'>◈ Fichier Pièces (opts.txt)</p>",
                    unsafe_allow_html=True)
        opts_file = st.file_uploader("opts.txt — mapping opération → pièce",
                                     type=["txt"], key="opts")
        if opts_file:
            content = opts_file.read().decode("utf-8")
            df_jobs = load_jobs_from_txt(content)
            st.session_state["df_jobs"] = df_jobs
            ok_db, msg_db = save_jobs(df_jobs, SID)
            if not ok_db:
                st.error(f"❌ Erreur DB : {msg_db}")
            else:
                st.success(f"✔ {df_jobs['JobID'].nunique()} pièces · {len(df_jobs)} opérations sauvegardées")
            st.dataframe(df_jobs, use_container_width=True)
        elif "df_jobs" in st.session_state:
            st.markdown("<span class='status-badge status-badge-teal'>⬡ PIÈCES EN MÉMOIRE</span>",
                        unsafe_allow_html=True)
            st.dataframe(st.session_state["df_jobs"], use_container_width=True)

    # ── Section OR-Tools ───────────────────────────────────────────────────────
    st.markdown("<hr style='border-color:#30363d;margin:28px 0'>", unsafe_allow_html=True)
    st.markdown("""
    <div class='page-header-bar'>
        <p class='page-title'>⚙ OPTIMISATION OR-TOOLS</p>
        <p class='page-subtitle'>Uploadez votre fichier Excel (template) ou lancez avec les données de test intégrées.</p>
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
        run_solver = st.button("▶ LANCER", key="run_solver_btn")

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
        except Exception as e:
            st.error(f"❌ Impossible de lire le fichier : {e}")
    else:
        st.markdown("""
        <p style='color:#8b949e;font-size:12px;font-family:Share Tech Mono,monospace'>
        ▸ Sans fichier uploadé, le solveur utilise les <b style='color:#ff6b00'>données de test intégrées</b>
        (13 pièces · 15 machines · 30 opérations · 6 techniciens · cte=15 min).
        </p>""", unsafe_allow_html=True)

    if run_solver:
        from backend.solver.input_parser import (parse_excel_to_dict,
                                                  validate_excel_data,
                                                  DATA as DEFAULT_DATA)
        from backend.solver.model import solve_flexible_jobshop

        if "excel_data_cache" in st.session_state:
            try:
                solver_data = parse_excel_to_dict(io.BytesIO(st.session_state["excel_data_cache"]))
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

        with st.spinner("⚙ Résolution en cours — cela peut prendre jusqu'à 10 minutes..."):
            try:
                df_result = solve_flexible_jobshop(solver_data)

                gammes_map = {g[0]: g[1] for g in solver_data["gammes"]}
                df_result["JobID"]    = df_result["OperationID"].map(gammes_map).fillna(0).astype(int)
                df_result["JobLabel"] = df_result["JobID"].apply(piece_label)

                st.session_state["data"] = df_result
                save_operations(df_result, SID)

                rows_jobs    = [{"OperationID": g[0], "JobID": g[1]} for g in solver_data["gammes"]]
                df_jobs_auto = pd.DataFrame(rows_jobs)
                st.session_state["df_jobs"] = df_jobs_auto
                save_jobs(df_jobs_auto, SID)
                st.session_state.pop("excel_data_cache", None)

                makespan  = int(df_result["EndTime"].max())
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
elif menu == "📅 Gantt Diagram":
    st.markdown("""
    <div class='page-header-bar'>
        <p class='page-title'>◈ GANTT DIAGRAM</p>
        <p class='page-subtitle'>Visualisation de l'ordonnancement des opérations sur les machines.</p>
    </div>""", unsafe_allow_html=True)

    if "data" not in st.session_state:
        st.info("⚠ Chargez d'abord vos données dans Upload Data")
    else:
        df_ops  = st.session_state["data"].copy()
        df_jobs = st.session_state.get("df_jobs", None)

        if "JobID" not in df_ops.columns:
            if df_jobs is not None and not df_jobs.empty:
                df_ops = pd.merge(df_ops, df_jobs[["OperationID", "JobID"]],
                                  on="OperationID", how="left")
            df_ops["JobID"] = df_ops.get("JobID", 0)
        df_ops["JobID"]    = df_ops["JobID"].fillna(0).astype(int)
        df_ops["JobLabel"] = df_ops["JobID"].apply(piece_label)

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

        # ── TAB 1 ─────────────────────────────────────────────────────────────
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
            if taux_idle > 25:      st.write("➡️ Réduire le nombre de machines ou regrouper les tâches")
            if taux_util_moyen < 50: st.write("➡️ Augmenter la charge ou revoir planification")
            if jobs_en_retard > 0:  st.write("➡️ Prioriser les pièces critiques ou ajuster séquencement")

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

        # ── TAB 2 — COÛTS (sans simulation opérateurs) ───────────────────────
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
                          "Coût MO (€)", "Coût indirect (€)", "Coût matière (€)", "Coût total (€)"]],
                use_container_width=True, hide_index=True)

        # ── TAB 3 — PROFIT & MARGE ────────────────────────────────────────────
        with tab3:
            st.markdown("<p class='section-title'>Prix de vente par pièce</p>", unsafe_allow_html=True)
            job_ids   = sorted(df["JobID"].unique())
            cols_prix = st.columns(min(len(job_ids), 5))
            prix_vente = {}
            for i, jid in enumerate(job_ids):
                with cols_prix[i % 5]:
                    saved_val = prix_saved.get(jid, prix_saved.get(str(jid), 10.0))
                    prix_vente[jid] = st.number_input(
                        f"PIÈCE {jid} (€/U)", min_value=0.0,
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

                df_profit["Pièce"]           = df_profit["JobLabel"]
                df_profit["Prix vente (€/u)"] = df_profit["JobID"].map(prix_vente).fillna(0)
                df_profit["Revenu (€)"]       = round(df_profit["Qté"] * df_profit["Prix vente (€/u)"], 2)
                df_profit["Profit (€)"]       = round(df_profit["Revenu (€)"] - df_profit["Coût total (€)"], 2)
                df_profit["Marge (%)"]        = round(
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

        # ── TAB 4 — VISUALISATION ─────────────────────────────────────────────
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
                " &nbsp;<span style='font-family:Share Tech Mono,monospace;font-weight:400;"
                "font-size:10px;color:#8b949e;text-transform:none;letter-spacing:0'>"
                "🟢 ≥75% · 🔵 50-75% · 🟠 25-50% · 🔴 &lt;25%"
                "</span></p>", unsafe_allow_html=True)

            fig_util = go.Figure()
            fig_util.add_trace(go.Bar(
                name="Utilisation (%)", x=machine_util.index.tolist(), y=taux_par_machine,
                marker_color=colors_util, marker_line=dict(width=0),
                text=[f"{v}%" for v in taux_par_machine], textposition="inside",
                textfont=dict(color="#ffffff", size=11, family="Share Tech Mono")
            ))
            fig_util.add_trace(go.Bar(
                name="Idle (%)", x=machine_util.index.tolist(), y=idle_par_machine,
                marker_color="rgba(48,54,61,0.6)", marker_line=dict(width=0),
                text=[f"{v}%" for v in idle_par_machine], textposition="inside",
                textfont=dict(color="#8b949e", size=10)
            ))
            fig_util.add_hline(y=75, line_dash="dot", line_color="#3fb950", line_width=1.2,
                annotation_text="Seuil 75%",
                annotation_font_color="#3fb950", annotation_font_size=10)
            fig_util.update_layout(**chart_layout(
                barmode="stack", height=320,
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
                    textfont=dict(size=11, color="#c9d1d9", family="Share Tech Mono"),
                ))
                center_color = ("#3fb950" if taux_util_moyen >= 75
                                else "#ff6b00" if taux_util_moyen >= 50 else "#f59e0b")
                fig_pie.add_annotation(
                    text=f"<b>{taux_util_moyen}%</b>", x=0.5, y=0.5,
                    font=dict(size=22, color=center_color, family="Rajdhani"), showarrow=False)
                fig_pie.update_layout(**chart_layout(height=300, showlegend=False))
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
                    textfont=dict(color="#c9d1d9", size=10, family="Share Tech Mono")
                ))
                fig_cycle.add_hline(y=cycle_mean, line_dash="dash", line_color="#f59e0b", line_width=1.5,
                    annotation_text=f"Moy : {cycle_mean:.0f} min",
                    annotation_font_color="#f59e0b", annotation_font_size=10)
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
                        "<p class='section-title' style='margin-top:8px'>Profit & Marge par pièce</p>",
                        unsafe_allow_html=True)
                    col_g3, col_g4 = st.columns(2)
                    piece_labels_list = df_kpi.get("Pièce", df_kpi["JobLabel"]).tolist()

                    with col_g3:
                        colors_profit = ["#3fb950" if v >= 0 else "#f85149"
                                         for v in df_kpi["Profit (€)"]]
                        fig_profit = go.Figure()
                        fig_profit.add_trace(go.Bar(
                            x=piece_labels_list, y=df_kpi["Profit (€)"].tolist(),
                            marker_color=colors_profit, marker_line=dict(width=0),
                            text=[f"{v:.1f}€" for v in df_kpi["Profit (€)"]],
                            textposition="outside",
                            textfont=dict(size=10, color="#c9d1d9", family="Share Tech Mono")
                        ))
                        fig_profit.add_hline(y=0, line_color="#30363d", line_width=1.2)
                        fig_profit.update_layout(**chart_layout(
                            height=300,
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
                            textfont=dict(size=10, color="#c9d1d9", family="Share Tech Mono")
                        ))
                        max_marge = df_kpi["Marge (%)"].max()
                        fig_marge.add_hrect(y0=20, y1=max(max_marge * 1.3, 25),
                            fillcolor="rgba(63,185,80,0.06)", line_width=0)
                        fig_marge.add_hline(y=20, line_dash="dash", line_color="#3fb950", line_width=1.2,
                            annotation_text="Seuil 20%",
                            annotation_font_color="#3fb950", annotation_font_size=10)
                        fig_marge.add_hline(y=0, line_color="#30363d", line_width=1)
                        fig_marge.update_layout(**chart_layout(
                            height=300,
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
                    x_labels = dc.get("Pièce", dc["JobLabel"]).tolist() if "Pièce" in dc.columns else dc["JobLabel"].tolist()
                    for col_name, col_color in cost_items:
                        if col_name in dc.columns:
                            fig_cout.add_trace(go.Bar(
                                name=col_name.replace(" (€)", ""),
                                x=x_labels, y=dc[col_name].tolist(),
                                marker_color=col_color, marker_line=dict(width=0),
                            ))
                    fig_cout.update_layout(**chart_layout(
                        barmode="stack", height=320,
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
elif menu == "📋 Historique":
    st.markdown("""
    <div class='page-header-bar'>
        <p class='page-title'>📋 HISTORIQUE DES PLANIFICATIONS</p>
        <p class='page-subtitle'>Consultez et rechargez les plannings des jours précédents.</p>
    </div>""", unsafe_allow_html=True)

    try:
        from backend.database import load_planning_jours
        jours = load_planning_jours(SID)

        if not jours:
            st.info("⚠ Aucun planning sauvegardé. Utilisez '💾 CLÔTURER CE JOUR' dans la sidebar après avoir généré un planning.")
        else:
            st.markdown(f"<p class='section-title'>{len(jours)} JOUR(S) SAUVEGARDÉ(S)</p>",
                        unsafe_allow_html=True)

            for idx, jour_data in enumerate(sorted(jours, key=lambda x: x['jour'], reverse=True)):
                jour_str = str(jour_data['jour'])
                ops_list = jour_data.get('operations', [])
                nb_ops   = len(ops_list)

                with st.expander(f"📅 {jour_str} — {nb_ops} opérations", expanded=(idx == 0)):
                    col_info, col_actions = st.columns([4, 1])

                    with col_info:
                        if ops_list:
                            df_hist = pd.DataFrame(ops_list)
                            if "JobID" in df_hist.columns:
                                df_hist["Pièce"] = df_hist["JobID"].apply(piece_label)
                            nb_pieces  = df_hist["JobID"].nunique() if "JobID" in df_hist.columns else "—"
                            nb_mchs_h  = df_hist["MachineID"].nunique() if "MachineID" in df_hist.columns else "—"
                            makespan_h = int(df_hist["EndTime"].max()) if "EndTime" in df_hist.columns else "—"

                            m1, m2, m3 = st.columns(3)
                            m1.metric("PIÈCES",   nb_pieces)
                            m2.metric("MACHINES", nb_mchs_h)
                            m3.metric("MAKESPAN", f"{makespan_h} min")

                            cols_show = [c for c in
                                ["OperationID", "Pièce", "MachineLabel", "StartTime", "EndTime", "Duration"]
                                if c in df_hist.columns]
                            st.dataframe(df_hist[cols_show], use_container_width=True, hide_index=True)

                    with col_actions:
                        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
                        if st.button(f"🔄 Recharger", key=f"reload_{jour_str}"):
                            df_reload = pd.DataFrame(ops_list)
                            if "JobID" in df_reload.columns:
                                df_reload["JobID"]    = df_reload["JobID"].fillna(0).astype(int)
                                df_reload["JobLabel"] = df_reload["JobID"].apply(piece_label)
                            st.session_state["data"] = df_reload
                            save_operations(df_reload, SID)
                            jobs_list = jour_data.get('jobs', [])
                            if jobs_list:
                                df_jobs_r = pd.DataFrame(jobs_list)
                                st.session_state["df_jobs"] = df_jobs_r
                                save_jobs(df_jobs_r, SID)
                            st.success(f"✔ Planning du {jour_str} rechargé")
                            st.rerun()

                        if ops_list:
                            df_exp      = pd.DataFrame(ops_list)
                            df_jobs_exp = pd.DataFrame(jour_data.get('jobs', []))
                            if "JobID" in df_exp.columns:
                                df_exp["JobLabel"] = df_exp["JobID"].apply(piece_label)
                            try:
                                import plotly.io as pio
                                fig_h      = build_gantt(df_exp, df_jobs_exp if not df_jobs_exp.empty else None)
                                gantt_html = pio.to_html(fig_h, full_html=True, include_plotlyjs="cdn")
                                st.download_button(
                                    f"⬇ Gantt {jour_str}", gantt_html.encode("utf-8"),
                                    f"gantt_{jour_str}.html", "text/html",
                                    key=f"dl_{jour_str}"
                                )
                            except Exception:
                                pass

    except Exception as e:
        st.error(f"❌ Erreur chargement historique : {e}")
        st.info("Vérifiez que la table 'planning_jours' existe dans Supabase et que les policies RLS sont configurées.")

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 5 — DOWNLOAD
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
            st.download_button("⬇ TÉLÉCHARGER EXCEL", buf.getvalue(), "rapport.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True)

        with c3:
            if df_ops is not None:
                import plotly.io as pio
                df_ops_export = df_ops.copy()
                if "JobID" not in df_ops_export.columns and df_jobs is not None:
                    job_map = df_jobs.set_index("OperationID")["JobID"].to_dict()
                    df_ops_export["JobID"] = df_ops_export["OperationID"].map(job_map).fillna(0).astype(int)
                if "JobID" in df_ops_export.columns:
                    df_ops_export["JobLabel"] = df_ops_export["JobID"].apply(piece_label)
                fig        = build_gantt(df_ops_export, df_jobs)
                gantt_html = pio.to_html(fig, full_html=True, include_plotlyjs="cdn")
                st.markdown("""<div class='dl-card'>
                    <span class='dl-icon'>📅</span>
                    <span class='dl-label'>Gantt HTML interactif</span>
                </div>""", unsafe_allow_html=True)
                st.download_button("⬇ TÉLÉCHARGER GANTT", gantt_html.encode("utf-8"),
                                   "gantt.html", "text/html", use_container_width=True)
            else:
                st.info("⚠ Chargez d'abord vos données pour exporter le Gantt")