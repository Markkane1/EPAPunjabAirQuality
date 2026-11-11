## 2026-11-11T08:19:05Z
You are explorer_m5_integration, a read-only exploration agent.
Your working directory is: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\explorer_m5_integration
Orchestrator conversation ID: dfe9ab49-5b73-4c71-b636-dccdcc9080ee

MANDATORY INPUTS:
- ORIGINAL_REQUEST.md: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\ORIGINAL_REQUEST.md
- PROJECT.md: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\orchestrator\PROJECT.md
- docs/SYSTEM_ARCHITECTURE.md: c:\Users\Asif\Downloads\Punjab Air Quality\docs\SYSTEM_ARCHITECTURE.md
- docs/UI_UX_SPECIFICATION.md: c:\Users\Asif\Downloads\Punjab Air Quality\docs\UI_UX_SPECIFICATION.md
- src/api/main.py: c:\Users\Asif\Downloads\Punjab Air Quality\src\api\main.py
- src/api/routes/: c:\Users\Asif\Downloads\Punjab Air Quality\src\api\routes\
- data/baseline/: c:\Users\Asif\Downloads\Punjab Air Quality\data\baseline\

MISSION:
Investigate and design the API Integration, Delivery, and Automated Testing strategy for Milestone M5:
1. Examine the FastAPI backend routes and design the client-side API layer (`src/frontend/src/api/`):
   - Metadata client: fetch districts and stations from `/api/v1/meta/`
   - Observation client: fetch current and hourly series from `/api/v1/observations/`
   - Spatial surface client: fetch IDW grid rasters from `/api/v1/spatial/surface`
   - Analytics client: fetch CPF polar roses, advection flux vectors, and transboundary metrics from `/api/v1/analytics/`
   - SSE Live Stream Consumer: consume `GET /api/v1/stream/live`, parse `event: hourly_update`, handle `: keepalive` heartbeats, and automatically reconnect with backoff.
   - User CSV Dataset Uploader: multipart form upload to `POST /api/v1/ingest/csv`, handle response summary and quarantine display.
2. Design Offline & Fallback Data Strategy:
   - Provide seamless offline capability where the frontend can load baseline data directly from `data/baseline/` or pre-packaged JSON bundles when the FastAPI server is launching or in standalone demo mode.
3. Design Frontend Delivery via FastAPI:
   - Determine how FastAPI serves the frontend (e.g. `fastapi.staticfiles.StaticFiles` mounted at `/` or `/ui`, serving `src/frontend/`). Fix the minor `Optional` typing import in `src/api/main.py:9` if modifying.
4. Design Automated Verification & UI Test Strategy:
   - Design test cases for automated UI testing (e.g., verifying DOM elements across all 5 zones, 9 pollutant switches, time scrubber range, canvas layer initialization, and API data binding).
5. DO NOT WRITE OR MODIFY CODE. You are read-only.
6. Write your comprehensive integration blueprint to c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\explorer_m5_integration\handoff.md and send a completion message back to the orchestrator.
