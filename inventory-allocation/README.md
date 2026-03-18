# Inventory Allocation

Minimize transportation cost when allocating inventory from warehouses to stores, with a configurable penalty for unmet demand.

## Approach

Linear program (LP) modeled with [Pyomo](https://www.pyomo.org/) and solved with HiGHS, CBC, or GLPK. Decision variables are units shipped from each warehouse to each store, plus a slack variable for unmet demand at each store. The objective minimizes total transport cost plus a penalty for any unmet demand. Supply and demand are randomly generated from configurable ranges, enabling reproducible scenario testing via a seed.

## Configuration Options

| Option | Type | Default | Description |
| --- | --- | --- | --- |
| `solver` | string | `highs` | LP solver: `highs`, `cbc`, or `glpk` |
| `penalty_unmet_demand` | float | `100` | Cost per unit of unmet demand (higher = prioritize fill rate) |
| `time_limit` | float | `30` | Solver time limit in seconds |

## Input Format

JSON with problem size parameters and random seed:

```json
{
  "seed": 1,
  "num_warehouses": 3,
  "num_stores": 5,
  "supply_range": [80, 150],
  "demand_range": [40, 80]
}
```

| Field | Type | Description |
| --- | --- | --- |
| `seed` | int | Random seed for reproducible supply/demand/cost generation |
| `num_warehouses` | int | Number of supply nodes |
| `num_stores` | int | Number of demand nodes |
| `supply_range` | [int, int] | `[min, max]` units available per warehouse |
| `demand_range` | [int, int] | `[min, int]` units required per store |

## Output

**Solution** (`solution.json`): list of allocations (warehouse → store → units) and any stores with unmet demand.

**Metrics** (`metrics.json`):

| Metric | Description |
| --- | --- |
| `result_value` | Total objective value (transport cost + penalties) |
| `transportation_cost` | Pure transport cost, excluding penalties |
| `fill_rate` | Fraction of total demand met (0–1) |
| `total_units_allocated` | Sum of all units shipped |
| `total_demand` | Sum of demand across all stores |
| `total_supply` | Sum of supply across all warehouses |
| `num_unmet_stores` | Number of stores with any unmet demand |
| `status` | Solver termination status |
| `solver` | Solver used |

**Visualization**: Sankey diagram showing flow from warehouses to stores.

## Running Locally

```bash
# Default input
cat input.json | nextmv local run create --app-src . --wait

# Named inputs
cat inputs/small.json | nextmv local run create --app-src . --name small --wait
cat inputs/medium.json | nextmv local run create --app-src . --name medium --wait
cat inputs/large.json | nextmv local run create --app-src . --name large --wait
cat inputs/supply-constrained.json | nextmv local run create --app-src . --name supply-constrained --wait
cat inputs/supply-surplus.json | nextmv local run create --app-src . --name supply-surplus --wait
```

## Syncing to Nextmv Cloud

```bash
nextmv local app sync --app-src . --target-app-id <cloud-app-id>
```
