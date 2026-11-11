# Task Assignment: Scientific Transformation Specification Mining

You are the Scientific Transformation Spec Miner (`spec_miner_math`).
Your working directory is: `c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\spec_miner_math\`

## Authoritative User Request
You MUST read the authoritative user request at:
`c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\ORIGINAL_REQUEST.md`

## Objectives
1. Deeply investigate `docs/TRANSFORMATION_LOGIC_SPEC.md` and related mathematical specifications:
   - IDW (Inverse Distance Weighting) spatial interpolation (power parameter, distance metrics, search radius, min/max points, grid resolution, boundary handling).
   - CPF (Conditional Probability Function) polar roses (wind speed/direction bins, concentration thresholds, sector calculations, calm wind handling).
   - Pollutant flux calculations (advection velocity vectors, concentration gradients, box model/cross-sectional fluxes).
   - PEPC (Punjab Environmental Protection Council / Punjab EPA) breakpoint calculations (AQI categories, linear interpolation formula, pollutant index mappings for PM2.5, PM10, NO2, SO2, CO, O3).
2. Document for each algorithm:
   - Mathematical formulation and equations.
   - Precise input types, structures, and units.
   - Precise output types, structures, and units.
   - Edge cases, numerical stability guards (e.g. division by zero, calm winds, identical coords in IDW).
   - Expected test cases and reference fixtures.
3. Recommend clean architecture decoupling for pure function implementations.
4. Write your comprehensive findings to `handoff.md` in your working directory.
5. Send a message to the orchestrator when complete.

## 2026-11-10T12:41:58Z
You are the Scientific Transformation Spec Miner.
Working directory: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\spec_miner_math\
First read the instructions in c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\spec_miner_math\DISPATCH.md and c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\ORIGINAL_REQUEST.md.
Investigate docs/TRANSFORMATION_LOGIC_SPEC.md to extract all mathematical models (IDW, CPF polar rose, flux, PEPC breakpoints), equations, inputs/outputs, edge cases, and test fixtures.
Write your full report to handoff.md in your working directory and notify the orchestrator when done.
