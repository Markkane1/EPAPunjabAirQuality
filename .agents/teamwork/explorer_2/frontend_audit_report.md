# PRE-PRODUCTION AUDIT REPORT: FRONTEND INSTITUTIONAL WORKSTATION
**System**: EPA Punjab Air Quality Monitoring, Processing, and Visualization System  
**Auditor**: Explorer 2 (Frontend & UI/UX Deep Auditor)  
**Date**: 2026-11-15T07:25:00Z  
**Audit Scope**: Institutional Workstation (`src/`), Cartographic Engine, Deck.gl 5-Layer Stack, UI Components, Design System Tokens, CSS Architecture, API & Ingestion Integration.  
**Compliance Target**: WCAG 2.1 AAA, Rigid 100vw x 100vh CSS Grid, 60 FPS Planimetric Workstation, Zero Banned Artifacts, Zero AI Slop.

---

## 1. Executive Summary & Severity Breakdown

A deep, aggressive pre-production audit of all frontend source code (`src/App.tsx`, `src/main.tsx`, `src/workstation/*`, `src/components/*`, `src/map/*`, `src/styles/*`, `src/services/*`, `package.json`, `index.html`, `src/workstation.html`) was performed against the authoritative specifications (`docs/UI_UX_SPECIFICATION.md`, `docs/SYSTEM_ARCHITECTURE.md`, `PROJECT.md`, and `ORIGINAL_REQUEST.md`).

While mathematical transformations (T1–T11), domain normalization (the 5 schema traps), MapLibre planimetric locking, and Deck.gl layer constructors show robust mathematical implementation passing 2,095 empirical assertions, the audit identified **critical architectural defects in layout execution, CSS styling delivery, unmanaged ghost dependencies, performance rendering pipelines, theme activation, and interaction wiring**.

### Severity Summary Table

| Severity | Count | Summary of Key Issues |
|---|:---:|---|
| **CRITICAL (P0)** | 4 | 1) CSS Grid container (`grid.module.css`) bypassed; 241 Tailwind utility classes uncompiled/missing in CSS bundle. <br>2) 19 Shadcn UI components import undeclared `@radix-ui/*` ghost dependencies not in `package.json`. <br>3) Light mode theme switching completely broken (`root.classList.add` vs `[data-theme="light"]` attribute selector). <br>4) 60 Hz RAF loop in `App.tsx` triggers full React component tree re-renders and 26,250-cell CPU IDW re-rasterization on every frame. |
| **HIGH (P1)** | 4 | 1) Zone 2: 41-District ranking table selection does NOT center/fly map to target district coordinates. <br>2) Zone 1: CSV upload ingestion feedback sets status string only; does not re-fetch observations or update baseline state. <br>3) `src/services/sse.ts` (`LiveStreamManager`) with 45s watchdog & backoff bypassed by raw `new EventSource` in `App.tsx`. <br>4) Contrast failure on statutory PEPC chip: `#ffffff` on `#FF0000` (Unhealthy) is 4.00:1 (fails both AAA 7.0:1 and AA 4.5:1). |
| **MEDIUM (P2)** | 4 | 1) Banned visual artifacts in UI component classes: `shadow-sm`, `shadow-lg`, `rounded-md`, `rounded-full`. <br>2) Banned artifacts in legacy files: `dashboard.html` (`backdrop-filter: blur(12px)`), `static/css/tokens.css` (blur & shadows). <br>3) Discrepancy in `state.ts`: Indian AQI tiers ("Poor", "Very Poor", "Severe", `#009966`) used instead of official PEPC 7 tiers. <br>4) Deck.gl `MapboxOverlay` configured with `interleaved: false` instead of `interleaved: true`. |
| **LOW (P3)** | 2 | 1) SVG stroke linecap discrepancy: `icons.tsx` defaults `strokeLinecap = 'round'` vs tokens `square`. <br>2) Dead code: `flyToLahore` on `MapHandle` is never exposed or bound to a UI button. |

---

## 2. Rigid 100vw x 100vh CSS Grid Layout Verification

