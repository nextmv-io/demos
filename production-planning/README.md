# Production Planning

Determine how much of each product to produce each period to minimize total cost (production + inventory holding) while meeting demand within capacity constraints.

## Approach

Linear program (LP) modeled with [Pyomo](https://www.pyomo.org/) and solved with HiGHS, CBC, or GLPK. Decision variables are production quantities and end-of-period inventory levels for each product in each period, plus an unmet demand slack variable. The objective minimizes production cost, weighted holding cost, and a penalty for any unmet demand. A shared resource capacity constraint limits total production across all products each period.

## Configuration Options

| Option | Type | Default | Description |
| --- | --- | --- | --- |
| `solver` | string | `highs` | LP solver: `highs`, `cbc`, or `glpk` |
| `holding_cost_weight` | float | `1.0` | Multiplier on holding costs (higher = discourages inventory buildup) |
| `penalty_unmet_demand` | float | `500.0` | Cost per unit of unmet demand (higher = prioritize fill rate) |
| `safety_stock_pct` | float | `0.0` | Minimum ending inventory as a % of next period's demand (0 = no requirement) |
| `max_production_ramp_pct` | float | `100.0` | Max period-over-period change as a % of each product's average period demand (100 = unconstrained) |
| `time_limit` | float | `30.0` | Solver time limit in seconds |

## Input Format

JSON with product names, period labels, demand matrix, costs, resource usage, and capacity:

```json
{
  "products": ["Widget A", "Widget B", "Widget C"],
  "periods": ["Jan", "Feb", "Mar", "Apr", "May", "Jun"],
  "demand": [
    [50, 60, 55, 70, 80, 75],
    [30, 35, 40, 45, 50, 55],
    [20, 25, 30, 35, 40, 45]
  ],
  "production_cost": [2.0, 3.5, 5.0],
  "holding_cost": [0.20, 0.35, 0.50],
  "resource_use": [1.0, 1.5, 2.0],
  "capacity": [200, 190, 210, 220, 210, 215],
  "initial_inventory": [10, 5, 0]
}
```

| Field | Type | Description |
| --- | --- | --- |
| `products` | string[] | Product names |
| `periods` | string[] | Period labels (e.g. month names, quarter labels) |
| `demand` | float\[\]\[\] | `demand[p][t]` — units of product `p` needed in period `t` |
| `production_cost` | float[] | Cost per unit produced, indexed by product |
| `holding_cost` | float[] | Cost per unit held per period, indexed by product |
| `resource_use` | float[] | Resource units consumed per unit produced, indexed by product |
| `capacity` | float[] | Total resource units available per period |
| `initial_inventory` | float[] | Starting inventory per product (optional, defaults to 0) |

## Output

**Solution** (`solution.json`): production quantities, ending inventory levels, and any unmet demand, all broken down by product and period.

**Metrics** (`metrics.json`):

| Metric | Description |
| --- | --- |
| `result_value` | Total objective value (production + holding cost + penalties) |
| `production_cost` | Pure production cost, excluding holding and penalties |
| `holding_cost` | Total inventory holding cost across all products and periods |
| `total_unmet_demand` | Total units of demand not fulfilled |
| `fill_rate` | Fraction of total demand met (0–1) |
| `total_demand` | Sum of all demand across products and periods |
| `status` | Solver termination status |
| `solver` | Solver used |

**Visualizations**:

- **Production Plan** (tab 1): stacked bar chart of production by product per period
- **Inventory Levels** (tab 2): line chart of end-of-period inventory by product

## Running Locally

```bash
# Default input (3 products, 6 periods)
cat input.json | nextmv local run create --app-src . --wait

# Named scenarios
cat inputs/small.json | nextmv local run create --app-src . --name small --wait
cat inputs/medium.json | nextmv local run create --app-src . --name medium --wait
cat inputs/large.json | nextmv local run create --app-src . --name large --wait
cat inputs/tight-capacity.json | nextmv local run create --app-src . --name tight-capacity --wait
cat inputs/seasonal-demand.json | nextmv local run create --app-src . --name seasonal-demand --wait
```

## Syncing to Nextmv Cloud

```bash
nextmv local app sync --app-src . --target-app-id <cloud-app-id>
```
