"""
Shift scheduling: assign workers to shifts, balancing coverage, cost, and fairness.

Coverage is soft: each shift has a shortfall variable penalized in the objective.
A high coverage_penalty (default) makes it behave like a hard constraint; lowering
it lets the solver leave shifts understaffed when the tradeoff is worth it.

Objective modes (operator-facing):
  - cost_only  : minimize labor cost (+ coverage penalty)
  - fair_only  : minimize shift-count spread across workers (+ coverage penalty)
  - weighted   : minimize cost + fairness_penalty * spread (+ coverage penalty)

This structure supports a two-rule ensemble:
  Rule 0: minimize result.value     (= total_cost; 1e12 sentinel for understaffed/infeasible runs
                                     means coverage violations are filtered out automatically)
  Rule 1: minimize shift_spread     (fairest within the Rule 0 cost tolerance)
"""

import time

import nextmv
from pyomo.environ import (
    Binary,
    ConcreteModel,
    Constraint,
    ConstraintList,
    NonNegativeIntegers,
    NonNegativeReals,
    Objective,
    SolverFactory,
    Var,
    minimize,
    value,
)

from visuals import build_schedule_chart, build_fairness_chart

STATUS_MAP = {
    "optimal": "optimal",
    "feasible": "suboptimal",
    "infeasible": "infeasible",
    "unbounded": "unbounded",
}

OBJECTIVE_MODES = ["cost_only", "fair_only", "weighted"]


