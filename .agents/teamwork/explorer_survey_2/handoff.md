# Phase 0 Frontend Codebase & Tooling Survey Report

**State Folder**: `c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\explorer_survey_2`  
**Working Directory**: `c:\Users\Asif\Downloads\Punjab Air Quality`  
**Investigator Archetype**: Explorer (`explorer_survey_2`)  
**Date**: 2026-11-11  

---

## 1. Observation

### 1.1 Dependency & Package Ecosystem (`package.json`)
- **Command Executed**: `Get-ChildItem -Path . -Recurse -Filter "*package*.json" -Force`
- **Result**: No output (`$null`). `package.json` does not exist anywhere in the repository.
- **Node & NPM Tooling**:
  - `node -v` -> `v22.23.4`
  - `npm -v` -> `10.9.9`
- **Banned Dependencies**: Since no `package.json` exists, banned libraries (`tailwindcss`, `lucide-react`, `heroicons`, `feather-icons`) are currently absent from the workspace.
- **TypeScript & Build Tooling**: Neither `tsconfig.json` nor bundler configurations (`vite.config.ts`, `webpack.config.js`) exist. Running `tsc` or `npm run build` fails immediately.

### 1.2 Entrypoints & HTML Structure
- **HTML Files Found**:
  1. `original System/index.html` (805 lines, legacy monolithic prototype)
  2. `src/frontend/dashboard.html` (345 lines, active entry point mounted by FastAPI)
- **FastAPI Routing (`src/api/main.py:121-135`)**:
  ```python
  frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
  static_dir = frontend_dir / "static"
  if static_dir.exists():
      app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

  @app.get("/", include_in_schema=False)
  @app.get("/index.html", include_in_schema=False)
  async def serve_index():
      html_file = frontend_dir / "dashboard.html"
      if not html_file.exists():
          html_file = frontend_dir / "index.html"
      if html_file.exists():
          return FileResponse(html_file)
      return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"message": "Frontend dashboard not found"})
  ```
- **Font Loading in `src/frontend/dashboard.html:9-11`**:
  ```html
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@500;600;700&family=Source+Sans+3:wght@400;600;700&family=JetBrains+Mono:wght@400;600;700&display=swap">
  ```
  - Directly contradicts Acceptance Criteria: Loads `Barlow Condensed`, `Source Sans 3`, and `JetBrains Mono` instead of `IBM Plex Sans`, `IBM Plex Sans Condensed`, and `IBM Plex Mono`.
  - There is currently no `index.html` at the project root or in `src/` (only `dashboard.html`).

### 1.3 Styles, Tokens & WCAG AAA Contrast Ratios
- **Tokens Location**: `src/styles/tokens.css` does not exist (`Test-Path "src/styles/tokens.css"` returned `False`). Tokens are currently at `src/frontend/static/css/tokens.css` (968 lines).
- **CSS Variable Definitions (`src/frontend/static/css/tokens.css:50-54`)**:
  ```css
  --font-display: "Barlow Condensed", "Arial Narrow", -apple-system, sans-serif;
  --font-body: "Source Sans 3", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  --font-mono: "JetBrains Mono", ui-monospace, "SFMono-Regular", Menlo, monospace;
  ```
- **Empirical WCAG 2.1 Contrast Calculation**:
  A Python test script calculated relative luminance across all declared text and background token pairs in `src/frontend/static/css/tokens.css`:
  - **Dark Theme (`--bg-canvas: #0f1716`, `--bg-panel: #152120`, `--bg-panel-elevated: #1c2b2a`)**:
    - `--ink-primary` (`#e3ece9`) on `--bg-canvas` (`#0f1716`): **15.11:1** (PASS AAA, $\ge 7.0:1$)
    - `--ink-primary` (`#e3ece9`) on `--bg-panel` (`#152120`): **13.73:1** (PASS AAA, $\ge 7.0:1$)
    - `--ink-secondary` (`#93a39e`) on `--bg-canvas` (`#0f1716`): **6.91:1** (**FAILS AAA**, $\ge 7.0:1$)
    - `--ink-secondary` (`#93a39e`) on `--bg-panel` (`#152120`): **6.28:1** (**FAILS AAA**, $\ge 7.0:1$)
    - `--ink-secondary` (`#93a39e`) on `--bg-panel-elevated` (`#1c2b2a`): **5.58:1** (**FAILS AAA**)
    - `--ink-tertiary` (`#6b7a76`) on `--bg-panel` (`#152120`): **3.68:1** (**FAILS AA and AAA**)
    - `--accent` (`#5fc4c4`) on `--bg-panel` (`#152120`): **8.01:1** (PASS AAA)
  - **Light Theme (`--bg-canvas: #eef1ef`, `--bg-panel: #fbfcfb`, `--bg-panel-elevated: #ffffff`)**:
    - `--ink-primary` (`#17221f`) on `--bg-panel` (`#fbfcfb`): **15.89:1** (PASS AAA)
    - `--ink-secondary` (`#5b6964`) on `--bg-panel` (`#fbfcfb`): **5.60:1** (**FAILS AAA**)
    - `--ink-tertiary` (`#7e8c87`) on `--bg-panel` (`#fbfcfb`): **3.41:1** (**FAILS AA and AAA**)
    - `--accent` (`#0d6e72`) on `--bg-panel` (`#fbfcfb`): **5.85:1** (**FAILS AAA**)

