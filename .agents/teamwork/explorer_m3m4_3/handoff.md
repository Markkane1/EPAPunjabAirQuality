# Handoff Report: Milestone M3-M4 Technical Exploration & Verification Strategy

**Author:** Explorer 3 (`explorer_m3m4_3`)  
**Mission:** Technical exploration and establishment of the comprehensive testing, build verification, and integrity validation strategy for Milestone M3-M4 (Planimetric Map Canvas, 5 Deck.gl Layers & Workstation UI Components).  
**Target Milestone:** M3-M4  
**Date:** 2026-11-14  

---

## 1. Observation

Direct empirical observations from executing all repository harnesses, scripts, and test suites:

### 1.1 Repository Build Scripts & npm Scripts Audit (`package.json`)
Inspection of `package.json` (lines 6–11) reveals:
```json
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview",
    "typecheck": "tsc --noEmit"
  }
```
Direct tool commands and execution results:
- **`npm run typecheck` (`tsc --noEmit`)**:
  - Command: `npm run typecheck`
  - Result: Exit code 0, 0 errors, 0 warnings.
- **`npm run build` (`tsc && vite build`)**:
  - Command: `npm run build`
  - Result: Exit code 0 in 3.71s. Output bundles:
    - `dist/workstation.html` (1.17 kB)
    - `dist/assets/workstation-Bl3E_mTB.css` (68.60 kB)
    - `dist/assets/workstation-BqDgTl6Y.js` (214.31 kB)
    - `dist/assets/maplibre-vendor-CXbqErUc.js` (761.88 kB)
    - `dist/assets/deckgl-vendor-B82YM446.js` (7.40 kB)
    - `dist/assets/react-vendor-OkpEnMSB.js` (133.99 kB)
    - `dist/assets/baseline_data-Cj5zOAvJ.json` (10,732.45 kB)
- **`npm run check:workstation`**:
  - Command: `npm run check:workstation`
  - Verbatim Output: `npm error Missing script: "check:workstation"` (Exit code 1).
  - Cause: Script entry is not declared in `package.json`.
  - Underlying Script: `scripts/check-workstation.mjs` exists (10,461 bytes).
  - Direct Execution: `node scripts/check-workstation.mjs`
  - Verbatim Result:
    ```text
    workstation-check ok stations=74/5 render-ok
    workstation-check ok stations=74/5 render-ok
    ```
    Exit code 0!
- **`npm run test:unit`**:
  - Command: `npm run test:unit`
  - Verbatim Output: `npm error Missing script: "test:unit"` (Exit code 1).
  - Cause: Script entry is not declared in `package.json`.

### 1.2 WCAG 2.1 AAA Contrast & Banned Dependency Audit (`tests/challenge_contrast.py`)
- Command: `python tests/challenge_contrast.py`
- Result: Exit code 0 (100% compliance).
- Empirical Matrix Metrics:
  - 56 surface/text pairs tested (28 dark mode + 28 light mode).
  - Dark mode minimum Contrast Ratio: `7.1268:1` (`--bg-panel-elevated` `#1c2b2a` vs `--accent` `#5fc4c4`).
  - Light mode minimum Contrast Ratio: `7.5749:1` (`--bg-dock` `#e8ecea` vs `--ink-tertiary` `#3d4c48`).
  - Required threshold $\ge 7.000:1$ satisfied across all 56 pairs.
  - Banned items detected: `0` across `package.json`, `package-lock.json`, and `node_modules` (scanned for `tailwindcss`, `lucide-react`, `heroicons`, `feather-icons`, `@heroicons/react`, `feather-icons-react`).

### 1.3 Build, Styling & Emoji Adversarial Audit (`tests/challenge_build_styling_r2.py`)
- Command: `python tests/challenge_build_styling_r2.py`
- Result: Exit code 0.
  - Probe 1 (Production Build): Verified `dist/` and 10 asset chunks cleanly compiled.
  - Probe 2 (Banned Imports & Ambient Evasion): 0 violations found across `src/` tree; zero banned dependencies in `package.json`; `ambient.d.ts` verified deleted.
  - Probe 3 (Unicode Emoji Audit): Verified 0 emojis detected across `src/frontend/dashboard.html`, `index.html`, `src/workstation.html`, and the entire `src/` directory.
  - Probe 4 (Contrast Matrix): Re-verified all 56 pairs meet WCAG 2.1 AAA.

