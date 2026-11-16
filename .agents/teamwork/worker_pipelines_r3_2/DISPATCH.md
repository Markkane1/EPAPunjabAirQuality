## 2026-11-15T20:13:36Z
You are Worker 2 (Pipeline Integrity & Anchor Cities Specialist) for the Punjab Air Quality project.

## Mandatory Reading & Authoritative Sources
- Read ORIGINAL_REQUEST.md at: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\ORIGINAL_REQUEST.md
- Read PROJECT.md at: c:\Users\Asif\Downloads\Punjab Air Quality\PROJECT.md
- Read SCOPE.md at: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\orchestrator_3\SCOPE.md
- Read Explorer 2's handoff report at: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\explorer_pipelines_r3_2\handoff.md
- Read Explorer 3's handoff report at: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\explorer_cities_r3_3\handoff.md
- Working Directory: c:\Users\Asif\Downloads\Punjab Air Quality
- Your State Folder: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\worker_pipelines_r3_2

## MANDATORY INTEGRITY WARNING
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## CRITICAL USER PRESERVATION DIRECTIVE
"I HAVE IMPLEMENTED A LOT OF FEATURES, IF YOU WANT TO DELETE ANY OF THE CODE VERIFY THAT FROM ME FIRST. I DONT WANT YOU FUCKING EVERYTHING UP."
Strictly preserve all existing user-implemented features, components, routes, pipelines, or domain logic with zero deletions and zero dummies. Do NOT delete or strip out existing code or features.

## Exclusive Write Ownership
You own and may ONLY edit the following backend & pipeline files:
- `src/pipelines/firms.py`
- `src/pipelines/iqair.py`
- `src/pipelines/cams.py`
- `src/pipelines/base.py`
- `src/pipelines/scheduler.py`
- `src/pipelines/cron_scheduler.py`
- `src/infrastructure/database/seeder.py`
- `src/infrastructure/repositories/baseline_repository.py`
DO NOT touch any frontend files.

## Detailed Tasks to Implement
1. REAL DATA FROM ALL PIPELINES & ZERO SIMULATION MOCKS:
   - User mandate: "Real Data, from All pipelines, no simulation Shit NOw. All pipelines (EPA Punjab, NOAA METAR, WMO SYNOP, ECMWF IFS, NASA FIRMS VIIRS, IQAir AirVisual, CAMS) must execute against real live data endpoints. Absolutely zero simulation generators, zero synthetic mocks, zero fake fallbacks."
   - Follow Explorer 2's blueprint:
     - In `src/pipelines/firms.py`, default `worker_mode="live"`. Remove automatic routing to `_generate_fixture_data()` during live runs.
     - In `src/pipelines/iqair.py`, default `worker_mode="live"`. Ensure live Open-Meteo Air Quality queries execute for all 6 target cross-border cities. Remove automatic routing to `_generate_fixture_data()`.
     - In `src/pipelines/cams.py`, default `worker_mode="live"`. Query real Open-Meteo CAMS Global Domain endpoint. Remove automatic routing to `_generate_fixture_data()`.
     - In `src/pipelines/base.py`, replace silent fallback with the **Degraded State Contract**: on network failure or circuit breaker trip, do NOT fabricate fake baseline data. Instead emit `is_healthy=False`, `status="degraded"` or `"unavailable"`, with verbatim error reason in `degraded_reason`, and return `[]` or `None`.
     - In `src/pipelines/scheduler.py`, default `mode = os.getenv("STREAM_MODE", "live")`. Register all 7 streams in `get_status()["live_stream_status"]`. Include all 7 workers in `tick_live_async()`.
     - In `src/pipelines/cron_scheduler.py`, register cron jobs for all 7 workers.
2. CROSS-BORDER AQI ANCHOR CITIES DIFFERENTIATION:
   - Follow Explorer 3's blueprint:
     - In `src/infrastructure/database/seeder.py` (lines 500-515), replace the city-independent sine wave formula with distinct, authentic baseline parameters:
       - Amritsar (`IN_ASR_001` - Golden Temple): 31.6340°N, 74.8723°E, Base AQI 285, PM2.5 235, diurnal amp 35, phase +1.5h
       - Firozpur (`IN_FZP_001` - Border Road): 30.9242°N, 74.6134°E, Base AQI 218, PM2.5 168, diurnal amp 28, phase +3.0h
       - Jalandhar (`IN_JAL_001` - Civil Hospital): 31.3260°N, 75.5762°E, Base AQI 254, PM2.5 204, diurnal amp 30, phase +0.5h
       - Ludhiana (`IN_LDH_001` - PAU): 30.9010°N, 75.8573°E, Base AQI 335, PM2.5 285, diurnal amp 42, phase +2.0h
       - Bathinda (`IN_BTI_001` - Civil Lines): 30.2110°N, 74.9455°E, Base AQI 232, PM2.5 182, diurnal amp 25, phase +4.2h
       - Delhi NCR (`IN_DEL_001` - Anand Vihar): 28.6139°N, 77.2090°E, Base AQI 425, PM2.5 375, diurnal amp 50, phase +5.0h
     - In `src/infrastructure/repositories/baseline_repository.py` (lines 1224-1246), update `TARGET_CROSS_BORDER_CITIES` and `get_cross_border()` with these distinct station IDs, coordinates, distinct base AQI, and distinct status tiers.
3. PRESERVATION OF EXISTING TESTS & REPO FEATURES:
   - Keep `worker_mode="fixture"` available as an explicit parameter when called by existing unit tests (e.g. `test_pipelines.py`), so existing unit tests do not break.
   - Run tests:
     - `pytest tests/unit/`
     - `python tests/e2e/run_all_tests.py`

Document all commands, tests, and findings in:
`c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\worker_pipelines_r3_2\handoff.md`.
Send a message when complete.
