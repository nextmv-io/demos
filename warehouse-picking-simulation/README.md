# Warehouse Picking Simulation

Agent-based simulation of a warehouse where picker agents fulfill orders, used to evaluate staffing levels and throughput under varying demand.

## Approach

Built with [Mesa](https://mesa.readthedocs.io/) (Apache 2.0), an agent-based modeling framework. Two agent types interact each simulation step:

- **PickerAgent** — idles until an unclaimed order appears, then picks it over `pick_duration × items_per_order` steps
- **OrderAgent** — arrives at a Poisson-distributed rate, waits to be claimed, tracks wait time

Metrics are collected each step to power the timeline chart. Picker utilization is computed as busy steps / total steps per picker.

## Configuration Options

| Option | Type | Default | Description |
|---|---|---|---|
| `num_pickers` | int (slider) | 5 | Number of picker agents |
| `num_steps` | int (slider) | 200 | Simulation length in steps |
| `order_arrival_rate` | float (slider) | 0.3 | Mean orders arriving per step (Poisson) |
| `pick_duration` | int | 5 | Steps required to pick one item |
| `items_per_order` | int | 3 | Fixed number of items per order |
| `random_seed` | int | — | Optional seed for reproducibility |

## Input Format

A JSON object with an optional `warehouse` metadata field. All simulation parameters come from options.

```json
{
  "warehouse": {
    "name": "My Warehouse",
    "description": "Optional description"
  }
}
```

## Output

**Solution fields:**
- `orders_completed` — total orders fulfilled during the simulation
- `orders_pending` — orders still in queue at end
- `picker_utilizations` — per-picker fraction of steps spent picking
- `history` — per-step snapshot of completed and pending order counts

**Metrics:**
| Metric | Description |
|---|---|
| `orders_completed` | Total orders fulfilled |
| `orders_pending` | Orders still in queue at end |
| `avg_wait_time` | Mean steps from order arrival to pickup start |
| `picker_utilization` | Fraction of total picker-steps spent busy (0–1) |
| `throughput` | Orders completed per simulation step |

**Visualizations:**
- **Tab 1 — Simulation Timeline**: orders completed and orders pending over time
- **Tab 2 — Picker Utilization**: per-picker utilization bar chart (green < 70%, orange 70–90%, red > 90%)

## Running Locally

```python
# Default input (balanced scenario)
mcp__nextmv__local_run(app_dir="warehouse-picking-simulation", input={"warehouse": {"name": "Default"}})

# Understaffed scenario — high arrival rate, few pickers
mcp__nextmv__local_run(
    app_dir="warehouse-picking-simulation",
    input={"warehouse": {"name": "Understaffed"}},
    run_options={"num_pickers": 2, "order_arrival_rate": 0.8}
)

# Large scenario
mcp__nextmv__local_run(
    app_dir="warehouse-picking-simulation",
    input={"warehouse": {"name": "Large"}},
    run_options={"num_pickers": 15, "num_steps": 500, "order_arrival_rate": 0.7}
)
```

## Syncing to Nextmv Cloud

```python
mcp__nextmv__local_sync(app_dir="warehouse-picking-simulation", cloud_app_id="warehouse-picking-simulation")
```
