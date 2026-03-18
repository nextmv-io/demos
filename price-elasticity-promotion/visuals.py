import json
import numpy as np
import nextmv
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def build_elasticity_chart(product_data: list[dict]) -> nextmv.Asset:
    """Tab 1: Demand curves for each product across a range of prices."""
    fig = go.Figure()

    colors = [
        "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
        "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf",
    ]

    for idx, pd in enumerate(product_data):
        base_price = pd["base_price"]
        base_demand = pd["base_demand"]
        e = pd["elasticity"]
        color = colors[idx % len(colors)]

        # Price range: base ± 40%
        prices = np.linspace(base_price * 0.6, base_price * 1.4, 60)
        demands = [base_demand * ((p / base_price) ** e) for p in prices]
        discounts = [(1 - p / base_price) * 100 for p in prices]

        fig.add_trace(go.Scatter(
            x=list(discounts),
            y=demands,
            mode="lines",
            name=f"{pd['name']} (e={e:.2f})",
            line=dict(color=color, width=2),
            hovertemplate=(
                f"<b>{pd['name']}</b><br>"
                "Discount: %{x:.1f}%<br>"
                "Expected Demand: %{y:.1f} units<extra></extra>"
            ),
        ))

        # Mark base point (0% discount)
        fig.add_trace(go.Scatter(
            x=[0],
            y=[base_demand],
            mode="markers",
            marker=dict(color=color, size=10, symbol="circle"),
            showlegend=False,
            hovertemplate=(
                f"<b>{pd['name']}</b><br>"
                f"Base Price: ${base_price:.2f}<br>"
                f"Base Demand: {base_demand:.0f} units<extra></extra>"
            ),
        ))

    fig.update_layout(
        title="Price Elasticity Demand Curves",
        xaxis_title="Discount (%)",
        yaxis_title="Expected Demand (units)",
        legend=dict(orientation="h", yanchor="bottom", y=-0.4, xanchor="center", x=0.5),
        hovermode="x unified",
        margin=dict(b=160),
    )

    fig.add_vline(x=0, line_dash="dash", line_color="gray", annotation_text="Base price")

    return nextmv.Asset(
        name="Elasticity Demand Curves",
        content_type="json",
        visual=nextmv.Visual(
            visual_schema=nextmv.VisualSchema(value="plotly"),
            visual_type="custom-tab",
            label="Elasticity Curves",
            tab_order=1,
        ),
        content=[json.loads(fig.to_json())],
    )


def build_promotion_chart(assignments: list[dict], product_data: list[dict]) -> nextmv.Asset:
    """Tab 2: Recommended discount per product with demand lift annotation."""
    if not assignments:
        fig = go.Figure()
        fig.update_layout(title="No feasible promotion plan found")
        return nextmv.Asset(
            name="Promotion Recommendations",
            content_type="json",
            visual=nextmv.Visual(
                visual_schema=nextmv.VisualSchema(value="plotly"),
                visual_type="custom-tab",
                label="Promotion Plan",
                tab_order=2,
            ),
            content=[json.loads(fig.to_json())],
        )

    names = [a["product_name"] for a in assignments]
    discounts = [a["discount_pct"] for a in assignments]
    demand_lifts = [a["demand_lift_pct"] for a in assignments]
    expected_demands = [a["expected_demand"] for a in assignments]
    base_demands = [a["base_demand"] for a in assignments]
    elasticities = [a["elasticity"] for a in assignments]

    # Color by discount level
    bar_colors = ["#2ecc71" if d > 0 else "#95a5a6" for d in discounts]

    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=("Recommended Discount (%)", "Demand Lift vs Baseline (%)"),
        horizontal_spacing=0.15,
    )

    # Left: discount percentages
    fig.add_trace(
        go.Bar(
            x=discounts,
            y=names,
            orientation="h",
            marker_color=bar_colors,
            text=[f"{d:.0f}%" if d > 0 else "No promo" for d in discounts],
            textposition="outside",
            hovertemplate=(
                "<b>%{y}</b><br>"
                "Discount: %{x:.1f}%<br>"
                "<extra></extra>"
            ),
            showlegend=False,
        ),
        row=1, col=1,
    )

    # Right: demand lift
    lift_colors = ["#e74c3c" if l < 0 else "#3498db" for l in demand_lifts]
    fig.add_trace(
        go.Bar(
            x=demand_lifts,
            y=names,
            orientation="h",
            marker_color=lift_colors,
            text=[f"+{l:.1f}%" if l >= 0 else f"{l:.1f}%" for l in demand_lifts],
            textposition="outside",
            customdata=list(zip(expected_demands, base_demands, elasticities)),
            hovertemplate=(
                "<b>%{y}</b><br>"
                "Demand Lift: %{x:.1f}%<br>"
                "Expected: %{customdata[0]:.0f} units<br>"
                "Baseline: %{customdata[1]:.0f} units<br>"
                "Elasticity: %{customdata[2]:.2f}<br>"
                "<extra></extra>"
            ),
            showlegend=False,
        ),
        row=1, col=2,
    )

    fig.update_xaxes(title_text="Discount (%)", row=1, col=1)
    fig.update_xaxes(title_text="Demand Lift (%)", row=1, col=2)

    n = len(names)
    height = max(400, 100 + n * 40)
    fig.update_layout(
        title="Promotion Recommendations",
        height=height,
        margin=dict(l=160),
    )

    return nextmv.Asset(
        name="Promotion Recommendations",
        content_type="json",
        visual=nextmv.Visual(
            visual_schema=nextmv.VisualSchema(value="plotly"),
            visual_type="custom-tab",
            label="Promotion Plan",
            tab_order=2,
        ),
        content=[json.loads(fig.to_json())],
    )


