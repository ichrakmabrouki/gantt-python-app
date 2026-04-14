import pandas as pd
import plotly.graph_objects as go
import plotly.colors as pc
from datetime import datetime, timedelta

START_DAY = datetime.strptime("06:00", "%H:%M")

def minutes_to_time(minutes: int) -> str:
    t = START_DAY + timedelta(minutes=int(minutes))
    return t.strftime("%H:%M")

def build_gantt(df_ops: pd.DataFrame,
                df_jobs: pd.DataFrame = None,
                of_map: dict = None,
                piece_map: dict = None) -> go.Figure:
    df = df_ops.copy()

    # ── Fusion JobID seulement si absent ──────────────────────────────────────
    if "JobID" not in df.columns:
        if df_jobs is not None and not df_jobs.empty:
            df = pd.merge(df, df_jobs[["OperationID", "JobID"]],
                          on="OperationID", how="left")
        else:
            df["JobID"] = 0

    df["JobID"] = df["JobID"].fillna(0).astype(int)

    # ── Label pièce : utilise piece_map si dispo, sinon "Pièce X" ─────────────
    def make_piece_label(job_id: int) -> str:
        if piece_map and job_id in piece_map:
            return f"P{job_id} — {piece_map[job_id]}"
        return f"Pièce {job_id}"

    df["JobLabel"] = df["JobID"].apply(make_piece_label)

    # ── OF label pour hover ───────────────────────────────────────────────────
    def get_of(job_id: int) -> str:
        if of_map and job_id in of_map:
            return of_map[job_id]
        return ""

    # Types
    df["MachineID"]   = df["MachineID"].astype(str)
    df["OperationID"] = df["OperationID"].astype(str)
    df["StartTime"]   = df["StartTime"].astype(int)
    df["EndTime"]     = df["EndTime"].astype(int)
    df["Duration"]    = df["Duration"].astype(int)

    df["Start_str"] = df["StartTime"].apply(minutes_to_time)
    df["End_str"]   = df["EndTime"].apply(minutes_to_time)

    # ── Couleurs par pièce ────────────────────────────────────────────────────
    pieces    = df["JobLabel"].unique()
    colors    = pc.qualitative.Plotly
    color_map = {p: colors[i % len(colors)] for i, p in enumerate(pieces)}

    # ── Machines triées ───────────────────────────────────────────────────────
    machines = {
        m: df[df["MachineID"] == m].sort_values("StartTime")
        for m in sorted(df["MachineID"].unique(), key=lambda x: int(x))
    }

    fig = go.Figure()
    seen = set()

    for machine, ops in machines.items():
        for _, row in ops.iterrows():
            piece = row["JobLabel"]
            of    = get_of(int(row["JobID"]))
            show  = piece not in seen
            seen.add(piece)
            fig.add_trace(go.Bar(
                x=[row["Duration"]],
                y=[f"Machine {machine}"],
                base=row["StartTime"],
                name=piece,
                legendgroup=piece,
                showlegend=show,
                orientation="h",
                text=f'Op {row["OperationID"]}',
                textposition="inside",
                marker=dict(color=color_map[piece]),
                hovertemplate=(
                    f'<b>{piece}</b><br>'
                    + (f'OF : {of}<br>' if of else '')
                    + f'Opération : {row["OperationID"]}<br>'
                    f'Machine   : {machine}<br>'
                    f'Début     : {row["Start_str"]}<br>'
                    f'Fin       : {row["End_str"]}<br>'
                    f'Durée     : {row["Duration"]} min'
                    '<extra></extra>'
                )
            ))

    # ── Makespan — ligne rouge ────────────────────────────────────────────────
    makespan = df["EndTime"].max()
    fig.add_shape(type="line",
        x0=makespan, x1=makespan, y0=-0.5, y1=len(machines)-0.5,
        line=dict(color="#f85149", width=2.5, dash="dash"))
    fig.add_annotation(x=makespan, y=len(machines)-0.5,
        text=f"Makespan : {minutes_to_time(makespan)}",
        showarrow=True, arrowhead=2, ax=0, ay=-30,
        font=dict(color="#f85149", size=12))

    # ── Heure actuelle — ligne blanche pointillée ─────────────────────────────
    now = datetime.now()
    start_of_day    = datetime.combine(now.date(), START_DAY.time())
    current_minutes = (now - start_of_day).total_seconds() / 60
    current_minutes = max(0, min(current_minutes, 960))
    fig.add_shape(type="line",
        x0=current_minutes, x1=current_minutes,
        y0=-0.5, y1=len(machines)-0.5,
        line=dict(color="#ffffff", width=2, dash="dot"))
    fig.add_annotation(x=current_minutes, y=0,
        text=f"Maintenant : {minutes_to_time(current_minutes)}",
        showarrow=True, arrowhead=2, ax=0, ay=-40,
        font=dict(color="#ffffff", size=11))

    # ── Axe X en heures ──────────────────────────────────────────────────────
    fig.update_xaxes(
        tickvals=list(range(0, 961, 60)),
        ticktext=[minutes_to_time(x) for x in range(0, 961, 60)],
        title="Heure de la journée",
        color="#8b949e",
        gridcolor="#21262d",
    )
    fig.update_yaxes(
        autorange="reversed",
        title="Machines",
        color="#8b949e",
        gridcolor="#21262d",
    )
    fig.update_layout(
        barmode="overlay",
        title=dict(
            text="Diagramme de Gantt — Ordonnancement des Machines",
            font=dict(family="Inter", color="#ff6b00", size=14)
        ),
        height=120 + 50 * len(machines),
        font=dict(family="Inter", size=12, color="#c9d1d9"),
        plot_bgcolor="#0d1117",
        paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(
            title=dict(text="Pièces", font=dict(color="#ff6b00")),
            orientation="v",
            font=dict(color="#c9d1d9"),
            bgcolor="rgba(22,27,34,0.8)",
            bordercolor="#30363d",
            borderwidth=1,
        ),
        margin=dict(l=10, r=10, t=60, b=10),
    )
    return fig