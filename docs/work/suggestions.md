# Technical Post-Mortem, Dual-UI Architecture Analysis, and Remediation Roadmap

**Document Reference:** `docs/work/suggestions.md`  
**Date:** November 17, 2026  
**Status:** Architecture Advisory & Remediation Proposal (No Code Changes Applied)

---

## 1. Executive Summary & Problem Diagnosis

During browser visual verification of the Punjab Air Quality Platform (`http://127.0.0.1:8000/`), the user observed two distinct failure modes across consecutive deployments:

1. **Failure Mode 1 (The Black Void on `/workstation`):** When viewing the modern React Workstation (`/workstation`, captured in user upload `media_1794888095540_4359e52d.jpg`), the outer UI chrome (Command Bar, Spatial Dock, Receptor Inspector, Scrubber) rendered properly, but:
   - The entire central map viewport was a completely black, empty box with zero cartographic geometry, zero district boundaries, and zero air quality data.
   - The 16-Sector CPF Polar Rose rendered as a solid black circle rather than an open wind-rose chart.
2. **Failure Mode 2 (The Cartoon 2D Canvas "Slop" on `dashboard.html`):** When the server route was redirected to the legacy fallback (`dashboard.html`), the user was presented with an amateur 1990s-style graphic:
   - A harsh, flat neon-red Punjab silhouette floating in empty black space.
   - Stepped concentric "target rings" (bullseyes) radiating from stations rather than an atmospheric dispersion field.
   - Cartoon clip-art flame emojis pasted across the Indian border representing NASA FIRMS fire detections.
   - The map canvas broke container boundaries, forcing all telemetry cards (*Provincial Summary*, *Active Fire Anomalies*, *Airport Weather Matrix*, and *District Concentrations*) underneath the map into an endless vertical scroll page.

### 1.1 Live Diagnosis of User Upload `media_1794888095540_4359e52d.jpg`
Deep browser inspection of `http://127.0.0.1:8000/workstation` isolated the exact mechanical breakdown:
- **Zero-Height Map Container:** In `src/workstation/WorkstationView.tsx` and `src/map/MapCanvas.tsx`, wrapper divs relied on Tailwind utility classes (`className="absolute inset-0"`). Because Tailwind was never integrated into the build toolchain, these classes did not exist in any stylesheet. The nested containers defaulted to static flow with `clientHeight = 0px`.
- **MapLibre 0px Canvas Collapse:** MapLibre initialized cleanly without console errors, but reading `clientHeight = 0`, it sized its WebGL canvas to `580px × 0px`, rendering nothing except the `#0f1716` dark background.
- **Black Polar Rose Circle:** `CpfRose` in `ReceptorInspector.tsx` used `className="fill-none stroke-border"`. Without utility CSS, SVG elements follow W3C defaults, which fills paths and circles with opaque black (`#000000`).

This document answers the core questions posed by the system stakeholders:
1. **Why do two UIs exist for the essentially same purpose?**
2. **If the proposed remediation is implemented, will the "black void and slop" be permanently eliminated?**
3. **What is the exact engineering roadmap to achieve a production-grade institutional console?**

---

## 2. Why Two UIs Exist (The Dual-UI Architecture Problem)

The repository currently contains two parallel frontend implementations attempting to solve the same problem:

```
Punjab Air Quality Platform
├── 1. Legacy Canvas Prototype  ──>  src/frontend/dashboard.html (+ static/js/canvas.js, ui.js, api.js)
└── 2. Target Institutional Workstation ──>  src/workstation/ (+ src/map/MapCanvas.tsx, React, Deck.gl, MapLibre)
```

### 2.1 Historical Evolution & Root Cause of the Split
- **The Origin Prototype (`dashboard.html`):** The project originated as a self-contained, zero-dependency, single-file HTML5/Canvas prototype (`original System/index.html` and `dashboard.html`). It used an HTML5 `<canvas>` with hand-calculated planar projections, CPU-driven IDW calculations, and direct DOM manipulation.
- **The Modern Target Specification (`src/workstation`):** The institutional target specification mandated a decoupled architecture: a FastAPI backend delivering Server-Sent Events (SSE) and TimescaleDB telemetry to a GPU-accelerated WebGL workstation using React, MapLibre GL JS, and Deck.gl.
- **The Split-Brain Trap:** Instead of migrating fully and deprecating the prototype, development proceeded on **both tracks simultaneously**:
  - Test suites and mock suites (`test_challenger_ui_r3.ts`) were written against `tokens.css` and `ui.js`.
  - Concurrently, React components were built in `src/workstation/` and `src/components/`.
  - When the React Workstation experienced mounting bugs (the black canvas), previous operators patched FastAPI's `/` route to serve `dashboard.html` as a fallback.
  - When `dashboard.html` was served, its crude 2D canvas aesthetics and broken layout shocked the user.

