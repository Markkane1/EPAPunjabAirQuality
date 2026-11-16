## 2026-11-14T15:40:27Z
You are Worker M5 (`worker_m5_1`).
Your state folder: `c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\worker_m5_1`
Working directory: `c:\Users\Asif\Downloads\Punjab Air Quality`
Original Request path: `c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\ORIGINAL_REQUEST.md`
Scope document path: `c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\orchestrator_2_gen1\SCOPE.md`
Project document path: `c:\Users\Asif\Downloads\Punjab Air Quality\PROJECT.md`
Explorer Handoff path: `c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\explorer_m5_1\handoff.md`

MANDATORY FIRST STEP: Read `c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\ORIGINAL_REQUEST.md` before starting work.
Read `c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\explorer_m5_1\handoff.md` for the complete implementation blueprint.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

EXCLUSIVE WRITE BOUNDARIES:
You exclusively own and may create/edit these files:
- `src/services/api.ts`
- `src/services/sse.ts`
- `src/services/fallback.ts`
- `src/services/index.ts`
- `src/components/command/CSVIngestModal.tsx`
- `src/components/command/CommandBar.tsx`
- `src/api/main.py` (ONLY the static mounting & root serve_index section around lines 178–205)
DO NOT delete `src/frontend/dashboard.html` or `src/frontend/static/js/api.js` (existing integration tests depend on them as fixtures).

TASKS:
1. Implement `src/services/api.ts` per blueprint:
   - Full typed client wrapping fetch for `/api/v1/*` endpoints (`getHealth`, `getDistricts`, `getStations`, `getCurrentObservations`, `getHourlyObservations`, `getCPFRose`, `getAdvectionFlux`, `getTransboundary`, `uploadCSV`).
   - Physical Invariant Guard: In `getAdvectionFlux`, when `pollutant === 'AQI'`, coerce to `'PM2.5'` and warn, preserving mass conservation.
2. Implement `src/services/sse.ts` per blueprint:
   - Live EventSource manager connecting to `/api/v1/stream/live`.
   - 45-second silent TCP drop watchdog timer (reset on `hourly_update`, `keepalive`, `ping`, and general messages).
   - Randomized exponential backoff with full jitter: `base = min(30000, 2000 * 1.5^attempts)`, `delay = base * (0.5 + Math.random() * 0.5)`.
3. Implement `src/services/fallback.ts` per blueprint:
   - Offline baseline data loader using normalized entities and 5 schema traps.
4. Implement `src/components/command/CSVIngestModal.tsx` per blueprint:
   - Multipart upload to `POST /api/v1/ingest/csv` with `allow_missing_coords`.
   - Displays validation errors, and for quarantined records, displays `#csvQuarantineArea` with a structured inspection table.
   - Wire it up cleanly in `CommandBar.tsx`.
5. Update `src/api/main.py` (lines 178–205):
   - Mount `/assets` to `dist/assets` (where Vite outputs compiled chunks).
   - Retain `/static` mount to `src/frontend/static`.
   - In `serve_index()`: check `dist_dir / "workstation.html"` first and return it; fall back to `src/frontend/dashboard.html` if unbuilt.
6. Run all verification commands:
   - `npm run typecheck` (exit code 0)
   - `npm run build` (exit code 0)
   - `npm run check:workstation` (exit code 0)
   - `npm run test:unit` (exit code 0)
   - `python tests/challenge_contrast.py` (exit code 0)
   - `python tests/challenge_build_styling_r2.py` (exit code 0)
   - `python tests/e2e/run_all_tests.py` (50/50 pass)
   - `python -m pytest tests/unit` (292/292 pass)
   - `python -m pytest tests/integration` (266/266 pass)
