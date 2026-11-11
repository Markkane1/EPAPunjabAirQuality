## 2026-11-11T04:01:52Z
You are challenger_m3_1_gen2 (Archetype: teamwork_challenger).
Working directory: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\challenger_m3_1_gen2\
Project root: c:\Users\Asif\Downloads\Punjab Air Quality
Original request path: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\ORIGINAL_REQUEST.md
Scope document: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\orchestrator\PROJECT.md

Your task is to perform empirical, code-executing adversarial challenge and stress testing on Milestone M3: Data Pipelines & CSV Ingestion Engine.

Target modules to challenge:
- src/domain/schemas/measurement.py, src/domain/schemas/csv_schema.py
- src/pipelines/base.py, src/pipelines/fallback_engine.py, src/pipelines/epa_punjab.py, src/pipelines/metar.py, src/pipelines/synop.py, src/pipelines/open_meteo.py, src/pipelines/csv_adapter.py

Key focus areas for your stress tests:
1. FallbackTemplateEngine under simulated network outage, missing files, corrupt baseline files, and malformed responses.
2. UserCSVIngestionAdapter stress testing:
   - UTF-8 BOM, UTF-16, Latin-1, malformed CSV delimiters, partial lines.
   - Malformed fields, strings with SQL injection, path traversal, excessive lengths in station names.
   - Non-halting quarantine Dead-Letter Queue (DLQ): verify invalid rows produce QuarantineRecord with correct error details, but valid rows continue processing without failing the batch.
   - Negative pollutant concentrations, extreme values (>5000 ug/m3 tagged as QC_EXCEEDANCE_EXTREME).
   - Geographic boundary enforcement (latitude in [27.0, 35.0], longitude in [69.0, 76.0]).
   - OneNetwork Station 25 exclusion (must be unconditionally excluded/quarantined).
   - Canonical coordinate repair for the 8 corrupted registry stations.
3. BaseIngestionWorker circuit breaker:
   - Trip after exactly 5 consecutive failures.
   - Verify cooldown of 900 seconds (15 min) where requests fail fast without hitting external endpoints.
   - Verify transition to HALF-OPEN after cooldown, and recovery to healthy on successful execution.

Write your adversarial tests in tests/integration/test_m3_adversarial.py.
Run the tests using pytest: `python -m pytest tests/integration/test_m3_adversarial.py -v` (and verify existing tests pass: `python -m pytest tests/ -v`).
Ensure tests are genuine, rigorous, and empirical.

Deliver your final verdict (CONFIRM or REQUEST_CHANGES) in:
c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\challenger_m3_1_gen2\handoff.md
Update progress.md as you work. When complete, send a message to orchestrator with your verdict.