def build_profit_chart(assignments: list[dict], product_data: list[dict]) -> nextmv.Asset:
    """Tab 3: Baseline vs promoted profit per product and overall budget usage."""
    if not assignments:
        fig = go.Figure()
        fig.update_layout(title="No feasible promotion plan found")
        return nextmv.Asset(
            name="Financial Impact",
            content_type="json",
            visual=nextmv.Visual(
                visual_schema=nextmv.VisualSchema(value="plotly"),
                visual_type="custom-tab",
                label="Financial Impact",
                tab_order=3,
            ),
            content=[json.loads(fig.to_json())],
        )

    # Build lookup from id -> assignment
    assign_map = {a["product_id"]: a for a in assignments}

    names = []
    baseline_profits = []
    promo_profits = []
    incremental = []

    for pd in product_data:
        a = assign_map.get(pd["id"])
        if a is None:
            continue
        base_profit = (pd["base_price"] - pd["cost"]) * pd["base_demand"]
        promo_profit = a["profit"]
        names.append(pd["name"])
        baseline_profits.append(round(base_profit, 2))
        promo_profits.append(round(promo_profit, 2))
        incremental.append(round(promo_profit - base_profit, 2))

    inc_colors = ["#27ae60" if v >= 0 else "#e74c3c" for v in incremental]

    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=("Profit: Baseline vs Promoted ($)", "Incremental Profit Lift ($)"),
        horizontal_spacing=0.15,
    )

    # Left: grouped bar
    fig.add_trace(
        go.Bar(
            name="Baseline",
            x=names,
            y=baseline_profits,
            marker_color="#95a5a6",
            hovertemplate="<b>%{x}</b><br>Baseline Profit: $%{y:,.2f}<extra></extra>",
        ),
        row=1, col=1,
    )
    fig.add_trace(
        go.Bar(
            name="Promoted",
            x=names,
            y=promo_profits,
            marker_color="#2980b9",
            hovertemplate="<b>%{x}</b><br>Promoted Profit: $%{y:,.2f}<extra></extra>",
        ),
        row=1, col=1,
    )

    # Right: incremental bars
    fig.add_trace(
        go.Bar(
            x=names,
            y=incremental,
            marker_color=inc_colors,
            text=[f"${v:+,.2f}" for v in incremental],
            textposition="outside",
            hovertemplate="<b>%{x}</b><br>Lift: $%{y:+,.2f}<extra></extra>",
            showlegend=False,
        ),
        row=1, col=2,
    )

    fig.update_layout(
        title="Financial Impact of Promotions",
        barmode="group",
        yaxis_title="Profit ($)",
        yaxis2_title="Incremental Profit ($)",
        xaxis_tickangle=-35,
        xaxis2_tickangle=-35,
        legend=dict(orientation="h", yanchor="bottom", y=-0.35, xanchor="center", x=0.25),
        margin=dict(b=120),
    )

    return nextmv.Asset(
        name="Financial Impact",
        content_type="json",
        visual=nextmv.Visual(
            visual_schema=nextmv.VisualSchema(value="plotly"),
            visual_type="custom-tab",
            label="Financial Impact",
            tab_order=3,
        ),
        content=[json.loads(fig.to_json())],
    )
