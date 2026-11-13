# Project: EPA Punjab Air Quality Institutional Frontend Workstation

## Architecture
- **Paradigm**: Institutional atmospheric physics and regulatory enforcement workstation.
- **Frontend Tech Stack**: React 18 / TypeScript / Vite / Scoped CSS Modules / Deck.gl v8 / MapLibre GL v3.
- **Visual Design Standard**: Rigid 100vw x 100vh CSS Grid, WCAG 2.1 AAA design tokens in `src/styles/tokens.css` (>= 7.0:1 contrast), exclusively IBM Plex Sans / IBM Plex Sans Condensed / IBM Plex Mono typography, tabular-nums formatting, 1.25px miter-joined inline SVGs, 1px solid structural hairlines. Banned: Tailwind CSS, consumer icon packs (lucide-react, heroicons), emojis, 3D pitch/tilt, backdrop-filter blur, drop shadows.
- **Cartographic Engine**: Strictly 2D planimetric MapLibre GL canvas (`pitch: 0, maxPitch: 0, bearing: 0, dragRotate: false, touchPitch: false`) with an interleaved Deck.gl `MapboxOverlay` rendering 5 hardware-accelerated layers.
- **Integration**: FastAPI backend at `http://127.0.0.1:9000/api/v1/*` with seamless fallback to in-memory baseline datasets (`data/baseline/baseline_data.json` and `data/baseline/airports.json`). The production dashboard is served at `GET /` and `/static/*`.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| F01 | T1: Discrete Geodesic IDW | Haversine distance ($R = 6371$ km, $p = 2$) with singularity clamp $d_0 = 5.0$ km for unmonitored district imputation. | M2 | `TRANSFORMATION_LOGIC_SPEC §2.1` |
| F02 | T2: Anisotropic Continuous IDW | 2D continuous concentration bitmap honoring Plate Carrée aspect ratio ($K_X = \cos 31^\circ$), wind steering ($\epsilon = 4.0$ px, $\cos\alpha$, speed boost), and 45–140 km alpha taper. | M2 | `TRANSFORMATION_LOGIC_SPEC §2.2` |
| F03 | T4: Vector Wind Blending & Cartesian Conversion | Polar to Cartesian wind flow vector conversion ($u = -w_s\sin\theta, v = -w_s\cos\theta$), physical speed clamp $\le 30$ m/s, and Station 172 Wazirabad blacklist. | M2 | `TRANSFORMATION_LOGIC_SPEC §2.4` |
| F04 | T5: Conditional Probability Function (CPF) Wind Rose | 16-sector polar rose, calm exclusion ($<0.50$ m/s), pooled station-hours $P_{75}$ threshold, and small-sample suppression ($N_k < 6$). | M2 | `TRANSFORMATION_LOGIC_SPEC §2.5` |
| F05 | T6: Inter-District Advection Mass Flux | Pairwise flux ($C_a w_a \cos(\Delta\theta) \exp(-d_{ab}/100)$), $d \le 180$ km, cone $\le 35^\circ$, with physical dimension guard locking to PM2.5 when AQI is selected. | M2 | `TRANSFORMATION_LOGIC_SPEC §2.6` |
| F06 | T7: Receptor CPF Pathway Coupling & Transport Balance | Flux weighted by receptor CPF probability $\Omega$ (fallback 0.25), truncated to top 60 links, and net transport balance (export - import). | M2 | `TRANSFORMATION_LOGIC_SPEC §2.7` |
| F07 | T8: Transboundary Border Belt & Normal Chevrons | 120 km border belt index and 39 border normal vector dot products $\Phi_j = \mathbf{w}_j \cdot \mathbf{n}_j$ triggering crimson chevrons when $\Phi_j > +0.25$ m/s. | M2 | `TRANSFORMATION_LOGIC_SPEC §2.8` |
| F08 | T9: PEPC Continuous Half-Open AQI Scale & Colors | Continuous half-open intervals $(BP_{i-1}, BP_i]$, piecewise linear calculation, 500 ceiling clamp when PM2.5 $> 350\ \mu\text{g/m}^3$, particulate-governed composite AQI, 7 statutory hex colors. | M2 | `TRANSFORMATION_LOGIC_SPEC §2.9` |
| F09 | T10: Temporal Aggregation, QC Filters & Lerp | Zero-purge, 7h median spike filter ($v_i > 4M_i \land v_i > 3\text{ref}_p$), 3h logger hold filter with $i \ge 2$ guard and AQI exemption, 75% completeness rule, sub-hourly continuous lerp. | M2 | `TRANSFORMATION_LOGIC_SPEC §2.10` |
| F10 | T11: Geographic Projection & Greedy AABB Labeling | Plate Carrée projection with standard parallel $31^\circ\text{N}$ ($K_X = \cos 31^\circ$), greedy AABB collision search across 12 candidate offsets, and leader lines when offset $> 20$ px. | M2 | `TRANSFORMATION_LOGIC_SPEC §2.11` |
| F11 | Schema Trap 1: Centroid Inversion | Invert district centroid `[lat, lon]` to `[lon, lat]` while preserving `label` and `boundary` coordinates. | M2 | `ORIGINAL_REQUEST §R5`, survey |
| F12 | Schema Trap 2: Aerodrome Null vs Calm | Differentiate airport wind telemetry dropouts (`null`) from aerodynamic calm ($0.0 \le w_s < 0.50$ m/s). | M2 | `ORIGINAL_REQUEST §R5`, survey |
| F13 | Schema Trap 3: Station 172 Wazirabad Blacklist | Hard-block wind vector rendering for Station 172 (Wazirabad) due to $140^\circ$ vane offset and flag as `ANEMOMETER BLACKLISTED (VANE OFFSET)`. | M2 | `ORIGINAL_REQUEST §R5`, survey |
| F14 | Schema Trap 4: Dynamic Station Counts | Dynamically compute fixed (74) vs mobile (5) station counts from active station records. | M2 | `ORIGINAL_REQUEST §R5`, survey |
| F15 | Schema Trap 5: Estimation Flag Unification & Hatching | Unify divergent estimation flags (`est`, `is_monitored`) into `is_estimated: boolean` and trigger diagonal polygon cross-hatching. | M2 | `ORIGINAL_REQUEST §R5`, survey |
| F16 | Visual Design System & Tokens | Rigid 100vw x 100vh CSS Grid, WCAG AAA tokens $\ge 7.0:1$ in `src/styles/tokens.css`, IBM Plex typography, tabular-nums, miter-joined SVGs, 1px hairlines, banned dependencies guard. | M1 | `ORIGINAL_REQUEST §R1` |
| F17 | Central Planimetric Map Canvas | Strict 2D MapLibre GL canvas (`pitch: 0, maxPitch: 0, bearing: 0, dragRotate: false, touchPitch: false`). | M3 | `ORIGINAL_REQUEST §R2` |
| F18 | Deck.gl 5-Layer Stack | Interleaved MapboxOverlay rendering 5 layers: Spatial Surface, District Choropleth + Greedy Labels, Wind Vectors, Advection Flux & Border Chevrons, Stations & Aerodromes (13 Lahore stations). | M3 | `ORIGINAL_REQUEST §R2` |
| F19 | Zone 1 Top Command Bar | System identity, live stream vs fallback indicator, assertive ARIA live alerts for Hazardous/500 clamp, 9-pollutant switcher, CSV ingest trigger, QA drawer toggle. | M4 | `ORIGINAL_REQUEST §R3` |
| F20 | Zone 2 Spatial Control Dock | 5-layer toggles, transboundary mass-balance attribution split bar, 41-district statutory ranking table with map centering. | M4 | `ORIGINAL_REQUEST §R3` |
| F21 | Zone 4 Receptor Inspector | Station/district metadata, 9-parameter statutory sub-index table with 75% completeness, 16-sector CPF rose ($N_k < 6$ suppression), 216h QC sparkline chart with 7h spikes and 3h holds. | M4 | `ORIGINAL_REQUEST §R3` |
| F22 | Zone 5 Precision Scrubber | 216h baseline timeline, transport controls, max AQI horizon sparkline, sub-hourly lerp, GPU update triggers. | M4 | `ORIGINAL_REQUEST §R4` |
| F23 | Multipart CSV Ingestion Adapter | POST /api/v1/ingest/csv validated against UserCSVRowContract with dynamic re-interpolation. | M5 | `ORIGINAL_REQUEST §R5` |
| F24 | Live SSE Streaming & Baseline Fallback | EventSource connection to `/api/v1/stream/live` with seamless fallback to in-memory `baseline_data.json` and `airports.json`. | M5 | `ORIGINAL_REQUEST §R5` |
| F25 | Production Serving & E2E Verification | Serve dashboard at `http://127.0.0.1:9000` preserving all `/api/v1/*` routes and 50/50 backend E2E tests, passing 100% of frontend E2E test suite. | M5 | `ORIGINAL_REQUEST §R5` |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| E2E | E2E Testing Track | Independent opaque-box test suite covering Tiers 1–4, publishes `TEST_READY.md`. | none | DONE |
| M1 | Foundation, Tooling & Design Tokens | `package.json`, `tsconfig.json`, Vite build, `src/styles/tokens.css` with WCAG AAA $\ge 7.0:1$, IBM Plex fonts, tabular-nums, 100vw x 100vh CSS Grid layout shell. | none | DONE |
| M2 | Domain Physics & Normalizer Engine | Math transformations T1–T11, `dataNormalizer.ts` addressing all 5 schema traps, physical dimension guard, and unit tests. | M1 | IN_PROGRESS |
| M3 | 2D Planimetric Canvas & 5-Layer Deck.gl Stack | MapLibre GL 2D locked canvas, Deck.gl MapboxOverlay with 5 layers (Spatial surface, choropleth with diagonal hatching, wind vectors with Wazirabad blacklist, advection flux with 39 border chevrons, stations/aerodromes with 13 Lahore stations). | M1, M2 | PLANNED |
| M4 | Telemetry, Controls, Inspector & Scrubber | Zone 1 Top Command Bar, Zone 2 Spatial Control Dock, Zone 4 Receptor Inspector (CPF rose, 216h QC chart), Zone 5 Precision Timeline Scrubber with GPU update triggers. | M2, M3 | PLANNED |
| M5 | Ingestion, SSE, Serving Integration & Final E2E Pass | FastAPI `/api/v1/*` client, multipart CSV ingestion, live SSE stream with baseline fallback, root serving at port 9000, passing 100% of E2E test suite. | M3, M4, E2E | PLANNED |

