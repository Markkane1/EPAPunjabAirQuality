## 2026-11-14T15:30:21Z
You are Explorer M5 (`explorer_m5_1`).
Your state folder: `c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\explorer_m5_1`
Working directory: `c:\Users\Asif\Downloads\Punjab Air Quality`
Original Request path: `c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\ORIGINAL_REQUEST.md`
Scope document path: `c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\orchestrator_2_gen1\SCOPE.md`
Project document path: `c:\Users\Asif\Downloads\Punjab Air Quality\PROJECT.md`

MANDATORY FIRST STEP: Read `c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\ORIGINAL_REQUEST.md` before starting work.

TASK:
Perform technical exploration and design the exact technical blueprint for Milestone M5: Services, Ingestion & Serving Integration.

SPECIFIC OBJECTIVES:
1. TypeScript Services Architecture in `src/services/`:
   - Inspect what exists in `src/services/` (if anything) and existing endpoints in `src/api/routes/`.
   - Design `src/services/api.ts`: typed client querying `/api/v1/districts`, `/api/v1/stations`, `/api/v1/forecast/hourly`, `/api/v1/health`, etc.
   - Design `src/services/sse.ts`: robust EventSource manager connecting to `/api/v1/stream/live` with automatic reconnection, heartbeat/keepalive monitoring, and message dispatch.
   - Design `src/services/fallback.ts`: fallback baseline data loader from `data/baseline/` or compiled assets when live stream disconnects.
2. CSV Multipart Ingestion Integration:
   - Check `src/api/routes/ingest.py` (or wherever `POST /api/v1/ingest/csv` is defined) to verify the expected multipart/form-data schema and response contracts.
   - Design the user CSV ingestion modal in `src/components/command/CSVIngestModal.tsx` (or integrated in `CommandBar.tsx`) to validate file format, upload to `POST /api/v1/ingest/csv`, display validation errors/success feedback, and trigger airshed re-interpolation.
3. Production Serving in FastAPI `src/api/main.py`:
   - Inspect `src/api/main.py` lines 180–185 where legacy `src/frontend/dashboard.html` is mounted.
   - Design the serving logic to serve compiled `dist/` (`dist/workstation.html` or `dist/index.html`) at `GET /`, and mount static assets (`dist/assets`) at `/assets` (and `/static`), while retiring the legacy dashboard.html.
   - CRITICAL REQUIREMENT: Verify that this change does NOT break any `/api/v1/*` endpoints, does not break any of the 50/50 backend E2E tests (`python tests/e2e/run_all_tests.py`), and does not break any of the 292/292 pytest unit tests or 266/266 integration tests. Check if any tests explicitly check `dashboard.html` or `GET /`.
4. Verification Plan for M5:
   - Detail the exact step-by-step verification commands and pass criteria.

DO NOT write source code to production files. You are an Explorer. Write your comprehensive analysis and technical blueprint to `c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\explorer_m5_1\handoff.md` and send a completion message to caller.
