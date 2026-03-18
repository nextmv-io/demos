import json

import nextmv
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def build_demand_chart(time_periods: list[dict], labels: list[str]) -> nextmv.Asset:
    """Bar chart of demand across all time periods."""
    demands = [tp["demand"] for tp in time_periods]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=labels,
            y=demands,
            name="Demand",
            marker_color="#4C72B0",
        )
    )
    fig.update_layout(
        title="Demand by Time Period",
        xaxis_title="Time Period",
        yaxis_title="Workers Required",
        plot_bgcolor="white",
        paper_bgcolor="white",
        xaxis=dict(tickangle=-45),
    )

    return nextmv.Asset(
        name="Demand Profile",
        content_type="json",
        visual=nextmv.Visual(
            visual_schema=nextmv.VisualSchema(value="plotly"),
            visual_type="custom-tab",
            label="Demand Profile",
            tab_order=1,
        ),
        content=[json.loads(fig.to_json())],
    )


def build_solution_chart(
    open_shifts: list[dict],
    coverage: list[dict],
    labels: list[str],
) -> nextmv.Asset:
    """Two-panel chart: staffing coverage (top) and shift Gantt (bottom)."""
    fig = make_subplots(
        rows=2,
        cols=1,
        subplot_titles=("Staffing Coverage vs Demand", "Published Shifts (Gantt)"),
        row_heights=[0.45, 0.55],
        vertical_spacing=0.14,
    )

    # --- Top panel: coverage bars + demand line ---
    assigned_vals = [c["assigned"] for c in coverage]
    demand_vals = [c["demand"] for c in coverage]

    fig.add_trace(
        go.Bar(
            x=labels,
            y=assigned_vals,
            name="Assigned Workers",
            marker_color="#55A868",
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=labels,
            y=demand_vals,
            name="Demand",
            mode="lines+markers",
            line=dict(color="#C44E52", width=2, dash="dash"),
            marker=dict(size=6),
        ),
        row=1,
        col=1,
    )

    # Highlight unmet periods
    unmet_labels = [c["label"] for c in coverage if c["unmet"] > 0]
    unmet_vals = [c["unmet"] for c in coverage if c["unmet"] > 0]
    if unmet_labels:
        fig.add_trace(
            go.Bar(
                x=unmet_labels,
                y=unmet_vals,
                name="Unmet Demand",
                marker_color="#DD8452",
                opacity=0.7,
            ),
            row=1,
            col=1,
        )

    # --- Bottom panel: Gantt chart of shifts ---
    colors = [
        "#4C72B0", "#55A868", "#C44E52", "#8172B2",
        "#CCB974", "#64B5CD", "#E377C2", "#7F7F7F",
    ]

    n_periods = len(labels)
    for i, shift in enumerate(open_shifts):
        color = colors[i % len(colors)]
        start = shift["start_period"]
        end = shift["end_period"]  # exclusive
        workers = shift["workers"]

        fig.add_trace(
            go.Bar(
                x=[end - start],
                y=[f"Shift {i + 1}"],
                base=[start],
                orientation="h",
                name=f"Shift {i + 1} ({shift['start_label']}–{shift['end_label']}, {workers}w)",
                marker_color=color,
                text=f"{workers} workers",
                textposition="inside",
                insidetextanchor="middle",
                showlegend=True,
            ),
            row=2,
            col=1,
        )

    # x-axis ticks for Gantt (period indices → labels)
    fig.update_xaxes(
        tickvals=list(range(n_periods)),
        ticktext=labels,
        tickangle=-45,
        row=2,
        col=1,
    )

    fig.update_layout(
        title="Shift Planning Solution",
        barmode="stack",
        plot_bgcolor="white",
        paper_bgcolor="white",
        height=700,
        legend=dict(orientation="v", x=1.02, y=1),
    )
    fig.update_xaxes(tickangle=-45, row=1, col=1)
    fig.update_yaxes(title_text="Workers", row=1, col=1)
    fig.update_yaxes(title_text="Shift", row=2, col=1)
    fig.update_xaxes(title_text="Time Period", row=2, col=1)

    return nextmv.Asset(
        name="Shift Plan",
        content_type="json",
        visual=nextmv.Visual(
            visual_schema=nextmv.VisualSchema(value="plotly"),
            visual_type="custom-tab",
            label="Shift Plan",
            tab_order=2,
        ),
        content=[json.loads(fig.to_json())],
    )
