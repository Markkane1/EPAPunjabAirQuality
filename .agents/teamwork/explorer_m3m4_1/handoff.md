# Technical Exploration & Architecture Blueprint: Milestone M3-M4
**Planimetric Map Canvas & Five Deck.gl Layers**

## 1. Observation

### 1.1 Codebase & Dependency Audit
- **Dependency Inventory (`package.json`)**:
  - `@deck.gl/core`: `^8.9.36`
  - `@deck.gl/geo-layers`: `^8.9.36`
  - `@deck.gl/layers`: `^8.9.36`
  - `@deck.gl/mapbox`: `^8.9.36`
  - `@deck.gl/react`: `^8.9.36`
  - `maplibre-gl`: `^3.6.2`
  - `react`: `^18.3.1`, `react-dom`: `^18.3.1`, `typescript`: `^5.6.3`, `vite`: `^5.4.11`
  - Zero banned dependencies (`tailwindcss`, `lucide-react`, `heroicons`, `@radix-ui/*` purged in M1).
- **TypeScript Declarations (`src/types/deckgl.d.ts`)**:
  - Ambient type re-exports map `@deck.gl/core`, `@deck.gl/layers`, `@deck.gl/mapbox`, `@deck.gl/geo-layers`, and `@deck.gl/react` to their internal `/typed` directories, resolving Deck.gl v8 typing exports.
  - `npm run typecheck` (`tsc --noEmit`) currently passes with zero errors (exit code 0).
- **Existing Map Code in `src/workstation/MapCanvas.tsx`**:
  - Currently implements an early prototype directly on MapLibre GL JS native layers (`map.addLayer` fill, circle, line) rather than an interleaved/overlaid Deck.gl layer stack.
  - Contains lingering banned styles in tooltips (`backdrop-blur shadow-lg` on lines 236-240 of `src/workstation/MapCanvas.tsx`), violating Requirement R1.
  - Boundary geometries in `src/workstation/mapData.ts` (lines 35-42) were mistakenly inverting boundary coordinates via `centroidLngLat`, which conflicts with Schema Trap 1.
- **Canonical Domain Normalizer (`src/domain/normalizer/dataNormalizer.ts`)**:
  - Fully verified and implemented with all 5 schema traps:
    1. `normalizeCentroid(centroid)`: Inverts `[lat, lon]` -> `[lon, lat]` while leaving boundary coordinates and label anchors untouched.
    2. `normalizeWind(speed, direction, stationId)`: Distinguishes `state: 'dropout'`, `state: 'calm'` ($0.0 \le w_s < 0.50$ m/s), and `state: 'active'`.
    3. `isStationBlacklisted(stationId)`: Hard-blocks Station 172 Wazirabad (140° vane offset), flags `blacklisted: true` and `blacklistReason: 'ANEMOMETER BLACKLISTED (VANE OFFSET)'`.
    4. `countStationNetworks(stations)`: Correctly separates 74 fixed and 5 mobile stations.
    5. `isDistrictEstimated(district)`: Unifies `est` and `!is_monitored` into `isEstimated: boolean` for triggering diagonal cross-hatching.
- **Domain Mathematical Transformations (`src/domain/math/*.ts`)**:
  - Transforms T1 & T2 in `idw.ts`: `discreteGeodesicIdw` (Haversine with $d_0 = 5.0$ km clamp) and `anisotropicIdw` (Plate Carrée pixel space with wind steering saturation $\psi = 1.0 + 0.70\cos\alpha\cdot\text{sat}$, and 45–140 km alpha taper).
  - Transform T4 in `wind.ts`: `polarToCartesianWind` ($u = -w_s\sin\theta, v = -w_s\cos\theta$), physical speed clamp $\le 30$ m/s, calm threshold $0.50$ m/s.
  - Transforms T6 & T7 in `flux.ts`: `calculateAdvectionFlux` (strictly returns `null` for `'AQI'` to enforce Physical Dimension Guard; active for physical mass concentrations like PM2.5, $d \le 180$ km, cone divergence $\le 35^\circ$, exponential decay $\exp(-d/100)$), `calculateReceptorCoupling` (truncates to top 60 links).
  - Transform T8 in `transboundary.ts`: `calculateTransboundaryIndex` and `calculateBorderNormalFlux` ($\Phi_j = u_j nx_j + v_j ny_j$ across 39 border nodes).
  - Transform T9 in `pepc_aqi.ts`: Statutory continuous half-open piecewise linear AQI interpolation, 500 ceiling clamp when PM2.5 $> 350\ \mu\text{g/m}^3$, 7 statutory hex colors.
  - Transform T10 in `qc.ts`: Zero purge, 7h median spike filter, 3h logger hold filter with $i \ge 2$ guard and AQI exemption, 75% temporal completeness rule, sub-hourly continuous lerp.
  - Transform T11 in `projection.ts`: Plate Carrée equirectangular projection centered on standard parallel $31^\circ\text{N}$ ($K_X = \cos 31^\circ$), greedy 12-candidate AABB label search, and leader line detection when offset $> 20$ px.
