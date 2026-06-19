"""Find a feasibility-stress regime for the ensemble demo.

We want inputs where MANY first-solution strategies return NO SOLUTION, the
*surviving* set differs across inputs, and ideally at least one input where only
a single strategy survives. That makes the ensemble the only thing that reliably
returns a route -- a much stronger justification than "best-per-input by ~1%".

Grid-searches capacity tightness x time tightness x geography and prints a
feasibility matrix (strategy x instance) at the demo budget.

Run:  python explore_feasibility.py [budget_seconds]
"""

import concurrent.futures as cf
import json
import subprocess
import sys

from generate_input import build_instance

PY = ".venv/bin/python"
BUDGET = int(sys.argv[1]) if len(sys.argv) > 1 else 5

# Candidate ensemble-member strategies (all run with GLS). SWEEP/CHRISTOFIDES are
# excluded -- they almost always fail on capacitated VRP, so they're "never pick"
# landmines for the sweep story, not useful ensemble members.
STRATEGIES = [
    "AUTOMATIC",
    "PATH_CHEAPEST_ARC",
    "PATH_MOST_CONSTRAINED_ARC",
    "GLOBAL_CHEAPEST_ARC",
    "LOCAL_CHEAPEST_ARC",
    "LOCAL_CHEAPEST_INSERTION",
    "SAVINGS",
    "PARALLEL_CHEAPEST_INSERTION",
]

# Stress instances. Tighten capacity (fleet slack over demand) and/or time
# (max_hours) toward the feasibility knife-edge. Capacity tightness and time
# tightness produce DIFFERENT failure patterns, which is what makes survivors
# differ across inputs.
INSTANCES = {}
# Capacity tightening leaves the same 6 robust strategies feasible. Now make the
# per-vehicle DURATION cap bind: with 8 vehicles (~19 stops/route, ~38min of
# service alone) routes run ~1-1.3h, so tightening max_hours toward ~1.0 forces
# route-length infeasibility -- a different failure mode that should hit
# different constructors than capacity does.
# Candidate FINAL demo set -- chosen so that no single strategy is feasible on
# all of them (the undeniable ensemble case).
INSTANCES["metro-tight"]   = dict(n_stops=150, n_vehicles=8,  geography="clustered", n_neighborhoods=6, capacity_factor=1.1,  max_hours=1.12, seed=42)  # expect: only SAVINGS
INSTANCES["suburb-tight"]  = dict(n_stops=150, n_vehicles=8,  geography="clustered", n_neighborhoods=6, capacity_factor=1.1,  max_hours=1.12, seed=7)   # expect: PATH_MOST_CONSTRAINED + SAVINGS
INSTANCES["metro-normal"]  = dict(n_stops=150, n_vehicles=8,  geography="clustered", n_neighborhoods=6, capacity_factor=1.1,  max_hours=1.5,  seed=42)  # expect: ~6/8, a "normal" input
INSTANCES["regional-big"]  = dict(n_stops=300, n_vehicles=16, geography="clustered", n_neighborhoods=6, capacity_factor=1.05, max_hours=4.0,  seed=42)  # expect: SAVINGS fails
INSTANCES["regional-big7"] = dict(n_stops=300, n_vehicles=16, geography="clustered", n_neighborhoods=6, capacity_factor=1.05, max_hours=4.0,  seed=7)   # backup


def run(instance_bytes, fss):
    out = subprocess.run(
        [PY, "main.py", "-duration", str(BUDGET),
         "-first_solution_strategy", fss, "-local_search_metaheuristic", "GUIDED_LOCAL_SEARCH"],
        input=instance_bytes, capture_output=True,
    )
    try:
        m = json.loads(out.stdout)["metrics"]
    except Exception:
        return None
    return m["objective_value"] if m.get("solution_found") else None


def main():
    instances = {name: json.dumps(build_instance(**p)).encode() for name, p in INSTANCES.items()}
    jobs = {}
    with cf.ThreadPoolExecutor(max_workers=8) as ex:
        for iname, ibytes in instances.items():
            for s in STRATEGIES:
                jobs[(iname, s)] = ex.submit(run, ibytes, s)
        res = {k: f.result() for k, f in jobs.items()}

    print(f"\nFeasibility / objective matrix (GLS, {BUDGET}s). 'X' = NO SOLUTION.\n")
    w = 15
    header = f"{'instance':<20}" + "".join(f"{s[:13]:>{w}}" for s in STRATEGIES) + "  #feas"
    print(header)
    print("-" * len(header))
    for iname in INSTANCES:
        row = {s: res[(iname, s)] for s in STRATEGIES}
        nfeas = sum(1 for v in row.values() if v is not None)
        cells = "".join((f"{'X':>{w}}" if row[s] is None else f"{row[s]:>{w}}") for s in STRATEGIES)
        print(f"{iname:<20}{cells}  {nfeas}/{len(STRATEGIES)}")

    # Which strategies are feasible-everywhere vs sometimes-fail.
    print("\nPer-strategy feasibility count (how many instances each survives):")
    for s in STRATEGIES:
        c = sum(1 for iname in INSTANCES if res[(iname, s)] is not None)
        print(f"  {s:<28} {c}/{len(INSTANCES)}")


if __name__ == "__main__":
    main()