### 1.4 End-to-End Regression Test Suite (`tests/e2e/run_all_tests.py`)
- Command: `python tests/e2e/run_all_tests.py`
- Result: Exit code 0, 50/50 tests passed (100% success rate) in 5.600s:
  - Tier 1 (Feature Coverage & Contract Validation): 13/13 passed in 1.369s.
  - Tier 2 (Boundary, Corner & Limit Cases): 11/11 passed in 1.474s.
  - Tier 3 (Pairwise Combinations & Cross-Feature Dataflow): 21/21 passed in 1.638s.
  - Tier 4 (Real-World Operational Scenarios): 5/5 passed in 1.119s.
  - Emits: `test_results_e2e.json`.

### 1.5 Unit Test Suites (`tests/unit/`)
- **Python Unit Tests**:
  - Command: `python -m pytest tests/unit`
  - Result: Exit code 0, 292/292 tests passed in 54.42s (1 warning for `CallSpec2` deprecation in anyio plugin).
- **TypeScript Challenger Unit Tests**:
  - Command: `npx tsx tests/unit/test_challenger_m1m2.ts`
  - Result: Exit code 0, 2,095/2,095 assertions evaluated and passed in 2.1s across all 5 schema traps, PEPC continuous calculation, 500 ceiling clamp, 7h median spike filter, and 3h logger hold with $i \ge 2$ guard and AQI exemption.
  - Command: `npx tsx tests/unit/test_challenger_adversarial_m1m2_r2.ts`
  - Result: Exit code 0, 250/250 assertions evaluated and passed in 1.5s across Wazirabad station 172 blacklist variations and calm/active wind boundaries.

### 1.6 Integration Test Suite (`tests/integration/`)
- Command: `python -m pytest tests/integration`
- Result: Exit code 0, 266/266 tests passed in 68.81s across API endpoints, spatial routes, EPA live workers, Redis caching, streaming, and canvas integration.

### 1.7 Current Source Code Architecture vs. PROJECT.md Layout
- `PROJECT.md` specifies canonical paths:
  - `src/map/MapCanvas.tsx`
  - `src/map/layers/` (`SurfaceLayer.ts`, `ChoroplethLayer.ts`, `WindLayer.ts`, `FluxLayer.ts`, `StationLayer.ts`)
  - `src/components/command/CommandBar.tsx` (Zone 1)
  - `src/components/dock/SpatialDock.tsx` (Zone 2)
  - `src/components/inspector/ReceptorInspector.tsx` (Zone 4)
  - `src/components/scrubber/TimelineScrubber.tsx` (Zone 5)
  - `src/styles/grid.module.css` (100vw x 100vh rigid 5-zone grid container)
- Current state in filesystem:
  - `src/map/` does not exist yet (`Test-Path src/map` -> `False`).
  - `src/components/{command,dock,inspector,scrubber}` do not exist yet (`Test-Path` -> `False`).
  - `src/workstation/` currently houses interim implementations: `MapCanvas.tsx`, `WorkstationView.tsx`, `state.ts`, `assemble.ts`, `loadBaseline.ts`, `ssrEntry.tsx`, `mapData.ts`.
  - `scripts/check-workstation.mjs` directly imports `src/workstation/state.ts` and `src/workstation/ssrEntry.tsx`.

---

## 2. Logic Chain

From the above observations, the reasoning chain progresses as follows:

1. **Scripts Declaration Gap in `package.json`**:
   - `package.json` currently only defines `dev`, `build`, `preview`, and `typecheck`.
   - Running `npm run check:workstation` fails because the script alias is omitted, even though `scripts/check-workstation.mjs` is present and functional.
   - Adding `"check:workstation": "node scripts/check-workstation.mjs"` and `"test:unit": "tsx tests/unit/test_challenger_m1m2.ts"` to `package.json` immediately satisfies both command requirements without breaking any existing workflow.

