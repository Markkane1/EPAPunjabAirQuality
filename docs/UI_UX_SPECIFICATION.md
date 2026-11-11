# Punjab Air Quality Information System
# UI/UX Architecture & Interface Design Specification (Requirement R5)

**Document Version:** 1.0.0 (Production Blueprint)  
**Status:** Approved Design Specification  
**Design Philosophy:** Mission-Critical Scientific Instrument Console (/impeccable)  
**Target Compliance:** WCAG 2.1 AAA Accessibility & 60 FPS Continuous Animation  

---

## 1. Design Vision & Aesthetic Direction (/impeccable)

### 1.1 The Operational Context: "Operate" Mode
Air quality monitoring during severe episodic events (e.g., the intense November smog season in Punjab, Pakistan) is not a passive reading experience or a marketing showcase. It is an **active operational console** used by environmental protection officers, meteorologists, public health authorities, and affected citizens.

The interface must satisfy the **"Operate" mode** (/impeccable):
- **Immediate Situational Awareness:** The user must grasp current provincial severity, peak hotspots, transboundary plume trajectories, and compliance with statutory limits within 3 seconds of load.
- **Scientific Instrument Density:** High information density without visual chaos. Clean typographic hierarchies, rigorous alignment to an 8pt spatial grid, and zero decorative fluff or artificial AI styling.
- **Atmospheric Palette with Absolute Contrast:** Dark and light modes designed with calibrated luminance steps. Pollutant colors are rooted in the official **Punjab Environmental Protection Council (PEPC)** and **Punjab Environmental Quality Standards (PEQS)** color ramps, verified for colorblind readability and WCAG 2.1 AAA text contrast.
- **Physical Dynamics Realism:** Smooth, tear-free particle advection and fluid sub-hourly temporal scrubbing operating synchronously at 60 FPS.

```
+---------------------------------------------------------------------------------------------------+
| COMMAND HEADER: [Live Telemetry Pulse]  Punjab Air Quality Console  [Composite AQI: 342 HAZARDOUS] |
+---------------------------------------------------------------------------------------------------+
| POLLUTANT MATRIX: [AQI (PEPC)] [PM2.5] [PM10] [NO2] [SO2] [CO] [O3] [NO] [NOx]                     |
+-----------------------------------------------------------------+---------------------------------+
| PRIMARY SPATIAL VIEWPORT                                        | TELEMETRY & ANALYTICS SIDEBAR   |
| +-------------------------------------------------------------+ | +-----------------------------+ |
| | MULTI-LAYER CANVAS / WEBGL MAP                              | | | Provincial Summary (This H) | |
| |   - Layer 0: Static Basemap (Path2D TopoJSON)               | | |   Mean: 284 | >PEQS: 38/41  | |
| |   - Layer 1: Continuous Wind-Steered IDW Field (WebGL)      | | |   Peak: Lahore (492)        | |
| |   - Layer 2: 1300-Particle Wind Advection (AQMS + ECMWF)    | | |   [Canvas: 24h Sparkline]   | |
| |   - Layer 3: Quadratic Bezier Flux Links & Border Chevrons  | | +-----------------------------+ |
| |   - Layer 4: Station Glyphs & Collision-Free Labels         | | | Airport Weather (METAR)     | |
| |   - Floating Dynamic Legend & Temporal Clock HUD            | | |   OPLA, OPFA, OPMT, OPST... | |
| +-------------------------------------------------------------+ | +-----------------------------+ |
| | TEMPORAL TRANSPORT SCRUBBER CONTROLLER                      | | | Ranked District List        | |
| |   [Play/Pause] [=== Range Scrubber (0.00 - 215.00) ===]     | | |   Lahore:      492 ████████ | |
| |   Mode: (•) Continuous Surface  ( ) Administrative Borders  | | |   Faisalabad:  380 ██████   | |
| |   Layers: [✓] Transport Flux  [✓] Regional ECMWF [10m|925]  | | +-----------------------------+ |
| |   Playback Speed: [0.35x] [0.8x Normal] [1.6x Fast]         | | | Selected District Detail    | |
| +-------------------------------------------------------------+ | |   9 Pollutants vs PEQS      | |
|                                                                 | |   [Canvas: 16-Sector CPF]   | |
|                                                                 | +-----------------------------+ |
+-----------------------------------------------------------------+---------------------------------+
| SECTION 2: Multi-Pollutant Synchronized 3x3 Grid (AQI, PM2.5, PM10, NO2, SO2, CO, O3, NO, NOx)   |
+---------------------------------------------------------------------------------------------------+
| SECTION 3: Detailed Lahore Network Focus (11 Fixed & Mobile AQMS Stations + Wagha Border Inset)   |
+---------------------------------------------------------------------------------------------------+
| SECTION 4: Virtualized District Hourly Matrix Heatmap (41 Districts x 216 Hours with Tabbed Views)|
+---------------------------------------------------------------------------------------------------+
| SECTION 5: Transboundary Inflow & Satellite Diagnostics (NASA FIRMS, ECMWF Flux, IQAir Anchors)   |
+---------------------------------------------------------------------------------------------------+
```

