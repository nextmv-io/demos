# Shift Planning

Decides how many shifts to publish and their lengths to meet hourly staffing demand at minimum cost.

## Approach

Mixed-integer programming (MIP) via [Pyomo](https://www.pyomo.org/) + [HiGHS](https://highs.dev/). All feasible shifts are enumerated from the configured min/max length bounds. The model selects which shifts to open and how many workers to assign to each, minimizing total labor cost (hourly wage × hours × workers) plus fixed setup costs per shift. A penalty term for unmet demand keeps the problem feasible when coverage is infeasible.

## Configuration Options

| Name | Type | Default | Description |
|---|---|---|---|
| `min_shift_length` | int | 4 | Minimum shift length in hours |
| `max_shift_length` | int | 8 | Maximum shift length in hours |
| `max_workers_per_shift` | int | 10 | Maximum workers allowed on a single shift |
| `hourly_wage` | float | 15.0 | Labor cost per worker per hour |
| `shift_setup_cost` | float | 50.0 | Fixed cost to open a shift |
| `penalty_unmet_demand` | float | 1000.0 | Cost per worker-period of unmet demand |
| `time_limit` | float | 30.0 | Solver time limit in seconds |

## Input Format

A JSON object with a `time_periods` list. Each entry has:

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | string | yes | Unique identifier |
| `label` | string | no | Display label (e.g. `"09:00"`, `"Mon 12:00"`) |
| `demand` | int | yes | Number of workers required in this period |

```json
{
  "time_periods": [
    {"id": "t0", "label": "08:00", "demand": 3},
    {"id": "t1", "label": "09:00", "demand": 5},
    {"id": "t2", "label": "10:00", "demand": 6}
  ]
}
```

Time periods are assumed to be equal-length (typically 1 hour). Multi-day schedules are supported by using descriptive labels like `"Mon 08:00"`.

## Output

**Solution fields:**
- `shifts`: published shifts with start/end period, length, workers assigned, and cost breakdown
- `coverage`: per-period demand vs. assigned workers

**Metrics (`metrics.json`):**

| Metric | Description |
|---|---|
| `status` | `optimal`, `suboptimal`, `infeasible`, or `unbounded` |
| `result_value` | Total cost (labor + setup + unmet penalty) |
| `total_shifts` | Number of published shifts |
| `total_worker_hours` | Total worker-hours scheduled |
| `total_labor_cost` | Labor cost component |
| `total_setup_cost` | Setup cost component |
| `unmet_periods` | Number of periods not fully covered |
| `total_unmet_demand` | Total worker-periods of unmet demand |

**Visualizations:**
- **Demand Profile** (tab 1): Bar chart of required workers per time period
- **Shift Plan** (tab 2): Staffing coverage vs demand (top) and Gantt chart of published shifts (bottom)

## Running Locally

```python
# Default input (single day, 8am–8pm)
mcp__nextmv__local_run(app_dir=".", input=<parsed input.json>)

# Peak demand scenario
mcp__nextmv__local_run(app_dir=".", input=<parsed inputs/peak-demand.json>)

# Full week
mcp__nextmv__local_run(app_dir=".", input=<parsed inputs/large.json>, run_options={"time_limit": "60"})

# Tighter shifts with higher wages
mcp__nextmv__local_run(app_dir=".", input=<parsed input.json>, run_options={"min_shift_length": "6", "hourly_wage": "25"})
```

## Syncing to Nextmv Cloud

```python
mcp__nextmv__local_sync(app_dir=".", cloud_app_id="<cloud-app-id>")
```
