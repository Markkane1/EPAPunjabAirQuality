# Investigation & Analysis Report: Frontend UI & Layout Architecture

**Explorer**: Explorer 1 (Frontend UI & Layout specialist)  
**Target Project**: Punjab Air Quality Institutional Monitoring & Workstation System  
**State Folder**: `c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\explorer_ui_r3_1`  
**Date**: 2026-11-15T20:15:00Z  

---

## 1. Observation

Direct, verbatim code observations across the codebase with exact file paths and line numbers:

### Observation 1.1: Serving Architecture & Dual Frontend Surfaces
- In `src/api/main.py` lines 213–237:
  ```python
  @app.get("/dashboard", include_in_schema=False)
  @app.get("/dashboard.html", include_in_schema=False)
  async def serve_dashboard():
      legacy_html = frontend_dir / "dashboard.html"
      if legacy_html.exists():
          return FileResponse(legacy_html)
      return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"message": "Dashboard not found"})

  @app.get("/", include_in_schema=False)
  @app.get("/index.html", include_in_schema=False)
  async def serve_index():
      dashboard_html = frontend_dir / "dashboard.html"
      if not dashboard_html.exists():
          dashboard_html = frontend_dir / "index.html"
      if dashboard_html.exists():
          return FileResponse(dashboard_html)
  ```
  The primary institutional frontend delivered to the browser at `GET /` and `GET /dashboard` is `src/frontend/dashboard.html` backed by `src/frontend/static/js/app.js`, `src/frontend/static/js/ui.js`, and `src/frontend/static/css/tokens.css`.
  In parallel, the React workstation application resides in `src/App.tsx`, `src/workstation/`, `src/components/`, built via Vite with entry `src/workstation.html`.

### Observation 1.2: Hardcoded Timeline Bounds & Constants
1. **`src/workstation/state.ts`** lines 4–6 and 224–230:
   ```typescript
   export const HORIZON_START = '2026-11-01 00:00';
   export const HORIZON_END = '2026-11-09 23:00';
   export const HORIZON_HOURS = 216;
   ...
   export function scrubberReadout(hourIndex: number, lerpAlpha: number, timestamp: string): { timestampLine: string; detailLine: string } {
     const clamped = Math.min(HORIZON_HOURS - 1, Math.max(0, hourIndex));
     return {
       timestampLine: `${timestamp} PKT`,
       detailLine: `Hour ${clamped + 1}/${HORIZON_HOURS} \u00B7 Lerp \u03B1=${lerpAlpha.toFixed(2)}`,
     };
   }
   ```
2. **`src/components/scrubber/TimelineScrubber.tsx`** line 138:
   ```tsx
   <Slider
     min={0}
     max={215}
     step={0.01}
     value={[position]}
     onValueChange={(val) => onScrub?.(val[0] ?? 0)}
     aria-label="216-Hour Simulation Timeline Scrubber"
   />
   ```
3. **`src/App.tsx`** lines 331–341:
   ```tsx
   onStep={(delta) => {
     setHourIndex((current) => (current + delta + 216) % 216);
     setLerpAlpha(0);
   }}
   onTogglePlay={() => setIsPlaying((current) => !current)}
   onSpeed={setPlaybackSpeed}
   onScrub={(position) => {
     const hour = Math.max(0, Math.min(215, Math.floor(position)));
     setHourIndex(hour);
     setLerpAlpha(position - hour);
   }}
   ```
4. **`src/frontend/dashboard.html`** line 119 & line 273:
   ```html
   <input type="range" id="scrubRange" class="range-scrubber-input" min="0" max="215" step="0.01" value="0" aria-label="Timeline Transport Scrubber (Hours 0 to 215)">
   ...
   <input type="range" id="gridScrubRange" class="range-scrubber-input grid-scrubber" min="0" max="215" step="0.01" value="0" aria-label="Timeline Transport Scrubber">
   ```
5. **`src/frontend/static/js/app.js`** line 41:
   ```javascript
   this.state = {
     currentHour: 0,
     totalHours: 216,
   ...
   ```