### 2.1 Specification vs Reality
- **Specification (`PROJECT.md §Architecture`, `src/styles/grid.module.css`)**:
  - Container must enforce `display: grid; width: 100vw; height: 100vh; overflow: hidden;`
  - Rows: `52px 1fr 68px`
  - Columns: `320px 1fr 380px`
  - Areas:
    ```
    "command-bar command-bar command-bar"
    "spatial-dock map-canvas receptor-inspector"
    "temporal-scrubber temporal-scrubber temporal-scrubber"
    ```
  - 1px hairlines separating zones: `border-bottom`, `border-right`, `border-left`, `border-top`.

### 2.2 Forensic Findings
1. **`grid.module.css` is Dead Code**:
   `src/styles/grid.module.css` defines the exact, pristine CSS Grid layout with scoped classes (`.workstation`, `.commandBar`, `.spatialDock`, `.mapCanvas`, `.receptorInspector`, `.temporalScrubber`). However, **`grid.module.css` is NOT imported anywhere in the entire codebase**.
2. **Layout Structure in `WorkstationView.tsx`**:
   Lines 43–62 of `src/workstation/WorkstationView.tsx`:
   ```tsx
   <div className="flex h-screen w-screen flex-col overflow-hidden bg-background text-foreground antialiased">
     <CommandBar ... />
     <div className="relative flex min-h-0 w-full flex-1 overflow-hidden">
       <SpatialDock ... />
       <main id="map-canvas" data-zone="map-canvas" className="relative h-full min-w-0 flex-1 overflow-hidden bg-muted/20">
         ...
       </main>
       <ReceptorInspector ... />
     </div>
     <TimelineScrubber ... />
   </div>
   ```
   - An intermediate `<div className="relative flex min-h-0 w-full flex-1 overflow-hidden">` wraps Zones 2, 3, and 4.
   - The layout uses nested Flexbox rather than the mandated rigid 3x3 CSS Grid.
3. **The 241 Missing Tailwind Utility Classes**:
   - `package.json` does NOT include `tailwindcss`, `postcss`, or `autoprefixer`.
   - `vite.config.ts` does NOT configure Tailwind.
   - An empirical scan of built CSS (`dist/assets/workstation-*.css`) reveals that **out of 242 unique utility classes used across JSX files, 241 classes (99.6%) do NOT exist in the CSS stylesheet**.
   - Classes like `flex`, `h-screen`, `w-screen`, `flex-col`, `overflow-hidden`, `bg-background`, `text-foreground`, `w-[340px]`, `w-[380px]`, `h-14`, `h-20`, `px-4`, `gap-3`, `border-border` are inert strings. In an unassisted browser, `<div className="flex ...">` renders as a default `display: block` element, collapsing or breaking the layout.

---

## 3. WCAG 2.1 AAA Design Tokens & Contrast Audit

Relative luminance and contrast ratios were calculated strictly according to ISO/IEC 17025 / WCAG 2.1 math:
$$L = 0.2126 R + 0.7152 G + 0.0722 B$$
$$CR = \frac{L_1 + 0.05}{L_2 + 0.05} \quad (\text{Target} \ge 7.0:1 \text{ for AAA})$$

### 3.1 Dark Mode Inks vs Surfaces (`src/styles/tokens.css`)

| Ink Token | Hex | Surface Token | Hex | Contrast Ratio | WCAG 2.1 AAA Status |
|---|---|---|---|:---:|:---:|
| `--ink-primary` | `#e3ece9` | `--bg-canvas` | `#0f1716` | **15.11:1** | PASS (AAA) |
| `--ink-primary` | `#e3ece9` | `--bg-panel` | `#152120` | **13.73:1** | PASS (AAA) |
| `--ink-primary` | `#e3ece9` | `--bg-panel-elevated` | `#1c2b2a` | **12.21:1** | PASS (AAA) |
| `--ink-primary` | `#e3ece9` | `--bg-dock` | `#131e1d` | **14.17:1** | PASS (AAA) |
| `--ink-secondary` | `#c0cfcb` | `--bg-canvas` | `#0f1716` | **11.29:1** | PASS (AAA) |
| `--ink-secondary` | `#c0cfcb` | `--bg-panel` | `#152120` | **10.26:1** | PASS (AAA) |
| `--ink-secondary` | `#c0cfcb` | `--bg-panel-elevated` | `#1c2b2a` | **9.12:1** | PASS (AAA) |
| `--ink-tertiary` | `#a8bbb5` | `--bg-canvas` | `#0f1716` | **9.04:1** | PASS (AAA) |
| `--ink-tertiary` | `#a8bbb5` | `--bg-panel` | `#152120` | **8.22:1** | PASS (AAA) |
| `--ink-tertiary` | `#a8bbb5` | `--bg-panel-elevated` | `#1c2b2a` | **7.31:1** | PASS (AAA) |
| `--accent` | `#5fc4c4` | `--bg-canvas` | `#0f1716` | **8.82:1** | PASS (AAA) |
| `--accent` | `#5fc4c4` | `--bg-panel-elevated` | `#1c2b2a` | **7.13:1** | PASS (AAA) |

