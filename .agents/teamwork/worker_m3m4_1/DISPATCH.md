## 2026-11-14T14:57:11Z
You are Worker 1 (`worker_m3m4_1`).
Your state folder: `c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\worker_m3m4_1`
Working directory: `c:\Users\Asif\Downloads\Punjab Air Quality`
Original Request path: `c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\ORIGINAL_REQUEST.md`
Scope document path: `c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\orchestrator_2_gen1\SCOPE.md`
Project document path: `c:\Users\Asif\Downloads\Punjab Air Quality\PROJECT.md`
Relevant Skill: `C:\Users\Asif\.gemini\config\plugins\agent-skills\skills\frontend-ui-engineering\SKILL.md`

MANDATORY FIRST STEP: Read `c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\ORIGINAL_REQUEST.md` before starting work.
Read the Explorer reports for detailed architecture and blueprints:
- `c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\explorer_m3m4_1\handoff.md` (Map & Deck.gl layers)
- `c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\explorer_m3m4_2\handoff.md` (UI Components Zones 1-5)
- `c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\explorer_m3m4_3\handoff.md` (Verification & Integration 5-Gate protocol)

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

EXCLUSIVE WRITE BOUNDARIES:
You exclusively own and may create/edit these files:
- `package.json` (add `"check:workstation"` and `"test:unit"` scripts)
- `src/map/*` (`MapCanvas.tsx`, `index.ts`, `layers/*.ts`)
- `src/components/command/CommandBar.tsx`
- `src/components/dock/SpatialDock.tsx`
- `src/components/inspector/ReceptorInspector.tsx`
- `src/components/scrubber/TimelineScrubber.tsx`
- `src/workstation/WorkstationView.tsx`, `src/workstation/MapCanvas.tsx`, `src/workstation/state.ts`
- `src/App.tsx`
DO NOT touch any backend python files in `src/api/` or `src/database/` or `tests/e2e/` or `tests/unit/`.

TASK & IMPLEMENTATION REQUIREMENTS:
1. Update `package.json` scripts:
   - Add `"check:workstation": "node scripts/check-workstation.mjs"`
   - Add `"test:unit": "tsx tests/unit/test_challenger_m1m2.ts"`
2. Implement Planimetric Map & 5 Deck.gl Layers in `src/map/`:
   - `src/map/layers/SurfaceLayer.ts`: 150x175 offscreen raster canvas, Plate Carrée aspect ratio ($K_X = \cos 31^\circ$), T1 geodesic and T2 anisotropic wind steering with saturation and 45-140 km alpha taper, hardware-filtered `BitmapLayer`.
   - `src/map/layers/ChoroplethLayer.ts`: 41 districts colored by statutory PEPC hex colors, `est-hatch` diagonal hatching pattern when `isEstimated === true`, deterministic Greedy AABB collision labels across 12 candidate offsets with leader lines when offset $> 20$ px.
   - `src/map/layers/WindLayer.ts`: 3-state vector display (dropout glyph for `null`, calm circle for $w_s < 0.50$ m/s, active vector arrow for $w_s \ge 0.50$ m/s), and Station 172 Wazirabad anemometer blacklist hard-block (`blacklisted: true`, `ANEMOMETER BLACKLISTED (VANE OFFSET)`).
   - `src/map/layers/FluxLayer.ts`: Top-60 coupled pathways ($d \le 180$ km, cone $\le 35^\circ$) with Physical Dimension Guard locking to PM2.5 when AQI selected, and 39 border normal chevrons triggering crimson (`#C00000`) strictly when $\Phi_j > +0.25$ m/s.
   - `src/map/layers/StationLayer.ts`: 79 stations and aerodromes (74 fixed squares, 5 mobile diamonds, 6 aerodrome crosshairs), pickable with tooltips and Lahore 13 micro-airshed picking.
   - `src/map/MapCanvas.tsx`: Locked 2D MapLibre GL map canvas (`pitch: 0, maxPitch: 0, bearing: 0, dragRotate: false, touchPitch: false`), integrated with `MapboxOverlay`. Clean up any legacy banned styling classes (ensure zero `backdrop-blur`, zero `shadow-lg`, zero non-zero border-radius).
   - `src/map/index.ts`: Clean exports.
3. Implement modular Workstation UI components in `src/components/`:
   - `src/components/command/CommandBar.tsx` (Zone 1) per blueprint in `explorer_m3m4_2\handoff.md`.
   - `src/components/dock/SpatialDock.tsx` (Zone 2) per blueprint in `explorer_m3m4_2\handoff.md`.
   - `src/components/inspector/ReceptorInspector.tsx` (Zone 4) per blueprint in `explorer_m3m4_2\handoff.md`.
   - `src/components/scrubber/TimelineScrubber.tsx` (Zone 5) per blueprint in `explorer_m3m4_2\handoff.md`.
4. Refactor and assemble `src/workstation/WorkstationView.tsx` to compose the 4 zone components and mapSlot in the rigid 100vw x 100vh 5-zone grid, preserving all required IDs (`command-bar`, `spatial-dock`, `map-canvas`, `receptor-inspector`, `temporal-scrubber`), data attributes (`data-zone`, `data-pitch="0"`, etc.), and test tokens. Ensure `src/workstation/MapCanvas.tsx` cleanly delegates to or re-exports `src/map/MapCanvas.tsx`.
5. Connect into `src/App.tsx`.
6. Run all verification commands:
   - `npm run check:workstation` (MUST pass with `workstation-check ok stations=74/5 render-ok`, exit code 0)
   - `npm run typecheck` (MUST pass with exit code 0)
   - `npm run build` (MUST pass with exit code 0)
   - `python tests/challenge_contrast.py` (MUST pass 56/56 pairs, 0 banned dependencies, exit code 0)
   - `python tests/challenge_build_styling_r2.py` (MUST pass 0 banned imports, 0 emojis, exit code 0)
   - `npx tsx tests/unit/test_challenger_m1m2.ts` (MUST pass 2095/2095 assertions)
   - `npx tsx tests/unit/test_challenger_adversarial_m1m2_r2.ts` (MUST pass 250/250 assertions)
   - `python tests/e2e/run_all_tests.py` (MUST pass 50/50 tests)
   - `python -m pytest tests/unit` (MUST pass 292/292 tests)
   - `python -m pytest tests/integration` (MUST pass 266/266 tests)