2. **Map Canvas & Planimetric Constraints (M3)**:
   - R2 and `PROJECT.md` mandate that the MapLibre GL canvas is strictly 2D planimetric:
     `pitch: 0, maxPitch: 0, bearing: 0, dragRotate: false, touchPitch: false`.
   - In `src/workstation/state.ts`, `mapLibreConstructorOptions()` locks:
     `{ pitch: 0, maxPitch: 0, bearing: 0, dragRotate: false, touchPitch: false }`.
   - `scripts/check-workstation.mjs` lines 144–146 verify this state directly:
     `assert(lock.pitch === 0 && lock.maxPitch === 0 && lock.bearing === 0 && lock.dragRotate === false && lock.touchPitch === false)`.
   - Furthermore, lines 224 of `scripts/check-workstation.mjs` assert that rendered SSR markup includes `"pitch":0` or `data-pitch="0"`.
   - Therefore, the implementation in `src/map/MapCanvas.tsx` must instantiate MapLibre with these constructor options and call `map.dragRotate.disable()`, `map.touchZoomRotate.disableRotation()`, and `map.touchPitch.disable()`, while ensuring the DOM wrapper maintains `data-pitch="0"` and `data-map-lock`.

3. **Deck.gl 5-Layer Stack Invariants (M3)**:
   - The interleaved Deck.gl `MapboxOverlay` must render 5 hardware-accelerated layers:
     - **Layer 1: Spatial Surface (`SurfaceLayer.ts`)**:
       - 2D continuous IDW spatial surface bitmap honoring the Plate Carrée equirectangular projection aspect ratio ($K_X = \cos 31^\circ \approx 0.857167$).
       - Supports both isotropic geodesic (T1) and anisotropic wind-steered (T2) modes.
       - Bounds must match Punjab geographic envelope: $[69.30^\circ\text{E}, 27.70^\circ\text{N}, 75.50^\circ\text{E}, 34.15^\circ\text{N}]$.
     - **Layer 2: District Choropleth & Labels (`ChoroplethLayer.ts`)**:
       - 41 district polygons colored according to PEPC statutory hex colors.
       - Diagonal hatching (`est-hatch` pattern) triggered when `is_estimated === true`.
       - Centroids inverted from raw `[lat, lon]` to `[lon, lat]` (Trap 1).
       - Deterministic Greedy AABB collision labels placed across 12 candidate offsets with leader lines when offset $> 20$ px.
     - **Layer 3: Wind Vector Field (`WindLayer.ts`)**:
       - 3-state vector display:
         - Missing telemetry (`state: 'dropout'`, `null`): renders dropout glyph.
         - Aerodynamic calm ($0.0 \le w_s < 0.50$ m/s): renders stationary calm circle.
         - Active wind ($0.50 \le w_s \le 30.0$ m/s): renders directional vector arrow.
       - Station 172 (Wazirabad) anemometer blacklist: hard-block wind vector rendering (`blacklisted: true`), reason `ANEMOMETER BLACKLISTED (VANE OFFSET)`.
     - **Layer 4: Advection Flux & Border Chevrons (`FluxLayer.ts`)**:
       - Inter-district mass flux calculated for top-60 coupled links ($d \le 180.0$ km, cone $\le 35.0^\circ$).
       - Physical Dimension Guard: when pollutant is `'AQI'`, mass flux returns empty array `[]` because AQI is a dimensionless composite index; UI displays dimension guard banner `"Dimension Guard: Flux locked to PM2.5 mass"`.
       - 39 transboundary border normal chevrons: dot product $\Phi_j = \mathbf{w}_j \cdot \mathbf{n}_j$ triggering crimson color (`#C00000`) strictly when $\Phi_j > +0.25$ m/s.
     - **Layer 5: Stations & Aerodromes (`StationLayer.ts`)**:
       - 79 monitoring stations (74 fixed, 5 mobile) and 6 aerodromes.
       - Fixed stations rendered as circles/squares, mobile as diamonds, aerodromes as crosshairs.
       - All 13 Lahore micro-airshed stations individually pickable and distinguishable on the canvas.

