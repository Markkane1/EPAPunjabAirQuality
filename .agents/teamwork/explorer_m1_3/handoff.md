# Milestone 1 Investigation Report: Workstation Layout Shell, HTML Entrypoint, and Shared TypeScript Domain Contracts

**Agent**: `explorer_m1_3`  
**State Folder**: `c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\explorer_m1_3`  
**Date**: 2026-11-11  
**Status**: COMPLETE  

---

## 1. Observation

### 1.1 Five-Zone Rigid Workstation Layout Architecture
1. **Specification Constraints (`PROJECT.md` lines 6, 28, 43, 58–60, 89; `ORIGINAL_REQUEST.md` lines 19–20, 30–37; `sub_orch_m1/SCOPE.md` lines 4–6, 18–20, 38–42)**:
   - "Build a rigid 100vw x 100vh CSS Grid five-zone workstation interface using strictly scoped CSS Modules backed by WCAG 2.1 AAA tokens in `src/styles/tokens.css` (>= 7.0:1 contrast)."
   - "Five discrete zones:
     - Zone 1: Command Bar (top) — grid area `command-bar`
     - Zone 2: Spatial Control Dock (left) — grid area `spatial-dock`
     - Zone 3: Central Map Canvas (center) — grid area `map-canvas`
     - Zone 4: Receptor Inspector (right) — grid area `receptor-inspector`
     - Zone 5: Temporal Playback Scrubber (bottom) — grid area `temporal-scrubber`"
   - Rigid layout rule: Viewport container must be strictly `100vw` by `100vh` with `overflow: hidden`, guaranteeing zero window-level scrollbars, zero bounce, and 60 FPS planimetric map operations.
   - Panel boundaries: Panels must have internal scrolling (`overflow-y: auto`, `overflow-x: hidden`), 1px solid structural hairlines (`border: 1px solid var(--border-hairline)`), and 0px border-radius (`border-radius: 0px`).

2. **Dimensional Allocations**:
   - `command-bar`: Fixed height `52px` (min/max 52px, spans 100vw full width across 3 columns). Accommodates system identity, live stream vs. baseline indicator, assertive ARIA live alerts, 9-pollutant statutory switcher, and CSV upload action.
   - `spatial-dock`: Fixed width `320px` (min 300px, max 340px, height `1fr`). Accommodates 5-layer toggles, transboundary mass-balance attribution split bar, and 41-district statutory ranking table.
   - `map-canvas`: Fluid `1fr` width and `1fr` height. Positioned relative with `overflow: hidden` for 2D planimetric MapLibre GL canvas + interleaved Deck.gl `MapboxOverlay`.
   - `receptor-inspector`: Fixed width `380px` (min 360px, max 400px, height `1fr`). Accommodates station/district metadata, 9-parameter sub-index QA table with 75% completeness enforcement, 16-sector CPF polar rose with small-sample suppression ($N_k < 6$), and 216-hour QC time-series sparkline.
   - `temporal-scrubber`: Fixed height `68px` (min/max 68px, spans 100vw full width across 3 columns). Accommodates 216-hour baseline slider (2026-11-01 00:00 to 2026-11-09 23:00), playback transport controls, horizon sparkline of provincial max AQI, and PEPC continuous legend.

### 1.2 HTML Entrypoint Requirements (`index.html`)
1. **Mandatory Directives (`ORIGINAL_REQUEST.md` line 51, 53; `PROJECT.md` line 55; `sub_orch_m1/SCOPE.md` lines 7–8, 17)**:
   - Root document must have `<meta charset="UTF-8">` and `<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">`.
   - Document title must strictly exclude all emojis: `EPA Punjab Air Quality Workstation - Atmospheric Monitoring Console`.
   - Google Fonts links must load exclusively `IBM Plex Sans`, `IBM Plex Sans Condensed`, and `IBM Plex Mono` (weights 400, 500, 600, 700; including italic variants for scientific notation).
   - Root DOM mount node: `<div id="root"></div>`.
   - Script entrypoint: `<script type="module" src="/src/main.tsx"></script>`.
   - Prior `src/frontend/dashboard.html` loaded non-conforming fonts (`Barlow Condensed`, `Source Sans 3`, `JetBrains Mono`) and had UTF-8 encoding corruptions (`Â·`, `â— `).

### 1.3 Empirical Baseline Data Structures & Schema Traps
Direct inspection of `data/baseline/` and `src/domain/entities/models.py` reveals the exact shape of raw records and proves the 5 schema traps:

1. **Schema Trap 1 (Centroid Inversion)**:
   - In `data/baseline/districts.json`:
     ```json
     {
       "id": "1",
       "name": "Attock",
       "centroid": [33.669, 72.501],
       "label": [72.425, 33.501],
       "boundary": [[[72.435, 34.002], ...]]
     }
     ```
   - Direct proof: `centroid` is `[33.669, 72.501]` which is `[lat, lon]`. In contrast, `label` is `[72.425, 33.501]` and `boundary` vertices are `[72.435, 34.002]`, both already in standard GeoJSON `[lon, lat]` order. Centroids MUST be inverted to `[lon, lat]` (`[centroid[1], centroid[0]]`) before passing to deck.gl or geospatial functions.

2. **Schema Trap 2 (Aerodrome Null vs Calm)**:
   - In `data/baseline/airports.json`:
     - OPLA: 37 `null` values and 36 `0` values in wind array `u`.
     - VIAR: 57 `null` values and 57 `0` values in wind array `u`.
   - Direct proof: `null` represents a sensor telemetry dropout (rendered as missing dropout glyph). In contrast, speeds $0.0 \le w_s < 0.50\ \text{m/s}$ represent aerodynamic calm (rendered as a calm circle glyph). Speeds $\ge 0.50\ \text{m/s}$ represent active directional wind vectors.