*Dark mode textual inks pass WCAG 2.1 AAA across all standard workstation panels.*

### 3.2 Light Mode Inks vs Surfaces (`[data-theme="light"]`)

| Ink Token | Hex | Surface Token | Hex | Contrast Ratio | WCAG 2.1 AAA Status |
|---|---|---|---|:---:|:---:|
| `--ink-primary` | `#17221f` | `--bg-canvas` | `#eef1ef` | **14.37:1** | PASS (AAA) |
| `--ink-primary` | `#17221f` | `--bg-panel` | `#fbfcfb` | **15.89:1** | PASS (AAA) |
| `--ink-secondary` | `#34423e` | `--bg-dock` | `#e8ecea` | **8.83:1** | PASS (AAA) |
| `--ink-tertiary` | `#3d4c48` | `--bg-dock` | `#e8ecea` | **7.57:1** | PASS (AAA) |
| `--accent` | `#084e51` | `--bg-dock` | `#e8ecea` | **7.94:1** | PASS (AAA) |

*Light mode textual inks pass WCAG 2.1 AAA across all calibrated light surfaces.*

### 3.3 PEPC Statutory Chip Ink Contrast Violations

When concentrations are rendered inside colored metric chips or ranking badges:

| PEPC Tier | Background Hex | Ink Hex | Contrast Ratio | WCAG 2.1 AAA Status |
|---|---|---|:---:|:---:|
| **Good** | `#00B050` | `#000000` | **7.33:1** | PASS (AAA) |
| **Satisfactory** | `#92D050` | `#000000` | **11.36:1** | PASS (AAA) |
| **Moderate** | `#FFFF00` | `#000000` | **19.56:1** | PASS (AAA) |
| **Unhealthy (Sensitive)** | `#ED7D31` | `#000000` | **7.58:1** | PASS (AAA) |
| **Unhealthy** | `#FF0000` | `#ffffff` | **4.00:1** | **FAIL (< 4.5:1 AA & < 7.0:1 AAA)** |
| **Very Unhealthy** | `#7030A0` | `#ffffff` | **8.02:1** | PASS (AAA) |
| **Hazardous** | `#C00000` | `#ffffff` | **6.48:1** | **FAIL AAA (< 7.0:1, passes AA)** |
| **Emergency** | `#4A154B` | `#ffffff` | **14.00:1** | PASS (AAA) |

**Finding**:
1. In `src/styles/tokens.css` line 66: `--pepc-unhealthy-ink: #ffffff;` on `#FF0000` yields only **4.00:1**, violating both WCAG 2.1 AA (4.5:1) and AAA (7.0:1). Black ink (`#000000`) on `#FF0000` yields **5.25:1** (passes AA), but for strict AAA compliance, text on `#FF0000` must either be bordered or use an approved dark badge container.
2. In `src/styles/tokens.css` line 68: `--pepc-hazardous-ink: #ffffff;` on `#C00000` yields **6.48:1**, passing AA (4.5:1) but narrowly missing AAA (7.0:1).

---

## 4. Banned Dependencies, Artifacts & Typography Audit

