# Creating New Nextmv Apps

## Overview

This repo contains Nextmv demo apps that showcase Apache-licensed, open-source Python decision tools running on the Nextmv Cloud platform.

## Rules

- **License**: Only use Apache 2.0 licensed solvers and libraries (e.g., Pyomo, OR-Tools, HiGHS, CBC, GLPK). Avoid commercial solvers (Gurobi, Xpress, CPLEX) unless an explicit free/academic license is available and documented.
- **Metrics**: Every app must write metrics to a `metrics.json` (or report them via `nextmv.Output(metrics={...})`).
  - **Optimization apps** (MIP, LP, CP, heuristics): use `status` (`optimal` | `suboptimal` | `infeasible` | `unbounded`) and `result_value` (objective value). Do NOT use these fields in ML or predictive apps.
  - **ML classifier apps**: omit `status`/`result_value`; instead include `accuracy`, `precision`, `recall`, `f1_score`, `roc_auc`, `log_loss`, and confusion matrix counts (`true_positives`, `true_negatives`, `false_positives`, `false_negatives`).
  - **ML regression / forecasting apps**: omit `status`/`result_value`; instead include `rmse`, `mae`, `r2`, and any domain-relevant metrics (e.g. `mape` for forecasting).
  - **Simulation / rules-engine apps**: use domain-specific metrics (e.g. throughput, utilization, queue length); no `status`/`result_value` unless the model includes an optimization objective.
- **Visualization**: Every app must include at least one Plotly visualization rendered as a `nextmv.Asset`.
- **Configuration**: Every app must expose user-facing configuration options via `app.yaml`. Any app that uses a random seed internally must expose a `random_seed` option (`option_type: int`, not required, no default) so results can be reproduced on demand.
- **Cloud Links**: Always provide a clickable link to any Nextmv Cloud resource when it is created or referenced (runs, apps, scenario tests, acceptance tests, input sets, instances, etc.). Use these URL patterns:
  - App: `https://cloud.nextmv.io/acc/{account-id}/app/{app-id}`
  - Run: `https://cloud.nextmv.io/acc/{account-id}/app/{app-id}/run?id={run-id}`
  - Scenario test: `https://cloud.nextmv.io/acc/{account-id}/app/{app-id}/experiments/scenario`
  - Acceptance test: `https://cloud.nextmv.io/acc/{account-id}/app/{app-id}/experiments/acceptance`
  - Batch experiment: `https://cloud.nextmv.io/acc/{account-id}/app/{app-id}/experiments/batch`
  - Input set: `https://cloud.nextmv.io/acc/{account-id}/app/{app-id}/input-sets`
  - Instance: `https://cloud.nextmv.io/acc/{account-id}/app/{app-id}/instances`
  - Use account ID `cd1ce146-1bf2-461a-83d0-20ba107387e5` for the mooney profile

---

## File Structure

Each app lives in its own directory with this structure:

```md
my-app/
├── app.yaml          # Nextmv manifest (required)
├── main.py           # Entry point
├── visuals.py        # Plotly visualization(s)
├── requirements.txt  # Python dependencies
├── input.json        # Sample input for local testing
└── README.md         # Short description and usage
```

---

## Step 1: Create the App Manifest

Use `mcp__nextmv__manifest_init` to scaffold an `app.yaml`, then edit it to match your app's options and content format:

```python
mcp__nextmv__manifest_init(manifest_type="python", content_format="json", dirpath="my-app")
# or for multi-file:
mcp__nextmv__manifest_init(manifest_type="python", content_format="multi-file", dirpath="my-app")
```

The generated file is a starting point — replace the placeholder options with your app's actual options per the templates in Step 2.

---

## Step 2: Write app.yaml

The manifest configures runtime, files, content format, and user-facing options.

### Content format: JSON (default)

Input is a single JSON file read from stdin; output is written to stdout as a single JSON object. Use this for most apps — it is simpler and works well with `nextmv.load` / `nextmv.write`.

