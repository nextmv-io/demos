# Ship Better Routes: Debugging a Solver in Production with Nextmv

> **Two-presenter, incident-driven version.** Tiff = model builder. Haley = operator
> (dispatcher). The talk is a live production incident: routes stop coming back, we
> diagnose it with scenario tests, the first fix relapses, and an ensemble is the
> thing that actually holds. Previous "tuning showcase" version preserved in
> `talk-outline-v1-tuning.md`.

---

## TL;DR — the whole talk on one screen

**One-liner:** some days, production returned **no route at all** — and no single solver setting fixes it. This is how you diagnose that with Nextmv and ship a fix that actually holds: an **ensemble**.

**The app:** a delivery route planner on **OR-Tools** (its routing engine). Depot + vehicles + stops → cheapest valid routes. **Nextmv** is the platform around it: run it, test it, operate it — solver-agnostic.

**The cast:**
- **Tiff** — model builder. Runs scenario tests, builds the ensemble, owns the production endpoint.
- **Haley** — operator / dispatcher. Hits the failures, escalates, verifies the fix in staging.

**The incident, in five acts:**
1. **The pain** — for a few days, some inputs come back with **no route**. (prod = `AUTOMATIC`)
2. **First fix** — Tiff scenario-tests a subset, finds `PATH_MOST_CONSTRAINED_ARC` gets routes everywhere in the sample → **promotes it to `staging`** for Haley.
3. **Relapse** — days later Haley runs a tighter input (`metro-tight`) → **no route again**. The patch didn't generalize.
4. **Real diagnosis** — Tiff clones the scenario test, **adds the bad input**, re-runs → the grid shows **no single strategy is feasible on every input.** You can't hard-code one.
5. **The fix that holds** — Tiff stands up an **ensemble** (run several, return the best route that came back) → run it on `metro-tight` → **a route.** Shipping it to prod is a **two-field payload change**.

**The twist that sells it:** the strategy Tiff *rejected* in Act 2 (`SAVINGS` — it failed on `regional-big`) is the **only** one that works on `metro-tight`. Neither is safe alone; the ensemble covers both.

**Mantra:** **Expose the knob → Scenario-test to diagnose → Ensemble to cover.**

---

## The two levers (Tiff's diagnosis toolkit — explain once, early)

When OR-Tools "solves," it does two things: **(1) BUILD** a first rough set of routes, then **(2) IMPROVE** them until time runs out. The community app hard-codes both to `AUTOMATIC`; we exposed them as options.

- **Build lever — `first_solution_strategy`:** the *construction recipe* for the first routes (`PATH_CHEAPEST_ARC`, `PATH_MOST_CONSTRAINED_ARC`, `GLOBAL_CHEAPEST_ARC`, `SAVINGS`, …). These are greedy with no backtracking, so on a tightly-constrained input a bad recipe can **paint itself into a corner and return no route at all.** *This is the lever the whole incident turns on.* (Not a warm start — it builds from scratch; a warm start hands in a prior solution.)
- **Improve lever — `local_search_metaheuristic`:** how it improves the draft (`GUIDED_LOCAL_SEARCH` keeps climbing given time; `GREEDY_DESCENT` gets stuck). Plus `duration` = time budget. *Secondary in this talk — mention in passing.*

> The key fact for the story: **the build lever decides whether you get a route at all**, and the right choice changes with the input.

---

## Slide 1 — Cold open (Haley) (1 min)

**Haley, deadpan:** *"Three Tuesdays ago, a batch of route requests came back empty. No routes. Dispatchers had nothing to hand drivers. Same model, same code that worked Monday."*

**Tiff:** *"And nothing had changed on our side. So — what do you do when the solver just… returns nothing?"*

> Sets the stakes before any product pitch. The room (ops + model builders) has lived this.

---

## Slide 2 — What is Nextmv? (Tiff) (2 min)

**"DevOps, but for optimization models — whatever solver is underneath."**

- Build a model (routing, scheduling, pricing) on the solver of your choice — OR-Tools, Nextroute, HiGHS, Gurobi, **FICO Xpress** — deploy to Nextmv Cloud, get a layer to test and operate it.
- Three features we'll use today:

| Feature | What it does |
|---------|--------------|
| **Runs** | Execute the model with different settings — no code changes |
| **Scenario tests** | Sweep many configurations against the same input(s) in one shot |
| **Ensemble definitions** | Run multiple configs in parallel, return the best result per request |

- Plus the **MCP server** — Tiff drives all of it from an AI assistant in plain English, live.

### Talk track
> Everything you're about to watch me do — run the model, sweep settings, build an ensemble — I do by *talking* to the platform through the MCP server. No clicking through forms. That's what makes debugging this live actually feasible.

---

## Slide 3 — Why would a route just not come back? (Tiff) (2 min)

Use the **two-levers** explainer above. Land one point hard:

> A solver doesn't just "solve" — first it *builds* a rough route, then it *improves* it. The **build** step is a greedy recipe, and the stock app hard-codes it to `AUTOMATIC`. On a tight day — short shifts, full trucks — that recipe can build itself into a dead end and hand back **nothing**. The fix isn't more compute. It's *which recipe* — and that's a setting nobody ever exposed.

→ "So let's expose it and go find the bad days."

---

## Slide 4 — Section divider: **"Let's debug it live."**

---

## Demo Operations — Prep vs. Live (READ BEFORE PRESENTING)

> Golden rule: **all heavy compute is pre-built.** On stage you trigger a few ~5s
> runs for drama (a "no route" and a "route") and *open* already-computed scenario
> tests. Everything below is real and cached in the Console.

### ✅ BEFORE the talk — pre-flight (build/verify these)

| # | Item | Identifier | Status |
|---|------|-----------|--------|
| 1 | App deployed | `ortools-routing`, version `version-ui7q5ohd` (v1.2) | ✅ |
| 2 | Instance — **production** (failing stock config) | `production` (AUTOMATIC, 5s) | ✅ |
| 3 | Instance — **staging** (Act-2 patch) | `staging` (PATH_MOST_CONSTRAINED_ARC + GLS, 5s) | ✅ |
| 4 | Managed inputs | `metro-tight`, `suburb-tight`, `metro-normal`, `regional-big` | ✅ |
| 5 | Input set — **Act-2 sample** (the days Tiff investigated) | `incident-sample` = {suburb-tight, metro-normal, regional-big} | ✅ |
| 6 | Input set — full suite (Act-4 grid) | `stress-suite` (4 inputs) | ✅ |
| 7 | Scenario test — **Act-2 sweep** (find a patch on the sample) | `diagnose-sample` (8 strategies × 3 inputs = 24 runs) | ✅ |
| 8 | Scenario test — **Act-4 grid** (clone + add metro-tight) | `stress-matrix` (8 × 4 = 32 runs) | ✅ |
| 9 | Ensemble definition (5-strategy portfolio, 1 rule) | `best-feasible-route` | ✅ |
| 10 | Cached run — prod fails on the sample | `production` on `suburb-tight` → no route (`production-29ytZB-vR`) | ✅ |
| 11 | Cached run — **staging patch relapses** | `staging` on `metro-tight` → no route (`staging-CuN2ZB-Dg`) | ✅ |
| 12 | Cached run — **ensemble saves it** | ensemble on `metro-tight` → SAVINGS, 30,833 (`latest-3__yx_-DR`) | ✅ |

> ✅ **`stress-matrix` rebuilt** to sweep the same 8 strategies as `diagnose-sample` over
> `stress-suite` (the 3 sample inputs **+ `metro-tight`**) = 32 runs. The Act-4 grid
> below reflects the real rebuilt numbers; PMC (staging) correctly fails on metro-tight,
> and SAVINGS is the lone survivor there.
| 12 | Cached run — **ensemble saves it** | ensemble on `metro-tight` → SAVINGS, ~30,500 | ✅ (re-run on v1.2) |

**Also:** open the Console to `ortools-routing`; have tabs ready for the **Runs** view, the two **Scenario tests** (`diagnose-sample`, `stress-matrix`), and the **Ensemble**. Confirm `claude mcp list` shows `nextmv` Connected. Do one throwaway warm-up run before doors open.