3. **Schema Trap 3 (Station 172 Wazirabad Blacklist)**:
   - In `data/baseline/stations.json`:
     ```json
     {
       "id": "172",
       "name": "Wazirabad",
       "district": "Wazirabad",
       "latitude": 32.320458,
       "longitude": 73.956272,
       "qa_summary": { "n": 216, "wind_valid": 0 }
     }
     ```
   - Direct proof: Station 172 has `wind_valid: 0` because of a permanent $140^\circ$ physical vane misalignment. Its wind vectors must be hard-blocked from map rendering and tagged as `ANEMOMETER BLACKLISTED (VANE OFFSET)`.

4. **Schema Trap 4 (Dynamic Station Counts)**:
   - In `data/baseline/stations.json`:
     - Total stations: 79
     - Fixed stations: 74 (`mobile: false` or `network_type: 'fixed'`)
     - Mobile stations: 5 (`mobile: true` or `network_type: 'mobile'`)
     - Lahore stations: 13 (`district: 'Lahore'` or `d: 'Lahore'`)
   - Direct proof: Station counts must be calculated dynamically from the active station record set rather than hardcoded.

5. **Schema Trap 5 (Estimation Flag Unification & Hatching)**:
   - In `data/baseline/districts.json`:
     - Districts contain both `est: boolean` and `is_monitored: boolean`.
     - Unmonitored districts (where `!is_monitored` or `est === true`) require geostatistical imputation (T1 Discrete IDW) and diagonal cross-hatch rendering on choropleth polygons.
   - Direct proof: These flags must be unified into a single canonical boolean: `is_estimated: boolean = !d.is_monitored || Boolean(d.est)`.

### 1.4 Mathematical & Physical Domain Entities
1. **Statutory Pollutants (`TRANSFORMATION_LOGIC_SPEC.md §2.9`)**:
   - 9 statutory parameters: `AQI`, `PM2.5`, `PM10`, `NO2`, `SO2`, `CO`, `O3`, `NO`, `NOX`.
   - Particulate-governed composite index: $\text{AQI}_{\text{composite}} = \max(I_{\text{PM2.5}}, I_{\text{PM10}})$. Gaseous pollutants are evaluated against PEQS independently.
   - Operational clamp: When $\text{PM}_{2.5} > 350.0\ \mu\text{g/m}^3$, $\text{AQI}$ is clamped to 500.

2. **PEPC Statutory 7-Tier AQI Scale**:
   - Tier 0: Good ($0 - 50$, `#00B050`, text `#000000`)
   - Tier 1: Satisfactory ($51 - 100$, `#92D050`, text `#000000`)
   - Tier 2: Moderate ($101 - 150$, `#FFFF00`, text `#000000`)
   - Tier 3: Unhealthy for Sensitive Groups ($151 - 200$, `#ED7D31`, text `#000000`)
   - Tier 4: Unhealthy ($201 - 300$, `#FF0000`, text `#FFFFFF`)
   - Tier 5: Very Unhealthy ($301 - 400$, `#7030A0`, text `#FFFFFF`)
   - Tier 6: Hazardous ($401+$, `#C00000`, text `#FFFFFF`)

3. **Transboundary Border Nodes (`TRANSFORMATION_LOGIC_SPEC.md §2.8`)**:
   - `data/baseline/baseline_data.json` contains `tbgeo.samples` with 39 border nodes along the 1,100 km Pakistan-India border: `[lon, lat, nx, ny]`.
   - Inward normal vector dot product: $\Phi_j(t) = u_j(t) \cdot nx_j + v_j(t) \cdot ny_j$.
   - When $\Phi_j > +0.25\ \text{m/s}$: Transboundary Inflow (triggers animated crimson chevrons).
   - When $\Phi_j < -0.25\ \text{m/s}$: Transboundary Outflow (triggers teal chevrons).

4. **Advection Flux Mass Transport (`TRANSFORMATION_LOGIC_SPEC.md §2.6 & §2.7`)**:
   - Physical mass flux: $\text{Flux}_{a \to b} = C_a w_a \cos(\Delta\theta) \exp(-d_{ab}/100)$ with $d \le 180\ \text{km}$, cone $\le 35.0^\circ$, $w_a \ge 0.5\ \text{m/s}$.
   - **Physical Dimension Guard**: Strictly disabled when `pollutant === 'AQI'`. When AQI is selected in the UI, flux calculations lock to $\text{PM}_{2.5}\ (\mu\text{g/m}^3)$ with an explanatory banner.
   - Receptor coupling score: $\text{Score} = \overline{\text{Flux}} \times \Omega$ ($\Omega = 0.25$ fallback for unmonitored or $N_k < 6$). Truncated strictly to top 60 links.

5. **16-Sector CPF Polar Wind Rose (`TRANSFORMATION_LOGIC_SPEC.md §2.5`)**:
   - Calm exclusion: $w_s < 0.50\ \text{m/s}$ excluded.
   - Pooled station-hours $P_{75}$ threshold.
   - Small-sample suppression rule: If sector hours $N_k < 6$, $\text{CPF}_k = \text{null}$ and renders as a neutral muted circular stub.

6. **Temporal QC Filters (`TRANSFORMATION_LOGIC_SPEC.md §2.10`)**:
   - Zero-purge step: $\le 0 \to \text{null}$.
   - 7-hour rolling median spike filter: $v_i > 4.0 M_i \land v_i > 3.0 \text{ref}_p$.
   - 3-hour logger hold filter: $i \ge 2 \land v_i = v_{i-1} = v_{i-2}$ (AQI exempt).
   - 75% completeness rule: $\ge \max(1, \text{round}(0.75 \times H))$ valid observations.

