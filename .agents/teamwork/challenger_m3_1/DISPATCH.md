## 2026-11-10T14:17:14Z
From: dfe9ab49-5b73-4c71-b636-dccdcc9080ee (parent)
Content:
You are challenger_m3_1 (Archetype: teamwork_challenger). Your working directory is c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\challenger_m3_1\

MANDATORY FIRST STEP: Read the following authoritative documents before testing:
1. c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\ORIGINAL_REQUEST.md
2. c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\orchestrator\PROJECT.md
3. c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\spec_miner_architecture\handoff.md
4. c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\worker_m3_pipeline_active\handoff.md
5. docs/DATA_SOURCES_AND_STREAMS.md
6. docs/DATA_PIPELINES_ARCHITECTURE.md

CHALLENGE OBJECTIVE:
Perform empirical adversarial testing and stress verification of Milestone M3 pipeline modules.
Stress-test:
- Fallback failover when live endpoints fail (simulate 404, 500, ConnectionError, timeout).
- User CSV adapter against corrupted inputs: missing columns, negative values, extreme coords, malformed timestamps, non-UTF8 characters, empty files.
Write an adversarial integration test suite in `tests/integration/test_m3_adversarial.py` and run `python -m pytest tests/integration/test_m3_adversarial.py -v`.
Deliver verdict: CONFIRM or REJECT in handoff.md and send a message when done.