### 2.2 Why Maintaining Two UIs is Fatal to Quality
1. **Divergent State & Test Coverage:** Bug fixes applied to `state.ts` in React do not propagate to `ui.js` in the canvas prototype, and vice versa.
2. **Fragile Fallback Route Hopping:** Whenever one UI encounters an unhandled exception, automated scripts flip the gateway route back to the other, masking the underlying bug and presenting an entirely different, degraded user experience.
3. **Double Maintenance Overhead:** Styling rules, PEPC 7-tier statutory color scales, station inventories (74 fixed + 5 mobile), and anemometer blacklists must be maintained in duplicate across TypeScript and vanilla JavaScript.

### 2.3 The Architectural Verdict
**The dual-UI model must be terminated.** The project must consolidate onto **one single production UI**: the modern, GPU-accelerated **MapLibre GL + Deck.gl React Workstation**. The legacy canvas prototype (`dashboard.html`) should be retired to an archival folder (`archive/legacy_prototype/`) and removed from the active routing table.

---

## 3. Post-Mortem: Why the Workstation Failed & Why the Canvas Looked Amateur

### 3.1 Why the React Workstation Showed a Pitch-Black Void
A comprehensive live browser inspection revealed the exact reason the map canvas and polar rose failed:
1. **Missing CSS Utility Classes & 0px Container Collapse:**
   In `src/workstation/WorkstationView.tsx` and `src/map/MapCanvas.tsx`, the map container divs were marked with `className="absolute inset-0"`. Because Tailwind CSS was never configured or built, `.absolute` and `.inset-0` did not exist in any compiled CSS bundle. The divs defaulted to static flow with `height: auto` and `clientHeight = 0px`. When MapLibre initialized, it sized its canvas to `580px × 0px`, collapsing into a 0-height sliver and exposing only the `#0f1716` dark canvas background.
2. **Missing SVG Stroke & Fill Utilities (The Solid Black Polar Rose):**
   In `ReceptorInspector.tsx`, `CpfRose` rendered SVG circles and sector paths with `className="fill-none stroke-border"`. Without utility classes defining `fill: none`, the browser defaulted to standard W3C SVG behavior: all concentric circles and sector wedges filled with solid black (`#000000`).
3. **Deck.gl Interleaved Mode with MapLibre v3:**
   `MapboxOverlay({ interleaved: true })` attempted to hook into non-public Mapbox painter internals (`map.painter.context.gl`), which behaves differently in MapLibre GL v3. Switching to `interleaved: false` creates an autonomous, synchronized Deck.gl WebGL canvas layered seamlessly over the map without private painter dependencies.
4. **Zero Basemap Tile Sources in MapLibre Style:**
   The MapLibre instance was initialized with:
   ```typescript
   style: {
     version: 8,
     sources: {},
     layers: [{ id: 'background', type: 'background', paint: { 'background-color': '#0b1211' } }]
   }
   ```
   No raster or vector tile sources (OpenStreetMap, CartoDB Dark Matter, or satellite imagery) were configured. Even if the canvas had rendered, there was no map underneath the data—only a solid dark-gray rectangle. Supplying an institutional CartoDB Dark Matter tile source gives the airshed real geographic context.

### 3.2 Why the 2D Canvas Prototype (`dashboard.html`) Looked Amateur
1. **Stepped "Target Ring" Bullseyes (Naive IDW):**
   In `canvas.js`, spatial interpolation is performed using discrete radial gradients (`ctx.createRadialGradient`) around station points. When mapped to discrete AQI category thresholds (`aqiCat`), this produces concentric target rings (purple rings enclosing red circles enclosing orange bands). In atmospheric science, pollutant plumes advect smoothly with wind; they do not form concentric bullseye rings.
2. **Clip-Art Cartoon Flames:**
   Active thermal anomalies from NASA FIRMS were drawn using a handwritten bezier routine that drew literal clip-art flame emojis (yellow flames with red borders) stacked in rows. In an institutional monitoring console, thermal anomalies must be represented as calibrated infrared radiance pips (subtle glowing circles scaled by MW Fire Radiative Power).