---

## 2. Logic Chain

1. **Premise 1 (Layout Stability)**: Institutional monitoring during severe smog emergencies requires zero visual shifting or unexpected window scrolling.
   - *Connecting Observation*: Obs 1.1 dictates a rigid 100vw x 100vh CSS Grid container with 5 named grid areas (`command-bar`, `spatial-dock`, `map-canvas`, `receptor-inspector`, `temporal-scrubber`).
   - *Inference*: Using CSS Grid with fixed header (`52px`), fixed footer (`68px`), fixed sidebars (`320px` left, `380px` right), and fluid center (`1fr 1fr`) ensures the MapLibre/Deck.gl canvas has deterministic pixel bounds at all times.

2. **Premise 2 (Typography & Style Isolation)**:
   - *Connecting Observation*: Obs 1.2 mandates exclusively IBM Plex typography, tabular-nums for numeric readouts, and scoped CSS Modules.
   - *Inference*: `src/styles/grid.module.css` localizes grid classes, preventing global CSS leakage. Enforcing `font-variant-numeric: tabular-nums` globally eliminates layout jitter as timeline numbers tick rapidly during 60 FPS playback.

3. **Premise 3 (Domain Contract Exactness)**:
   - *Connecting Observation*: Obs 1.3 reveals 5 subtle schema traps (centroid inversion, aerodrome nulls vs. calms, Wazirabad blacklist, dynamic station counts, estimation flags).
   - *Inference*: The TypeScript contracts in `src/domain/types/index.ts` must explicitly model these edge cases. For instance, `WindVector` must support 4 distinct states (`'active' | 'calm' | 'dropout' | 'blacklisted'`), and `NormalizedDistrict` must type `centroid` as `LngLat` (`[lon, lat]`).

4. **Premise 4 (Cross-Milestone Contract Cohesion)**:
   - *Connecting Observation*: M1 feeds directly into M2 (Normalizer & Physics), M3 (Deck.gl Canvas), M4 (UI Components), and M5 (Backend Ingestion & SSE).
   - *Inference*: Providing exhaustive TypeScript interfaces in M1 eliminates type discrepancies downstream. All transforms T1–T11, deck.gl layers, and API responses can be typed against this single canonical file.

---

## 3. Caveats

1. **Deck.gl & MapLibre Canvas Mount in M1**:
   - The map canvas in `src/App.tsx` contains placeholder DOM structures (`#mapLibreCanvas`, `#deckOverlay`). Full WebGL context initialization and MapboxOverlay integration belong to Milestone 3.
2. **Dynamic Data Fetching**:
   - Data loading services (`api.ts`, `sse.ts`, `fallback.ts`) are implemented in Milestone 5. Milestone 1 establishes the structural shell and domain contracts that these loaders will fulfill.
3. **Responsive Mobile Breakpoints**:
   - The workstation is designed specifically as an institutional desktop monitoring console (target screens $\ge 1280 \times 720$). While responsive CSS flex/grid rules can degrade gracefully on narrower screens, the primary architecture targets 100vw x 100vh desktop workstations.
4. **No Direct Source Changes by Explorer**:
   - In accordance with the Explorer archetype rules, these exact specifications are written to this report for `worker_m1` to implement directly.

---

## 4. Conclusion & Concrete Specifications

The following concrete, complete specifications are ready for drop-in implementation by `worker_m1`:

### 4.1 HTML Entrypoint (`index.html`)

```html
<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
  <title>EPA Punjab Air Quality Workstation - Atmospheric Monitoring Console</title>
  
  <!-- Preconnect to Google Fonts -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  
  <!-- Institutional Typography: Exclusively IBM Plex Sans, IBM Plex Sans Condensed, IBM Plex Mono -->
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:ital,wght@0,400;0,500;0,600;0,700;1,400&family=IBM+Plex+Sans+Condensed:ital,wght@0,400;0,600;0,700;1,400;1,600&family=IBM+Plex+Sans:ital,wght@0,400;0,500;0,600;0,700;1,400&display=swap">
  
  <!-- MapLibre GL CSS -->
  <link rel="stylesheet" href="https://unpkg.com/maplibre-gl@3.6.2/dist/maplibre-gl.css">
</head>
<body>
  <div id="root"></div>
  <script type="module" src="/src/main.tsx"></script>
</body>
</html>
```

---

### 4.2 Scoped Grid CSS Module (`src/styles/grid.module.css`)