- **Baseline Geographic Data Assets (`data/baseline/`)**:
  - `districts.json`: Exactly 41 administrative districts with boundaries and centroids.
  - `stations.json`: Exactly 79 stations (74 fixed, 5 mobile vans).
  - `baseline_data.json`: Contains `tbgeo.samples` with exactly 39 border normal nodes `[lon, lat, nx, ny]` along the Pakistan-India boundary.
  - Lahore Micro-Airshed: Exactly 13 stations situated in Lahore District (8 fixed: IDs 24, 22, 12, 25, 19, 15, 18, 23; and 5 mobile vans: IDs 27, 28, 29, 30, 31).
  - `airports.json`: Exactly 6 aerodromes (OPLA, OPIS, OPRN, OPFA, OPST, OPMT) with telemetry outages (`null` values) in $u$ and $v$ arrays.
- **Backend Test Status**:
  - `python tests/e2e/run_all_tests.py` passes 50/50 tests (100%) in 5.25 seconds.

---

## 2. Logic Chain

1. **Planimetric Map Canvas Architecture (`src/map/MapCanvas.tsx`)**:
   - *Observation*: Requirement R2 and Project Architecture require a strictly 2D planimetric MapLibre GL map canvas (`pitch: 0, maxPitch: 0, bearing: 0, dragRotate: false, touchPitch: false`).
   - *Deduction*: Any 3D tilt, pitch, or bearing rotation breaks atmospheric physics and regulatory spatial measurements. MapLibre must be initialized with explicit zero constraints, and runtime rotation handlers (`map.dragRotate.disable()`, `map.touchZoomRotate.disableRotation()`, `map.touchPitch.disable()`, `map.keyboard.disableRotation()`) must be called immediately on canvas creation.
   - *Deck.gl Overlay Integration*: `@deck.gl/mapbox` provides `MapboxOverlay`. Adding `MapboxOverlay` as a MapLibre control (`map.addControl(overlay as unknown as maplibregl.IControl)`) guarantees synchronous rendering with MapLibre's camera.
   - *Timing & Pitfall Guard*: In MapLibre GL v3, calling `addControl` before `map.isStyleLoaded()` can trigger style race conditions if `interleaved: true` is used. Using `interleaved: false` (overlaid mode) or attaching inside `map.on('load')` ensures 100% stability, zero style race conditions, and identical hardware-accelerated 60 FPS performance.

2. **Layer 1: Spatial Surface (`src/map/layers/SurfaceLayer.ts`)**:
   - *Observation*: Requirement R2 specifies "2D continuous IDW spatial surface bitmap honoring Plate Carrée aspect ratio ($K_X = \cos 31^\circ$), supporting both discrete geodesic (T1) and anisotropic wind-steered (T2) modes."
   - *Deduction*: Continuous scalar surfaces in Deck.gl are best represented via `BitmapLayer`.
   - *Computational Budget*: CPU rasterization at full screen resolution ($1200 \times 900$) takes 80+ ms, violating 60 FPS budget. UI_UX_SPECIFICATION §5.2 mandates a downsampled $150 \times 175$ compute grid ($0.25\times$ resolution, 26,250 cells), which completes in $< 2.2$ ms.
   - *Cartographic Aspect Ratio*: For bounds $69.10^\circ\text{E}$ to $75.75^\circ\text{E}$ and $27.55^\circ\text{N}$ to $34.30^\circ\text{N}$, $K_X = \cos(31^\circ) \approx 0.857167$. Setting grid width to 150 and height to 175 matches the Plate Carrée metric aspect ratio ($\frac{6.65 \times 0.857}{6.75} \approx 0.844$).
   - *WebGL Bilinear Upsampling*: The 150x175 canvas is passed to `BitmapLayer` with geographic bounds `[69.10, 27.55, 75.75, 34.30]`. Hardware WebGL bilinear texture filtering produces smooth plume gradients with zero pixelation and zero CPU rendering overhead during timeline scrubbing.