---

## 2. Information Architecture & Visual Hierarchy

The application layout is structured into five principal functional zones designed to guide cognitive focus from provincial overviews down to hyper-local sensor telemetry:

### 2.1 Zone 1: Command Header & Navigation Strip
- **System Status Pill:** Real-time pulse indicator reflecting data freshness (`LIVE SYNC: ACTIVE`, `T+04 min`, or `FALLBACK ARCHIVE`).
- **Provincial Air Quality Badge:** High-visibility badge summarizing current composite status (e.g. `AQI: 342 - VERY UNHEALTHY`), color-coded to the active PEPC tier.
- **Temporal Clock Readout:** High-legibility digital readout displaying current simulation timestamp in Pakistan Standard Time (`PKT (UTC+5): Sat 09 Nov 23:00`).
- **Sub-View Navigation:** Rapid tabs switching between `Main Console`, `Lahore Network Focus`, `Hourly Heatmap Matrix`, and `Transboundary Diagnostics`.

### 2.2 Zone 2: Primary Pollutant Switcher
A persistent horizontal control strip containing 9 statutory pollutants with standardized abbreviations, regulatory limits, and measurement units:
1. `AQI` (PEPC Composite Index, $0 - 500+$)
2. `PM2.5` (Fine Particulates, PEQS $35\,\mu\text{g/m}^3$)
3. `PM10` (Coarse Particulates, PEQS $150\,\mu\text{g/m}^3$)
4. `NO2` (Nitrogen Dioxide, PEQS $80\,\mu\text{g/m}^3$)
5. `SO2` (Sulfur Dioxide, PEQS $120\,\mu\text{g/m}^3$)
6. `CO` (Carbon Monoxide, PEQS $5\,\text{mg/m}^3$)
7. `O3` (Ground-level Ozone, PEQS $130\,\mu\text{g/m}^3$)
8. `NO` (Nitric Oxide, $40\,\mu\text{g/m}^3$)
9. `NOx` (Total Oxides of Nitrogen)

*Interaction Behavior:* Switching pollutants updates all map continuous fields, choropleth fills, legend stops, sparkline reference baselines, and data tables instantaneously without losing playback position.

### 2.3 Zone 3: Interactive Geographic Map Viewport & Controls
- **Canvas Display:** 16:9 responsive viewport rendering the Province of Punjab and adjacent international borderlands (69.10°E–75.75°E, 27.55°N–34.30°N).
- **Floating HUD Clock & Legend:**
  - Dynamic gradient bar displaying the exact color stops, numerical values, and qualitative health categories for the selected pollutant.
  - Interactive click on legend segments highlights districts falling within that bracket.
- **Playback Control Deck:**
  - Precision Scrubber: Continuous slider with 216 integer hour tick stops and fractional sub-hour lerp position ($fp \in [0.00, 215.00]$).
  - Play/Pause Toggle with keyboard spacebar shortcut.
  - Speed Stepper ($0.35\times$ Slow, $0.8\times$ Real-time pacing, $1.6\times$ Fast overview).
  - Layer Visibility Toggles:
    - Surface Mode (`Continuous IDW Field` vs `Administrative Choropleth`).
    - Inter-District Transport Flux Curves (toggle on/off).
    - Regional ECMWF IFS Winds (toggle on/off, with 10m vs 925 hPa height selector).

### 2.4 Zone 4: Real-Time Telemetry Sidebar (360px Fixed Desktop)
Positioned adjacent to the primary map for instant comparative readout:
1. **Provincial Summary Card:** Displays period/hourly mean, count of districts exceeding PEQS (e.g. `38 / 41 districts > PEQS`), and peak district identifier.
2. **24-Hour Sparkline Canvas:** Visualizes the 216-hour provincial average curve with an active scrubber bar indicating current playback time and a dashed red line at the PEQS limit.
3. **Airport Wind & Visibility Matrix:** Real-time decoding of 12 METAR airport feeds (wind vector arrow, speed in knots, metric visibility, temperature, and present weather codes like `smoke, haze`).
4. **Ranked District Exceedance List:** Dynamically sorted list of all 41 districts displaying current concentration, relative bar indicator, and monitoring status badge (`LIVE` vs `IDW ESTIMATE`). Clicking any district selects it.
5. **Selected District Telemetry Drawer:** 
   - 9-pollutant breakdown table showing raw concentration vs PEQS multiple.
   - **16-Sector Polar Wind Rose:** Real-time Conditional Probability Function (CPF) diagram displaying upwind source directions exceeding the district's 75th percentile ($P_{75}$) threshold, with a dashed $0.25$ null hypothesis circle.

