# Comprehensive Specification & Codebase Audit Report: Frontend, UI/UX, Map & Layers

**Agent Identity:** `spec_miner_r1_2`  
**State Folder:** `c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\spec_miner_r1_2`  
**Timestamp:** 2026-11-14T07:52:00Z  
**Authoritative Specifications Examined:**
- `c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\ORIGINAL_REQUEST.md`
- `c:\Users\Asif\Downloads\Punjab Air Quality\PROJECT.md`
- `c:\Users\Asif\Downloads\Punjab Air Quality\docs\UI_UX_SPECIFICATION.md`
- `c:\Users\Asif\Downloads\Punjab Air Quality\docs\TRANSFORMATION_LOGIC_SPEC.md`
- `c:\Users\Asif\Downloads\Punjab Air Quality\docs\SYSTEM_ARCHITECTURE.md`

---

## 1. Observation

### 1.1 Codebase Structure and File Existence Verification
A recursive inspection of `src/`, `package.json`, `tsconfig.json`, `vite.config.ts`, and root files reveals the following concrete layout:
- **Root Build Configuration:**
  - `package.json`: Contains React 18 (`^18.3.1`), MapLibre GL (`^3.6.2`), Deck.gl v8 packages (`@deck.gl/core`, `@deck.gl/layers`, `@deck.gl/mapbox`, `@deck.gl/geo-layers`, `@deck.gl/react` at `^8.9.36`), Vite 5 (`^5.4.11`), and TypeScript 5 (`^5.6.3`). Banned dependencies (`tailwindcss`, `lucide-react`, `heroicons`, `feather-icons`) are verified absent.
  - `tsconfig.json`: Configured with path alias `"@/*": ["src/*"]`, ES2022 target, React 18 JSX transform.
  - `vite.config.ts`: Configures `@vitejs/plugin-react`, `@` path alias, proxy to `http://127.0.0.1:9000/api`, and vendor chunking.
  - **CRITICAL DEFECT — Missing Root `index.html`:** There is **NO `index.html`** in the project root directory (`c:\Users\Asif\Downloads\Punjab Air Quality\index.html`).
- **Existing React Source Files (`src/`):**
  - `src/App.tsx` (157 lines): Scaffold container rendering the 5-zone grid shell with stubbed content and placeholder comments.
  - `src/main.tsx` (16 lines): Bootstrap mounting `<App />` into `#root`.
  - `src/styles/tokens.css` (176 lines): Scoped CSS custom properties for dark and light modes, meeting WCAG 2.1 AAA.
  - `src/styles/grid.module.css` (124 lines): Scoped CSS Module defining rigid 100vw x 100vh 5-zone grid.
  - `src/styles/typography.css` (135 lines): Typography hierarchy enforcing IBM Plex font stacks and tabular-nums.
  - `src/types/deckgl.d.ts` (24 lines): Ambient type declarations for Deck.gl packages.
  - `src/domain/types/index.ts` (508 lines): Complete canonical TypeScript interfaces for 9 pollutants, 7 PEPC grades, stations, districts, wind vectors, border nodes, fluxes, CPF roses, and QC series.
- **Missing Directories and Components in React (`src/`):**
  - `src/map/` (including `MapCanvas.tsx` and `layers/`): **DOES NOT EXIST**.
  - `src/components/` (including `command/`, `dock/`, `inspector/`, `scrubber/`, `common/`): **DOES NOT EXIST**.
  - `src/domain/normalizer/` (`dataNormalizer.ts`): **DOES NOT EXIST**.
  - `src/domain/math/*.ts` (client-side math transforms in TypeScript): **DOES NOT EXIST**.
  - `src/services/*.ts` (`api.ts`, `sse.ts`, `fallback.ts` in TypeScript): **DOES NOT EXIST**.
- **Legacy Prototype Code in `src/frontend/`:**
  - `src/frontend/dashboard.html` (546 lines) and `src/frontend/static/js/` (`api.js`, `app.js`, `canvas.js`, `geo.js`, `ui.js`) exist.
  - This legacy prototype is currently mounted and served by FastAPI at `GET /` (`src/api/main.py` lines 180-185).
  - Inspection of `src/frontend/dashboard.html` reveals:
    - Loads consumer fonts: `Barlow Condensed`, `Source Sans 3`, `JetBrains Mono` (line 11) rather than `IBM Plex`.
    - Contains consumer emojis: line 48 (`🔥 Fire Archive`), line 104 (`✈ Airport METAR Wind`), line 116 (`🔴 LIVE`).
    - Uses Canvas 2D custom software rasterization instead of locked MapLibre 2D + Deck.gl 5-layer stack.

