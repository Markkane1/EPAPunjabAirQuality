## 2026-11-11T09:26:37Z

You are worker_m5_remediation, a software engineering Worker for Milestone M5 (Iteration 2: Remediation) in the Punjab Air Quality Platform.

Working directory: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\worker_m5_remediation
Parent Orchestrator ID: dfe9ab49-5b73-4c71-b636-dccdcc9080ee

DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Mandatory Context Files to Read:
1. c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\ORIGINAL_REQUEST.md
2. c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\orchestrator\PROJECT.md
3. c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\explorer_m5_it2_1\handoff.md (CSV Quarantine UI blueprint)
4. c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\explorer_m5_it2_2\handoff.md (SSE Watchdog & Jitter blueprint)
5. c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\explorer_m5_it2_3\handoff.md (Test verification blueprint)

Your Implementation Tasks:
1. Implement Defect D1 Fix (CSV Quarantine Inspector UI Feedback):
   - In `src/frontend/static/js/ui.js`:
     - Add `renderCsvQuarantineReport(result)` that renders a styled, scrollable 5-column table (`Row #`, `Station ID`, `Error Type`, `Error Message`, `Raw Row Data`) and top-level schema error box inside `this.dom.csvQuarantineArea`.
     - Update `handleCsvUpload()`: If `result.status === 'failed'` or `valid_rows === 0`: show failure alert, render quarantine table, keep modal open (do NOT dismiss modal), and do NOT switch app mode. If `valid_rows > 0 && quarantined_rows > 0`: show partial warning alert, render quarantine table, keep modal open, and merge telemetry via `this.app.onCsvIngested(result)`. If `valid_rows > 0 && quarantined_rows === 0`: show success alert, dismiss modal, clear quarantine area, and call `this.app.onCsvIngested(result)`.
     - When file input changes, clear any previous quarantine messages.
   - In `src/frontend/static/js/api.js`:
     - In `uploadCSV()`: Only set `this.mode = 'user_csv'` if `result.valid_rows > 0 && result.status !== 'failed'`.
   - In `src/frontend/static/js/app.js`:
     - In `onCsvIngested(result)`: Add defensive guard: only update live status badge to `user_csv` if `result && result.valid_rows > 0 && result.status !== 'failed'`.
   - In `src/frontend/static/css/tokens.css`:
     - Expand `.modal-box` to `max-width: 760px; width: 92%;` and style the quarantine table classes (`.quarantine-table-wrap`, `.quarantine-table`, etc.) per the blueprint.

2. Implement Defect D2 Fix (SSE 45s Watchdog & Jittered Reconnection):
   - In `src/frontend/static/js/api.js`:
     - In `ApiClient` constructor, initialize `this.watchdogTimer = null; this.watchdogTimeoutMs = 45000;`.
     - Add `resetWatchdog(onStatusChange)`: clears previous timer and starts a 45s timer that, if expired, logs warning, closes `this.eventSource`, sets `this.mode = 'fallback'`, calls `onStatusChange('fallback')`, and triggers `this.handleReconnect(onStatusChange)`.
     - Add `clearWatchdog()` to cancel timer on close/error.
     - In `connectLiveStream()`: on open, on `hourly_update`, on `keepalive`, and on `ping`, call `this.resetWatchdog(onStatusChange)`.
     - In `handleReconnect()` (or `onerror`): add randomized full jitter:
       `const base = Math.min(30000, 2000 * Math.pow(1.5, Math.min(this.reconnectAttempts, 10)));`
       `const timeout = base * (0.5 + Math.random() * 0.5);`
       Allow continuous background reconnection attempts capped at 30s so the dashboard never permanently abandons live stream.
   - In `src/api/routes/stream.py`:
     - In `sse_event_generator()`: on the 15-second heartbeat, emit both the comment and the named event:
       `yield ": keepalive\n\nevent: keepalive\ndata: {}\n\n"`

3. Update Adversarial Resilience Test Suite:
   - In `tests/integration/test_m5_resilience_challenge.py`:
     - Update Test 4, Test 5, and Test 7 as detailed in `explorer_m5_it2_3/handoff.md §4.3` to positively assert the remediated behaviors (jitter presence and variance, 45s watchdog timer and keepalive listener, and quarantine inspector table rendering without premature modal dismissal).

4. Verification Commands:
   - Run `python -m pytest tests/integration/test_m5_resilience_challenge.py -v` (all 9 must pass).
   - Run `python -m pytest tests/integration/test_frontend.py -v` (all 7 must pass).
   - Run `python tests/e2e/run_all_tests.py` (all 50 must pass).
   - Run `python -m pytest tests/ -q` (all 540+ tests must pass with 0 failures and 0 regressions).

5. Handoff Report:
   - Write a detailed report to `c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\worker_m5_remediation\handoff.md`.
   - Send a message to the orchestrator (dfe9ab49-5b73-4c71-b636-dccdcc9080ee) with test outputs and results.