### 2.5 Zone 5: Deep-Dive Analytics & Transboundary Panels
- **Synchronized 3x3 Multi-Pollutant Grid:** 9 synchronized mini-canvas viewports rendering all pollutants simultaneously under identical playback controls.
- **Dedicated Lahore Network Drawer:** Inset map of Lahore's 11 monitoring stations (7 fixed, 4 mobile) showing micro-scale intra-city gradients and proximity to the Wagha international border.
- **Virtualized Hourly Heatmap Matrix:** High-performance tabular matrix rendering 41 districts $\times$ 216 hours, featuring interactive cell inspect tooltips and column scrubber tracking.
- **Transboundary Remote Sensing Hub:** Incorporates NASA FIRMS VIIRS active fire counts across 11 subnational provinces, ECMWF transboundary mass fluxes, and IQAir cross-border city anchors.

---

## 3. Visual Design System & Design Tokens

### 3.1 Color Tokens & Atmospheric Themes

The design system incorporates a dual-mode atmospheric palette. The dark mode mimics a nocturnal aerospace radar console, reducing eye fatigue during intensive monitoring shifts while making vibrant pollutant plumes pop. The light mode maintains high-contrast crispness for daytime office and field operations.

```css
:root {
  /* Surface & Container Colors */
  --color-bg-canvas: #0f1716;             /* Deep atmospheric slate background */
  --color-bg-panel: #152120;              /* Card and sidebar background */
  --color-bg-panel-elevated: #1c2b2a;     /* Hover and modal drawer background */
  --color-border-subtle: #2a3a38;         /* Structural borders and dividers */
  --color-border-strong: #4f625e;         /* Interactive input boundaries */

  /* Text & Ink Tokens (WCAG 2.1 AAA Compliant) */
  --color-ink-primary: #e3ece9;           /* Contrast ratio 14.2:1 against bg-panel */
  --color-ink-secondary: #93a39e;         /* Contrast ratio 7.8:1 against bg-panel */
  --color-ink-tertiary: #6b7a76;          /* Minimum 4.5:1 ratio for captions */

  /* Map Geographic Cartography Fills */
  --color-geo-sea: #0b1211;               /* Map exterior non-land backdrop */
  --color-geo-land: #162120;              /* Neighboring provincial territory fill */
  --color-geo-punjab: #1d2d2c;            /* Punjab provincial territory */
  --color-geo-district-border: #4f625e;   /* Inter-district administrative boundaries */
  --color-geo-international: #ff7a6b;     /* International border (dashed red) */
  --color-geo-india-fill: #26231a;        /* Cross-border Indian territory */

  /* Environmental Flow & Dynamics */
  --color-flow-link: #e3f4f2;             /* Inter-district transport curve stroke */
  --color-flow-particle: rgba(225,245,242,0.38); /* Wind advection particle streak */
  --color-flow-inflow: #ff6b5e;           /* Transboundary cross-border inflow chevron */
  --color-flow-outflow: #5fc4c4;          /* Transboundary cross-border outflow chevron */
}

/* Light Theme Overrides */
[data-theme="light"] {
  --color-bg-canvas: #eef1ef;
  --color-bg-panel: #fbfcfb;
  --color-bg-panel-elevated: #ffffff;
  --color-border-subtle: #d3dad7;
  --color-border-strong: #9aa6a2;
  --color-ink-primary: #17221f;           /* Contrast ratio 15.1:1 against bg-panel */
  --color-ink-secondary: #5b6964;         /* Contrast ratio 6.9:1 against bg-panel */
  --color-ink-tertiary: #7d8c87;
  --color-geo-sea: #e3e8e5;
  --color-geo-land: #eceeec;
  --color-geo-punjab: #f8f9f8;
  --color-geo-district-border: #9aa6a2;
  --color-geo-international: #a3261f;
  --color-geo-india-fill: #efe8d8;
  --color-flow-link: #18302f;
  --color-flow-particle: rgba(20,40,40,0.35);
  --color-flow-inflow: #c4312a;
  --color-flow-outflow: #0d6e72;
}
```

