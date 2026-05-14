import json
import nextmv
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def build_input_chart(data, label="Baseline Portfolio", tab_order=1) -> nextmv.Asset:
    products = data["products"]
    names = [p["name"] for p in products]
    product_ids = [p["id"] for p in products]
    volumes = [p["baseline_volume_mm"] for p in products]
    apys = [p["baseline_apy_bps"] / 100 for p in products]

    elasticity_raw = data["elasticity_matrix"]
    z_vals = []
    for pid_i in product_ids:
        row = [elasticity_raw.get(pid_i, {}).get(pid_j, 0.0) for pid_j in product_ids]
        z_vals.append(row)

    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=("Baseline Volume & APY by Product", "Price Elasticity Matrix ($MM per bps)"),
        column_widths=[0.48, 0.52],
    )

    fig.add_trace(
        go.Bar(
            x=names,
            y=volumes,
            name="Volume ($MM)",
            marker_color="#4C72B0",
            text=[f"${v:,.0f}MM<br>{a:.2f}% APY" for v, a in zip(volumes, apys)],
            textposition="outside",
            hovertemplate="<b>%{x}</b><br>Volume: $%{y:,.0f}MM<br>APY: " +
                          "<br>".join([f"{a:.2f}%" for a in apys]).split("<br>")[0] +
                          "<extra></extra>",
            customdata=[[a] for a in apys],
        ),
        row=1, col=1,
    )

    # Re-add with proper hover using customdata
    fig.data[-1].hovertemplate = (
        "<b>%{x}</b><br>Volume: $%{y:,.0f}MM<br>APY: %{customdata[0]:.2f}%<extra></extra>"
    )

    fig.add_trace(
        go.Heatmap(
            z=z_vals,
            x=names,
            y=names,
            colorscale=[
                [0.0, "#d73027"],
                [0.5, "#f7f7f7"],
                [1.0, "#1a9850"],
            ],
            zmid=0,
            text=[[f"{v:.1f}" for v in row] for row in z_vals],
            texttemplate="%{text}",
            hovertemplate=(
                "<b>%{y}</b> volume response<br>"
                "to <b>%{x}</b> rate change<br>"
                "Elasticity: %{z:.2f} $MM/bps<extra></extra>"
            ),
            name="",
            showscale=True,
            colorbar=dict(title="$MM/bps", x=1.02, len=0.8),
        ),
        row=1, col=2,
    )

    fig.update_yaxes(title_text="Volume ($MM)", row=1, col=1)
    fig.update_xaxes(tickangle=-25, row=1, col=1)
    fig.update_xaxes(tickangle=-25, row=1, col=2)
    fig.update_yaxes(tickangle=0, row=1, col=2)
    fig.update_layout(
        title="Baseline Deposit Portfolio",
        height=460,
        showlegend=False,
        margin=dict(t=80, b=80, l=60, r=80),
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


def build_solution_chart(solution, data, label="Scenario Results", tab_order=2) -> nextmv.Asset:
    products = solution["products"]
    names = [p["name"] for p in products]
    deltas = [p["delta_volume_mm"] for p in products]
    baseline_vols = [p["baseline_volume_mm"] for p in products]
    new_vols = [p["new_volume_mm"] for p in products]
    baseline_apys = [p["baseline_apy_bps"] / 100 for p in products]
    new_apys = [p["new_apy_bps"] / 100 for p in products]
    delta_apys = [p["delta_apy_bps"] for p in products]

    summary = solution["portfolio_summary"]
    nim = summary["nim_impact_bps"]
    total_delta = summary["total_delta_volume_mm"]
    delta_spread = summary["delta_spread_income_mm"]
    nim_warning = solution.get("nim_warning", False)

    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=(
            "Volume Change by Product ($MM)",
            "Before vs. After: Volume & APY",
        ),
        column_widths=[0.45, 0.55],
    )

    bar_colors = ["#2ca02c" if d >= 0 else "#d62728" for d in deltas]
    fig.add_trace(
        go.Bar(
            x=names,
            y=deltas,
            name="Volume Change",
            marker_color=bar_colors,
            text=[f"{'+' if d >= 0 else ''}{d:,.1f}" for d in deltas],
            textposition="outside",
            customdata=[[delta_apys[i]] for i in range(len(names))],
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Volume change: %{y:+,.1f} $MM<br>"
                "Rate change: %{customdata[0]:+d} bps<extra></extra>"
            ),
        ),
        row=1, col=1,
    )

    fig.add_trace(
        go.Bar(
            x=names,
            y=baseline_vols,
            name="Baseline",
            marker_color="#AEC7E8",
            text=[f"{a:.2f}%" for a in baseline_apys],
            textposition="inside",
            textfont=dict(color="black", size=11),
            hovertemplate="<b>%{x}</b> Baseline<br>Volume: $%{y:,.0f}MM<br>APY: %{text}<extra></extra>",
        ),
        row=1, col=2,
    )
    fig.add_trace(
        go.Bar(
            x=names,
            y=new_vols,
            name="Post-Scenario",
            marker_color="#1F77B4",
            text=[f"{a:.2f}%" for a in new_apys],
            textposition="inside",
            textfont=dict(color="white", size=11),
            hovertemplate="<b>%{x}</b> Post-Scenario<br>Volume: $%{y:,.0f}MM<br>APY: %{text}<extra></extra>",
        ),
        row=1, col=2,
    )

    nim_color = "#d62728" if nim_warning else "#2ca02c" if nim >= 0 else "#ff7f0e"
    subtitle = (
        f"NIM: <span style='color:{nim_color}'>{nim:+.2f} bps</span> &nbsp;|&nbsp; "
        f"Volume: {total_delta:+,.0f} $MM &nbsp;|&nbsp; "
        f"Spread income: {delta_spread:+.1f} $MM"
    )

    fig.update_yaxes(title_text="Volume Change ($MM)", row=1, col=1)
    fig.update_yaxes(title_text="Volume ($MM)", row=1, col=2)
    fig.update_xaxes(tickangle=-25)
    fig.update_layout(
        title=dict(text=f"Rate Scenario Results<br><sup>{subtitle}</sup>"),
        height=460,
        barmode="group",
        legend=dict(orientation="h", yanchor="bottom", y=1.04, xanchor="right", x=1),
        margin=dict(t=100, b=80, l=60, r=40),
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