### 4.1 Dependency Audit (`package.json`)
- **Tailwind CSS**: ABSENT from `package.json` (Compliant).
- **Consumer Icon Packs** (`lucide-react`, `@heroicons/react`, `react-icons`, `feather-icons`): ABSENT from `package.json` and 0 imports in source code (Compliant).
- **Ghost Dependencies Detected**:
  - `src/components/ui/*.tsx` imports:
    - `@radix-ui/react-slot`
    - `@radix-ui/react-dialog`
    - `@radix-ui/react-dropdown-menu`
    - `@radix-ui/react-label`
    - `@radix-ui/react-progress`
    - `@radix-ui/react-scroll-area`
    - `@radix-ui/react-select`
    - `@radix-ui/react-separator`
    - `@radix-ui/react-slider`
    - `@radix-ui/react-switch`
    - `@radix-ui/react-tabs`
    - `@radix-ui/react-tooltip`
  - NONE of these `@radix-ui/*` packages are defined in `package.json`! They currently exist only as unpinned transitive dependencies in `node_modules`.

### 4.2 Banned Visual Artifacts (Shadows, Blur, 3D Tilt, Emojis)
- **Emojis**: Scanned entire `src/` directory with Unicode regex (`[\u{1F300}-\u{1F9FF}]`, etc.). **0 emojis found** (Compliant).
- **3D Pitch/Tilt**: Scanned for pitch/bearing in map files. MapLibre canvas is strictly locked to `pitch: 0, maxPitch: 0, bearing: 0, dragRotate: false, touchPitch: false`.
- **Drop Shadows in Component Classes**:
  - `src/components/ui/button.tsx`: `shadow-sm`
  - `src/components/ui/card.tsx`: `shadow-sm`
  - `src/components/ui/dialog.tsx`: `shadow-lg`
  - `src/components/ui/dropdown-menu.tsx`: `shadow-md`
  - `src/components/ui/input.tsx`: `shadow-sm`
  - `src/components/ui/select.tsx`: `shadow-sm`, `shadow-md`
  - `src/components/ui/sheet.tsx`: `shadow-lg`
  - `src/components/ui/switch.tsx`: `shadow-sm`, `shadow-lg`
  - `src/components/ui/tabs.tsx`: `shadow-sm`
  - `src/components/ui/tooltip.tsx`: `shadow-md`
  *(Note: While `tokens.css` has `box-shadow: none !important`, the component codebase contains these banned artifact strings).*
- **Backdrop Blur in Legacy Files**:
  - `src/frontend/dashboard.html` line 19: `.zone-1-header { backdrop-filter: blur(12px); ... }`
  - `src/frontend/dashboard.html` line 543: `box-shadow: 0 4px 16px rgba(0,0,0,0.6); border-radius: 4px;`
  - `src/frontend/static/css/tokens.css`: lines 184, 551, 567, 640 (`backdrop-filter: blur(...)`) and lines 568, 1295, 1407, 1451 (`box-shadow: ...`).
- **Rounded Corners in Component Classes**:
  - `src/components/theme-switch.tsx` line 20: `rounded-full` (circular button).
  - Multiple `rounded-md`, `rounded-lg`, `rounded-full` classes in `src/components/ui/*`.

### 4.3 Typography & Inline SVGs
- **Fonts**: `index.html` / `workstation.html` properly load Google Fonts for IBM Plex Sans, IBM Plex Sans Condensed, and IBM Plex Mono.
- **Tabular-Nums**: `.tabular-nums` is declared in `src/styles/typography.css` with `font-variant-numeric: tabular-nums; font-feature-settings: "tnum" 1, "zero" 1;` and correctly applied to telemetry cells and coordinate labels.
- **Inline SVGs**: `src/components/common/icons.tsx` defines 30+ custom icons with `strokeWidth = 1.25` and `strokeLinejoin = 'miter'`.
  - **Minor Discrepancy**: Line 9 sets `strokeLinecap = 'round'`, whereas `tokens.css` specifies `--svg-stroke-linecap: square`.

---

## 5. Cartographic Engine & Deck.gl 5-Layer Stack Audit

### 5.1 Planimetric MapLibre Canvas (`src/map/MapCanvas.tsx`)
- Strictly 2D planimetric constraints verified:
  - `pitch: 0`
  - `maxPitch: 0`
  - `bearing: 0`
  - `dragRotate: false`
  - `touchPitch: false`
  - Keyboard rotation disabled (`map.keyboard.disableRotation()`).
  - Touch zoom rotation disabled (`map.touchZoomRotate.disableRotation()`).
