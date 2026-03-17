#!/usr/bin/env python3.11

# Copyright 2025, Gurobi Optimization, LLC

# Solve the classic diet model, showing how to add constraints
# to an existing model.

import json

import gurobipy as gp
import nextmv
from gurobipy import GRB
from nextmv import cloud

# Nutrition guidelines, based on
# USDA Dietary Guidelines for Americans, 2005
# http://www.health.gov/DietaryGuidelines/dga2005/

# MODIFIED - load manifest and extract options to use in the execution
manifest = cloud.Manifest.from_yaml(".")
options = manifest.extract_options()


# Load data from JSON file
with open("diet_data.json", "r") as f:
    data = json.load(f)

# Extract categories and nutrition limits
categories = list(data["categories"].keys())
minNutrition = {}
maxNutrition = {}

for category in categories:
    minNutrition[category] = data["categories"][category]["min"]
    max_val = data["categories"][category]["max"]
    maxNutrition[category] = GRB.INFINITY if max_val is None else max_val

# Extract foods and costs
foods = list(data["foods"].keys())
cost = {}
for food in foods:
    cost[food] = data["foods"][food]["cost"]

# Extract nutrition values
nutritionValues = {}
for food in foods:
    for category in categories:
        nutritionValues[(food, category)] = data["foods"][food]["nutrition"][category]

# Model
m = gp.Model("diet")

# Create decision variables for the foods to buy
buy = m.addVars(foods, name="buy")


# The objective is to minimize the costs
m.setObjective(buy.prod(cost), GRB.MINIMIZE)


# Nutrition constraints
m.addConstrs(
    (
        gp.quicksum(nutritionValues[f, c] * buy[f] for f in foods)
        == [minNutrition[c], maxNutrition[c]]
        for c in categories
    ),
    "_",
)


def printSolution(filename="solution.txt", append=False):
    mode = "a" if append else "w"
    with open(filename, mode) as f:
        if m.status == GRB.OPTIMAL:
            result = f"\nCost: {m.ObjVal:g}\n"
            result += "\nBuy:\n"
            for food in foods:
                if buy[food].X > 0.0001:
                    result += f"{food} {buy[food].X:g}\n"

            # Print to console
            print(result.strip())
            # Write to file
            f.write(result)
        else:
            message = "No solution\n"
            print("No solution")
            f.write(message)


if options.limit_dairy:
    m.addConstr(buy.sum(["milk", "ice cream"]) <= 10, "limit_dairy")

# Solve
m.optimize()
printSolution("solution.txt", append=True)


# MODIFIED - write statistics to statistics.json
statistics_file = "statistics.json"
with open(statistics_file, "w") as stats_f:
    statistics = nextmv.Statistics(
        result=nextmv.ResultStatistics(
            duration=m.Runtime,
            value=m.ObjVal,
            custom={
                "nvars": m.NumVars,
                "ncons": m.NumConstrs,
            },
        ),
    )
    stats_f.write(json.dumps({"statistics": statistics.to_dict()}))
