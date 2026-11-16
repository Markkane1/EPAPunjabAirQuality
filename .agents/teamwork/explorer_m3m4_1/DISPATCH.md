## 2026-11-14T09:44:10Z
You are Explorer 1 (`explorer_m3m4_1`).
Your state folder: `c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\explorer_m3m4_1`
Working directory: `c:\Users\Asif\Downloads\Punjab Air Quality`
Original Request path: `c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\ORIGINAL_REQUEST.md`
Scope document path: `c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\orchestrator_2_gen1\SCOPE.md`
Project document path: `c:\Users\Asif\Downloads\Punjab Air Quality\PROJECT.md`

MANDATORY FIRST STEP: Read `c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\ORIGINAL_REQUEST.md` before starting work.

TASK:
Perform technical exploration and design the exact implementation plan for Milestone M3-M4: Planimetric Map Canvas & 5 Deck.gl Layers.

SPECIFIC OBJECTIVES:
1. Investigate the codebase for existing map components, Deck.gl types, and domain math transforms:
   - Check `src/types/deckgl.d.ts`, `src/domain/types/index.ts`, `src/domain/math/*.ts`, `src/domain/normalizer/dataNormalizer.ts`.
   - Check if `src/map/` or `src/workstation/` contains existing layer code or stubs.
2. Formulate the concrete implementation details for `src/map/MapCanvas.tsx`:
   - Locked 2D MapLibre GL map canvas (`pitch: 0, maxPitch: 0, bearing: 0, dragRotate: false, touchPitch: false`).
   - Integration with Deck.gl `MapboxOverlay` (or React DeckGL overlay if compatible).
   - Viewport bounds for Punjab: bounds clamping, initial center, zoom controls.
3. Formulate the concrete implementation details for each of the 5 Deck.gl layers in `src/map/layers/`:
   - `SurfaceLayer.ts`: 2D continuous IDW surface bitmap honoring Plate Carrée aspect ratio ($K_X = \cos 31^\circ$) and wind steering.
   - `ChoroplethLayer.ts`: 41 districts colored by statutory PEPC hex colors, diagonal hatching for estimated/unmonitored districts, greedy AABB collision labels.
   - `WindLayer.ts`: 3-state vector display (dropout glyph for null, calm circle for <0.50 m/s, active vector) with Station 172 Wazirabad blacklist.
   - `FluxLayer.ts`: Top-60 coupled pathways ($d \le 180$ km, cone $\le 35^\circ$) with Physical Dimension Guard locking to PM2.5 when AQI selected, and 39 border normal chevrons triggering crimson when $\Phi_j > +0.25$ m/s.
   - `StationLayer.ts`: 79 stations and aerodromes (fixed squares, mobile diamonds, aerodrome crosshairs), pickable with tooltips and Lahore 13 micro-airshed picking.
4. Document the exact file paths, exported signatures, data flow from normalized store/state to Deck.gl layers, and error guards.
5. Identify any potential build/typecheck pitfalls with Deck.gl v8 packages and MapLibre GL v3.