- Deck.gl MapboxOverlay:
  - Line 281: `const overlay = new MapboxOverlay({ interleaved: false, layers: buildLayers(propsRef.current) });`
  - **Discrepancy**: `PROJECT.md` line 7 specifies an **interleaved** Deck.gl overlay (`interleaved: true`), whereas `MapCanvas.tsx` sets `interleaved: false`.

### 5.2 Layer 1: Spatial Surface Continuous Field (`SurfaceLayer.ts`)
- **Status**: Implemented & active.
- **Bounds**: `PUNJAB_SURFACE_BOUNDS = [69.10, 27.55, 75.75, 34.30]`.
- **Computation**: 150x175 offscreen canvas grid rasterizer using `anisotropicIdw` (incorporating wind steering vector and aspect ratio $K_X = \cos 31^\circ$) or `discreteGeodesicIdw`.
- **Alpha Taper**: Smooth distance opacity taper between 45 km and 140 km from monitors.
- **Output**: Returns hardware-accelerated Deck.gl `BitmapLayer`.

### 5.3 Layer 2: District Choropleth & Labels (`ChoroplethLayer.ts`)
- **Status**: Implemented & active.
- **Polygons**: Renders 41 district polygons via `GeoJsonLayer`, colored by PEPC AQI tier with 1px borders.
- **Diagonal Hatching**: Generates 45-degree diagonal cross-hatching paths rendered via `PathLayer` for districts where `d.isEstimated === true`.
- **Greedy AABB Labels**: Evaluates label placement across 12 candidate offsets (`LABEL_CANDIDATE_OFFSETS`) using AABB bounding box collision checks (`checkAabbCollision`). Renders `LineLayer` leader lines when offset exceeds 20px threshold (`LEADER_LINE_THRESHOLD_PX`). Renders text labels via `TextLayer`.

### 5.4 Layer 3: Wind Vectors (`WindLayer.ts`)
- **Status**: Implemented & active.
- **Station 172 Wazirabad Blacklist**: Evaluated via `isStationBlacklisted(st.id)`. Station 172 is hard-blocked from active arrow rendering and placed into `wind-blacklisted-badges` with crimson fill (`[192, 0, 0, 230]`) and hover tooltip `"ANEMOMETER BLACKLISTED (VANE OFFSET)"`.
- **Active Vectors**: Polar/Cartesian wind arrows with physical speed clamp ($\le 30$ m/s) rendered via `PathLayer`.
- **Calm Exclusion**: Winds $< 0.50$ m/s rendered as distinct open circles (`ScatterplotLayer` with `filled: false, stroked: true`).
- **Telemetry Dropouts**: Airport/station null telemetry dropouts rendered as neutral gray glyphs (`[100, 116, 139, 120]`).

### 5.5 Layer 4: Advection Flux & Border Chevrons (`FluxLayer.ts`)
- **Status**: Implemented & active.
- **Physical Dimension Guard**: When `pollutant === 'AQI'`, the calculation locks to PM2.5 mass values (`effectiveValues = pm25Values`).
- **Top 60 Truncation**: Pairwise flux calculated with $d \le 180$ km, cone $\le 35^\circ$, and exponential decay ($L_S = 100$ km), sorted and truncated to the top 60 links.
- **39 Border Chevrons**: Evaluates border normal vector dot product $\Phi_j = \mathbf{w}_j \cdot \mathbf{n}_j$ across 39 border nodes. Inflow ($\Phi_j > +0.25$ m/s) renders statutory crimson chevrons (`#C00000`). Outflow ($\Phi_j < -0.25$ m/s) renders teal chevrons (`#5fc4c4`).
- **Notice on ArcLayer**: Rendered using Deck.gl `ArcLayer`. In planimetric pitch-0 view, 3D arcs appear as straight line segments rather than 2D planar curves.

### 5.6 Layer 5: Stations & Aerodromes (`StationLayer.ts`)
- **Status**: Implemented & active.
- **Fixed Stations**: 74 fixed monitoring stations rendered as squares (`PolygonLayer`, $8\text{px} \times 8\text{px}$).
- **Mobile Stations**: 5 mobile AQMS vans rendered as diamonds (`PolygonLayer`).
- **Aerodromes**: 6 airport METAR stations rendered as crosshairs (`PathLayer`).
- **13 Lahore Stations**: All 13 Lahore stations are mapped and receive distinct interactive hitboxes (`ScatterplotLayer` with picking radius 8px).