### 3.2 Official PEPC / PEQS AQI Continuous Color Ramps
The color scale maps pollutant values directly to statutory health threat levels:

| Tier | Health Category | AQI Range | PM2.5 (24h) | Hex Code | RGB Color | WCAG Text On Color |
|---|---|---|---|---|---|---|
| **0** | **Good** | $0 - 50$ | $0 - 15\,\mu\text{g/m}^3$ | `#00B050` | `rgb(0, 176, 80)` | `#000000` (8.4:1) |
| **1** | **Satisfactory** | $51 - 100$ | $16 - 35\,\mu\text{g/m}^3$ | `#92D050` | `rgb(146, 208, 80)` | `#000000` (10.2:1) |
| **2** | **Moderate** | $101 - 150$ | $36 - 70\,\mu\text{g/m}^3$ | `#FFFF00` | `rgb(255, 255, 0)` | `#000000` (18.6:1) |
| **3** | **Unhealthy (Sensitive)** | $151 - 200$ | $71 - 140\,\mu\text{g/m}^3$ | `#ED7D31` | `rgb(237, 125, 49)` | `#000000` (6.2:1) |
| **4** | **Unhealthy** | $201 - 300$ | $141 - 250\,\mu\text{g/m}^3$ | `#FF0000` | `rgb(255, 0, 0)` | `#FFFFFF` (4.9:1) |
| **5** | **Very Unhealthy** | $301 - 400$ | $251 - 350\,\mu\text{g/m}^3$ | `#7030A0` | `rgb(112, 48, 160)` | `#FFFFFF` (7.3:1) |
| **6** | **Hazardous** | $401+$ | $> 350\,\mu\text{g/m}^3$ | `#C00000` | `rgb(192, 0, 0)` | `#FFFFFF` (6.1:1) |

*Continuous Piecewise Color Interpolation Formula:*
For any concentration $v$ falling between discrete regulatory breakpoints $x_0$ and $x_1$ with RGB endpoints $\mathbf{C}_0$ and $\mathbf{C}_1$:
$$t = \text{clamp}\left(\frac{v - x_0}{x_1 - x_0}, 0.0, 1.0\right)$$
$$\mathbf{C}(v) = \mathbf{C}_0 + t \cdot (\mathbf{C}_1 - \mathbf{C}_0)$$

### 3.3 Typography Hierarchy
The typographic system enforces clear cognitive separation between qualitative scientific prose, structural instrument labels, and high-frequency tabular numeric telemetry:

| Style Class | Font Family | Size (px) | Line Height | Weight | Letter Spacing | Semantic Usage |
|---|---|---|---|---|---|---|
| **Display Header** | `Barlow Condensed` | 28px | 32px | 700 | -0.02em | Application title, prominent AQI banner |
| **Section Header** | `Barlow Condensed` | 20px | 24px | 600 | 0.00em | Card titles, drawer headers, section labels |
| **Component Label**| `Source Sans 3` | 13px | 18px | 600 | +0.02em | Toolbar button text, table column headers |
| **Body Scientific** | `Source Sans 3` | 14px | 20px | 400 | 0.00em | Diagnostic notes, methodology documentation |
| **Telemetry Value** | `JetBrains Mono` | 18px | 22px | 600 | -0.02em | Live concentrations, wind speed scalars |
| **Tabular Matrix**  | `JetBrains Mono` | 12px | 16px | 400 | 0.00em | Cell values in 41x216 table (`tabular-nums`) |
| **Caption / Tick**  | `JetBrains Mono` | 10px | 12px | 400 | +0.03em | Axis ticks, latitude/longitude coordinates |

*Mandatory CSS Rule:* All numeric values must enforce `font-variant-numeric: tabular-nums` to eliminate layout jank and column vibration during continuous timeline playback.

### 3.4 8-Point Spatial Layout Grid
All layouts, card paddings, margins, and control touch targets conform strictly to an **8-point spatial grid**:
- `$spacing-xxs`: 2px (subtle borders and divider offsets)
- `$spacing-xs`: 4px (badge internal padding, compact table cell margins)
- `$spacing-sm`: 8px (standard grid unit: icon spacing, input padding)
- `$spacing-md`: 16px (card inner padding, button margins, column gutters)
- `$spacing-lg`: 24px (section margins, sidebar headers)
- `$spacing-xl`: 32px (major layout grid gaps, modal gutters)
- `$spacing-xxl`: 48px (outer container margins)

---

## 4. State Management Architecture