### 🎤 LIVE on stage — only these

| Act | Live action (≈time) | Backed by |
|---|---|---|
| 2 — first fix | open `diagnose-sample` scenario test (pre-built); promote PMC → `staging` (1 instance update) | items 7, 3 |
| 3 — relapse | **Haley runs `staging` on `metro-tight` → no route** (~5s) | item 11 |
| 4 — diagnosis | open `stress-matrix` grid (pre-built) | item 8 |
| 5 — fix | **Tiff runs ensemble on `metro-tight` → route** (~5s); open the 3 pre-computed | items 9, 12 |

> If the network is flaky: every number is cached — present entirely from pre-built and skip the live triggers.

---

## ACT 1 — Reproduce the pain (Tiff + Haley) (2 min)

**Haley:** *"Here's one of the inputs that failed — a tight-shift day."* (`suburb-tight`)
**Tiff (🎤 LIVE ~5s):** *"Run it on production."* → **`solution_found: false`. No route.**

| Run | Result |
|---|---|
| `production` (AUTOMATIC) on `suburb-tight` | **NO ROUTE** |

### Talk track
> First rule of debugging: reproduce it. There's the failure, live — production config, real input, nothing comes back. Not a crash, not a timeout. The solver's build step gave up. Now I have something to test against.

---

## ACT 2 — First fix: scenario-test the sample, promote to staging (Tiff) (4 min)

**Tiff:** *"I don't trust one input. Let me grab the last few problem days and sweep every build strategy across all of them at once."*

**✅ PRE-BUILT — open `diagnose-sample`** (sweep `first_solution_strategy` across 8, held GLS/5s, over the 3-input sample `incident-sample`). **`X` = no route:**

```
strategy                     suburb-tight  metro-normal  regional-big   feasible on all 3?
AUTOMATIC (prod)                  X           30,384       57,266              no
PATH_CHEAPEST_ARC                 X           30,384       57,266              no
PATH_MOST_CONSTRAINED_ARC      29,234        30,539        57,188            ✅ YES
SAVINGS                        29,578        30,787          X                no  (fails regional)
PARALLEL_CHEAPEST_INSERTION       X           30,288       57,597              no
GLOBAL_CHEAPEST_ARC               X             X             X               no
LOCAL_CHEAPEST_ARC                X             X             X               no
LOCAL_CHEAPEST_INSERTION          X           31,067       62,270             no
```

**Result:** exactly one strategy — **`PATH_MOST_CONSTRAINED_ARC`** — returns a route on *all three* sample inputs.

**Tiff (🎤 LIVE):** *"Promote that to staging."* → update the `staging` instance's `first_solution_strategy` to `PATH_MOST_CONSTRAINED_ARC` (one call; no redeploy).
**Haley:** *"Great — I'll run my dailies against staging."*

### Talk track
> One scenario test, 24 runs, one answer: path-most-constrained is the only build recipe that gets a route on every bad day in my sample. I promote *just that config* to a staging instance — same code, different setting — and hand it to Haley to run against. Notice what I rejected: Savings failed on the big regional input, so it's out. Remember that.

> ⚠️ **Foreshadow:** "feasible on the sample" ≠ "feasible on every future input."

---

## ACT 3 — The relapse (Haley → Tiff) (2 min)

**Haley:** *"Worked great for a couple days. Then this morning —"* (`metro-tight`, an even tighter day)
**Haley (🎤 LIVE ~5s):** *"Run it on staging."* → **`solution_found: false`. No route.** (cached `staging` on `metro-tight`)

**Haley:** *"Tiff. It's back."*

| Run | Result |
|---|---|
| `staging` (PATH_MOST_CONSTRAINED_ARC) on `metro-tight` | **NO ROUTE** |

### Talk track
> The patch that fixed last week is empty-handed this week. The metrics tab even names the culprit — `first_solution_strategy: PATH_MOST_CONSTRAINED_ARC` → no solution. We didn't regress; we just hit an input our sample never covered. This is the trap: you tune to the data you have.

---

## ACT 4 — Real diagnosis: clone the test, add the bad input (Tiff) (3 min)