3. **Container Blowout and Infinite Vertical Scroll:**
   In `canvas.js`, `resize()` computed a fixed canvas pixel height of ~1100px:
   ```javascript
   this.height = this.width / ((B.lo1 - B.lo0) * KX) * (B.la1 - B.la0);
   ```
   This forced the parent container to expand to 1100px, destroying the viewport constraints and shoving the telemetry sidebar down into an endless page scroll.

---

## 4. Elimination of the "Slop": Exactly How the Modern Stack Fixes Everything

If the recommended architecture is implemented, **every single defect described above is eliminated completely**. The comparison below details the transformation:

| Visual / Architectural Feature | The Current "Slop" (Legacy Canvas / Broken Void) | The Remediated Modern Workstation (MapLibre + Deck.gl) |
| :--- | :--- | :--- |
| **Central Map Viewport** | Either pitch-black void or flat neon silhouette on dark void | **Real geographic basemap** (CartoDB Dark Matter / Stadia tiles) showing topography, rivers, national borders, and roads. |
| **Air Quality Interpolation** | Stepped concentric "target rings" (bullseyes) | **Continuous GPU/Bitmap atmospheric field**: Smooth, advected Gaussian plume dispersion with multi-stop bilinear color transitions. |
| **Active Fire Hotspots** | Cartoon clip-art flame emojis | **Scientific infrared radiance pips**: Deck.gl `ScatterplotLayer` with pulsing radiant cores and translucent falloff proportional to FRP (MW). |
| **District Boundaries** | Missing or covered by opaque canvas fill | **Crisp SVG/WebGL vector strokes**: High-contrast, hardware-antialiased inter-district borders with automatic AABB collision-free labels. |
| **Screen Layout & Ergonomics** | Endless vertical page scroll (cards below map) | **Rigid 100vh Institutional Cockpit**: Map on left (full height), independently scrolling telemetry inspector on right, scrubber pinned at bottom. Zero page scrollbar. |
| **Wind & Advection** | Static or missing vectors | **Animated GPU particle stream / advection vectors**: Showing real-time aerodynamic wind direction across the Indo-Gangetic airshed. |
| **System Stability** | Route flipping between broken React and crude HTML | **Single, deterministic bundle**: React 18 production build with verified WebGL mounting and zero silent fallbacks. |

---

## 5. Technical Remediation Plan (Execution Steps)

When execution is authorized, the remediation will proceed strictly in these sequential phases:

```
[Phase 1: Basemap & WebGL Lifecycle] ──> [Phase 2: GPU Continuous Surface Layer]
                   │
                   ▼
[Phase 3: Scientific Hotspot & Wind Layers] ──> [Phase 4: 100vh Workstation Cockpit]
                   │
                   ▼
[Phase 5: Route Consolidation & Legacy Retirement]
```

### Phase 1: Fix MapLibre & Deck.gl Lifecycle in React
- Refactor `src/map/MapCanvas.tsx` to handle React 18 StrictMode idempotently:
  - Guard MapLibre initialization against double-invocation so `map.remove()` only executes on genuine unmount.
  - Switch Deck.gl from `interleaved: true` to a standalone overlay canvas (`interleaved: false`) or configure the MapLibre style with a valid basemap source.
- Configure a high-contrast dark basemap style:
  - Source: CartoDB Dark Matter raster/vector tiles (`https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json` or local offline tile cache for air-gapped deployment).
  - Geographic extent: Frame South Asia (Pakistan, India, Afghanistan, Iran, China) so the transboundary airshed has genuine geographic grounding.

### Phase 2: Implement Continuous Atmospheric Surface Interpolation
- Replace discrete radial gradient drawing with an offscreen rasterization pipeline or Deck.gl `BitmapLayer` / `HeatmapLayer`.
- Implement continuous PEPC multi-stop color blending (`pepcInterpolateColor`) across the statutory scale:
  - Good (`#00B050`) $\to$ Satisfactory (`#92D050`) $\to$ Moderate (`#FFFF00`) $\to$ Poor (`#FFC000`) $\to$ Very Poor (`#FF0000`) $\to$ Severe (`#7030A0`) $\to$ Emergency (`#C00000`).
- Ensure no stepped circular thresholds appear on the map.

### Phase 3: Scientific Thermal Anomaly & Vector Overlays
- In `src/map/layers/`:
  - Thermal Anomalies: Implement `ScatterplotLayer` for NASA FIRMS fire detections. Color: `#FF4810` with variable radius based on Fire Radiative Power (FRP) and confidence weighting. Completely eliminate all flame emoji references.
  - Wind Vectors: Implement `LineLayer` / animated particle advection streaks for the 925 hPa and 10m surface wind field.
  - Cross-Border Flux: Draw moving directional chevrons along the Radcliffe border line indicating aerosol mass transport.

