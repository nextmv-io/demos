import json

import nextmv
import plotly.graph_objects as go

PRIORITY_COLORS = {
    "expedite": "#e15759",
    "standard": "#4e79a7",
    "defer": "#bab0ac",
}
TIERS = ["gold", "silver", "bronze"]
PRIORITIES = ["expedite", "standard", "defer"]


def priority_breakdown_chart(results, tab_order=1) -> nextmv.Asset:
    """Grouped bar chart: priority counts broken down by customer tier."""

    tier_priority_counts = {
        tier: {p: sum(1 for r in results if r["customer_tier"] == tier and r["priority"] == p) for p in PRIORITIES}
        for tier in TIERS
    }

    fig = go.Figure()
    for priority in PRIORITIES:
        fig.add_trace(
            go.Bar(
                name=priority.capitalize(),
                x=TIERS,
                y=[tier_priority_counts[tier][priority] for tier in TIERS],
                marker_color=PRIORITY_COLORS[priority],
            )
        )

    fig.update_layout(
        title="Order Priority by Customer Tier",
        xaxis_title="Customer Tier",
        yaxis_title="Number of Orders",
        barmode="group",
        legend_title="Priority",
        width=800,
        height=500,
    )

    return nextmv.Asset(
        name="Priority Breakdown",
        content_type="json",
        visual=nextmv.Visual(
            visual_schema=nextmv.VisualSchema(value="plotly"),
            visual_type="custom-tab",
            label="Priority Breakdown",
            tab_order=tab_order,
        ),
        content=[json.loads(fig.to_json())],
    )


def priority_scatter_chart(results, tab_order=2) -> nextmv.Asset:
    """Scatter plot: order value vs days until deadline, colored by priority."""

    fig = go.Figure()
    for priority in PRIORITIES:
        orders = [r for r in results if r["priority"] == priority]
        fig.add_trace(
            go.Scatter(
                x=[o["days_until_deadline"] for o in orders],
                y=[o["value"] for o in orders],
                mode="markers",
                name=priority.capitalize(),
                marker=dict(color=PRIORITY_COLORS[priority], size=8, opacity=0.75),
                text=[f"{o['id']}<br>Tier: {o['customer_tier']}<br>Units: {o['units']}" for o in orders],
                hoverinfo="text+x+y",
            )
        )

    fig.update_layout(
        title="Order Value vs. Days Until Deadline",
        xaxis_title="Days Until Deadline",
        yaxis_title="Order Value ($)",
        legend_title="Priority",
        width=800,
        height=500,
    )

    return nextmv.Asset(
        name="Value vs Deadline",
        content_type="json",
        visual=nextmv.Visual(
            visual_schema=nextmv.VisualSchema(value="plotly"),
            visual_type="custom-tab",
            label="Value vs Deadline",
            tab_order=tab_order,
        ),
        content=[json.loads(fig.to_json())],
    )
