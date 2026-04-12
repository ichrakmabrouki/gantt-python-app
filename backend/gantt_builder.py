import pandas as pd
import plotly.graph_objects as go
import plotly.colors as pc
from datetime import datetime, timedelta

START_DAY = datetime.strptime("06:00", "%H:%M")

def minutes_to_time(minutes: int) -> str:
    t = START_DAY + timedelta(minutes=int(minutes))
    return t.strftime("%H:%M")

def build_gantt(df_ops: pd.DataFrame,
                df_jobs: pd.DataFrame = None) -> go.Figure:
    df = df_ops.copy()

    # ── Fusion JobID seulement si absent ─────────────────────────────────────
    if "JobID" not in df.columns:
        if df_jobs is not None and not df_jobs.empty:
            df = pd.merge(df, df_jobs[["OperationID", "JobID"]],
                          on="OperationID", how="left")
        else:
            df["JobID"] = 0

    df["JobID"]    = df["JobID"].fillna(0).astype(int)
    df["JobLabel"] = "Job " + df["JobID"].astype(str)

    # Types
    df["MachineID"]   = df["MachineID"].astype(str)
    df["OperationID"] = df["OperationID"].astype(str)
    df["StartTime"]   = df["StartTime"].astype(int)
    df["EndTime"]     = df["EndTime"].astype(int)
    df["Duration"]    = df["Duration"].astype(int)

    # Conversion minutes → heures
    df["Start_str"] = df["StartTime"].apply(minutes_to_time)
    df["End_str"]   = df["EndTime"].apply(minutes_to_time)

    # Couleurs par Job
    jobs      = df["JobLabel"].unique()
    colors    = pc.qualitative.Plotly
    color_map = {j: colors[i % len(colors)] for i, j in enumerate(jobs)}

    # Machines triées
    machines = {
        m: df[df["MachineID"] == m].sort_values("StartTime")
        for m in sorted(df["MachineID"].unique(), key=lambda x: int(x))
    }

    fig = go.Figure()
    seen_jobs = set()

    for machine, ops in machines.items():
        for _, row in ops.iterrows():
            job = row["JobLabel"]
            show = job not in seen_jobs
            seen_jobs.add(job)
            fig.add_trace(go.Bar(
                x=[row["Duration"]],
                y=[f"Machine {machine}"],
                base=row["StartTime"],
                name=job,
                legendgroup=job,
                showlegend=show,
                orientation="h",
                text=f'Op {row["OperationID"]}',
                textposition="inside",
                marker=dict(color=color_map[job]),
                hovertemplate=(
                    f'<b>{job}</b><br>'
                    f'Opération : {row["OperationID"]}<br>'
                    f'Machine   : {machine}<br>'
                    f'Début     : {row["Start_str"]}<br>'
                    f'Fin       : {row["End_str"]}<br>'
                    f'Durée     : {row["Duration"]} min'
                    '<extra></extra>'
                )
            ))

    # Makespan — ligne rouge
    makespan = df["EndTime"].max()
    fig.add_shape(type="line",
        x0=makespan, x1=makespan, y0=-0.5, y1=len(machines)-0.5,
        line=dict(color="red", width=3, dash="dash"))
    fig.add_annotation(x=makespan, y=len(machines)-0.5,
        text=f"Makespan : {minutes_to_time(makespan)}",
        showarrow=True, arrowhead=2, ax=0, ay=-30,
        font=dict(color="red", size=13))

    # Heure actuelle — ligne verte
    now = datetime.now()
    start_of_day    = datetime.combine(now.date(), START_DAY.time())
    current_minutes = (now - start_of_day).total_seconds() / 60
    current_minutes = max(0, min(current_minutes, 960))
    fig.add_shape(type="line",
        x0=current_minutes, x1=current_minutes,
        y0=-0.5, y1=len(machines)-0.5,
        line=dict(color="green", width=3, dash="dot"))
    fig.add_annotation(x=current_minutes, y=0,
        text=f"Maintenant : {minutes_to_time(current_minutes)}",
        showarrow=True, arrowhead=2, ax=0, ay=-40,
        font=dict(color="green", size=12))

    # Axe X en heures
    fig.update_xaxes(
        tickvals=list(range(0, 961, 60)),
        ticktext=[minutes_to_time(x) for x in range(0, 961, 60)],
        title="Heure de la journée"
    )
    fig.update_yaxes(autorange="reversed", title="Machines")
    fig.update_layout(
        barmode="overlay",
        title="Diagramme de Gantt — Ordonnancement des Machines",
        height=120 + 50 * len(machines),
        font=dict(family="Segoe UI", size=13),
        plot_bgcolor="#f8fafc",
        paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(title="Jobs", orientation="v"),
        margin=dict(l=10, r=10, t=60, b=10),
    )
    return fig