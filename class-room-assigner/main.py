import nextmv
from pyomo.environ import (
    Binary,
    ConcreteModel,
    Constraint,
    Objective,
    Param,
    Set,
    SolverFactory,
    Var,
    maximize,
    value,
)
from visualizations import generate_visual_assets


def solve(input_data: dict, options: nextmv.Options) -> dict:
    """Solve the school class assignment problem using Pyomo."""

    students = input_data.get("students", [])
    classes = input_data.get("classes", [])

    # Create model
    model = ConcreteModel()

    # Sets
    student_ids = [s["id"] for s in students]
    class_ids = [c["id"] for c in classes]

    model.S = Set(initialize=student_ids)
    model.C = Set(initialize=class_ids)

    # Parameters
    student_data = {s["id"]: s for s in students}
    class_data = {c["id"]: c for c in classes}

    # Student priority (e.g., IEP/special needs students get higher priority)
    model.priority = Param(
        model.S, initialize={s["id"]: s.get("priority", 1) for s in students}
    )

    # Subject focus preference bonus
    # Calculate bonus for each (student, class) pair based on subject focus preferences
    def calc_focus_bonus(student_id, class_id):
        student_prefs = student_data[student_id].get("preferences", [])
        class_focus = class_data[class_id].get("subject_focus")
        if class_focus and class_focus in student_prefs:
            # Higher bonus for first preference, decreasing for later ones
            rank = student_prefs.index(class_focus)
            return len(student_prefs) - rank  # e.g., 3 prefs: 1st=3, 2nd=2, 3rd=1
        return 0

    focus_bonus = {(s, c): calc_focus_bonus(s, c) for s in student_ids for c in class_ids}
    model.focus_bonus = Param(model.S, model.C, initialize=focus_bonus)

    # Extended day penalty and bonus
    # Standard end of school day is 15 (3 PM)
    standard_end_time = 15

    # Identify students eligible for extended day (requested time within config limit)
    eligible_extended_day = [
        s for s in student_ids
        if student_data[s].get("extended_day_request")
        and student_data[s].get("extended_day_request") <= options.extended_day_time
    ]
    model.E = Set(initialize=eligible_extended_day)

    # Penalty based on hours past standard end time, bonus scaled by student priority
    extended_day_penalty = {}
    extended_day_bonus = {}
    for s in student_ids:
        requested_time = student_data[s].get("extended_day_request")
        if s in eligible_extended_day:
            hours_past = requested_time - standard_end_time
            student_priority = student_data[s].get("priority", 1)
            # Penalty = configurable rate * hours past standard end time
            extended_day_penalty[s] = options.extended_day_penalty * hours_past
            # Bonus = configurable bonus * student priority (higher priority = more valuable)
            extended_day_bonus[s] = options.extended_day_bonus * student_priority
        else:
            extended_day_penalty[s] = 0
            extended_day_bonus[s] = 0
    model.extended_day_penalty = Param(model.S, initialize=extended_day_penalty)
    model.extended_day_bonus = Param(model.S, initialize=extended_day_bonus)

    # Class capacity (max number of students)
    model.capacity = Param(
        model.C, initialize={c["id"]: c.get("capacity", 30) for c in classes}
    )

    # Decision variables: x[s,c] = 1 if student s is assigned to class c
    model.x = Var(model.S, model.C, domain=Binary)

    # Decision variable: y[s] = 1 if extended day is granted to student s
    model.y = Var(model.E, domain=Binary)

    # Objective: maximize total priority + focus bonus + extended day bonus - extended day penalty
    def objective_rule(m):
        priority_score = sum(m.priority[s] * m.x[s, c] for s in m.S for c in m.C)
        focus_score = sum(m.focus_bonus[s, c] * m.x[s, c] for s in m.S for c in m.C)
        # Extended day bonus/penalty only applies when granted (y[s] = 1)
        ext_bonus = sum(m.extended_day_bonus[s] * m.y[s] for s in m.E)
        ext_penalty = sum(m.extended_day_penalty[s] * m.y[s] for s in m.E)
        return priority_score + focus_score + ext_bonus - ext_penalty

    model.obj = Objective(rule=objective_rule, sense=maximize)

    # Constraint: each student assigned to at most one class
    def one_class_per_student_rule(m, s):
        return sum(m.x[s, c] for c in m.C) <= 1

    model.one_class_per_student = Constraint(model.S, rule=one_class_per_student_rule)

    # Constraint: class capacity not exceeded
    def class_capacity_rule(m, c):
        return sum(m.x[s, c] for s in m.S) <= m.capacity[c]

    model.class_capacity = Constraint(model.C, rule=class_capacity_rule)

    # Separation constraint: pairs of students who should not be in the same class
    separations = input_data.get("separations", [])
    separation_pairs = []
    for pair in separations:
        if len(pair) == 2:
            s1, s2 = pair[0], pair[1]
            if s1 in student_data and s2 in student_data:
                separation_pairs.append((s1, s2))

    def no_same_class_rule(m, s1, s2, c):
        return m.x[s1, c] + m.x[s2, c] <= 1

    model.no_same_class = Constraint(
        [(s1, s2, c) for (s1, s2) in separation_pairs for c in class_ids],
        rule=lambda m, s1, s2, c: no_same_class_rule(m, s1, s2, c),
    )

    # Class level matching constraint (students must be in classes matching their level)
    def class_level_match_rule(m, s, c):
        student_level = student_data[s].get("class_level")
        class_level = class_data[c].get("level")
        if student_level and class_level and student_level != class_level:
            return m.x[s, c] == 0
        return Constraint.Skip

    model.class_level_match = Constraint(model.S, model.C, rule=class_level_match_rule)

    # Constraint: extended day can only be granted if student is assigned a class
    def extended_day_requires_assignment_rule(m, s):
        return m.y[s] <= sum(m.x[s, c] for c in m.C)

    model.extended_day_requires_assignment = Constraint(
        model.E, rule=extended_day_requires_assignment_rule
    )

    # Solve
    solver = SolverFactory(options.solver)
    solver.options["timelimit"] = options.duration
    results = solver.solve(model, tee=False)

    # Extract solution
    assignments = []
    unassigned = []

    for s in model.S:
        assigned = False
        for c in model.C:
            if value(model.x[s, c]) > 0.5:
                student_prefs = student_data[s].get("preferences", [])
                class_focus = class_data[c].get("subject_focus")
                pref_match = (
                    class_focus in student_prefs if student_prefs and class_focus else None
                )
                requested_extended_day = student_data[s].get("extended_day_request")
                # Check if extended day was granted by the optimizer
                extended_day_granted = (
                    s in eligible_extended_day and value(model.y[s]) > 0.5
                )
                assignments.append(
                    {
                        "student_id": s,
                        "class_id": c,
                        "student_name": student_data[s].get("name", s),
                        "class_name": class_data[c].get("name", c),
                        "subject_focus": class_focus,
                        "focus_preference_match": pref_match,
                        "extended_day_requested": requested_extended_day,
                        "extended_day_granted": extended_day_granted,
                    }
                )
                assigned = True
                break
        if not assigned:
            unassigned.append(
                {
                    "student_id": s,
                    "student_name": student_data[s].get("name", s),
                    "reason": "No suitable class available",
                }
            )

    # Calculate preference statistics
    students_with_prefs = [
        a for a in assignments if student_data[a["student_id"]].get("preferences")
    ]
    prefs_met = sum(1 for a in assignments if a.get("focus_preference_match") is True)
    pref_percentage = (
        (prefs_met / len(students_with_prefs) * 100) if students_with_prefs else 0
    )

    # Calculate extended day statistics
    extended_day_requests = sum(
        1 for a in assignments if a.get("extended_day_requested") is not None
    )
    extended_day_granted_count = sum(
        1 for a in assignments if a.get("extended_day_granted") is True
    )
    extended_day_percentage = (
        (extended_day_granted_count / extended_day_requests * 100)
        if extended_day_requests
        else 0
    )

    solution = {
        "assignments": assignments,
        "unassigned": unassigned,
        "total_assigned": len(assignments),
        "total_students": len(students),
    }

    metrics = {
        "value": value(model.obj) if value(model.obj) else 0,
        "assigned_students": len(assignments),
        "unassigned_students": len(unassigned),
        "preferences_met": prefs_met,
        "preferences_met_percentage": round(pref_percentage, 1),
        "extended_day_requests": extended_day_requests,
        "extended_day_granted": extended_day_granted_count,
        "extended_day_granted_percentage": round(extended_day_percentage, 1),
        "solver_status": str(results.solver.status),
        "termination_condition": str(results.solver.termination_condition),
    }

    # Generate visual assets
    visual_assets = generate_visual_assets(input_data, solution, metrics)

    return solution, metrics, visual_assets


def main():
    """Entry point for the application."""

    options = nextmv.Manifest.from_yaml(".").extract_options()

    input_data = nextmv.load(options=options)

    nextmv.log("Solving school class assignment problem...")
    nextmv.log(f"  Students: {len(input_data.data.get('students', []))}")
    nextmv.log(f"  Classes: {len(input_data.data.get('classes', []))}")

    solution, metrics, visual_assets = solve(input_data.data, options)

    nextmv.log(f"  Assigned: {solution['total_assigned']}/{solution['total_students']}")

    output = nextmv.Output(
        options=options, solution=solution, metrics=metrics, assets=visual_assets
    )
    nextmv.write(output)


if __name__ == "__main__":
    main()