### 1.2 Verbatim Tool Command Results
1. **TypeScript Typecheck (`npm run typecheck`):**
   ```
   > punjab-air-quality@1.0.0 typecheck
   > tsc --noEmit
   (Exit code: 0 - 0 errors across existing TypeScript files)
   ```
2. **Vite Production Build (`npm run build`):**
   ```
   > punjab-air-quality@1.0.0 build
   > tsc && vite build

   vite v5.4.21 building for production...
   ✓ 0 modules transformed.
   x Build failed in 12ms
   error during build:
   Could not resolve entry module "index.html".
       at getRollupError (file:///.../rollup/dist/es/shared/parseAst.js:350:41)
       at error (file:///.../rollup/dist/es/shared/parseAst.js:346:42)
       at ModuleLoader.loadEntryModule (file:///.../rollup/dist/es/shared/node-entry.js:23298:20)
   (Exit code: 1 - Build fails because root index.html is absent)
   ```
3. **WCAG 2.1 AAA Contrast & Banned Dependencies Audit (`python tests/challenge_contrast.py`):**
   ```
   Total surface/text pairs tested: 56 (28 dark + 28 light)
   Dark mode minimum CR:  7.1268:1 (--bg-panel-elevated vs --accent)
   Light mode minimum CR: 7.5749:1 (--bg-dock vs --ink-tertiary)
   All 56 pairs meet WCAG 2.1 AAA (>= 7.000:1): True
   Banned items detected: 0 (Zero banned dependencies in package.json, package-lock.json, or node_modules)
   (Exit code: 0)
   ```
4. **Backend E2E Regression Suite (`python tests/e2e/run_all_tests.py`):**
   ```
   Tier 1 | Feature Coverage & Contract Validation     | 13/13 PASS | 2.062s
   Tier 2 | Boundary, Corner & Limit Cases             | 11/11 PASS | 1.894s
   Tier 3 | Pairwise Combinations & Cross-Feature Dataflow | 21/21 PASS | 2.653s
   Tier 4 | Real-World Operational Scenarios           | 5/5   PASS | 1.634s
   TOTAL  | All E2E Test Suites                        | 50/50 PASS | 8.243s (100%)
   (Exit code: 0)
   ```
5. **Unit Test Suite Execution (`python -m pytest tests/unit`):**
   ```
   289 passed, 1 failed in 68.31s.
   Failure: tests/unit/test_m1_adversarial.py::TestArchivalRemnantsEmpirical::test_no_legacy_remnants_in_root_or_subdirs
   AssertionError: Found legacy artifact remnants outside 'original System/':
     ['node_modules\\texture-compressor\\docs\\index.html', 'node_modules\\hammerjs\\tests\\unit\\index.html']
   ```

---

## 2. Features Discovered

The following matrix documents all frontend, architectural, cartographic, and component features specified across `ORIGINAL_REQUEST.md`, `PROJECT.md`, `docs/UI_UX_SPECIFICATION.md`, and `docs/TRANSFORMATION_LOGIC_SPEC.md`, cross-referenced with empirical codebase status:

| # | Category | Feature | Description | Inputs | Outputs | Error Behavior | Discovered Via | Codebase Status |
|---|----------|---------|-------------|--------|---------|----------------|----------------|-----------------|
| 1 | Architecture | Rigid 100vw x 100vh 5-Zone CSS Grid | Strict grid layout containing command-bar, spatial-dock, map-canvas, receptor-inspector, temporal-scrubber with 0 page scrollbars | Viewport dimensions | 5 designated grid regions | Overflow hidden; clamped | `PROJECT.md §Architecture`, `UI_UX §1` | **Fully Implemented** (`src/styles/grid.module.css`, `src/App.tsx`) |
| 2 | Design System | WCAG 2.1 AAA Design Tokens | Contrast ratio >= 7.0:1 across all 56 surface/ink pairs (dark/light), 1px structural hairlines, 0px radius, 0px blur, 0 shadows | Theme attribute `[data-theme]` | CSS custom properties | Fallbacks in CSS vars | `PROJECT.md §F16`, `UI_UX §3.1` | **Fully Implemented** (`src/styles/tokens.css`) |
| 3 | Typography | IBM Plex Typography Hierarchy | Exclusive use of IBM Plex Sans, Sans Condensed, and Mono; mandatory `tabular-nums` on numbers | Font CSS rules & classes | Scaled, monospaced tabular readouts | System font fallback chain | `ORIGINAL_REQUEST §R1`, `UI_UX §3.3` | **Partially Implemented** (CSS defined in `src/styles/typography.css`; font loader missing in HTML) |
| 4 | Tooling | Banned Dependencies Ban | Absence of `tailwindcss`, `lucide-react`, `heroicons`, `feather-icons` | `package.json` | Clean build manifest | Build / test failure if present | `ORIGINAL_REQUEST §R1`, `PROJECT.md §F16` | **Fully Implemented** (Clean `package.json`, verified by test) |
| 5 | Bundler | Vite Production HTML Entry Point | Root `index.html` loading IBM Plex fonts, mounting `#root`, bootstrapping `src/main.tsx` | HTML template & Vite scripts | Compiled production bundle in `dist/` | Rollup entry module resolution error | `PROJECT.md §Code Layout` | **Missing** (`index.html` absent at root; `npm run build` fails) |
| 6 | Cartography | MapLibre GL 2D Planimetric Canvas | Strictly 2D planimetric canvas with `pitch: 0, maxPitch: 0, bearing: 0, dragRotate: false, touchPitch: false` | Geographic bounds (Punjab: 69.10°E–75.75°E, 27.55°N–34.30°N) | WebGL map container | Throws WebGL context error if canvas invalid | `ORIGINAL_REQUEST §R2`, `PROJECT.md §F17` | **Stubbed / Missing** (`src/App.tsx` line 105 has empty `div#mapLibreCanvas`; `src/map/` missing) |
| 7 | Layers | Deck.gl Interleaved `MapboxOverlay` Stack | Coordinates 5 Deck.gl layers interleaved over MapLibre canvas with GPU update triggers | Station/district geometries & layer toggles | Interleaved WebGL layers | Disables layer on data error | `ORIGINAL_REQUEST §R2`, `PROJECT.md §F18` | **Missing** (`src/map/` missing; only type defs in `src/types/deckgl.d.ts`) |
| 8 | Layers | Deck.gl Layer 1: Spatial Continuous Surface | 2D continuous IDW surface honoring Plate Carrée aspect ratio ($K_X = \cos 31^\circ$), anisotropic wind steering ($\epsilon = 4.0$ px, speed boost), 45-140 km alpha taper | Station coords, concentrations, wind $(u, v)$ | Continuous raster bitmap layer | Falls back to discrete isotropic IDW if wind missing | `ORIGINAL_REQUEST §R2`, `TRANSFORMS §2.2` | **Missing** in React (Python version exists in `src/domain/math/idw.py`) |
| 9 | Layers | Deck.gl Layer 2: District Choropleth & Labels | 41 district polygons colored by PEPC hex colors, diagonal hatching for estimated districts, Greedy AABB collision labels | District boundaries, concentrations, PEPC colors | PolygonLayer + TextLayer with leader lines | Clamps label offset within bounding box | `ORIGINAL_REQUEST §R2`, `TRANSFORMS §2.11` | **Missing** in React |
| 10 | Layers | Deck.gl Layer 3: Kinematic Wind Field | 3-state vector display: telemetry dropout glyphs (`null`), aerodynamic calm circles (<0.50 m/s), active vectors; Wazirabad blacklist | Station winds $(w_s, \theta)$ | Vector arrows & calm circles | Blacklisted station 172 renders no vector | `ORIGINAL_REQUEST §R2`, `TRANSFORMS §2.4` | **Missing** in React |
| 11 | Layers | Deck.gl Layer 4: Advection Flux & Border Chevrons | Top-60 coupled pathways ($d \le 180$ km, cone $\le 35^\circ$) with PM2.5 lock for AQI; 39 border normal chevrons (crimson when $\Phi_j > +0.25$ m/s) | District centroids, winds, concentrations | Animated Bezier arcs & border chevrons | Returns empty set for `AQI` (dimension guard) | `ORIGINAL_REQUEST §R2`, `TRANSFORMS §2.6-2.8`| **Missing** in React |
| 12 | Layers | Deck.gl Layer 5: Stations & Aerodromes | 79 monitoring stations (fixed squares, mobile diamonds, aerodrome crosshairs), Lahore 13 micro-airshed picking | Station metadata & coordinates | IconLayer / ScatterplotLayer with tooltips | Skips unlocated stations | `ORIGINAL_REQUEST §R2`, `PROJECT.md §F18` | **Missing** in React |
| 13 | Zone 1 | Top Command Bar & Identity | Workstation header, title, live stream vs fallback indicator, simulation clock | App state, connection status | Responsive header toolbar | Shows FALLBACK ARCHIVE on disconnect | `ORIGINAL_REQUEST §R3`, `PROJECT.md §F19` | **Partially Implemented** (hardcoded in `src/App.tsx` lines 19-42) |
| 14 | Zone 1 | Assertive ARIA Live Alert Region | Live screen reader announcements for hazardous smog episodes, PEQS exceedances, and 500 ceiling clamp | AQI values & alerts | Screen-reader audible text (`aria-live="assertive"`) | Silent when values within normal limits | `ORIGINAL_REQUEST §R3`, `UI_UX §6.3` | **Stubbed** (empty `div[role="status"]` in `src/App.tsx` line 45) |
| 15 | Zone 1 | 9-Pollutant Statutory Switcher | Radio buttons for AQI, PM2.5, PM10, NO2, SO2, CO, O3, NO, NOX with regulatory units | Selected pollutant state | Active button highlight & state update | Defaults to `AQI` | `ORIGINAL_REQUEST §R3`, `UI_UX §2.2` | **Partially Implemented** (buttons switch state in `App.tsx`, units/limits missing) |
| 16 | Zone 1 | CSV Ingestion & QA Toggles | Trigger buttons for user CSV modal upload (`POST /api/v1/ingest/csv`) and QA summary drawer | Click events | Ingestion dialog modal / QA drawer | Error badge on invalid file format | `ORIGINAL_REQUEST §R3`, `PROJECT.md §F19` | **Missing** from `src/App.tsx` |
| 17 | Zone 2 | Spatial Dock: 5-Layer Visibility Toggles | Interactive checkboxes toggling visibility for surface, choropleth, wind, flux, and stations | Layer visibility state record | Checkbox UI & layer visibility dispatch | None (state boolean) | `ORIGINAL_REQUEST §R3`, `PROJECT.md §F20` | **Partially Implemented** (checkboxes rendered in `App.tsx` lines 88-99) |
| 18 | Zone 2 | Spatial Dock: Mass-Balance Attribution Split Bar | Visual ratio bar comparing easterly transboundary inflow against domestic provincial emissions | Regional flux integrals | Bi-color split bar (e.g. 62% Cross-Border / 38% Domestic) | Falls back to 50/50 neutral if zero wind | `ORIGINAL_REQUEST §R3`, `PROJECT.md §F20` | **Missing** from `src/App.tsx` |
| 19 | Zone 2 | Spatial Dock: 41-District Statutory Ranking Table | Dynamically sorted table of 41 districts with current concentration, PEPC badge, and row selection centering the map | District hourly telemetry | Table with ranked rows; clicking centers map | Shows `IDW ESTIMATE` badge if unmonitored | `ORIGINAL_REQUEST §R3`, `PROJECT.md §F20` | **Missing** (`{/* Milestone 4 will mount ... */}` in `App.tsx` line 86) |
| 20 | Zone 4 | Receptor Inspector: Station & District Metadata | Name, division, coordinates, station type, anemometer flag, altitude | Selected station/district ID | Metadata header card | Shows "Select station/district" prompt when null | `ORIGINAL_REQUEST §R3`, `PROJECT.md §F21` | **Stubbed** (placeholder prompt in `src/App.tsx` lines 126-128) |
| 21 | Zone 4 | Receptor Inspector: 9-Parameter Sub-Index Table | Complete 9-pollutant table showing concentration, sub-index, PEPC category chip, and 75% completeness enforcement badge | Station hourly readings | Formatted tabular-nums metrics table | Shows `QC_INCOMPLETE_75` badge if valid hours < 75% | `ORIGINAL_REQUEST §R3`, `TRANSFORMS §2.10` | **Missing** from React |
| 22 | Zone 4 | Receptor Inspector: 16-Sector CPF Polar Wind Rose | 16-sector ($22.5^\circ$) directional probability rose, calm wind (<0.50 m/s) exclusion, pooled station $P_{75}$ threshold, $N_k < 6$ small-sample suppression, 0.25 null circle | Pooled station hourly wind $(w_s, \theta)$ & concentration | Polar rose SVG / Canvas with concentric rings | Sectors with $N_k < 6$ render muted 10px stubs | `ORIGINAL_REQUEST §R3`, `TRANSFORMS §2.5` | **Missing** in React (Python math exists in `src/domain/math/cpf.py`) |
| 23 | Zone 4 | Receptor Inspector: 216-Hour QC Time-Series Chart | Historical curve across 216 hours with PEQS threshold line, highlighting 7h median spikes and 3h logger holds (AQI exempt) | 216h station observation array | Interactive sparkline / line chart with anomaly markers | Zeroes and negatives purged to null | `ORIGINAL_REQUEST §R3`, `TRANSFORMS §2.10` | **Missing** in React (Python math exists in `src/domain/math/qc.py`) |
| 24 | Zone 5 | Precision Timeline Scrubber: Range Slider | Slider covering 216 integer hours with continuous sub-hourly decimal positions ($fp \in [0.00, 215.00]$) | Slider input `value` | Scrub position $fp$ & hour index | Clamped to $[0.00, 215.00]$ | `ORIGINAL_REQUEST §R4`, `PROJECT.md §F22` | **Stubbed** (bare `<input type="range">` in `src/App.tsx` lines 140-147) |
| 25 | Zone 5 | Precision Scrubber: Transport Controls & Shortcuts | Play/Pause toggle, +1h / -1h step, speed selection (0.35x, 0.8x, 1.6x), keyboard shortcuts (Space, Arrows, 1-9) | Keyboard events & button clicks | Animation loop start/stop & speed update | Monotonic requestAnimationFrame clamping | `ORIGINAL_REQUEST §R4`, `UI_UX §6.1` | **Missing** from `src/App.tsx` |
| 26 | Zone 5 | Precision Scrubber: Max AQI Horizon Sparkline | Sparkline of provincial maximum AQI plotted behind scrubber track, revealing severe inversion episodes | 216h provincial max AQI array | Background SVG / Canvas sparkline | Highlights severe smog inversions (>400) | `ORIGINAL_REQUEST §R4`, `PROJECT.md §F22` | **Missing** from `src/App.tsx` |
| 27 | Zone 5 | Precision Scrubber: Sub-Hourly Continuous Lerp | Smooth linear interpolation between hour $i$ and $i+1$ for concentrations and wind vectors without React state tearing | Fractional hour $fp$ & adjacent hourly matrices | Continuous snapshot for 60 FPS renderer | If either hour null, retains valid neighbor | `ORIGINAL_REQUEST §R4`, `UI_UX §4.1` | **Missing** in React |
| 28 | Domain | Normalizer Engine: 5 Schema Traps (`dataNormalizer.ts`) | Resolves: (1) centroid inversion, (2) aerodrome null vs calm, (3) station 172 blacklist, (4) dynamic station counts, (5) unified estimation flag & hatching | Raw baseline JSON or API payloads | NormalizedStation, NormalizedDistrict entities | Validates and sanitizes schemas | `ORIGINAL_REQUEST §R5`, `PROJECT.md §F11-F15` | **Missing** in TypeScript (`src/domain/normalizer/` absent) |
| 29 | Domain | TypeScript Client Math Engine | Frontend implementations of transforms T1, T2, T4, T5, T6, T7, T8, T9, T10, T11 in TypeScript | Client geometries, winds, readings | Calculated fields, vectors, matrices, colors | Numerical guards and singularity clamps | `PROJECT.md §F01-F10`, `TRANSFORMS §2` | **Missing** in TypeScript (Python versions exist in `src/domain/math/`) |
| 30 | Services | API & Streaming Integration Services | Typed client querying `/api/v1/*`, EventSource connecting to `/api/v1/stream/live`, in-memory fallback loader | HTTP/SSE network requests | Synchronized state in memory / store | Reconnects on network loss; falls back to baseline | `ORIGINAL_REQUEST §R5`, `PROJECT.md §F23-F25` | **Missing** in TypeScript (`src/services/*.ts` absent) |
| 31 | Ingestion | User CSV Multipart Ingestion Adapter | Client upload form sending CSV to `POST /api/v1/ingest/csv` validated against `UserCSVRowContract` | CSV file upload | Ingestion confirmation & re-interpolated field | Displays validation error messages on 422 | `ORIGINAL_REQUEST §R5`, `PROJECT.md §F23` | **Missing** in React |
| 32 | Integration | Production Serving at Port 9000 | FastAPI root serving compiled React dashboard at `GET /` and `/static/*`, preserving all 50/50 backend tests | HTTP requests to port 9000 | Compiled HTML, CSS, JS workstation app | 404 handler if dist missing | `ORIGINAL_REQUEST §R5`, `PROJECT.md §F25` | **Miswired** (FastAPI serves legacy `src/frontend/dashboard.html` instead of built React bundle) |