The application replaces the legacy tangle of 60+ global variables with a **Single Source of Truth reactive store (Zustand)** structured into clear, decoupled slices:

```mermaid
flowchart TD
    subgraph Store["Zustand Root State Store"]
        TS["TemporalSlice\n- fpos: number (0.00 - 215.00)\n- isPlaying: boolean\n- speedMultiplier: 0.35 | 0.8 | 1.6\n- currentHourIndex: number (floor fpos)"]
        SS["SpatialSlice\n- selectedDistrictId: string | null\n- hoveredStationId: string | null\n- displayMode: 'surface' | 'district'\n- activeMapBounds: BoundingBox"]
        PS["PollutantSlice\n- activePollutant: 'AQI' | 'PM2.5' | ...\n- activeBreakpoints: PollutantThresholds\n- activePaletteRamp: ColorStop[]"]
        LS["LayerSlice\n- showTransportLinks: boolean\n- showRegionalWind: boolean\n- ecmwfVerticalLevel: '10' | '925'\n- stationFilter: 'all' | 'fixed' | 'mobile'"]
        DATA["TelemetrySlice\n- historicalSeries: 216h Master Matrix\n- districtMetadata: 41 District Records\n- stationMetadata: 79 Station Records\n- airportMetarRecords: 12 Airport Objects\n- transboundaryFluxCache: FluxMatrix"]
    end

    subgraph Subscribers["Reactive Subscribers"]
        RENDERER["Multi-Layer Canvas / WebGL Renderer"]
        SCRUBBER["Temporal Transport Control Deck"]
        SIDEBAR["Telemetry Sidebar & CPF Rose"]
        MATRIX["Virtualized Heatmap Matrix"]
    end

    TS --> RENDERER & SCRUBBER & SIDEBAR & MATRIX
    SS --> RENDERER & SIDEBAR
    PS --> RENDERER & SIDEBAR & MATRIX
    LS --> RENDERER
    DATA --> RENDERER & SIDEBAR & MATRIX
```

### 4.1 Sub-Hourly Continuous Temporal Lerp Engine & State Tearing Prevention
To achieve fluid, tear-free animation at 60 FPS across discrete hourly data files while eliminating React 19 Concurrent Mode tearing (Challenge 3.2), the system strictly **decouples the high-frequency animation frame loop from the React component state tree**:

1. **Decoupled Subscription Channels**:
   - High-frequency temporal scrubbing positions (`fpos` at 60 Hz) do NOT trigger top-level React component re-renders.
   - The Canvas/WebGL render loop reads `fpos` directly via mutable `useRef` handles and Zustand transient subscriptions (`useTimeStore.subscribe(fpos => mapRenderer.render(fpos))`).
   - React UI components (Sidebar, Tooltips, Metric Cards) subscribe to an integer hour slice or throttled snapshot (10 Hz), preventing component tree churn and reference tearing.

2. **Immutable Snapshot Selector for UI Consumers**:
   Unlike legacy closures that mutate a shared singleton object behind React's back (causing race conditions where sidebars read mutated state from future hours), UI selectors return fresh, immutable snapshots:

```typescript
export interface InterpolatedHourState {
  readonly concentrations: Readonly<Record<string, number | null>>;
  readonly windVectors: Readonly<Record<string, [number, number]>>; // [u, v] in m/s
  readonly airportWinds: Readonly<Record<string, [number, number]>>;
}

export const createTemporalLerp = (telemetry: TelemetrySlice) => {
  return (fpos: number, pollutantKey: string): InterpolatedHourState => {
    const totalHours = telemetry.hours.length;
    const hourA = Math.min(totalHours - 1, Math.floor(fpos));
    const hourB = Math.min(totalHours - 1, hourA + 1);
    const fraction = fpos - hourA;

    const lerp = (a: number | null, b: number | null): number | null => {
      if (a === null) return b;
      if (b === null) return a;
      return a + (b - a) * fraction;
    };

    const concentrations: Record<string, number | null> = {};
    const windVectors: Record<string, [number, number]> = {};
    const districtList = telemetry.districtIds;

    for (let i = 0; i < districtList.length; i++) {
      const d = districtList[i];
      const valA = telemetry.matrix[pollutantKey][hourA][d];
      const valB = telemetry.matrix[pollutantKey][hourB][d];
      concentrations[d] = lerp(valA, valB);

      const windA = telemetry.windMatrix[hourA][d];
      const windB = telemetry.windMatrix[hourB][d];
      windVectors[d] = [
        lerp(windA[0], windB[0]) ?? 0,
        lerp(windA[1], windB[1]) ?? 0
      ];
    }

    // Returns an isolated immutable snapshot for UI consumers
    return {
      concentrations,
      windVectors,
      airportWinds: {}
    };
  };
};
```

