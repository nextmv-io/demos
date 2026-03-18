import json

import nextmv
import plotly.graph_objects as go


def score_distribution_chart(decisions, label="Credit Score Distribution", tab_order=1) -> nextmv.Asset:
    approved = [d["approval_score"] for d in decisions if d["decision"] == "approved"]
    review = [d["approval_score"] for d in decisions if d["decision"] == "review"]
    denied = [d["approval_score"] for d in decisions if d["decision"] == "denied"]

    fig = go.Figure()
    if approved:
        fig.add_trace(go.Histogram(x=approved, name="Approved", marker_color="#2ecc71", opacity=0.75, nbinsx=20))
    if review:
        fig.add_trace(go.Histogram(x=review, name="Review", marker_color="#f39c12", opacity=0.75, nbinsx=20))
    if denied:
        fig.add_trace(go.Histogram(x=denied, name="Denied", marker_color="#e74c3c", opacity=0.75, nbinsx=20))

    fig.update_layout(
        title=label,
        xaxis_title="Approval Score (probability of no default)",
        yaxis_title="Number of Applicants",
        barmode="overlay",
        legend_title="Decision",
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


def feature_importance_chart(feature_names, importances, model_type, label="Feature Importance", tab_order=2) -> nextmv.Asset:
    sorted_pairs = sorted(zip(feature_names, importances), key=lambda x: x[1])
    names = [p[0] for p in sorted_pairs]
    values = [p[1] for p in sorted_pairs]

    fig = go.Figure(
        go.Bar(
            x=values,
            y=names,
            orientation="h",
            marker_color="#3498db",
        )
    )
    fig.update_layout(
        title=f"{label} — {model_type.replace('_', ' ').title()}",
        xaxis_title="Relative Importance",
        yaxis_title="Feature",
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