```css
/* ==========================================================================
   EPA Punjab Air Quality Workstation - Rigid 5-Zone CSS Grid Container
   Enforces 100vw x 100vh with zero window-level scrollbars and 1px hairlines.
   ========================================================================== */

.workstation {
  display: grid;
  width: 100vw;
  height: 100vh;
  margin: 0;
  padding: 0;
  overflow: hidden;
  box-sizing: border-box;
  background-color: var(--bg-canvas, #0f1716);
  color: var(--ink-primary, #e3ece9);
  font-family: var(--font-sans, "IBM Plex Sans", -apple-system, sans-serif);
  
  /* 3 Rows: Command Bar (52px), Workstation Main (1fr), Temporal Scrubber (68px) */
  grid-template-rows: 52px 1fr 68px;
  
  /* 3 Columns: Spatial Dock (320px), Map Canvas (1fr), Receptor Inspector (380px) */
  grid-template-columns: 320px 1fr 380px;
  
  /* 5 Canonical Grid Areas */
  grid-template-areas:
    "command-bar command-bar command-bar"
    "spatial-dock map-canvas receptor-inspector"
    "temporal-scrubber temporal-scrubber temporal-scrubber";
}

/* Zone 1: Top Command Bar */
.commandBar {
  grid-area: command-bar;
  height: 52px;
  min-height: 52px;
  max-height: 52px;
  box-sizing: border-box;
  border-bottom: var(--border-hairline, 1px solid #2a3a38);
  background-color: var(--bg-panel, #152120);
  z-index: 20;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 var(--space-md, 16px);
  overflow: hidden;
}

/* Zone 2: Spatial Control Dock (Left) */
.spatialDock {
  grid-area: spatial-dock;
  box-sizing: border-box;
  border-right: var(--border-hairline, 1px solid #2a3a38);
  background-color: var(--bg-dock, #131e1d);
  z-index: 10;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  overflow-x: hidden;
}

/* Zone 3: Central Planimetric Map Canvas */
.mapCanvas {
  grid-area: map-canvas;
  box-sizing: border-box;
  position: relative;
  overflow: hidden;
  background-color: var(--bg-canvas, #0f1716);
  z-index: 1;
}

/* Zone 4: Receptor Inspector (Right) */
.receptorInspector {
  grid-area: receptor-inspector;
  box-sizing: border-box;
  border-left: var(--border-hairline, 1px solid #2a3a38);
  background-color: var(--bg-inspector, #152120);
  z-index: 10;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  overflow-x: hidden;
}

/* Zone 5: Temporal Playback Scrubber (Bottom) */
.temporalScrubber {
  grid-area: temporal-scrubber;
  height: 68px;
  min-height: 68px;
  max-height: 68px;
  box-sizing: border-box;
  border-top: var(--border-hairline, 1px solid #2a3a38);
  background-color: var(--bg-panel, #152120);
  z-index: 20;
  display: flex;
  align-items: center;
  padding: 0 var(--space-md, 16px);
  overflow: hidden;
}

/* Panel Header Utility */
.panelHeader {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 36px;
  min-height: 36px;
  padding: 0 var(--space-sm, 8px);
  border-bottom: var(--border-hairline, 1px solid #2a3a38);
  background-color: var(--bg-panel-elevated, #1c2b2a);
  font-family: var(--font-condensed, "IBM Plex Sans Condensed", sans-serif);
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--ink-secondary, #c0cfcb);
}

/* Panel Content Scroll Container */
.panelBody {
  flex: 1 1 auto;
  padding: var(--space-sm, 8px);
  overflow-y: auto;
  overflow-x: hidden;
}
```

---

### 4.3 Main Layout Container Component (`src/App.tsx`)