def main() -> None:
    manifest = nextmv.Manifest.from_yaml(".")
    options = manifest.extract_options()

    inp = nextmv.load(options=options)
    data = inp.data

    workers = data["workers"]
    shifts = data["shifts"]
    n_workers = len(workers)
    n_shifts = len(shifts)

    mode = getattr(options, "objective_mode", "cost_only")
    if mode not in OBJECTIVE_MODES:
        nextmv.log(f"Unknown objective_mode '{mode}', defaulting to 'cost_only'.")
        mode = "cost_only"

    default_hourly_wage = options.hourly_wage
    fairness_penalty = getattr(options, "fairness_penalty", 200.0)
    coverage_penalty = options.coverage_penalty
    time_limit = options.time_limit

    # Per-worker wage falls back to the global hourly_wage option
    worker_wage = {w["id"]: w.get("hourly_wage", default_hourly_wage) for w in workers}

    nextmv.log(f"Workers: {n_workers}, Shifts: {n_shifts}, Mode: {mode}")
    nextmv.log(
        f"Default wage: ${default_hourly_wage}/hr, Fairness penalty: ${fairness_penalty}, "
        f"Coverage penalty: ${coverage_penalty}/worker-slot, Time limit: {time_limit}s"
    )

    shift_ids = [s["id"] for s in shifts]
    shift_idx = {s["id"]: i for i, s in enumerate(shifts)}

    # Build availability mask
    avail = {(w["id"], s["id"]): False for w in workers for s in shifts}
    for w in workers:
        allowed = set(w.get("available_shifts", shift_ids))
        for sid in allowed:
            if sid in shift_idx:
                avail[(w["id"], sid)] = True

    shift_hours = {s["id"]: s.get("hours", 8) for s in shifts}
    required = {s["id"]: s.get("required_workers", 1) for s in shifts}

    model = ConcreteModel()

    # x[w, s] = 1 if worker w is assigned to shift s
    model.x = Var(
        [(w["id"], s["id"]) for w in workers for s in shifts],
        domain=Binary,
    )

    # Force unavailable assignments to 0
    for w in workers:
        for s in shifts:
            if not avail[(w["id"], s["id"])]:
                model.x[(w["id"], s["id"])].fix(0)

    # Per-worker shift limits
    model.worker_min = ConstraintList()
    model.worker_max = ConstraintList()
    for w in workers:
        lo = w.get("min_shifts", 0)
        hi = w.get("max_shifts", n_shifts)
        total = sum(model.x[(w["id"], s["id"])] for s in shifts)
        model.worker_min.add(total >= lo)
        model.worker_max.add(total <= hi)

    # Hard upper bound: never assign more workers than required for a shift
    model.coverage_upper = ConstraintList()
    for s in shifts:
        model.coverage_upper.add(
            sum(model.x[(w["id"], s["id"])] for w in workers) <= required[s["id"]]
        )

    # Shortfall = required - assigned (>= 0 by the upper bound above).
    # Penalized in the objective; zero when the shift is fully covered.
    model.shortfall = Var(shift_ids, domain=NonNegativeIntegers)
    model.shortfall_def = ConstraintList()
    for s in shifts:
        model.shortfall_def.add(
            model.shortfall[s["id"]]
            == required[s["id"]] - sum(model.x[(w["id"], s["id"])] for w in workers)
        )

    model.total_shortfall = Var(domain=NonNegativeIntegers)
    model.total_shortfall_def = Constraint(
        expr=model.total_shortfall == sum(model.shortfall[s["id"]] for s in shifts)
    )

    # Labor cost (always tracked, even in fair_only mode)
    model.total_cost = Var(domain=NonNegativeReals)
    model.cost_def = Constraint(
        expr=model.total_cost == sum(
            worker_wage[w["id"]] * shift_hours[s["id"]] * model.x[(w["id"], s["id"])]
            for w in workers
            for s in shifts
        )
    )

    # Fairness: max-min spread of shifts assigned per worker
    model.shifts_assigned = Var(range(n_workers), domain=NonNegativeIntegers)
    model.shifts_def = ConstraintList()
    for i, w in enumerate(workers):
        model.shifts_def.add(
            model.shifts_assigned[i] == sum(model.x[(w["id"], s["id"])] for s in shifts)
        )

    model.max_shifts = Var(domain=NonNegativeIntegers)
    model.min_shifts = Var(domain=NonNegativeIntegers)
    model.spread = Var(domain=NonNegativeIntegers)
    model.max_def = ConstraintList()
    model.min_def = ConstraintList()
    for i in range(n_workers):
        model.max_def.add(model.max_shifts >= model.shifts_assigned[i])
        model.min_def.add(model.min_shifts <= model.shifts_assigned[i])
    model.spread_def = Constraint(
        expr=model.spread == model.max_shifts - model.min_shifts
    )

    coverage_term = coverage_penalty * model.total_shortfall

    if mode == "cost_only":
        model.obj = Objective(expr=coverage_term + model.total_cost, sense=minimize)
    elif mode == "fair_only":
        model.obj = Objective(expr=coverage_term + model.spread, sense=minimize)
    else:  # weighted
        model.obj = Objective(
            expr=coverage_term + model.total_cost + fairness_penalty * model.spread,
            sense=minimize,
        )

    nextmv.redirect_stdout()

    start_time = time.time()
    solver = SolverFactory("appsi_highs")
    result = solver.solve(model, tee=False, options={"time_limit": time_limit})
    elapsed = time.time() - start_time

    termination = str(result.solver.termination_condition)
    status = STATUS_MAP.get(termination, "suboptimal")
    nextmv.log(f"Solver: {termination} → {status} in {elapsed:.2f}s")

    feasible = status in ("optimal", "suboptimal")

    # Build solution
    assignments = []
    worker_shift_counts = {w["id"]: 0 for w in workers}
    if feasible:
        for w in workers:
            for s in shifts:
                if value(model.x[(w["id"], s["id"])]) > 0.5:
                    assignments.append({
                        "worker_id": w["id"],
                        "worker_name": w.get("name", w["id"]),
                        "shift_id": s["id"],
                        "shift_name": s.get("name", s["id"]),
                        "shift_hours": shift_hours[s["id"]],
                        "cost": worker_wage[w["id"]] * shift_hours[s["id"]],
                    })
                    worker_shift_counts[w["id"]] += 1

    # Per-shift coverage summary
    shift_coverage = {}
    for s in shifts:
        assigned_workers = [a["worker_id"] for a in assignments if a["shift_id"] == s["id"]]
        shortfall_val = int(round(value(model.shortfall[s["id"]]))) if feasible else required[s["id"]]
        shift_coverage[s["id"]] = {
            "shift_id": s["id"],
            "shift_name": s.get("name", s["id"]),
            "assigned": len(assigned_workers),
            "required": required[s["id"]],
            "shortfall": shortfall_val,
            "workers": assigned_workers,
        }

    infeasible_sentinel = 1e12

    total_cost_val = round(value(model.total_cost), 2) if feasible else infeasible_sentinel
    total_shortfall_val = int(round(value(model.total_shortfall))) if feasible else int(infeasible_sentinel)
    spread_val = int(round(value(model.spread))) if feasible else int(infeasible_sentinel)
    max_s = int(round(value(model.max_shifts))) if feasible else int(infeasible_sentinel)
    min_s = int(round(value(model.min_shifts))) if feasible else 0
    unplanned_shifts = sum(1 for sc in shift_coverage.values() if sc["shortfall"] > 0)

    nextmv.log(
        f"Total cost: ${total_cost_val:.2f}, Shortfall: {total_shortfall_val} worker-slots "
        f"({unplanned_shifts} shifts), Spread: {spread_val}"
        if feasible
        else "No feasible solution found."
    )

    schedule_chart = build_schedule_chart(assignments, workers, shifts, shift_coverage, tab_order=1)
    fairness_chart = build_fairness_chart(worker_shift_counts, workers, tab_order=2)

    metrics = {
        "status": status,
        "result_value": total_cost_val,
        "total_cost": total_cost_val,
        "total_shortfall": total_shortfall_val,
        "unplanned_shifts": unplanned_shifts,
        "shift_spread": spread_val,
        "max_shifts_per_worker": max_s,
        "min_shifts_per_worker": min_s,
        "assignments": len(assignments),
        "objective_mode": mode,
    }

    # statistics.result.value = total_cost for feasible, 1e12 sentinel for infeasible/understaffed.
    # Ensemble Rule 0 minimizes cost (5% tolerance); the sentinel routes around understaffed runs.
    # Spread lives in custom for Rule 1.
    result_stat_value = total_cost_val if (feasible and total_shortfall_val == 0) else infeasible_sentinel
    statistics = nextmv.Statistics(
        run=nextmv.RunStatistics(duration=elapsed),
        result=nextmv.ResultStatistics(
            value=result_stat_value,
            custom={**metrics, "feasible": 1.0 if feasible else 0.0},
        ),
    )

    output = nextmv.Output(
        solution={
            "assignments": assignments,
            "shift_coverage": list(shift_coverage.values()),
            "worker_shift_counts": [
                {"worker_id": wid, "count": cnt}
                for wid, cnt in worker_shift_counts.items()
            ],
        },
        assets=[schedule_chart, fairness_chart],
        statistics=statistics,
        metrics=metrics,
        options=options,
    )

    nextmv.write(output)


if __name__ == "__main__":
    main()
