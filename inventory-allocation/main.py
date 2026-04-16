import nextmv
import numpy as np
from pyomo.environ import (
    ConcreteModel,
    Constraint,
    NonNegativeReals,
    Objective,
    RangeSet,
    SolverFactory,
    Var,
    minimize,
    value,
)

from visuals import allocation_chart

STATUS_MAP = {
    "optimal": "optimal",
    "feasible": "suboptimal",
    "infeasible": "infeasible",
    "unbounded": "unbounded",
}


def main() -> None:
    """Entry point for the inventory allocation model."""

    manifest = nextmv.Manifest.from_yaml(".")
    options = manifest.extract_options()

    inp = nextmv.load(options=options, path=options.input)
    data = inp.data

    np.random.seed(data.get("seed", 42))

    num_warehouses = data.get("num_warehouses", 5)
    num_stores = data.get("num_stores", 10)

    supply = np.random.randint(*data.get("supply_range", [100, 300]), size=num_warehouses).tolist()
    demand = np.random.randint(*data.get("demand_range", [50, 150]), size=num_stores).tolist()
    cost = np.round(np.random.uniform(1, 10, size=(num_warehouses, num_stores)), 2).tolist()

    W = range(num_warehouses)
    S = range(num_stores)

    nextmv.log(f"Warehouses: {num_warehouses}, total supply: {sum(supply)}")
    nextmv.log(f"Stores: {num_stores}, total demand: {sum(demand)}")
    nextmv.log(f"Solver: {options.solver}")
    nextmv.log(f"Penalty per unmet unit: {options.penalty_unmet_demand}")

    model = ConcreteModel()
    model.W = RangeSet(0, num_warehouses - 1)
    model.S = RangeSet(0, num_stores - 1)

    model.x = Var(model.W, model.S, domain=NonNegativeReals)  # units allocated
    model.unmet = Var(model.S, domain=NonNegativeReals)  # unmet demand

    model.obj = Objective(
        expr=(
            sum(cost[w][s] * model.x[w, s] for w in W for s in S)
            + options.penalty_unmet_demand * sum(model.unmet[s] for s in S)
        ),
        sense=minimize,
    )

    model.supply_con = Constraint(
        model.W,
        rule=lambda m, w: sum(m.x[w, s] for s in S) <= supply[w],
    )

    model.demand_con = Constraint(
        model.S,
        rule=lambda m, s: sum(m.x[w, s] for w in W) + m.unmet[s] == demand[s],
    )

    nextmv.redirect_stdout()

    # Each solver uses a different option name for the time limit.
    SOLVER_MAP = {
        "highs": ("appsi_highs", "time_limit"),
        "cbc": ("cbc", "seconds"),
        "glpk": ("glpk", "tmlim"),
    }
    solver_name = options.solver if options.solver in SOLVER_MAP else "highs"
    pyomo_solver, time_limit_key = SOLVER_MAP[solver_name]

    solver = SolverFactory(pyomo_solver)
    if not solver.available():
        raise RuntimeError(f"Solver '{solver_name}' ({pyomo_solver}) is not installed or not on PATH.")
    solver.options[time_limit_key] = options.time_limit
    results = solver.solve(model)
    status = str(results.solver.termination_condition)
    nextmv.log(f"Solver status: {status}")

    allocations = [
        {"warehouse": w, "store": s, "units": round(value(model.x[w, s]), 2)}
        for w in W
        for s in S
        if value(model.x[w, s]) > 0.01
    ]
    unmet = [
        {"store": s, "unmet_demand": round(value(model.unmet[s]), 2)}
        for s in S
        if value(model.unmet[s]) > 0.01
    ]

    total_allocated = sum(a["units"] for a in allocations)
    total_demand = sum(demand)
    fill_rate = total_allocated / total_demand if total_demand > 0 else 0
    transport_cost = sum(cost[a["warehouse"]][a["store"]] * a["units"] for a in allocations)

    chart = allocation_chart(
        allocations=allocations,
        num_warehouses=num_warehouses,
        num_stores=num_stores,
    )

    metrics_dict = {
        "result_value": round(value(model.obj), 2),
        "transportation_cost": round(transport_cost, 2),
        "fill_rate": round(fill_rate, 4),
        "total_units_allocated": round(total_allocated, 2),
        "total_demand": total_demand,
        "total_supply": sum(supply),
        "num_unmet_stores": len(unmet),
        "status": STATUS_MAP.get(status, status),
        "solver": solver_name,
    }

    output = nextmv.Output(
        solution={"allocations": allocations, "unmet_demand": unmet},
        assets=[chart],
        metrics=metrics_dict,
        statistics=nextmv.Statistics(
            result=nextmv.ResultStatistics(
                custom=metrics_dict,
                value=metrics_dict["result_value"],
            ),
        ),
    )

    nextmv.write(output, path=options.output)


if __name__ == "__main__":
    main()
