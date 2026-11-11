## 2026-11-11T09:13:28Z
You are explorer_m5_it2_2, a technical Explorer for Milestone M5 (Iteration 2: Remediation) in the Punjab Air Quality Platform.

Working directory: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\explorer_m5_it2_2
Parent Orchestrator ID: dfe9ab49-5b73-4c71-b636-dccdcc9080ee

Mandatory Context Files to Read:
1. c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\ORIGINAL_REQUEST.md
2. c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\orchestrator\PROJECT.md
3. c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\challenger_m5_2\handoff.md
4. src/frontend/static/js/api.js (especially lines 130-180)
5. src/api/routes/stream.py (to see the SSE heartbeat and event formats)

Your Investigation Mission:
Investigate Defect D2 reported by Challenger 2:
1. In `src/frontend/static/js/api.js:134-176`, the EventSource / stream connection lacks a 45-second watchdog timer to detect silent TCP connection drops, ignores server keepalive comments, uses deterministic backoff without jitter (creating thundering herd risk), and abandons reconnection prematurely after 5 attempts.
2. Formulate the precise remediation blueprint:
   - Add a 45-second watchdog timer in `ApiClient` (`this.watchdogTimer`).
   - Listen for server ping / keepalive comments or messages (`: keepalive` comments or event handlers) to reset the watchdog timer.
   - If 45 seconds pass without receiving any data or keepalive ping, forcibly close the `EventSource`, transition status to `'fallback'`, and trigger reconnection.
   - Update `onerror` exponential backoff to incorporate full randomized jitter:
     `const base = Math.min(30000, 2000 * Math.pow(1.5, this.reconnectAttempts));`
     `const timeout = base * (0.5 + Math.random() * 0.5);`
   - Increase max reconnect attempts or allow continuous background reconnection attempts so the dashboard never permanently gives up.
3. Produce a detailed handoff report in c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\explorer_m5_it2_2\handoff.md following standard sections (Observation, Logic Chain, Caveats, Conclusion, Verification Method).
4. Send a message to the orchestrator (dfe9ab49-5b73-4c71-b636-dccdcc9080ee) when finished. DO NOT write or edit source code files.
