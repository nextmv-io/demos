import json

import nextmv
import plotly.graph_objects as go
from plotly.subplots import make_subplots

COLORS = [
    "#4C72B0", "#55A868", "#C44E52", "#8172B2",
    "#CCB974", "#64B5CD", "#E377C2", "#7F7F7F",
    "#BCBD22", "#17BECF",
]


def build_schedule_chart(
    assignments: list[dict],
    workers: list[dict],
    shifts: list[dict],
    shift_coverage: dict,
    tab_order: int = 1,
) -> nextmv.Asset:
    """Heatmap of worker × shift assignments, plus per-shift coverage bar."""
    worker_ids = [w["id"] for w in workers]
    worker_names = [w.get("name", w["id"]) for w in workers]
    shift_ids = [s["id"] for s in shifts]
    shift_names = [s.get("name", s["id"]) for s in shifts]

    # Build assignment matrix
    matrix = [[0] * len(shift_ids) for _ in range(len(worker_ids))]
    for a in assignments:
        wi = next(i for i, w in enumerate(workers) if w["id"] == a["worker_id"])
        si = next(i for i, s in enumerate(shifts) if s["id"] == a["shift_id"])
        matrix[wi][si] = 1

    required_counts = [shift_coverage[sid]["required"] for sid in shift_ids]
    assigned_counts = [shift_coverage[sid]["assigned"] for sid in shift_ids]
    shortfall_counts = [shift_coverage[sid].get("shortfall", 0) for sid in shift_ids]

    fig = make_subplots(
        rows=2,
        cols=1,
        subplot_titles=("Worker–Shift Assignment Matrix", "Coverage vs. Required Workers"),
        row_heights=[0.65, 0.35],
        vertical_spacing=0.14,
    )

    # Heatmap
    fig.add_trace(
        go.Heatmap(
            z=matrix,
            x=shift_names,
            y=worker_names,
            colorscale=[[0, "#F5F5F5"], [1, "#4C72B0"]],
            showscale=False,
            text=[
                ["✓" if matrix[wi][si] else "" for si in range(len(shift_ids))]
                for wi in range(len(worker_ids))
            ],
            texttemplate="%{text}",
            hovertemplate="Worker: %{y}<br>Shift: %{x}<br>Assigned: %{z}<extra></extra>",
        ),
        row=1,
        col=1,
    )

    # Coverage bars — stacked: assigned (green/red) + shortfall (orange)
    met_color = "#55A868"
    unmet_color = "#C44E52"
    bar_colors = [met_color if a >= r else unmet_color for a, r in zip(assigned_counts, required_counts)]

    fig.add_trace(
        go.Bar(
            x=shift_names,
            y=assigned_counts,
            name="Assigned",
            marker_color=bar_colors,
            text=[f"{a}/{r}" for a, r in zip(assigned_counts, required_counts)],
            textposition="inside",
        ),
        row=2,
        col=1,
    )
    if any(s > 0 for s in shortfall_counts):
        fig.add_trace(
            go.Bar(
                x=shift_names,
                y=shortfall_counts,
                name="Shortfall",
                marker_color="#DD8452",
                opacity=0.85,
                text=[f"-{s}" if s > 0 else "" for s in shortfall_counts],
                textposition="outside",
            ),
            row=2,
            col=1,
        )
    fig.add_trace(
        go.Scatter(
            x=shift_names,
            y=required_counts,
            name="Required",
            mode="lines+markers",
            line=dict(color="#333333", dash="dash", width=2),
            marker=dict(size=7),
        ),
        row=2,
        col=1,
    )

    fig.update_layout(
        title="Shift Schedule",
        height=650,
        barmode="stack",
        plot_bgcolor="white",
        paper_bgcolor="white",
        showlegend=True,
    )
    fig.update_xaxes(tickangle=-35, row=1, col=1)
    fig.update_xaxes(tickangle=-35, row=2, col=1)
    fig.update_yaxes(title_text="Worker", row=1, col=1)
    fig.update_yaxes(title_text="Workers Assigned", row=2, col=1)

    return nextmv.Asset(
        name="Shift Schedule",
        content_type="json",
        visual=nextmv.Visual(
            visual_schema=nextmv.VisualSchema(value="plotly"),
            visual_type="custom-tab",
            label="Shift Schedule",
            tab_order=tab_order,
        ),
        content=[json.loads(fig.to_json())],
    )


def build_fairness_chart(
    worker_shift_counts: dict,
    workers: list[dict],
    tab_order: int = 2,
) -> nextmv.Asset:
    """Bar chart of shifts assigned per worker, colored by deviation from mean."""
    worker_names = [w.get("name", w["id"]) for w in workers]
    counts = [worker_shift_counts[w["id"]] for w in workers]

    if counts:
        mean_count = sum(counts) / len(counts)
        max_dev = max(abs(c - mean_count) for c in counts) or 1.0
        bar_colors = [
            f"rgba({int(76 + 179 * abs(c - mean_count) / max_dev)}, "
            f"{int(114 - 114 * abs(c - mean_count) / max_dev)}, "
            f"{int(176 - 176 * abs(c - mean_count) / max_dev)}, 0.85)"
            for c in counts
        ]
    else:
        mean_count = 0
        bar_colors = ["#4C72B0"] * len(workers)

    spread = max(counts) - min(counts) if counts else 0

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=worker_names,
            y=counts,
            marker_color=bar_colors,
            text=counts,
            textposition="outside",
            hovertemplate="%{x}: %{y} shifts<extra></extra>",
        )
    )
    if counts:
        fig.add_hline(
            y=mean_count,
            line_dash="dash",
            line_color="#555",
            annotation_text=f"Mean: {mean_count:.1f}",
            annotation_position="right",
        )

    fig.update_layout(
        title=f"Shifts per Worker  (spread = {spread})",
        xaxis_title="Worker",
        yaxis_title="Shifts Assigned",
        plot_bgcolor="white",
        paper_bgcolor="white",
        xaxis=dict(tickangle=-35),
        showlegend=False,
    )

    return nextmv.Asset(
        name="Fairness View",
        content_type="json",
        visual=nextmv.Visual(
            visual_schema=nextmv.VisualSchema(value="plotly"),
            visual_type="custom-tab",
            label="Fairness View",
            tab_order=tab_order,
        ),
        content=[json.loads(fig.to_json())],
    )
