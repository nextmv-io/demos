import nextmv
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

from visuals import inventory_chart, production_chart

STATUS_MAP = {
    "optimal": "optimal",
    "feasible": "suboptimal",
    "infeasible": "infeasible",
    "unbounded": "unbounded",
}

SOLVER_MAP = {
    "highs": ("appsi_highs", "time_limit"),
    "cbc": ("cbc", "seconds"),
    "glpk": ("glpk", "tmlim"),
}


def main() -> None:
    """Entry point for the production planning model."""

    manifest = nextmv.Manifest.from_yaml(".")
    options = manifest.extract_options()

    inp = nextmv.load(options=options, path=options.input)
    data = inp.data

    products = data["products"]
    periods = data["periods"]
    demand = data["demand"]          # demand[p][t]
    prod_cost = data["production_cost"]   # cost per unit produced
    hold_cost = data["holding_cost"]      # cost per unit held per period
    resource_use = data["resource_use"]   # resource units consumed per unit produced
    capacity = data["capacity"]           # available resource units per period
    initial_inv = data.get("initial_inventory", [0] * len(products))

    num_products = len(products)
    num_periods = len(periods)
    P = range(num_products)
    T = range(num_periods)

    nextmv.log(f"Products: {num_products}, Periods: {num_periods}")
    nextmv.log(f"Total demand: {sum(demand[p][t] for p in P for t in T):.0f} units")
    nextmv.log(f"Solver: {options.solver}")

    model = ConcreteModel()
    model.P = RangeSet(0, num_products - 1)
    model.T = RangeSet(0, num_periods - 1)

    model.x = Var(model.P, model.T, domain=NonNegativeReals)    # production quantity
    model.inv = Var(model.P, model.T, domain=NonNegativeReals)  # ending inventory
    model.unmet = Var(model.P, model.T, domain=NonNegativeReals)  # unmet demand

    model.obj = Objective(
        expr=sum(
            prod_cost[p] * model.x[p, t]
            + options.holding_cost_weight * hold_cost[p] * model.inv[p, t]
            + options.penalty_unmet_demand * model.unmet[p, t]
            for p in P for t in T
        ),
        sense=minimize,
    )

    def inv_balance(m, p, t):
        prev = initial_inv[p] if t == 0 else m.inv[p, t - 1]
        return m.inv[p, t] == prev + m.x[p, t] - demand[p][t] + m.unmet[p, t]

    model.inv_balance = Constraint(model.P, model.T, rule=inv_balance)

    model.capacity_con = Constraint(
        model.T,
        rule=lambda m, t: sum(resource_use[p] * m.x[p, t] for p in P) <= capacity[t],
    )

    # Safety stock: ending inventory must be >= pct of next period's demand.
    if options.safety_stock_pct > 0:
        pct = options.safety_stock_pct / 100.0
        model.safety_stock_con = Constraint(
            model.P,
            RangeSet(0, num_periods - 2),  # no next period for the last period
            rule=lambda m, p, t: m.inv[p, t] >= pct * demand[p][t + 1],
        )

    # Production ramp: limit absolute change between consecutive periods.
    # Ramp limit is expressed as a % of each product's average period demand.
    if options.max_production_ramp_pct < 100.0:
        avg_demand = [sum(demand[p]) / num_periods for p in P]
        ramp_limit = [options.max_production_ramp_pct / 100.0 * avg_demand[p] for p in P]
        model.ramp_up_con = Constraint(
            model.P,
            RangeSet(1, num_periods - 1),
            rule=lambda m, p, t: m.x[p, t] - m.x[p, t - 1] <= ramp_limit[p],
        )
        model.ramp_dn_con = Constraint(
            model.P,
            RangeSet(1, num_periods - 1),
            rule=lambda m, p, t: m.x[p, t - 1] - m.x[p, t] <= ramp_limit[p],
        )

    nextmv.redirect_stdout()

    solver_name = options.solver if options.solver in SOLVER_MAP else "highs"
    pyomo_solver, time_limit_key = SOLVER_MAP[solver_name]

    solver = SolverFactory(pyomo_solver)
    if not solver.available():
        raise RuntimeError(
            f"Solver '{solver_name}' ({pyomo_solver}) is not installed or not on PATH."
        )
    solver.options[time_limit_key] = options.time_limit
    results = solver.solve(model)
    status = str(results.solver.termination_condition)
    nextmv.log(f"Solver status: {status}")

    # Extract solution
    production = [
        [round(value(model.x[p, t]), 2) for t in T]
        for p in P
    ]
    inventory = [
        [round(value(model.inv[p, t]), 2) for t in T]
        for p in P
    ]
    unmet = [
        [round(value(model.unmet[p, t]), 2) for t in T]
        for p in P
    ]

    total_prod_cost = sum(prod_cost[p] * value(model.x[p, t]) for p in P for t in T)
    total_hold_cost = sum(hold_cost[p] * value(model.inv[p, t]) for p in P for t in T)
    total_unmet = sum(value(model.unmet[p, t]) for p in P for t in T)
    total_demand = sum(demand[p][t] for p in P for t in T)
    fill_rate = 1.0 - (total_unmet / total_demand) if total_demand > 0 else 1.0

    nextmv.log(f"Total production cost: {total_prod_cost:.2f}")
    nextmv.log(f"Total holding cost: {total_hold_cost:.2f}")
    nextmv.log(f"Fill rate: {fill_rate:.2%}")

    prod_chart = production_chart(products, periods, production)
    inv_chart = inventory_chart(products, periods, inventory)

    output = nextmv.Output(
        solution={
            "production": [
                {"product": products[p], "quantities": production[p]} for p in P
            ],
            "inventory": [
                {"product": products[p], "levels": inventory[p]} for p in P
            ],
            "unmet_demand": [
                {"product": products[p], "quantities": unmet[p]} for p in P
                if any(u > 0.01 for u in unmet[p])
            ],
        },
        assets=[prod_chart, inv_chart],
        metrics={
            "result_value": round(value(model.obj), 2),
            "production_cost": round(total_prod_cost, 2),
            "holding_cost": round(total_hold_cost, 2),
            "total_unmet_demand": round(total_unmet, 2),
            "fill_rate": round(fill_rate, 4),
            "total_demand": round(total_demand, 2),
            "status": STATUS_MAP.get(status, status),
            "solver": solver_name,
        },
    )

    nextmv.write(output, path=options.output)


if __name__ == "__main__":
    main()
