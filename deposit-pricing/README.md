# Deposit Pricing Elasticity Model

Model how changes to deposit product APYs shift volume across a bank's savings portfolio, and quantify the net interest margin impact.

## Approach

Given a portfolio of deposit products (savings accounts, money market, CDs) and a proposed set of rate changes, the model applies a price elasticity matrix to estimate volume changes:

```
ΔQ_i = Σ_j (α_ij × Δrate_j)
```

where `α_ij` is the cross-price elasticity of product `i` volume with respect to product `j`'s rate change (in $MM per basis point). Diagonal entries capture own-price sensitivity; off-diagonal entries capture substitution effects between products. The model then computes interest expense and net interest margin impact at the portfolio level.

## Configuration Options

| Name | Type | Default | Description |
|---|---|---|---|
| `delta_*_bps` | int | `0` | Rate change per product in basis points (one slider per product) |
| `total_assets_mm` | int | `10000` | Total bank assets in $MM |
| `funding_rate_bps` | int | `530` | Bank's asset yield used to compute deposit spread income (bps) |
| `min_nim_impact_bps` | float | `-2.0` | NIM impact threshold — flags a warning if breached |

## Input Format

```json
{
  "products": [
    {
      "id": "hysa",
      "name": "High-Yield Savings",
      "baseline_apy_bps": 450,
      "baseline_volume_mm": 1200
    }
  ],
  "elasticity_matrix": {
    "hysa": {
      "hysa": 8.5,
      "money_market": -2.1
    },
    "money_market": {
      "hysa": -2.8,
      "money_market": 6.8
    }
  }
}
```

| Field | Type | Description |
|---|---|---|
| `products[].id` | string | Unique product identifier (must match elasticity matrix keys) |
| `products[].baseline_apy_bps` | int | Current APY in basis points (e.g., 450 = 4.50%) |
| `products[].baseline_volume_mm` | float | Current deposit balance in $MM |
| `elasticity_matrix` | object | n×n matrix: `[row_product][col_product]` = $MM volume change in row product per 1 bps change in col product's rate |

## Output

**Metrics**

| Metric | Description |
|---|---|
| `total_volume_change_mm` | Net deposit volume change across all products ($MM) |
| `delta_interest_expense_mm` | Change in annual interest expense ($MM) |
| `nim_impact_bps` | Net interest margin impact (basis points) |
| `delta_spread_income_mm` | Change in deposit spread income ($MM) |
| `volume_weighted_new_apy_bps` | Portfolio volume-weighted APY after rate changes (bps) |
| `nim_warning` | 1.0 if NIM impact breaches `min_nim_impact_bps` threshold |

**Visualizations**

- **Baseline Portfolio**: Bar chart of current deposit volumes and APYs; heatmap of the full elasticity matrix (green = positive elasticity, red = substitution/cannibalization)
- **Rate Impact Analysis**: Volume change waterfall by product; before/after volume comparison with APY annotations; headline showing NIM impact, total volume change, and spread income change

## Running Locally

```python
mcp__nextmv__local_run(
    app_dir="deposit-pricing",
    input=<parsed input.json>,
    run_options={"delta_hysa_bps": "25", "delta_money_market_bps": "10"}
)
```

## Included Inputs

| File | Description |
|---|---|
| `input.json` | 5-product portfolio baseline |
| `inputs/small.json` | 3-product portfolio |
| `inputs/medium.json` | 5-product portfolio |
| `inputs/large.json` | 7-product portfolio with full CD ladder |
| `inputs/nim-defensive.json` | 5-product portfolio, low-elasticity configuration |

## Syncing to Nextmv Cloud

```python
mcp__nextmv__local_sync(
    app_dir="deposit-pricing",
    cloud_app_id="deposit-pricing"
)
```