---

## 6. Component Functionality & Interaction Audit

### 6.1 Zone 1: Top Command Bar (`CommandBar.tsx`)
- **System Identity & Stream Badge**: Displays system title, subtitle, stream mode (`LIVE SSE` vs `BASELINE FALLBACK`), and dynamic station counter (`74 Fixed · 5 Mobile`).
- **9-Pollutant Switcher**: Radio tabs switching between `AQI`, `PM2.5`, `PM10`, `NO2`, `SO2`, `CO`, `O3`, `NO`, `NOx`.
- **Hazardous ARIA Alert**: Assertive `role="alert"` and `aria-live="assertive"` badge triggers when PM2.5 > 350 (`HAZARDOUS: PEPC 500 CEILING CLAMP ACTIVE`).
- **QA Diagnostics Drawer**: Opens slide-over sheet displaying 8 diagnostic lines (stream type, horizon, completeness, spike counts, logger holds, blacklist status, inflow node counts).
- **CSV Ingestion Modal (`CSVIngestModal.tsx`)**: Multipart upload to `POST /api/v1/ingest/csv` with `allow_missing_coords` toggle, client-side validation, error summary, and `#csvQuarantineArea` dead-letter quarantine table.
- **DEFECT 1 — Missing Ingestion State Re-fetch**:
  In `App.tsx` lines 241–251, `onIngestFile` uploads the CSV and writes `setCsvFeedback`, but does NOT re-fetch `/api/v1/observations/current` or update the active workstation `baseline` state. Ingested data is invisible on the dashboard until manual page reload.
- **DEFECT 2 — Broken Theme Switcher**:
  `ThemeSwitch` calls `setTheme` in `ThemeProvider`. In `src/context/theme-provider.tsx` lines 49–50:
  ```ts
  root.classList.remove('light', 'dark');
  root.classList.add(next);
  ```
  It adds class `light` to `<html>`, but `src/styles/tokens.css` defines overrides using the attribute selector:
  ```css
  [data-theme="light"], :root[data-theme="light"] { ... }
  ```
  Because `root.setAttribute('data-theme', next)` is never called, light mode CSS variables never take effect.

### 6.2 Zone 2: Spatial Control Dock (`SpatialDock.tsx`)
- **5-Layer Toggles**: Active count badge (`X/5 Active`) and 5 toggle switches (`surface`, `choropleth`, `wind`, `flux`, `stations`).
- **Attribution Split Bar**: Dynamic domestic vs inflow percentage split bar and active inflow chevron count.
- **41-District Statutory Ranking Table**: Renders all 41 districts with rank, name, `EST` badge for unmonitored districts, and PEPC tier badge. Filterable via search input.
- **DEFECT 3 — Missing Map Centering**:
  When a district row is clicked, `onSelectDistrict(d.id)` in `App.tsx` only updates `selected` state. It does NOT call `mapRef.current?.flyTo([district.longitude, district.latitude])`. The map does not center on the selected district.

### 6.3 Zone 4: Receptor Inspector (`ReceptorInspector.tsx`)
- **Receptor Header**: Displays entity type, name, coordinates, composite AQI, and PEPC qualitative category badge.
- **Wazirabad Blacklist Banner**: Renders red alert banner (`ANEMOMETER BLACKLISTED (VANE OFFSET)`) when Station 172 is inspected.
- **Aerodrome Wind Readout**: Differentiates `TELEMETRY DROPOUT (NULL)` vs `AERODYNAMIC CALM (< 0.50 m/s)` vs active velocity.
- **Statutory Sub-Index Table**: Displays all 9 pollutants with PEQS multiple and governing pollutant badge (`governing`).
- **75% Completeness Rule**: Displays `≥75% VALID` (outline) or `<75% INCOMPLETE` (destructive badge).
- **16-Sector CPF Polar Rose**: Renders 16 cardinal/intercardinal sectors with $P_{75}$ threshold, null hypothesis circle at 0.25, calm hour exclusion count, and **suppresses rendering with dashed stroke when $N_k < 6$**.
- **216h QC Sparkline**: Time-series sparkline with crimson points (`#C00000`) for 7h median spikes and orange points (`#FF9933`) for 3h logger holds.

