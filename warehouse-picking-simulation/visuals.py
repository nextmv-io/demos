import json

import nextmv
import plotly.graph_objects as go


def build_timeline_chart(history: list[dict], label="Simulation Timeline", tab_order=1) -> nextmv.Asset:
    steps = [h["step"] for h in history]
    completed = [h["orders_completed"] for h in history]
    pending = [h["orders_pending"] for h in history]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=steps, y=completed,
        mode="lines",
        name="Orders Completed",
        line={"color": "#2ecc71", "width": 2},
    ))
    fig.add_trace(go.Scatter(
        x=steps, y=pending,
        mode="lines",
        name="Orders Pending",
        line={"color": "#e74c3c", "width": 2},
    ))
    fig.update_layout(
        title="Order Queue Over Time",
        xaxis_title="Simulation Step",
        yaxis_title="Orders",
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "right", "x": 1},
        template="plotly_white",
    )

    return nextmv.Asset(
        name=label,
        content_type="json",
        visual=nextmv.Visual(
            visual_schema=nextmv.VisualSchema(value="plotly"),
            visual_type="custom-tab",
            label=label,
            tab_order=tab_order,
        ),
        content=[json.loads(fig.to_json())],
    )


def build_utilization_chart(picker_utilizations: list[dict], label="Picker Utilization", tab_order=2) -> nextmv.Asset:
    picker_ids = [f"Picker {p['picker_id'] + 1}" for p in picker_utilizations]
    utilizations = [round(p["utilization"] * 100, 1) for p in picker_utilizations]

    colors = ["#e74c3c" if u > 90 else "#f39c12" if u > 70 else "#2ecc71" for u in utilizations]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=picker_ids,
        y=utilizations,
        marker_color=colors,
        text=[f"{u}%" for u in utilizations],
        textposition="outside",
    ))
    fig.update_layout(
        title="Picker Utilization (%)",
        xaxis_title="Picker",
        yaxis_title="Utilization (%)",
        yaxis={"range": [0, 110]},
        template="plotly_white",
    )

    return nextmv.Asset(
        name=label,
        content_type="json",
        visual=nextmv.Visual(
            visual_schema=nextmv.VisualSchema(value="plotly"),
            visual_type="custom-tab",
            label=label,
            tab_order=tab_order,
        ),
        content=[json.loads(fig.to_json())],
    )
