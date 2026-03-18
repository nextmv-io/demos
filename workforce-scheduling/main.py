"""Workforce shift scheduling via multi-objective genetic algorithm (NSGA-II)."""

import numpy as np
import nextmv
from pymoo.config import Config
Config.warnings['not_compiled'] = False
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.core.problem import Problem
from pymoo.core.callback import Callback
from pymoo.core.repair import Repair
from pymoo.operators.crossover.ux import UniformCrossover
from pymoo.operators.mutation.bitflip import BitflipMutation
from pymoo.operators.sampling.rnd import BinaryRandomSampling
from pymoo.optimize import minimize

from visuals import pareto_chart, schedule_heatmap, convergence_chart


class WorkforceProblem(Problem):
    """NSGA-II problem: minimize (total cost, total understaffing)."""

    def __init__(self, workers, shifts, availability):
        self.workers = workers
        self.shifts = shifts
        self.n_workers = len(workers)
        self.n_shifts = len(shifts)
        self._avail_flat = availability.flatten()
        self._costs = np.array([w["cost_per_shift"] for w in workers], dtype=float)
        self._min_cov = np.array([s["min_workers"] for s in shifts], dtype=float)

        super().__init__(
            n_var=self.n_workers * self.n_shifts,
            n_obj=2,
            xl=0,
            xu=1,
            vtype=bool,
        )

    def _evaluate(self, X, out, *args, **kwargs):
        # Enforce availability: unavailable slots forced to 0
        X_bool = X.astype(bool) & self._avail_flat
        X_mat = X_bool.reshape(len(X), self.n_workers, self.n_shifts)

        # Objective 1: total labor cost
        f1 = (X_mat * self._costs[:, np.newaxis]).sum(axis=(1, 2))

        # Objective 2: total understaffing (shortfall across all shifts)
        coverage = X_mat.sum(axis=1)
        f2 = np.maximum(0, self._min_cov - coverage).sum(axis=1)

        out["F"] = np.column_stack([f1, f2])


class MaxShiftsRepair(Repair):
    """Ensure no worker exceeds their max_shifts limit."""

    def _do(self, problem, X, **kwargs):
        rng = np.random.default_rng()
        for i in range(len(X)):
            x = X[i].reshape(problem.n_workers, problem.n_shifts).copy()
            for w, worker in enumerate(problem.workers):
                assigned = np.where(x[w])[0]
                excess = len(assigned) - worker["max_shifts"]
                if excess > 0:
                    drop = rng.choice(assigned, excess, replace=False)
                    x[w, drop] = 0
            X[i] = x.flatten()
        return X


class GenerationCallback(Callback):
    """Track best feasible cost and minimum understaffing per generation."""

    def __init__(self):
        super().__init__()
        self.history = []

    def notify(self, algorithm):
        F = algorithm.pop.get("F")
        feasible = F[F[:, 1] == 0]
        self.history.append(
            {
                "generation": algorithm.n_gen,
                "best_cost": float(feasible[:, 0].min()) if len(feasible) else None,
                "min_understaffing": float(F[:, 1].min()),
            }
        )


def main():
    manifest = nextmv.Manifest.from_yaml(".")
    options = manifest.extract_options()

    input_data = nextmv.load(options=options, path=options.input)
    data = input_data.data

    workers = data["workers"]
    shifts = data["shifts"]
    n_workers = len(workers)
    n_shifts = len(shifts)

    nextmv.log(f"Workers: {n_workers}, Shifts: {n_shifts}")
    nextmv.log(
        f"Pop: {options.population_size}, Gens: {options.num_generations}, "
        f"Mutation: {options.mutation_rate}, Crossover: {options.crossover_rate}"
    )

    # Build availability mask: (n_workers, n_shifts) bool
    shift_idx = {s["id"]: i for i, s in enumerate(shifts)}
    all_shift_ids = list(shift_idx.keys())
    availability = np.zeros((n_workers, n_shifts), dtype=bool)
    for w, worker in enumerate(workers):
        for sid in worker.get("available_shifts", all_shift_ids):
            if sid in shift_idx:
                availability[w, shift_idx[sid]] = True

    problem = WorkforceProblem(workers, shifts, availability)
    callback = GenerationCallback()

    algorithm = NSGA2(
        pop_size=options.population_size,
        sampling=BinaryRandomSampling(),
        crossover=UniformCrossover(prob=options.crossover_rate),
        mutation=BitflipMutation(prob=options.mutation_rate),
        repair=MaxShiftsRepair(),
        eliminate_duplicates=True,
    )

    nextmv.redirect_stdout()

    res = minimize(
        problem,
        algorithm,
        ("n_gen", options.num_generations),
        callback=callback,
        verbose=False,
        seed=options.seed,
    )

    pareto_F = res.F  # (n_pareto, 2): [cost, understaffing]
    pareto_X = res.X.astype(bool) & availability.flatten()

    # Select best: lexicographic sort — min understaffing first, then min cost
    order = np.lexsort((pareto_F[:, 0], pareto_F[:, 1]))
    best_idx = int(order[0])
    best_cost = float(pareto_F[best_idx, 0])
    best_understaffing = float(pareto_F[best_idx, 1])
    best_x = pareto_X[best_idx].reshape(n_workers, n_shifts)

    # Build assignment list
    assignments = [
        {
            "worker_id": workers[w]["id"],
            "worker_name": workers[w].get("name", workers[w]["id"]),
            "shift_id": shifts[s]["id"],
            "shift_name": shifts[s].get("name", shifts[s]["id"]),
            "cost": workers[w]["cost_per_shift"],
        }
        for w in range(n_workers)
        for s in range(n_shifts)
        if best_x[w, s]
    ]

    # Shift coverage summary
    coverage_per_shift = best_x.sum(axis=0)
    shift_summary = [
        {
            "shift_id": shifts[s]["id"],
            "shift_name": shifts[s].get("name", shifts[s]["id"]),
            "assigned": int(coverage_per_shift[s]),
            "required": shifts[s]["min_workers"],
            "covered": bool(coverage_per_shift[s] >= shifts[s]["min_workers"]),
        }
        for s in range(n_shifts)
    ]
    n_covered = sum(1 for ss in shift_summary if ss["covered"])
    coverage_rate = n_covered / n_shifts if n_shifts else 0.0
    workers_used = int(best_x.any(axis=1).sum())

    status = "optimal" if best_understaffing == 0 else "suboptimal"
    nextmv.log(
        f"Best cost: ${best_cost:,.0f} | Understaffed shifts: {int(best_understaffing)} | "
        f"Coverage: {coverage_rate:.1%} | Pareto front: {len(pareto_F)} solutions"
    )

    pareto_points = [
        {"cost": float(pareto_F[i, 0]), "understaffing": float(pareto_F[i, 1])}
        for i in range(len(pareto_F))
    ]

    chart1 = pareto_chart(pareto_points, best_idx=best_idx, tab_order=1)
    chart2 = schedule_heatmap(best_x, workers, shifts, shift_summary, tab_order=2)
    chart3 = convergence_chart(callback.history, tab_order=3)

    output = nextmv.Output(
        solution={"assignments": assignments, "shift_summary": shift_summary},
        assets=[chart1, chart2, chart3],
        metrics={
            "result_value": round(best_cost, 2),
            "total_cost": round(best_cost, 2),
            "understaffed_shifts": int(best_understaffing),
            "coverage_rate": round(coverage_rate, 4),
            "workers_scheduled": workers_used,
            "pareto_front_size": len(pareto_F),
            "status": status,
        },
    )
    nextmv.write(output)


if __name__ == "__main__":
    main()
