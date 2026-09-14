import pandas as pd
import plotly.colors as pc
import plotly.graph_objects as go
from datetime import datetime, timedelta

from backend.ui_theme import PALETTES


DEFAULT_START_MINUTES = 360
WORKDAY_MINUTES = 16 * 60
SETUP_COLOR = "#00bcd4"


def minutes_to_time(minutes: int, start_time_day: int = DEFAULT_START_MINUTES) -> str:
    day_index = int(minutes) // WORKDAY_MINUTES
    minute_in_day = int(minutes) % WORKDAY_MINUTES
    clock_minutes = int(start_time_day) + minute_in_day
    time_label = (datetime.strptime("00:00", "%H:%M") + timedelta(minutes=clock_minutes)).strftime("%H:%M")
    if day_index <= 0:
        return time_label
    return f"J{day_index + 1} {time_label}"


def hour_tick_label(minutes: int, start_time_day: int = DEFAULT_START_MINUTES) -> str:
    minute_in_day = int(minutes) % WORKDAY_MINUTES
    clock_minutes = int(start_time_day) + minute_in_day
    hour = (clock_minutes // 60) % 24
    minute = clock_minutes % 60
    if minute == 0:
        return f"{hour}h"
    return f"{hour}h{minute:02d}"


def build_gantt(
    df_ops: pd.DataFrame,
    df_jobs: pd.DataFrame = None,
    of_map: dict = None,
    piece_map: dict = None,
    start_time_day: int = DEFAULT_START_MINUTES,
    cte: int = 0,
    x_range: tuple[int, int] | None = None,
    palette: dict | None = None,
    mobile: bool = False,
) -> go.Figure:
    # Le Gantt etait entierement code en sombre : sur fond blanc, il devenait
    # un rectangle noir au texte gris. Les couleurs viennent maintenant de la
    # palette du theme actif ; sans argument, on garde le mode sombre.
    # Sur telephone, le diagramme ne peut pas seulement retrecir : la legende
    # verticale devorerait la moitie de la largeur, et des etiquettes de 7 px
    # ne se lisent pas. Il est donc reconstruit, pas seulement redimensionne.
    pal = palette or PALETTES["sombre"]
    c_texte  = pal["texte"]
    c_faible = pal["texteFaible"]
    c_grille = pal["bordure"]
    c_fond   = pal["fond"]
    c_accent = pal["accent3"]   # orange assombri : lisible sur fond blanc
    c_danger = pal["danger"]
    c_panneau = pal["surface"]

    df = df_ops.copy()

    if df.empty:
        fig = go.Figure()
        fig.update_layout(
            title="Diagramme de Gantt",
            plot_bgcolor=c_fond,
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Inter", size=12, color=c_texte),
        )
        return fig

    if "JobID" not in df.columns:
        if df_jobs is not None and not df_jobs.empty:
            df = pd.merge(df, df_jobs[["OperationID", "JobID"]], on="OperationID", how="left")
        else:
            df["JobID"] = 0

    df["JobID"] = df["JobID"].fillna(0).astype(int)

    def make_piece_label(job_id: int) -> str:
        if piece_map and job_id in piece_map:
            return f"P{job_id} - {piece_map[job_id]}"
        return f"Piece {job_id}"

    def get_of(job_id: int) -> str:
        if of_map and job_id in of_map:
            return of_map[job_id]
        return ""

    df["MachineID"] = df["MachineID"].astype(str)
    df["OperationID"] = df["OperationID"].astype(str)
    df["StartTime"] = df["StartTime"].astype(int)
    df["EndTime"] = df["EndTime"].astype(int)
    df["Duration"] = df["Duration"].astype(int)
    df["JobLabel"] = df["JobID"].apply(make_piece_label)
    df["Start_str"] = df["StartTime"].apply(lambda value: minutes_to_time(value, start_time_day))
    df["End_str"] = df["EndTime"].apply(lambda value: minutes_to_time(value, start_time_day))

    pieces = df["JobLabel"].unique()
    colors = pc.qualitative.Plotly
    color_map = {piece: colors[index % len(colors)] for index, piece in enumerate(pieces)}

    machines = {
        machine: df[df["MachineID"] == machine].sort_values("StartTime")
        for machine in sorted(df["MachineID"].unique(), key=lambda value: int(value))
    }

    fig = go.Figure()
    seen_legend = set()
    setup_legend_shown = False
    setup_minutes = max(int(cte or 0), 0)

    for machine, ops in machines.items():
        machine_label = f"Machine {machine}"

        for _, row in ops.iterrows():
            piece = row["JobLabel"]
            of_value = get_of(int(row["JobID"]))
            show_piece = piece not in seen_legend
            seen_legend.add(piece)

            if setup_minutes > 0:
                setup_start = max(0, row["StartTime"] - setup_minutes)
                setup_duration = row["StartTime"] - setup_start
                if setup_duration > 0:
                    fig.add_trace(
                        go.Bar(
                            x=[setup_duration],
                            y=[machine_label],
                            base=setup_start,
                            name="Setup",
                            legendgroup="Setup",
                            showlegend=not setup_legend_shown,
                            orientation="h",
                            text="setup",
                            textposition="inside",
                            textfont=dict(size=10, color="#0d1117"),
                            marker=dict(color=SETUP_COLOR),
                            hovertemplate=(
                                "<b>Setup</b><br>"
                                f"Machine : {machine}<br>"
                                f"Debut   : {minutes_to_time(setup_start, start_time_day)}<br>"
                                f"Fin     : {minutes_to_time(row['StartTime'], start_time_day)}<br>"
                                f"Duree   : {setup_duration} min"
                                "<extra></extra>"
                            ),
                        )
                    )
                    setup_legend_shown = True

            fig.add_trace(
                go.Bar(
                    x=[row["Duration"]],
                    y=[machine_label],
                    base=row["StartTime"],
                    name=piece,
                    legendgroup=piece,
                    showlegend=show_piece,
                    orientation="h",
                    text=f"Op {row['OperationID']}",
                    textposition="inside",
                    marker=dict(color=color_map[piece]),
                    hovertemplate=(
                        f"<b>{piece}</b><br>"
                        + (f"OF : {of_value}<br>" if of_value else "")
                        + f"Operation : {row['OperationID']}<br>"
                        f"Machine   : {machine}<br>"
                        f"Debut     : {row['Start_str']}<br>"
                        f"Fin       : {row['End_str']}<br>"
                        f"Duree     : {row['Duration']} min"
                        "<extra></extra>"
                    ),
                )
            )

    makespan = int(df["EndTime"].max())
    batch_makespan = int(df["EndTime"].max() - df["StartTime"].min())
    machine_count = len(machines)
    if x_range is not None:
        view_start, view_end = x_range
        axis_max = max(int(view_end), WORKDAY_MINUTES)
        day_count = max(1, (axis_max + WORKDAY_MINUTES - 1) // WORKDAY_MINUTES)
        day_start_index = max(0, int(view_start) // WORKDAY_MINUTES)
        day_end_index = max(day_start_index, (max(int(view_end) - 1, 0)) // WORKDAY_MINUTES)
    else:
        axis_max = max(makespan + 60, WORKDAY_MINUTES)
        day_count = max(1, (axis_max + WORKDAY_MINUTES - 1) // WORKDAY_MINUTES)
        view_start = 0
        view_end = max(axis_max, ((makespan // 60) + 2) * 60)
        day_start_index = 0
        day_end_index = day_count - 1

    makespan_day_index = makespan // WORKDAY_MINUTES
    if day_start_index <= makespan_day_index <= day_end_index:
        fig.add_shape(
            type="line",
            x0=makespan,
            x1=makespan,
            y0=-0.5,
            y1=machine_count - 0.5,
            line=dict(color=c_danger, width=2.5, dash="dash"),
        )
        fig.add_annotation(
            x=makespan,
            y=machine_count - 0.5,
            text=f"Fin du lot : {minutes_to_time(makespan, start_time_day)}",
            showarrow=True,
            arrowhead=2,
            ax=0,
            ay=-30,
            font=dict(color=c_danger, size=12),
        )

    tick_step = 4 * 60
    tick_start = (int(view_start) // tick_step) * tick_step
    tick_end = ((int(view_end) + tick_step - 1) // tick_step) * tick_step
    tickvals = list(range(tick_start, tick_end + 1, tick_step))

    for day_index in range(day_start_index, day_end_index + 1):
        day_start = day_index * WORKDAY_MINUTES
        if day_start > 0:
            fig.add_shape(
                type="line",
                x0=day_start,
                x1=day_start,
                y0=-0.5,
                y1=machine_count - 0.5,
                line=dict(color=c_grille, width=1.6, dash="dot"),
            )
        fig.add_annotation(
            x=day_start + (WORKDAY_MINUTES / 2),
            y=machine_count - 0.25,
            text=f"Jour {day_index + 1}",
            showarrow=False,
            font=dict(color=c_faible, size=11),
        )

    now = datetime.now()
    current_clock_minutes = (now.hour * 60 + now.minute) - int(start_time_day)
    if 0 <= current_clock_minutes <= WORKDAY_MINUTES:
        now_x = day_end_index * WORKDAY_MINUTES + current_clock_minutes
        if view_start <= now_x <= view_end:
            fig.add_shape(
                type="line",
                x0=now_x,
                x1=now_x,
                y0=-0.5,
                y1=machine_count - 0.5,
                line=dict(color=c_texte, width=1.8, dash="dot"),
            )
            fig.add_annotation(
                x=now_x,
                y=-0.35,
                text=f"Maintenant : {now.strftime('%H:%M')}",
                showarrow=False,
                font=dict(color=c_fond, size=10),
                bgcolor=c_texte,
            )

    fig.update_xaxes(
        tickvals=tickvals,
        ticktext=[hour_tick_label(value, start_time_day) for value in tickvals],
        title="Heures",
        color=c_faible,
        gridcolor=c_grille,
        range=[view_start, view_end],
        tickfont=dict(size=10 if mobile else 7),
        tickangle=0,
        title_standoff=4,
        automargin=True,
    )
    fig.update_yaxes(
        autorange="reversed",
        title="Machines",
        color=c_faible,
        gridcolor=c_grille,
    )
    fig.update_layout(
        barmode="overlay",
        title=dict(
            text="Ordonnancement" if mobile
                 else "Diagramme de Gantt - Ordonnancement continu multi-jours",
            font=dict(family="Inter", color=c_accent, size=13 if mobile else 14),
        ),
        height=(150 + 62 * machine_count) if mobile
               else (160 + 70 * machine_count),
        font=dict(family="Inter", size=12 if not mobile else 13, color=c_texte),
        plot_bgcolor=c_fond,
        paper_bgcolor="rgba(0,0,0,0)",
        # Legende sous le graphique sur telephone : posee a droite, elle
        # prenait la moitie de l'ecran et le Gantt devenait une bande.
        legend=dict(
            title=dict(text="" if mobile else "Pieces",
                       font=dict(color=c_accent)),
            orientation="h" if mobile else "v",
            yanchor="top" if mobile else "auto",
            y=-0.22 if mobile else 1,
            x=0 if mobile else 1.02,
            font=dict(color=c_texte, size=11 if mobile else 12),
            bgcolor="rgba(0,0,0,0)" if mobile else c_panneau,
            bordercolor=c_grille,
            borderwidth=0 if mobile else 1,
        ),
        # Le doigt fait defiler le temps ; le pincement zoome.
        dragmode="pan" if mobile else "zoom",
        margin=(dict(l=4, r=4, t=34, b=96) if mobile
                else dict(l=10, r=10, t=60, b=52)),
    )
    return fig
