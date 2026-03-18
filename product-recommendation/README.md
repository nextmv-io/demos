# Product Recommendation

Recommend products to a customer from a catalog by scoring each product across category match, brand affinity, price fit, and rating — with configurable weights and optional diversity enforcement.

## Approach

Content-based scoring with hard constraint filtering. Each product is scored across four dimensions, combined using user-configured weights:

- **Category match**: 1.0 if the product's category is in the customer's preferred list, 0.4 otherwise
- **Brand affinity**: 1.0 if the product's brand is preferred, 0.4 otherwise
- **Price fit**: decreases as price approaches budget, scaled by `price_sensitivity`
- **Rating**: normalized product rating (0–1)

Hard filters exclude products that are: over budget, out of stock, already purchased, or in an excluded category.

When **diversity mode** is enabled, recommendations are selected via greedy marginal relevance — after each pick, products in the same category are penalized to encourage spread across categories.

## Configuration Options

| Option | Type | Default | Description |
| --- | --- | --- | --- |
| `max_recommendations` | int | `10` | Maximum number of products to recommend |
| `category_weight` | float | `0.35` | Weight given to category match |
| `brand_weight` | float | `0.25` | Weight given to brand affinity |
| `price_weight` | float | `0.2` | Weight given to price fit |
| `rating_weight` | float | `0.2` | Weight given to product rating |
| `diversity` | bool | `true` | Enforce category diversity in recommendations |

Weights are automatically normalized so relative ratios matter, not absolute values.

## Input Format

A single JSON object with a `customer` and a `products` array.

### `customer`

| Field | Type | Description |
| --- | --- | --- |
| `id` | string | Customer identifier |
| `preferred_categories` | string[] | Categories the customer prefers |
| `preferred_brands` | string[] | Brands the customer prefers |
| `excluded_categories` | string[] | Categories to exclude entirely |
| `budget` | number | Maximum price the customer will pay |
| `price_sensitivity` | float | 0 = ignores price, 1 = very price sensitive |
| `previously_purchased` | string[] | Product IDs already owned (excluded from results) |

### `products`

| Field | Type | Description |
| --- | --- | --- |
| `id` | string | Unique product identifier |
| `name` | string | Display name |
| `category` | string | Product category |
| `brand` | string | Brand name |
| `price` | number | Price in dollars |
| `rating` | float | Rating out of 5.0 |
| `in_stock` | bool | Whether the product is available |

## Output

**Solution**: `recommendations` list (ranked by composite score) and filter summary.

**Metrics** (`metrics.json`):

| Metric | Description |
| --- | --- |
| `result_value` | Average composite score of recommendations |
| `recommendations_count` | Number of products recommended |
| `avg_score` | Average composite score |
| `avg_price` | Average price of recommendations |
| `avg_rating` | Average rating of recommendations |
| `categories_covered` | Number of distinct categories in recommendations |
| `preferred_category_rate` | Fraction of recommendations in preferred categories |
| `eligible_products` | Products passing hard filters |

**Visualizations**:
- **Recommendations** (tab 1): ranked horizontal bar chart with price and rating labels, colored by category
- **Score Breakdown** (tab 2): stacked bar showing each recommendation's score by component
- **Catalog Overview** (tab 3): scatter of all products by price vs. rating; recommended products numbered and highlighted

## Input Scenarios

| File | Description |
| --- | --- |
| `input.json` | Default — tech customer, $600 budget, 30-product catalog |
| `inputs/small.json` | 10 products, books-focused customer |
| `inputs/electronics.json` | High-budget tech enthusiast, Apple/Sony/Bose preferences |
| `inputs/budget.json` | Price-sensitive customer, tight $80 budget |
| `inputs/diverse.json` | No category/brand preferences — rating and price driven |
| `inputs/no-preferences.json` | Electronics-focused, shows effect of excluding categories |

## Running Locally

```bash
# Default input
cat input.json | nextmv local run create --app-src . --wait

# Named scenarios
cat inputs/small.json | nextmv local run create --app-src . --name small --wait
cat inputs/electronics.json | nextmv local run create --app-src . --name electronics --wait
cat inputs/budget.json | nextmv local run create --app-src . --name budget --wait
cat inputs/diverse.json | nextmv local run create --app-src . --name diverse --wait

# Run with high category weight (prioritize matching preferences)
cat input.json | nextmv local run create --app-src . -o category_weight=0.7 -o brand_weight=0.1 --wait

# Run without diversity enforcement
cat input.json | nextmv local run create --app-src . -o diversity=false --wait
```

## Syncing to Nextmv Cloud

```bash
nextmv local app sync --app-src . --target-app-id <cloud-app-id>
```