### 6.4 Zone 5: Precision Scrubber (`TimelineScrubber.tsx`)
- **Transport Controls**: Skip Back (1h), Play/Pause, Skip Forward (1h), playback speed selector (`1x`, `2x`, `4x`, `8x`).
- **Keyboard Shortcuts**: Spacebar toggles playback; Arrow Left / Right steps $\pm 1$ hour (guarded against input fields).
- **Max AQI Horizon Sparkline**: SVG sparkline displaying peak provincial AQI across 216 hours.
- **Continuous Sub-Hourly Lerp**: Slider supporting fractional hour positions ($fp \in [0.00, 215.00]$) and PKT clock readout.
- **DEFECT 4 — High-Frequency State Tearing / Re-render Churn**:
  In `App.tsx` lines 142–162:
  ```tsx
  setHourIndex(hour);
  setLerpAlpha(alpha);
  ```
  The 60 FPS animation loop calls React state setters on every frame, triggering a full re-render of `App.tsx`, invoking `assemble(baseline, ui)` (which iterates over all districts, stations, QC filters, and CPF calculations), and regenerating a 26,250-cell canvas IDW bitmap on every frame. This causes high CPU usage and frame stutter on high-DPI displays, violating `UI_UX_SPECIFICATION.md §4.1` (which mandates decoupling the high-frequency animation loop from the React component tree).

---

## 7. State Model Inconsistencies & AI Slop Audit

1. **Non-Statutory Indian AQI Scale in `src/workstation/state.ts`**:
   Lines 129–137 of `src/workstation/state.ts`:
   ```ts
   const LEGEND: LegendTier[] = [
     { label: 'Good 0–50', hex: '#009966', min: 0, max: 50 },
     { label: 'Satisfactory 51–100', hex: '#58B947', min: 51, max: 100 },
     { label: 'Moderate 101–200', hex: '#FFDE33', min: 101, max: 200 },
     { label: 'Poor 201–300', hex: '#FF9933', min: 201, max: 300 },
     { label: 'Very Poor 301–400', hex: '#CC0033', min: 301, max: 400 },
     { label: 'Severe 401–499', hex: '#901530', min: 401, max: 499 },
     { label: 'Hazardous 500+', hex: '#C00000', min: 500, max: 500 },
   ];
   ```
   - Labels "Poor", "Very Poor", "Severe" and colors `#009966`, `#58B947`, `#FFDE33`, `#CC0033`, `#901530` are Indian CPCB standard, NOT Punjab EPA (PEPC) standard!
   - Official PEPC categories in `src/domain/math/pepc_aqi.ts` and `src/styles/tokens.css` are:
     * Good (`#00B050`, 0–50)
     * Satisfactory (`#92D050`, 51–100)
     * Moderate (`#FFFF00`, 101–150)
     * Unhealthy for Sensitive Groups (`#ED7D31`, 151–200)
     * Unhealthy (`#FF0000`, 201–300)
     * Very Unhealthy (`#7030A0`, 301–400)
     * Hazardous (`#C00000`, 401–500+)
2. **Bypassed SSE Stream Service (`src/services/sse.ts`)**:
   - `src/services/sse.ts` provides a robust `LiveStreamManager` class implementing a 45s silent TCP drop watchdog, jittered exponential backoff, and fallback transition.
   - However, `App.tsx` line 99 uses a naive, unmanaged `new EventSource('/api/v1/stream/live')` without watchdog or backoff.
3. **Dead Code**:
   - `flyToLahore` in `src/map/MapCanvas.tsx` is defined on `MapHandle` but never exposed or invoked in the workstation UI.

---

## 8. Concrete, Step-by-Step Remediation Plan

To bring the frontend to full production-grade compliance with zero slop, the Worker agent must execute the following remediation steps:

### Step 1: Enforce Rigid 5-Zone CSS Grid & Eliminate Uncompiled Tailwind Classes
1. In `src/styles/grid.module.css`:
   - Ensure classes for `.workstation`, `.commandBar`, `.spatialDock`, `.mapCanvas`, `.receptorInspector`, `.temporalScrubber` are exported and defined with standard CSS variables.