4. **Workstation UI Zones 1–5 Regulatory Rules (M4)**:
   - **Zone 1: Command Bar (`CommandBar.tsx`)**:
     - Identity: `WORKSTATION_TITLE = "EPA Punjab Air Quality"`.
     - Stream indicator: `'LIVE SSE'` vs `'BASELINE FALLBACK'`.
     - Assertive ARIA Alert (`role="alert"`, `aria-live="assertive"`) triggered when PM2.5 $> 350.0\ \mu\text{g/m}^3$ (or AQI $\ge 500$) with background `#C00000` and text containing `HAZARDOUS` and `500`.
     - 9-pollutant statutory switcher (`AQI`, `PM2.5`, `PM10`, `NO2`, `SO2`, `CO`, `O3`, `NO`, `NOX`) with PEQS threshold limits.
     - Multipart CSV ingestion dialog trigger and QA drawer toggle.
   - **Zone 2: Spatial Control Dock (`SpatialDock.tsx`)**:
     - 5 layer toggle switches with active count badge (e.g. `5/5 Active`).
     - Transboundary mass-balance attribution split bar (domestic emissions share vs transboundary inflow share).
     - 41-district statutory ranking table with EST badges for estimated districts, and row selection centering the map.
   - **Zone 4: Receptor Inspector (`ReceptorInspector.tsx`)**:
     - Selected station / district metadata card.
     - 9-parameter statutory table with 75% temporal completeness rule (`validHours / totalHours >= 0.75` -> `≥75% VALID`, else `<75% INCOMPLETE`).
     - 16-sector CPF polar wind rose: calm wind exclusion ($w_s < 0.50$ m/s) and small-sample suppression ($N_k < 6$ valid hours hides sector fill and renders dashed arc).
     - 216-hour QC chart highlighting 7-hour median spikes ($v_i > 4M_i \land v_i > 3\text{ref}_p$) and 3-hour logger holds ($v_i = v_{i-1} = v_{i-2}$ with $i \ge 2$), with AQI exempted from logger hold detection.
   - **Zone 5: Temporal Playback Scrubber (`TimelineScrubber.tsx`)**:
     - 216-hour horizon (`2026-11-01 00:00` to `2026-11-09 23:00 PKT`).
     - Transport playback controls (play/pause, step forward/backward, speed rates `1x`, `2x`, `4x`, `8x`).
     - Horizon sparkline of provincial maximum AQI allowing direct click-to-seek for severe inversion episodes.
     - Sub-hourly continuous lerp ($\alpha \in [0.00, 1.00)$) driving GPU update triggers without re-parsing GeoJSON on CPU.

5. **Structural Integrity & Preservation of Test Guarantees**:
   - To satisfy `PROJECT.md`, the code should be cleanly organized in `src/map/` and `src/components/{command,dock,inspector,scrubber}`, while maintaining full backwards-compatibility with `src/workstation/` (via re-exports or unified modules) so that `scripts/check-workstation.mjs` and `npm run build` continue to succeed with exit code 0.
   - Zero banned packages (`tailwindcss`, `lucide-react`, `heroicons`, etc.) and zero Unicode emojis must be introduced.
   - Zero changes to backend routes that could degrade the 50/50 passing E2E suite or 266/266 integration suite.

---

## 3. Caveats

- **Headless WebGL Rendering in Node**: Deck.gl and MapLibre GL cannot initialize WebGL contexts under standard Node.js without software GL (e.g., headless-gl). The existing `scripts/check-workstation.mjs` appropriately validates SSR markup and pure mathematical models using esbuild bundling and `renderToStaticMarkup`. Real WebGL canvas rendering is verified via browser build bundling (`npm run build`) and DOM runtime inspection.
- **Backend Port 9000 Serving**: Serving the built frontend at `GET /` on port 9000 is part of Milestone M5. During M3-M4, the frontend is bundled to `dist/` and tested via Vite dev/preview and SSR node harnesses without altering FastAPI routing.
- **No other caveats.** All test suites, harnesses, and code trees have been empirically audited.

---

## 4. Conclusion & Technical Blueprint for M3-M4

Milestone M3-M4 must implement the authentic, institutional 2D Planimetric Map Canvas, the 5 Deck.gl layers, and the five-zone workstation UI components. The technical blueprint and component architecture are structured as follows:

```
src/
├── styles/
│   ├── tokens.css                     # WCAG 2.1 AAA tokens (CR >= 7.0:1)
│   ├── grid.module.css                # 100vw x 100vh rigid 5-zone grid
│   └── typography.css                 # IBM Plex Sans/Mono & tabular-nums
├── domain/
│   ├── normalizer/dataNormalizer.ts   # 5 schema traps, station counting
│   ├── math/                          # T1-T11 transforms (IDW, CPF, Flux, AQI, QC)
│   └── types/                         # Shared interfaces
├── map/
│   ├── MapCanvas.tsx                  # 2D locked MapLibre GL + MapboxOverlay
│   └── layers/
│       ├── SurfaceLayer.ts            # Layer 1: Continuous IDW bitmap (K_X = cos 31°)
│       ├── ChoroplethLayer.ts         # Layer 2: 41 districts, est hatching, greedy labels
│       ├── WindLayer.ts               # Layer 3: 3-state vector field, station 172 blacklist
│       ├── FluxLayer.ts               # Layer 4: Top-60 pathways, dimension guard, 39 chevrons
│       └── StationLayer.ts            # Layer 5: 79 stations/aerodromes, 13 Lahore picking
├── components/
│   ├── command/CommandBar.tsx         # Zone 1: Title, SSE/fallback, ARIA alert, 9 pollutants
│   ├── dock/SpatialDock.tsx           # Zone 2: 5 layer toggles, mass attribution, district table
│   ├── inspector/ReceptorInspector.tsx# Zone 4: Metadata, 75% completeness, 16-sector CPF, 216h QC
│   ├── scrubber/TimelineScrubber.tsx  # Zone 5: 216h scrubber, transport controls, max AQI horizon
│   └── common/icons.tsx               # 24 bespoke 1.25px stroke, miter-joined SVGs
├── workstation/                       # Pure state, SSR entrypoint & assemble pipeline
│   ├── state.ts                       # Workstation model builder, badges, legend, map options
│   ├── ssrEntry.tsx                   # Server-side renderToStaticMarkup harness
│   └── assemble.ts                    # UI model assemblage from baseline / API
└── App.tsx                            # Root application integrating grid & zones
```

---

## 5. Concrete Acceptance Criteria & 5-Gate Pass/Fail Verification Protocol

The upcoming Worker and Reviewer/Challenger/Auditor agents MUST execute and verify all 5 gates before sign-off:

### Gate 1: Static Code, Types & Dependency Hygiene
| Check ID | Verification Target | Command / Method | Pass Criteria |
|---|---|---|---|
| **G1.1** | TypeScript Compilation | `npm run typecheck` (`tsc --noEmit`) | Exit code 0, zero diagnostics. |
| **G1.2** | Banned Dependencies | `python tests/challenge_contrast.py` | 0 banned dependencies in `package.json`, `package-lock.json`, `node_modules`. |
| **G1.3** | Banned Imports & Evasion | `python tests/challenge_build_styling_r2.py` | 0 banned imports (`lucide-react`, `heroicons`, `tailwindcss`, etc.) in `src/`, zero `ambient.d.ts`. |
| **G1.4** | Unicode Emoji Eradication | `python tests/challenge_build_styling_r2.py` | 0 emojis detected in any `.html` or `src/` files. |
| **G1.5** | WCAG 2.1 AAA Contrast | `python tests/challenge_contrast.py` | 56/56 surface/ink pairs have contrast ratio $\ge 7.000:1$. |

### Gate 2: Production Build & Bundle Cleanliness
| Check ID | Verification Target | Command / Method | Pass Criteria |
|---|---|---|---|
| **G2.1** | Production Build | `npm run build` | Exit code 0 in $< 15$s. |
| **G2.2** | Bundle Artifacts | Inspect `dist/` directory | `dist/workstation.html` and valid JS/CSS asset chunks generated. |
| **G2.3** | Scripts Registration | `package.json` inspection | Both `"check:workstation"` and `"test:unit"` defined in scripts. |

### Gate 3: Workstation Specification & SSR Markup Integrity
| Check ID | Verification Target | Command / Method | Pass Criteria |
|---|---|---|---|
| **G3.1** | Workstation Pure State & SSR | `node scripts/check-workstation.mjs` (or `npm run check:workstation`) | Output contains `workstation-check ok stations=74/5 render-ok`, exit code 0. |
| **G3.2** | 5 Canonical Grid Zones | Inspect rendered SSR markup | Markup includes `id="command-bar"`, `id="spatial-dock"`, `id="map-canvas"`, `id="receptor-inspector"`, `id="temporal-scrubber"` with corresponding `data-zone` attributes. |
| **G3.3** | Rigid CSS Grid Container | Inspect layout styles | Uses `src/styles/grid.module.css` (`.workstation` grid container) with 100vw x 100vh, 1px hairlines, zero window-level scrollbars. |

