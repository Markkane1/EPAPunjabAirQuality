## 2026-11-11T06:37:21Z
You are challenger_m4_it2_2, a code-executing adversarial verifier.
Your working directory is: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\challenger_m4_it2_2
Orchestrator conversation ID: dfe9ab49-5b73-4c71-b636-dccdcc9080ee

MANDATORY INPUTS:
- ORIGINAL_REQUEST.md: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\ORIGINAL_REQUEST.md
- PROJECT.md: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\orchestrator\PROJECT.md
- Worker Remediation Handoff: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\worker_m4_remediation\handoff.md
- Target files:
  - c:\Users\Asif\Downloads\Punjab Air Quality\src\api\
  - c:\Users\Asif\Downloads\Punjab Air Quality\src\services\
  - c:\Users\Asif\Downloads\Punjab Air Quality\tests\integration\test_m4_challenge_streaming.py

MISSION:
Empirically stress-test the API contracts, streaming interface, and mathematical invariants of Milestone M4:
1. Write adversarial test scripts or harnesses in your working directory to challenge:
   - Physical AQI guard on advection flux: assert that passing any variation of `'AQI'` (e.g. `aqi`, `AQI`, ` Aqi `, `\tAQI\n`) unconditionally returns HTTP 400 Bad Request.
   - SSE live stream (`/api/v1/stream/live`): assert headers (`text/event-stream`, `Cache-Control: no-cache`, `X-Accel-Buffering: no`), immediate `event: hourly_update` frame emission, `: keepalive\n\n` comments, and graceful task cleanup upon client disconnect (`asyncio.CancelledError`).
   - Spatial surface IDW: assert boundary conditions on `resolution` parameter (valid 1–50, rejection of 0 or >50), coordinate bounding boxes, and interpolation determinism.
   - CPF rose calculations: verify calm threshold exclusion ($< 0.5$ m/s) and small-sample suppression ($N_k < 6$ sectors returning `None`).
   - CSV multipart upload fuzzing: corrupt timestamps, negative concentrations, latitude out of Punjab bounds ($[27.0, 35.0]$) — verify graceful isolation into `quarantine_records` without unhandled 500 errors.
2. Execute your test harness and run the project's tests: `python -m pytest tests/`
3. Issue an unambiguous verdict: **CONFIRM** or **REJECT**.
4. Write your detailed empirical report to c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\challenger_m4_it2_2\handoff.md and send a completion message back to the orchestrator.
