# Sets and parameters

set thermal_gens;
set renewable_gens;

param S {thermal_gens};
set gen_startup_categories {g in thermal_gens} := 1..S[g];

param startup_lag  {g in thermal_gens, gen_startup_categories[g]};
param startup_cost {g in thermal_gens, gen_startup_categories[g]};

param L {thermal_gens};
set gen_pwl_points {g in thermal_gens} := 1..L[g];

param piecewise_mw   {g in thermal_gens, gen_pwl_points[g]};
param piecewise_cost {g in thermal_gens, gen_pwl_points[g]};

param T;
set time_periods := 1..T;

param demand   {time_periods};
param reserves {time_periods};

param must_run             {thermal_gens};
param power_output_minimum {thermal_gens};
param power_output_maximum {thermal_gens};
param ramp_up_limit        {thermal_gens};
param ramp_down_limit      {thermal_gens};
param ramp_startup_limit   {thermal_gens};
param ramp_shutdown_limit  {thermal_gens};
param time_up_minimum      {thermal_gens};
param time_down_minimum    {thermal_gens};
param power_output_t0      {thermal_gens};
param unit_on_t0           {thermal_gens};
param time_down_t0         {thermal_gens};
param time_up_t0           {thermal_gens};


# Renewable Generator Parameters
param ren_power_output_minimum {renewable_gens, time_periods};
param ren_power_output_maximum {renewable_gens, time_periods};

# Variables
var cg {thermal_gens, time_periods};
var pg {thermal_gens, time_periods} >= 0;
var rg {thermal_gens, time_periods} >= 0;
var pw {renewable_gens, time_periods} >= 0;
var ug {thermal_gens, time_periods} binary;
var vg {thermal_gens, time_periods} binary;
var wg {thermal_gens, time_periods} binary;
var dg {g in thermal_gens, gen_startup_categories[g], time_periods} binary;
var lg {g in thermal_gens, gen_pwl_points[g], time_periods} >= 0, <= 1;

# Objective

#(1)
minimize obj:
	sum{g in thermal_gens, t in time_periods}(
		cg[g,t] +
		piecewise_cost[g, 1] * ug[g,t] +
		sum{s in gen_startup_categories[g]}(
			startup_cost[g, s] * dg[g,s,t]
		)
	);

# Constraints

#(2)
s.t. UCDemand {t in time_periods}:
	sum{g in thermal_gens}(pg[g,t] + power_output_minimum[g] * ug[g,t]) + sum{w in renewable_gens} pw[w,t] == demand[t];

#(3)
s.t. UCReserves {t in time_periods}:
	sum{g in thermal_gens} rg[g,t] >= reserves[t];

#(4)
s.t. initialUpRequirement {g in thermal_gens: unit_on_t0[g] == 1}:
	sum{t in 1 .. min(time_up_minimum[g] - time_up_t0[g], T)} (ug[g,t] - 1) == 0;

#(5)
s.t. initialDownRequirement {g in thermal_gens: unit_on_t0[g] == 0}:
	sum{t in 1 .. min(time_down_minimum[g] - time_down_t0[g], T)} ug[g,t] == 0;

#(6)
s.t. LogicalInitial {g in thermal_gens}:
	ug[g,1] - unit_on_t0[g] == vg[g,1] - wg[g,1];

#(7)
s.t. STIInit {g in thermal_gens}:
	sum{
		s in 1..(S[g]-1),
		t in
			(max(1, startup_lag[g, s+1] - time_down_t0[g] + 1)) ..
			(min(startup_lag[g, s+1]-1, T))
	} dg[g,s,t] == 0;

#(8)
s.t. RampUpInit {g in thermal_gens}:
	pg[g,1] + rg[g,1] - unit_on_t0[g] * (power_output_t0[g] - power_output_minimum[g]) <= ramp_up_limit[g];

#(9)
s.t. RampDownInit {g in thermal_gens}:
	unit_on_t0[g] * (power_output_t0[g] - power_output_minimum[g]) - pg[g,1] <= ramp_down_limit[g];

#(10)
s.t. MaxOutput2Init {g in thermal_gens}:
	unit_on_t0[g] * (power_output_t0[g] - power_output_minimum[g]) <=
		unit_on_t0[g] *(power_output_maximum[g] - power_output_minimum[g]) - max((power_output_maximum[g] - ramp_shutdown_limit[g]),0) * wg[g,1];

#(11)
s.t. MustRun {g in thermal_gens, t in time_periods}:
	ug[g,t] >= must_run[g];

#(12)
s.t. Logical {g in thermal_gens, t in time_periods: t != 1}:
	ug[g,t] - ug[g,t-1] == vg[g,t] - wg[g,t];

#(13)
s.t. Startup {g in thermal_gens, t in min(time_up_minimum[g], T) .. T}:
	sum{i in (t - min(time_up_minimum[g], T) + 1).. t} vg[g,i] <= ug[g,t];

#(14)
s.t. Shutdown {g in thermal_gens, t in min(time_down_minimum[g], T) .. T}:
	sum{i in (t - min(time_down_minimum[g], T) + 1) .. t} wg[g,i] <= 1 - ug[g,t];

#(15)
s.t. STISelect {
	g in thermal_gens,
	s in gen_startup_categories[g],
	t in startup_lag[g, s+1] .. T:
		s != S[g]
	}:
	dg[g,s,t] <= sum{i in startup_lag[g, s] .. (startup_lag[g, s+1]-1)} wg[g,t-i];

#(16)
s.t. STILink {g in thermal_gens, t in time_periods}:
	vg[g,t] == sum{s in 1..S[g]} dg[g,s,t];

#(17)
s.t. MaxOutput1 {g in thermal_gens, t in time_periods}:
	pg[g,t] + rg[g,t] <=
	(power_output_maximum[g] - power_output_minimum[g]) * ug[g,t] -
	max((power_output_maximum[g] - ramp_startup_limit[g]),0) * vg[g,t];

#(18)
s.t. MaxOutput2 {g in thermal_gens, t in time_periods: t != T}:
	pg[g,t] + rg[g,t] <=
	(power_output_maximum[g] - power_output_minimum[g]) * ug[g,t] -
	max((power_output_maximum[g] - ramp_shutdown_limit[g]),0) * wg[g,t+1];

#(19)
s.t. RampUp {g in thermal_gens, t in time_periods: t != 1}:
	pg[g,t] + rg[g,t] - pg[g,t-1] <= ramp_up_limit[g];

#(20)
s.t. RampDown {g in thermal_gens, t in time_periods: t != 1}:
	pg[g,t-1] - pg[g,t] <= ramp_down_limit[g];

#(21)
s.t. PiecewiseParts {g in thermal_gens, t in time_periods}:
	pg[g,t] == sum{l in gen_pwl_points[g]}(piecewise_mw[g,l] - piecewise_mw[g,1]) * lg[g,l,t];

#(22)
s.t. PiecewisePartsCost {g in thermal_gens, t in time_periods}:
	cg[g,t] == sum{l in gen_pwl_points[g]}((piecewise_cost[g,l] - piecewise_cost[g,1]) * lg[g,l,t]);

#(23)
s.t. PiecewiseLimits {g in thermal_gens, t in time_periods}:
	ug[g,t] == sum{l in gen_pwl_points[g]} lg[g,l,t];

#(24)
s.t. WindLimit {w in renewable_gens, t in time_periods}:
	ren_power_output_minimum[w,t] <= pw[w,t] <= ren_power_output_maximum[w,t];

