import json

import nextmv
import plotly.graph_objects as go

# Qualitative color palette, cycling for many jobs
COLORS = [
    "#636EFA", "#EF553B", "#00CC96", "#AB63FA", "#FFA15A",
    "#19D3F3", "#FF6692", "#B6E880", "#FF97FF", "#FECB52",
]


def gantt_chart(schedule: list, machines: list, tab_order: int = 1) -> nextmv.Asset:
    """Horizontal Gantt chart: one row per machine, bars colored by job."""
    job_ids = sorted({t["job_id"] for t in schedule})
    job_colors = {j: COLORS[i % len(COLORS)] for i, j in enumerate(job_ids)}

    fig = go.Figure()
    legend_added = set()

    for task in sorted(schedule, key=lambda t: (t["machine"], t["start"])):
        job = task["job_id"]
        show_legend = job not in legend_added
        legend_added.add(job)

        fig.add_trace(
            go.Bar(
                name=job,
                x=[task["duration"]],
                y=[task["machine"]],
                base=[task["start"]],
                orientation="h",
                marker_color=job_colors[job],
                showlegend=show_legend,
                hovertemplate=(
                    f"<b>{job}</b> — step {task['step'] + 1}<br>"
                    f"Machine: {task['machine']}<br>"
                    f"Start: {task['start']} min<br>"
                    f"End: {task['end']} min<br>"
                    f"Duration: {task['duration']} min"
                    "<extra></extra>"
                ),
            )
        )

    fig.update_layout(
        title="Machine Shop Schedule — Gantt Chart",
        xaxis_title="Time (minutes)",
        yaxis_title="Machine",
        barmode="overlay",
        legend_title="Job",
        yaxis={"categoryorder": "array", "categoryarray": machines[::-1]},
    )

    return nextmv.Asset(
        name="Gantt Chart",
        content_type="json",
        visual=nextmv.Visual(
            visual_schema=nextmv.VisualSchema(value="plotly"),
            visual_type="custom-tab",
            label="Gantt Chart",
            tab_order=tab_order,
        ),
        content=[json.loads(fig.to_json())],
    )


def utilization_chart(
    machine_util: dict, makespan: int, tab_order: int = 2
) -> nextmv.Asset:
    """Bar chart of utilization percentage per machine."""
    machines = sorted(machine_util)
    pcts = [round(machine_util[m] * 100, 1) for m in machines]

    fig = go.Figure(
        go.Bar(
            x=machines,
            y=pcts,
            marker_color="#00CC96",
            text=[f"{p}%" for p in pcts],
            textposition="outside",
        )
    )

    fig.update_layout(
        title=f"Machine Utilization  (makespan = {makespan} min)",
        xaxis_title="Machine",
        yaxis_title="Utilization (%)",
        yaxis={"range": [0, 115]},
    )

    return nextmv.Asset(
        name="Machine Utilization",
        content_type="json",
        visual=nextmv.Visual(
            visual_schema=nextmv.VisualSchema(value="plotly"),
            visual_type="custom-tab",
            label="Machine Utilization",
            tab_order=tab_order,
        ),
        content=[json.loads(fig.to_json())],
    )