---

## 3. Edge Cases

The following matrix documents critical boundary conditions, mathematical singularities, and schema edge cases across all subsystems:

| # | Feature | Input | Observed / Required Behavior |
|---|---------|-------|------------------------------|
| 1 | Station 172 Anemometer Blacklist | Station 172 (Wazirabad) wind reading `ws = 2.4 m/s, wd = 45°` | Must be suppressed from map vector rendering and marked `blacklisted: true, state: 'blacklisted', blacklistReason: 'ANEMOMETER BLACKLISTED (VANE OFFSET)'` due to physical 140° vane offset. |
| 2 | Aerodrome Wind Outage vs Calm | Airport METAR wind speed `null` vs `0.0 <= ws < 0.50 m/s` | `null` wind speed must classify as `state: 'dropout'` and render a missing telemetry dropout glyph; `0.0 <= ws < 0.50 m/s` must classify as `state: 'calm'` and render a calm circle, excluded from directional rose counts. |
| 3 | Physical Dimension Guard | Advection flux calculation requested when active pollutant is `AQI` | Calculation must return an empty array `[]` or lock to PM2.5 ($\mu\text{g/m}^3$) with an assertive physical dimension guard warning, as multiplying dimensionless AQI by physical velocity ($m/s$) violates dimensional homogeneity and mass conservation. |
| 4 | PEPC AQI 500 Ceiling Clamping | Measured PM2.5 concentration $> 350.0\ \mu\text{g/m}^3$ (e.g. $420.0\ \mu\text{g/m}^3$) | Calculated AQI must be capped at 500 in accordance with EPA Punjab regulatory practice, assigned Tier 6 "Hazardous" with hex color `#C00000`, rather than extrapolating into unphysical unbounded values. |
| 5 | District Centroid Inversion | Raw district centroid in `baseline_data.json` formatted as `[lat, lon]` (e.g. `[31.5497, 74.3436]`) | Normalizer must invert centroid to `[lon, lat]` (`[74.3436, 31.5497]`) before passing to Deck.gl/MapLibre layers, while preserving `label` and `boundary` coordinates which are already `[lon, lat]`. |
| 6 | CPF Rose Small-Sample Suppression | Sector $k$ with total hours $N_k < 6$ (e.g. $N_k = 3$, $m_k = 3$) | Sector probability must be set to `null` and rendered as a neutral muted 10px circular stub rather than an exaggerated 100% directional plume wedge, preventing false directional attribution from rare winds. |
| 7 | 3-Hour Logger Hold Index Guard | Sample sequence at index $i=0$ or $i=1$ with identical values | An index boundary condition $i \ge 2$ must be enforced to prevent negative index array wraparound in Python/TypeScript pipelines (`v[-1]`), and physical pollutants ($p \ne \text{'AQI'}$) with $v_i = v_{i-1} = v_{i-2}$ must be flagged as logger holds and set to `null` (with AQI exempted). |
| 8 | 7-Hour Median Spike Filter | Measured value $v_i > 4.0 \cdot M_i$ and $v_i > 3.0 \cdot \text{ref}_p$ with rolling window $\ge 3$ samples | Value must be flagged as `QC_SPIKE_7H_MEDIAN` and converted to `null`, incrementing the spike anomaly counter for that station and pollutant. |
| 9 | Transboundary Normal Vector Inflow | 39 border normal vector dot products $\Phi_j = \mathbf{w}_j \cdot \mathbf{n}_j$ | When $\Phi_j > +0.25\text{ m/s}$, node triggers crimson chevron (`#ff6b5e`) indicating transboundary inflow into Punjab; when $\Phi_j < -0.25\text{ m/s}$, triggers teal chevron (`#5fc4c4`); when $|\Phi_j| \le 0.25\text{ m/s}$, chevron is neutral/suppressed. |
| 10 | Geodesic IDW Singularity Clamping | Distance between target unmonitored centroid and reporting station is 0.0 km | Distance must be clamped to minimum radius $d_0 = 5.0\text{ km}$, preventing division by zero and yielding finite weight $w = 1 / 25 = 0.04$. |
| 11 | 75% Temporal Completeness Rule | Daily aggregation duration with $< 75\%$ valid non-null hourly observations | Aggregated mean must return `null` and be flagged as `QC_INCOMPLETE_75` (enforced via $\ge \max(1, \text{round}(0.75 \times H))$). |
| 12 | Greedy AABB Label Placement | Two adjacent districts with overlapping bounding boxes (e.g. Lahore and Kasur) | Traverses 12 candidate offsets in order ($[0,0], [0,14], [0,-14], [16,0], \dots$); if displacement $> 20.0$ px, an automated leader line connects the centroid anchor dot to the offset label. |
| 13 | MapLibre 2D Planimetric Lock | User attempts touch-pitch, mouse right-drag rotation, or tilt gestures | Map viewport must strictly suppress pitch and bearing alterations (`pitch: 0, maxPitch: 0, bearing: 0, dragRotate: false, touchPitch: false`), maintaining an institutional planimetric cartographic projection. |