**Tiff:** *"Okay. Same scenario test — but I'll clone it and drop `metro-tight` into the input set, so we see every strategy against every input, including this one."*

**✅ PRE-BUILT — open `stress-matrix`** (the clone: 8 strategies × all 4 inputs, GLS/5s). **`X` = no route:**

```
strategy                     metro-tight  suburb-tight  metro-normal  regional-big
AUTOMATIC (prod)                  X            X          30,384       57,298
PATH_MOST_CONSTRAINED (staging)   X         29,079        30,539       57,188
SAVINGS                        30,833       29,606        30,787         X
PARALLEL_CHEAPEST_INSERTION       X            X          30,290       57,516
GLOBAL_CHEAPEST_ARC               X            X             X            X
… (others all X on metro-tight)
─────────────────────────────────────────────────────────────────────────
feasible strategies / 8           1            2             6            5
```

Three things to point at:
1. **On `metro-tight`, 7 of 8 strategies return nothing** — only `SAVINGS` finds a route.
2. **`SAVINGS` is the one I threw out in Act 2** (it failed on regional-big) — yet it's the *only* survivor here.
3. **No row is green all the way across.** Whatever single setting you pick, some input breaks it.

### Talk track
> Cloning a scenario test and swapping the input set is two clicks — or one sentence to the assistant. And now the picture is undeniable. On today's input, seven of eight strategies come back empty; the lone survivor is Savings — the exact one I rejected last week. And look down any column: there's no setting that's green everywhere. You cannot hard-code your way out of this. So stop trying to pick one.

---

## Slide 5 — Ensembles: don't pick one, run several (Tiff) (2 min)

**"Run a handful of strong configs in parallel; return the best route that actually came back."**

- **Robustness (the point):** at least one member returns a feasible route, even when others choke.
- **Best-per-input:** you capture the winner without predicting which strategy it'll be.
- **One rule:** *minimize objective.* Infeasible members report a huge **sentinel** cost, so "feasible first, then cheapest" falls out of a single `minimize $.result.value` rule — no separate feasibility check.

### Talk track
> An ensemble runs several configs at once and returns the best one that worked. You're not betting on a strategy surviving tomorrow's input — you're hedging. And because a config that finds nothing reports an impossibly high cost, one rule — lowest cost wins — quietly means "feasible first, then cheapest."

---

## ACT 5 — The fix that holds (Tiff + Haley) (3 min)

**Tiff:** *"Five strong build strategies, one rule. Run it on the input that just failed."*

**🎤 LIVE (~5–10s):** *"Run the `best-feasible-route` ensemble on `metro-tight`."* → **a route. `SAVINGS`, ~30,800.** Then open the 3 pre-computed runs:

| Input | Ensemble returns | Why it matters |
|---|---|---|
| metro-tight | SAVINGS → **30,833** | 7 of 8 strategies returned nothing — still ships a route |
| suburb-tight | PATH_MOST_CONSTRAINED → **29,234** | AUTOMATIC & PARALLEL failed here |
| metro-normal | PARALLEL_CHEAPEST_INSERTION → **30,288** | normal day — best of six survivors |
| regional-big | PATH_MOST_CONSTRAINED → **57,188** | SAVINGS failed here |

> Four inputs, four ensemble runs, **a different winning strategy almost every time**
> (SAVINGS, PMC, PARALLEL, PMC). Cached runs: `latest-3__yx_-DR` (metro-tight),
> `latest-ewJlbl-DR` (suburb-tight), `latest-BrWXb_-Dg` (metro-normal),
> `latest-qRsux_-Dg` (regional-big).

**Haley:** *"So whatever comes in tomorrow —"*
**Tiff:** *"— it runs five strategies and hands you the best one that came home. You stop predicting."*

### Then: ship it (the operational punch)

**Tiff:** *"And rolling this into production isn't a redeploy. Your caller adds two fields."*

```diff
  POST https://api.cloud.nextmv.io/v1/applications/ortools-routing/runs
  {
    "instance_id": "production",
    "input": { ...same stops and vehicles... }
+   ,"configuration": {
+     "run_type": { "type": "ensemble", "definition_id": "best-feasible-route" }
+   }
  }
```

