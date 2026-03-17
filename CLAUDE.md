# Creating New Nextmv Apps

## Overview

This repo contains Nextmv demo apps that showcase Apache-licensed, open-source Python decision tools running on the Nextmv Cloud platform.

## Rules

- **License**: Only use Apache 2.0 licensed solvers and libraries (e.g., Pyomo, OR-Tools, HiGHS, CBC, GLPK). Avoid commercial solvers (Gurobi, Xpress, CPLEX) unless an explicit free/academic license is available and documented.
- **Metrics**: Every app must write metrics to a `metrics.json` (or report them via `nextmv.Output(metrics={...})`).
- **Visualization**: Every app must include at least one Plotly visualization rendered as a `nextmv.Asset`.
- **Configuration**: Every app must expose user-facing configuration options via `app.yaml`.

---

## File Structure

Each app lives in its own directory with this structure:

```
my-app/
├── app.yaml          # Nextmv manifest (required)
├── main.py           # Entry point
├── visuals.py        # Plotly visualization(s)
├── requirements.txt  # Python dependencies
├── input.json        # Sample input for local testing
└── README.md         # Short description and usage
```

---

## Step 1: Generate the App Manifest with the Nextmv CLI

Use the Nextmv CLI to scaffold the `app.yaml` manifest:

```bash
nextmv manifest init --type python
```

This creates a base `app.yaml`. Edit it to match the app's runtime, files, and options (see Step 2).

To validate the manifest at any time:

```bash
nextmv manifest validate
```

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
```

No `content` block is needed; JSON is the default.

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
output = nextmv.Output(
    solution={"assignments": [...]},
    assets=[chart],          # list of nextmv.Asset from visuals.py
    metrics={
        "result_value": objective_value,
        "status": "optimal",   # optimal | suboptimal | infeasible | unbounded
        "variables": num_vars,
        "constraints": num_constraints,
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
with open("metrics.json", "w") as f:
    json.dump({
        "result_value": objective_value,
        "status": "optimal",   # optimal | suboptimal | infeasible | unbounded
    }, f)

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

```
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
| `input.json` | Default — small/medium, used by `nextmv local run create` without flags |
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

### Run locally with the Nextmv CLI

The app is registered automatically on first run. Use `--app-src .` to point at the current directory, or `--app-id <id>` once it's registered.

```bash
# Run with the default input — app is auto-registered on first run
cat input.json | nextmv local run create --app-src . --wait

# Run a specific input with a name
cat inputs/large.json | nextmv local run create --app-src . --name large --wait

# Run all inputs in the inputs/ directory
for f in inputs/*.json; do
  cat $f | nextmv local run create --app-src . --name $(basename $f .json) --wait
done

# List all local runs for this app
nextmv local run list --app-src .

# View logs for a specific run
nextmv local run logs --app-src . --run-id <run-id>
```

### Sync local runs to Nextmv Cloud

Once runs look good locally, sync them to a Cloud app for sharing, experiments, and the UI.

```bash
# Sync all local runs to a Cloud app
nextmv local app sync --app-src . --target-app-id <cloud-app-id>

# Sync only specific runs
nextmv local app sync --app-src . --target-app-id <cloud-app-id> \
  --run-ids <run-id-1> --run-ids <run-id-2>

# Sync and associate runs with a specific Cloud instance (for experiments)
nextmv local app sync --app-src . --target-app-id <cloud-app-id> \
  --instance-id <instance-id>
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

**`## Running Locally`** — Commands to run with the Nextmv CLI:

```bash
# JSON format app
cat input.json | nextmv local run create --app-src . --wait
cat inputs/large.json | nextmv local run create --app-src . --name large --wait

# Multi-file app (run from the input directory)
nextmv local run create --app-src . --wait
```

**`## Syncing to Nextmv Cloud`**:

```bash
nextmv local app sync --app-src . --target-app-id <cloud-app-id>
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

### 1. Sync local runs to the Cloud app

Sync successful local runs so they are visible in the Cloud UI and can be used as inputs for scenario tests.

```bash
nextmv local app sync --app-src . --target-app-id <cloud-app-id>
```

### 2. Push the app

Push the app code to create a new deployable version. Use `--version-yes` to skip the interactive prompt.

```bash
# Push and create a new version (auto-generates version ID)
nextmv cloud app push --app-id <cloud-app-id> --version-yes

