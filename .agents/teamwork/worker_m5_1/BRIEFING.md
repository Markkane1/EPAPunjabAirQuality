# BRIEFING — 2026-11-14T15:53:00Z

## Mission
Implement Milestone 5: API client, SSE real-time streaming with watchdog & jitter, offline fallback data provider with schema compatibility traps, CSV ingestion modal with quarantine area, CommandBar integration, and FastAPI static/assets mounting for workstation.html.

## 🔒 My Identity
- Archetype: worker
- Roles: implementer, qa
- Working directory: c:\Users\Asif\Downloads\Punjab Air Quality
- State folder: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\worker_m5_1
- Original parent: 5de15e2a-6787-41e5-b91a-9899ca75c352
- Milestone: M5

## 🔒 Key Constraints
- EXCLUSIVE WRITE BOUNDARIES:
  - `src/services/api.ts`
  - `src/services/sse.ts`
  - `src/services/fallback.ts`
  - `src/services/index.ts`
  - `src/components/command/CSVIngestModal.tsx`
  - `src/components/command/CommandBar.tsx`
  - `src/api/main.py` (ONLY static mounting & root serve_index section around lines 178–205)
- DO NOT delete `src/frontend/dashboard.html` or `src/frontend/static/js/api.js` (fixtures for tests).
- NO CHEATING: Genuine implementations, real state/behavior, no fake test assertions.

## Current Parent
- Conversation ID: 5de15e2a-6787-41e5-b91a-9899ca75c352
- Updated: 2026-11-14T15:53:00Z

## Task Summary
- **What to build**:
  1. `src/services/api.ts`: Typed fetch wrapper for `/api/v1/*` with Physical Invariant Guard on AQI -> PM2.5 in getAdvectionFlux.
  2. `src/services/sse.ts`: EventSource manager for `/api/v1/stream/live` with 45s TCP drop watchdog and full-jitter exponential backoff.
  3. `src/services/fallback.ts`: Offline baseline data loader adhering to the 5 schema traps.
  4. `src/services/index.ts`: Re-export services.
  5. `src/components/command/CSVIngestModal.tsx`: File upload modal with missing coord option and `#csvQuarantineArea`.
  6. `src/components/command/CommandBar.tsx`: Wire up Ingest CSV trigger.
  7. `src/api/main.py`: Mount `/assets` to `dist/assets`, retain `/static`, serve `dist/workstation.html` with fallback to `dashboard.html`.
- **Success criteria**: All typechecks, builds, unit tests, styling challenges, e2e tests (50/50), pytest unit (292/292), pytest integration (266/266) pass.

## Key Decisions Made
- `src/services/api.ts`: Coerces AQI to PM2.5 with a console warning in `getAdvectionFlux` to enforce physical mass conservation. Provides aliases `getFluxTransport`, `getDistrictsMeta`, `getStationsMeta`, `ApiClient`.
- `src/services/sse.ts`: Watchdog timer triggers after 45000ms of silence, resets mode to `'fallback'`, and invokes backoff with full jitter bounded between 1500ms and 30000ms.
- `src/services/fallback.ts`: Normalizes districts (inverted centroids to [lon, lat], unified isEstimated), stations (Wazirabad blacklist flagged), airports (3-state winds), and dynamic station counts (74 fixed, 5 mobile).
- `src/components/command/CSVIngestModal.tsx`: Features `#csvQuarantineArea` rendering a structured Dead Letter Quarantine table with `Row`, `Station ID`, `Error Code`, `Error Message`.
- `src/components/command/CommandBar.tsx`: Replaced inline dialog with `CSVIngestModal`, keeping full backwards compatibility with optional callbacks.
- `src/api/main.py`: Mounted `/assets` to `dist/assets`, kept `/static` mount to `src/frontend/static`, and configured `serve_index` to deliver `dist/workstation.html` first.

## Artifact Index
- `.agents/teamwork/worker_m5_1/handoff.md` — Detailed M5 implementation & verification report
- `.agents/teamwork/worker_m5_1/progress.md` — Execution timeline and status
- `.agents/teamwork/worker_m5_1/DISPATCH.md` — Assignment log

## Change Tracker
- **Files modified**:
  - `src/services/api.ts` (created)
  - `src/services/sse.ts` (created)
  - `src/services/fallback.ts` (created)
  - `src/services/index.ts` (created)
  - `src/components/command/CSVIngestModal.tsx` (created)
  - `src/components/command/CommandBar.tsx` (modified)
  - `src/api/main.py` (modified)
- **Build status**: PASS (npm run build: exit code 0; npm run typecheck: exit code 0)
- **Pending issues**: None

## Quality Status
- **Build/test result**: ALL PASSED (50/50 E2E, 292/292 unit, 266/266 integration, 2095/2095 challenger assertions)
- **Lint status**: Clean, zero TS errors, zero banned dependencies
- **Tests added/modified**: Full suite passing without regression
