"""Greedy dispatching heuristics for machine shop scheduling.

Implements list-scheduling for job shop problems. Tasks are scheduled
greedily by assigning the highest-priority eligible operation to each
free machine at every decision point.

Dispatch rules
--------------
spt  – Shortest Processing Time first: minimises average flow time
lpt  – Longest Processing Time first: improves load balancing
fifo – First-In-First-Out: natural job-input order
"""

from collections import defaultdict

DISPATCH_RULES = ("spt", "lpt", "fifo")


def greedy_schedule(jobs, changeovers, changeover_weight, dispatch_rule="spt"):
    """Return a feasible schedule produced by greedy list scheduling.

    Parameters
    ----------
    jobs : dict[str, list[dict]]
        job_id -> list of ops (sorted by sequence), each op has keys
        ``machine`` and ``duration``.
    changeovers : dict[(str, str, str), int]
        (machine, from_job, to_job) -> changeover minutes.
    changeover_weight : float
        Multiplier applied to every changeover time.
    dispatch_rule : str
        One of "spt", "lpt", "fifo".

    Returns
    -------
    list[dict]
        Schedule rows with keys: job_id, step, machine, start, end, duration.
    """
    if dispatch_rule not in DISPATCH_RULES:
        dispatch_rule = "spt"

    # Earliest time each machine is free
    machine_free_at = defaultdict(int)
    # Last job processed on each machine (for changeover lookup)
    machine_last_job = {}
    # Earliest time each job's next step may start (respects precedence)
    job_free_at = {job_id: 0 for job_id in jobs}
    # Index of next unscheduled step per job
    job_next_step = {job_id: 0 for job_id in jobs}

    schedule = []
    total_tasks = sum(len(ops) for ops in jobs.values())

    while len(schedule) < total_tasks:
        # Collect one eligible task per job: its next unscheduled step
        machine_candidates = defaultdict(list)
        for job_id, ops in jobs.items():
            step = job_next_step[job_id]
            if step < len(ops):
                op = ops[step]
                machine_candidates[op["machine"]].append(
                    {
                        "job_id": job_id,
                        "step": step,
                        "machine": op["machine"],
                        "duration": op["duration"],
                    }
                )

        if not machine_candidates:
            break

        made_assignment = False
        for machine in sorted(machine_candidates):
            candidates = machine_candidates[machine]

            if dispatch_rule == "spt":
                candidates.sort(key=lambda t: t["duration"])
            elif dispatch_rule == "lpt":
                candidates.sort(key=lambda t: -t["duration"])
            # fifo: preserves dict-insertion order (Python 3.7+)

            task = candidates[0]
            job_id = task["job_id"]

            # Changeover: applies when previous job on this machine differs
            last_job = machine_last_job.get(machine)
            co = 0
            if last_job and last_job != job_id:
                base_co = changeovers.get((machine, last_job, job_id), 0)
                co = int(round(base_co * changeover_weight))

            # Start as soon as both the machine (+ changeover) and the job are ready
            start = max(machine_free_at[machine] + co, job_free_at[job_id])
            end = start + task["duration"]

            schedule.append(
                {
                    "job_id": job_id,
                    "step": task["step"],
                    "machine": machine,
                    "start": start,
                    "end": end,
                    "duration": task["duration"],
                }
            )

            machine_free_at[machine] = end
            machine_last_job[machine] = job_id
            job_free_at[job_id] = end
            job_next_step[job_id] = task["step"] + 1
            made_assignment = True

        if not made_assignment:
            break

    return schedule
