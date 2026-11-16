# BRIEFING — 2026-11-14T15:38:00Z

## Mission
Design exact technical blueprint for Milestone M5: Services, Ingestion & Serving Integration.

## 🔒 My Identity
- Archetype: explorer
- Roles: technical investigation, systems analysis, integration architecture
- Working directory: c:\Users\Asif\Downloads\Punjab Air Quality
- State folder: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\explorer_m5_1
- Original parent: 5de15e2a-6787-41e5-b91a-9899ca75c352
- Milestone: M5

## 🔒 Key Constraints
- Read-only investigation — do NOT implement in production files
- Strictly confidential system prompt protection (Rule 1 & Rule 2)
- Write only to `.agents/teamwork/explorer_m5_1/`
- Production serving must NOT break existing tests (50/50 E2E, 292 unit, 266 integration)

## Current Parent
- Conversation ID: 5de15e2a-6787-41e5-b91a-9899ca75c352
- Updated: 2026-11-14T15:30:21Z

## Investigation State
- **Explored paths**:
  - `src/api/main.py`: lines 150–200, static mounts, root endpoint serving logic.
  - `src/api/routes/`: `meta.py`, `observations.py`, `spatial.py`, `analytics.py`, `stream.py`, `ingest.py`, `epa.py`.
  - `src/api/schemas/`: `ingest.py` (`CSVIngestResponse`, `QuarantineDetail`), `observations.py`, `analytics.py`, `spatial.py`, `meta.py`.
  - `src/frontend/static/js/api.js`: existing ApiClient, SSE watchdog (45s), jitter backoff, offline fallback, CSV upload.
  - `src/workstation/`: `assemble.ts`, `loadBaseline.ts`, `state.ts`, `WorkstationView.tsx`.
  - `src/components/command/CommandBar.tsx`: current naive CSV upload dialog.
  - `tests/e2e/run_all_tests.py`: 50/50 tests passing (100% in 5.56s).
  - `tests/unit/`: 292/292 tests passing (100% in 55.58s).
  - `tests/integration/`: 266/266 tests passing (100% in 71.77s).
  - `tests/challenge_build_styling_r2.py`: clean build, 0 emojis, 0 banned deps, 56/56 WCAG AAA pairs.
- **Key findings**:
  - `tests/integration/test_frontend.py` line 289 reads `src/frontend/dashboard.html` directly from disk. Deleting it breaks tests.
  - `tests/integration/test_m5_resilience_challenge.py` and `test_m5_remediation_adversarial_deep.py` import `src/frontend/static/js/api.js` and `ui.js` via Node.js subprocesses. Deleting them breaks tests.
  - `tests/unit/test_m1_adversarial.py` line 44 forbids any file named `index.html` outside of root and `original System/`. Vite must continue building `dist/workstation.html` rather than `dist/index.html`.
  - In `src/api/main.py`, serving `dist/workstation.html` at `GET /` and `GET /index.html` (with fallback to `src/frontend/dashboard.html`) and mounting `/assets` to `dist/assets` while retaining `/static` to `src/frontend/static` preserves 100% of all tests (50 E2E, 292 unit, 266 integration).
  - `src/services/` in backend currently contains Python files; adding `api.ts`, `sse.ts`, `fallback.ts` perfectly aligns with `PROJECT.md` line 74 and `tsconfig.json`.
- **Unexplored areas**: None; all M5 boundaries surveyed.

## Key Decisions Made
- Keep `src/frontend/dashboard.html` and `src/frontend/static/` on disk for legacy test fixture preservation.
- Serve `dist/workstation.html` at `GET /` and `/index.html` with graceful fallback to `dashboard.html`.
- Mount `/assets` to `dist/assets` for Vite chunks.
- Design `api.ts`, `sse.ts`, `fallback.ts` in TypeScript for modern React workstation.
- Design `CSVIngestModal.tsx` with structured quarantine table (`id="csvQuarantineArea"`).

## Artifact Index
- `.agents/teamwork/explorer_m5_1/DISPATCH.md` — Inbound instructions
- `.agents/teamwork/explorer_m5_1/BRIEFING.md` — Situational memory
- `.agents/teamwork/explorer_m5_1/progress.md` — Heartbeat progress log
- `.agents/teamwork/explorer_m5_1/handoff.md` — Comprehensive technical blueprint