### 1.4 Map Implementation & Deck.gl / MapLibre Setup
- **Current Viewport Element (`src/frontend/dashboard.html:78-79`)**:
  ```html
  <div class="viewport-canvas-container">
    <canvas id="mainMapCanvas" class="map-canvas" aria-label="Punjab Regional Air Quality Multi-Layer Map"></canvas>
  ```
- **Current Rendering Engine (`src/frontend/static/js/canvas.js:77-100`)**:
  - Employs an HTML5 2D canvas `CanvasMapEngine` drawing Path2D vector shapes, an offscreen downsampled canvas (`this.fcCanvas`) for IDW raster rendering, and a particle ring buffer.
  - Neither `maplibre-gl` nor `@deck.gl/core` / `@deck.gl/layers` / `@deck.gl/mapbox` are present or imported anywhere.
  - Pitch locking, MapboxOverlay interleaving, and Deck.gl update triggers do not exist in the current codebase.

### 1.5 Baseline Schema Traps Verification
- **District Centroids (`data/baseline/districts.json:10-13, 21-24, 25-30`)**:
  - `centroid`: `[33.669, 72.501]` ($\to [\text{lat}, \text{lon}]$)
  - `label`: `[72.425, 33.501]` ($\to [\text{lon}, \text{lat}]$)
  - `boundary`: `[[[72.435, 34.002], ...]]` ($\to [\text{lon}, \text{lat}]$)
  - **Trap Confirmed**: Centroid coordinates are strictly inverted relative to label/boundary GeoJSON conventions.
- **Station 172 (Wazirabad) Anemometer Blacklist (`data/baseline/stations.json:610-622`)**:
  - Station ID `"172"`, Name `"Wazirabad"`, Lat `32.320458`, Lon `73.956272`.
  - Must have wind vectors suppressed and flagged as ANEMOMETER BLACKLISTED (VANE OFFSET).
- **Aerodrome Wind Outages vs Calm (`data/baseline/airports.json:120-132`)**:
  - Aerodrome vector components `u` and `v` contain explicit `null` elements (e.g. lines 122-131).
  - Telemetry dropouts (`null`) are physically distinct from aerodynamic calm ($0.0 \le w_s < 0.500\text{ m/s}$).

### 1.6 Existing Test Suites & Backend Health
- **Backend E2E Regression Suite**:
  - `python tests/e2e/run_all_tests.py` ran 50 tests across Tiers 1-4.
  - Result: **50/50 passed (100%) in 2.122 seconds**.
- **Integration Test Suite**:
  - `python -m pytest tests/integration/` ran 239 tests.
  - Result: **239 passed in 53.60 seconds**.
- **CRITICAL DISCOVERY — Integration Test Coupling**:
  - `tests/integration/test_frontend.py`, `test_m5_canvas_challenge.py`, `test_m5_remediation_adversarial_deep.py`, and `test_m5_resilience_challenge.py` contain explicit assertions and Node.js subprocess harnesses targeting `src/frontend/static/js/canvas.js`, `src/frontend/static/js/ui.js`, `src/frontend/static/js/api.js`, and `src/frontend/static/css/tokens.css`.
  - For example, `test_m5_canvas_challenge.py:46` asserts `"this.PARTICLE_COUNT = 1300" in src`, and line 52 asserts `"new Float32Array(this.PARTICLE_COUNT * this.TRAIL_LENGTH * 2)" in src`.
  - `test_frontend.py:208-210` asserts `"Barlow Condensed" in tokens_css`, `"Source Sans 3" in tokens_css`, and `"JetBrains Mono" in tokens_css`.