2. In `src/workstation/WorkstationView.tsx`:
   - Import `gridStyles from '../styles/grid.module.css'`.
   - Replace the outer `<div className="flex h-screen ...">` and the intermediate wrapper with the direct 5-zone grid structure:
     ```tsx
     <div className={gridStyles.workstation}>
       <CommandBar ... className={gridStyles.commandBar} />
       <SpatialDock ... className={gridStyles.spatialDock} />
       <main id="map-canvas" data-zone="map-canvas" className={gridStyles.mapCanvas}>
         ...
       </main>
       <ReceptorInspector ... className={gridStyles.receptorInspector} />
       <TimelineScrubber ... className={gridStyles.temporalScrubber} />
     </div>
     ```
3. Remove uncompiled Tailwind utility classes from `src/components/*` or define a lightweight scoped CSS module / standard CSS rule set for panels, badges, and buttons that respects `--border-hairline`, `--bg-panel`, and `--ink-primary`.

### Step 2: Fix Ghost Dependencies in `package.json`
- Add the required Radix UI dependencies to `package.json` dependencies:
  - `@radix-ui/react-dialog`
  - `@radix-ui/react-dropdown-menu`
  - `@radix-ui/react-scroll-area`
  - `@radix-ui/react-select`
  - `@radix-ui/react-separator`
  - `@radix-ui/react-slider`
  - `@radix-ui/react-slot`
  - `@radix-ui/react-switch`
  - `@radix-ui/react-tabs`
  - `@radix-ui/react-tooltip`

### Step 3: Fix Theme Switcher (`data-theme="light"`)
- In `src/context/theme-provider.tsx`:
  - When `apply(next)` is called, execute `root.setAttribute('data-theme', next);` in addition to modifying classes.
  - In `src/components/theme-switch.tsx`:
    - Remove `rounded-full` from the button class (use `rounded-none`).
    - Update `themeColor` to use `#0f1716` (dark) and `#eef1ef` (light).

### Step 4: Fix PEPC Unhealthy Text Contrast
- In `src/styles/tokens.css`:
  - For `--pepc-unhealthy: #FF0000`, set `--pepc-unhealthy-ink: #000000;` (contrast 5.25:1, passing AA) or render a high-contrast ink chip container for AAA compliance.

### Step 5: Wire Map Centering on District Selection
- In `src/App.tsx`:
  - In `onSelectDistrict`:
    ```tsx
    onSelectDistrict={(id) => {
      const district = baseline.districts[id];
      if (district && typeof district.longitude === 'number' && typeof district.latitude === 'number') {
        mapRef.current?.flyTo([district.longitude, district.latitude]);
      }
      setSelected({
        kind: 'district',
        id,
        name: id,
        latitude: district?.latitude ?? 0,
        longitude: district?.longitude ?? 0,
      });
    }}
    ```

### Step 6: Integrate `LiveStreamManager` & Ingestion Dynamic Refresh
- In `src/App.tsx`:
  - Replace the naive `new EventSource` with `LiveStreamManager` from `src/services/sse.ts`.
  - When CSV ingestion succeeds (`onSuccessMerged`), trigger a re-fetch of `/api/v1/observations/current` and dynamically re-interpolate into the active `baseline` state.

### Step 7: Decouple Scrubber Animation Loop to Prevent 60 Hz Re-render Churn
- In `src/App.tsx`:
  - Throttle React state updates (`setHourIndex`, `setLerpAlpha`) during continuous playback (e.g. update React UI at 10 Hz or on integer hour crossings, while passing high-frequency continuous lerp position directly to the map overlay via ref).

### Step 8: Clean Banned Artifacts
- Remove `shadow-sm`, `shadow-md`, `shadow-lg`, `rounded-md`, `rounded-full` from `src/components/ui/*.tsx`.
- Remove `backdrop-filter: blur(...)` and `box-shadow` from `src/frontend/dashboard.html` and `src/frontend/static/css/tokens.css`.
- Update `strokeLinecap = 'square'` in `src/components/common/icons.tsx`.