```tsx
import React, { useState } from 'react';
import styles from './styles/grid.module.css';
import { PollutantKey, LayerId } from './domain/types';

export const App: React.FC = () => {
  const [activePollutant, setActivePollutant] = useState<PollutantKey>('AQI');
  const [layerVisibility, setLayerVisibility] = useState<Record<LayerId, boolean>>({
    surface: true,
    choropleth: true,
    wind: true,
    flux: true,
    stations: true,
  });

  return (
    <div className={styles.workstation} role="application" aria-label="EPA Punjab Air Quality Institutional Workstation">
      
      {/* Zone 1: Command Bar (Top) */}
      <header className={styles.commandBar} role="banner" aria-label="Workstation Command Bar">
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span
              style={{
                width: '8px',
                height: '8px',
                borderRadius: '0px',
                backgroundColor: 'var(--color-status-success, #34d399)',
                display: 'inline-block',
              }}
              aria-hidden="true"
            />
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', letterSpacing: '0.06em' }}>
              LIVE SYNC: ACTIVE (BASELINE FALLBACK READY)
            </span>
          </div>

          <div style={{ height: '18px', width: '1px', backgroundColor: 'var(--border-hairline, #2a3a38)' }} />

          <h1 style={{ fontSize: '15px', fontWeight: 600, margin: 0, letterSpacing: '0.02em' }}>
            EPA PUNJAB AIR QUALITY WORKSTATION
          </h1>
        </div>

        {/* Assertive ARIA Live Region for Hazardous Alerts / 500 Clamps */}
        <div
          role="status"
          aria-live="assertive"
          aria-atomic="true"
          style={{ fontFamily: 'var(--font-mono)', fontSize: '12px', color: 'var(--pepc-hazardous, #C00000)' }}
        >
          {/* Milestone 4 Alert Banners mount here */}
        </div>

        {/* 9 Statutory Pollutant Switcher Placeholder */}
        <div role="radiogroup" aria-label="Statutory Pollutant Switcher" style={{ display: 'flex', gap: '4px' }}>
          {(['AQI', 'PM2.5', 'PM10', 'NO2', 'SO2', 'CO', 'O3', 'NO', 'NOX'] as PollutantKey[]).map((pol) => (
            <button
              key={pol}
              type="button"
              role="radio"
              aria-checked={activePollutant === pol}
              onClick={() => setActivePollutant(pol)}
              style={{
                fontFamily: 'var(--font-condensed)',
                fontSize: '12px',
                fontWeight: activePollutant === pol ? 600 : 400,
                padding: '4px 8px',
                border: activePollutant === pol ? '1px solid var(--accent, #5fc4c4)' : '1px solid transparent',
                backgroundColor: activePollutant === pol ? 'var(--bg-panel-elevated, #1c2b2a)' : 'transparent',
                color: activePollutant === pol ? 'var(--ink-primary, #e3ece9)' : 'var(--ink-secondary, #c0cfcb)',
                cursor: 'pointer',
              }}
            >
              {pol}
            </button>
          ))}
        </div>
      </header>

      {/* Zone 2: Spatial Control Dock (Left) */}
      <aside className={styles.spatialDock} role="region" aria-label="Spatial Control Dock">
        <div className={styles.panelHeader}>
          <span>Spatial Controls &amp; 41 Districts</span>
        </div>
        <div className={styles.panelBody}>
          {/* Milestone 4 will mount Layer Stack Toggles, Mass-Balance Split Bar, District Ranking Table */}
          <div style={{ fontSize: '12px', color: 'var(--ink-secondary)' }}>
            <div style={{ marginBottom: '8px', fontWeight: 600 }}>ACTIVE DECK.GL LAYERS:</div>
            {(Object.keys(layerVisibility) as LayerId[]).map((layerId) => (
              <label key={layerId} style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                <input
                  type="checkbox"
                  checked={layerVisibility[layerId]}
                  onChange={(e) => setLayerVisibility({ ...layerVisibility, [layerId]: e.target.checked })}
                />
                <span style={{ textTransform: 'capitalize' }}>{layerId}</span>
              </label>
            ))}
          </div>
        </div>
      </aside>

      {/* Zone 3: Central Planimetric Map Canvas (Center) */}
      <main className={styles.mapCanvas} role="main" aria-label="Planimetric Atmospheric Map Viewport">
        <div
          id="mapLibreCanvas"
          style={{ width: '100%', height: '100%', position: 'absolute', top: 0, left: 0 }}
        >
          {/* Milestone 3 will mount strictly locked MapLibre GL instance (pitch: 0, dragRotate: false) */}
        </div>
        <div
          id="deckOverlay"
          style={{ width: '100%', height: '100%', position: 'absolute', top: 0, left: 0, pointerEvents: 'none' }}
        >
          {/* Milestone 3 will mount interleaved Deck.gl 5-layer MapboxOverlay */}
        </div>
      </main>

      {/* Zone 4: Receptor Inspector (Right) */}
      <aside className={styles.receptorInspector} role="complementary" aria-label="Receptor Inspector">
        <div className={styles.panelHeader}>
          <span>Receptor Telemetry &amp; Diagnostics</span>
        </div>
        <div className={styles.panelBody}>
          {/* Milestone 4 will mount 9-parameter sub-index table, 16-sector CPF rose, 216h QC sparkline */}
          <div style={{ fontSize: '12px', color: 'var(--ink-secondary)' }}>
            Select a station or district on the map or spatial dock to inspect detailed receptor telemetry and polar wind rose.
          </div>
        </div>
      </aside>

      {/* Zone 5: Temporal Playback Scrubber (Bottom) */}
      <footer className={styles.temporalScrubber} role="contentinfo" aria-label="Temporal Playback Controller">
        <div style={{ display: 'flex', alignItems: 'center', width: '100%', gap: '16px' }}>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: '12px', minWidth: '160px' }}>
            PKT: 2026-11-01 00:00
          </span>
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '4px' }}>
            {/* Scrubber slider and horizon sparkline placeholder */}
            <input
              type="range"
              min="0"
              max="215"
              defaultValue="0"
              style={{ width: '100%', accentColor: 'var(--accent, #5fc4c4)' }}
              aria-label="216-Hour Simulation Timeline Scrubber"
            />
          </div>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: '12px' }}>
            HOUR: 0 / 215
          </span>
        </div>
      </footer>

    </div>
  );
};
```

---

### 4.4 Bootstrap Entrypoint (`src/main.tsx`)

```tsx
import React from 'react';
import ReactDOM from 'react-dom/client';
import { App } from './App';
import './styles/tokens.css';
import './styles/typography.css';

const rootElement = document.getElementById('root');
if (!rootElement) {
  throw new Error('Fatal: #root mount element missing from index.html');
}

ReactDOM.createRoot(rootElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
```

---

### 4.5 Canonical TypeScript Domain Contracts (`src/domain/types/index.ts`)

