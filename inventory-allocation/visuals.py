import json

import nextmv
import plotly.graph_objects as go


def allocation_chart(allocations, num_warehouses, num_stores, tab_order=1) -> nextmv.Asset:
    """Sankey diagram showing unit flow from warehouses to stores."""

    W = num_warehouses
    labels = [f"Warehouse {w}" for w in range(W)] + [f"Store {s}" for s in range(num_stores)]

    sources = [a["warehouse"] for a in allocations]
    targets = [W + a["store"] for a in allocations]
    units = [a["units"] for a in allocations]

    fig = go.Figure(
        go.Sankey(
            node=dict(
                pad=15,
                thickness=20,
                line=dict(color="black", width=0.5),
                label=labels,
                color=["#4e79a7"] * W + ["#f28e2b"] * num_stores,
            ),
            link=dict(
                source=sources,
                target=targets,
                value=units,
            ),
        )
    )

    fig.update_layout(
        title="Inventory Allocation: Warehouses to Stores",
        font_size=12,
        width=900,
        height=600,
    )

    return nextmv.Asset(
        name="Allocation Flow",
        content_type="json",
        visual=nextmv.Visual(
            visual_schema=nextmv.VisualSchema(value="plotly"),
            visual_type="custom-tab",
            label="Allocation Flow",
            tab_order=tab_order,
        ),
        content=[json.loads(fig.to_json())],
    )
