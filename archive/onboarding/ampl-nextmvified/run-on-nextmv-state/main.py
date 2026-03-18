# -*- coding: utf-8 -*-
#
# Description: generic python script to solve unit commitment problems with Amplpy and
# using Power Grid Lib.
#
# Author: Nicolau Santos <<nicolau@ampl.com>>
#
# See original reference https://colab.research.google.com/github/ampl/colab.ampl.com/blob/master/authors/nfbvs/pglib_uc/pglib_uc.ipynb

import json
import os
import time

import pandas as pd

# highs and gurobi modules will be used
from amplpy import AMPL, modules


def prepare_pglib_uc(data_file, log=True):
    data = json.load(open(data_file, "r"))

    thermal_gens_data = data["thermal_generators"]
    renewable_gens_data = data["renewable_generators"]

    startup_info = []
    piecewise_production_info = []

    T = data["time_periods"]
    S = {}
    L = {}

    for k, v in thermal_gens_data.items():
        for i, val in enumerate(v["startup"]):
            startup_info.append([k, i + 1, val["lag"], val["cost"]])

        S[k] = len(v["startup"])

        for i, val in enumerate(v["piecewise_production"]):
            piecewise_production_info.append([k, i + 1, val["mw"], val["cost"]])

        L[k] = len(v["piecewise_production"])

        del v["startup"]
        del v["piecewise_production"]

    df_thermal_gens = pd.DataFrame(thermal_gens_data).transpose()
    df_thermal_gens = df_thermal_gens.drop("name", axis=1)

    df_startup = pd.DataFrame(
        startup_info, columns=["gen", "cat", "startup_lag", "startup_cost"]
    ).set_index(["gen", "cat"])

    df_piecewise_production = pd.DataFrame(
        piecewise_production_info,
        columns=["gen", "int", "piecewise_mw", "piecewise_cost"],
    ).set_index(["gen", "int"])

    renewable_gens = list(renewable_gens_data)

    ren_power_output_minimum = {}
    ren_power_output_maximum = {}

    for k, v in renewable_gens_data.items():
        p_min = v["power_output_minimum"]

        for i, val in enumerate(p_min):
            ren_power_output_minimum[(k, i + 1)] = val

        p_max = v["power_output_maximum"]

        for i, val in enumerate(p_max):
            ren_power_output_maximum[(k, i + 1)] = val

    demand = data["demand"]
    reserves = data["reserves"]

    # pack everything in a dict and return data
    ampl_data = {}
    ampl_data["T"] = T
    ampl_data["S"] = S
    ampl_data["L"] = L
    ampl_data["demand"] = demand
    ampl_data["reserves"] = reserves
    ampl_data["renewable_gens"] = renewable_gens
    ampl_data["ren_power_output_minimum"] = ren_power_output_minimum
    ampl_data["ren_power_output_maximum"] = ren_power_output_maximum
    ampl_data["df_thermal_gens"] = df_thermal_gens
    ampl_data["df_startup"] = df_startup
    ampl_data["df_piecewise_production"] = df_piecewise_production

    return ampl_data


def run_uc(data, solver="highs", solver_options=None, log=True):
    start_time = time.time()

    # activate license if file with license uuid is present (otherwise use demo
    # license)
    if os.path.isfile("ampl_license_uuid.txt"):
        with open("ampl_license_uuid.txt") as file:
            license = file.read().strip()
        modules.activate(license)
    start_time = time.time()

    if log:
        print("Starting run_uc")

    # instantiate AMPL and load model
    ampl = AMPL()
    ampl.read("uc.mod")

    # load data
    if log:
        print("Loading data")

    ampl.set_data(data["df_thermal_gens"], "thermal_gens")
    ampl.param["S"] = data["S"]
    ampl.param["L"] = data["L"]
    ampl.param["T"] = data["T"]

    ampl.set["renewable_gens"] = data["renewable_gens"]
    ampl.param["ren_power_output_minimum"] = data["ren_power_output_minimum"]
    ampl.param["ren_power_output_maximum"] = data["ren_power_output_maximum"]

    ampl.set_data(data["df_startup"])
    ampl.set_data(data["df_piecewise_production"])

    ampl.param["demand"] = data["demand"]
    ampl.param["reserves"] = data["reserves"]

    # set solver and options
    if log:
        print("Setting solver and options")

    ampl.option["solver"] = solver

    if solver_options is not None:
        ampl.option[solver + "_options"] = solver_options

    # solve
    if log:
        print("Solving")
        ampl.solve()
    else:
        ampl.get_output("solve;")

    # check solve result and time
    solve_result = ampl.get_value("solve_result")
    solve_time = ampl.get_value("_total_solve_elapsed_time")

    assert ampl.solve_result in ["solved", "limit"], ampl.solve_result

    if solve_result != "solved":
        print("WARNING: solver returned '%s' status" % (solve_result,))

    # get result info
    # objective
    objective = ampl.obj["obj"].value()
    # dataframe with variables indexed by thermal_gens and time_periods
    df_tg_tp = ampl.get_data("cg", "pg", "rg", "ug", "vg", "wg").to_pandas()
    # dataframe with variables indexed by renewable_gens and time_periods
    df_rg_tp = ampl.get_data("pw").to_pandas()
    # dataframe with variables indexed by renewable_gens, gen_startup_categories and time_periods
    df_dg = ampl.get_data("dg").to_pandas()
    # dataframe with variables indexed by renewable_gens, gen_pwl_points and time_periods
    df_lg = ampl.get_data("lg").to_pandas()

    var_dict = {
        "thermal_info": df_tg_tp,
        "renewable_info": df_rg_tp,
        "dg_df": df_dg,
        "lg_df": df_lg,
    }

    end_time = time.time()

    result = {
        "nvars": ampl.get_value("_nvars"),
        "ncons": ampl.get_value("_ncons"),
        "objective": objective,
        "solve_result": solve_result,
        "solve_time": solve_time,
        "total_time": end_time - start_time,
        "vars": var_dict,
    }

    return result


data = prepare_pglib_uc("data.json")

# Solve with HiGHS

result_highs = run_uc(
    data, solver="highs", solver_options="outlev=1 timelim=30 threads=16"
)
with open("result_highs.txt", "w") as f:
    f.write(f"result: {result_highs}\n")

print(f"objective: {result_highs['objective']}")

# Solve with Gurobi

result_gurobi = run_uc(data, solver="gurobi", solver_options="outlev=1")
with open("result_gurobi.txt", "w") as f:
    f.write(f"result: {result_gurobi}\n")

print(f"objective: {result_gurobi['objective']}")