```yaml
type: python
runtime: ghcr.io/nextmv-io/runtime/python:3.11
python:
  pip-requirements: requirements.txt

files:
  - main.py
  - visuals.py

configuration:
  options:
    strict: false
    items:
      - name: input
        option_type: string
        default: ''
        required: false
        ui:
          control_type: input
          hidden_from:
            - operator
      - name: output
        option_type: string
        default: ''
        required: false
        ui:
          control_type: input
          hidden_from:
            - operator
```

No `content` block is needed; JSON is the default. The `input` and `output` options are required so that `nextmv.load(options=options, path=options.input)` works correctly.

### Content format: multi-file

Input and output are directories of files. Use this when the solver writes its own output files (e.g., Pyomo, AMPL) or when you need to separate solution files, csv, text, or excel.

```yaml
type: python
runtime: ghcr.io/nextmv-io/runtime/python:3.11
python:
  pip-requirements: requirements.txt

files:
  - main.py
  - visuals.py

configuration:
  content:
    format: multi-file
    multi-file:
      input:
        path: .
      output:
        solutions: .
        metrics: metrics.json
        assets: assets.json
  options:
    strict: true
    validation:
      enforce: all
    items:
      - name: option_1_slider
        option_type: int
        default: 10
        required: true
        additional_attributes:
          min: 0
          max: 100
          step: 10
        ui:
          control_type: slider
          display_name: Option 1 Slider
      - name: option_1_input
        option_type: int
        default: 10
        required: true
        additional_attributes:
          min: 0
          max: 100
          step: 1
        ui: 
          hidden_from:
            - operator
          control_type: input
      - name: option_2
        option_type: string
        additional_attributes:
          values:
            - choice_1
            - choice_2
            - choice_3
        ui:
          control_type: select
          display_name: Option 2
      - name: option_2_default
        option_type: string
        default: choice_2
        additional_attributes:
          values:
            - choice_1
            - choice_2
            - choice_3
        ui:
          control_type: select
      - name: option_3
        option_type: bool
        default: true
        required: true
      - name: option_4
        option_type: float
        ui:
          control_type: input
          hidden_from:
            - operator
      - name: option_4_slider
        option_type: float
        additional_attributes:
          min: 0
          max: 10
          step: 0.1
        ui:
          control_type: slider
```

### Random seed option

Any app that uses a random seed must expose it as an optional, unhidden option with no default so users can reproduce specific results:

```yaml
- name: random_seed
  option_type: int
  required: false
  ui:
    control_type: input
    display_name: Random Seed (optional, for reproducibility)
```

In code, use `None` as the fallback so the library picks a random seed when unset:

```python
seed = options.random_seed if options.random_seed else None
```

### Option types and valid control_types

| `option_type` | Valid `control_type` values | Default | Notes |
| --- | --- | --- | --- |
| `string` | `input`, `select`, `multiselect` | `input` | Use `additional_attributes.values` for `select`/`multiselect` |
| `int` | `input`, `slider` | `input` | Use `additional_attributes` for `min`, `max`, `step` |
| `float` | `input`, `slider` | `input` | Same as `int` |
| `bool` | `toggle` | `toggle` | No additional attributes needed |

> Using an invalid `control_type` for a given `option_type` will cause a manifest validation error. For example, `slider` is not valid for `string`, and `select` is not valid for `int`.

---

## Step 3: Write main.py

### Load manifest and options

```python
import nextmv

manifest = nextmv.Manifest.from_yaml(".")
options = manifest.extract_options()
```

Access options as attributes: `options.solver`, `options.time_limit`, etc.

### JSON format — load input and write output

Single JSON in via stdin, single JSON out via stdout.