```typescript
/**
 * EPA Punjab Air Quality Monitoring, Processing, and Visualization System
 * Canonical Shared TypeScript Domain Contracts
 *
 * Implements strict contracts covering:
 * - 9 Statutory Pollutants & Measurements
 * - 7 Official PEPC Health Tiers & Breakpoints
 * - Stations (Fixed, Mobile, Aerodrome METAR, WMO SYNOP; 13 Lahore stations)
 * - Districts (41 districts, Centroid [lon, lat], unified is_estimated flag)
 * - Wind Vector Kinematics (Active, Calm, Dropout, Station 172 Blacklist)
 * - Transboundary Border Nodes (39 nodes, normal flux dot product, crimson/teal chevrons)
 * - Advection Mass Transport Flux (Physical dimension guard: locked to PM2.5 for AQI)
 * - 16-Sector CPF Polar Wind Rose (Small-sample suppression Nk < 6, calm exclusion)
 * - Quality Control & Time Series (7h median spike, 3h logger hold, 75% rule)
 * - Workstation 5-Zone UI & Reactive State Contracts
 */

// ============================================================================
// 1. Coordinates, Spatial & Geodetic Primitives
// ============================================================================

/**
 * Standard WGS-84 coordinate tuple in GeoJSON / deck.gl order: [longitude, latitude].
 * Note: Longitude precedes Latitude in all cartographic operations.
 */
export type LngLat = [longitude: number, latitude: number];

/**
 * Legacy or tabular coordinate tuple: [latitude, longitude].
 */
export type LatLng = [latitude: number, longitude: number];

/**
 * Geographic bounding box.
 */
export interface BoundingBox {
  west: number;
  south: number;
  east: number;
  north: number;
}

// ============================================================================
// 2. Statutory Pollutants & Regulatory Limits
// ============================================================================

/**
 * The 9 statutory air pollutants recognized by the Punjab Environmental Protection Council.
 */
export type PollutantKey =
  | 'AQI'
  | 'PM2.5'
  | 'PM10'
  | 'NO2'
  | 'SO2'
  | 'CO'
  | 'O3'
  | 'NO'
  | 'NOX';

/**
 * Physical chemical pollutants (excluding the dimensionless AQI index).
 * Used to enforce the Physical Dimension Guard in advection flux calculations.
 */
export type PhysicalPollutantKey = Exclude<PollutantKey, 'AQI'>;

export type PollutantUnit = 'ug/m3' | 'mg/m3' | 'index';

export interface PollutantMetadata {
  key: PollutantKey;
  label: string;
  chemicalFormula: string;
  unit: PollutantUnit;
  peqs24hLimit?: number;
  peqs1hLimit?: number;
  peqs8hLimit?: number;
  isDimensionless: boolean;
  stepSize: number;
}

export const STATUTORY_POLLUTANTS: Record<PollutantKey, PollutantMetadata> = {
  AQI: {
    key: 'AQI',
    label: 'Punjab Composite AQI',
    chemicalFormula: 'AQI',
    unit: 'index',
    isDimensionless: true,
    stepSize: 1,
  },
  'PM2.5': {
    key: 'PM2.5',
    label: 'Fine Particulate Matter (<= 2.5 um)',
    chemicalFormula: 'PM2.5',
    unit: 'ug/m3',
    peqs24hLimit: 35.0,
    isDimensionless: false,
    stepSize: 0.1,
  },
  PM10: {
    key: 'PM10',
    label: 'Coarse Particulate Matter (<= 10 um)',
    chemicalFormula: 'PM10',
    unit: 'ug/m3',
    peqs24hLimit: 150.0,
    isDimensionless: false,
    stepSize: 0.1,
  },
  NO2: {
    key: 'NO2',
    label: 'Nitrogen Dioxide',
    chemicalFormula: 'NO2',
    unit: 'ug/m3',
    peqs24hLimit: 80.0,
    isDimensionless: false,
    stepSize: 0.1,
  },
  SO2: {
    key: 'SO2',
    label: 'Sulfur Dioxide',
    chemicalFormula: 'SO2',
    unit: 'ug/m3',
    peqs24hLimit: 120.0,
    isDimensionless: false,
    stepSize: 0.1,
  },
  CO: {
    key: 'CO',
    label: 'Carbon Monoxide',
    chemicalFormula: 'CO',
    unit: 'mg/m3',
    peqs8hLimit: 5.0,
    isDimensionless: false,
    stepSize: 0.01,
  },
  O3: {
    key: 'O3',
    label: 'Ground-Level Ozone',
    chemicalFormula: 'O3',
    unit: 'ug/m3',
    peqs1hLimit: 130.0,
    isDimensionless: false,
    stepSize: 0.1,
  },
  NO: {
    key: 'NO',
    label: 'Nitric Oxide',
    chemicalFormula: 'NO',
    unit: 'ug/m3',
    peqs24hLimit: 40.0,
    isDimensionless: false,
    stepSize: 0.1,
  },
  NOX: {
    key: 'NOX',
    label: 'Total Oxides of Nitrogen',
    chemicalFormula: 'NOx',
    unit: 'ug/m3',
    isDimensionless: false,
    stepSize: 0.1,
  },
};

// ============================================================================
// 3. PEPC Health Tiers & Continuous Piecewise Color Scale
// ============================================================================

export type PEPCGrade =
  | 'good'
  | 'satisfactory'
  | 'moderate'
  | 'unhealthy_sensitive'
  | 'unhealthy'
  | 'very_unhealthy'
  | 'hazardous';

export type PEPCTierIndex = 0 | 1 | 2 | 3 | 4 | 5 | 6;

export interface PEPCBreakpoint {
  tier: PEPCTierIndex;
  grade: PEPCGrade;
  descriptor: string;
  aqiMin: number;
  aqiMax: number;
  hexColor: string;
  rgbColor: [number, number, number];
  textColor: string;
  pm25Max: number;
  pm10Max: number;
}

export interface AQICalculationResult {
  aqi: number;
  tier: PEPCTierIndex;
  grade: PEPCGrade;
  hexColor: string;
  textColor: string;
  isClamped: boolean;
  governingPollutant: 'PM2.5' | 'PM10';
}

// ============================================================================
// 4. Monitoring Stations & Aerodromes
// ============================================================================

export type StationNetworkType = 'fixed' | 'mobile' | 'airport_metar' | 'wmo_synop';

export interface StationQASummary {
  district: string;
  n: number;
  wind_valid: number;
  AQI?: number;
  AQI_spk?: number;
  PM10?: number;
  PM10_spk?: number;
  'PM2.5'?: number;
  'PM2.5_spk'?: number;
  NO2?: number;
  NO2_spk?: number;
  SO2?: number;
  SO2_spk?: number;
  CO?: number;
  CO_spk?: number;
  O3?: number;
  O3_spk?: number;
  NO?: number;
  NO_spk?: number;
  NOX?: number;
  NOX_spk?: number;
  [key: string]: number | string | undefined;
}

/**
 * Raw station record from baseline or backend API.
 */
export interface RawStation {
  id: string;
  station_id?: string;
  numeric_id?: number;
  name: string;
  district: string;
  d?: string;
  latitude: number;
  longitude: number;
  lat?: number;
  lon?: number;
  mobile?: boolean;
  network_type?: string;
  coord_source?: string;
  qa_summary?: StationQASummary;
}

/**
 * Canonical normalized station entity.
 */
export interface NormalizedStation {
  id: string;
  name: string;
  district: string;
  coordinates: LngLat; // [lon, lat]
  latitude: number;
  longitude: number;
  stationType: StationNetworkType;
  mobile: boolean;
  isLahore: boolean;
  hasAnemometer: boolean;
  anemometerBlacklisted: boolean; // Station 172 (Wazirabad)
  altitudeM?: number;
  coordSource?: string;
  qaSummary?: StationQASummary;
}

/**
 * Airport METAR observation node.
 */
export interface AirportStation {
  id: string;
  icao: string;
  name: string;
  coordinates: LngLat;
  latitude: number;
  longitude: number;
}

// ============================================================================
// 5. Administrative Districts
// ============================================================================

/**
 * Raw district record from baseline data.
 * Notice Schema Trap 1: raw centroid is [lat, lon]!
 */
export interface RawDistrict {
  id: string;
  name: string;
  district?: string;
  latitude?: number;
  longitude?: number;
  lat?: number;
  lon?: number;
  centroid: LatLng; // [lat, lon] TRAP!
  label?: LngLat;   // [lon, lat]
  boundary?: number[][][] | number[][][][];
  polys?: number[][][];
  est?: boolean;
  is_monitored?: boolean;
  stations?: string[];
  station_count?: number;
}

/**
 * Canonical normalized district entity.
 */
export interface NormalizedDistrict {
  id: string;
  name: string;
  division?: string;
  centroid: LngLat; // Normalized to [lon, lat]!
  labelCoordinates: LngLat; // [lon, lat]
  boundary: number[][][] | number[][][][]; // GeoJSON Polygon / MultiPolygon
  polys?: number[][][];
  isMonitored: boolean;
  isEstimated: boolean; // Unified from est and !is_monitored
  stationCount: number;
  stations: string[];
  borderDistanceKm: number;
  indiaInflowSectors: number[];
}

// ============================================================================
// 6. Kinematic Wind Vectors & Anemometer States
// ============================================================================

export type WindState = 'active' | 'calm' | 'dropout' | 'blacklisted';

/**
 * Canonical wind vector representation addressing Schema Traps 2 & 3.
 */
export interface WindVector {
  state: WindState;
  speed: number | null;     // Validated speed in m/s [0.0, 30.0], or null
  direction: number | null; // Azimuth in degrees FROM [0.0, 360.0], or null
  u: number | null;         // Cartesian eastward velocity in m/s
  v: number | null;         // Cartesian northward velocity in m/s
  blacklisted: boolean;     // True for Station 172
  blacklistReason?: string; // 'ANEMOMETER BLACKLISTED (VANE OFFSET)'
}

// ============================================================================
// 7. Transboundary Border Nodes & Cross-Border Flux
// ============================================================================

export type BorderFlowState = 'inflow' | 'outflow' | 'neutral';

/**
 * One of the 39 border animation nodes along the Pakistan-India boundary.
 */
export interface BorderNode {
  index: number;
  coordinates: LngLat; // [lon, lat]
  normal: [nx: number, ny: number]; // Inward unit normal vector pointing into Punjab
  phiFlux: number | null; // Normal dot product: Phi = u * nx + v * ny
  flowState: BorderFlowState; // Inflow if Phi > +0.25 m/s, Outflow if Phi < -0.25 m/s
}

export interface TransboundaryMassBalance {
  timestamp: string;
  inflowTotal: number;
  outflowTotal: number;
  netFlux: number; // Inflow - Outflow
  easternInflowRatio: number; // 0.0 to 1.0 (Attribution Split Bar)
  domesticEmissionRatio: number; // 0.0 to 1.0
  borderNodes: BorderNode[];
}

// ============================================================================
// 8. Physical Inter-District Advection Mass Transport Flux
// ============================================================================

export interface PathwayLink {
  sourceDistrict: string;
  receptorDistrict: string;
  distanceKm: number; // <= 180.0 km
  bearingDeg: number;
  divergenceDeg: number; // <= 35.0 deg
  flux: number | null; // Null if calm < 0.50 m/s or divergence > 35 deg
  omega: number; // Receptor CPF feedback coefficient (default 0.25)
  score: number; // flux * omega
  isPM25Locked: boolean; // Physical Dimension Guard flag
}

export interface TransportBalanceSummary {
  districtName: string;
  totalExport: number;
  totalImport: number;
  netTransport: number; // Export - Import (>0 smog source, <0 receptor)
}

// ============================================================================
// 9. Conditional Probability Function (CPF) Polar Wind Rose
// ============================================================================

export interface CPFSector {
  sectorIndex: number; // 0 to 15
  azimuthDeg: number;  // 0.0 to 337.5
  cardinalLabel: string; // 'N', 'NNE', 'NE', etc.
  totalHours: number;  // Nk
  exceedanceHours: number; // mk (hours > P75)
  cpfProbability: number | null; // Null if Nk < 6 (small-sample suppression rule)
  isSuppressed: boolean; // True if Nk < 6
}

export interface CPFRoseData {
  districtName: string;
  pollutant: PollutantKey;
  p75Threshold: number; // P75 concentration threshold
  calmHours: number;    // Count of hours with ws < 0.50 m/s
  totalHours: number;   // Total valid hours
  calmRatio: number;    // calmHours / totalHours
  sectors: CPFSector[]; // Exactly 16 sectors
}

// ============================================================================
// 10. Quality Control & Time Series Inspection
// ============================================================================

export type QCFlag =
  | 'QC_EXCEEDANCE_EXTREME' // PM2.5 > 1000 or PM10 > 1500
  | 'QC_SPIKE_7H_MEDIAN'   // vi > 4 * Mi && vi > 3 * ref_p
  | 'QC_LOGGER_HOLD_3H'    // 3 identical consecutive values for i >= 2 (AQI exempt)
  | 'QC_ZERO_PURGED'       // Raw <= 0 converted to null
  | 'QC_INCOMPLETE_75'     // < 75% temporal completeness
  | 'ANEMOMETER_BLACKLISTED'
  | 'WIND_DROPOUT'
  | 'WIND_CALM';

export interface QCPoint {
  hourIndex: number;
  timestamp: string;
  rawValue: number | null;
  qcValue: number | null;
  isSpike7h: boolean;
  isHold3h: boolean;
  peqsLimit?: number;
}

export interface StationQCSeries {
  stationId: string;
  pollutant: PollutantKey;
  completenessPct: number;
  meets75Rule: boolean;
  points: QCPoint[];
}

// ============================================================================
// 11. Workstation State, Layers & Viewport
// ============================================================================

export type LayerId = 'surface' | 'choropleth' | 'wind' | 'flux' | 'stations';

export type LayerVisibilityState = Record<LayerId, boolean>;

export type SurfaceMode = 'discrete_geodesic' | 'anisotropic_wind_steered';

export type DataSourceMode = 'live_stream' | 'fallback_baseline';

export type PlaybackSpeed = 0.35 | 0.8 | 1.6;

export interface MapViewport {
  longitude: number;
  latitude: number;
  zoom: number;
  pitch: 0; // Strictly locked to 0
  bearing: 0; // Strictly locked to 0
  maxPitch: 0;
}

export type SelectedEntity =
  | { type: 'district'; id: string; name: string }
  | { type: 'station'; id: string; name: string }
  | { type: 'airport'; id: string; icao: string }
  | null;

export interface WorkstationAlert {
  id: string;
  level: 'info' | 'warning' | 'hazardous' | 'clamp_500';
  message: string;
  timestamp: string;
  assertive: boolean;
}

/**
 * Continuous Sub-Hourly Interpolated State snapshot for 60 FPS rendering.
 */
export interface InterpolatedWorkstationState {
  fpos: number;
  hourA: number;
  hourB: number;
  fraction: number;
  timestamp: string;
  districtConcentrations: Record<string, number | null>;
  districtWinds: Record<string, [u: number, v: number]>;
  stationConcentrations: Record<string, number | null>;
  stationWinds: Record<string, [u: number, v: number]>;
  provincialMeanAQI: number;
  provincialPeakAQI: number;
  peakDistrictName: string;
  districtsExceedingPEQS: number;
}
```