# Push with a specific version ID
nextmv cloud app push --app-id <cloud-app-id> --version-id v1.0.0
```

### 3. Create production and staging instances

Instances link a version to a set of default options. Create at minimum a `production` instance and a `staging` instance so you can compare them in tests.

```bash
# Production instance — conservative defaults
nextmv cloud instance create \
  --app-id <cloud-app-id> \
  --version-id <version-id> \
  --instance-id production \
  --name "Production"

# Staging instance — candidate config to test against production
nextmv cloud instance create \
  --app-id <cloud-app-id> \
  --version-id <version-id> \
  --instance-id staging \
  --name "Staging" \
  --options <option-name>=<value>
```

To update an existing instance to a new version:

```bash
nextmv cloud instance update \
  --app-id <cloud-app-id> \
  --instance-id staging \
  --version-id <new-version-id>
```

### 4. Run a scenario test

A scenario test runs one or more inputs against one or more instances and compares the results. Use this to validate that a new version or config change does not regress quality metrics.

Each scenario requires an `instance_id` and an `input_set` input (create input sets in the Cloud UI or via `nextmv cloud input-set`).

```bash
SCENARIO='{
  "instance_id": "staging",
  "scenario_input": {
    "scenario_input_type": "input_set",
    "scenario_input_data": {
      "input_id": "<input-id>",
      "input_set_id": "<input-set-id>"
    }
  }
}'

nextmv cloud scenario create \
  --app-id <cloud-app-id> \
  --name "Smoke test after deploy" \
  --scenarios "$SCENARIO" \
  --wait
```

To sweep multiple option values in a single test, add a `configuration` block:

```bash
SCENARIO='{
  "instance_id": "production",
  "scenario_input": {
    "scenario_input_type": "input_set",
    "scenario_input_data": {
      "input_id": "<input-id>",
      "input_set_id": "<input-set-id>"
    }
  },
  "configuration": [
    {"name": "<option-name>", "values": ["<value-1>", "<value-2>"]}
  ]
}'
```

### 5. Run a shadow test

A shadow test routes live traffic to both a baseline and one or more candidate instances simultaneously and compares their outputs. Use this to evaluate a new version or config against real production traffic before promoting.

```bash
COMPARISONS='{
  "production": ["staging"]
}'

nextmv cloud shadow create \
  --app-id <cloud-app-id> \
  --name "Staging vs Production" \
  --comparisons "$COMPARISONS" \
  --termination-maximum-runs 50

# Start the shadow test (if not using --start-time)
nextmv cloud shadow start --app-id <cloud-app-id> --shadow-test-id <shadow-test-id>

# Stop it early if needed
nextmv cloud shadow stop --app-id <cloud-app-id> --shadow-test-id <shadow-test-id>
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
- [ ] Ran locally with the Nextmv CLI and confirmed:
  - Run status is `succeeded` (not `failed`)
  - Quality metric is in the expected range
  - At least one non-default option value was tested (e.g. `-o penalty_unmet_demand=1000`) and the result changed in the expected direction

  **JSON format** — pipe input via stdin:

  ```bash
  nextmv local run create -i input.json --app-src . --wait
  ```

  **Multi-file format** — pass the input directory with `--input-dir`; do NOT pipe via stdin:

  ```bash
  nextmv local run create --app-src . --input-dir input --wait
  nextmv local run create --app-src . --input-dir inputs/large --name large --wait
  ```

- [ ] Synced local runs to Cloud app (`nextmv local app sync --app-src . --target-app-id <cloud-app-id>`)
- [ ] Pushed app to Cloud and created a new version (`nextmv cloud app push --app-id <cloud-app-id> --version-yes`)
- [ ] Created or updated `production` and `staging` instances with the new version
- [ ] Ran a scenario test against the production instance and confirmed metrics are within expected range
- [ ] (For config changes) Ran a shadow test comparing `staging` vs `production` before promoting