```python
# Load
input = nextmv.load(options=options, path=options.input)
data = input.data  # dict parsed from input.json

# Redirect solver logs away from stdout
nextmv.redirect_stdout()

# Write
# Optimization app — use status + result_value
output = nextmv.Output(
    solution={"assignments": [...]},
    assets=[chart],          # list of nextmv.Asset from visuals.py
    metrics={
        "result_value": objective_value,   # optimization apps only
        "status": "optimal",               # optimal | suboptimal | infeasible | unbounded — optimization apps only
        "variables": num_vars,
        "constraints": num_constraints,
    },
)

# ML / predictive app — do NOT use status or result_value; use model metrics instead
output = nextmv.Output(
    solution={"predictions": [...]},
    assets=[chart],
    metrics={
        # Classifier
        "accuracy": 0.91, "precision": 0.88, "recall": 0.85,
        "f1_score": 0.86, "roc_auc": 0.94, "log_loss": 0.32,
        "true_positives": 42, "true_negatives": 130,
        "false_positives": 6, "false_negatives": 8,
        # Regressor / forecaster (use instead of classifier metrics)
        # "rmse": 12.4, "mae": 9.1, "r2": 0.87, "mape": 0.08,
    },
)

nextmv.write(output, path=options.output)
```

### Multi-file format — load input and write output

Input files are read from a directory; output files (solution, metrics, assets) are written to disk separately. Do NOT call `nextmv.load` — read input files directly (CSV, JSON, etc.) and write output files explicitly.

```python
import csv, json, os

# Read input — read files directly; working directory is the input path
with open("orders.csv", newline="") as f:
    rows = list(csv.DictReader(f))

# ... run solver or rules engine ...

# Write solution file — create the output dir first
os.makedirs("output", exist_ok=True)
with open("output/results.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=[...])
    writer.writeheader()
    writer.writerows(results)

# Write metrics.json as a plain dict
# Optimization apps: use result_value + status
with open("metrics.json", "w") as f:
    json.dump({
        "result_value": objective_value,
        "status": "optimal",   # optimal | suboptimal | infeasible | unbounded — optimization only
    }, f)
# ML/predictive apps: use model metrics instead (no status/result_value)

# Write assets.json — must be {"assets": [...]} at the top level
# Each asset's visual uses "schema" and "type" (not "visual_schema"/"visual_type")
with open("assets.json", "w") as f:
    json.dump(
        {
            "assets": [
                {
                    "name": a.name,
                    "content_type": a.content_type,
                    "visual": {
                        "schema": a.visual.visual_schema.value,
                        "type": a.visual.visual_type,
                        "label": a.visual.label,
                    },
                    "content": a.content,  # keep as list
                }
                for a in [chart1, chart2]
            ]
        },
        f,
    )
```

> **Multi-file asset format gotchas:**
>
> - Top level of `assets.json` must be `{"assets": [...]}` — a bare list will crash the CLI
> - Inside each asset, `visual.schema` and `visual.type` — NOT `visual_schema`/`visual_type`
> - `content` stays as a list (do not unwrap with `[0]`)
> - Do NOT use `asset.model_dump()` — it serializes `VisualSchema` as a flat string, breaking the schema field

### Logging

Use `nextmv.log(...)` (writes to stderr, not stdout) for progress messages.

---

## Step 4: Write visuals.py

Every app needs at least one Plotly chart returned as a `nextmv.Asset`.

```python
import json
import nextmv
import plotly.graph_objects as go


def build_chart(solution, input_data, label="Solution", tab_order=1) -> nextmv.Asset:
    fig = go.Figure()

    # --- build your Plotly figure here ---
    fig.add_trace(go.Scatter(...))
    fig.update_layout(title=label)
    # -------------------------------------

    return nextmv.Asset(
        name=label,
        content_type="json",
        visual=nextmv.Visual(
            visual_schema=nextmv.VisualSchema(value="plotly"),
            visual_type="custom-tab",
            label=label,
            tab_order=tab_order,
        ),
        content=[json.loads(fig.to_json())],
    )
```

- Use `tab_order=1` for the first chart, incrementing for each additional chart.
- Provide both an **input chart** (tab 1) and an **output/solution chart** (tab 2) where meaningful.

---

## Step 5: Write requirements.txt

Pin all dependencies. Always include `nextmv` and `plotly`. Use Apache-licensed solvers only.