> ✅ **Verified** (Nextmv docs — *Runs ensembling*): the ensemble run hits the **same
> endpoint** as a normal run (`POST /v1/applications/{app}/runs`); you only add the
> `configuration.run_type` block (`type: "ensemble"` + `definition_id`). Same input,
> same instance, no redeploy. The "add a couple of fields" claim is accurate.

### Talk track
> Same input that returned nothing five minutes ago — now it returns a route, via Savings, the strategy I'd written off. Four inputs, and the ensemble picks a *different* winner almost every time. And shipping it is a two-field change to the request your production system already makes — no model change, no redeploy. That's the whole arc: reproduce it, diagnose it with a scenario test, cover it with an ensemble.

---

## Slide 6 — Tour d'ensemble (if time) (2–3 min)

**"Same pattern, any solver — and more than one rule."**

- The ensemble idea isn't OR-Tools-specific. The same "run several, pick the best by rules" wraps **Nextroute**, **Hexaly**, an **AMPL pricing** model — different solving tech, identical operational move.
- **Multi-rule** case (where this demo only used one rule): rules are evaluated in order with tolerances. Example for a pricing model:
  1. `maximize $.result.revenue`
  2. tiebreak: `minimize $.result.runtime` within a tolerance of rule 1
  — i.e. "highest revenue, and among near-ties, the fastest."

> ⬜ **TO BUILD:** clone Nextroute / Hexaly / AMPL-pricing from the marketplace/community
> apps into the account, deploy, and create one ensemble def each (one of them
> multi-rule). Until then this is a conceptual slide. *(Hexaly is commercial — confirm
> license before showing live.)*

### Talk track
> This wasn't a routing trick. Bring Nextroute, Hexaly, an AMPL pricing model — the ensemble is the same operational pattern, and the rules can stack: feasible first, then cheapest, then fastest. One platform move over whatever solver you've got.

---

## Slide 7 — The workflow (Tiff) (1.5 min)

**"Expose → Scenario-test to diagnose → Ensemble to cover."**

```
1. Expose the knob   → make the solver setting a parameter (so you can test it at all)
2. Scenario test     → reproduce the failure; sweep configs across the inputs that bite
3. Ensemble          → cover every input by running several and returning the best feasible
```

MCP server makes each step a sentence, not an afternoon. Solver-agnostic: the same three steps wrap OR-Tools, Nextroute, Hexaly, or Xpress.

### Talk track
> Three steps. Expose the setting so the platform can test it. Scenario-test to reproduce and diagnose — and watch a single config never be enough. Then ensemble to cover. OR-Tools today; same workflow for any solver in this room.

---

## Slide 8 — Getting started (30 sec)

- Nextmv is free to start; MCP server available now.
- The OR-Tools routing app is in the community marketplace (`nextmv community clone -a python-ortools-routing`).
- Docs + contact links.

---

## Slide 9 — Q&A (~3 min)

---

## Timing Summary

| Segment | Min | Type |
|---|---|---|
| Cold open (Haley) | 1 | Slide |
| What is Nextmv? | 2 | Slide |
| Why would a route not come back? (levers) | 2 | Slide |
| Act 1 — reproduce the pain | 2 | Live |
| Act 2 — first fix → staging | 4 | Live + scenario test |
| Act 3 — relapse | 2 | Live |
| Act 4 — diagnosis (grid) | 3 | Live (open pre-built) |
| Ensembles concept | 2 | Slide |
| Act 5 — fix that holds + ship it | 3 | Live |
| Tour d'ensemble (if time) | 2–3 | Slide |
| Workflow recap | 1.5 | Slide |
| Getting started | 0.5 | Slide |
| **Q&A** | **~2.5** | |
| **Total** | **~28–30** | |

---

## Reference: the demo app

**App:** `ortools-routing/` (cloned from `python-ortools-routing`, modified to expose the search strategy as options).

**Exposed options:**

| Option | Default | Notes |
|--------|---------|-------|
| `first_solution_strategy` | AUTOMATIC | the **build** lever; 10 choices; decides feasibility on tight inputs |
| `local_search_metaheuristic` | AUTOMATIC | the **improve** lever; 6 choices; GLS pulls ahead with more time |
| `duration` | 30 | solve-time budget (s) |
| `log_search` | false | stream OR-Tools search progress |

