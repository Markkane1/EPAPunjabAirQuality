# Pre-Production Deep Audit Remediation Master Plan

## 1. Executive Summary & Audit Synthesis
This Master Plan synthesizes the exhaustive pre-production audits conducted by:
- Explorer 1 (Backend & Data Pipelines)
- Explorer 2 (Frontend UI, Cartography & Design System)
- Explorer 3 (Domain Physics, Normalizer & Test Integrity)

All findings directly address the mandate: **Zero dummies, zero dummy fallbacks, no imagined data, no AI slop, 100% production-grade rigor.**

---

## 2. Work Breakdown Structure (WBS)

### Track A: Backend Architecture & Pipelines (`src/api/`, `src/pipelines/`, `src/infrastructure/`)
1. **Direct Endpoint Aliases**:
   - In `src/api/main.py` and `src/api/routes/meta.py`, register direct `/api/v1/stations` and `/api/v1/districts` routes (in addition to `/api/v1/meta/*`) to satisfy `DATA_SOURCES_AND_STREAMS.md` and frontend API contracts.
2. **CORS Security Fix**:
   - In `src/api/main.py`, remove wildcard `*` when `allow_credentials=True`. Configure explicit institutional origins (`http://localhost:5173`, `http://127.0.0.1:5173`, `http://127.0.0.1:9000`, `http://localhost:9000`) or dynamically reflect request origin for credentials.
3. **Eliminate Masqueraded Mock Generators & Replace with Degraded Health Signals**:
   - In `src/pipelines/firms.py` and `src/pipelines/iqair.py`:
     * When external API keys are missing or requests fail, do NOT return synthetic random/hardcoded detections as if they were live telemetry.
     * Set clear pipeline health status (`status="degraded"` or `"unavailable"`), log warning, and return empty or explicitly flagged degraded records without synthetic mock masquerade.
4. **Remove Magic Numbers**:
   - In `src/pipelines/cams.py`: Remove hardcoded static wind fallback `(-1.8, -0.9)` and static multiplier `2.2`. Derive boundary wind from the nearest meteorological aerodrome/station vector or report telemetry unavailable.
   - In `src/pipelines/staging_buffer.py`: Remove hardcoded fallback flux `357.7` and fallback AQI `100`. Compute genuine values or propagate null/unmonitored indicators.
5. **Code Hygiene in `PipelineOrchestrator`**:
   - In `src/pipelines/scheduler.py`: Delete duplicate shadowed definition of `async def tick_async` (lines 331–368).
6. **Concurrent Station Registration & Thread-Safe Catalog**:
   - In `src/infrastructure/repositories/baseline_repository.py` and `src/api/routes/ingest.py`:
     * Fix `test_concurrent_reads_and_dynamic_csv_mutations`: When CSV rows introduce new stations, immediately register them in the station catalog (`list_stations()`).
     * Ensure thread-safe or atomic file reads/writes on `baseline_data.json` to prevent `JSONDecodeError` during concurrent execution.

---

### Track B: Domain Physics & Schema Traps (`src/domain/`)
1. **Station 172 Blacklist Completion in Python**:
   - In `src/domain/math/wind.py:19-25`, add `"172"` and `172` to `WIND_BLACKLIST_STATIONS` so that `is_station_blacklisted("172")` returns `True`.
   - In `src/infrastructure/repositories/baseline_repository.py:304`, use `is_station_blacklisted(sname)` or check `sid in ["172", 172]` instead of only string-searching `"wazirabad"`.
2. **Dedicated Python Data Normalizer**:
   - Create `src/domain/normalizer/normalizer.py` implementing the 5 schema traps:
     * Centroid inversion `[lat, lon]` -> `[lon, lat]`.
     * Aerodrome null vs calm ($w_s = \text{null}$ dropout vs $0.0 \le w_s < 0.50$ m/s calm).
     * Station 172 Wazirabad blacklist.
     * Dynamic station count segregation (fixed vs mobile).
     * Estimation flag unification (`is_estimated: boolean` from `est` / `is_monitored`).
   - Refactor `tests/unit/test_data_normalizer.py` to import and verify this production module.