### Gate 4: Cartographic Engine & Deck.gl Layer Verification
| Check ID | Verification Target | Command / Method | Pass Criteria |
|---|---|---|---|
| **G4.1** | 2D Planimetric Map Lock | Inspect `MapCanvas.tsx` & SSR | `pitch: 0, maxPitch: 0, bearing: 0, dragRotate: false, touchPitch: false`; handlers disabled; markup contains `data-pitch="0"`. |
| **G4.2** | Layer 1: Spatial Surface | `SurfaceLayer.ts` inspection & tests | Continuous IDW bitmap honoring Plate Carrée aspect ratio ($K_X = \cos 31^\circ$) and wind steering. |
| **G4.3** | Layer 2: District Choropleth | `ChoroplethLayer.ts` inspection & tests | 41 districts colored by statutory PEPC hex colors, `est-hatch` pattern for estimated districts, greedy AABB labels with leader lines when offset $> 20$ px. |
| **G4.4** | Layer 3: Wind Vector Field | `WindLayer.ts` inspection & tests | 3 states: dropout glyph for `null`, calm circle for $w_s < 0.50$ m/s, active vector arrow for $w_s \ge 0.50$ m/s. Station 172 (Wazirabad) wind vector suppressed. |
| **G4.5** | Layer 4: Flux & Chevrons | `FluxLayer.ts` inspection & tests | Top-60 coupled links ($d \le 180$ km, cone $\le 35^\circ$); returns `[]` when pollutant is AQI (physical dimension guard); 39 border normal chevrons render crimson (`#C00000`) strictly when $\Phi_j > +0.25$ m/s. |
| **G4.6** | Layer 5: Stations/Aerodromes | `StationLayer.ts` inspection & tests | 79 stations (74 fixed, 5 mobile, 6 aerodromes); fixed circles/squares, mobile diamonds, aerodrome crosshairs; 13 Lahore micro-airshed stations pickable. |
| **G4.7** | Domain Math & Normalizer Tests | `npx tsx tests/unit/test_challenger_m1m2.ts` | 2,095/2,095 assertions pass (exit code 0). |
| **G4.8** | Adversarial Kinematics Tests | `npx tsx tests/unit/test_challenger_adversarial_m1m2_r2.ts` | 250/250 assertions pass (exit code 0). |

### Gate 5: Backend Regression & E2E Preservation
| Check ID | Verification Target | Command / Method | Pass Criteria |
|---|---|---|---|
| **G5.1** | Backend E2E Suite | `python tests/e2e/run_all_tests.py` | 50/50 tests pass (100% success rate) in $< 30$s. |
| **G5.2** | Backend Unit Tests | `python -m pytest tests/unit` | 292/292 tests pass with exit code 0. |
| **G5.3** | Backend Integration Tests | `python -m pytest tests/integration` | 266/266 tests pass with exit code 0. |

---

## 6. Verification Method

To independently verify the findings in this report, execute the following commands in sequence:

```powershell
# 1. Typecheck and build verification
npm run typecheck
npm run build

# 2. Workstation specification & SSR harness
node scripts/check-workstation.mjs

# 3. TypeScript domain math & normalizer challenger suites
npx tsx tests/unit/test_challenger_m1m2.ts
npx tsx tests/unit/test_challenger_adversarial_m1m2_r2.ts

# 4. WCAG 2.1 AAA contrast and banned dependency verification
python tests/challenge_contrast.py
python tests/challenge_build_styling_r2.py

# 5. Backend regression and E2E verification
python tests/e2e/run_all_tests.py
python -m pytest tests/unit
python -m pytest tests/integration
```

**Invalidation Conditions:**
- Any TypeScript diagnostic or failure in `npm run build`.
- Any failure in `node scripts/check-workstation.mjs`.
- Any presence of banned dependencies or Unicode emojis.
- Any contrast ratio dropping below `7.000:1` in `src/styles/tokens.css`.
- Any failure or slowdown ($> 30$s) in the 50/50 backend E2E test suite.
