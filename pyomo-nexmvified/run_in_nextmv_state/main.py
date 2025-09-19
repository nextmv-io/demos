#!/usr/bin/env python3

import json

import nextmv
from diet import model
from nextmv import cloud
from pyomo.environ import value
from pyomo.opt import SolverFactory


def main():
    """
    Main function to solve the diet optimization problem using Pyomo functions.
    """
    # MODIFIED - redirect solver chatter from stdout to stderr 
    nextmv.redirect_stdout()
    
    # MODIFIED - read input from inputs/diet.dat
    instance = model.create_instance("inputs/diet.dat")
    solver = SolverFactory("glpk")
    if not solver.available():
        
        print(f"Error: glpk solver is not available!")
        print("Please install the solver or try a different solver.")
        return
    results = solver.solve(instance, tee=True)
    
    # MODIFIED - write output to outputs/solutions
    output_file = "outputs/solutions/diet_solution.txt"
    with open(output_file, "w") as f:
        if results.solver.termination_condition == "optimal":
            f.write("=" * 50 + "\n")
            f.write("DIET OPTIMIZATION SOLUTION\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Minimum cost: ${value(instance.cost):.2f}\n\n")
            f.write("Optimal food selections:\n")
            f.write("-" * 40 + "\n")
            total_cost = 0
            for food in instance.F:
                servings = value(instance.x[food])
                if servings > 0:
                    cost_per_serving = value(instance.c[food])
                    food_cost = cost_per_serving * servings
                    total_cost += food_cost
                    f.write(
                        f"{food:18s}: {servings:2.0f} servings @ ${cost_per_serving:.2f} = ${food_cost:.2f}\n"
                    )
        else:
            f.write(
                f"Solver terminated with condition: {results.solver.termination_condition}\n"
            )
            f.write("No optimal solution found.\n")

    print(f"Results written to {output_file}")


if __name__ == "__main__":
    main()