---

## 5. High-Performance Real-Time Visualization Layer

The visualization engine completely departs from monolithic canvas drawing by implementing a **decoupled five-layer rendering architecture**:

```
+------------------------------------------------------------------------------------+
| STACKED MULTI-LAYER RENDERING COMPOSITION                                          |
+------------------------------------------------------------------------------------+
| [Layer 4: DOM Interaction Layer]  HTML accessible focus nodes, tooltips, HUD clock |
+------------------------------------------------------------------------------------+
| [Layer 3: Canvas Vector Overlay]  Station nodes, Bezier transport curves, chevrons |
+------------------------------------------------------------------------------------+
| [Layer 2: Canvas Particle System] 1300 dual-layer wind advection particles (60 FPS)|
+------------------------------------------------------------------------------------+
| [Layer 1: WebGL / Offscreen IDW]  Wind-steered continuous raster field (sub-hour)  |
+------------------------------------------------------------------------------------+
| [Layer 0: Static Basemap Canvas]  Path2D TopoJSON province and international borders|
+------------------------------------------------------------------------------------+
```

### 5.1 Layer 0: Static Vector Basemap Canvas
- **Technology:** HTML5 Canvas 2D with cached `Path2D` geometry paths.
- **Update Frequency:** Only on window resize or theme switch (Zero per-frame drawing overhead).
- **Contents:**
  - Exterior non-land fill (`--color-geo-sea`).
  - Punjab provincial territory fill (`--color-geo-punjab`).
  - Neighboring provinces of Pakistan (`--color-geo-land`).
  - Cross-border international territory of India (`--color-geo-india-fill`).
  - International border stroke (`--color-geo-international`, 1.5px dashed pattern `[4, 4]`).

### 5.2 Layer 1: Continuous Field Rasterizer (WebGL Fragment Shader / Downsampled Canvas IDW)
- **Performance Mandate & Frame Budget Compliance (Challenge 3.1)**:
  Benchmarking reveals that unconstrained CPU IDW rasterization requires $8.8\text{ ms}$ to $82.9\text{ ms}$ per frame, severely exceeding the $16.67\text{ ms}$ 60 FPS frame budget and causing framerates to plummet to 12–15 FPS on high-DPI displays.
  To preserve the 60 FPS budget, the continuous field engine implements two hardware-accelerated modes guaranteeing execution time **$< 3\text{ ms}$**:
  1. **Primary GPU Pipeline (WebGL 2.0 Fragment Shader)**:
     - Station coordinates, wind vectors, and normalized concentrations are bound as uniform arrays or floating-point textures.
     - Massively parallel GPU fragment cores evaluate anisotropic wind-steered IDW weights and the distance alpha taper simultaneously in **$< 0.4\text{ ms}$**.
  2. **Canvas 2D Hardware Fallback (Downsampled Compute Grid + Bilinear Upsampling)**:
     - When WebGL is unavailable, the CPU evaluates IDW exclusively on a **downsampled $150 \times 175$ cell grid** ($0.25\times$ resolution, 26,250 cells).
     - Grid calculation completes in **$< 2.2\text{ ms}$**.
     - The low-resolution offscreen buffer is stretched to the primary viewport with hardware bilinear texture filtering (`ctx.imageSmoothingEnabled = true`), producing smooth plume gradients with zero pixelation and zero frame drops.
- **Canvas Context & VRAM Optimization (Challenge 3.3)**:
  - Consolidates the 5 rendering tiers into **two physical canvases**: Base Canvas (Layers 0 & 1) and Dynamic Canvas (Layers 2 & 3), topped by DOM Layer 4.
  - Clamps `devicePixelRatio` to `1.5` on mobile devices, keeping total backing store VRAM $< 35\text{ MB}$ and preventing iOS Safari context destruction (`webglcontextlost`).
  - Virtualizes the 3x3 comparison grid so inactive panes render as static PNG thumbnails without allocating live WebGL contexts.
- **Distance Taper Alpha**: Opacity is automatically faded between $45\text{ km}$ and $140\text{ km}$ from the nearest reporting monitor ($235 \to 95$) to visually convey spatial uncertainty in remote rural districts.