---

## 2. Logic Chain

1. **Premise 1 (Tooling & Dependencies)**: Acceptance criteria require `package.json` with no banned dependencies, clean builds via `tsc` and `npm run build`, and zero compilation errors.
   - *Observation*: Neither `package.json`, `tsconfig.json`, nor build configs exist.
   - *Inference*: A root-level or frontend-level Node/TypeScript project structure must be formally initialized with standard devDependencies (`typescript`, `@types/*`, bundler/compiler) and production dependencies (`deck.gl`, `maplibre-gl`), strictly excluding `tailwindcss`, `lucide-react`, `heroicons`, and `feather-icons`.

2. **Premise 2 (Typography & Visual Tokens)**: Requirement R1 and acceptance criteria state: "index.html loads exclusively IBM Plex Sans, IBM Plex Sans Condensed, and IBM Plex Mono typography", and "All text/surface pairs in `src/styles/tokens.css` meet WCAG 2.1 AAA contrast ratio (>= 7.0:1)".
   - *Observation*: `dashboard.html` currently loads `Barlow Condensed`, `Source Sans 3`, and `JetBrains Mono`. `src/styles/tokens.css` does not exist (currently `src/frontend/static/css/tokens.css`). In current tokens, secondary ink (6.28:1), tertiary ink (3.68:1), and light theme accent (5.85:1) fail the 7.0:1 AAA threshold.
   - *Inference*:
     a. `src/styles/tokens.css` must be created.
     b. Color tokens must be recalibrated so that every foreground/background combination reaches $\ge 7.0:1$ luminance contrast.
     c. Google Fonts / local webfonts must be switched exclusively to IBM Plex Sans, IBM Plex Sans Condensed, and IBM Plex Mono.
     d. All numeric readouts must enforce `font-variant-numeric: tabular-nums`.

3. **Premise 3 (Map Rendering Architecture)**: Requirement R2 demands a 2D planimetric MapLibre GL map canvas with pitch 0, bearing 0, rotation disabled, and an interleaved Deck.gl MapboxOverlay with 5 discrete layers.
   - *Observation*: Current UI uses an HTML5 2D canvas without Deck.gl or MapLibre.
   - *Inference*: A modern Deck.gl + MapLibre integration must replace or encapsulate the 2D canvas viewport, rendering:
     - Layer 1: Continuous IDW surface bitmap honoring Plate Carrée aspect ratio ($K_X = \cos 31^\circ$).
     - Layer 2: GeoJsonLayer for 41 district polygons with PEPC colors, diagonal hatching for estimated districts, and greedy AABB label placement.
     - Layer 3: Wind vector field with 3-state logic and station 172 blacklist.
     - Layer 4: LineLayer/ArcLayer for top-60 transport flux pathways (PM2.5 locked when AQI is active) and 39 border normal chevrons ($\Phi_j > +0.25\text{ m/s}$ crimson trigger).
     - Layer 5: Scatterplot/IconLayer for 79 stations and aerodromes, with distinct glyphs and Lahore micro-airshed disaggregation.

4. **Premise 4 (Backend Compatibility & Regression Guardrails)**: Requirement R5 and acceptance criteria demand:
   - Dashboard accessible at `http://127.0.0.1:9000` while preserving all `/api/v1/*` routes and passing all 50/50 E2E backend tests.
   - Existing integration tests in `tests/integration/` test both backend routes and certain static JS/CSS structures.
   - *Inference*: The frontend build output must integrate seamlessly into the FastAPI delivery pipeline (e.g. served via `dashboard.html`/`index.html` and `/static`), maintaining full backward-compatibility with existing E2E regression tests (`tests/e2e/run_all_tests.py`), which currently run 100% clean (50/50 passed).

---

## 3. Caveats

1. **Integration Test Invariants vs. New Requirements**:
   - `tests/integration/test_frontend.py` checks for `"Barlow Condensed"`, `"Source Sans 3"`, and `"JetBrains Mono"` inside `tokens.css`.
   - `tests/integration/test_m5_canvas_challenge.py` tests specific properties in `src/frontend/static/js/canvas.js` (e.g. `PARTICLE_COUNT = 1300`).
   - *Caution*: The Phase 1/Phase 2 implementation plan must preserve the baseline JS modules or ensure compatibility so that running `pytest` does not trigger unintended test regressions unless those milestone-specific tests are intentionally aligned with R1-R5.
