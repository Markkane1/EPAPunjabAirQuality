# Task Assignment: E2E Testing Track — Test Infrastructure & Suite Design

You are `test_writer_e2e` (Type: `teamwork_test_writer`).
Your working directory is: `c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\test_writer_e2e\`

## Authoritative Specifications
You MUST read:
1. `c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\ORIGINAL_REQUEST.md`
2. `c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\orchestrator\PROJECT.md`
3. All specification files in `docs/`:
   - `docs/ARCHITECTURE_OVERVIEW.md`
   - `docs/DATA_SOURCES_AND_STREAMS.md`
   - `docs/TRANSFORMATION_LOGIC_SPEC.md`
   - `docs/DATA_PIPELINES_ARCHITECTURE.md`
   - `docs/SYSTEM_ARCHITECTURE.md`
   - `docs/UI_UX_SPECIFICATION.md`

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. Tests must be rigorous, requirement-driven, opaque-box, and independent of implementation design.

## File Ownership
You exclusively own:
- `TEST_INFRA.md` in the project root
- `tests/e2e/` directory (test harness, runners, and E2E test scenarios across Tiers 1–4)
- `tests/fixtures/` (sample CSV datasets, expected outputs)

Do NOT modify implementation source code in `src/`.

## Objectives
1. **Design Test Infrastructure (`TEST_INFRA.md`)**:
   - Create `TEST_INFRA.md` at project root using the standard template:
     - Test Philosophy (opaque-box, requirement-driven, Category-Partition + BVA + Pairwise + Workload Testing)
     - Feature Inventory mapping against Tiers 1, 2, 3
     - Test Architecture (runner commands, invocation, assertions)
     - Real-World Application Scenarios (Tier 4)
     - Coverage thresholds
2. **Build E2E Test Suite (Tiers 1–4)**:
   - **Tier 1 (Feature Coverage)**: Happy-path tests for each core feature in isolation (API contract tests, data ingestion validation, basic math calculations).
   - **Tier 2 (Boundary & Corner Cases)**: Extreme values ($le=5000$, calm winds $<0.5\text{ m/s}$, zero coordinates, Wazirabad blacklist, sensor freeze holding last value, 75% completeness cutoff).
   - **Tier 3 (Cross-Feature Combinations)**: Combinations (e.g., CSV upload triggering IDW recalculation, wind vector update recalculating CPF rose and advection flux, non-AQI vs AQI flux guard).
   - **Tier 4 (Real-World Application Scenarios)**: Realistic end-to-end user journeys:
     - Scenario 1: Severe Smog Inversion Episode (high PM2.5, transboundary transport plume, hazardous AQI).
     - Scenario 2: Offline Fallback & Graceful Degradation (EPA portal 404 falling back to baseline templates).
     - Scenario 3: Custom User CSV Upload & Dynamic Re-interpolation.
     - Scenario 4: Cross-Border Plume Inflow Analysis with CAMS / normal vector checks.
     - Scenario 5: Multi-Station District Disaggregation (Lahore 13 stations vs Attock single station).
3. **Automated Test Runner**:
   - Provide an executable test runner script: `python -m pytest tests/` or `python tests/e2e/run_all_tests.py` that can execute and report structured JSON / console summary.
4. **Publish TEST_READY.md**:
   - When the test suite and harness are fully implemented and verified, publish `TEST_READY.md` at the project root summarizing total counts per tier and runner command.
5. **Handoff**:
   - Document all test files created, execution commands, and tier coverage in `handoff.md`.
   - Send a message to the orchestrator when finished.

## 2026-11-10T12:53:29Z
You are test_writer_e2e.
Working directory: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\test_writer_e2e\
Read c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\test_writer_e2e\DISPATCH.md, c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\ORIGINAL_REQUEST.md, c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\orchestrator\PROJECT.md, and all specification files in docs/.

MANDATORY INTEGRITY WARNING: DO NOT CHEAT. All test implementations must be genuine, requirement-driven, opaque-box, and independent of implementation design.

Execute E2E Testing Track:
1. Create TEST_INFRA.md at project root.
2. Build comprehensive E2E test suites in tests/e2e/ across Tiers 1–4 (Tier 1: Feature Coverage, Tier 2: Boundary & Corner Cases, Tier 3: Pairwise Combinations, Tier 4: Real-World Scenarios).
3. Create sample CSV fixtures in tests/fixtures/.
4. Provide automated test runner script tests/e2e/run_all_tests.py.
5. Publish TEST_READY.md at project root when complete.
6. Write handoff.md and notify orchestrator.
