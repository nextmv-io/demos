# Credit Scoring

Scores loan applicants using a machine learning classifier trained on historical loan data, and outputs approve/review/deny decisions based on configurable probability thresholds.

## Approach

The app trains a scikit-learn classifier (logistic regression, random forest, or gradient boosting) on labeled historical loan records where the outcome (`defaulted: true/false`) is known. It then scores new applicants by predicting their probability of **not** defaulting — the approval score. Applicants above the approval threshold are approved; those between the two thresholds are flagged for manual review; the rest are denied.

See [scikit-learn documentation](https://scikit-learn.org/stable/) for details on the classifiers.

## Configuration Options

| Name | Type | Default | Description |
|---|---|---|---|
| `model_type` | string (select) | `random_forest` | Classifier: `logistic_regression`, `random_forest`, or `gradient_boosting` |
| `n_estimators` | int (slider, 10–300) | `100` | Number of trees (ignored for logistic regression) |
| `approval_threshold` | float (slider, 0.5–0.95) | `0.7` | Minimum approval score to approve an applicant |
| `review_threshold` | float (slider, 0.1–0.65) | `0.4` | Minimum approval score to flag for manual review |

## Input Format

JSON with two fields:

- `historical_data`: array of past loans used to train the model. Each record must include all applicant features plus `defaulted` (bool).
- `applicants`: array of new applicants to score. Same features, without `defaulted`. Optional `id` and `name` fields are passed through to the output.

**Applicant features:**

| Field | Type | Description |
|---|---|---|
| `age` | int | Applicant age |
| `annual_income` | int | Annual income in dollars |
| `employment_length_years` | int | Years at current employer |
| `debt_to_income_ratio` | float | Total debt payments / gross income |
| `credit_history_length_years` | int | Length of credit history |
| `num_delinquencies_last_2_years` | int | Number of delinquencies in past 2 years |
| `loan_amount` | int | Requested loan amount |
| `loan_purpose` | string | One of: `personal`, `auto`, `home_improvement`, `debt_consolidation`, `business` |

**Example:**
```json
{
  "historical_data": [
    {
      "age": 45, "annual_income": 80000, "employment_length_years": 5,
      "debt_to_income_ratio": 0.25, "credit_history_length_years": 12,
      "num_delinquencies_last_2_years": 0, "loan_amount": 15000,
      "loan_purpose": "auto", "defaulted": false
    }
  ],
  "applicants": [
    {
      "id": 1, "name": "Jordan Lee",
      "age": 38, "annual_income": 95000, "employment_length_years": 8,
      "debt_to_income_ratio": 0.2, "credit_history_length_years": 14,
      "num_delinquencies_last_2_years": 0, "loan_amount": 20000,
      "loan_purpose": "home_improvement"
    }
  ]
}
```

## Output

**Solution:** `decisions` array with one entry per applicant:
- `applicant_id`, `name`
- `approval_score`: probability of no default (0–1)
- `decision`: `approved`, `review`, or `denied`

**Metrics:**

| Metric | Description |
|---|---|
| `result_value` | Approval rate (fraction of applicants approved) |
| `model_accuracy` | Accuracy on held-out 20% of historical data |
| `num_approved` / `num_review` / `num_denied` | Decision counts |
| `approval_rate` | Same as `result_value` |
| `model_type` | Classifier used |
| `status` | Always `optimal` |

**Visualizations:**
- **Tab 1 — Credit Score Distribution:** Histogram of approval scores colored by decision (approved/review/denied)
- **Tab 2 — Feature Importance:** Horizontal bar chart of relative feature importances

## Running Locally

```bash
cat input.json | nextmv local run create --app-src . --wait
cat inputs/large.json | nextmv local run create --app-src . --name large --wait
cat inputs/high-risk.json | nextmv local run create --app-src . --name high-risk --wait
cat inputs/low-risk.json | nextmv local run create --app-src . --name low-risk --wait
```

Try a stricter approval threshold:
```bash
cat input.json | nextmv local run create --app-src . --wait -o approval_threshold=0.85
```

## Syncing to Nextmv Cloud

```bash
nextmv local app sync --app-src . --target-app-id <cloud-app-id>
```