## Code Layout & Write Ownership
```
Punjab Air Quality/
├── package.json                   # [M1, E2E] Root package dependencies and scripts
├── tsconfig.json                  # [M1] TypeScript configuration
├── vite.config.ts                 # [M1] Vite bundler configuration
├── index.html                     # [M1] Main HTML entrypoint (IBM Plex typography, zero emojis)
├── src/
│   ├── styles/
│   │   ├── tokens.css             # [M1] WCAG 2.1 AAA design tokens (>= 7.0:1 contrast)
│   │   ├── grid.module.css        # [M1] 100vw x 100vh rigid 5-zone grid
│   │   └── typography.css         # [M1] IBM Plex Sans/Mono & tabular-nums rules
│   ├── domain/
│   │   ├── normalizer/            # [M2] dataNormalizer.ts (5 schema traps)
│   │   ├── math/                  # [M2] transforms T1-T11 (IDW, CPF, Flux, AQI, QC)
│   │   └── types/                 # [M1, M2] Core data contracts and TypeScript interfaces
│   ├── map/
│   │   ├── MapCanvas.tsx          # [M3] 2D MapLibre planimetric map canvas (pitch 0, bearing 0)
│   │   └── layers/                # [M3] 5 Deck.gl layers (surface, choropleth, wind, flux, stations)
│   ├── components/
│   │   ├── command/               # [M4] Zone 1 Top Command Bar & ARIA alerts
│   │   ├── dock/                  # [M4] Zone 2 Spatial Control Dock & district table
│   │   ├── inspector/             # [M4] Zone 4 Receptor Inspector, CPF rose, 216h QC chart
│   │   ├── scrubber/              # [M4] Zone 5 Temporal Scrubber & horizon sparkline
│   │   └── common/                # [M1, M4] 1.25px miter-joined SVGs, metric chips
│   ├── services/
│   │   ├── api.ts                 # [M5] FastAPI client for /api/v1/*
│   │   ├── sse.ts                 # [M5] Live SSE streaming client
│   │   └── fallback.ts            # [M5] In-memory baseline data fallback loader
│   ├── App.tsx                    # [M1, M4] Main workstation application container
│   └── main.tsx                   # [M1] Application bootstrap
├── tests/
│   ├── e2e/                       # [E2E] Opaque-box E2E test suite (Tiers 1-4)
│   └── unit/                      # [M2, M3, M4] Unit tests for transforms and normalizer
```

