import json
import nextmv
import plotly.graph_objects as go

CATEGORY_COLORS = {
    "electronics": "#636EFA",
    "books": "#EF553B",
    "clothing": "#00CC96",
    "home": "#AB63FA",
    "sports": "#FFA15A",
    "beauty": "#19D3F3",
    "toys": "#FF6692",
    "food": "#B6E880",
    "tools": "#FF97FF",
    "automotive": "#FECB52",
}

def _cat_color(category):
    return CATEGORY_COLORS.get(category, "#AAAAAA")


def recommendations_chart(recommendations, customer, tab_order=1) -> nextmv.Asset:
    """Horizontal bar chart: top recommendations ranked by composite score."""
    if not recommendations:
        fig = go.Figure()
        fig.update_layout(title="No recommendations generated")
        return _asset(fig, "Recommendations", tab_order)

    names = [f"{r['name'][:35]}…" if len(r['name']) > 35 else r['name'] for r in recommendations]
    scores = [r["composite_score"] for r in recommendations]
    colors = [_cat_color(r["category"]) for r in recommendations]
    prices = [r["price"] for r in recommendations]
    ratings = [r["rating"] for r in recommendations]
    categories = [r["category"] for r in recommendations]

    fig = go.Figure(
        go.Bar(
            x=scores,
            y=names,
            orientation="h",
            marker_color=colors,
            text=[f"${p:.0f}  ★{r:.1f}" for p, r in zip(prices, ratings)],
            textposition="outside",
            hovertemplate=(
                "<b>%{y}</b><br>"
                "Score: %{x:.3f}<br>"
                "Category: %{customdata[0]}<br>"
                "Price: $%{customdata[1]:.2f}<br>"
                "Rating: %{customdata[2]:.1f}"
                "<extra></extra>"
            ),
            customdata=list(zip(categories, prices, ratings)),
        )
    )
    fig.update_layout(
        title=f"Top Recommendations for {customer['id']} (Budget: ${customer['budget']})",
        xaxis_title="Composite Score",
        yaxis={"autorange": "reversed", "tickfont": {"size": 11}},
        xaxis={"range": [0, 1.15]},
        margin={"l": 240},
    )
    return _asset(fig, "Recommendations", tab_order)


def score_breakdown_chart(recommendations, tab_order=2) -> nextmv.Asset:
    """Stacked bar chart showing score component breakdown per recommendation."""
    if not recommendations:
        fig = go.Figure()
        fig.update_layout(title="No recommendations generated")
        return _asset(fig, "Score Breakdown", tab_order)

    names = [r["name"][:28] + "…" if len(r["name"]) > 28 else r["name"] for r in recommendations]
    components = ["category", "brand", "price", "rating"]
    component_labels = {"category": "Category Match", "brand": "Brand Affinity", "price": "Price Fit", "rating": "Rating"}
    comp_colors = {"category": "#636EFA", "brand": "#00CC96", "price": "#FFA15A", "rating": "#EF553B"}

    fig = go.Figure()
    for comp in components:
        fig.add_trace(
            go.Bar(
                name=component_labels[comp],
                x=[r["score_components"][comp] for r in recommendations],
                y=names,
                orientation="h",
                marker_color=comp_colors[comp],
                hovertemplate=f"<b>{component_labels[comp]}</b>: %{{x:.3f}}<extra></extra>",
            )
        )

    fig.update_layout(
        barmode="stack",
        title="Score Breakdown by Component",
        xaxis_title="Contribution to Composite Score",
        yaxis={"autorange": "reversed", "tickfont": {"size": 11}},
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02},
        margin={"l": 220},
    )
    return _asset(fig, "Score Breakdown", tab_order)


def catalog_scatter(products, recommendations, customer, tab_order=3) -> nextmv.Asset:
    """Scatter: all products by price vs rating; recommended ones highlighted."""
    rec_ids = {r["id"] for r in recommendations}
    preferred_cats = set(customer.get("preferred_categories", []))
    budget = customer["budget"]

    in_stock = [p for p in products if p.get("in_stock", True)]
    rec_prods = [p for p in in_stock if p["id"] in rec_ids]
    other_prods = [p for p in in_stock if p["id"] not in rec_ids]

    fig = go.Figure()

    # Non-recommended products
    if other_prods:
        fig.add_trace(
            go.Scatter(
                x=[p["price"] for p in other_prods],
                y=[p.get("rating", 0) for p in other_prods],
                mode="markers",
                marker=dict(color="#CCCCCC", size=7, opacity=0.6),
                name="Not Recommended",
                hovertemplate="<b>%{customdata[0]}</b><br>$%{x}<br>★%{y}<br>%{customdata[1]}<extra></extra>",
                customdata=[(p["name"], p["category"]) for p in other_prods],
            )
        )

    # Recommended products — colored by category
    if rec_prods:
        fig.add_trace(
            go.Scatter(
                x=[p["price"] for p in rec_prods],
                y=[p.get("rating", 0) for p in rec_prods],
                mode="markers+text",
                marker=dict(
                    color=[_cat_color(p["category"]) for p in rec_prods],
                    size=14,
                    line=dict(width=2, color="white"),
                ),
                text=[str(i + 1) for i in range(len(rec_prods))],
                textposition="middle center",
                textfont=dict(color="white", size=9),
                name="Recommended",
                hovertemplate="<b>%{customdata[0]}</b><br>$%{x}<br>★%{y}<br>%{customdata[1]}<extra></extra>",
                customdata=[(p["name"], p["category"]) for p in rec_prods],
            )
        )

    # Budget line
    fig.add_vline(x=budget, line_color="red", line_dash="dash", annotation_text=f"Budget ${budget}", annotation_position="top right")

    fig.update_layout(
        title="Product Catalog — Price vs. Rating (numbered = recommended)",
        xaxis_title="Price ($)",
        yaxis_title="Rating (★)",
        yaxis={"range": [0, 5.3]},
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02},
    )
    return _asset(fig, "Catalog Overview", tab_order)


def _asset(fig, label, tab_order) -> nextmv.Asset:
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