6. **`src/frontend/static/js/ui.js`** lines 1027–1028:
   ```javascript
   const hours = hourlyData.hours || Array.from({ length: 216 }, (_, i) => `H${i}`);
   const totalCols = Math.min(hours.length, 216);
   ```
7. **Existing baseline data expansion**:
   Inspected `data/baseline/baseline_data.json` and `src/frontend/static/data/baseline_data.json`:
   ```json
   {
     "start": "2026-11-01 00:00",
     "end": "2026-11-16 23:00",
     "hours": 384,
     "updated": "2026-11-16T00:00:00Z"
   }
   ```
   The underlying baseline dataset has already been extended to 384 hours (16 days, Nov 1–16), but frontend hardcoded bounds of `216` and `215` truncate user navigation and prevent the scrubber from advancing to subsequent days or to current real-world time.

### Observation 1.3: Pollutant Species Bar Scope Leakage
1. **`src/frontend/dashboard.html`** lines 65–70:
   ```html
   <!-- ZONE 2: PRIMARY POLLUTANT SWITCHER (9 Statutory Species) -->
   <nav class="zone-2-pollutants" role="radiogroup" aria-label="Primary Pollutant Species Switcher">
     <span class="pollutant-label-tag">Pollutant Species:</span>
     <div id="pollutantStrip" class="pollutant-strip">
       <!-- Injected dynamically by UIController with regulatory limits -->
     </div>
   </nav>
   ```
   `<nav class="zone-2-pollutants">` is placed outside `<main id="panel-console">`, directly underneath `<header class="zone-1-header">`.
2. **`src/frontend/static/js/ui.js`** lines 405–409:
   ```javascript
   // Toggle single-pollutant strip: show on console, hide on grid where 9 species are shown simultaneously
   const polNav = document.querySelector('.zone-2-pollutants');
   if (polNav) {
     polNav.style.display = (viewName === 'grid') ? 'none' : 'flex';
   }
   ```
   Because the condition only checks `viewName === 'grid'`, when switching to `viewName === 'lahore'`, `'heatmap'`, `'transboundary'`, or `'fires'`, `polNav.style.display` is set to `'flex'`, leaving the pollutant species bar visible on all sub-view tabs. On the `Hourly Heatmap` tab, which features its own dedicated `.heatmap-metric-selector` (lines 351–359), having the global pollutant bar visible above it causes visual clutter, vertical space consumption, and UX confusion.

### Observation 1.4: Red Block Artifact in Header
1. **`src/frontend/dashboard.html`** lines 34–41:
   ```html
   <div class="header-status-group">
     <div id="provincialAqiBadge" class="provincial-aqi-badge" aria-label="Provincial Air Quality Index">
       -- · INITIALIZING
     </div>
     <div id="clockReadout" class="clock-readout tabular-nums" aria-label="Current Simulation Time">
       PKT (UTC+5): --:--
     </div>
   </div>
   ```
2. **`src/frontend/static/css/tokens.css`** lines 370–382:
   ```css
   .provincial-aqi-badge {
     font-family: var(--font-display);
     font-size: 16px;
     font-weight: 700;
     padding: 4px 10px;
     border-radius: var(--radius-sm);
     background-color: var(--pepc-very-unhealthy);
     color: #ffffff;
     display: inline-flex;
     align-items: center;
     gap: 6px;
     letter-spacing: 0.03em;
   }
   ```
3. **`src/frontend/static/js/ui.js`** lines 561–578:
   ```javascript
   // Update Provincial Header Badge
   if (this.dom.provincialAqiBadge) {
     if (summary.peak_aqi !== undefined && summary.peak_aqi !== null) {
       const maxVal = summary.peak_aqi;
       let tier = PEPC_TIERS[3]; // Unhealthy default
       for (const t of PEPC_TIERS) {
         if (maxVal <= t.max) {
           tier = t;
           break;
         }
       }
       this.dom.provincialAqiBadge.style.backgroundColor = `rgb(${tier.color.join(',')})`;
       this.dom.provincialAqiBadge.textContent = `${activePollutant} ${Math.round(maxVal)} · ${tier.label.toUpperCase()}`;
     } else {
       this.dom.provincialAqiBadge.style.backgroundColor = 'var(--bg-card)';
       this.dom.provincialAqiBadge.textContent = `${activePollutant} – · STANDBY`;
     }
   }
   ```
   In `src/frontend/static/js/canvas.js` line 17:
   `PEPC_TIERS` for Hazardous (AQI > 400): `color: [192, 0, 0]` (`#C00000` pure crimson red).
   Because provincial peak AQI in Punjab is consistently in the Hazardous bracket (400–500), `this.dom.provincialAqiBadge.style.backgroundColor` is set to `rgb(192, 0, 0)`. With white bold text and blocky padding (`4px 10px`), this renders as a jarring solid red brick right in the header toolbar, which users perceive as a broken error state or unstyled block artifact.