---

## 4. Logic Chain

1. **Premise 1 (Specification Target):** The project specification (`ORIGINAL_REQUEST.md`, `PROJECT.md`, `docs/UI_UX_SPECIFICATION.md`) mandates an institutional workstation frontend built using React 18, TypeScript, Scoped CSS Modules, MapLibre GL 2D, and Deck.gl v8 with 5 hardware-accelerated layers, WCAG 2.1 AAA tokens, and exclusively IBM Plex typography.
2. **Premise 2 (Current Codebase Reality):** Examination of `src/` confirms that:
   - Milestone 1 foundations (`tokens.css`, `grid.module.css`, `typography.css`) and TypeScript contracts (`src/domain/types/index.ts`) are implemented.
   - However, the component tree in React (`src/components/`, `src/map/`, `src/services/`, `src/domain/normalizer/`) is entirely missing. `src/App.tsx` contains only an empty skeleton with HTML placeholder divs and comments marking future milestones.
   - Root `index.html` is completely missing, which causes `vite build` to fail immediately.
   - The FastAPI server serves `src/frontend/dashboard.html` (a legacy prototype using Barlow/JetBrains fonts, emojis, and Canvas 2D) at `GET /`, rather than a built React bundle.
3. **Premise 3 (Backend Readiness):** The backend Python API, database repositories, and mathematical transformation engines are fully functional and pass all 50/50 backend E2E tests in 8.2s and 289/290 unit tests.
4. **Premise 4 (Adversarial Test Conflict):** The only failing unit test (`test_m1_adversarial.py`) contains a flaw: it checks `PROJECT_ROOT.rglob("*")` for forbidden file names `{"index.html", "index.htm", "collector.py"}` without excluding `node_modules`. If an implementer creates `index.html` at the project root for Vite, `test_m1_adversarial.py` will fail unless the test is updated to either exclude modern Vite entry points or exclude `node_modules` and allow root `index.html`.
5. **Conclusion:** The core gap in the system is that **Milestone 2 (TypeScript Normalizer/Math), Milestone 3 (MapLibre 2D Canvas & Deck.gl 5-Layer Stack), Milestone 4 (Zone 1-5 UI Components, CPF Rose, 216h QC Chart, Scrubber), and Milestone 5 (Frontend Services & Serving Integration)** have not been implemented in the React codebase.

