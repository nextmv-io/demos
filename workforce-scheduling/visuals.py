import json
import nextmv
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def pareto_chart(pareto_points, best_idx, tab_order=1) -> nextmv.Asset:
    """Scatter plot of Pareto front: cost vs. understaffing."""
    costs = [p["cost"] for p in pareto_points]
    understaffing = [p["understaffing"] for p in pareto_points]

    colors = ["#636EFA"] * len(pareto_points)
    sizes = [8] * len(pareto_points)
    colors[best_idx] = "#EF553B"
    sizes[best_idx] = 16

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=costs,
            y=understaffing,
            mode="markers",
            marker=dict(color=colors, size=sizes, line=dict(width=1, color="white")),
            name="Pareto Front",
            hovertemplate="Cost: $%{x:,.0f}<br>Understaffed shifts: %{y}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=[costs[best_idx]],
            y=[understaffing[best_idx]],
            mode="markers",
            marker=dict(color="#EF553B", size=16, symbol="star"),
            name="Selected Solution",
            hovertemplate="Cost: $%{x:,.0f}<br>Understaffed: %{y}<extra></extra>",
        )
    )
    fig.update_layout(
        title="Pareto Front — Cost vs. Understaffed Shifts",
        xaxis_title="Total Labor Cost ($)",
        yaxis_title="Understaffed Shifts",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )

    return nextmv.Asset(
        name="Pareto Front",
        content_type="json",
        visual=nextmv.Visual(
            visual_schema=nextmv.VisualSchema(value="plotly"),
            visual_type="custom-tab",
            label="Pareto Front",
            tab_order=tab_order,
        ),
        content=[json.loads(fig.to_json())],
    )


def schedule_heatmap(assignment_matrix, workers, shifts, shift_summary, tab_order=2) -> nextmv.Asset:
    """Heatmap of worker×shift assignments for the best solution."""
    worker_names = [w.get("name", w["id"]) for w in workers]
    shift_names = [s.get("name", s["id"]) for s in shifts]

    z = assignment_matrix.astype(int).tolist()

    hover = []
    for w, worker in enumerate(workers):
        row = []
        for s, shift in enumerate(shifts):
            name = worker.get("name", worker["id"])
            sname = shift.get("name", shift["id"])
            if assignment_matrix[w, s]:
                row.append(f"<b>{name}</b><br>{sname}<br>Cost: ${worker['cost_per_shift']}/shift")
            else:
                row.append(f"{name}<br>{sname}<br>Not assigned")
        hover.append(row)

    fig = go.Figure(
        go.Heatmap(
            z=z,
            x=shift_names,
            y=worker_names,
            colorscale=[[0, "#F0F4FF"], [1, "#636EFA"]],
            showscale=False,
            hovertemplate="%{customdata}<extra></extra>",
            customdata=hover,
            zmin=0,
            zmax=1,
        )
    )

    # Mark understaffed shifts with a red annotation
    coverage_map = {ss["shift_name"]: ss["covered"] for ss in shift_summary}
    for i, sname in enumerate(shift_names):
        if not coverage_map.get(sname, True):
            fig.add_annotation(
                x=sname,
                y=1.01,
                xref="x",
                yref="paper",
                text="⚠",
                showarrow=False,
                font=dict(color="red", size=14),
            )

    fig.update_layout(
        title="Schedule Heatmap — Best Solution (⚠ = understaffed shift)",
        xaxis_title="Shift",
        yaxis_title="Worker",
        xaxis={"side": "bottom", "tickangle": -30},
    )

    return nextmv.Asset(
        name="Schedule Heatmap",
        content_type="json",
        visual=nextmv.Visual(
            visual_schema=nextmv.VisualSchema(value="plotly"),
            visual_type="custom-tab",
            label="Schedule",
            tab_order=tab_order,
        ),
        content=[json.loads(fig.to_json())],
    )


def convergence_chart(history, tab_order=3) -> nextmv.Asset:
    """Dual-axis line chart: best feasible cost and min understaffing over generations."""
    gens = [h["generation"] for h in history]
    min_understaff = [h["min_understaffing"] for h in history]

    # Forward-fill best_cost (None before first fully-covered solution)
    best_costs = []
    last = None
    for h in history:
        if h["best_cost"] is not None:
            last = h["best_cost"]
        best_costs.append(last)

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Scatter(
            x=gens,
            y=best_costs,
            name="Best Fully-Covered Cost",
            line=dict(color="#636EFA"),
            connectgaps=True,
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=gens,
            y=min_understaff,
            name="Min Understaffing",
            line=dict(color="#EF553B", dash="dot"),
        ),
        secondary_y=True,
    )
    fig.update_layout(
        title="GA Convergence over Generations",
        xaxis_title="Generation",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    fig.update_yaxes(title_text="Cost ($)", secondary_y=False)
    fig.update_yaxes(title_text="Understaffed Shifts", secondary_y=True, rangemode="tozero")

    return nextmv.Asset(
        name="Convergence",
        content_type="json",
        visual=nextmv.Visual(
            visual_schema=nextmv.VisualSchema(value="plotly"),
            visual_type="custom-tab",
            label="Convergence",
            tab_order=tab_order,
        ),
        content=[json.loads(fig.to_json())],
    )
