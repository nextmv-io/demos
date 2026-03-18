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

from visuals import build_demand_chart, build_solution_chart

STATUS_MAP = {
    "optimal": "optimal",
    "feasible": "suboptimal",
    "infeasible": "infeasible",
    "unbounded": "unbounded",
}


def generate_shifts(n_periods: int, min_length: int, max_length: int) -> list[dict]:
    """Enumerate all feasible (start, length) shift combinations."""
    shifts = []
    for start in range(n_periods):
        for length in range(min_length, max_length + 1):
            if start + length <= n_periods:
                shifts.append(
                    {
                        "id": f"s_{start}_{length}",
                        "start": start,
                        "length": length,
                        "end": start + length,
                        "periods": set(range(start, start + length)),
                    }
                )
    return shifts


def main() -> None:
    manifest = nextmv.Manifest.from_yaml(".")
    options = manifest.extract_options()

    inp = nextmv.load(options=options, path=options.input)
    data = inp.data

    time_periods = data["time_periods"]
    n = len(time_periods)
    demands = [tp["demand"] for tp in time_periods]
    labels = [tp.get("label", str(idx)) for idx, tp in enumerate(time_periods)]

    min_len = options.min_shift_length
    max_len = options.max_shift_length
    max_workers = options.max_workers_per_shift
    wage = options.hourly_wage
    setup_cost = options.shift_setup_cost
    penalty = options.penalty_unmet_demand
    time_limit = options.time_limit

    if min_len > max_len:
        nextmv.log(f"min_shift_length ({min_len}) > max_shift_length ({max_len}), swapping.")
        min_len, max_len = max_len, min_len

    shifts = generate_shifts(n, min_len, max_len)
    nextmv.log(f"Generated {len(shifts)} feasible shift templates for {n} time periods.")

    S = range(len(shifts))
    T = range(n)

    model = ConcreteModel()

    # Decision variables
    model.x = Var(S, domain=Binary)           # 1 if shift s is published
    model.w = Var(S, domain=NonNegativeIntegers)  # workers assigned to shift s
    model.u = Var(T, domain=NonNegativeReals)  # unmet demand per period (slack)

    # Objective: minimize labor cost + setup costs + penalty for unmet demand
    model.obj = Objective(
        expr=sum(
            setup_cost * model.x[s] + wage * shifts[s]["length"] * model.w[s]
            for s in S
        )
        + sum(penalty * model.u[t] for t in T),
        sense=minimize,
    )

    # Coverage: workers on active shifts must cover demand (with optional slack)
    model.coverage = ConstraintList()
    for t in T:
        covering = [s for s in S if t in shifts[s]["periods"]]
        if covering:
            model.coverage.add(
                sum(model.w[s] for s in covering) + model.u[t] >= demands[t]
            )
        else:
            model.coverage.add(model.u[t] >= demands[t])

    # Linking: workers only if shift is open; at most max_workers
    model.linking_upper = ConstraintList()
    model.linking_lower = ConstraintList()
    for s in S:
        model.linking_upper.add(model.w[s] <= max_workers * model.x[s])
        model.linking_lower.add(model.w[s] >= model.x[s])

    nextmv.redirect_stdout()

    solver = SolverFactory("appsi_highs")
    result = solver.solve(model, tee=False, options={"time_limit": time_limit})

    termination = str(result.solver.termination_condition)
    status = STATUS_MAP.get(termination, "suboptimal")
    nextmv.log(f"Solver status: {termination} → {status}")

    # Build solution
    open_shifts = []
    for s in S:
        if value(model.x[s]) > 0.5:
            workers = int(round(value(model.w[s])))
            open_shifts.append(
                {
                    "id": shifts[s]["id"],
                    "start_period": shifts[s]["start"],
                    "end_period": shifts[s]["end"],
                    "length_hours": shifts[s]["length"],
                    "workers": workers,
                    "start_label": labels[shifts[s]["start"]],
                    "end_label": labels[shifts[s]["end"] - 1],
                    "labor_cost": wage * shifts[s]["length"] * workers,
                    "setup_cost": setup_cost,
                }
            )

    open_shifts.sort(key=lambda s: (s["start_period"], s["end_period"]))

    coverage = []
    for t in T:
        covering = [s for s in range(len(open_shifts)) if open_shifts[s]["start_period"] <= t < open_shifts[s]["end_period"]]
        assigned = sum(open_shifts[s]["workers"] for s in covering)
        coverage.append(
            {
                "period": t,
                "label": labels[t],
                "demand": demands[t],
                "assigned": assigned,
                "unmet": max(0, demands[t] - assigned),
            }
        )

    total_cost = value(model.obj)
    total_labor_cost = sum(s["labor_cost"] for s in open_shifts)
    total_setup_cost = sum(s["setup_cost"] for s in open_shifts)
    total_worker_hours = sum(s["length_hours"] * s["workers"] for s in open_shifts)
    unmet_periods = sum(1 for c in coverage if c["unmet"] > 0)
    total_unmet = sum(c["unmet"] for c in coverage)

    nextmv.log(
        f"Published {len(open_shifts)} shifts, "
        f"{total_worker_hours} worker-hours, "
        f"total cost ${total_cost:.2f}, "
        f"{unmet_periods} periods with unmet demand."
    )

    demand_chart = build_demand_chart(time_periods, labels)
    solution_chart = build_solution_chart(open_shifts, coverage, labels)

    output = nextmv.Output(
        solution={
            "shifts": open_shifts,
            "coverage": coverage,
        },
        assets=[demand_chart, solution_chart],
        metrics={
            "status": status,
            "result_value": total_cost,
            "total_shifts": len(open_shifts),
            "total_worker_hours": total_worker_hours,
            "total_labor_cost": total_labor_cost,
            "total_setup_cost": total_setup_cost,
            "unmet_periods": unmet_periods,
            "total_unmet_demand": total_unmet,
        },
    )

    nextmv.write(output, path=options.output)


if __name__ == "__main__":
    main()
