# Machine Shop Scheduling

Schedule a set of jobs through a machine shop to minimize makespan (total completion time), respecting operation sequencing within each job and sequence-dependent changeover times between jobs on each machine.

## Approach

Constraint programming model built with [OR-Tools CP-SAT](https://developers.google.com/optimization). Each operation is an interval variable. The model enforces:

- **Precedence**: operations within a job run in order (raw material → finished product)
- **Machine exclusivity**: only one job runs on each machine at a time
- **Sequence-dependent changeovers**: when a machine switches from one job to another, setup time is incurred; the optimal ordering across jobs on each machine is determined by the solver via a circuit (Hamiltonian path) constraint

The objective minimizes makespan — the time at which all jobs are complete — which directly maximizes throughput for a given set of orders.

## Configuration Options

| Option | Type | Default | Description |
| --- | --- | --- | --- |
| `time_limit` | float | `30.0` | Solver time limit in seconds |
| `num_workers` | int | `4` | Parallel CP-SAT search workers (1–8) |
| `changeover_weight` | float | `1.0` | Multiplier on all changeover times (0 = ignore changeovers, 2 = double all setup costs) |

## Input Format

Two CSV files placed in the same input directory.

### `jobs.csv` — operations for each job

| Column | Type | Description |
| --- | --- | --- |
| `job_id` | string | Product/job identifier |
| `sequence` | int | Order of this operation within the job (1 = first) |
| `machine` | string | Machine required for this operation |
| `duration` | int | Processing time in minutes |

```csv
job_id,sequence,machine,duration
product_A,1,drill,20
product_A,2,mill,15
product_A,3,grind,10
product_A,4,inspect,5
product_B,1,lathe,25
product_B,2,drill,12
```

### `changeovers.csv` — machine setup times when switching between jobs

| Column | Type | Description |
| --- | --- | --- |
| `machine` | string | Machine where the changeover occurs |
| `from_job` | string | Job currently on the machine |
| `to_job` | string | Job being set up next |
| `changeover` | int | Setup/cleaning time in minutes |

Any `(machine, from_job, to_job)` pair not listed defaults to 0.

```csv
machine,from_job,to_job,changeover
drill,product_A,product_B,8
drill,product_B,product_A,5
mill,product_A,product_C,10
```

## Output

**Solution** (`output/schedule.csv`): one row per operation with assigned start and end times.

| Column | Description |
| --- | --- |
| `job_id` | Job identifier |
| `step` | Zero-based step index within the job |
| `machine` | Machine the operation runs on |
| `start` | Start time (minutes from time 0) |
| `end` | End time |
| `duration` | Processing time |

**Metrics** (`metrics.json`):

| Metric | Description |
| --- | --- |
| `result_value` | Makespan — total time to complete all jobs (minutes) |
| `makespan` | Same as `result_value` |
| `avg_machine_utilization` | Average utilization across all machines (0–1) |
| `total_jobs` | Number of jobs scheduled |
| `total_tasks` | Total number of operations |
| `status` | Solver status: `optimal`, `suboptimal`, or `infeasible` |

**Visualizations**:
- **Gantt Chart** (tab 1): horizontal bars by machine, colored by job — shows the full schedule at a glance
- **Machine Utilization** (tab 2): bar chart of utilization percentage per machine

## Input Scenarios

| Directory | Description |
| --- | --- |
| `input/` | Default — 4 jobs, 5 machines, moderate changeovers |
| `inputs/small/` | 3 jobs, 3 machines — fast to solve, easy to inspect |
| `inputs/medium/` | 6 jobs, 5 machines |
| `inputs/large/` | 8 jobs, 6 machines (adds press) |
| `inputs/high-changeover/` | Same as medium with 3× changeover times — tests scheduling around setup costs |
| `inputs/no-changeover/` | Same as medium with zero changeovers — baseline comparison |

## Running Locally

```bash
# Default input
nextmv local run create --app-src . --input-dir input --wait

# Named scenarios
nextmv local run create --app-src . --input-dir inputs/small --name small --wait
nextmv local run create --app-src . --input-dir inputs/medium --name medium --wait
nextmv local run create --app-src . --input-dir inputs/large --name large --wait
nextmv local run create --app-src . --input-dir inputs/high-changeover --name high-changeover --wait
nextmv local run create --app-src . --input-dir inputs/no-changeover --name no-changeover --wait
```

## Syncing to Nextmv Cloud

```bash
nextmv local app sync --app-src . --target-app-id <cloud-app-id>
```