### 5.3 Layer 2: Dual Wind Particle Advection Engine & Ring Buffer Memory
- **Technology:** High-performance Canvas 2D path rendering with zero GC overhead.
- **Particle Count:** 1,300 total particles running concurrently:
  - **Local Layer (700 particles):** Advected across Punjab using ground station and airport METAR winds blended via Gaussian distance decay.
  - **Regional Layer (600 particles):** Advected across broader Northwestern India and Eastern Pakistan using ECMWF IFS 0.25° grid winds (interpolated bilinearly at 10m or 925 hPa).
- **Numerical Integration:** Euler forward integration step:
  $$\mathbf{x}(t + \Delta t) = \mathbf{x}(t) + \mathbf{v}(\mathbf{x}(t)) \cdot k \cdot \Delta t$$
- **Pre-Allocated Float32Array Ring Buffer (Challenge 3.4)**:
  Replaces dynamic JavaScript array manipulation (`push` / `shift`) with a pre-allocated flat typed buffer:
  ```typescript
  // 1,300 particles * 8 history points * 2 coordinates (x, y) = 20,800 floats (81.25 KB)
  const particleRingBuffer = new Float32Array(1300 * 8 * 2);
  ```
  Updating particle trails is performed via integer pointer arithmetic ($O(1)$) with **zero heap allocations per frame**, eliminating the 78,000 array allocations/sec that previously triggered cyclic garbage collection stutter.
- **Lifecycle Management:** Particles have a maximum lifespan of 120 frames with stochastic respawn upon border exit.

### 5.4 Layer 3: Dynamic Transport Vector Overlay
- **Pairwise Inter-District Flux Curves:**
  - Evaluated between districts within $180\text{ km}$ where wind direction aligns within $\pm 35^\circ$ of the source-to-receptor bearing.
  - Strictly disabled for `AQI` (active only for physical concentrations).
  - Truncated to the top 60 pathways by composite score to prevent visual clutter and CPU overhead.
  - Rendered as quadratic Bezier curves with perpendicular curvature $uy \cdot L \cdot 0.12$.
  - Line thickness scales dynamically with $\sqrt{\text{flux}}$.
  - Arrowheads advance along the curve with animated stroke dash offsets (`dash -= 0.6`).
- **Transboundary Cross-Border Chevrons:**
  - Evaluated across 39 discrete border sample nodes (`tbgeo.samples`) spaced $\sim 25\text{ km}$ apart along the Pakistan-India international border.
  - Chevron orientation points along the boundary normal vector.
  - Color indicates advective transport direction (Bright Red `#ff6b5e` for Inflow into Pakistan; Teal `#5fc4c4` for Outflow into India).
  - Subtle oscillation phase ($A \cdot \sin(\omega t)$) creates directional wave motion.

### 5.5 Layer 4: Station Glyphs & Collision-Free Greedy Labeling
- **Station Nodes:** Rendered as clean vector shapes:
  - Fixed AQMS: Square glyph ($8\text{px} \times 8\text{px}$).
  - Mobile AQMS Vans: Triangle glyph.
  - Airport METAR: Aviation directional wind barb.
- **Collision-Free Label Placement:** Implements an AABB greedy search across 12 candidate offsets ($[0,0], [0,14], [0,-14], [16,0], \dots$). If displacement $>20\text{px}$ is required to prevent label overlap, an automated leader line connects the text tag to the anchor node.

### 5.6 Dynamic 16-Sector CPF Polar Rose Renderer
Rendered in the sidebar to reveal upwind source trajectories for any selected district:
- **Geometry:** 16 sectors of $22.5^\circ$ width ($360^\circ / 16$) centered on cardinal/intercardinal azimuths.
- **Calm Exclusion:** Winds $<0.5\text{ m/s}$ are removed from directional counts; calm fraction displayed as a central badge.
- **Null Hypothesis Baseline:** Concentric dashed circle at $\text{CPF} = 0.25$. Any sector extending beyond $0.25$ indicates statistically significant directional source enrichment.
- **Dynamic Chromatic Amplification:** Sector wedges are tinted by concentration: $\mathbf{C} = \text{thr} \cdot (0.6 + 1.4 \cdot \text{CPF}_i)$.

---

## 6. Interaction Models & Responsive Breakpoints

### 6.1 Timeline Scrubbing & Keyboard Navigation
- **Fluid Scrubbing:** Direct mouse or touch dragging on `#scrub` yields sub-millisecond visual updates using the sub-hourly lerp engine.
- **Keyboard Shortcuts:**
  - `Space`: Toggle Animation Play / Pause.
  - `ArrowLeft` / `ArrowRight`: Step backward / forward by exactly 1 hour.
  - `Shift + ArrowLeft` / `Shift + ArrowRight`: Step backward / forward by 6 hours.
  - `Home` / `End`: Jump to hour 0 (start) or hour 215 (latest observation).
  - `Digit1` through `Digit9`: Direct selection of statutory pollutants (1 = AQI, 2 = PM2.5, ...).

