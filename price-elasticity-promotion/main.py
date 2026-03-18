import math
import nextmv
import numpy as np
from ortools.sat.python import cp_model

from visuals import build_elasticity_chart, build_promotion_chart, build_profit_chart

SCALE = 1000  # integer scaling factor for CP-SAT


def estimate_elasticity(price_history: list[dict]) -> float:
    """Fit price elasticity via log-log OLS: log(demand) = a + e * log(price)."""
    if len(price_history) < 2:
        return -1.0

    prices = np.array([p["price"] for p in price_history], dtype=float)
    demands = np.array([p["demand"] for p in price_history], dtype=float)

    # Drop any zero/negative values
    mask = (prices > 0) & (demands > 0)
    if mask.sum() < 2:
        return -1.0

    log_p = np.log(prices[mask])
    log_d = np.log(demands[mask])

    x_mean = log_p.mean()
    y_mean = log_d.mean()
    numerator = np.sum((log_p - x_mean) * (log_d - y_mean))
    denominator = np.sum((log_p - x_mean) ** 2)

    if abs(denominator) < 1e-12:
        return -1.0

    return float(numerator / denominator)


def expected_demand(base_demand: float, base_price: float, promo_price: float, elasticity: float) -> float:
    """Estimate demand at promo_price using constant-elasticity demand model."""
    if base_price <= 0 or promo_price <= 0:
        return base_demand
    ratio = promo_price / base_price
    return base_demand * (ratio ** elasticity)


def build_product_levels(product: dict, elasticity: float, discount_levels: list[float]) -> list[dict]:
    """Compute metrics for each discount level for a product."""
    base_price = product["base_price"]
    cost = product["cost"]
    base_dem = product["base_demand"]

    levels = []
    for disc in discount_levels:
        promo_price = base_price * (1 - disc)
        exp_dem = expected_demand(base_dem, base_price, promo_price, elasticity)
        revenue = promo_price * exp_dem
        profit = (promo_price - cost) * exp_dem
        promo_cost = disc * base_price * exp_dem  # total dollar discount given away

        levels.append({
            "discount": disc,
            "promo_price": promo_price,
            "expected_demand": exp_dem,
            "revenue": revenue,
            "profit": profit,
            "promo_cost": promo_cost,
        })
    return levels