---

## 5. Caveats

1. **Legacy Prototype vs. Target Workstation:** `src/frontend/dashboard.html` and its associated JavaScript files in `src/frontend/static/js/` represent a functional prototype that satisfies many functional requirements in vanilla JavaScript, but it directly violates the visual design, typography, and architectural constraints of `ORIGINAL_REQUEST.md` (no emojis, IBM Plex fonts only, MapLibre + Deck.gl 5-layer stack). The audit evaluates the target React workstation specified in `PROJECT.md`.
2. **Backend Unaffected:** The backend Python service and its test suite are solid and must not be broken during frontend completion.
3. **Third-Party Dependency Artifacts:** The unit test failure in `test_m1_adversarial.py` is caused by `node_modules\texture-compressor\docs\index.html` and `node_modules\hammerjs\tests\unit\index.html` matching `rglob("*")`, not by application source code.

---

## 6. Conclusion & Actionable Roadmap

The frontend implementation is currently at **Milestone 1 completion**. The remaining implementation work requires:
1. **Entry Point & Build Setup:** Create root `index.html` loading IBM Plex fonts (Sans, Sans Condensed, Mono) and mounting `src/main.tsx`. Fix `tests/unit/test_m1_adversarial.py` to exclude `node_modules` and permit the Vite root `index.html`.
2. **Domain Normalizer (`src/domain/normalizer/dataNormalizer.ts`):** Implement the 5 schema traps (centroid inversion, aerodrome null vs calm, station 172 blacklist, dynamic station counts, unified estimation flag).
3. **Client-Side Math Engine (`src/domain/math/`):** Port transforms T1, T2, T4, T5 (CPF rose), T6 (Advection flux with PM2.5 lock for AQI), T8 (39 border normals), T9 (PEPC continuous AQI & 500 clamp), T10 (QC filters & lerp), and T11 (AABB greedy labeling) to TypeScript.
4. **Planimetric Map & Deck.gl Stack (`src/map/`):**
   - `MapCanvas.tsx`: Locked 2D MapLibre GL canvas.
   - `layers/SurfaceLayer.ts`: IDW bitmap layer.
   - `layers/ChoroplethLayer.ts`: 41 districts with PEPC colors, diagonal hatching, and collision-free labels.
   - `layers/WindLayer.ts`: 3-state vector display with Station 172 blacklist.
   - `layers/FluxLayer.ts`: Top-60 pathways + 39 border chevrons.
   - `layers/StationLayer.ts`: 79 stations and aerodromes with picking.