4. **React `src/components/command/CommandBar.tsx`** lines 118–128:
   ```tsx
   {hazardous ? (
     <Badge
       role={hazardous.role}
       aria-live={hazardous.ariaLive}
       variant="destructive"
       className="h-7 gap-1.5 rounded-none px-2.5 font-mono text-xs uppercase tracking-wider"
       style={{ backgroundColor: hazardous.background, color: hazardous.color }}
     >
       <AlertTriangle size={14} strokeWidth={1.25} />
       {hazardous.text}
     </Badge>
   ) : null}
   ```
   In `src/workstation/state.ts` lines 213–222:
   ```typescript
   export function hazardousAlert(pm25: number | null): HazardousAlert | null {
     if (pm25 === null || !(pm25 > 350)) return null;
     return {
       role: 'alert',
       ariaLive: 'assertive',
       background: '#C00000',
       color: '#FFFFFF',
       text: 'HAZARDOUS \u00B7 500 CEILING CLAMP',
     };
   }
   ```
   Because baseline PM2.5 in Punjab exceeds 350 µg/m³ constantly, `hazardousAlert()` permanently triggers, rendering an opaque crimson red `#C00000` block badge in the command bar.

### Observation 1.5: Hourly Heatmap Viewport Overflow & Scroll Mechanics
1. **`src/frontend/dashboard.html`** lines 344–366:
   ```html
   <section id="panel-heatmap" class="deep-dive-panel instrument-card" hidden aria-label="Virtualized Hourly Heatmap Matrix">
     <div class="panel-screen-header">
       <div class="panel-title-group">
         <span class="panel-eyebrow">Spatiotemporal Dynamics</span>
         <h2>Spatiotemporal Observation Matrix (41 Districts × 216 Continuous Hours)</h2>
         <div class="card-hint">Hourly mean concentrations across the 9-day synoptic timeline...</div>
       </div>
       <div class="heatmap-metric-selector" role="radiogroup" aria-label="Heatmap Metric Selector">
         <button type="button" class="heatmap-metric-tab active" data-metric="aqi">AQI (PEPC)</button>
         ...
       </div>
     </div>
     <div id="heatmapContainer" class="heatmap-container">
       <table id="heatmapTable" class="heatmap-table"></table>
     </div>
   </section>
   ```
2. **`src/frontend/static/css/tokens.css`** lines 142–145, 754–759, 918–922, and 1424–1471:
   ```css
   .deep-dive-panel {
     min-height: calc(100vh - 120px);
     width: 100%;
     display: flex;
     flex-direction: column;
     gap: 0;
   }
   .instrument-card {
     background: var(--bg-panel);
     border: 1px solid var(--border-subtle);
     border-radius: var(--radius-md);
     padding: 12px 14px;
   }
   .heatmap-container {
     overflow-x: auto;
     max-height: calc(100vh - 220px);
     min-height: 480px;
     overflow-y: auto;
     border: 1px solid var(--border-subtle);
     background: var(--bg-panel);
   }
   table.heatmap-table th {
     background: var(--bg-panel-elevated);
     color: var(--ink-secondary);
     font-weight: 700;
     position: sticky;
     top: 0;
     z-index: 3;
   }
   table.heatmap-table th.sticky-district, table.heatmap-table td.sticky-district {
     position: sticky;
     left: 0;
     background: var(--bg-panel-elevated);
     font-family: var(--font-body);
     font-weight: 600;
     text-align: left;
     z-index: 4;
     border-right: 1px solid var(--border-subtle);
     color: var(--ink-primary);
   }
   ```
   **CSS Sizing Defect**: `min-height: 480px` on `.heatmap-container` combined with `.deep-dive-panel` min-height and `.instrument-card` padding (24px) plus `.panel-screen-header` (~90px) plus header (~50px) results in a minimum total page height of >650px. On viewports with heights <= 768px (standard laptops), `min-height` overrides `max-height: calc(100vh - 220px)`, causing outer window overflow and nested dual vertical scrollbars.
   **Sticky Coordinate Defect**: In `table.heatmap-table`, top-left header cell `<th class="sticky-district">District</th>` has `z-index: 4` while `th` has `z-index: 3`. When scrolling diagonally or down/right, ordinary `td.sticky-district` cells (also `z-index: 4`) overlap with the top header or bleed during fast scrolling unless the intersection corner has a dedicated `z-index: 5` and `border-collapse: separate` with `border-spacing: 0`.