2. **Offline Baseline Availability**:
   - All 5 baseline JSON files (`airports.json`, `baseline_data.json`, `districts.json`, `districts_dict.json`, `stations.json`) are present and intact in both `data/baseline/` and `src/frontend/static/data/`.
3. **No Network Access for External CDNs**:
   - If external font downloads or map tiles fail in offline environments, webfonts and local GeoJSON boundary rendering must gracefully degrade without throwing unhandled runtime exceptions.

---

## 4. Conclusion

The existing codebase features a complete, highly-tuned FastAPI backend with 50/50 passing E2E tests and an initial vanilla JS canvas prototype. However, to meet the formal specification requirements (R1–R5) and acceptance criteria, the frontend requires:

1. **Build & Tooling Infrastructure**:
   - Create `package.json` with zero banned dependencies.
   - Configure TypeScript (`tsconfig.json`) and bundler (e.g., Vite) producing clean builds via `npm run build` and `tsc`.
2. **Typography & Styling System**:
   - Establish `src/styles/tokens.css` with verified $\ge 7.0:1$ WCAG 2.1 AAA contrast for all text/surface pairs.
   - Load exclusively IBM Plex Sans, IBM Plex Sans Condensed, and IBM Plex Mono.
   - Apply scoped CSS Modules for a rigid 100vw $\times$ 100vh 5-zone workstation layout.
3. **Cartography & Deck.gl Stack (R2)**:
   - Implement MapLibre GL locked to 2D planimetric view (`pitch: 0, maxPitch: 0, bearing: 0, dragRotate: false, touchPitch: false`).
   - Implement the interleaved 5-layer Deck.gl stack (`MapboxOverlay`).
4. **Data Normalization & Schema Traps (R5)**:
   - Implement `dataNormalizer.ts` resolving the 5 traps (Centroid inversion, aerodrome null vs calm, Station 172 blacklist, dynamic station counts, diagonal polygon hatching).
5. **FastAPI Serving Integration**:
   - Ensure the built dashboard is served at `http://127.0.0.1:9000/` without breaking any `/api/v1/*` endpoints.

---

## 5. Verification Method

To independently verify the observations and findings in this report:

1. **Verify Backend E2E Test Suite**:
   ```powershell
   python tests/e2e/run_all_tests.py
   ```
   *Expected Result*: 50/50 tests pass with 100% success rate in $< 3$ seconds.

2. **Verify Missing Frontend Tooling**:
   ```powershell
   Test-Path package.json
   Test-Path tsconfig.json
   Test-Path src/styles/tokens.css
   ```
   *Expected Result*: All return `False`.

3. **Verify Existing Token Contrast Failures**:
   ```powershell
   python -c "
   def lum(hex_c):
       hex_c = hex_c.lstrip('#')
       rgb = [int(hex_c[i:i+2], 16) / 255.0 for i in (0, 2, 4)]
       rgb = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
       return 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]
   def contrast(c1, c2):
       l1, l2 = lum(c1), lum(c2)
       return (max(l1, l2) + 0.05) / (min(l1, l2) + 0.05)
   print('Dark ink-secondary on panel:', contrast('#152120', '#93a39e'))
   print('Light accent on panel:', contrast('#fbfcfb', '#0d6e72'))
   "
   ```
   *Expected Result*: Output shows `6.28` and `5.85` respectively (both failing the $\ge 7.0:1$ requirement).

4. **Verify Centroid Schema Inversion in Baseline Data**:
   ```powershell
   python -c "
   import json
   with open('data/baseline/districts.json') as f:
       d = json.load(f)[0]
   print('Name:', d['name'])
   print('Centroid [lat, lon]:', d['centroid'])
   print('Label [lon, lat]:', d['label'])
   "
   ```
   *Expected Result*: Centroid is `[33.669, 72.501]` (Lat, Lon) while Label is `[72.425, 33.501]` (Lon, Lat).

5. **Verify Station 172 Anemometer Blacklist Record**:
   ```powershell
   python -c "
   import json
   with open('data/baseline/stations.json') as f:
       st = [s for s in json.load(f) if s.get('station_id') == '172'][0]
   print('Station 172 Name:', st['name'], 'District:', st['district'])
   "
   ```
   *Expected Result*: Output confirms Station 172 is `Wazirabad`.
