"""Plotly visualisations for the demand-forecast-allocation flow."""

import json

import nextmv
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def forecast_chart(forecasts: list, historical_sales: list, tab_order: int = 1) -> nextmv.Asset:
    """
    Two-panel chart:
      • Left  — historical sales per store (line chart)
      • Right — forecasted demand for the next period (bar chart)
    """
    stores_seen = sorted({r["store_id"] for r in historical_sales})
    store_history: dict[str, dict] = {
        sid: {"periods": [], "units": [], "name": sid} for sid in stores_seen
    }
    for r in historical_sales:
        store_history[r["store_id"]]["periods"].append(r["period"])
        store_history[r["store_id"]]["units"].append(r["units_sold"])
    name_map = {f["store_id"]: f["store_name"] for f in forecasts}
    for sid in store_history:
        store_history[sid]["name"] = name_map.get(sid, sid)

    fig = make_subplots(
        rows=1,
        cols=2,
        subplot_titles=("Historical Sales by Store", "Forecasted Demand — Next Period"),
        column_widths=[0.6, 0.4],
    )

    colors = [
        "#4e79a7", "#f28e2b", "#e15759", "#76b7b2",
        "#59a14f", "#edc948", "#b07aa1", "#ff9da7",
        "#9c755f", "#bab0ac",
    ]

    for i, sid in enumerate(stores_seen):
        h = store_history[sid]
        color = colors[i % len(colors)]
        periods_sorted = sorted(zip(h["periods"], h["units"]))
        xs, ys = zip(*periods_sorted) if periods_sorted else ([], [])
        fig.add_trace(
            go.Scatter(
                x=list(xs),
                y=list(ys),
                mode="lines+markers",
                name=h["name"],
                line=dict(color=color, width=2),
                marker=dict(size=5),
                legendgroup=sid,
            ),
            row=1, col=1,
        )

    forecast_names = [f["store_name"] for f in forecasts]
    forecast_values = [f["forecasted_demand"] for f in forecasts]
    bar_colors = [colors[stores_seen.index(f["store_id"]) % len(colors)] for f in forecasts]

    fig.add_trace(
        go.Bar(
            x=forecast_names,
            y=forecast_values,
            marker_color=bar_colors,
            name="Forecast",
            showlegend=False,
            text=forecast_values,
            textposition="outside",
        ),
        row=1, col=2,
    )

    fig.update_xaxes(title_text="Period", row=1, col=1)
    fig.update_yaxes(title_text="Units Sold", row=1, col=1)
    fig.update_xaxes(title_text="Store", row=1, col=2)
    fig.update_yaxes(title_text="Forecasted Units", row=1, col=2)
    fig.update_layout(
        title="Demand Forecast",
        height=500,
        legend=dict(orientation="v", x=1.02, y=1),
    )

    return nextmv.Asset(
        name="Demand Forecast",
        content_type="json",
        visual=nextmv.Visual(
            visual_schema=nextmv.VisualSchema(value="plotly"),
            visual_type="custom-tab",
            label="Demand Forecast",
            tab_order=tab_order,
        ),
        content=[json.loads(fig.to_json())],
    )


def allocation_sankey(allocations: list, tab_order: int = 2) -> nextmv.Asset:
    """
    Sankey diagram using warehouse_name / store_name fields returned by
    the inventory-allocation sub-app.
    """
    # Preserve insertion order for node positions.
    wh_names = list(dict.fromkeys(a["warehouse_name"] for a in allocations))
    st_names = list(dict.fromkeys(a["store_name"] for a in allocations))
    labels = wh_names + st_names

    wh_idx = {name: i for i, name in enumerate(wh_names)}
    st_idx = {name: len(wh_names) + i for i, name in enumerate(st_names)}

    sources = [wh_idx[a["warehouse_name"]] for a in allocations]
    targets = [st_idx[a["store_name"]] for a in allocations]
    values = [a["units"] for a in allocations]

    node_colors = ["#4e79a7"] * len(wh_names) + ["#f28e2b"] * len(st_names)

    fig = go.Figure(
        go.Sankey(
            node=dict(
                pad=15,
                thickness=20,
                line=dict(color="black", width=0.5),
                label=labels,
                color=node_colors,
            ),
            link=dict(source=sources, target=targets, value=values),
        )
    )
    fig.update_layout(
        title="Inventory Allocation: Warehouses → Stores",
        font_size=12,
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
