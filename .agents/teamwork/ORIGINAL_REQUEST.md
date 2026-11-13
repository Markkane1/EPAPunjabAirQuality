# Original User Request

## Initial Request — 2026-11-11T12:52:15Z

Implement the end-to-end frontend for the EPA Punjab Air Quality Monitoring, Processing, and Visualization System as an institutional atmospheric physics and regulatory enforcement workstation.

Integrity mode: development

Reference Materials:
- `TEST_INFRA.md`
- `docs/TRANSFORMATION_LOGIC_SPEC.md`
- `docs/UI_UX_SPECIFICATION.md`
- `docs/SYSTEM_ARCHITECTURE.md`
- `data/baseline/baseline_data.json`
- `data/baseline/airports.json`

## Requirements

### R1. Institutional Workstation Architecture & Visual Design
Build a rigid 100vw x 100vh CSS Grid five-zone workstation interface using strictly scoped CSS Modules backed by WCAG 2.1 AAA tokens in `src/styles/tokens.css` (>= 7.0:1 contrast). Load exclusively IBM Plex Sans, IBM Plex Sans Condensed, and IBM Plex Mono typography, enforcing tabular-nums formatting on all numeric readouts. Do not use Tailwind CSS, generic fonts, consumer icon packs (lucide-react, heroicons), emojis, 3D tilted map perspectives, backdrop-filter blur, or drop shadows; use crisp 1.25px miter-joined inline SVGs or deck.gl primitives and 1px solid structural hairlines.

### R2. Central Planimetric Map Canvas & Five-Layer Deck.gl Stack
Implement a strictly 2D planimetric MapLibre GL map canvas (pitch: 0, bearing: 0, dragRotate: false) with an interleaved deck.gl MapboxOverlay rendering 5 authoritative layers:
1. Spatial Surface: 2D continuous IDW spatial surface bitmap honoring the Plate Carrée aspect ratio (K_X = cos 31°), supporting both discrete geodesic (T1) and anisotropic wind-steered (T2) modes.
2. District Choropleth & Labels: 41 district polygons colored by statutory PEPC hex colors, applying diagonal hatching for estimated/unmonitored districts, and deterministic Greedy AABB label collision placement.
3. Wind Vector Field: 3-state vector display distinguishing telemetry dropouts (null), aerodynamic calm (<0.50 m/s), and active wind vectors, while enforcing the station 172 (Wazirabad) anemometer blacklist.
4. Advection Flux & Transboundary Border Belt: Top-60 coupled pathways (d <= 180.0 km, cone <= 35.0°) with physical dimension guard locking flux calculations to PM2.5 when AQI is selected, and 39 transboundary border normal chevrons triggering crimson when normal dot product Phi_j > +0.25 m/s.
5. Stations & Aerodromes: 79 monitoring stations (fixed circles, mobile diamonds, ICAO aerodrome crosshairs) with distinct disaggregation for Lahore's 13 micro-airshed stations.

### R3. Telemetry, Controls & Inspector Panels
- Zone 1 Top Command Bar: System identity, live stream vs. fallback baseline indicator, assertive ARIA live alerts for hazardous conditions or 500 ceiling clamp, 9-pollutant statutory switcher (AQI, PM2.5, PM10, NO2, SO2, CO, O3, NO, NOX), CSV ingestion trigger, and QA drawer toggle.
- Zone 2 Spatial Control Dock: 5-layer stack toggles, transboundary mass-balance attribution split bar (cross-border easterly inflow vs. domestic emissions), and 41-district statutory ranking table with row selection centering the map.
- Zone 4 Receptor Inspector: Station/district metadata, 9-parameter statutory sub-index and QA table with 75% temporal completeness enforcement, 16-sector CPF polar wind rose with small-sample suppression (N_k < 6) and calm exclusion, and 216-hour time-series QC chart highlighting 7-hour median spikes and 3-hour logger holds (with AQI exempted).

