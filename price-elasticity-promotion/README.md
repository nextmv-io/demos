# Price Elasticity Promotion Engine

Optimizes promotional pricing decisions by estimating each product's price elasticity from historical data and solving a budget-constrained promotion allocation problem.

## Approach

The app runs in two stages:

1. **Elasticity estimation** — fits a constant-elasticity demand model (`log(demand) = a + e * log(price)`) to each product's price history via ordinary least squares. The coefficient `e` is the price elasticity of demand (e.g., `e = -2.5` means a 10% price cut raises demand by ~28%).

2. **Promotion optimization** — formulates a mixed-integer program using OR-Tools CP-SAT. For each product, a discrete set of discount levels is evaluated (e.g., 0%, 10%, 20%, …, 50%). The solver picks one discount level per product to maximize the chosen objective (profit, revenue, or units sold) subject to the total promotional budget constraint.

Inelastic products (|e| < 1) are typically left unpromotioned unless budget is plentiful, since their demand barely responds to price cuts. Elastic products (|e| > 1) are prioritized.

## Configuration Options

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `objective` | string | `profit` | What to maximize: `profit`, `revenue`, or `units` |
| `min_discount_pct` | int | `10` | Minimum discount level considered (%) |
| `max_discount_pct` | int | `50` | Maximum discount level allowed (%) |
| `discount_step_pct` | int | `10` | Step between discount levels (%) |
| `max_products_on_promotion` | int | `0` | Max simultaneous promotions (0 = unlimited) |
| `solve_duration` | int | `30` | Solver time limit in seconds |

## Input Format

A JSON object with a product catalog and a promotion budget:

```json
{
  "promotion_budget": 2000.0,
  "products": [
    {
      "id": "SKU001",
      "name": "Premium Coffee Beans",
      "base_price": 18.99,
      "cost": 7.50,
      "base_demand": 80,
      "price_history": [
        {"price": 14.99, "demand": 143},
        {"price": 18.99, "demand": 80},
        {"price": 22.99, "demand": 49}
      ]
    }
  ]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `promotion_budget` | float | Total dollar amount available for discounts |
| `products[].id` | string | Unique product identifier |
| `products[].base_price` | float | Current/reference selling price |
| `products[].cost` | float | Unit cost (used for profit calculation) |
| `products[].base_demand` | int | Units sold at the base price |
| `products[].price_history` | list | Past observations of `{price, demand}` used to fit elasticity |

At least 2 price history observations are needed for elasticity estimation; products with fewer observations default to `e = -1.0`.

## Output

**Solution** (`assignments` list):

| Field | Description |
|-------|-------------|
| `discount_pct` | Recommended discount (0 = no promotion) |
| `promo_price` | Resulting promotional price |
| `elasticity` | Fitted price elasticity coefficient |
| `expected_demand` | Forecast units at promo price |
| `demand_lift_pct` | % demand increase vs baseline |
| `profit` / `revenue` / `promo_cost` | Financial projections |

**Metrics** (`metrics.json`):

| Metric | Description |
|--------|-------------|
| `status` | `optimal` or `suboptimal` |
| `result_value` | Objective value (profit, revenue, or units) |
| `total_profit` | Total forecasted profit across all products |
| `total_revenue` | Total forecasted revenue |
| `total_promo_cost` | Budget consumed |
| `profit_lift_vs_baseline` | Incremental profit vs no promotions |
| `products_on_promotion` | Number of products receiving a discount |
| `avg_elasticity` | Mean price elasticity across the catalog |

**Visualizations**:
- **Tab 1 — Elasticity Curves**: Demand vs discount % for each product, showing the fitted elasticity model
- **Tab 2 — Promotion Plan**: Horizontal bars showing recommended discount and demand lift per product
- **Tab 3 — Financial Impact**: Grouped bar comparing baseline vs promoted profit per product, plus incremental lift

## Running Locally

```python
# Default input (10 products, $2,000 budget)
mcp__nextmv__local_run(app_dir=".", input=<parsed input.json>)

# Larger catalog, $5,000 budget
mcp__nextmv__local_run(app_dir=".", input=<parsed inputs/large.json>)

# Tight budget — forces selective allocation
mcp__nextmv__local_run(app_dir=".", input=<parsed inputs/tight-budget.json>)

# Catalog dominated by inelastic goods
mcp__nextmv__local_run(app_dir=".", input=<parsed inputs/inelastic-heavy.json>)

# Maximize revenue instead of profit
mcp__nextmv__local_run(app_dir=".", input=<parsed input.json>, run_options={"objective": "revenue"})

# Limit to at most 3 products on promotion
mcp__nextmv__local_run(app_dir=".", input=<parsed input.json>, run_options={"max_products_on_promotion": "3"})
```

## Syncing to Nextmv Cloud

```python
mcp__nextmv__local_sync(app_dir=".", cloud_app_id="<cloud-app-id>")
```
