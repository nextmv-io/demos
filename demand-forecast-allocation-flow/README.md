# Demand Forecast + Inventory Allocation Flow

A two-stage decision pipeline that uses Nextpipe's `FlowSpec` to chain a
scikit-learn demand forecast directly into a Pyomo/HiGHS inventory allocation LP.

## Approach

The app is structured as a Nextpipe workflow with three steps:

1. **`forecast_demand`** — Trains a `GradientBoostingRegressor` on historical
   store sales (features: store ID, period, price, promotion flag) and predicts
   next-period demand for each store.

2. **`optimize_allocation`** — Takes the forecasted demand as the right-hand
   side of a transportation LP. Minimises total shipping cost plus a penalty
   for unmet demand, subject to warehouse supply limits. Solved with
   Pyomo + HiGHS (or CBC / GLPK).

3. **`bundle_results`** — Combines both outputs into a unified `nextmv.Output`
   with two Plotly visualisations: a forecast chart and an allocation Sankey.

## Configuration Options

| Name | Type | Default | Description |
|---|---|---|---|
| `solver` | string | `highs` | LP solver: `highs`, `cbc`, or `glpk` |
| `penalty_unmet_demand` | float | `100` | Cost per unit of unmet store demand |
| `time_limit` | float | `30` | Solver wall-clock time limit (seconds) |
| `random_seed` | int | — | Seed for reproducible cost-matrix generation when `transportation_costs` is omitted |

## Input Format

```json
{
  "stores": [
    {"id": "store_0", "name": "Downtown"}
  ],
  "warehouses": [
    {"id": "wh_0", "name": "Central Hub", "supply": 250}
  ],
  "historical_sales": [
    {"store_id": "store_0", "period": 1, "price": 12.0, "promotion": 0, "units_sold": 75}
  ],
  "transportation_costs": {
    "wh_0": {"store_0": 3.5}
  }
}
```

- `historical_sales` — One row per store per period. The model trains on all
  rows and forecasts `max(period) + 1`.
- `transportation_costs` — Optional. If omitted, costs are sampled uniformly
  from [1, 10] using `random_seed`.

## Output

**Solution fields:**
- `forecasts` — Predicted demand per store for the next period.
- `allocations` — Units shipped from each warehouse to each store.
- `unmet_demand` — Stores where demand exceeds available supply.

**Metrics:**
| Metric | Description |
|---|---|
| `result_value` | LP objective value (transport cost + unmet penalty) |
| `transportation_cost` | Pure shipping cost component |
| `fill_rate` | Fraction of total demand fulfilled |
| `total_units_allocated` | Sum of all allocated units |
| `total_demand` | Sum of forecasted demand across all stores |
| `total_supply` | Sum of warehouse supply capacities |
| `num_unmet_stores` | Number of stores with unmet demand |
| `status` | Solver status: `optimal`, `suboptimal`, `infeasible`, `unbounded` |

**Visualisations:**
- **Demand Forecast** — Historical sales line chart + next-period forecast bar chart per store.
- **Allocation Flow** — Sankey diagram of units flowing from warehouses to stores.

## Running Locally

```python
# Default input (5 stores, 3 warehouses, 12 periods)
mcp__nextmv__local_run(app_dir=".", input=<parsed input.json>)

# Supply-constrained scenario (tests penalty behaviour)
mcp__nextmv__local_run(app_dir=".", input=<parsed inputs/supply-constrained.json>)

# Large scenario (10 stores, 5 warehouses, 24 periods)
mcp__nextmv__local_run(app_dir=".", input=<parsed inputs/large.json>)

# Test with elevated penalty
mcp__nextmv__local_run(app_dir=".", input=<parsed input.json>, run_options={"penalty_unmet_demand": 500})
```

## Syncing to Nextmv Cloud

```python
mcp__nextmv__local_sync(app_dir=".", cloud_app_id="<cloud-app-id>")
```