```txt
nextmv==1.2.0
plotly==6.5.2
numpy==2.2.0
# Solver options (Apache-licensed):
highspy==1.7.2      # HiGHS via Python
pyomo==6.8.0        # modeling layer (works with highs, cbc, glpk)
# ortools==9.10.4067  # Google OR-Tools (Apache 2.0)
```

---

## Step 6: Create Input Files

Every app must include a default `input.json` at the root plus an `inputs/` directory with **3–5 files of varying sizes**. This enables local testing across problem scales and supports experiment runs on Nextmv Cloud.

### Required inputs

| File | Purpose |
| --- | --- |
| `input.json` | Default — small/medium, used by `mcp__nextmv__local_run` without specifying an input directory |
| `inputs/small.json` | Smallest meaningful problem — fast solver, easy to inspect |
| `inputs/medium.json` | Representative mid-size instance |
| `inputs/large.json` | Stress test — larger problem, longer solve time |
| `inputs/supply-constrained.json` | Scenario where supply < demand — tests penalty behavior |
| `inputs/supply-surplus.json` | Scenario where supply >> demand — tests cost minimization |

Vary the scenario axes that matter for your problem: problem size (nodes, items, periods), supply/demand balance, tightness of constraints, time horizons, etc.

### Naming convention

Use descriptive names that reflect what varies, not just size:

- `small.json`, `medium.json`, `large.json` — for scale
- `tight-capacity.json`, `relaxed-capacity.json` — for constraint tightness
- `peak-demand.json`, `off-peak.json` — for scenario type

---

## Step 7: Local Testing and Cloud Sync

### Run locally with the Nextmv MCP server

Use `mcp__nextmv__local_run` to run the app and wait for the result, or `mcp__nextmv__local_run_submit` for a non-blocking submit.

**JSON format** — pass the parsed JSON object as `input`:

```python
# Run with the default input and wait
mcp__nextmv__local_run(app_dir=".", input=<parsed input.json>)

# Run with a specific input and solver options
mcp__nextmv__local_run(
  app_dir=".",
  input=<parsed inputs/large.json>,
  run_options={"solve.duration": "30s"}
)

# Submit without waiting (returns run_id)
mcp__nextmv__local_run_submit(app_dir=".", input=<parsed input.json>)
```

**Multi-file format** — pass the input directory path as `input_dir`:

```python
# Run with the default input directory
mcp__nextmv__local_run(app_dir=".", input_dir="input")

# Run a named input directory
mcp__nextmv__local_run(app_dir=".", input_dir="inputs/large")
```

**List and inspect runs:**

```python
# List all local runs for this app
mcp__nextmv__local_list_runs(app_dir=".")

# View logs for a specific run
mcp__nextmv__local_run_logs(app_dir=".", run_id="<run-id>")

# Check status of a submitted run
mcp__nextmv__local_run_status(app_dir=".", run_id="<run-id>")

# Get path to the result file of a completed run
mcp__nextmv__local_run_result(app_dir=".", run_id="<run-id>")

# Poll until a submitted run completes and return the result path
mcp__nextmv__local_run_poll_result(app_dir=".", run_id="<run-id>")

# Get the input data used in a local run
mcp__nextmv__local_run_input(app_dir=".", run_id="<run-id>")
```

### Sync local runs to Nextmv Cloud

Once runs look good locally, sync them to a Cloud app using `mcp__nextmv__local_sync`.

```python
# Sync all local runs to a Cloud app
mcp__nextmv__local_sync(app_dir=".", cloud_app_id="<cloud-app-id>")

# Sync only specific runs
mcp__nextmv__local_sync(
  app_dir=".",
  cloud_app_id="<cloud-app-id>",
  run_ids=["<run-id-1>", "<run-id-2>"]
)

# Sync and associate runs with a specific Cloud instance (for experiments)
mcp__nextmv__local_sync(
  app_dir=".",
  cloud_app_id="<cloud-app-id>",
  instance_id="<instance-id>"
)
```

