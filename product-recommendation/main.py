"""Content-based product recommendation engine with configurable scoring weights."""

import numpy as np
import nextmv

from visuals import recommendations_chart, score_breakdown_chart, catalog_scatter


def score_product(product, customer, w_cat, w_brand, w_price, w_rating):
    """Return scored product dict or None if filtered out."""
    # Hard filters
    if not product.get("in_stock", True):
        return None
    if product["price"] > customer["budget"]:
        return None
    if product["id"] in customer.get("previously_purchased", []):
        return None

    budget = customer["budget"]
    price_sensitivity = customer.get("price_sensitivity", 0.5)

    # Category score: 1.0 if preferred, 0.5 if neutral, 0.1 if excluded
    preferred_cats = set(customer.get("preferred_categories", []))
    excluded_cats = set(customer.get("excluded_categories", []))
    if product["category"] in excluded_cats:
        return None
    cat_score = 1.0 if product["category"] in preferred_cats else 0.4

    # Brand score: 1.0 if preferred, 0.4 if neutral
    preferred_brands = set(customer.get("preferred_brands", []))
    brand_score = 1.0 if product["brand"] in preferred_brands else 0.4

    # Price score: lower price relative to budget = better when price_sensitive
    price_ratio = product["price"] / budget
    price_score = max(0.0, 1.0 - price_ratio * price_sensitivity)

    # Rating score: normalized 0–1
    rating_score = product.get("rating", 3.0) / 5.0

    # Normalize weights so they always sum correctly
    total_w = w_cat + w_brand + w_price + w_rating
    if total_w == 0:
        total_w = 1.0

    composite = (
        w_cat * cat_score
        + w_brand * brand_score
        + w_price * price_score
        + w_rating * rating_score
    ) / total_w

    return {
        "id": product["id"],
        "name": product["name"],
        "category": product["category"],
        "brand": product["brand"],
        "price": product["price"],
        "rating": product.get("rating", 0.0),
        "composite_score": round(composite, 4),
        "category_score": round(cat_score, 4),
        "brand_score": round(brand_score, 4),
        "price_score": round(price_score, 4),
        "rating_score": round(rating_score, 4),
        "score_components": {
            "category": round(w_cat * cat_score / total_w, 4),
            "brand": round(w_brand * brand_score / total_w, 4),
            "price": round(w_price * price_score / total_w, 4),
            "rating": round(w_rating * rating_score / total_w, 4),
        },
    }


def select_diverse(candidates, n):
    """Greedy diversity selection: after each pick, penalize same-category candidates."""
    selected = []
    category_penalty = {}
    remaining = list(candidates)

    while remaining and len(selected) < n:
        # Apply penalties
        for c in remaining:
            penalty = category_penalty.get(c["category"], 0)
            c["_adjusted"] = c["composite_score"] * (0.7 ** penalty)

        remaining.sort(key=lambda x: x["_adjusted"], reverse=True)
        pick = remaining.pop(0)
        selected.append(pick)
        category_penalty[pick["category"]] = category_penalty.get(pick["category"], 0) + 1

    return selected


def main():
    manifest = nextmv.Manifest.from_yaml(".")
    options = manifest.extract_options()

    input_data = nextmv.load(options=options, path=options.input)
    data = input_data.data

    customer = data["customer"]
    products = data["products"]

    nextmv.log(f"Customer: {customer['id']} | Budget: ${customer['budget']} | Products: {len(products)}")
    nextmv.log(
        f"Weights — category: {options.category_weight}, brand: {options.brand_weight}, "
        f"price: {options.price_weight}, rating: {options.rating_weight}"
    )

    # Score all products
    candidates = []
    for product in products:
        scored = score_product(
            product, customer,
            options.category_weight,
            options.brand_weight,
            options.price_weight,
            options.rating_weight,
        )
        if scored is not None:
            candidates.append(scored)

    nextmv.log(f"Eligible products: {len(candidates)} / {len(products)}")

    # Sort by composite score
    candidates.sort(key=lambda x: x["composite_score"], reverse=True)

    # Select with or without diversity enforcement
    if options.diversity:
        recommendations = select_diverse(candidates, options.max_recommendations)
    else:
        recommendations = candidates[: options.max_recommendations]

    # Clean up internal field
    for r in recommendations:
        r.pop("_adjusted", None)

    # Metrics
    avg_score = float(np.mean([r["composite_score"] for r in recommendations])) if recommendations else 0.0
    avg_price = float(np.mean([r["price"] for r in recommendations])) if recommendations else 0.0
    avg_rating = float(np.mean([r["rating"] for r in recommendations])) if recommendations else 0.0
    categories_covered = len({r["category"] for r in recommendations})
    preferred_cats = set(customer.get("preferred_categories", []))
    pref_cat_rate = (
        sum(1 for r in recommendations if r["category"] in preferred_cats) / len(recommendations)
        if recommendations else 0.0
    )

    nextmv.log(
        f"Recommendations: {len(recommendations)} | Avg score: {avg_score:.3f} | "
        f"Categories: {categories_covered} | Avg price: ${avg_price:.2f}"
    )

    chart1 = recommendations_chart(recommendations, customer, tab_order=1)
    chart2 = score_breakdown_chart(recommendations, tab_order=2)
    chart3 = catalog_scatter(products, recommendations, customer, tab_order=3)

    output = nextmv.Output(
        solution={
            "recommendations": recommendations,
            "customer_id": customer["id"],
            "filters_applied": {
                "budget": customer["budget"],
                "excluded_categories": customer.get("excluded_categories", []),
                "previously_purchased_excluded": len(customer.get("previously_purchased", [])),
            },
        },
        assets=[chart1, chart2, chart3],
        metrics={
            "result_value": round(avg_score, 4),
            "recommendations_count": len(recommendations),
            "avg_score": round(avg_score, 4),
            "avg_price": round(avg_price, 2),
            "avg_rating": round(avg_rating, 2),
            "categories_covered": categories_covered,
            "preferred_category_rate": round(pref_cat_rate, 4),
            "eligible_products": len(candidates),
        },
    )
    nextmv.write(output)


if __name__ == "__main__":
    main()
