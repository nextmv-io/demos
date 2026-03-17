# Workforce Scheduling

Schedule workers to shifts to minimize total labor cost while maximizing shift coverage, using multi-objective genetic algorithm optimization (NSGA-II).

## Approach

Multi-objective optimization via [NSGA-II](https://pymoo.org/algorithms/moo/nsga2.html) (Non-dominated Sorting Genetic Algorithm II) from the [pymoo](https://pymoo.org/) library. Two competing objectives are optimized simultaneously:

1. **Minimize total labor cost** — sum of `cost_per_shift` across all assigned worker–shift pairs
2. **Minimize understaffing** — total shortfall across all shifts (sum of `max(0, min_workers - assigned)`)

The algorithm returns the full **Pareto front** of non-dominated solutions — the set of assignments where no solution is strictly better on both objectives. A single "best" solution is then selected by minimizing understaffing first, then cost.

Workers respect two constraints enforced via a repair operator:
- **Availability**: workers can only be assigned to shifts in their `available_shifts` list
- **Max shifts**: workers cannot be assigned more than `max_shifts` shifts per week

## Configuration Options

| Option | Type | Default | Description |
| --- | --- | --- | --- |
| `population_size` | int | `100` | Number of candidate solutions in each generation |
| `num_generations` | int | `100` | Number of GA generations to run |
| `mutation_rate` | float | `0.02` | Per-gene (per worker–shift pair) bit-flip probability |
| `crossover_rate` | float | `0.9` | Probability of uniform crossover between parents |
| `seed` | int | `42` | Random seed for reproducibility |

## Input Format

A single JSON object with two arrays.

### `workers`

| Field | Type | Description |
| --- | --- | --- |
| `id` | string | Unique worker identifier |
| `name` | string | Display name |
| `cost_per_shift` | int | Labor cost per assigned shift |
| `max_shifts` | int | Maximum shifts this worker can work in the week |
| `available_shifts` | string[] | List of shift IDs this worker is available for |

### `shifts`

| Field | Type | Description |
| --- | --- | --- |
| `id` | string | Unique shift identifier |
| `name` | string | Display name |
| `min_workers` | int | Minimum number of workers required |

```json
{
  "workers": [
    {"id": "w1", "name": "Alice", "cost_per_shift": 120, "max_shifts": 5,
     "available_shifts": ["mon-am", "tue-am", "wed-am"]}
  ],
  "shifts": [
    {"id": "mon-am", "name": "Mon Morning", "min_workers": 2}
  ]
}
```

## Output

**Solution**: `assignments` (list of worker–shift pairs in best solution) and `shift_summary` (coverage per shift).

**Metrics** (`metrics.json`):

| Metric | Description |
| --- | --- |
| `result_value` | Total labor cost of the selected solution |
| `total_cost` | Same as `result_value` |
| `understaffed_shifts` | Number of shifts below minimum coverage |
| `coverage_rate` | Fraction of shifts fully covered (0–1) |
| `workers_scheduled` | Number of workers assigned at least one shift |
| `pareto_front_size` | Number of non-dominated solutions found |
| `status` | `optimal` (fully covered) or `suboptimal` (some understaffing) |

**Visualizations**:
- **Pareto Front** (tab 1): scatter plot of cost vs. understaffed shifts — each point is a non-dominated solution; the selected solution is highlighted
- **Schedule** (tab 2): heatmap of worker × shift assignments for the best solution; understaffed shifts are marked with ⚠
- **Convergence** (tab 3): best feasible cost and minimum understaffing over generations

## Input Scenarios

| File | Description |
| --- | --- |
| `input.json` | Default — 8 workers, 10 shifts (Mon–Fri, AM/PM) |
| `inputs/small.json` | 5 workers, 6 shifts — fast to run, easy to inspect |
| `inputs/medium.json` | 12 workers, 15 shifts (3 shifts per day) |
| `inputs/large.json` | 20 workers, 21 shifts including weekends |
| `inputs/tight-budget.json` | 6 workers, 10 shifts — understaffing is expected |
| `inputs/peak-demand.json` | 8 workers, higher min coverage — shows tradeoff pressure |

## Running Locally

```bash
# Default input
cat input.json | nextmv local run create --app-src . --wait

# Named scenarios
cat inputs/small.json | nextmv local run create --app-src . --name small --wait
cat inputs/medium.json | nextmv local run create --app-src . --name medium --wait
cat inputs/large.json | nextmv local run create --app-src . --name large --wait
cat inputs/tight-budget.json | nextmv local run create --app-src . --name tight-budget --wait
cat inputs/peak-demand.json | nextmv local run create --app-src . --name peak-demand --wait

# Run with more generations for better results
cat input.json | nextmv local run create --app-src . -o num_generations=300 -o population_size=200 --wait
```

## Syncing to Nextmv Cloud

```bash
nextmv local app sync --app-src . --target-app-id <cloud-app-id>
```