**Metrics:** the app emits a flat `metrics` dict (read by scenario tests) — `objective_value`, `solution_found`, `activated_vehicles`, plus the chosen strategies echoed back **even on no-solution runs** (v1.2) — and a canonical `statistics` object where `result.value` = objective when feasible, a large sentinel (1e12) when not, and `result.custom.feasible` = 1.0/0.0. The **ensemble rule** reads `$.result.value` (the `$.` prefix is required), so a no-solution config reporting the sentinel can never win.

**Input suite (`ortools-routing/inputs/`):**

| Input | Shape | Role in the story |
|---|---|---|
| `suburb-tight` | 150 / 8, 1.12h, seed 7 | Act-1 reproduce; feasible for PMC & SAVINGS |
| `metro-normal` | 150 / 8, 1.5h shift | "normal" day; 6 of 8 feasible |
| `regional-big` | 300 / 16, loose time | in the sample; **SAVINGS fails here** (why Tiff rejects it) |
| `metro-tight` | 150 / 8, 1.12h shift cap | the **relapse** input; only SAVINGS feasible (1 of 8) |

The stress comes from the per-vehicle **duration cap** (~1.1–1.2h shift) binding — not capacity. `explore_feasibility.py` found this regime.

**Reproduce locally:**
```bash
cd ortools-routing
python generate_input.py --stops 150 --vehicles 10 > input.json
python sweep.py 5
python explore_feasibility.py 5   # the feasibility-stress matrix
```

### Live cloud resources (profile `default` = personal/tiff account, api.cloud.nextmv.io)

| Resource | ID | Status |
|---|---|---|
| App | `ortools-routing` | ✅ |
| Version | `version-ui7q5ohd` (v1.2) | ✅ echoes strategy on no-solution runs |
| Instance (prod) | `production` (AUTOMATIC, 5s) | ✅ |
| Instance (staging) | `staging` (PATH_MOST_CONSTRAINED_ARC + GLS, 5s) | ✅ |
| Managed inputs | `metro-tight`, `suburb-tight`, `metro-normal`, `regional-big` | ✅ |
| Input set | `incident-sample` {suburb-tight, metro-normal, regional-big} | ✅ |
| Input set | `stress-suite` (4 inputs) | ✅ |
| Scenario test | `diagnose-sample` (Act 2; 24 runs) | ✅ |
| Scenario test | `stress-matrix` (Act 4; 32 runs) | ✅ rebuilt (8 strategies incl. PMC × 4 inputs) |
| Ensemble | `best-feasible-route` (5-strategy, rule `minimize $.result.value`) | ✅ |

> **Also still on cloud, but cut from this talk:** instances `default`/`tuned`, scenario
> tests `sweep-first-solution` & `metaheuristic-budget`, acceptance test
> `feasible-and-better` (from the v1 tuning version). Harmless; ignore or delete.

**Honest caveats (for Q&A):**
- **The stress inputs are deliberately engineered** near the feasibility edge (shift cap ≈ 1.1–1.2h). Say so: it's the regime ops teams actually live in (tight shifts, full trucks), constructed to be tight, not cherry-picked. "Did you rig it?" → yes, we dialed the shift to the edge on purpose; that's what makes the build recipe decide feasibility.
- **Feasibility at 5s can flip run-to-run** for a borderline strategy, and GLS objectives wobble ±a few tenths of a percent (SAVINGS returned 30,505 / 30,574 / 30,833 on metro-tight across runs — same strategy, different run). The *pattern* (who's feasible) is stable; exact objectives are not to the digit.
- The narrative's punch is **feasibility/robustness**, not cost. Among feasible strategies, objective margins are modest (~0.5–4%). The undeniable story is: no single strategy returns a route everywhere, so the ensemble is the only safe ship.
- `GLOBAL_CHEAPEST_ARC` / `LOCAL_CHEAPEST_ARC` are chronic failures on capacitated VRP — that's why they're **not** ensemble members.
