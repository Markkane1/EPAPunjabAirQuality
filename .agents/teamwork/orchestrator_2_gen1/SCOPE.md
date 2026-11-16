# Scope: Punjab Air Quality Institutional Frontend Workstation Remediation & Completion

## Audit Findings & Synthesis
Following the survey by `spec_miner_r1_1`, `spec_miner_r1_2`, and `explorer_r1_1`:
1. **Backend**: 23/23 REST endpoints operational, SSE live stream functional with 15s keepalive, 10 active mathematical transformations (T1, T2, T4, T5, T6, T7, T8, T9, T10, T11) verified, 50/50 backend E2E tests pass (100%), 266/266 integration tests pass.
2. **Milestone 1 Deliverables (DONE)**:
   - `package.json` purged of all banned dependencies (`tailwindcss`, `lucide-react`, `tailwind-merge`, `tailwindcss-animate`, `@radix-ui/*`, `autoprefixer`, `postcss`).
   - Root `index.html` created, loading exclusively IBM Plex typography (Sans, Sans Condensed, Mono) with zero emojis.
   - `tests/unit/test_m1_adversarial.py`, `test_archival_and_baseline.py`, and `test_m1_adversarial_challenge.py` synchronized to allow Vite root `index.html` via size guard (<100KB).
   - `src/components/common/icons.tsx` created with 24 bespoke 1.25px stroke, miter-joined inline SVGs.
   - `ambient.d.ts` deleted; zero banned imports in `src/`.
   - `npm run build` verified cleanly (exit code 0 in ~4s).
3. **Milestone 2 Deliverables (DONE)**:
   - `src/domain/normalizer/dataNormalizer.ts` fully implemented and passing 7/7 unit tests and 2095/2095 challenger assertions across all 5 schema traps:
     1. Centroid inversion: `[lat, lon]` -> `[lon, lat]`.
     2. Aerodrome null vs calm: `state: 'dropout' | 'calm' | 'active'`, with physical bounds checking.
     3. Station 172 Wazirabad blacklist: `blacklisted: true`, reason: `ANEMOMETER BLACKLISTED (VANE OFFSET)` checking `raw.id ?? raw.station_id`.
     4. Dynamic station counts: 74 fixed, 5 mobile.
     5. Unified estimation flag: `is_estimated: boolean` and diagonal cross-hatching.
   - `src/domain/math/*.ts` fully implemented in TypeScript: Transforms T1, T2, T4, T5, T6 (with Physical Dimension Guard locking to PM2.5 when AQI selected), T8 (39 border normals), T9 (continuous half-open PEPC AQI with 500 ceiling clamp), T10 (QC filters, 7h median spike, 3h logger hold with $i \ge 2$ guard and AQI exemption, 75% completeness rule, sub-hourly continuous lerp), T11 (Plate Carrée equirectangular projection & Greedy AABB labeling with leader lines when offset > 20px).
4. **Milestone 3-M4 Deliverables (DONE & CERTIFIED PASS)**:
   - `src/map/MapCanvas.tsx`: Strictly 2D planimetric MapLibre GL canvas (`pitch: 0, maxPitch: 0, bearing: 0, dragRotate: false, touchPitch: false`), integrated with Deck.gl `MapboxOverlay`.
   - `src/map/layers/`: Interleaved Deck.gl MapboxOverlay with 5 layers:
     1. `SurfaceLayer.ts`: 2D continuous IDW spatial surface bitmap honoring Plate Carrée aspect ratio ($K_X = \cos 31^\circ$) and wind steering.
     2. `ChoroplethLayer.ts`: 41 districts colored by statutory PEPC hex colors, diagonal hatching for estimated/unmonitored districts, greedy AABB collision labels with leader lines when offset > 20px.
     3. `WindLayer.ts`: 3-state vector display (dropout glyph, calm circle, active vector) with Station 172 blacklist.
     4. `FluxLayer.ts`: Top-60 coupled pathways ($d \le 180$ km, cone $\le 35^\circ$) with physical dimension guard locking to PM2.5 when AQI selected, and 39 border normal chevrons triggering crimson when $\Phi_j > +0.25$ m/s.
     5. `StationLayer.ts`: 79 stations and aerodromes (fixed squares, mobile diamonds, aerodrome crosshairs), pickable with tooltips and Lahore 13 micro-airshed picking.
   - `src/components/`:
     - `command/CommandBar.tsx`: Zone 1 header, live vs fallback badge, assertive ARIA alerts, 9-pollutant switcher with PEQS limits, CSV modal trigger, QA drawer toggle.
     - `dock/SpatialDock.tsx`: Zone 2 5-layer toggles, transboundary mass-balance attribution split bar, 41-district statutory ranking table with map centering.
     - `inspector/ReceptorInspector.tsx`: Zone 4 metadata card, 9-parameter statutory table with 75% completeness enforcement, 16-sector CPF polar wind rose, 216h QC sparkline chart with 7h median spike and 3h logger hold markers.
     - `scrubber/TimelineScrubber.tsx`: Zone 5 216h baseline timeline, transport controls, max AQI horizon sparkline, continuous sub-hourly lerp, GPU update triggers.
     - Component and state wiring in `src/App.tsx` and `src/workstation/WorkstationView.tsx`.
   - Certification: Gate Result PASS (auditor CLEAN, 2 reviewers APPROVE, 2 challengers APPROVE with 79,931 assertions).
5. **Milestone 5 Deliverables (DONE & CERTIFIED PASS)**:
   - `src/services/api.ts`: Typed REST client with Physical Invariant Guard.
   - `src/services/sse.ts`: Resilient SSE stream manager with 45s TCP drop watchdog and full-jitter backoff.
   - `src/services/fallback.ts`: Zero-dependency offline baseline provider honoring 5 schema traps.
   - `src/components/command/CSVIngestModal.tsx`: Multipart CSV upload with `#csvQuarantineArea` inspection table.
   - Serving integration in `src/api/main.py`: Serves compiled `dist/workstation.html` at `GET /` and `/index.html`, mounted `/assets` to `dist/assets`, retained `/static` for legacy fixtures.
   - Certification: Gate Result PASS (auditor CLEAN, 2 reviewers APPROVE, 2 challengers APPROVE with 15,324 service assertions).

## Milestone Decomposition Plan

| # | Milestone Name | Scope | Dependencies | Status |
|---|----------------|-------|--------------|--------|
| M1-M2 | Foundation Fix & Domain Engine | Purge banned deps, create root `index.html` with IBM Plex typography, fix test remnants, implement `src/domain/normalizer/dataNormalizer.ts` (5 schema traps), TypeScript math transforms, icons.tsx, unit tests. | none | **DONE** |
| M3-M4 | Planimetric Map & Workstation UI | MapLibre 2D canvas, 5 Deck.gl layers, Zones 1-5 UI components, `App.tsx` integration, `src/workstation/` state, `npm run check:workstation` pass. | M1-M2 | **DONE** |
| M5 | Services, Ingestion & Serving Integration | TypeScript API/SSE/fallback services, CSV ingestion modal, FastAPI `main.py` serving `dist/` at root, full build and verification pass. | M3-M4 | **DONE** |