def main():
    manifest = nextmv.Manifest.from_yaml(".")
    options = manifest.extract_options()

    inp = nextmv.load(options=options, path=options.input)
    data = inp.data

    products = data["products"]
    promotion_budget = float(data.get("promotion_budget", 0))

    min_disc = options.min_discount_pct / 100.0
    max_disc = options.max_discount_pct / 100.0
    step_disc = options.discount_step_pct / 100.0
    objective_type = options.objective
    max_on_promo = options.max_products_on_promotion
    solve_seconds = options.solve_duration

    # Build discount level grid: always include 0% (no promotion)
    discount_levels = [0.0]
    d = min_disc
    while d <= max_disc + 1e-9:
        discount_levels.append(round(d, 4))
        d = round(d + step_disc, 4)
    discount_levels = sorted(set(discount_levels))

    nextmv.log(f"Discount levels: {[f'{int(d*100)}%' for d in discount_levels]}")

    # Step 1: Estimate elasticities from price history
    product_data = []
    for product in products:
        pid = product["id"]
        history = product.get("price_history", [])
        e = estimate_elasticity(history)
        nextmv.log(f"  {product['name']}: elasticity = {e:.3f}")
        levels = build_product_levels(product, e, discount_levels)
        product_data.append({
            "id": pid,
            "name": product["name"],
            "base_price": product["base_price"],
            "cost": product["cost"],
            "base_demand": product["base_demand"],
            "elasticity": e,
            "levels": levels,
        })

    # Step 2: Formulate promotion optimization with OR-Tools CP-SAT
    model = cp_model.CpModel()
    n_prod = len(product_data)
    n_lev = len(discount_levels)

    # x[i][k] = 1 if product i receives discount level k
    x = [[model.NewBoolVar(f"x_{i}_{k}") for k in range(n_lev)] for i in range(n_prod)]

    # Each product gets exactly one discount level
    for i in range(n_prod):
        model.AddExactlyOne(x[i])

    # Budget constraint
    budget_scaled = int(promotion_budget * SCALE)
    model.Add(
        sum(x[i][k] * int(product_data[i]["levels"][k]["promo_cost"] * SCALE)
            for i in range(n_prod) for k in range(n_lev)) <= budget_scaled
    )

    # Optional max-products-on-promotion constraint
    if 0 < max_on_promo < n_prod:
        on_promo = []
        for i in range(n_prod):
            is_on_promo = model.NewBoolVar(f"on_promo_{i}")
            # is_on_promo = 1 iff product is NOT at level 0 (no discount)
            model.Add(is_on_promo + x[i][0] == 1)
            on_promo.append(is_on_promo)
        model.Add(sum(on_promo) <= max_on_promo)

    # Objective
    def obj_value(pd, level):
        if objective_type == "profit":
            return level["profit"]
        elif objective_type == "revenue":
            return level["revenue"]
        else:  # units
            return level["expected_demand"]

    model.Maximize(
        sum(x[i][k] * int(obj_value(product_data[i], product_data[i]["levels"][k]) * SCALE)
            for i in range(n_prod) for k in range(n_lev))
    )

    # Solve
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = float(solve_seconds)
    status = solver.Solve(model)
    nextmv.log(f"Solver status: {solver.StatusName(status)}")

    # Extract solution
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        solve_status = "optimal" if status == cp_model.OPTIMAL else "suboptimal"
        assignments = []
        total_profit = 0.0
        total_revenue = 0.0
        total_promo_cost = 0.0
        total_units = 0.0

        for i, pd in enumerate(product_data):
            for k in range(n_lev):
                if solver.Value(x[i][k]) == 1:
                    lev = pd["levels"][k]
                    assignments.append({
                        "product_id": pd["id"],
                        "product_name": pd["name"],
                        "base_price": round(pd["base_price"], 2),
                        "promo_price": round(lev["promo_price"], 2),
                        "discount_pct": round(lev["discount"] * 100, 1),
                        "elasticity": round(pd["elasticity"], 3),
                        "base_demand": round(pd["base_demand"], 1),
                        "expected_demand": round(lev["expected_demand"], 1),
                        "demand_lift_pct": round((lev["expected_demand"] / pd["base_demand"] - 1) * 100, 1),
                        "revenue": round(lev["revenue"], 2),
                        "profit": round(lev["profit"], 2),
                        "promo_cost": round(lev["promo_cost"], 2),
                    })
                    total_profit += lev["profit"]
                    total_revenue += lev["revenue"]
                    total_promo_cost += lev["promo_cost"]
                    total_units += lev["expected_demand"]
                    break

        baseline_profit = sum(
            (pd["base_price"] - pd["cost"]) * pd["base_demand"] for pd in product_data
        )
        baseline_revenue = sum(pd["base_price"] * pd["base_demand"] for pd in product_data)

        result_value = (
            total_profit if objective_type == "profit"
            else total_revenue if objective_type == "revenue"
            else total_units
        )
        budget_used_pct = round(total_promo_cost / promotion_budget * 100, 1) if promotion_budget > 0 else 0.0

    else:
        solve_status = "infeasible"
        assignments = []
        total_profit = total_revenue = total_promo_cost = total_units = 0.0
        baseline_profit = baseline_revenue = result_value = 0.0
        budget_used_pct = 0.0

    nextmv.redirect_stdout()

    # Build visualizations
    chart1 = build_elasticity_chart(product_data)
    chart2 = build_promotion_chart(assignments, product_data)
    chart3 = build_profit_chart(assignments, product_data)

    output = nextmv.Output(
        solution={
            "assignments": assignments,
            "summary": {
                "total_revenue": round(total_revenue, 2),
                "total_profit": round(total_profit, 2),
                "total_promo_cost": round(total_promo_cost, 2),
                "total_expected_units": round(total_units, 1),
                "budget_used_pct": budget_used_pct,
                "profit_lift_vs_baseline": round(total_profit - baseline_profit, 2),
                "revenue_lift_vs_baseline": round(total_revenue - baseline_revenue, 2),
            },
        },
        assets=[chart1, chart2, chart3],
        metrics={
            "status": solve_status,
            "result_value": round(result_value, 2),
            "total_profit": round(total_profit, 2),
            "total_revenue": round(total_revenue, 2),
            "total_promo_cost": round(total_promo_cost, 2),
            "profit_lift_vs_baseline": round(total_profit - baseline_profit, 2),
            "products_on_promotion": sum(1 for a in assignments if a["discount_pct"] > 0),
            "avg_elasticity": round(float(np.mean([pd["elasticity"] for pd in product_data])), 3),
        },
    )

    nextmv.write(output, path=options.output)


if __name__ == "__main__":
    main()
