"""Machine shop scheduling with sequence-dependent changeovers using OR-Tools CP-SAT."""

import csv
import json
import os
from collections import defaultdict

import nextmv
from ortools.sat.python import cp_model

from visuals import gantt_chart, utilization_chart

STATUS_MAP = {
    "optimal": "optimal",
    "feasible": "suboptimal",
    "infeasible": "infeasible",
    "model_invalid": "infeasible",
    "unknown": "infeasible",
}


def read_jobs(path="jobs.csv"):
    """Return dict: job_id -> list of ops sorted by sequence."""
    jobs = defaultdict(list)
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            jobs[row["job_id"]].append(
                {
                    "sequence": int(row["sequence"]),
                    "machine": row["machine"],
                    "duration": int(row["duration"]),
                }
            )
    for ops in jobs.values():
        ops.sort(key=lambda x: x["sequence"])
    return dict(jobs)


def read_changeovers(path="changeovers.csv"):
    """Return dict: (machine, from_job, to_job) -> changeover minutes."""
    co = {}
    if not os.path.exists(path):
        return co
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            co[(row["machine"], row["from_job"], row["to_job"])] = int(row["changeover"])
    return co


def main():
    manifest = nextmv.Manifest.from_yaml(".")
    options = manifest.extract_options()

    jobs = read_jobs()
    changeovers = read_changeovers()

    all_job_ids = list(jobs.keys())
    all_machines = sorted({op["machine"] for ops in jobs.values() for op in ops})

    nextmv.log(f"Jobs: {len(all_job_ids)}, Machines: {len(all_machines)}")
    nextmv.log(f"Changeover pairs: {len(changeovers)}, weight: {options.changeover_weight}")

    # Flatten to task list
    tasks = [
        {
            "job_id": job_id,
            "step": step,
            "machine": op["machine"],
            "duration": op["duration"],
        }
        for job_id, ops in jobs.items()
        for step, op in enumerate(ops)
    ]

    # Conservative horizon: sum of all durations + all changeovers at max weight
    co_total = sum(changeovers.values()) if changeovers else 0
    horizon = int(
        sum(t["duration"] for t in tasks)
        + co_total * max(options.changeover_weight, 1.0)
        + 60
    )

    model = cp_model.CpModel()

    # Interval variables for each (job_id, step)
    task_starts = {}
    task_ends = {}
    for t in tasks:
        key = (t["job_id"], t["step"])
        s = model.NewIntVar(0, horizon, f"s_{t['job_id']}_{t['step']}")
        e = model.NewIntVar(0, horizon, f"e_{t['job_id']}_{t['step']}")
        model.NewIntervalVar(s, t["duration"], e, f"iv_{t['job_id']}_{t['step']}")
        task_starts[key] = s
        task_ends[key] = e

    # Precedence: within each job, operation i must finish before operation i+1 starts
    for job_id, ops in jobs.items():
        for step in range(len(ops) - 1):
            model.Add(task_ends[(job_id, step)] <= task_starts[(job_id, step + 1)])

    # Per-machine ordering with sequence-dependent changeovers via circuit constraint
    machine_tasks = defaultdict(list)
    for t in tasks:
        machine_tasks[t["machine"]].append((t["job_id"], t["step"]))

    for machine, mtasks in machine_tasks.items():
        n = len(mtasks)
        if n <= 1:
            continue

        dummy = n
        arcs = []

        for i in range(n):
            # Dummy → i: task i is first on this machine
            arcs.append((dummy, i, model.NewBoolVar(f"first_{machine}_{i}")))
            # i → dummy: task i is last on this machine
            arcs.append((i, dummy, model.NewBoolVar(f"last_{machine}_{i}")))

            for j in range(n):
                if i == j:
                    continue
                lit = model.NewBoolVar(f"arc_{machine}_{i}_{j}")
                arcs.append((i, j, lit))

                # If task i is immediately followed by task j on this machine:
                # start[j] >= end[i] + changeover(i -> j)
                job_i, job_j = mtasks[i][0], mtasks[j][0]
                base_co = changeovers.get((machine, job_i, job_j), 0)
                co = int(round(base_co * options.changeover_weight))
                model.Add(
                    task_starts[mtasks[j]] >= task_ends[mtasks[i]] + co
                ).OnlyEnforceIf(lit)

        model.AddCircuit(arcs)

    # Minimize makespan: latest end time across all final job operations
    makespan = model.NewIntVar(0, horizon, "makespan")
    final_ends = [task_ends[(job_id, len(ops) - 1)] for job_id, ops in jobs.items()]
    model.AddMaxEquality(makespan, final_ends)
    model.Minimize(makespan)

    # Solve
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = options.time_limit
    solver.parameters.num_workers = options.num_workers

    nextmv.redirect_stdout()
    status_code = solver.Solve(model)
    status_str = solver.StatusName(status_code).lower()
    nextmv.log(f"Solver status: {status_str}")

    # Extract solution
    if status_code in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        makespan_val = int(solver.ObjectiveValue())
        schedule = []
        for t in tasks:
            key = (t["job_id"], t["step"])
            start = solver.Value(task_starts[key])
            schedule.append(
                {
                    "job_id": t["job_id"],
                    "step": t["step"],
                    "machine": t["machine"],
                    "start": start,
                    "end": start + t["duration"],
                    "duration": t["duration"],
                }
            )

        total_processing = sum(t["duration"] for t in tasks)
        avg_util = total_processing / (makespan_val * len(all_machines)) if makespan_val > 0 else 0
        machine_util = {
            m: sum(t["duration"] for t in schedule if t["machine"] == m) / makespan_val
            for m in all_machines
        }
        nextmv.log(f"Makespan: {makespan_val} min | Avg utilization: {avg_util:.1%}")
    else:
        makespan_val = 0
        schedule = []
        avg_util = 0.0
        machine_util = {m: 0.0 for m in all_machines}

    # Write solution CSV
    os.makedirs("output", exist_ok=True)
    with open("output/schedule.csv", "w", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=["job_id", "step", "machine", "start", "end", "duration"]
        )
        writer.writeheader()
        writer.writerows(schedule)

    # Build charts
    chart1 = gantt_chart(schedule, all_machines)
    chart2 = utilization_chart(machine_util, makespan_val)

    # Write metrics
    with open("metrics.json", "w") as f:
        json.dump(
            {
                "result_value": makespan_val,
                "makespan": makespan_val,
                "avg_machine_utilization": round(avg_util, 4),
                "total_jobs": len(all_job_ids),
                "total_tasks": len(tasks),
                "status": STATUS_MAP.get(status_str, status_str),
            },
            f,
        )

    # Write assets
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
                    for a in [chart1, chart2]
                ]
            },
            f,
        )


if __name__ == "__main__":
    main()
