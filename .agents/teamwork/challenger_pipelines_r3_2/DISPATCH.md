## 2026-11-15T20:46:59Z
You are Challenger 2 (Pipeline & Anchor Cities Empirical Challenger) for the Punjab Air Quality project.

## Mandatory Reading & Authoritative Sources
- Read ORIGINAL_REQUEST.md at: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\ORIGINAL_REQUEST.md
- Read PROJECT.md at: c:\Users\Asif\Downloads\Punjab Air Quality\PROJECT.md
- Read SCOPE.md at: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\orchestrator_3\SCOPE.md
- Read Worker 2's handoff report at: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\worker_pipelines_r3_2\handoff.md
- Working Directory: c:\Users\Asif\Downloads\Punjab Air Quality
- Your State Folder: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\challenger_pipelines_r3_2

## Mission & Empirical Stress-Testing Tasks
Write empirical stress test scripts and assert mathematical and operational correctness of Worker 2's pipeline implementations:
1. Live Data Mandate & Zero Synthetic Mocks:
   - Probe live upstream endpoints for NASA FIRMS, EPA Punjab, NOAA METAR, ECMWF IFS, and CAMS. Assert real telemetry is fetched.
   - Assert `worker_mode == "live"` by default on `FirmsIngestionWorker`, `IQAirIngestionWorker`, and `CamsIngestionWorker`.
   - Assert `PipelineOrchestrator` defaults `mode == "live"` and registers all 7 streams (`STR-01` to `STR-07`).
2. Degraded State Contract Fault Injection:
   - Inject network timeouts / transport exceptions into workers.
   - Assert that `run()` returns `[]` or `None`, sets `is_healthy == False`, `status == "degraded"` or `"unavailable"`, and does NOT fall back to fake numbers or synthetic dictionaries.
3. Cross-Border Anchor Cities Mathematical Differentiation:
   - Inspect `BaselineRepository.get_cross_border()` and `src/infrastructure/database/seeder.py`.
   - Assert that for all 6 anchor cities (Amritsar, Firozpur, Jalandhar, Ludhiana, Bathinda, Delhi NCR):
     - All 6 have unique, distinct `station_id` (e.g. `IN_ASR_001`, `IN_FZP_001`, etc.).
     - All 6 have unique, distinct `latitude` and `longitude`.
     - All 6 have unique, distinct baseline `aqi`, `pm25`, and `pm10` values.
     - Mathematical variance across city AQIs is non-zero (zero identical duplicates).
4. Run verification tests:
   - `python -m pytest tests/unit/test_staging_and_orchestrator.py`
   - `python -m pytest tests/integration/test_pipelines.py`
   - `python tests/e2e/run_all_tests.py`

Deliver your verdict (APPROVE or REQUEST_CHANGES) with assertion counts and test outputs in:
`c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\challenger_pipelines_r3_2\handoff.md`.
Use send_message to report completion.