### R4. Temporal Playback Scrubber & PEPC Scale Governance
Implement Zone 5 timeline scrubber covering the 216-hour baseline (2026-11-01 00:00 to 2026-11-09 23:00) with playback transport controls, horizon sparkline of provincial max AQI for jumping to severe smog inversion episodes, and statutory PEPC continuous half-open piecewise linear AQI scale clamped at 500 when PM2.5 > 350 μg/m³. Decouple timeline scrubbing from static geometry using GPU update triggers without re-parsing GeoJSON on the CPU.

### R5. Data Normalization, Ingestion & Backend Integration
Query the FastAPI backend at `http://127.0.0.1:9000/api/v1/*` and provide seamless fallback to in-memory baseline structures (`baseline_data.json` and `airports.json`). Implement `dataNormalizer.ts` addressing all five schema traps:
- Invert district centroid `[lat, lon]` to `[lon, lat]` while keeping `label` and `boundary` `[lon, lat]` unchanged.
- Differentiate aerodrome `null` wind outages from aerodynamic calm.
- Hard-block wind vector rendering for station 172 (Wazirabad) due to vane offset blacklist.
- Compute fixed vs. mobile station counts dynamically.
- Unify estimation flags and apply diagonal hatching to estimated polygons.
Support multipart CSV ingestion (`POST /api/v1/ingest/csv`) validated against `UserCSVRowContract` with dynamic re-interpolation. Serve or proxy the frontend so `http://127.0.0.1:9000` renders the production dashboard without breaking any `/api/v1/*` routes or backend E2E tests.

## Acceptance Criteria

### Institutional Visual Standards & Dependencies
- [ ] `package.json` contains no banned dependencies (`tailwindcss`, `lucide-react`, `heroicons`, `feather-icons`).
- [ ] `index.html` loads exclusively `IBM Plex Sans`, `IBM Plex Sans Condensed`, and `IBM Plex Mono`.
- [ ] Tabular-nums formatting is enforced for all numeric readouts.
- [ ] No emojis are used in code, UI text, or ARIA labels.
- [ ] MapLibre pitch is permanently locked to 0 with rotation disabled (`pitch: 0, maxPitch: 0, bearing: 0, dragRotate: false, touchPitch: false`).
- [ ] All text/surface pairs in `src/styles/tokens.css` meet WCAG 2.1 AAA contrast ratio (>= 7.0:1).

### Mathematical, Cartographic & Physical Exactness
- [ ] District centroids are normalized from `[lat, lon]` to `[lon, lat]` before passing to deck.gl layers.
- [ ] Aerodrome wind values of `null` render as missing telemetry dropout glyphs, wind speeds 0.0 <= ws < 0.500 m/s render as aerodynamic calm circles, and ws >= 0.500 m/s render directional vectors.
- [ ] Station 172 (Wazirabad) wind vectors are suppressed and flagged as ANEMOMETER BLACKLISTED (VANE OFFSET).
- [ ] When AQI is selected, advection flux calculations and display lock to PM2.5 (μg/m³) with a physical dimension guard banner.
- [ ] Transboundary border nodes render crimson chevrons strictly when dot product Phi_j > +0.25 m/s.
- [ ] CPF polar wind rose suppresses sectors with N_k < 6 valid wind hours and excludes calm periods (ws < 0.50 m/s).
- [ ] Temporal QC chart visually flags 7-hour median spikes and 3-hour logger holds (with AQI exempted).
- [ ] All 13 Lahore stations are individually pickable and distinguishable on the map canvas.

### Verification & Integration Guardrails
- [ ] Backend E2E regression suite (`python tests/e2e/run_all_tests.py`) passes 50/50 tests (100%) in < 30 seconds.
- [ ] Frontend builds cleanly with zero TypeScript compilation or bundle errors (`tsc`, `npm run build`).
- [ ] The dashboard is accessible at `http://127.0.0.1:9000` while preserving all `/api/v1/*` endpoints.
