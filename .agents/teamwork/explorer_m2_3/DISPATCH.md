# Task Assignment: Explorer 3 (Unit Test Suite Architecture & Tolerances)

## Working Directory
c:\Users\Asif\Downloads\Punjab Air Quality

## State Folder
c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\explorer_m2_3

## Objective
Design the automated unit test suite in `tests/unit/` for Milestone 2 covering:
1. Normalizer test cases for all 5 schema traps:
   - Centroid inversion verification ([lon, lat] vs [lat, lon]).
   - Aerodrome null vs calm distinction.
   - Station 172 blacklist enforcement and warning reason.
   - Dynamic station counts matching baseline expectations (74 fixed, 5 mobile).
   - Unified `is_estimated` flag mapping.
2. Math Transforms T1–T11 unit tests:
   - Numerical tolerance tests ($\epsilon = 10^{-5}$) using reference test vectors from `docs/TRANSFORMATION_LOGIC_SPEC.md` and Python implementations.
   - Singularity clamp testing ($d_0 = 5.0$ km).
   - Wind speed clamp ($0 \le w_s \le 30$ m/s) and Cartesian vector signs ($u = -w_s\sin\theta, v = -w_s\cos\theta$).
   - CPF small-sample suppression ($N_k < 6$) and calm exclusion.
   - Advection flux dimension guard (locking to PM2.5 on AQI).
   - Transboundary chevron threshold testing ($>+0.25$ m/s, $<-0.25$ m/s).
   - PEPC AQI breakpoints, 500 ceiling clamp for PM2.5 > 350 $\mu\text{g/m}^3$, composite AQI logic.
   - QC filters (7h spike, 3h logger hold with $i \ge 2$ index guard and AQI exemption, 75% rule, sub-hourly lerp).
   - Equirectangular projection and greedy AABB collision offset testing.
3. Test framework setup:
   - Inspect package.json and determine test runner (e.g. `npm test` / vitest / tsx).

## Files to Inspect
- `c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\ORIGINAL_REQUEST.md` (MUST read first)
- `c:\Users\Asif\Downloads\Punjab Air Quality\PROJECT.md`
- `c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\sub_orch_m2\SCOPE.md`
- `c:\Users\Asif\Downloads\Punjab Air Quality\docs\TRANSFORMATION_LOGIC_SPEC.md`
- `c:\Users\Asif\Downloads\Punjab Air Quality\package.json`
- `c:\Users\Asif\Downloads\Punjab Air Quality\tests/`

## Output Requirements
Produce a comprehensive handoff report at `c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\explorer_m2_3\handoff.md` detailing:
- Recommended test directory structure and test file naming in `tests/unit/`.
- Test runner invocation command and configuration needed in package.json.
- Concrete test cases with input values, expected outputs, and numerical tolerance assertions for every transform and schema trap.


## 2026-11-11T14:00:15Z
You are Explorer 3 for Milestone 2: Domain Physics, Normalizer & Schema Trap Engine.
Working directory: c:\Users\Asif\Downloads\Punjab Air Quality
State folder: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\explorer_m2_3

Your task assignment is in:
c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\explorer_m2_3\DISPATCH.md

MANDATORY: You MUST read the authoritative user request first at:
c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\ORIGINAL_REQUEST.md
Also read:
- c:\Users\Asif\Downloads\Punjab Air Quality\PROJECT.md
- c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\sub_orch_m2\SCOPE.md
- c:\Users\Asif\Downloads\Punjab Air Quality\docs\TRANSFORMATION_LOGIC_SPEC.md
- c:\Users\Asif\Downloads\Punjab Air Quality\package.json
- c:\Users\Asif\Downloads\Punjab Air Quality\tests/

Investigate and design the automated unit test suite in `tests/unit/` for Milestone 2:
1. Normalizer test cases for all 5 schema traps.
2. Math Transforms T1-T11 unit tests with numerical tolerances (epsilon = 10^-5) against reference test vectors from spec and Python tests.
3. Edge case tests (calm cutoff, 500 ceiling clamp, singularity clamp d0 = 5.0 km, physical dimension guard locking to PM2.5 on AQI, Wazirabad blacklist, small-sample suppression Nk < 6).
4. Recommended test runner configuration in package.json (vitest / tsx) and execution commands.

Write your final structured report to:
c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\explorer_m2_3\handoff.md
Update progress.md as you work. When complete, send a message to your parent orchestrator with your report location.


## 2026-11-11T21:43:55Z
**Context**: Milestone 2 Exploration Phase
**Content**: Checking in on your exploration progress. Explorer 2 has completed its report.
**Action**: Please update progress.md and let me know your current status and estimated time to handoff.md.
