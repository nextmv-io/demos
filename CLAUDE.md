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

Some apps use multi-file input/output instead (`input/` and `output/` directories); see the guide.

## How to build an app

Follow **`docs/creating-apps.md`**, one step at a time: manifest, `app.yaml`
(JSON vs multi-file formats, the `random_seed` option, valid
`option_type`/`control_type` pairs), `main.py`, `visuals.py`,
`requirements.txt`, inputs, local runs and sync, the README, then the Cloud
deploy and experiments. It also lists the preferred Apache-licensed tools by
category. The `nextmv_workflow_guide` MCP tool has the generic version.

Conventions that are easy to miss:
- Log with `nextmv.log(...)` (stderr), never `print`, so stdout stays the output.
- `slider` is only valid for `int`/`float`, `select` only for `string`; a wrong
  pair fails manifest validation.
- Ship a default `input.json` plus `inputs/` with 3–5 files that vary what
  matters (size, supply vs demand, constraint tightness), named for what varies
  (`tight-capacity.json`, not `test2.json`).
- README sections: title + one-line problem, Approach, Configuration Options,
  Input Format, Output, Running Locally, Syncing to Nextmv Cloud. Don't repeat
  the code; explain the options and metrics.
- Use the Nextmv MCP tools for local and Cloud runs. For multi-file apps pass
  `input_dir_path` with `content_format="multi-file"`.
- **Never update the `production` instance without asking the user.**

## Checklist before committing

- [ ] `app.yaml` has at least one user-facing configuration option (beyond input/output)
- [ ] `main.py` loads `manifest` and `options` via `nextmv.Manifest.from_yaml`
- [ ] Metrics follow the Rules above for the app type (`status` + `result_value` for optimization apps only)
- [ ] At least one Plotly visualization is included as a `nextmv.Asset`
- [ ] All solver/library dependencies are Apache 2.0 (or MIT/BSD) licensed
- [ ] `input.json` and `inputs/` are included and run locally
- [ ] `requirements.txt` has pinned versions
- [ ] Ran locally with the Nextmv MCP server: run `succeeded`, the quality metric is in range, and a non-default option value changed the result in the expected direction
- [ ] Synced local runs, pushed the app and cut a named version
- [ ] Updated `staging`, ran each input there, built an input set and ran an acceptance test vs `production`
- [ ] **Asked the user** before promoting `staging` to `production`