3. **Layer 2: District Choropleth & Labels (`src/map/layers/ChoroplethLayer.ts`)**:
   - *Observation*: Requirement R2 mandates "41 district polygons colored by statutory PEPC hex colors, applying diagonal hatching for estimated/unmonitored districts, and deterministic Greedy AABB label collision placement."
   - *Deduction*:
     - Polygon Fills & Borders: `GeoJsonLayer` / `PolygonLayer` renders 41 districts colored by statutory PEPC hex colors (from Transform T9). Line stroke is 1px hairline (`#94a3b8` / `[148, 163, 184]`), highlighted white when selected.
     - Diagonal Cross-Hatching: For districts where `isEstimated === true` (Schema Trap 5), generate 45° diagonal line segments spaced at $\approx 0.08^\circ$ within the district bounding box and render via Deck.gl `PathLayer`.
     - Collision-Free Labels: Apply Transform T11 (`greedyLabelPlacement` from `src/domain/math/projection.ts`). For labels where displacement $> 20$ px, `has_leader_line === true`: render leader lines with `LineLayer`, and render label text with `TextLayer` (`IBM Plex Sans`, `sdf: true`, high-contrast solid background).

4. **Layer 3: Wind Vector Field (`src/map/layers/WindLayer.ts`)**:
   - *Observation*: Requirement R2 & Schema Traps 2 & 3 mandate "3-state vector display distinguishing telemetry dropouts (null), aerodynamic calm (<0.50 m/s), and active wind vectors, while enforcing the station 172 (Wazirabad) anemometer blacklist."
   - *Deduction*:
     - For active winds ($w_s \ge 0.50$ m/s): Render directional flow vectors pointing in the direction air mass travels TO ($u = -w_s\sin\theta, v = -w_s\cos\theta$) using `PathLayer` (shaft + arrowhead).
     - For aerodynamic calm ($0.0 \le w_s < 0.50$ m/s): Suppress directional vector; render a concentric calm circle using `ScatterplotLayer` (radius 4.5px, stroked).
     - For telemetry dropout (null/undefined speed or direction, airport outages): Suppress vector; render a dropout glyph using `ScatterplotLayer` / `PathLayer` (slashed circle, `#94a3b8`).
     - For Station 172 (Wazirabad): HARD-BLOCK wind vector rendering! Render a blacklist alert badge (crimson `#C00000`), with tooltip `ANEMOMETER BLACKLISTED (VANE OFFSET)`.

5. **Layer 4: Advection Flux & Transboundary Border Belt (`src/map/layers/FluxLayer.ts`)**:
   - *Observation*: Requirement R2 mandates "Top-60 coupled pathways ($d \le 180.0$ km, cone $\le 35.0^\circ$) with physical dimension guard locking flux calculations to PM2.5 when AQI is selected, and 39 transboundary border normal chevrons triggering crimson when normal dot product $\Phi_j > +0.25$ m/s."
   - *Deduction*:
     - Advection Pathways: Evaluated using Transforms T6 & T7. If active pollutant is `'AQI'`, lock source to `'PM2.5'` mass concentration ($\mu\text{g/m}^3$) and flag `isPM25Locked: true`. Render top 60 links using `ArcLayer` or `PathLayer` (sky blue `#38bdf8` at emission source transitioning to rose `#f43f5e` at receptor; thickness $\propto \sqrt{\text{flux}}$).
     - 39 Transboundary Border Chevrons: Evaluated across the 39 border nodes from `tbgeo.samples`. Calculate normal dot product $\Phi_j = u_j nx_j + v_j ny_j$. If $\Phi_j > +0.25$ m/s, render statutory crimson (`#C00000`) inward chevron pointing into Punjab. If $\Phi_j < -0.25$ m/s, render teal (`#5fc4c4`) outward chevron pointing into India. Rendered via `PathLayer`.

6. **Layer 5: Stations & Aerodromes (`src/map/layers/StationLayer.ts`)**:
   - *Observation*: Requirement R2 mandates "79 monitoring stations (fixed circles/squares, mobile diamonds, ICAO aerodrome crosshairs) with distinct disaggregation for Lahore's 13 micro-airshed stations."
   - *Deduction*:
     - 74 fixed stations: Square glyphs ($8\text{px} \times 8\text{px}$).
     - 5 mobile vans (all in Lahore): Diamond glyphs ($9\text{px} \times 9\text{px}$).
     - 6 aerodromes: Crosshair glyphs (4-spoke crosshairs).
     - Color fill matches statutory PEPC hex color for current measurement.
     - Lahore Disaggregation: All 13 Lahore stations have distinct coordinates; configure `pickingRadius: 8` with `autoHighlight: true` to guarantee effortless, accurate individual picking on the map canvas.