5. **Workstation Components (`src/components/`):**
   - `command/CommandBar.tsx`: System status, assertive ARIA alerts, 9-pollutant switcher with PEQS limits, CSV upload modal trigger.
   - `dock/SpatialDock.tsx`: Layer toggles, transboundary mass-balance attribution split bar, 41-district statutory ranking table with map centering.
   - `inspector/ReceptorInspector.tsx`: Station/district metadata, 9-parameter statutory table with 75% completeness enforcement, 16-sector CPF polar wind rose, 216h time-series QC chart.
   - `scrubber/TimelineScrubber.tsx`: 216h baseline timeline, transport controls, max AQI horizon sparkline, continuous sub-hourly lerp.
6. **Services & Root Integration (`src/services/`):**
   - `api.ts`, `sse.ts`, `fallback.ts`.
   - Update `src/api/main.py` to serve Vite's compiled `dist/index.html` at `GET /` when built.

---

## 7. Verification Method

To independently verify all findings in this audit report:

1. **Verify Root Build Failure (Missing `index.html`):**
   ```powershell
   npm run build
   ```
   *Expected result:* Fails with `error during build: Could not resolve entry module "index.html"`.

2. **Verify TypeScript Compilation on Existing Types/Styles:**
   ```powershell
   npm run typecheck
   ```
   *Expected result:* Passes with exit code 0 on existing files.

3. **Verify WCAG 2.1 AAA Contrast & Banned Dependencies:**
   ```powershell
   python tests/challenge_contrast.py
   ```
   *Expected result:* 56/56 surface/ink pairs pass AAA contrast (CR >= 7.0:1); 0 banned dependencies.

4. **Verify Backend E2E Test Suite (50/50 Tests):**
   ```powershell
   python tests/e2e/run_all_tests.py
   ```
   *Expected result:* 50/50 tests pass across Tiers 1–4 in < 10 seconds.

5. **Verify Adversarial Archival Unit Test Failure on `node_modules`:**
   ```powershell
   python -m pytest tests/unit/test_m1_adversarial.py -k test_no_legacy_remnants_in_root_or_subdirs
   ```
   *Expected result:* Fails on `node_modules` index.html paths.

6. **Verify Non-Existence of Frontend Component & Layer Folders:**
   ```powershell
   Test-Path src/map; Test-Path src/components; Test-Path src/domain/normalizer
   ```
   *Expected result:* All return `False`.
