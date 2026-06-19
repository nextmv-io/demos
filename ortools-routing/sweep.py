"""Quick local sweep to validate that strategy choice changes the objective.

Not part of the app -- just a harness to prove the demo premise before we
build scenario tests on Nextmv Cloud.
"""

import json
import subprocess
import sys

PY = ".venv/bin/python"
FIRST = [
    "PATH_CHEAPEST_ARC",
    "GLOBAL_CHEAPEST_ARC",
    "LOCAL_CHEAPEST_ARC",
    "SAVINGS",
    "SWEEP",
    "CHRISTOFIDES",
    "PARALLEL_CHEAPEST_INSERTION",
]
META = [
    "GREEDY_DESCENT",
    "GUIDED_LOCAL_SEARCH",
    "SIMULATED_ANNEALING",
    "TABU_SEARCH",
]


def run(duration, fss, lsm):
    with open("input.json", "rb") as f:
        out = subprocess.run(
            [PY, "main.py", "-duration", str(duration),
             "-first_solution_strategy", fss, "-local_search_metaheuristic", lsm],
            stdin=f, capture_output=True,
        )
    m = json.loads(out.stdout)["metrics"]
    if not m.get("solution_found"):
        return None, None, None
    return m["objective_value"], m["activated_vehicles"], m["max_route_duration"]


def table(title, rows):
    print(f"\n=== {title} ===")
    print(f"{'config':<46} {'objective':>10} {'veh':>4} {'maxRoute':>9}")
    solved = [r for r in rows if r[1][0] is not None]
    best = min(r[1][0] for r in solved) if solved else None
    for label, (obj, veh, maxr) in rows:
        if obj is None:
            print(f"{label:<46} {'NO SOLUTION':>10}")
            continue
        gap = (obj / best - 1) * 100
        flag = "  <- best" if obj == best else f"  (+{gap:.1f}%)"
        print(f"{label:<46} {obj:>10} {veh:>4} {maxr:>9}{flag}")


dur = int(sys.argv[1]) if len(sys.argv) > 1 else 2

rows = [(f"{fss} x GREEDY_DESCENT", run(dur, fss, "GREEDY_DESCENT")) for fss in FIRST]
table(f"First-solution strategy (greedy descent, {dur}s) -- isolates initial build", rows)

rows = [(f"PATH_CHEAPEST_ARC x {lsm}", run(dur, "PATH_CHEAPEST_ARC", lsm)) for lsm in META]
table(f"Metaheuristic (from path-cheapest-arc, {dur}s) -- isolates improvement", rows)