---

## 3. Implementation Blueprint & Module Signatures

### 3.1 Directory Layout for `src/map/`
```
src/
└── map/
    ├── MapCanvas.tsx            # Main React 2D Planimetric Canvas & MapboxOverlay container
    ├── MapCanvas.module.css     # Strict CSS Module for map viewport & WCAG AAA tooltips
    ├── index.ts                 # Clean barrel export
    └── layers/
        ├── SurfaceLayer.ts      # 2D continuous IDW surface bitmap (Plate Carrée K_X = cos 31°)
        ├── ChoroplethLayer.ts   # 41 districts, PEPC colors, diagonal hatching, greedy labels
        ├── WindLayer.ts         # 3-state vector field + Station 172 blacklist hard-block
        ├── FluxLayer.ts         # Top-60 pathways + PM2.5 dimension guard + 39 border chevrons
        └── StationLayer.ts      # 79 stations + 6 airports + Lahore 13 micro-airshed picking
```

### 3.2 Concrete Signatures & Contracts

#### `src/map/MapCanvas.tsx`
```typescript
import React from 'react';
import type {
  AirportStation,
  LayerId,
  NormalizedDistrict,
  NormalizedStation,
  PollutantKey,
  SelectedEntity,
  SurfaceMode,
} from '../domain/types';

export interface MapHandle {
  zoomIn: () => void;
  zoomOut: () => void;
  reset: () => void;
  flyTo: (center: [number, number], zoom?: number) => void;
  flyToLahore: () => void;
}

export interface MapCanvasProps {
  districts: NormalizedDistrict[];
  stations: NormalizedStation[];
  airports: AirportStation[];
  borderSamples: number[][]; // 39 nodes: [lon, lat, nx, ny]
  districtValues: Record<string, number | null>;
  stationValues: Record<string, number | null>;
  districtWinds: Record<string, [u: number, v: number]>;
  stationWinds?: Record<string, [u: number, v: number]>;
  airportWinds?: Record<string, [u: number, v: number]>;
  pollutant: PollutantKey;
  surfaceMode?: SurfaceMode;
  layers: Record<LayerId, boolean>;
  selectedEntity?: SelectedEntity | null;
  onSelect?: (entity: SelectedEntity) => void;
  hourIndex: number;
  lerpAlpha: number;
}
```

#### `src/map/layers/SurfaceLayer.ts`
```typescript
import { BitmapLayer } from '@deck.gl/layers';
import type { NormalizedStation, PollutantKey, SurfaceMode } from '../../domain/types';

export interface SurfaceLayerProps {
  id?: string;
  visible: boolean;
  opacity?: number;
  mode: SurfaceMode;
  pollutant: PollutantKey;
  stations: NormalizedStation[];
  stationValues: Record<string, number | null>;
  stationWinds?: Record<string, [u: number, v: number]>;
  regionalWind?: [u: number, v: number] | null;
  updateTrigger?: any;
}

export function createSurfaceLayer(props: SurfaceLayerProps): BitmapLayer | null;
```

#### `src/map/layers/ChoroplethLayer.ts`
```typescript
import type { Layer } from '@deck.gl/core';
import type { NormalizedDistrict, PollutantKey } from '../../domain/types';

export interface ChoroplethLayerProps {
  districts: NormalizedDistrict[];
  districtValues: Record<string, number | null>;
  pollutant: PollutantKey;
  visible: boolean;
  selectedDistrictId?: string | null;
  onSelect?: (district: NormalizedDistrict) => void;
  onHover?: (info: any) => void;
  updateTrigger?: any;
}

export function createChoroplethLayers(props: ChoroplethLayerProps): Layer[];
```

#### `src/map/layers/WindLayer.ts`
```typescript
import type { Layer } from '@deck.gl/core';
import type { AirportStation, NormalizedDistrict, NormalizedStation } from '../../domain/types';

export interface WindLayerProps {
  stations: NormalizedStation[];
  airports: AirportStation[];
  districts: NormalizedDistrict[];
  districtWinds: Record<string, [u: number, v: number]>;
  stationWinds?: Record<string, [u: number, v: number]>;
  airportWinds?: Record<string, [u: number, v: number]>;
  visible: boolean;
  onHover?: (info: any) => void;
  updateTrigger?: any;
}

export function createWindLayers(props: WindLayerProps): Layer[];
```