---

## Preferred Open-Source Tools (Apache 2.0)

### Mathematical Programming & Solvers

| Tool | License | Use case |
| --- | --- | --- |
| [Pyomo](https://www.pyomo.org/) | BSD | MIP/LP modeling language |
| [OR-Tools](https://developers.google.com/optimization) | Apache 2.0 | Routing, scheduling, CP-SAT |
| [HiGHS](https://highs.dev/) | MIT | LP/MIP solver |
| [CBC](https://github.com/coin-or/Cbc) | EPL | LP/MIP solver |
| [GLPK](https://www.gnu.org/software/glpk/) | GPL | LP/MIP solver (GPL — use only if acceptable) |
| [NetworkX](https://networkx.org/) | BSD | Graph/network problems |

### Simulation

| Tool | License | Use case |
| --- | --- | --- |
| [SimPy](https://simpy.readthedocs.io/) | MIT | Discrete-event simulation (queues, workflows, resources) |
| [Salabim](https://www.salabim.org/) | MIT | Discrete-event simulation with built-in animation support |
| [Mesa](https://mesa.readthedocs.io/) | Apache 2.0 | Agent-based modeling and simulation |
| [NumPy](https://numpy.org/) | BSD | Monte Carlo and stochastic simulation |

### Heuristics & Metaheuristics

| Tool | License | Use case |
| --- | --- | --- |
| [DEAP](https://deap.readthedocs.io/) | LGPL | Genetic algorithms, evolutionary strategies, GP |
| [pymoo](https://pymoo.org/) | Apache 2.0 | Multi-objective optimization (NSGA-II, NSGA-III, etc.) |
| [Optuna](https://optuna.org/) | MIT | Bayesian/black-box optimization, hyperparameter search |
| [scikit-opt](https://github.com/guofei9987/scikit-opt) | MIT | GA, PSO, simulated annealing, ant colony, tabu search |
| [mealpy](https://mealpy.readthedocs.io/) | MIT | 200+ metaheuristic algorithms (swarm, evolutionary, physics-based) |

### Rules Engines

| Tool | License | Use case |
| --- | --- | --- |
| [Experta](https://experta.readthedocs.io/) | Apache 2.0 | Forward-chaining rules engine (CLIPS-style); business logic |
| [business-rules](https://github.com/venmo/business-rules) | MIT | Declarative rules engine with operator/condition/action model |
| [durable_rules](https://github.com/jruizgit/rules) | MIT | Stateful, event-driven rules engine with pattern matching |

### General

| Tool | License | Use case |
| --- | --- | --- |
| [scikit-learn](https://scikit-learn.org/) | BSD | ML/clustering for demand forecasting, classification |
| [Plotly](https://plotly.com/python/) | MIT | Visualization (required for all apps) |

---

## Step 8: Write README.md

Every app must include a `README.md` in its directory. Keep it concise — the goal is to quickly orient someone to what the app does and how to run it.

### Required sections

The README should contain the following sections:

**`# App Name`** — One-sentence description of the decision problem being solved.

**`## Approach`** — Describe the modeling approach or framework (e.g., LP via Pyomo/HiGHS, declarative rules via business-rules). Mention key design choices.

**`## Configuration Options`** — Table of options with name, type, default, and description.

**`## Input Format`** — Describe JSON fields/types or CSV columns. Include a short example.

**`## Output`** — Describe the solution file(s), metrics reported in `metrics.json`, and the Plotly visualizations.

**`## Running Locally`** — MCP tool calls to run the app:

```python
# JSON format app
mcp__nextmv__local_run(app_dir=".", input=<parsed input.json>)
mcp__nextmv__local_run(app_dir=".", input=<parsed inputs/large.json>)

# Multi-file app
mcp__nextmv__local_run(app_dir=".", input_dir="input")
```

**`## Syncing to Nextmv Cloud`**:

```python
mcp__nextmv__local_sync(app_dir=".", cloud_app_id="<cloud-app-id>")
```

### README tips

- Do not repeat content that is obvious from the code.
- Focus on options and how to use them.
- Explain the metrics.
- Link to the tool or solver documentation for readers unfamiliar with it.
- For multi-file apps, clarify which directory to run from and where output files appear.

---

## Step 9: Deploy to Nextmv Cloud

Once local tests pass, deploy the app to Nextmv Cloud, set up instances, and run tests to validate behavior before and after changes.

### 0. Create the Cloud app (first time only)

```python
mcp__nextmv__cloud_create_app(name="My App Name", app_id="my-app-id", description="What this app does")
```

The `app_id` becomes the URL-friendly identifier used in all subsequent calls. It is auto-generated from the name if omitted.

### 1. Sync local runs to the Cloud app

Sync successful local runs so they are visible in the Cloud UI and can be used as inputs for scenario tests.

```python
mcp__nextmv__local_sync(app_dir=".", cloud_app_id="<cloud-app-id>")
```

### 2. Push the app and create a named version

Use `mcp__nextmv__cloud_push_app` to upload the local directory, then `mcp__nextmv__cloud_create_version` to tag the push as a named version.

```python
# Push the app code
mcp__nextmv__cloud_push_app(app_id="<cloud-app-id>", app_dir=".")

# Create a named version (version_id is auto-generated if omitted)
mcp__nextmv__cloud_create_version(
  app_id="<cloud-app-id>",
  name="v1.0",
  description="Initial release"
)
```

The returned `version_id` (e.g. `version-b4w8qco4`) is used when creating or updating instances below.

### 4. Create cloud runs from all inputs

After the first push, create cloud runs on the `latest` instance using each input. Use `mcp__nextmv__cloud_run` (blocking) or `mcp__nextmv__cloud_run_submit` (non-blocking) depending on whether you need to wait for the result.

**JSON format** — pass the parsed JSON object as `input`:

```python
# Run default input (blocking — waits for result)
mcp__nextmv__cloud_run(app_id="<cloud-app-id>", instance_id="latest", input=<parsed input.json>)

# Run each input in inputs/
mcp__nextmv__cloud_run(app_id="<cloud-app-id>", instance_id="latest", input=<parsed inputs/small.json>)
mcp__nextmv__cloud_run(app_id="<cloud-app-id>", instance_id="latest", input=<parsed inputs/large.json>)

# Submit without waiting (returns run_id immediately)
mcp__nextmv__cloud_run_submit(app_id="<cloud-app-id>", instance_id="latest", input=<parsed input.json>)
```

**Multi-file format** — pass the local directory path as `input_dir_path` with `content_format="multi-file"`:

```python
# Run default input directory (blocking)
mcp__nextmv__cloud_run(app_id="<cloud-app-id>", instance_id="latest", input_dir="input")

# Submit without waiting
mcp__nextmv__cloud_run_submit(
  app_id="<cloud-app-id>",
  instance_id="latest",
  input_dir_path="inputs/large",
  content_format="multi-file"
)
```

**Inspect cloud runs:**

```python
# Check status of a submitted run (also returns metrics when succeeded)
mcp__nextmv__cloud_run_status(app_id="<cloud-app-id>", run_id="<run-id>")

# Get full result of a completed run (saves to temp file)
mcp__nextmv__cloud_run_result(app_id="<cloud-app-id>", run_id="<run-id>")

# Get logs snapshot (use for completed runs)
mcp__nextmv__cloud_run_logs(app_id="<cloud-app-id>", run_id="<run-id>")

# Get the input that was submitted to a run
mcp__nextmv__cloud_run_input(app_id="<cloud-app-id>", run_id="<run-id>")

# Cancel a run
mcp__nextmv__cloud_cancel_run(app_id="<cloud-app-id>", run_id="<run-id>")
```

`mcp__nextmv__cloud_poll_run_logs` is not yet implemented — use repeated `mcp__nextmv__cloud_run_status` calls to wait for completion instead.

### 5. Create production and staging instances

Instances link a version to a set of default options. Create at minimum a `production` instance and a `staging` instance so you can compare them in tests.

```python
# Production instance — conservative defaults
mcp__nextmv__cloud_create_instance(
  app_id="<cloud-app-id>",
  version_id="<version-id>",
  instance_id="production",
  name="Production"
)

# Staging instance — candidate config to test against production
mcp__nextmv__cloud_create_instance(
  app_id="<cloud-app-id>",
  version_id="<version-id>",
  instance_id="staging",
  name="Staging",
  configuration={"options": {"<option-name>": "<value>"}}
)
```

To update an existing instance to a new version:

```python
mcp__nextmv__cloud_update_instance(
  app_id="<cloud-app-id>",
  instance_id="staging",
  version_id="<new-version-id>"
)
```

### 6. Create an input set

An input set collects inputs for use in batch experiments and acceptance tests. Create one from recent runs on an instance, from specific run IDs, or from managed inputs.

```python
# From recent runs on an instance (default: up to 20 runs)
mcp__nextmv__cloud_create_input_set(
  app_id="<cloud-app-id>",
  name="My input set",
  instance_id="latest",
  maximum_runs=10
)

# From specific run IDs (preferred — use the staging run IDs from step 4)
mcp__nextmv__cloud_create_input_set(
  app_id="<cloud-app-id>",
  name="My input set",
  run_ids=["<run-id-1>", "<run-id-2>"]
)
```

The returned `input_set_id` is used in scenario tests, acceptance tests, and batch experiments below.

### 7. Run a batch experiment

A batch experiment runs the app against every input in an input set, optionally sweeping multiple option configurations side by side.

```python
mcp__nextmv__cloud_create_batch(
  app_id="<cloud-app-id>",
  input_set_id="<input-set-id>",
  name="Config comparison",
  option_sets={
    "fast": {"solve.duration": "5s"},
    "thorough": {"solve.duration": "60s"}
  }
)
```

### 8. Run a scenario test

A scenario test runs one or more inputs against one or more instances and compares the results. Use this to validate that a new version or config change does not regress quality metrics.

Each scenario requires an `instance_id` and a `scenario_input`.

```python
mcp__nextmv__cloud_create_scenario_test(
  app_id="<cloud-app-id>",
  name="Smoke test after deploy",
  scenarios=[
    {
      "instance_id": "staging",
      "scenario_input": {
        "scenario_input_type": "input_set",
        "scenario_input_data": {
          "input_id": "<input-id>",
          "input_set_id": "<input-set-id>"
        }
      }
    }
  ]
)
```

To sweep multiple option values in a single test, add a `configuration` list to the scenario:

```python
mcp__nextmv__cloud_create_scenario_test(
  app_id="<cloud-app-id>",
  name="Option sweep",
  scenarios=[
    {
      "instance_id": "production",
      "scenario_input": {
        "scenario_input_type": "input_set",
        "scenario_input_data": {"input_id": "<input-id>", "input_set_id": "<input-set-id>"}
      },
      "configuration": [
        {"name": "<option-name>", "values": ["<value-1>", "<value-2>"]}
      ]
    }
  ]
)
```

### 9. Run an acceptance test

An acceptance test runs both a candidate and baseline instance against the same input set and compares results using defined metrics to determine whether the candidate meets acceptance criteria.

```python
mcp__nextmv__cloud_create_acceptance_test(
  app_id="<cloud-app-id>",
  name="Staging vs Production quality check",
  candidate_instance_id="staging",
  baseline_instance_id="production",
  input_set_id="<input-set-id>",
  metrics=[
    {
      "field": "result_value",
      "metric_type": "direct-comparison",  # only valid value
      "statistic": "mean",
      "params": {
        "operator": "le"  # operator goes inside params: gt, ge, lt, le, eq, ne
      }
    }
  ]
)
```

> The acceptance test auto-runs on creation. Poll `mcp__nextmv__cloud_get_acceptance_test` until `status == "completed"`, then check `results.passed`.

### 10. Run a shadow test

A shadow test routes live traffic to both a baseline and one or more candidate instances simultaneously and compares their outputs. Use this to evaluate a new version or config against real production traffic before promoting.

```python
# Create the shadow test
mcp__nextmv__cloud_create_shadow_test(
  app_id="<cloud-app-id>",
  name="Staging vs Production",
  comparisons={"production": ["staging"]},
  termination_events={"maximum_runs": 50}
)

# Start the shadow test
mcp__nextmv__cloud_start_shadow_test(app_id="<cloud-app-id>", shadow_test_id="<shadow-test-id>")

# Stop it early if needed
mcp__nextmv__cloud_stop_shadow_test(app_id="<cloud-app-id>", shadow_test_id="<shadow-test-id>")
```

### 11. Run a switchback test

A switchback test alternates live traffic between baseline and candidate instances over fixed time periods. Use this when shadow testing is insufficient and you want to measure real-world impact in alternating windows.

```python
# Create the switchback test (alternates every 60 minutes, 6 total units)
mcp__nextmv__cloud_create_switchback_test(
  app_id="<cloud-app-id>",
  name="Staging vs Production switchback",
  baseline_instance_id="production",
  candidate_instance_id="staging",
  unit_duration_minutes=60.0,
  units=6
)

# Start the switchback test
mcp__nextmv__cloud_start_switchback_test(app_id="<cloud-app-id>", switchback_test_id="<switchback-test-id>")

# Stop it early if needed
mcp__nextmv__cloud_stop_switchback_test(app_id="<cloud-app-id>", switchback_test_id="<switchback-test-id>")
```

---

## Checklist Before Committing

- [ ] `app.yaml` has at least one user-facing configuration option (beyond input/output)
- [ ] `main.py` loads `manifest` and `options` via `nextmv.Manifest.from_yaml`
- [ ] Metrics are reported in `nextmv.Output(metrics={...})` (include `status` and `result_value` at minimum)
- [ ] At least one Plotly visualization is included as a `nextmv.Asset`
- [ ] All solver/library dependencies are Apache 2.0 (or MIT/BSD) licensed
- [ ] `input.json` sample is included and works locally
- [ ] `requirements.txt` has pinned versions
- [ ] Ran locally with the Nextmv MCP server and confirmed:
  - Run status is `succeeded` (not `failed`)
  - Quality metric is in the expected range
  - At least one non-default option value was tested (e.g. `run_options={"penalty_unmet_demand": "1000"}`) and the result changed in the expected direction

  **JSON format**: `mcp__nextmv__local_run(app_dir=".", input=<parsed input.json>)`

  **Multi-file format**: `mcp__nextmv__local_run(app_dir=".", input_dir="input")`

- [ ] Synced local runs to Cloud app (`mcp__nextmv__local_sync(app_dir=".", cloud_app_id="<cloud-app-id>")`)
- [ ] Pushed app (`mcp__nextmv__cloud_push_app(app_id="<cloud-app-id>", app_dir=".")`) and cut a named version (`mcp__nextmv__cloud_create_version(app_id="<cloud-app-id>", name="v1.0")`)
- [ ] Updated `staging` instance to the new version (`mcp__nextmv__cloud_update_instance(app_id="<cloud-app-id>", instance_id="staging", version_id="<version-id>")`)
- [ ] Created sample runs on `staging` for each input and confirmed results look correct
- [ ] Created an input set from staging runs (`mcp__nextmv__cloud_create_input_set(app_id="<cloud-app-id>", instance_id="staging")`)
- [ ] Ran an acceptance test comparing `staging` (candidate) vs `production` (baseline) and reviewed results
- [ ] **Asked the user** whether to promote `staging` to `production` — do NOT update the `production` instance without explicit confirmation
- [ ] (If approved) Updated `production` instance to the new version (`mcp__nextmv__cloud_update_instance(app_id="<cloud-app-id>", instance_id="production", version_id="<version-id>")`)
