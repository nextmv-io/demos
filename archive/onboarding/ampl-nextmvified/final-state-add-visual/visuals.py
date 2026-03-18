# Disable Python bytecode generation (__pycache__)
import os
import sys

os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
sys.dont_write_bytecode = True

import json
from typing import Any

import nextmv
import pandas as pd
import plotly.graph_objects as go


def create_power_system_dashboard(result: dict[str, Any]) -> list[nextmv.Asset]:
    """Create Nextmv assets with Plotly visualizations for power system optimization results."""

    # Extract data from result
    thermal_info = result["vars"]["thermal_info"]
    renewable_info = result["vars"]["renewable_info"]

    assets = []

    # 1. Generation Mix Over Time
    fig_mix = create_generation_mix_chart(thermal_info, renewable_info)
    fig_mix_json = fig_mix.to_json()

    assets.append(
        nextmv.Asset(
            name="Generation Mix Over Time",
            content_type="json",
            visual=nextmv.Visual(
                visual_schema=nextmv.VisualSchema.PLOTLY,
                visual_type="custom-tab",
                label="Generation Mix",
            ),
            content=[json.loads(fig_mix_json)],
        )
    )

    # 2. Unit Commitment Status
    fig_commitment = create_unit_commitment_chart(thermal_info)
    fig_commitment_json = fig_commitment.to_json()

    assets.append(
        nextmv.Asset(
            name="Unit Commitment Status",
            content_type="json",
            visual=nextmv.Visual(
                visual_schema=nextmv.VisualSchema.PLOTLY,
                visual_type="custom-tab",
                label="Unit Status",
            ),
            content=[json.loads(fig_commitment_json)],
        )
    )

    return assets


def create_unit_commitment_chart(thermal_info: pd.DataFrame) -> go.Figure:
    """Create unit commitment status heatmap."""

    df = thermal_info.reset_index()

    # Create pivot table for heatmap
    pivot_ug = df.pivot(index="index0", columns="index1", values="ug")

    fig = go.Figure(
        data=go.Heatmap(
            z=pivot_ug.values,
            x=pivot_ug.columns,
            y=pivot_ug.index,
            colorscale=[
                [0, "red"],
                [1, "green"],
            ],  # Binary colorscale: red=off, green=on
            zmin=0,
            zmax=1,
            hoverongaps=False,
            hovertemplate="Unit: %{y}<br>Time: %{x}<br>Status: %{z} (%{z:.0f})<extra></extra>",
            colorbar=dict(title="Unit Status", tickvals=[0, 1], ticktext=["Off", "On"]),
        )
    )

    fig.update_layout(
        title="Unit Commitment Status (Binary: Red=Off, Green=On)",
        xaxis_title="Time Period",
        yaxis_title="Thermal Units",
        height=500,
        width=800,
        font=dict(size=12),
    )

    return fig


def create_generation_mix_chart(
    thermal_info: pd.DataFrame, renewable_info: pd.DataFrame
) -> go.Figure:
    """Create stacked area chart showing generation mix over time."""

    thermal_df = thermal_info.reset_index()
    renewable_df = renewable_info.reset_index()

    # Aggregate by time period
    thermal_by_time = thermal_df.groupby("index1")["pg"].sum().reset_index()
    renewable_by_time = renewable_df.groupby("index1")["pw"].sum().reset_index()

    # Merge data
    merged = pd.merge(
        thermal_by_time, renewable_by_time, on="index1", how="outer"
    ).fillna(0)

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=merged["index1"],
            y=merged["pg"],
            fill="tozeroy",
            mode="none",
            name="Thermal Generation",
            fillcolor="rgba(255, 100, 100, 0.8)",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=merged["index1"],
            y=merged["pg"] + merged["pw"],
            fill="tonexty",
            mode="none",
            name="Renewable Generation",
            fillcolor="rgba(100, 255, 100, 0.8)",
        )
    )

    fig.update_layout(
        title="Power Generation Mix Over Time",
        xaxis_title="Time Period",
        yaxis_title="Power Generation (MW)",
        height=500,
        width=800,
        font=dict(size=12),
        legend=dict(x=0.02, y=0.98),
    )

    return fig