---

## 5. Verification Method

To independently verify the architecture and specifications established in this report:

1. **HTML Entrypoint Verification**:
   - Inspect `index.html` structure:
     - Verify `<meta charset="UTF-8">` is present.
     - Verify title is `EPA Punjab Air Quality Workstation - Atmospheric Monitoring Console` with **zero emojis**.
     - Verify font links specify `IBM+Plex+Sans`, `IBM+Plex+Sans+Condensed`, and `IBM+Plex+Mono` with no third-party fonts (`Barlow`, `Source Sans`, `JetBrains`).
     - Verify `<div id="root"></div>` and `<script type="module" src="/src/main.tsx"></script>` exist.

2. **Workstation Grid Layout Verification**:
   - Inspect `src/styles/grid.module.css`:
     - Verify CSS Grid specifies:
       ```css
       grid-template-rows: 52px 1fr 68px;
       grid-template-columns: 320px 1fr 380px;
       grid-template-areas:
         "command-bar command-bar command-bar"
         "spatial-dock map-canvas receptor-inspector"
         "temporal-scrubber temporal-scrubber temporal-scrubber";
       ```
     - Verify container has `width: 100vw; height: 100vh; overflow: hidden;` guaranteeing no document scrollbars.

3. **TypeScript Contract Integrity Verification**:
   - Verify that all five schema traps are completely handled in `src/domain/types/index.ts`:
     - Schema Trap 1: `NormalizedDistrict.centroid` is `LngLat` (`[lon, lat]`).
     - Schema Trap 2: `WindVector.state` explicitly models `'dropout' | 'calm' | 'active' | 'blacklisted'`.
     - Schema Trap 3: `NormalizedStation.anemometerBlacklisted` and `WindVector.blacklisted` explicitly guard Station 172 (Wazirabad).
     - Schema Trap 4: Dynamic station counts support 74 fixed, 5 mobile, and 13 Lahore stations.
     - Schema Trap 5: `NormalizedDistrict.isEstimated` unifies `est` and `is_monitored`.
   - Run TypeScript type-checker:
     ```powershell
     npx tsc --noEmit
     ```
   - Run backend regression suite to ensure zero backend routes are broken:
     ```powershell
     python tests/e2e/run_all_tests.py
     ```
     Expected result: 50/50 tests passing in < 30 seconds.

4. **Invalidation Conditions**:
   - Presence of any emoji in HTML, titles, ARIA labels, or TypeScript strings.
   - Use of banned libraries (`tailwindcss`, `lucide-react`, `heroicons`, `feather-icons`).
   - Use of non-IBM Plex fonts or missing `tabular-nums` formatting.
   - Any layout specification that permits root window scrolling.
   - Any failure of `npx tsc --noEmit` or backend E2E tests.
