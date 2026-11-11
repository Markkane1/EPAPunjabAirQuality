# Dispatch: challenger_m5_2
Target: Milestone M5 Component-Driven UI/UX Dashboard - Challenger 2 (Resilience, Offline Fallback, Streaming & Guard Stress Test)
Working directory: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\challenger_m5_2
Original request: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\ORIGINAL_REQUEST.md
Project plan: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\orchestrator\PROJECT.md
Implementation report: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\worker_m5_frontend\handoff.md
Specification: docs/UI_UX_SPECIFICATION.md


## 2026-11-11T08:55:05Z

You are challenger_m5_2, a code-executing adversarial verifier for Milestone M5: Component-Driven UI/UX Dashboard in the Punjab Air Quality Platform.

Working directory: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\challenger_m5_2
Parent Orchestrator ID: dfe9ab49-5b73-4c71-b636-dccdcc9080ee

Mandatory Context Files to Read:
1. c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\ORIGINAL_REQUEST.md
2. c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\orchestrator\PROJECT.md
3. c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\worker_m5_frontend\handoff.md
4. docs/UI_UX_SPECIFICATION.md

Your Responsibilities:
Empirically stress-test the frontend resilience, network failure modes, offline data fallback, and data integrity guards:
1. Offline Fallback & Zero-Dependency Operation: Verify that the frontend can load, initialize, and render all 5 zones completely from offline baseline fixtures (data/baseline/) without throwing uncaught exceptions when external network requests fail or return 500/503.
2. SSE Stream Watchdog & Reconnection: Verify that the EventSource / fetch stream consumer in src/frontend/static/js/api.js implements exponential backoff with jitter and a 45-second watchdog timer against silent TCP connection drops.
3. CSV Quarantine Inspector: Test uploading malformed, corrupted, out-of-bounds, or missing-column CSV files to ensure the client-side validation logic properly rejects them with detailed line-by-line quarantine feedback without crashing the dashboard.
4. Physical Invariant Guard: Confirm that requesting advection flux for dimensionless 'AQI' is blocked both on the client side (in api.js / ui.js) and returns 400 on the backend, preserving physical mass conservation J = C * u.
5. Write and execute an automated adversarial challenge script in tests/integration/ (e.g. tests/integration/test_m5_resilience_challenge.py) to empirically prove these defenses hold.
6. Verify the entire test suite passes without regressions: python -m pytest tests/
7. Produce a detailed handoff report in c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\challenger_m5_2\handoff.md with quantitative empirical evidence.
8. State your explicit verdict in handoff.md: **CONFIRM** or **REJECT**.
9. Send a message to the orchestrator (dfe9ab49-5b73-4c71-b636-dccdcc9080ee) with your verdict and report path.
