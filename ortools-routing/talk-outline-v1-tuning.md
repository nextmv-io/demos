# Ship Better Routes: Testing and Tuning a Solver with Nextmv

## TL;DR — the whole talk on one screen

**One-liner:** same model, same solver, same input — the *search settings* decide whether you ship a good route, a 4%-worse one, or no route at all.

**The app:** a delivery route planner on **OR-Tools** (free solver). Depot + vehicles + stops → cheapest valid routes. **Nextmv** is the platform around it: run it, tune it, test it, operate it — solver-agnostic.

**The two levers we expose** (both hard-coded to `AUTOMATIC` in the stock app):

- **Build lever — `first_solution_strategy`:** the *construction recipe* that builds the first routes from scratch (`PATH_CHEAPEST_ARC`, `GLOBAL_CHEAPEST_ARC`, `SAVINGS`, …). Different recipes → different starting routes; some build **no valid route at all**. *(Not a warm start — it's how the starting point is generated, not a prior solution handed in.)*
- **Improve lever — `local_search_metaheuristic`:** how it improves those routes until time runs out (`GREEDY_DESCENT` gets stuck; `GUIDED_LOCAL_SEARCH` keeps climbing if given time). Plus `duration` = the time budget.

**Three Nextmv features used:** Runs · Scenario tests (sweep configs) · Ensembles (run several, return the best feasible). All driven live through the **MCP server** in plain English.

**Demo arc (the throughline):**

1. Sweep the **build** lever → best is **~4% cheaper for free** (30,230 vs 31,463 default); two strategies return **no route**.
2. Sweep the **improve** lever × time → the right one depends on your **latency budget**.
3. The twist (feasibility grid) → the Part-1 champion **fails on all 4** realistic inputs; **no single setting is safe everywhere**.
4. The answer → **ensemble**: run a portfolio, return the best route that actually came back. On `metro-tight` the **tuned champion returns nothing**, yet the ensemble still ships a route (SAVINGS).

**Recap:** **Expose → Sweep → Ensemble.** Same workflow for any solver (OR-Tools, Nextroute, HiGHS, Gurobi, FICO Xpress).

---

## Talk Track & Slide Outline (OR-Tools routing demo)

**Total: ~30 min (27.5 min content + ~2.5 min Q&A)**

> Demo app: `ortools-routing/` in this repo — the `python-ortools-routing`
> community app, modified to expose OR-Tools' search strategy as tunable
> options. All numbers below are real and reproducible from the scripts in that
> directory (`generate_input.py`, `explore_feasibility.py`, `sweep.py`).
>
> Audience: Nextmv customers + prospects (model builders, infra/ops) and FICO
> folks post-acquisition. The throughline — **Nextmv is the solver-agnostic
> DecisionOps layer: test, tune, and operate any solver** — is aimed squarely
> at that mixed room.

---

## Slide 1 — Title (30 sec)

**"Ship Better Routes: Testing and Tuning a Solver with Nextmv"**

One-liner: "Same model, same solver, same input — the settings decide whether you ship a good route, a 4% worse one, or no route at all."

---

## Slide 2 — What is Nextmv? (2 min)

**"A platform for building, testing, and deploying decision models — whatever solver is underneath."**

- Nextmv is a DecisionOps platform — think DevOps, but for optimization models
- You build a model (routing, scheduling, pricing) on the solver of your choice — OR-Tools, Nextroute, HiGHS, Gurobi, **FICO Xpress** — deploy it to Nextmv Cloud, and get a layer to test, tune, and operate it
- Three features we'll use today:

| Feature | What it does |
|---------|--------------|
| **Runs** | Execute the model with different settings — no code changes |
| **Scenario tests** | Sweep many configurations against the same input in one shot |
| **Ensemble definitions** | Run multiple configs in parallel, return the best result per request |

- Plus the **MCP server** — drive all of it from an AI assistant in natural language

### Talk track

> Nextmv sits on top of your solver and gives you the testing and deployment layer around it. It's solver-agnostic on purpose — OR-Tools today, but the exact same workflow wraps Nextroute, HiGHS, Gurobi, or Xpress. Today I'll tune an OR-Tools routing model — its build strategy and its improvement strategy — and drive the whole thing through the MCP server.

---

## Slide 3 — The Problem (2 min)

**"A solver has knobs that have nothing to do with your data — and the right setting isn't obvious."**

- Our model: a vehicle routing problem on OR-Tools. Stops, vehicles, capacities, a depot.
- OR-Tools doesn't just "solve" — it asks you to choose a **search strategy**:
  - a **first-solution strategy** (how it builds the initial routes), and
  - a **local-search metaheuristic** (how it improves them until time runs out)
- These don't change the *problem* — they change *how the solver searches*. And the best choice depends on the input and your time budget.

### Talk track

> Here's a thing people miss about solvers: a big chunk of the tuning surface has nothing to do with your business data. It's how the *search* is configured. OR-Tools gives you a dozen ways to build the first routes and half a dozen ways to improve them. Pick wrong and you leave money on the table — or get nothing back at all. And nobody hand-picks these by reading the docs; they leave them on default and hope.

---

## Slide 4 — The Knobs (1.5 min)

**"Two settings, hidden in plain sight."**

```python
# What the community app ships with — hardcoded:
search_parameters.first_solution_strategy      = FirstSolutionStrategy.AUTOMATIC
search_parameters.local_search_metaheuristic   = LocalSearchMetaheuristic.AUTOMATIC
```

- The stock app **hardcodes both to AUTOMATIC** — you can't even test alternatives
- Step one of tuning is often just *exposing the knob*. We promoted both to Nextmv options (a few lines), so now they're sweepable, testable, and selectable in the Console.

### Talk track

> Step zero of tuning is making the thing tunable. The community app hardcodes both strategies to AUTOMATIC — so there's nothing to test. Five lines later they're first-class Nextmv options with dropdowns in the Console. That's the unlock: once a decision is a parameter, the platform can test it for you.

---

## Slide 5 — Guess-and-Check vs. Workflow (1.5 min)

| Guess-and-check | Workflow |
|-----------------|----------|
| Leave it on AUTOMATIC, hope | Sweep every strategy in one test |
| "Seems fine" | Measurable: objective, runtime, feasibility |
| One config, every input | Test across input shapes |
| Pray it never returns nothing | Ensemble: run several, return the best feasible |

### Talk track

> The rest of the talk replaces the left column with the right. Sweep the strategies and — because the best one changes with the input — ensemble them. And the MCP server makes it a conversation instead of an afternoon of clicking.

---

## Slide 6 — What is the MCP Server? (1.5 min)

**"Your AI assistant talks directly to the platform."**

- MCP = Model Context Protocol — an open standard letting AI tools (Claude, Cursor) call APIs on your behalf
- The Nextmv MCP server lets your assistant run the app, create tests, build ensembles, read results
- You describe what you want; it executes — no clicking through the Console per run

### Talk track

> Think of it as giving your AI pair-programmer direct access to Nextmv Cloud. "Sweep the first-solution strategy across all eight options at a five-second budget" — and it builds and runs the scenario test. That's what makes this practical live.

---

## Slide 7 — Section Divider — **"Let's see it."**

---

## Demo Operations — Prep vs. Live (READ THIS BEFORE PRESENTING)

> The golden rule for a live MCP demo: **all heavy compute is done before you
> walk on stage.** Scenario tests and the ensemble all take
> tens of seconds to minutes to finish. You do NOT run those cold in front of an
> audience. You set them up ahead of time so their results are cached and visible
> in the Console, and on stage you mostly *trigger one quick thing* and *open
> what's already computed* — narrating as you go.

### ✅ BEFORE the talk — pre-flight setup (already done / verify these exist)

Everything in this list should already be deployed and have cached results. If
you're picking this talk up cold, run the checklist to recreate it.

| # | Item | Identifier | Status |
|---|------|-----------|--------|
| 1 | Cloud app deployed | app `ortools-routing`, version `version-ui7q5ohd` (v1.2) | ✅ |
| 2 | Instance — stock config | `default` (AUTOMATIC, duration 5s) | ✅ |
| 3 | Instance — tuned config | `tuned` (GLOBAL_CHEAPEST_ARC, GUIDED_LOCAL_SEARCH, 5s) | ✅ |
| 4 | Input sets | `tuning-input` (from `input.json`), `stress-suite` (4 stress inputs) | ✅ |
| 5 | Scenario test — first-solution sweep | `sweep-first-solution` (8 runs) | ✅ |
| 6 | Scenario test — metaheuristic × budget | `metaheuristic-budget` (12 runs) | ✅ |
| 7 | Ensemble definition (5-strategy portfolio, 1 rule) | `best-feasible-route` | ✅ |
| 8 | Managed inputs (warm) for the stress suite | `metro-tight`, `suburb-tight`, `metro-normal`, `regional-big` | ✅ |
| 9 | Scenario test — feasibility matrix (Slide 8) | `stress-matrix` (32 runs) | ✅ |

**Also before you start:**
- Open the Nextmv Console to the `ortools-routing` app; have these tabs ready:
  the **Runs** view (for the baseline map), the three **Scenario test** results
  (sweep, metaheuristic, feasibility grid), and the **Ensemble** definition.
- Confirm the MCP server is connected in your assistant: `claude mcp list` shows
  `nextmv` Connected. (Setup + the PATH gotcha are in the `nextmv-mcp-setup` note.)
- Have `ortools-routing/input.json` and the four stress inputs
  (`inputs/metro-tight.json`, `inputs/suburb-tight.json`, `inputs/metro-normal.json`,
  `inputs/regional-big.json`) on hand in case you want to show the raw input.
- Do one **throwaway live run** in rehearsal right before doors open so the
  container is warm — the first cold run of the session can be slow to schedule.

### 🎤 LIVE on stage — what you actually do per demo part

These are the only things you execute in front of the audience. Each is either a
single fast run (~5s) or *opening an already-computed result*. Exact MCP prompts
and what to click are in each Demo Part below, tagged **🎤 LIVE** vs **✅ PRE-BUILT**.

| Demo part | Live action (≈time) | Backed by (pre-built) |
|---|---|---|
| 1 — Baseline + sweep | Trigger 1 live baseline run on `default` (~5s) → open the pre-built first-solution scenario test | items 1–5 |
| 2 — Metaheuristic × budget | Open the pre-built metaheuristic×budget scenario test | item 6 |
| Slide 8 — feasibility grid | Open the pre-built `stress-matrix` scenario test | item 9 |
| 3 — Ensemble | Run `tuned` on `metro-tight` → **no route** (~5s); then run the ensemble on the *same* input → **SAVINGS ships a route** (~5s); open the other three pre-computed | items 2, 7, 8 |

> If the network or Cloud is flaky on the day: every number in the tables below is
> already cached in the Console, so you can present entirely from pre-built results
> and skip the live triggers without losing the story.

---

## Demo Part 1 — Baseline + Sweep the Build Strategy (4 min)

**Input:** `input.json` — 150 stops, 10 vehicles, clustered, capacity binds.

### Actions
1. **🎤 LIVE (~5s):** Run with defaults (`AUTOMATIC`/`AUTOMATIC`) on the `default` instance via MCP — *"Run the ortools-routing app on input.json with the default instance."* Show routes on the map + objective **31,463**. (This is the one fresh run here — it proves the demo is live.)
2. **✅ PRE-BUILT — open, don't create:** Open the pre-built `sweep-first-solution` scenario test and walk the results table. *Do not create it live — it sweeps 8 strategies × 5s and takes too long.* If you want to show the MCP call, say *"Show me the sweep-first-solution scenario test results"* (a read, returns instantly).

**Scenario test result** (real cloud numbers, objective, lower is better; metaheuristic held at GUIDED_LOCAL_SEARCH, 5s):

| First-solution strategy | Objective | |
|---|---|---|
| AUTOMATIC | 31,242 | |
| PATH_CHEAPEST_ARC | 31,463 | |
| **GLOBAL_CHEAPEST_ARC** | **30,230** | **← best, −3.9% vs the 31,463 default** |
| SAVINGS | 30,640 | |
| PARALLEL_CHEAPEST_INSERTION | 31,009 | |
| LOCAL_CHEAPEST_ARC | 30,957 | |
| SWEEP | **NO SOLUTION** | |
| CHRISTOFIDES | **NO SOLUTION** | |

> Note: the stock default (`AUTOMATIC`/`AUTOMATIC`) returns **31,463**. In the sweep we hold the metaheuristic at GLS, so the `AUTOMATIC` *first-solution* row is 31,242 — and notice it is **not** the same as `PATH_CHEAPEST_ARC` (31,463): AUTOMATIC picks its own constructor, and here it's neither the default's pick nor the best one.

### Talk track

> The default route costs 31,463. Now I sweep all eight build strategies in one test. Two things jump out. First, the best strategy — global-cheapest-arc — comes in at 30,230, about **4% cheaper**, same solver, same five seconds, for free; nobody chose it, it was just sitting in a dropdown. Second — and remember this — two strategies, SWEEP and CHRISTOFIDES, return *no solution at all* on this capacitated problem. The knob you never looked at was quietly costing you 4%, and two of its settings are landmines.

---

## Demo Part 2 — The Metaheuristic Depends on Your Time Budget (3 min)

**✅ PRE-BUILT — open, don't create:** the `metaheuristic-budget` scenario test (12 runs). **Scenario test: metaheuristic × solve time** (real cloud numbers, from PATH_CHEAPEST_ARC, on `input.json`):

| Metaheuristic | 2s | 10s | 30s |
|---|---|---|---|
| GREEDY_DESCENT | 31,463 | 31,463 | 31,463 |
| SIMULATED_ANNEALING | 31,500 | 31,500 | 31,500 |
| TABU_SEARCH | 31,500 | 31,500 | 31,231 |
| **GUIDED_LOCAL_SEARCH** | 31,463 | 31,101 | **30,995** |

### Talk track

> Now the improvement knob — and here the lesson is about *time*, not a big number. Greedy descent and simulated annealing get *stuck*: same objective at 2 seconds and at 30, more time buys nothing. Guided local search starts no better, but it climbs out of local optima and keeps improving — 31,463 down to 30,995 as the budget grows. The gap is modest here, but the *shape* is the point: if you have a 2-second SLA, the metaheuristic barely matters; if you have 30 seconds, GLS is the one that actually uses them. The biggest single win was the build strategy we just saw (~4%); this knob is the one you tune to your latency budget. Either way, you can only know by testing — and that sets up the real question.

---

## Slide 8 — The Real Question: Can You Hard-Code One Strategy? (2.5 min)

**"We tuned a champion on one input. Does it hold — or even *run* — on others?"**

**✅ PRE-BUILT — open the `stress-matrix` scenario test.** Four production-shaped inputs near the feasibility edge (tight shift length + capacity), every strategy swept (GLS, 5s, all real cloud runs). **`X` = returns no route at all:**

```
strategy                     metro-tight  suburb-tight  metro-normal  regional-big
AUTOMATIC (default pick)          X            X          30,384       57,146
PATH_CHEAPEST_ARC                 X            X          30,384       57,146
PATH_MOST_CONSTRAINED_ARC         X         29,056        30,539       56,994
GLOBAL_CHEAPEST_ARC (champion)    X            X             X            X
LOCAL_CHEAPEST_ARC                X            X             X            X
LOCAL_CHEAPEST_INSERTION          X            X          31,067       62,075
SAVINGS                        30,574       29,344        30,787         X
PARALLEL_CHEAPEST_INSERTION       X            X          30,288       57,123
─────────────────────────────────────────────────────────────────────────────
feasible strategies / 8           1            2             6            5
```

Three things jump off this grid:
1. **The champion is a landmine.** `GLOBAL_CHEAPEST_ARC` — our Part-1 winner — returns **no route on all four**.
2. **On `metro-tight`, 7 of 8 strategies return nothing** — only `SAVINGS` finds a route.
3. **No single row is green all the way across.** `SAVINGS` is the *only* survivor on metro-tight, yet it's the *one that fails* on regional-big. Whatever you hard-code, some input breaks it.

### Talk track

> We crowned global-cheapest-arc as our champion. Here it is on four real-world-shaped inputs: no route, no route, no route, no route. The setting that won our benchmark is a landmine in production. Now look across the grid. On the tight-shift input — metro-tight — *seven of eight* strategies come back empty; only Savings finds a route. So you'd ship Savings… except on the big regional input, Savings is the one that fails. There is no column you can pick that's green top to bottom. You cannot hard-code your way out of this — which is exactly what an ensemble is for.

---

## Slide 9 — Ensembles: Don't Pick One — Run Several (2 min)

**"Run a handful of strong configs; return the best feasible result per request."**

- Two things an ensemble buys you here:
  1. **Robustness (the big one)** — at least one config always returns a feasible answer, even when others choke on a given input
  2. **Best-per-input** — you capture the winner without having to predict, per input, which strategy that'll be
- The rule is one line: **return the lowest-cost route.** Infeasible configs report a sentinel (huge) cost, so "feasible first, then cheapest" falls out of a single `minimize objective` rule — no separate feasibility check needed

### Talk track

> An ensemble runs several configs in parallel and returns the best one that actually worked. You're not betting on a single strategy surviving tomorrow's input — you're hedging. The rule is just "lowest-cost route wins" — and because a config that finds nothing reports an impossibly high cost, that one rule quietly means "feasible first, then cheapest." You stop predicting and start covering.

---

## Demo Part 3 — Create & Run the Ensemble via MCP (3 min)

### Actions
1. **🎤 LIVE (~5s) — the champion fails:** Run the **`tuned`** instance (GLOBAL_CHEAPEST_ARC + GLS — the Part-1 champion) on `metro-tight` — *"Run the ortools-routing app on the metro-tight input with the tuned instance."* It comes back **`solution_found: false` — no route, zero vehicles**, and the **metrics tab shows `first_solution_strategy: GLOBAL_CHEAPEST_ARC`** so the audience sees exactly which config failed (cached run `tuned-Cqb3b-aDR`). The config we crowned ten minutes ago returns *nothing* on a real input.
2. **✅ PRE-BUILT:** ensemble `best-feasible-route` — a **5-strategy portfolio** (all GLS, 5s): `AUTOMATIC`, `PATH_CHEAPEST_ARC`, `PATH_MOST_CONSTRAINED_ARC`, `SAVINGS`, `PARALLEL_CHEAPEST_INSERTION`. One rule: minimize objective (`$.result.value`); infeasible members report a sentinel cost, so feasible-first is automatic.
3. **🎤 LIVE (~5–10s) — the ensemble saves it:** run the ensemble on the **same input** — *"Run the best-feasible-route ensemble on the metro-tight input."* It returns a route (SAVINGS, ~30,500) even though the tuned champion — and 7 of 8 raw strategies — fail there. Then open the three pre-computed runs.

| Input | Ensemble returns | Why it matters |
|---|---|---|
| metro-tight | SAVINGS → **30,505** | 7 of 8 strategies returned nothing — ensemble still ships a route |
| suburb-tight | PATH_MOST_CONSTRAINED → **29,056** | AUTOMATIC & PARALLEL both failed here |
| metro-normal | PARALLEL_CHEAPEST_INSERTION → **30,288** | a normal input — best of six survivors |
| regional-big | PATH_MOST_CONSTRAINED → **56,994** | SAVINGS failed here |

### Talk track

> Watch this. The config we crowned the champion — global-cheapest-arc — on this exact input: no route. Nothing. The setting that won our benchmark *ships nothing* in production. Now the ensemble, *same input*: it comes back with a route. That's the whole argument in one A/B. And it's not a fluke — same ensemble, four inputs, and it returns a *different* strategy almost every time: Savings, then path-most-constrained, then parallel-insertion, then path-most-constrained again. On metro-tight, seven of eight strategies came back empty and the ensemble still shipped a route. On regional-big, the strategy that saved us on metro-tight — Savings — is the one that failed, and the ensemble just reached for a different member. You're not predicting the winner or the failure anymore. You run five, you take the best one that came home, every request. That's the safety net — and it's the same `$.result.value` rule doing feasibility and quality at once.

---

## Slide 10 — The Full Workflow (1.5 min)

**"Expose. Sweep. Ensemble."**

```
1. Expose the knob       → make the solver setting a parameter
2. Scenario test         → sweep it; find the best AND the broken
3. Ensemble              → because no single config is safe on every input
```

MCP server accelerates every step — minutes of clicking become a conversation. And it's solver-agnostic: the same three steps wrap OR-Tools, Nextroute, or Xpress.

### Talk track

> Three steps, three features. Expose the setting, sweep it to find the winner *and* the landmines, and ensemble it because no single config is safe on every input. This is OR-Tools today, but it's the same workflow for any solver — including the ones in this room post-acquisition. Bring your solver; Nextmv helps you prove which configuration wins on *your* inputs and operate it safely.

---

## Slide 11 — Getting Started (30 sec)

- Nextmv is free to start; MCP server available now
- The OR-Tools routing app is in the community marketplace (`nextmv community clone -a python-ortools-routing`)
- Docs + contact links

---

## Slide 12 — Q&A (~3 min)

---

## Timing Summary

| Segment | Min | Type |
|---|---|---|
| Title | 0.5 | Slide |
| What is Nextmv? | 2 | Slide |
| The problem | 2 | Slide |
| The knobs | 1.5 | Slide |
| Guess-and-check vs workflow | 1.5 | Slide |
| MCP intro | 1.5 | Slide |
| Demo: baseline + sweep build strategy | 4 | Live (MCP) |
| Demo: metaheuristic × budget | 3 | Live (MCP) |
| Can you hard-code one strategy? (feasibility grid) | 2.5 | Slide |
| Ensembles concept | 2 | Slide |
| Demo: ensemble | 3 | Live (MCP) |
| Full workflow recap | 1.5 | Slide |
| Getting started | 0.5 | Slide |
| **Q&A** | **~4.5** | |
| **Total** | **~30** | |

---

## Reference: the demo app

**App:** `ortools-routing/` (cloned from `python-ortools-routing`, modified)

**Exposed options (`first_solution_strategy`, `local_search_metaheuristic`, `duration`, `log_search`):**

| Option | Default | Notes |
|--------|---------|-------|
| `first_solution_strategy` | AUTOMATIC | 10 choices; AUTOMATIC picks its own constructor (≠ PATH_CHEAPEST_ARC on this input: 31,242 vs 31,463) |
| `local_search_metaheuristic` | AUTOMATIC | 6 choices; GLS pulls ahead as the time budget grows |
| `duration` | 30 | solve-time budget (s) |
| `log_search` | false | stream OR-Tools search progress |

**Metrics:** the app emits both a flat `metrics` dict (read by scenario tests) — `objective_value`, `solution_found`, `activated_vehicles`, `max_route_duration`, `max_stops_in_vehicle`, `min_stops_in_vehicle`, plus the chosen strategies echoed back — **and** a canonical `statistics` object where `result.value` = objective when feasible, a large sentinel (1e12) when not, and `result.custom.feasible` = 1.0/0.0. The **ensemble rule** (JSONPath **`$.result.value`**, `$.` prefix required) reads this canonical objective — so a no-solution config reporting the sentinel can never win the ensemble.

**Input suite (`ortools-routing/inputs/`):** the demo uses `input.json` (the 150/10 tuning input for Parts 1–3) plus four **feasibility-stress** inputs for Slide 8 + the ensemble:

| Input | Shape | Why it's here |
|---|---|---|
| `metro-tight` | 150 stops / 8 veh, 1.12h shift cap | only **1 of 8** strategies feasible (SAVINGS) |
| `suburb-tight` | 150 / 8, 1.12h, seed 7 | only 2 feasible (PATH_MOST_CONSTRAINED, SAVINGS) |
| `metro-normal` | 150 / 8, 1.5h shift | a "normal" input — 6 feasible |
| `regional-big` | 300 / 16, loose time | SAVINGS **fails**; 5 feasible |

The stress comes from the per-vehicle **duration cap** (`max_hours` ≈ 1.1–1.2h) binding — *not* capacity, which leaves the robust constructors feasible. `explore_feasibility.py` is the harness that found this regime.

**Reproduce locally:**
```bash
cd ortools-routing
python generate_input.py --stops 150 --vehicles 10 > input.json   # default tuning input
python sweep.py 5                  # first-solution + metaheuristic sweeps
python explore_feasibility.py 5    # the feasibility-stress matrix (Slide 8 regime)
```

### Live cloud resources (already provisioned — profile `default`, api.cloud.nextmv.io)

| Resource | ID | Notes |
|---|---|---|
| App | `ortools-routing` | "OR-Tools Routing (Tuning Demo)" |
| Version | `version-ui7q5ohd` | v1.2 — emits `statistics` for ensembling; echoes strategy on no-solution runs |
| Instance (stock) | `default` | AUTOMATIC, 5s |
| Instance (tuned) | `tuned` | GLOBAL_CHEAPEST_ARC + GLS, 5s |
| Input set (tuning) | `tuning-input` | the 150/10 `input.json` |
| Input set (stress) | `stress-suite` | the four feasibility-stress inputs |
| Managed inputs | `metro-tight`, `suburb-tight`, `metro-normal`, `regional-big` | warm inputs for Slide 8 + ensemble |
| Scenario test | `sweep-first-solution` | Demo Part 1 (8 runs) |
| Scenario test | `metaheuristic-budget` | Demo Part 2 (12 runs) |
| Scenario test | `stress-matrix` | Slide 8 feasibility grid (32 runs) |
| Ensemble | `best-feasible-route` | 5-strategy portfolio, rule `minimize $.result.value` |
| Acceptance test | `feasible-and-better` | tuned ≤ default → PASS — *still provisioned in cloud, but cut from the talk flow; open only if Q&A asks* |

> All scenario/ensemble results are cached in Console — present from them if the network misbehaves on the day.

**Honest caveats (for Q&A):**
- The demo's center of gravity is **feasibility/robustness**, not objective gains. Among *feasible* strategies the objective margins are modest (~0.5–4%); the undeniable story is that on the stress inputs no single strategy returns a route everywhere, so the ensemble is the only safe ship.
- **The stress inputs are deliberately engineered** near the feasibility edge (per-vehicle shift cap ≈ 1.1–1.2h). That's honest to say out loud — it's the regime where ops teams actually live (tight shifts, full trucks), and it's *constructed* to be tight, not cherry-picked from random data. If asked "did you rig it?": yes, we dialed the shift length to the edge on purpose — that's what makes the constructor choice decide feasibility.
- **Feasibility at a 5s budget can flip run-to-run** for a borderline strategy, and GLS objectives wobble ±a few tenths of a percent (e.g. ensemble returned SAVINGS 30,505 on metro-tight vs 30,574 in the matrix sweep — same strategy, different run). The *pattern* (who's feasible vs not) is stable; exact objectives are not to the digit.
- The single cleanest deterministic tuning number is still the Part-1 **build strategy: 30,230 vs 31,463 default, ~3.9%**. The metaheuristic×budget effect is smaller (~1.5% over 30s) — tell it as "the right metaheuristic depends on your latency budget," not as a headline percentage.
- `GLOBAL_CHEAPEST_ARC` and `LOCAL_CHEAPEST_ARC` are chronic failures on capacitated VRP — fine as "landmines" in the sweep, which is why they're **not** ensemble members.
