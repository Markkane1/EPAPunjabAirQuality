## 2026-11-15T20:46:27Z
[Message] timestamp=2026-11-15T20:46:27Z sender=f2fa7191-2b95-4f46-b1cb-ef6f552d742b priority=MESSAGE_PRIORITY_HIGH content=You are Reviewer 2 (Pipeline & Anchor Cities Reviewer & Adversarial Evaluator) for the Punjab Air Quality project.

## Mandatory Reading & Authoritative Sources
- Read ORIGINAL_REQUEST.md at: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\ORIGINAL_REQUEST.md
- Read PROJECT.md at: c:\Users\Asif\Downloads\Punjab Air Quality\PROJECT.md
- Read SCOPE.md at: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\orchestrator_3\SCOPE.md
- Read Worker 2's handoff report at: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\worker_pipelines_r3_2\handoff.md
- Working Directory: c:\Users\Asif\Downloads\Punjab Air Quality
- Your State Folder: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\reviewer_pipelines_r3_2

## Mission & Verification Tasks
Objectively review AND adversarially challenge all pipeline and anchor city changes implemented by Worker 2:
1. Real Data Mandate (All 7 Pipelines):
   - Inspect `src/pipelines/firms.py`, `src/pipelines/iqair.py`, `src/pipelines/cams.py`, `src/pipelines/base.py`, `src/pipelines/scheduler.py`, `src/pipelines/cron_scheduler.py`.
   - Verify that all 7 required pipelines (EPA Punjab, NOAA METAR, WMO SYNOP, ECMWF IFS, NASA FIRMS, IQAir, CAMS) default to `live` mode and connect to real endpoints.
   - Verify that NO synthetic simulation generators (`_generate_fixture_data()`) or mock fallbacks are executed during live runs.
2. Degraded State Contract:
   - Check `src/pipelines/base.py`. Verify that when an external API is down or circuit breaker is tripped, workers emit `is_healthy = False`, `status = "degraded"` or `"unavailable"`, record the exact `degraded_reason`, and return `[]` or `None` rather than generating fake numbers.
3. Cross-Border Anchor Cities Differentiation:
   - Check `src/infrastructure/database/seeder.py` (lines 500-515) and `src/infrastructure/repositories/baseline_repository.py` (lines 1224-1246).
   - Verify that the city-independent sine wave formula has been eliminated.
   - Verify that all 6 anchor cities (Amritsar, Firozpur, Jalandhar, Ludhiana, Bathinda, Delhi NCR) possess distinct CPCB station IDs, distinct coordinates, distinct baseline AQI, PM2.5, PM10, diurnal variations, and statutory health tiers.
4. Master Orchestrator & Cron Scheduling:
   - Check `src/pipelines/scheduler.py` and `src/pipelines/cron_scheduler.py`.
   - Verify all 7 streams are registered in `live_stream_status`, `live_enabled_streams`, `tick_live_async()`, and cron jobs.
5. Strict User Feature Preservation:
   - Verify that zero user-implemented features, components, routes, pipelines, or domain logic have been deleted.
6. Run verification commands:
   - `python -m pytest tests/unit/test_staging_and_orchestrator.py`
   - `python -m pytest tests/integration/test_pipelines.py`
   - `python -m pytest tests/unit/test_epa_live_worker.py`
   - `python tests/e2e/run_all_tests.py`

Deliver your verdict (APPROVE or REQUEST_CHANGES) with full evidence chains in:
`c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\reviewer_pipelines_r3_2\handoff.md`.
Use send_message to report completion.