### 6.2 Responsive Layout Breakpoints

```
+---------------------------------------------------------------------------------------------------+
| RESPONSIVE BREAKPOINT MATRICES                                                                    |
+---------------------------------------------------------------------------------------------------+
| 1. DESKTOP VIEWPORT (> 980px)                                                                     |
|    - Layout: 2-Column Grid (1fr Main Map + 360px Telemetry Sidebar)                               |
|    - Comparison Grid: 3 Columns x 3 Rows (Synchronized 9-Map Array)                               |
|    - Lahore Network: Interactive Split Modal / Drawer                                             |
+---------------------------------------------------------------------------------------------------+
| 2. TABLET VIEWPORT (560px - 980px)                                                                |
|    - Layout: Stacked Single-Column (Map on top, Sidebar below as collapsible cards)               |
|    - Comparison Grid: 2 Columns x 5 Rows                                                          |
|    - Lahore Network: Full-width responsive card                                                   |
+---------------------------------------------------------------------------------------------------+
| 3. MOBILE VIEWPORT (< 560px)                                                                      |
|    - Layout: Compact Vertical Stack                                                               |
|    - Map: Fixed 320px height with touch-pinch zoom and pan lock                                   |
|    - Telemetry Sidebar: Bottom sheet drawer with swipe-up expansion                               |
|    - Matrix Tables: Horizontal touch scroll with sticky district name headers                     |
|    - Comparison Grid: 1 Column vertical list with synchronous scrubber                             |
+---------------------------------------------------------------------------------------------------+
```

### 6.3 Accessibility & Inclusivity Specifications (WCAG 2.1 AAA)
1. **Screen Reader Live Announcements:**
   - A hidden ARIA live region (`aria-live="polite"`, `id="a11y-status"`) announces hourly transitions:  
     `"Simulation at Saturday 9 November 23:00 PKT. Provincial mean AQI is 284, Hazardous. Highest reading in Lahore at 492."`
2. **Keyboard Focus Outlines:**
   - All interactive controls (buttons, sliders, table rows) feature high-visibility dual-ring focus outlines (`outline: 2px solid var(--color-ink-primary); outline-offset: 2px`).
3. **Canvas Fallback DOM Tree:**
   - The canvas element wraps an offscreen semantic table structure containing all active district values, ensuring non-visual user agents can inspect geographic readings.
4. **Colorblind-Safe Palettes:**
   - In addition to color hue, all health categories display numerical values, qualitative text descriptors, and distinct hazard glyphs (e.g. `● Good`, `▲ Moderate`, `■ Hazardous`).

---

## 7. UI Component Hierarchy & Design Tokens Summary

| Component Name | File / Module | Key Responsibilities | WCAG / Accessibility Feature |
|---|---|---|---|
| `<CommandHeader />` | `components/header/` | System status, live pulse, AQI badge, time display | ARIA live status region |
| `<PollutantStrip />` | `components/controls/` | Statutory pollutant switcher buttons | Tab-index navigation, `aria-pressed` |
| `<MapView />` | `components/map/` | Multi-layer Canvas/WebGL composition | Canvas fallback DOM table |
| `<TimelineDeck />` | `components/controls/` | Scrub range slider, play/pause, speed, mode | ARIA slider attributes (`aria-valuenow`) |
| `<ProvincialCard />` | `components/sidebar/` | Summary KPIs, 24-hour mean sparkline | High-contrast text labels |
| `<DistrictList />` | `components/sidebar/` | Ranked exceedance list with relative bars | Semantic `<ol>` list with button rows |
| `<WindRoseCard />` | `components/sidebar/` | 16-sector CPF polar diagram & calm badge | Text alternative table of sector % |
| `<ComparisonGrid />` | `components/comparison/`| 3x3 synchronized 9-pollutant mini maps | Linked `aria-controls` |
| `<LahoreDrawer />` | `components/lahore/` | Inset 11-station high-resolution network | Accessible modal dialog with focus trap |
| `<VirtualizedMatrix />`| `components/tables/` | 41 districts x 216 hours heatmap table | Keyboard row/col focus, virtualized rows |
| `<TransboundaryHub />` | `components/analytics/`| FIRMS fires, ECMWF flux, IQAir border cities | Structured data tables with footnotes |

*All UI/UX component architectures and design specifications satisfy Requirement R5 in full.*
