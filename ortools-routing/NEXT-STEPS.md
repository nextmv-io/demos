# Next steps — OR-Tools routing talk (incident narrative)

_Picked up: Monday 2026-06-22. Paused: Fri 2026-06-19._

## Where we landed
- Talk rewritten as a **2-presenter production-incident** story (Tiff = builder, Haley = operator) in `talk-outline.md`. Old "tuning showcase" version backed up in `talk-outline-v1-tuning.md`.
- **Casting locked (real stress-matrix data):**
  - `production` = AUTOMATIC (fails on tight days)
  - Act-2 patch = **PATH_MOST_CONSTRAINED_ARC** → promoted to `staging`
  - relapse input = **metro-tight** (PMC fails there)
  - ensemble savior = **SAVINGS** (the strategy Tiff rejected in Act 2 because it failed on regional-big) ← the narrative irony
- App is deployed: `ortools-routing`, version **`version-ui7q5ohd` (v1.2)** — v1.2 echoes the chosen strategy in metrics even on no-solution runs.

## DONE (built Fri 2026-06-19 via MCP, profile `default`)
1. ✅ **Instance `production`** — AUTOMATIC/AUTOMATIC, 5s, v1.2.
2. ✅ **Instance `staging`** — PATH_MOST_CONSTRAINED_ARC + GLS, 5s, v1.2.
3. ✅ **Input set `incident-sample`** = {suburb-tight, metro-normal, regional-big}.
4. ✅ **Scenario test `diagnose-sample`** — 24 runs, completed. Confirmed PMC is the **only** strategy feasible on all 3; SAVINGS fails on regional-big (the Act-2 rejection). Fresh numbers synced into `talk-outline.md` Act-2 table.
5. ✅ **Cached run** `production-29ytZB-vR` — production (AUTOMATIC) on suburb-tight → no route.
6. ✅ **Cached run** `staging-CuN2ZB-Dg` — staging (PMC) on metro-tight → no route; metrics tab names `PATH_MOST_CONSTRAINED_ARC`.

7. ✅ **`stress-matrix` rebuilt** (Mon 2026-06-22) — same 8 strategies as `diagnose-sample` over `stress-suite` (4 inputs incl. metro-tight), 32 runs, completed. Real grid: metro-tight 1/8 (only SAVINGS 30,833), suburb 2/8, normal 6/8, regional 5/8; PMC fails metro-tight; SAVINGS fails regional-big. Outline Act-4 grid synced to real numbers.
8. ✅ **Ensemble runs on v1.2** for all 4 inputs (cached): metro-tight→SAVINGS 30,833 (`latest-3__yx_-DR`), suburb-tight→PMC 29,234 (`latest-ewJlbl-DR`), metro-normal→PARALLEL 30,288 (`latest-BrWXb_-Dg`), regional-big→PMC 57,188 (`latest-qRsux_-Dg`). Outline Act-5 table synced.

_Reused: managed inputs, `stress-suite`, `best-feasible-route` ensemble._

**→ Cloud provisioning for the core demo (Acts 1–5) is now COMPLETE.** Remaining work is verification, the stretch tour, cleanup, and wordsmithing (below).

## VERIFIED
9. ✅ **Two-field payload claim** (Act 5) — confirmed against Nextmv docs (*Runs ensembling*): ensemble runs hit the **same endpoint** as a normal run (`POST /v1/applications/{app}/runs`); you add a `configuration.run_type` block (`type: "ensemble"` + `definition_id`). Same input, same instance, no redeploy. Outline snippet corrected; VERIFY flag removed.

## TOUR D'ENSEMBLE (stretch / if time) — all TO BUILD in the account
9. Clone from marketplace/community + deploy: **Nextroute**, **Hexaly**, **AMPL pricing**. Create one ensemble def per app; make one **multi-rule** (e.g. pricing: rule 0 `maximize revenue`, rule 1 tiebreak `minimize runtime` within tolerance). Confirm **Hexaly license** before showing live.

## OPTIONAL CLEANUP
10. Leftover v1 resources still on cloud, now cut from the talk: instances `default`/`tuned`, scenario tests `sweep-first-solution` & `metaheuristic-budget`, acceptance test `feasible-and-better`. Harmless — ignore or delete for tidiness.

## STILL OPEN / TO DISCUSS
- Wordsmith the Tiff/Haley back-and-forth (script is drafted, not polished).
- Decide whether to commit these changes (currently uncommitted; `ortools-routing/` is untracked).
