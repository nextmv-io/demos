# Shift Scheduling

Assign workers to shifts across a weekly schedule, balancing **total labor cost** against **scheduling fairness** (equitable shift distribution).

## The Story

An operations manager has been running the scheduler in `cost_only` mode. Workers start complaining: some are getting 5 shifts a week while others get 1 or none. The manager runs a **scenario test** — sweeping `objective_mode` across all three values on their historical inputs — and sees that for most inputs, a fair schedule costs exactly the same. For a few tight-availability inputs, fairness costs 3–8% more. That data lets the manager set a concrete policy: "up to 5% more cost is acceptable." They encode it in an **ensemble** — four run groups covering the cost–fairness frontier, with rules that minimize cost first (within that 5% tolerance) and break ties on spread. Every new scheduling run automatically gets the fairest schedule the budget allows.

## Approach

Mixed-Integer Linear Program (MILP) via [Pyomo](https://www.pyomo.org/) + [HiGHS](https://highs.dev/) (both Apache/MIT licensed).

**Decision variables**: binary assignment of each worker to each shift they're available for.

**Constraints**:
- Each shift must be staffed with exactly its required number of workers.
- Each worker is assigned between their `min_shifts` and `max_shifts` limits.
- Workers can only be assigned to shifts in their `available_shifts` list.

**Coverage is soft:** each shift has a `shortfall` variable (required − assigned) that is penalized in the objective. A high `coverage_penalty` (default 10,000) makes it behave identically to a hard constraint; lowering it lets the solver trade off understaffing against cost or fairness. This gives the ensemble a natural first rule: always prefer fully-staffed schedules.

**Selectable objectives** — all include the coverage penalty term:
- `cost_only` — minimize `coverage_penalty × shortfall + labor_cost`
- `fair_only` — minimize `coverage_penalty × shortfall + spread`
- `weighted` — minimize `coverage_penalty × shortfall + labor_cost + fairness_penalty × spread`

At high `coverage_penalty`, all three modes produce fully-staffed schedules and differ only on the cost/fairness tradeoff. Lowering the penalty reveals whether partial staffing is ever worth it for a given input.

## Configuration Options

| Option | Type | Default | Description |
|---|---|---|---|
| `objective_mode` | string | `weighted` | `cost_only`, `fair_only`, or `weighted` |
| `coverage_penalty` | float | `10000.0` | Penalty per unstaffed worker-slot. High values enforce full coverage; lower values allow strategic understaffing |
| `hourly_wage` | float | `18.0` | Labor cost per worker per hour |
| `fairness_penalty` | float | `200.0` | Penalty per unit of max–min spread (`weighted` mode only) |
| `time_limit` | float | `30.0` | Solver time limit in seconds |

## Input Format

```json
{
  "workers": [
    {
      "id": "w1",
      "min_shifts": 2,
      "max_shifts": 5,
      "available_shifts": ["mon-am", "tue-pm", "wed-am"]
    }
  ],
  "shifts": [
    {
      "id": "mon-am",
      "name": "Monday AM",
      "hours": 4,
      "required_workers": 2
    }
  ]
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `workers[].id` | string | yes | Unique worker ID (used as the display label) |
| `workers[].min_shifts` | int | no (default 0) | Minimum shifts the worker must be assigned |
| `workers[].max_shifts` | int | no (default ∞) | Maximum shifts the worker can be assigned |
| `workers[].available_shifts` | list[string] | no (default all) | Which shift IDs this worker can take |
| `shifts[].id` | string | yes | Unique shift ID |
| `shifts[].name` | string | no | Display name |
| `shifts[].hours` | float | no (default 8) | Duration in hours (affects labor cost) |
| `shifts[].required_workers` | int | no (default 1) | Exact number of workers required for this shift |

## Output

**Solution fields**:
- `assignments` — list of `{worker_id, worker_name, shift_id, shift_name, shift_hours, cost}` records
- `shift_coverage` — per-shift assigned vs. required headcount
- `worker_shift_counts` — shifts per worker (used to quantify fairness)

**Metrics**:
| Metric | Description |
|---|---|
| `status` | `optimal`, `suboptimal`, `infeasible`, or `unbounded` |
| `result_value` | Total labor cost (consistent across all modes for comparison) |
| `total_cost` | Total labor cost in dollars |
| `total_shortfall` | Sum of unstaffed worker-slots across all shifts |
| `unplanned_shifts` | Number of shifts with at least one unfilled slot |
| `shift_spread` | max – min shifts per worker (0 = perfectly fair) |
| `max_shifts_per_worker` | Most shifts assigned to any single worker |
| `min_shifts_per_worker` | Fewest shifts assigned to any single worker |
| `assignments` | Total number of worker–shift assignments |
| `objective_mode` | Which mode was used |

**Visualizations**:
- **Shift Schedule** (tab 1) — Worker × shift assignment heatmap + coverage bar chart
- **Fairness View** (tab 2) — Shifts per worker bar chart colored by deviation from mean

## Running Locally

```python
mcp__nextmv__local_run(app_dir=".", input=<parsed input.json>)

# Test a specific objective mode
mcp__nextmv__local_run(app_dir=".", input=<parsed input.json>, run_options={"objective_mode": "cost_only"})
mcp__nextmv__local_run(app_dir=".", input=<parsed input.json>, run_options={"objective_mode": "fair_only"})

# Run larger inputs
mcp__nextmv__local_run(app_dir=".", input=<parsed inputs/large.json>)
mcp__nextmv__local_run(app_dir=".", input=<parsed inputs/tight-availability.json>)
```

## Syncing to Nextmv Cloud

```python
mcp__nextmv__local_sync(app_dir=".", cloud_app_id="<cloud-app-id>")
```

## Workflow: From Complaint to Ensemble

### Step 1 — Scenario test: discover the tradeoff

The operator has been running `cost_only` in production. Workers complain that shifts aren't distributed fairly. Before changing anything, the operator runs a **scenario test** that sweeps `objective_mode` across all three values on the same inputs they've been scheduling:

```python
mcp__nextmv__cloud_create_scenario_test(
    app_id="shift-scheduling",
    name="Fairness exploration: cost vs. spread",
    scenarios=[
        {
            "instance_id": "production",
            "scenario_input": {
                "scenario_input_type": "input_set",
                "scenario_input_data": "<input-set-id>",
            },
            "configuration": [
                {"name": "objective_mode", "values": ["cost_only", "weighted", "fair_only"]}
            ],
        }
    ],
)
```

The results table shows cost and `shift_spread` side by side for each mode and each input. The typical finding:

- For most inputs: `weighted` and `fair_only` achieve the **same cost** as `cost_only` with a spread of 1 vs 5.
- For some inputs (tight availability, varied shift lengths): fairness has a real cost — spread=1 might cost 3–8% more.

This is the data that lets the operator make a policy decision: "I'm willing to accept up to 5% more cost to get a fair schedule."

### Step 2 — Ensemble: auto-route every input

The ensemble encodes that policy with three rules and four run groups.

**Run groups** — each explores a different point on the cost–fairness frontier:

| Run group | Mode | `fairness_penalty` | What it optimizes |
|---|---|---|---|
| `cost-only` | `cost_only` | — | Cost floor — anchor for Rule 1's tolerance |
| `light-fairness` | `weighted` | `100` | Slight nudge toward fairness; cost stays close to minimum |
| `strong-fairness` | `weighted` | `500` | Real fairness pressure; will accept a meaningful cost increase |
| `max-fairness` | `fair_only` | — | Best possible spread, cost secondary — ceiling reference |

`max-fairness` earns its place: when it passes Rule 1's cost filter it wins outright on Rule 2. When it doesn't, the ensemble correctly routes to a cheaper-but-still-fair config. That routing decision is the ensemble visibly doing its job.

**Rules** — two priorities in order:

1. **Cost within tolerance** (`$.result.value`, 5% tolerance): `result.value` is the total labor cost for fully-staffed runs and `1e12` (a large sentinel) for any run that leaves shifts understaffed. This means understaffed runs are automatically filtered before the cost comparison even happens — coverage is implicitly first.
2. **Fairest within budget** (`$.result.custom.shift_spread`, no tolerance): among candidates that passed Rule 0, pick the one with the smallest max–min spread.

```python
mcp__nextmv__cloud_create_ensemble(
    app_id="shift-scheduling",
    ensemble_id="coverage-cost-fairness",
    name="Coverage cost fairness",
    run_groups=[
        {"id": "cost-only",       "instance_id": "production", "options": {"objective_mode": "cost_only"}},
        {"id": "light-fairness",  "instance_id": "production", "options": {"objective_mode": "weighted", "fairness_penalty": "100"}},
        {"id": "strong-fairness", "instance_id": "production", "options": {"objective_mode": "fair_only"}},
    ],
    rules=[
        # Rule 0: minimize cost (1e12 sentinel routes around understaffed/infeasible runs)
        {
            "id": "min-shortfall",
            "statistics_path": "$.result.value",
            "objective": "minimize",
            "tolerance": {"value": 5.0, "type": "relative"},
            "index": 0,
        },
        # Rule 1: fairest schedule within cost budget
        {
            "id": "min-spread",
            "statistics_path": "$.result.custom.shift_spread",
            "objective": "minimize",
            "index": 1,
        },
    ],
)
```