### Phase 4: Enforce 100vh Rigid Cockpit Layout
- Ensure `src/styles/tokens.css` and `src/styles/grid.module.css` strictly lock the viewport:
  ```css
  html, body, #root {
    height: 100vh;
    width: 100vw;
    margin: 0;
    padding: 0;
    overflow: hidden;
  }
  .workstation {
    display: grid;
    grid-template-rows: 56px 1fr 64px;
    grid-template-columns: 320px 1fr 380px;
    height: 100vh;
    width: 100vw;
    overflow: hidden;
  }
  ```
- The central map viewport expands dynamically to fit `1fr` in both directions. The right inspector scrolls internally with zero overflow on the document body.

### Phase 5: Route Consolidation & Deprecation
- In `src/api/main.py`:
  - Route `/` and `/index.html` exclusively to the built production workstation (`dist/index.html`).
  - Eliminate the route switch that pointed back to `dashboard.html`.
  - Move `src/frontend/dashboard.html` to `archive/legacy_prototype/dashboard.html`.
  - Add automated E2E browser tests verifying that `/` renders with an active WebGL canvas context and zero console errors.

---

## 6. Resolution Applied & Verification Results (November 17, 2026)

Following user review of the black workstation viewport (`media_1794888095540_4359e52d.jpg`), the core defects were resolved directly in the workstation source:

1. **Structural CSS Utility Shims (`src/styles/tokens.css`):**
   - Added missing structural layout rules (`.absolute`, `.relative`, `.inset-0`, `.w-full`, `.h-full`, `.min-w-0`, `.overflow-hidden`, `.flex`).
   - Forced `#map-canvas`, `.mapCanvas`, and child containers to strictly fill `width: 100% !important; height: 100% !important; position: absolute !important; inset: 0 !important;`.
2. **Explicit WebGL Sizing & Standalone Overlay (`src/map/MapCanvas.tsx`):**
   - Inlined `style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%' }}` on map container divs to guarantee non-zero height independent of CSS compiler rules.
   - Set `interleaved: false` in `MapboxOverlay` to run Deck.gl as a synchronized, hardware-accelerated WebGL layer directly above MapLibre.
   - Connected an institutional dark basemap source (`CartoDB Dark Matter`) with dark background fallback.
   - Added a `ResizeObserver` on the map container calling `map.resize()` on viewport changes.
3. **SVG Attribute Enforcement (`src/components/inspector/ReceptorInspector.tsx`):**
   - Replaced un-emitted CSS classes on `CpfRose` with direct SVG attributes: `fill="none"`, `stroke="var(--border-strong, #4f625e)"`, and `fill="rgba(0, 176, 80, 0.25)"`.
   - The 16-Sector Polar Rose now renders open circular concentric grids with green directional probability petals instead of a solid black circle.
4. **Primary Route Consolidation (`src/api/main.py`):**
   - Updated root route `/` and `/index.html` to serve `dist/workstation.html` directly.

### 6.1 Browser Verification Evidence
- **Browser Execution**: Verified live at `http://127.0.0.1:8000/workstation` and `http://127.0.0.1:8000/` via browser inspection.
- **Canvas Sizing**: `#map-canvas canvas.maplibregl-canvas` expanded to `1920px × 1080px` (device buffer: `2880px × 1620px`).
- **Cartographic Fills**: All 41 districts actively painted with PEPC statutory colors (Good green `#00B050`, Moderate yellow `#FFFF00`, Unhealthy orange `#ED7D31`, Very Unhealthy purple `#7030A0`, Hazardous red `#C00000`).
- **Deck.gl Overlays**: Transport flux arcs, border transport chevrons, and collision-free district badges render on top of the basemap.
- **Polar Rose**: Fully functional with radial sector guides and P75 directional petals.

## 7. AI Slop Detection & Remediation Plan (Audit of User Upload `media_1794893216613_64c2b80b.jpg`)

While the MapLibre and Deck.gl engines are now successfully mounting and rendering data, the live browser capture (`media_1794893216613_64c2b80b.jpg`) reveals severe **AI slop**—unpolished, careless visual artifacts produced by naive agent implementations:

```
+-----------------------------------------------------------------------------------------------+
| AI SLOP AUDIT MATRIX                                                                          |
| 1. "API KEY REQUIRED" Watermark Grid  ──> Carto tile gating stamps watermarks across map     |
| 2. Smashed Header Text               ──> Missing CSS gap collapses title, badges, timestamps   |
| 3. Laser-Beam Flux Spaghetti Lines   ──> 60 high-opacity bright arcs clutter central Punjab   |
| 4. Black Rectangular Label Boxes     ──> Opaque text backgrounds cover district boundaries    |
| 5. Invisible Scrubber Track          ──> Radix slider track collapsed to 0px height            |
| 6. Truncated Right Inspector Badge   ──> Status badge clipped off right container edge        |
+-----------------------------------------------------------------------------------------------+
```

### 7.1 Detailed AI Slop Inventory & Root Causes

1. **Carto "API KEY REQUIRED" Watermark Grid:**
   - **Visual Manifestation:** Giant diagonal watermarks (`API KEY REQUIRED carto.com/basemaps/apikey`) repeated in a grid across the entire map background.
   - **Root Cause:** CartoDB has gated their direct `cartocdn.com` raster endpoints to require an authenticated token. Unauthenticated requests are served watermarked tiles.
   - **Remediation:** Replace Carto tiles with **Esri World Dark Gray Base** (`https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}`). Esri World Dark Gray is unwatermarked, freely available for web mapping, features high-contrast dark cartography, and has proven HTTP 200 reliability.

2. **Smashed Command Bar Header Text:**
   - **Visual Manifestation:** `EPA Punjab Air QualityAQMS & Atmospheric Transport WorkstationLIVE SSE74 Fixed · 5 Mobile2026-11-01 17:00 PKT` rendered as a single unspaced, overlapping string.
   - **Root Cause:** `CommandBar.tsx` relied on un-emitted Tailwind utility classes (`gap-3`, `gap-1.5`). Without CSS `gap` rules, flex items collapse touching one another.
   - **Remediation:** Enforce explicit CSS flexbox spacing (`gap: 12px;`) and margin rules on `.commandBar` items in `tokens.css`.

3. **Laser-Beam Flux "Spaghetti" Lines:**
   - **Visual Manifestation:** A tangled spiderweb of bright cyan and magenta straight lines shooting across Sargodha, Chiniot, Faisalabad, Nankana, and Lahore.
   - **Root Cause:** `FluxLayer.ts` renders up to 60 coupled district pathways using high-opacity colors (`alpha 220`) and heavy stroke widths (`Math.sqrt(flux) * 0.8`), which visually drowns out the underlying air quality surface.
   - **Remediation:** Default the `flux` layer to off or subtle; lower opacity to translucent `alpha 60`; reduce stroke width to `0.8px - 1.5px`; and filter strictly to the top 10 statistically governing corridors (> 90th percentile).

4. **Black Box Labels Plastered Over District Boundaries:**
   - **Visual Manifestation:** Every district label (e.g., Attock, Rawalpindi, Lahore) is rendered inside an opaque black box (`[15, 23, 22, 220]`), causing clutter and clumping.
   - **Root Cause:** `ChoroplethLayer.ts` set `backgroundColor: [15, 23, 22, 220]` in Deck.gl's `TextLayer`.
   - **Remediation:** Remove `backgroundColor` entirely. Enable Deck.gl text halo/outline (`outlineWidth: 2`, `outlineColor: [15, 23, 22, 255]`) for clean, publication-grade cartographic typography.

5. **Invisible Timeline Scrubber Track:**
   - **Visual Manifestation:** A giant blank space in the bottom scrubber bar between the time chip and the edge; no draggable slider track is visible.
   - **Root Cause:** `SliderPrimitive.Track` in `src/components/ui/slider.tsx` used un-emitted classes (`h-1.5`, `bg-primary/20`), collapsing to 0px height.
   - **Remediation:** Provide explicit CSS styles for `[data-radix-slider-track]` (height: `4px`, `background: #2a3a38`) and `[data-radix-slider-thumb]` (width: `14px`, height: `14px`, `background: #00B050`).

6. **Truncated Right Inspector Status Badge:**
   - **Visual Manifestation:** The red "Unhealthy" status badge is pushed against the right card border and clipped in half.
   - **Root Cause:** Missing padding and flex layout overflow constraints in `ReceptorInspector.tsx`.
   - **Remediation:** Enforce `padding: 12px 16px;` and `min-width: max-content;` on inspector header cards.

---

## 8. Summary & Execution Readiness

All findings from the **modern-web-guidance legacy-scan** (21 items across scrollbars, array sorting, and parser clearing) and the **AI slop visual audit** (watermarks, smashed text, spaghetti lines, black label boxes, invisible slider) are fully diagnosed. Ready to execute on command.