---

### Track C: Frontend Workstation & Cartography (`src/`)
1. **Canonical 100vw x 100vh CSS Grid Restoration**:
   - In `src/workstation/WorkstationView.tsx`, import `src/styles/grid.module.css`.
   - Replace uncompiled Tailwind classes with the semantic classes from `grid.module.css`:
     * Container: `styles.workstation` (rigid 100vw x 100vh, 5 named grid areas).
     * Zone 1: `styles.commandBar`
     * Zone 2: `styles.spatialDock`
     * Zone 3: `styles.mapCanvas`
     * Zone 4: `styles.receptorInspector`
     * Zone 5: `styles.temporalScrubber`
2. **Resolve Ghost Dependencies in `package.json`**:
   - Add all 10 imported `@radix-ui/*` packages (`@radix-ui/react-slot`, `@radix-ui/react-dialog`, `@radix-ui/react-dropdown-menu`, `@radix-ui/react-label`, `@radix-ui/react-progress`, `@radix-ui/react-scroll-area`, `@radix-ui/react-select`, `@radix-ui/react-separator`, `@radix-ui/react-slider`, `@radix-ui/react-switch`, `@radix-ui/react-tabs`, `@radix-ui/react-tooltip`) to `package.json` dependencies, or replace with lightweight semantic accessible primitives.
3. **Theme Switch Attribute Fix**:
   - In `src/context/theme-provider.tsx`, ensure `root.setAttribute('data-theme', next)` is called alongside classList modifications so that light mode tokens in `src/styles/tokens.css` (`[data-theme="light"]`) correctly activate.
4. **WCAG 2.1 AAA Contrast Compliance**:
   - In `src/styles/tokens.css`, update `--pepc-unhealthy` or its ink token:
     * When badge background is `--pepc-unhealthy: #FF0000`, use dark ink (e.g. `#000000` or `#1A0000` which yields 10.5:1 contrast >= 7.0:1) or adjust tint to guarantee >= 7.0:1 AAA contrast.
5. **Interactive Wiring**:
   - In `src/App.tsx`:
     * In `onSelectDistrict`, trigger `mapRef.current?.flyTo([district.longitude, district.latitude])` to center the map.
     * In `onIngestFile`, after successful CSV upload, re-fetch observations or dynamically inject and re-interpolate into the active workstation state.
     * Connect `src/services/sse.ts` (`LiveStreamManager`) with its 45s watchdog instead of bypassing with raw unmanaged `new EventSource`.
6. **Animation Loop Optimization**:
   - In `src/App.tsx`, throttle or decouple the continuous sub-hourly lerp calculations from heavy 26,250-cell IDW raster recalculations (only re-rasterize when the active hourly observation slice changes or clamp to discrete animation frames).

---

### Track D: Test Harness & Verification Integrity (`tests/`)
1. **Eliminate Duplicate Shadow Oracle in `tests/e2e/conftest.py`**:
   - Refactor `tests/e2e/` suites (`test_tier1_feature_coverage.py`, `test_tier2_boundary_corner.py`, `test_tier3_pairwise_combinations.py`) to import directly from `src/domain/math/` instead of testing duplicate code in `conftest.py`.
2. **Remove In-Test Mock in Tier 4 Scenario 2**:
   - In `tests/e2e/test_tier4_real_world_scenarios.py`, test the real production `src/pipelines/fallback_engine.py` or fallback services instead of the in-test function stub.
3. **Ensure 100% Pass Across Entire Test Suite**:
   - Verify that `python -m pytest` passes 100% of tests with 0 failures across all unit, integration, and E2E suites.
   - Verify that `npx tsx tests/unit/*.ts` and `npm run typecheck` pass with 0 errors.