---

## 2. Logic Chain

From the direct observations above, the causal logic chain is as follows:

### 2.1 Dynamic Timeline Advancement Logic
1. **Observation 1.2** proves that the baseline dataset has already extended to 384 hours (`2026-11-01 00:00` to `2026-11-16 23:00`), and live SSE streaming (`src/services/sse.ts`, `src/pipelines/scheduler.py`) continuously produces new timestamps.
2. However, multiple frontend components clamp the timeline to a rigid 216-hour horizon:
   - `TimelineScrubber.tsx` clamps `<Slider max={215}>`
   - `App.tsx` calculates `onStep` with `(current + delta + 216) % 216` and clamps `onScrub` with `Math.min(215, ...)`
   - `state.ts` clamps `scrubberReadout` to `HORIZON_HOURS = 216`
   - `dashboard.html` sets `<input id="scrubRange" max="215">`
   - `ui.js` truncates heatmap columns to `Math.min(hours.length, 216)`
3. Therefore, whenever the application runs with extended baseline data or ingests real live telemetry, the UI locks the scrubber at index 215, denying users access to subsequent days and current time.
4. **Architectural Solution**: The scrubber, range inputs, step increments, readouts, and heatmap columns must be dynamically parameterised by `totalHours = hours.length` (or `Math.max(hours.length, dynamicHoursUntilNow)`). When in "LIVE" mode, the scrubber defaults to `totalHours - 1` while preserving backward scrub navigation to hour 0.

### 2.2 Pollutant Species Bar Scoping Logic
1. **Observation 1.3** demonstrates that `.zone-2-pollutants` is located outside the view panels in `src/frontend/dashboard.html`.
2. In `src/frontend/static/js/ui.js` line 408, the visibility toggle is coded as: `polNav.style.display = (viewName === 'grid') ? 'none' : 'flex';`.
3. Consequently, for all views other than `'grid'` (i.e. `'lahore'`, `'heatmap'`, `'transboundary'`, `'fires'`), `polNav.style.display` is forced to `'flex'`.
4. On `'heatmap'`, a dedicated metric selector (`.heatmap-metric-selector`) already exists with buttons for AQI, PM2.5, PM10, NO2, SO2, CO, O3. Having the global pollutant bar above it is redundant and takes up ~50px of critical vertical viewport space.
5. **Architectural Solution**: By replacing line 408 with `polNav.style.display = (viewName === 'console') ? 'flex' : 'none';`, the pollutant species bar is strictly and cleanly restricted to the Main Console tab with zero side effects.

