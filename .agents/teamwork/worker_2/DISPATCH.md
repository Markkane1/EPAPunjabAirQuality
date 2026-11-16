## 2026-11-15T16:34:55Z
You are Worker 2: Pre-Production Remediation Worker.
Your mission is to execute the Iteration 2 Remediation Plan across the Punjab Air Quality repository to resolve all integrity violations and reviewer requests with genuine production-grade implementations and 100% test pass rates.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

MANDATORY FIRST STEP: Read the original user request at:
c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\ORIGINAL_REQUEST.md

Authoritative Action Plan and Evidence Reports:
- Iteration 2 Plan: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\orchestrator_1\REMEDIATION_PLAN_R2.md
- Forensic Auditor Evidence: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\auditor_1\handoff.md
- Reviewer 2 Evidence: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\reviewer_2\handoff.md

Tasks to execute:

1. Telemetry Health Transparency in CAMS (`src/pipelines/cams.py` & `src/pipelines/base.py`):
   - In `src/pipelines/cams.py`:
     * When `not valid_nodes` (line ~118): log warning, set `self.is_healthy = False`, and return fallback.
     * In `except Exception as e` (line ~161): log warning, set `self.is_healthy = False`, and return fallback.
   - In `src/pipelines/base.py`:
     * In `run()`: Ensure `self.is_healthy = True` is only set if `self.is_healthy` was not set to `False` by `fetch_data()`.

2. Fix Concurrency Stress Test Invariant (`tests/integration/test_m4_concurrency_stress.py`):
   - In `test_multithreaded_concurrent_reads_writes_and_cache_locks` (lines ~160-185):
     * 50 worker threads concurrently invoke `repo.save_surface_grid()` followed by `repo.get_surface_grid()` while other operations in the same test invoke `repo.clear_cache()`.
     * Because `clear_cache()` clears the global shared cache, concurrent reader threads observe `None` and fail assertion.
     * Reconcile this so that thread-local cache validation is isolated or operations do not race with intentional global clearing mid-assertion, so that `python -m pytest` passes 100% cleanly (0 failures across all 757 tests).

3. Purge Prohibited Emojis in Mounted Static Assets:
   - In `src/frontend/static/js/app.js`:
     * Line 1692: Replace `📍 ${activeDistName}` with `[DISTRICT] ${activeDistName}` or `${activeDistName}`.
     * Line 1869: Replace `▶ Amritsar` with `-> Amritsar`.
   - In `src/frontend/static/js/ui.js`:
     * Line 414: Replace `🔥 FIRES` with `FIRES`.
     * Line 739: Replace `🔴 LIVE` with `LIVE`.
     * Line 744: Replace `⚪ HISTORICAL` with `HISTORICAL`.
     * Line 996: Replace `⚠️ CSV Validation Failed` with `[WARNING] CSV Validation Failed`.
     * Line 1005: Replace `ℹ️ Partial Ingestion` with `[INFO] Partial Ingestion`.
   - Scan `src/frontend/static/` to verify ZERO emojis remain.

4. Declare `@radix-ui/react-avatar` in `package.json`:
   - Add `"@radix-ui/react-avatar": "^1.1.1"` to `"dependencies"` in `package.json`.
   - Ensure clean dependency tree (`npm run typecheck` and `npm run check:workstation` pass).

5. Calibrate WCAG 2.1 AAA Contrast on PEPC Badges (>= 7.0:1):
   - In `src/styles/tokens.css`:
     * Set `--pepc-unhealthy: #B30000;` and `--pepc-unhealthy-ink: #ffffff;` (giving 7.20:1 AAA contrast >= 7.0:1).
   - In `src/workstation/state.ts` (lines ~155-165):
     * In `pepcColorForAqi(aqi)`:
       - Good (0–50): background `#009966`, text `#000000` (9.5:1 contrast >= 7.0:1).
       - Satisfactory (51–100): background `#58B947`, text `#000000` (10.5:1 contrast >= 7.0:1).
       - Moderate (101–200): background `#FFDE33`, text `#111827` (16.2:1 contrast >= 7.0:1).
       - Poor (201–300): background `#FF9933`, text `#000000` (10.5:1 contrast >= 7.0:1).
       - Very Poor (301–400): background `#B30000`, text `#FFFFFF` (7.20:1 contrast >= 7.0:1).
       - Severe/Hazardous (400+): background `#800000`, text `#FFFFFF` (9.2:1 contrast >= 7.0:1).