#### `src/map/layers/FluxLayer.ts`
```typescript
import type { Layer } from '@deck.gl/core';
import type { NormalizedDistrict, PollutantKey } from '../../domain/types';

export interface FluxLayerProps {
  districts: NormalizedDistrict[];
  districtValues: Record<string, number | null>;
  pm25Values: Record<string, number | null>;
  districtWinds: Record<string, [u: number, v: number]>;
  borderSamples: number[][]; // 39 nodes: [lon, lat, nx, ny]
  pollutant: PollutantKey;
  visible: boolean;
  onHover?: (info: any) => void;
  updateTrigger?: any;
}

export function createFluxLayers(props: FluxLayerProps): Layer[];
```

#### `src/map/layers/StationLayer.ts`
```typescript
import type { Layer } from '@deck.gl/core';
import type { AirportStation, NormalizedStation, PollutantKey } from '../../domain/types';

export interface StationLayerProps {
  stations: NormalizedStation[];
  airports: AirportStation[];
  stationValues: Record<string, number | null>;
  pollutant: PollutantKey;
  visible: boolean;
  selectedStationId?: string | null;
  onSelect?: (entity: { type: 'station' | 'airport'; id: string; name: string }) => void;
  onHover?: (info: any) => void;
  updateTrigger?: any;
}

export function createStationLayers(props: StationLayerProps): Layer[];
```

---

## 4. Caveats & Assumptions

1. **Overlay Mode Selection**:
   - `MapboxOverlay({ interleaved: false })` (overlaid mode) is recommended over `interleaved: true` because MapLibre v3 creates a separate WebGL context in overlaid mode, eliminating any style race conditions or custom layer shader conflicts while maintaining identical 60 FPS performance and camera synchronization. If `interleaved: true` is strictly required by test assertions, it must be added strictly inside `map.on('load')`.
2. **Greedy Label Placement Coordinate Space**:
   - Transform T11 greedy AABB placement evaluates offsets in 2D projected space. In `MapCanvas`, label anchors are projected using `map.project([lon, lat])` or the standard Plate Carrée projection with $K_X = \cos 31^\circ$. Both yield consistent collision-free placement.
3. **No Production Writes**:
   - As an Explorer subagent, no modifications have been made to files in `src/`. All architectural specifications and blueprints are recorded here in `handoff.md` for the implementing agent (`developer_m3m4`).

---

## 5. Conclusion & Actionable Execution Steps

1. **Directory Creation**:
   Create `src/map/` and `src/map/layers/`.
2. **Layer Implementation Order**:
   - Step 1: Implement `src/map/layers/SurfaceLayer.ts` (150x175 offscreen canvas, T1/T2, $K_X = \cos 31^\circ$, `BitmapLayer`).
   - Step 2: Implement `src/map/layers/ChoroplethLayer.ts` (`PolygonLayer` fills, `PathLayer` diagonal hatching for `isEstimated`, `LineLayer` + `TextLayer` greedy AABB labels).
   - Step 3: Implement `src/map/layers/WindLayer.ts` (Active vectors, calm circles $<0.50$ m/s, dropout glyphs, Station 172 Wazirabad blacklist hard-block).
   - Step 4: Implement `src/map/layers/FluxLayer.ts` (Top 60 pathways, Physical Dimension Guard locking to PM2.5 for AQI, 39 border normal chevrons triggering crimson for $\Phi_j > +0.25$ m/s).
   - Step 5: Implement `src/map/layers/StationLayer.ts` (74 fixed squares, 5 mobile diamonds, 6 airport crosshairs, 13 Lahore stations with distinct picking).
   - Step 6: Implement `src/map/MapCanvas.tsx` (Locked 2D MapLibre map, `MapboxOverlay` control, WCAG AAA tooltip, ref controls).
   - Step 7: Update `src/App.tsx` and `src/workstation/WorkstationView.tsx` to mount the new `MapCanvas`.
3. **Verification**:
   Execute `npm run typecheck`, `npm run build`, and `python tests/e2e/run_all_tests.py` to ensure zero compilation or E2E regressions.

---

## 6. Verification Method

To independently verify this exploration and technical blueprint:
1. **Typecheck & Build**:
   ```powershell
   npm run typecheck
   npm run build
   ```
   Both commands must exit with code 0.
2. **Backend E2E Suite**:
   ```powershell
   python tests/e2e/run_all_tests.py
   ```
   Must pass 50/50 tests (100%) in $< 10$ seconds.
3. **Challenger Adversarial Unit Tests**:
   ```powershell
   python -m pytest tests/unit/test_challenger_m1m2.py tests/unit/test_data_normalizer.py
   npx tsx tests/unit/test_challenger_adversarial_m1m2_r2.ts
   ```
   All challenger probes must pass.