## Interface Contracts

### M1 ↔ M2, M3, M4
- Tokens: CSS variables in `src/styles/tokens.css` with verified AAA contrast (`--bg-canvas`, `--bg-panel`, `--ink-primary`, `--ink-secondary`, `--accent`, `--pepc-good`, etc.).
- Layout: 5 grid area identifiers (`command-bar`, `spatial-dock`, `map-canvas`, `receptor-inspector`, `temporal-scrubber`).
- Types: `Station`, `District`, `HourlyObservation`, `WindVector`, `BorderNode`.

### M2 ↔ M3, M4, M5
- `normalizeDistrict(rawDistrict: RawDistrict): NormalizedDistrict`:
  - Centroid inverted: `centroid: [number, number]` where `[0]` is lon, `[1]` is lat.
  - `is_estimated: boolean` (unified from `est` and `is_monitored`).
- `normalizeWind(rawWind: RawWind, stationId: string): NormalizedWind`:
  - Station 172: `blacklisted: true, u: null, v: null, speed: null, direction: null`.
  - Aerodrome null vs calm: `state: 'dropout' | 'calm' | 'active'`.
- `calculateAQI(concentration: number, pollutant: PollutantKey): { aqi: number, tier: PEPCGrade, color: string }`:
  - Half-open continuous piecewise linear calculation clamped to 500 when PM2.5 > 350.
- `calculateAdvectionFlux(params: FluxParams): PathwayLink[]`:
  - If `pollutant === 'AQI'`, returns `[]` (physical dimension guard).

### M3 ↔ M4
- Map state: `viewport: { center: [lon, lat], zoom: number }`, `selectedEntity: { type: 'station' | 'district', id: string } | null`.
- Layer toggles: `Record<LayerId, boolean>`.

### M5 ↔ Backend
- Server: `http://127.0.0.1:9000`.
- All `/api/v1/*` routes preserved.
- `GET /` serves `src/frontend/dashboard.html` / `index.html`.
