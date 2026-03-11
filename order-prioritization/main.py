import csv
import json
import os

import nextmv
from business_rules import run_all

from rules import OrderActions, OrderVariables, get_rules
from visuals import priority_breakdown_chart, priority_scatter_chart

PRIORITIES = ["expedite", "standard", "defer"]


def read_orders(path="orders.csv") -> list:
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        return [
            {
                "id": row["id"],
                "value": float(row["value"]),
                "days_until_deadline": int(row["days_until_deadline"]),
                "customer_tier": row["customer_tier"],
                "units": int(row["units"]),
            }
            for row in reader
        ]


def write_results(results: list, path="output/results.csv") -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fieldnames = ["id", "value", "days_until_deadline", "customer_tier", "units", "priority"]
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)


def main() -> None:
    """Entry point for the order prioritization rules engine."""

    manifest = nextmv.Manifest.from_yaml(".")
    options = manifest.extract_options()

    orders = read_orders("orders.csv")

    nextmv.log(f"Orders: {len(orders)}")
    nextmv.log(f"Rule set: {options.rule_set}")
    nextmv.log(f"Expedite deadline threshold: {options.expedite_deadline_days} days")
    nextmv.log(f"Standard deadline threshold: {options.standard_deadline_days} days")

    rules = get_rules(options.rule_set, options)

    results = []
    for order in orders:
        variables = OrderVariables(order)
        actions = OrderActions(order)
        run_all(
            rule_list=rules,
            defined_variables=variables,
            defined_actions=actions,
            stop_on_first_trigger=True,
        )
        results.append({**order, "priority": actions.priority})

    counts = {p: sum(1 for r in results if r["priority"] == p) for p in PRIORITIES}
    nextmv.log(f"expedite={counts['expedite']}  standard={counts['standard']}  defer={counts['defer']}")

    write_results(results)

    with open("metrics.json", "w") as f:
        json.dump(
            {
                "result_value": counts["expedite"],
                "total_orders": len(results),
                "expedite_count": counts["expedite"],
                "standard_count": counts["standard"],
                "defer_count": counts["defer"],
                "expedite_pct": round(counts["expedite"] / len(results), 4),
                "rule_set": options.rule_set,
            },
            f,
        )

    breakdown_chart = priority_breakdown_chart(results, tab_order=1)
    scatter_chart = priority_scatter_chart(results, tab_order=2)

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
                        "content": a.content,
                    }
                    for a in [breakdown_chart, scatter_chart]
                ]
            },
            f,
        )


if __name__ == "__main__":
    main()