### 2.3 Red Block Artifact Logic
1. **Observation 1.4** demonstrates that `#provincialAqiBadge` in `dashboard.html` has CSS `background-color: var(--pepc-very-unhealthy)` and in `ui.js` is set to `style.backgroundColor = 'rgb(192, 0, 0)'` (pure crimson Hazardous AQI red).
2. Because AQI in the provincial summary during smog episodes is consistently >= 400, this element permanently renders with an opaque, solid red background with 16px bold text and thick padding.
3. In `CommandBar.tsx`, the hazardous alert badge similarly sets an opaque `style={{ backgroundColor: '#C00000' }}`.
4. An opaque `#C00000` / `rgb(192, 0, 0)` block on an otherwise dark slate/teal institutional canvas (#0f1716, #152120) visually registers as an unstyled error banner, broken image fallback, or styling conflict artifact.
5. **Architectural Solution**: Refactor `.provincial-aqi-badge` and the header alert badge into a refined institutional status pill:
   - Translucent background: `rgba(192, 0, 0, 0.18)`
   - Hairline border: `1px solid rgb(192, 0, 0)`
   - High-contrast crisp text: `#ffffff` or `rgb(255, 107, 94)`
   - Dedicated small indicator dot matching `.live-pulse-badge`
   This eliminates the solid "red block" visual artifact while preserving 100% of the statutory Hazardous notification requirement and WCAG AAA contrast.

### 2.4 Hourly Heatmap Viewport Fit & Scrolling Logic
1. **Observation 1.5** demonstrates that `.heatmap-container` has a hardcoded `min-height: 480px` and `max-height: calc(100vh - 220px)`.
2. Under standard CSS box model rules, `min-height` overrides `max-height`. When total window height is <= 768px, `Header (48px) + Margins (16px) + Panel Card Padding (24px) + Screen Header (90px) + min-height (480px) = 658px+`, which causes `#panel-heatmap` to push past the window bottom.
3. This triggers outer browser scrollbars, creating a nested scrolling trap where scrolling the table accidentally scrolls the entire page and moves the header off-screen.
4. Furthermore, sticky positioning for `th.sticky-district` (top-left corner) requires `z-index: 5` and `border-collapse: separate` with `border-spacing: 0` to prevent cell bleeding when scrolling simultaneously in X and Y directions.
5. In addition, `ui.js` line 1028 artificially clamps heatmap columns with `Math.min(hours.length, 216)`, preventing inspection of hours 216 through 384+.
6. **Architectural Solution**:
   - Lock `#panel-heatmap` to `height: calc(100vh - 72px); max-height: calc(100vh - 72px); overflow: hidden; display: flex; flex-direction: column;`.
   - Make `.heatmap-container` flex-grow to fill exact remaining space: `flex: 1 1 0; min-height: 0; width: 100%; overflow: auto; overscroll-behavior: contain;`.
   - Set `th.sticky-district` corner cell to `z-index: 5`.
   - Update `ui.js` to render all columns `totalCols = hours.length`.

---

## 3. Caveats

1. **Backend Real-Time Availability**: If an external telemetry worker (EPA Punjab, NOAA METAR, CAMS) encounters network downtime or API rate limiting, the pipeline enters degraded state. The frontend must display the latest available hour timestamp rather than generating synthetic forward hours.
2. **Dynamic Time Extension Calculation**: When computing current simulation or wall-clock hours, time zone conversion must strictly use `Asia/Karachi` (UTC+5 / PKT) in accordance with the regulatory specification.
3. **Preservation of Automated Integration Tests**: In `tests/integration/test_frontend.py`, tests assert the presence of specific DOM IDs (`id="pollutantStrip"`, `id="provincialAqiBadge"`, `id="panel-heatmap"`, `id="heatmapContainer"`, `id="heatmapTable"`). None of these elements can be renamed or removed.

---

## 4. Conclusion & Proposed Surgical Fixes

All four reported defects have been pinned to exact file paths and line numbers. The required remedies are surgical, zero-deletion improvements that enhance functionality while strictly preserving existing features.

### Proposed Code Change 1: Dynamic Timeline Advancement
**Target Files**:
1. `src/workstation/state.ts` (lines 4–6, lines 224–230):
```typescript
// BEFORE:
export const HORIZON_START = '2026-11-01 00:00';
export const HORIZON_END = '2026-11-09 23:00';
export const HORIZON_HOURS = 216;

export function scrubberReadout(hourIndex: number, lerpAlpha: number, timestamp: string): { timestampLine: string; detailLine: string } {
  const clamped = Math.min(HORIZON_HOURS - 1, Math.max(0, hourIndex));
  return {
    timestampLine: `${timestamp} PKT`,
    detailLine: `Hour ${clamped + 1}/${HORIZON_HOURS} \u00B7 Lerp \u03B1=${lerpAlpha.toFixed(2)}`,
  };
}

// AFTER:
export const HORIZON_START = '2026-11-01 00:00';
export const HORIZON_HOURS = 216; // Retained as default fallback constant

export function scrubberReadout(
  hourIndex: number,
  lerpAlpha: number,
  timestamp: string,
  totalHours: number = 216
): { timestampLine: string; detailLine: string } {
  const clamped = Math.min(Math.max(1, totalHours) - 1, Math.max(0, hourIndex));
  return {
    timestampLine: `${timestamp} PKT`,
    detailLine: `Hour ${clamped + 1}/${totalHours} \u00B7 Lerp \u03B1=${lerpAlpha.toFixed(2)}`,
  };
}
```

2. `src/components/scrubber/TimelineScrubber.tsx` (lines 9–21, lines 136–144):
```tsx
// BEFORE:
export interface TimelineScrubberProps {
  ...
  scrubber: WorkstationModel['scrubber'];
  horizon: number[];
  ...
}
...
<Slider
  min={0}
  max={215}
  step={0.01}
  value={[position]}
  onValueChange={(val) => onScrub?.(val[0] ?? 0)}
  aria-label="216-Hour Simulation Timeline Scrubber"
/>

// AFTER:
export interface TimelineScrubberProps {
  ...
  totalHours?: number;
  scrubber: WorkstationModel['scrubber'];
  horizon: number[];
  ...
}
...
const maxHour = Math.max(0, (totalHours ?? (horizon.length || 216)) - 1);
<Slider
  min={0}
  max={maxHour}
  step={0.01}
  value={[position]}
  onValueChange={(val) => onScrub?.(val[0] ?? 0)}
  aria-label={`${maxHour + 1}-Hour Dynamic Timeline Scrubber`}
/>
```

3. `src/App.tsx` (lines 331–342):
```tsx
// BEFORE:
onStep={(delta) => {
  setHourIndex((current) => (current + delta + 216) % 216);
  setLerpAlpha(0);
}}
onTogglePlay={() => setIsPlaying((current) => !current)}
onSpeed={setPlaybackSpeed}
onScrub={(position) => {
  const hour = Math.max(0, Math.min(215, Math.floor(position)));
  setHourIndex(hour);
  setLerpAlpha(position - hour);
}}

// AFTER:
onStep={(delta) => {
  setHourIndex((current) => (current + delta + totalHours) % totalHours);
  setLerpAlpha(0);
}}
onTogglePlay={() => setIsPlaying((current) => !current)}
onSpeed={setPlaybackSpeed}
onScrub={(position) => {
  const hour = Math.max(0, Math.min(totalHours - 1, Math.floor(position)));
  setHourIndex(hour);
  setLerpAlpha(position - hour);
}}
```

4. `src/frontend/static/js/app.js` (lines 228–232, 677–681):
```javascript
// Ensure scrubRange.max updates dynamically on initialization & SSE live updates
this.state.totalHours = hourly.hours ? hourly.hours.length : 216;
const scrubRange = document.getElementById('scrubRange');
if (scrubRange) {
  scrubRange.max = String(Math.max(0, this.state.totalHours - 1));
}
const gridScrubRange = document.getElementById('gridScrubRange');
if (gridScrubRange) {
  gridScrubRange.max = String(Math.max(0, this.state.totalHours - 1));
}
```

---

### Proposed Code Change 2: Pollutant Species Bar Tab Scoping
**Target File**: `src/frontend/static/js/ui.js` (lines 405–410):
```javascript
// BEFORE (line 406-409):
// Toggle single-pollutant strip: show on console, hide on grid where 9 species are shown simultaneously
const polNav = document.querySelector('.zone-2-pollutants');
if (polNav) {
  polNav.style.display = (viewName === 'grid') ? 'none' : 'flex';
}

// AFTER:
// Scope pollutant species bar exclusively to the Main Console tab
const polNav = document.querySelector('.zone-2-pollutants');
if (polNav) {
  polNav.style.display = (viewName === 'console') ? 'flex' : 'none';
}
```

---

### Proposed Code Change 3: Red Block Artifact in Header Remediation
**Target Files**:
1. `src/frontend/static/css/tokens.css` (lines 370–382):
```css
/* BEFORE: */
.provincial-aqi-badge {
  font-family: var(--font-display);
  font-size: 16px;
  font-weight: 700;
  padding: 4px 10px;
  border-radius: var(--radius-sm);
  background-color: var(--pepc-very-unhealthy);
  color: #ffffff;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  letter-spacing: 0.03em;
}

/* AFTER: */
.provincial-aqi-badge {
  font-family: var(--font-display);
  font-size: 13px;
  font-weight: 700;
  padding: 3px 8px;
  border-radius: var(--radius-sm);
  background-color: rgba(112, 48, 160, 0.18);
  color: #ffffff;
  border: 1px solid var(--border-subtle);
  display: inline-flex;
  align-items: center;
  gap: 6px;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.provincial-aqi-badge .badge-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  display: inline-block;
}
```

2. `src/frontend/static/js/ui.js` (lines 561–578):
```javascript
// BEFORE:
this.dom.provincialAqiBadge.style.backgroundColor = `rgb(${tier.color.join(',')})`;
this.dom.provincialAqiBadge.textContent = `${activePollutant} ${Math.round(maxVal)} · ${tier.label.toUpperCase()}`;

// AFTER:
const rgb = tier.color.join(',');
this.dom.provincialAqiBadge.style.backgroundColor = `rgba(${rgb}, 0.18)`;
this.dom.provincialAqiBadge.style.borderColor = `rgba(${rgb}, 0.8)`;
this.dom.provincialAqiBadge.style.color = '#ffffff';
this.dom.provincialAqiBadge.innerHTML = `<span class="badge-dot" style="background: rgb(${rgb})"></span>${activePollutant} ${Math.round(maxVal)} · ${tier.label.toUpperCase()}`;
```

3. React `src/components/command/CommandBar.tsx` (lines 118–127):
```tsx
// BEFORE:
<Badge
  role={hazardous.role}
  aria-live={hazardous.ariaLive}
  variant="destructive"
  className="h-7 gap-1.5 rounded-none px-2.5 font-mono text-xs uppercase tracking-wider"
  style={{ backgroundColor: hazardous.background, color: hazardous.color }}
>
  <AlertTriangle size={14} strokeWidth={1.25} />
  {hazardous.text}
</Badge>

// AFTER:
<Badge
  role={hazardous.role}
  aria-live={hazardous.ariaLive}
  variant="outline"
  className="h-7 gap-1.5 rounded-none border border-red-500/60 bg-red-500/15 px-2.5 font-mono text-xs uppercase tracking-wider text-red-400"
>
  <AlertTriangle size={14} strokeWidth={1.25} className="text-red-500" />
  {hazardous.text}
</Badge>
```

---

### Proposed Code Change 4: Hourly Heatmap Viewport Fit & Scrolling Fix
**Target Files**:
1. `src/frontend/static/css/tokens.css` (lines 1424–1471):
```css
/* BEFORE: */
.heatmap-container {
  overflow-x: auto;
  max-height: calc(100vh - 220px);
  min-height: 480px;
  overflow-y: auto;
  border: 1px solid var(--border-subtle);
  background: var(--bg-panel);
}

table.heatmap-table {
  border-collapse: collapse;
  font-family: var(--font-mono);
  font-size: 11px;
  min-width: 100%;
}
...
table.heatmap-table th {
  background: var(--bg-panel-elevated);
  color: var(--ink-secondary);
  font-weight: 700;
  position: sticky;
  top: 0;
  z-index: 3;
}
table.heatmap-table th.sticky-district, table.heatmap-table td.sticky-district {
  position: sticky;
  left: 0;
  background: var(--bg-panel-elevated);
  font-family: var(--font-body);
  font-weight: 600;
  text-align: left;
  z-index: 4;
  border-right: 1px solid var(--border-subtle);
  color: var(--ink-primary);
}

/* AFTER: */
#panel-heatmap {
  height: calc(100vh - 72px);
  max-height: calc(100vh - 72px);
  min-height: 0;
  display: flex;
  flex-direction: column;
  padding: 10px 14px;
  box-sizing: border-box;
  overflow: hidden;
}

#panel-heatmap .panel-screen-header {
  flex-shrink: 0;
  margin-bottom: 8px;
}

.heatmap-container {
  flex: 1 1 0;
  min-height: 0;
  width: 100%;
  overflow: auto;
  overscroll-behavior: contain;
  border: 1px solid var(--border-subtle);
  background: var(--bg-panel);
  position: relative;
}

table.heatmap-table {
  border-collapse: separate;
  border-spacing: 0;
  font-family: var(--font-mono);
  font-size: 11px;
  min-width: 100%;
}

table.heatmap-table th {
  background: var(--bg-panel-elevated);
  color: var(--ink-secondary);
  font-weight: 700;
  position: sticky;
  top: 0;
  z-index: 3;
  border-bottom: 1px solid var(--border-subtle);
}

table.heatmap-table td.sticky-district {
  position: sticky;
  left: 0;
  background: var(--bg-panel-elevated);
  font-family: var(--font-body);
  font-weight: 600;
  text-align: left;
  z-index: 2;
  border-right: 1px solid var(--border-subtle);
  color: var(--ink-primary);
}

/* Intersection corner cell: must stay above both scrolling headers and scrolling rows */
table.heatmap-table th.sticky-district {
  position: sticky;
  top: 0;
  left: 0;
  z-index: 5;
  background: var(--bg-panel-elevated);
  border-right: 1px solid var(--border-subtle);
  border-bottom: 1px solid var(--border-subtle);
}
```

2. `src/frontend/static/js/ui.js` (lines 1027–1029):
```javascript
// BEFORE:
const hours = hourlyData.hours || Array.from({ length: 216 }, (_, i) => `H${i}`);
const totalCols = Math.min(hours.length, 216);

// AFTER:
const hours = hourlyData.hours || Array.from({ length: 216 }, (_, i) => `H${i}`);
const totalCols = hours.length; // Unlock full dynamic timeline (e.g. 384+ hours)
```

---

## 5. Verification Method

To independently verify these findings and proposed solutions:

1. **Verify TypeScript compilation**:
   ```powershell
   npm run typecheck
   ```
   Must pass with 0 errors.

2. **Verify Workstation Baseline Render**:
   ```powershell
   npm run check:workstation
   ```
   Must exit with code 0 (`workstation-check ok stations=74/5 render-ok`).

3. **Verify Frontend HTML and DOM Contracts**:
   Inspect `tests/integration/test_frontend.py` lines 81–147:
   Confirm all required element IDs (`liveSyncBadge`, `provincialAqiBadge`, `pollutantStrip`, `panel-heatmap`, `heatmapContainer`, `heatmapTable`) are strictly present.

4. **Verify Tab Scoping in Browser**:
   Navigate to `http://127.0.0.1:9000/#/console` -> Verify `.zone-2-pollutants` is visible (`display: flex`).
   Navigate to `http://127.0.0.1:9000/#/heatmap` -> Verify `.zone-2-pollutants` is hidden (`display: none`).
   Navigate to `http://127.0.0.1:9000/#/lahore`, `#/transboundary`, `#/fires` -> Verify `.zone-2-pollutants` is hidden (`display: none`).

5. **Verify Heatmap Viewport Fit in Browser**:
   Open Developer Tools, set viewport height to 720px, 800px, and 1080px:
   Confirm that the window does NOT develop an outer vertical scrollbar on the `#/heatmap` tab.
   Confirm that `.heatmap-container` scrolls both horizontally (across all 384+ hours) and vertically (across all 41 districts).
   Confirm that district names stay pinned to the left and hour labels stay pinned to the top.

6. **Invalidation Conditions**:
   - If `test_frontend.py` fails due to missing DOM IDs, the change is invalid.
   - If any user feature or existing navigation tab is removed, the change violates the strict preservation directive.
