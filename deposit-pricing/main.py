import nextmv
import numpy as np
from visuals import build_input_chart, build_solution_chart


def main():
    manifest = nextmv.Manifest.from_yaml(".")
    options = manifest.extract_options()

    input_data = nextmv.load(options=options, path=options.input)
    data = input_data.data

    nextmv.redirect_stdout()

    products = data["products"]
    product_ids = [p["id"] for p in products]
    n = len(products)

    # Build elasticity matrix (n x n)
    # entry [i][j] = $MM volume change in product i per 1 bps change in product j's rate
    elasticity_raw = data["elasticity_matrix"]
    elasticity = np.zeros((n, n))
    for i, pid_i in enumerate(product_ids):
        for j, pid_j in enumerate(product_ids):
            elasticity[i][j] = elasticity_raw.get(pid_i, {}).get(pid_j, 0.0)

    # Rate scenario: delta in bps per product, driven by app.yaml sliders
    delta_rates = np.array([
        getattr(options, f"delta_{pid}_bps", None) or 0
        for pid in product_ids
    ])

    baseline_volumes = np.array([p["baseline_volume_mm"] for p in products])
    baseline_rates = np.array([p["baseline_apy_bps"] for p in products])

    # Core elasticity model: ΔQ_i = Σ_j (α_ij × Δrate_j)
    delta_volumes = elasticity @ delta_rates
    new_volumes = np.maximum(baseline_volumes + delta_volumes, 0.0)
    new_rates = baseline_rates + delta_rates

    funding_rate_bps = options.funding_rate_bps
    total_assets_mm = data.get("portfolio", {}).get("total_assets_mm", 10000)

    # Interest expense = Σ volume_i * rate_i  (volume in $MM, rate in bps → / 10000 → annual $MM)
    baseline_interest_mm = float(np.sum(baseline_volumes * baseline_rates) / 10000)
    new_interest_mm = float(np.sum(new_volumes * new_rates) / 10000)
    delta_interest_mm = new_interest_mm - baseline_interest_mm

    # Spread income = Σ volume_i * (funding_rate - deposit_rate) — net interest earned on deposits
    baseline_spread_mm = float(np.sum(baseline_volumes * (funding_rate_bps - baseline_rates)) / 10000)
    new_spread_mm = float(np.sum(new_volumes * (funding_rate_bps - new_rates)) / 10000)
    delta_spread_mm = new_spread_mm - baseline_spread_mm

    # NIM impact in bps = delta_spread_income / total_assets * 10000
    nim_impact_bps = (delta_spread_mm / total_assets_mm) * 10000

    min_nim = getattr(options, "min_nim_impact_bps", -2.0)
    nim_warning = nim_impact_bps < min_nim

    product_results = []
    for i, p in enumerate(products):
        bvol = float(baseline_volumes[i])
        dvol = float(delta_volumes[i])
        nvol = float(new_volumes[i])
        product_results.append({
            "id": p["id"],
            "name": p["name"],
            "baseline_apy_bps": int(baseline_rates[i]),
            "new_apy_bps": int(new_rates[i]),
            "delta_apy_bps": int(delta_rates[i]),
            "baseline_volume_mm": round(bvol, 2),
            "new_volume_mm": round(nvol, 2),
            "delta_volume_mm": round(dvol, 2),
            "delta_volume_pct": round(dvol / bvol * 100, 2) if bvol > 0 else 0.0,
            "baseline_interest_expense_mm": round(bvol * float(baseline_rates[i]) / 10000, 3),
            "new_interest_expense_mm": round(nvol * float(new_rates[i]) / 10000, 3),
        })

    total_baseline_vol = float(np.sum(baseline_volumes))
    total_new_vol = float(np.sum(new_volumes))
    vw_baseline_apy = float(np.sum(baseline_volumes * baseline_rates) / total_baseline_vol) if total_baseline_vol > 0 else 0.0
    vw_new_apy = float(np.sum(new_volumes * new_rates) / total_new_vol) if total_new_vol > 0 else 0.0

    solution = {
        "nim_warning": nim_warning,
        "products": product_results,
        "portfolio_summary": {
            "total_baseline_volume_mm": round(total_baseline_vol, 2),
            "total_new_volume_mm": round(total_new_vol, 2),
            "total_delta_volume_mm": round(float(np.sum(delta_volumes)), 2),
            "volume_weighted_baseline_apy_bps": round(vw_baseline_apy, 1),
            "volume_weighted_new_apy_bps": round(vw_new_apy, 1),
            "baseline_interest_expense_mm": round(baseline_interest_mm, 3),
            "new_interest_expense_mm": round(new_interest_mm, 3),
            "delta_interest_expense_mm": round(delta_interest_mm, 3),
            "baseline_spread_income_mm": round(baseline_spread_mm, 3),
            "new_spread_income_mm": round(new_spread_mm, 3),
            "delta_spread_income_mm": round(delta_spread_mm, 3),
            "nim_impact_bps": round(nim_impact_bps, 2),
            "funding_rate_bps": funding_rate_bps,
        },
    }

    metrics = {
        "total_volume_change_mm": round(float(np.sum(delta_volumes)), 2),
        "delta_interest_expense_mm": round(delta_interest_mm, 3),
        "nim_impact_bps": round(nim_impact_bps, 2),
        "delta_spread_income_mm": round(delta_spread_mm, 3),
        "volume_weighted_new_apy_bps": round(vw_new_apy, 1),
        "nim_warning": 1.0 if nim_warning else 0.0,
    }

    nextmv.log(f"Total volume change: {np.sum(delta_volumes):+.1f} $MM")
    nextmv.log(f"NIM impact: {nim_impact_bps:+.2f} bps")
    if nim_warning:
        nextmv.log(f"WARNING: NIM impact {nim_impact_bps:.2f} bps is below threshold {min_nim} bps")

    input_chart = build_input_chart(data)
    solution_chart = build_solution_chart(solution, data)

    output = nextmv.Output(
        solution=solution,
        assets=[input_chart, solution_chart],
        metrics=metrics,
    )
    nextmv.write(output, path=options.output)


if __name__ == "__main__":
    main()
