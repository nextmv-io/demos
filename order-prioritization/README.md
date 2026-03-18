# Order Prioritization

Assign a fulfillment priority (expedite / standard / defer) to each incoming order using a declarative rules engine.

## Approach

Declarative rules engine built with [business-rules](https://github.com/venmo/business-rules). Each order is evaluated against a configurable rule set; the first matching rule sets the priority. Three built-in rule sets cover different prioritization strategies — cost-driven, deadline-driven, and tier-driven — and the deadline thresholds are adjustable via options.

## Configuration Options

| Option | Type | Default | Description |
| --- | --- | --- | --- |
| `rule_set` | string | `cost-first` | Which rule set to apply: `cost-first`, `deadline-first`, or `tier-first` |
| `expedite_deadline_days` | int | `2` | Deadline threshold (days) for expedite priority (used by `deadline-first`) |
| `standard_deadline_days` | int | `7` | Deadline threshold (days) for standard priority (used by `deadline-first`) |

### Rule sets

| Rule set | Logic |
| --- | --- |
| `cost-first` | Expedite if value > $10k or gold tier; standard if value > $3k or silver tier |
| `deadline-first` | Expedite if deadline ≤ `expedite_deadline_days`; standard if ≤ `standard_deadline_days` |
| `tier-first` | Expedite all gold-tier orders; standard all silver-tier orders |

Orders that match no rule are deferred.

## Input Format

CSV file (`orders.csv`) with one row per order:

| Column | Type | Description |
| --- | --- | --- |
| `id` | string | Unique order identifier |
| `value` | float | Order value in dollars |
| `days_until_deadline` | int | Days remaining until fulfillment deadline |
| `customer_tier` | string | Customer segment: `gold`, `silver`, or `bronze` |
| `units` | int | Number of units ordered |

## Output

**Solution** (`output/results.csv`): all input columns plus a `priority` column (`expedite`, `standard`, or `defer`).

**Metrics** (`metrics.json`):

| Metric | Description |
| --- | --- |
| `result_value` | Number of orders marked expedite |
| `total_orders` | Total orders processed |
| `expedite_count` | Orders assigned expedite priority |
| `standard_count` | Orders assigned standard priority |
| `defer_count` | Orders assigned defer priority |
| `expedite_pct` | Fraction of orders expedited (0–1) |
| `rule_set` | Rule set used |

**Visualizations**:
- **Priority Breakdown** (tab 1): grouped bar chart of order counts by priority and customer tier
- **Priority Scatter** (tab 2): scatter plot of order value vs. days until deadline, colored by priority

## Running Locally

This app uses multi-file format. Run from the directory containing `orders.csv`:

```bash
# Run with the default input directory
nextmv local run create --app-src . --wait

# Run a specific scenario from its input directory
nextmv local run create --app-src . --input-dir inputs/large --name large --wait
```

## Syncing to Nextmv Cloud

```bash
nextmv local app sync --app-src . --target-app-id <cloud-app-id>
```
