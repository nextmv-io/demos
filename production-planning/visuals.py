import json

import nextmv
import plotly.graph_objects as go


def production_chart(
    products: list,
    periods: list,
    production: list,
    tab_order: int = 1,
) -> nextmv.Asset:
    """Stacked bar chart showing production quantity by product per period."""
    fig = go.Figure()

    for p, product in enumerate(products):
        fig.add_trace(
            go.Bar(
                name=product,
                x=periods,
                y=production[p],
            )
        )

    fig.update_layout(
        title="Production Plan by Period",
        xaxis_title="Period",
        yaxis_title="Units Produced",
        barmode="stack",
        legend_title="Product",
    )

    return nextmv.Asset(
        name="Production Plan",
        content_type="json",
        visual=nextmv.Visual(
            visual_schema=nextmv.VisualSchema(value="plotly"),
            visual_type="custom-tab",
            label="Production Plan",
            tab_order=tab_order,
        ),
        content=[json.loads(fig.to_json())],
    )


def inventory_chart(
    products: list,
    periods: list,
    inventory: list,
    tab_order: int = 2,
) -> nextmv.Asset:
    """Line chart showing end-of-period inventory levels by product."""
    fig = go.Figure()

    for p, product in enumerate(products):
        fig.add_trace(
            go.Scatter(
                name=product,
                x=periods,
                y=inventory[p],
                mode="lines+markers",
            )
        )

    fig.update_layout(
        title="Inventory Levels by Period",
        xaxis_title="Period",
        yaxis_title="Units in Inventory",
        legend_title="Product",
    )

    return nextmv.Asset(
        name="Inventory Levels",
        content_type="json",
        visual=nextmv.Visual(
            visual_schema=nextmv.VisualSchema(value="plotly"),
            visual_type="custom-tab",
            label="Inventory Levels",
            tab_order=tab_order,
        ),
        content=[json.loads(fig.to_json())],
    )
