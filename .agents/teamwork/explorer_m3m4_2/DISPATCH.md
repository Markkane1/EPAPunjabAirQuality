## 2026-11-14T09:44:21Z
You are Explorer 2 (`explorer_m3m4_2`).
Your state folder: `c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\explorer_m3m4_2`
Working directory: `c:\Users\Asif\Downloads\Punjab Air Quality`
Original Request path: `c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\ORIGINAL_REQUEST.md`
Scope document path: `c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\orchestrator_2_gen1\SCOPE.md`
Project document path: `c:\Users\Asif\Downloads\Punjab Air Quality\PROJECT.md`

MANDATORY FIRST STEP: Read `c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\ORIGINAL_REQUEST.md` before starting work.

TASK:
Perform technical exploration and design the exact implementation plan for Milestone M3-M4: Workstation UI Components across Zones 1 to 5.

SPECIFIC OBJECTIVES:
1. Investigate existing components, styles, and state management in `src/`:
   - Check `src/styles/tokens.css`, `src/styles/grid.module.css`, `src/styles/typography.css`.
   - Check `src/components/common/icons.tsx` and any other existing components.
   - Check `src/workstation/` (e.g. `WorkstationView.tsx`, `state.ts`) and `src/App.tsx`.
   - Check what `npm run check:workstation` executes and expects.
2. Formulate the concrete implementation details for each Zone component:
   - Zone 1: `src/components/command/CommandBar.tsx`:
     - System identity & connection status badge (LIVE vs FALLBACK ARCHIVE).
     - Assertive ARIA Live Alert Region (`aria-live="assertive"`) for hazardous episodes and 500 ceiling clamp.
     - 9-pollutant statutory switcher (AQI, PM2.5, PM10, NO2, SO2, CO, O3, NO, NOX) with regulatory units and PEQS 24h limits.
     - CSV Ingestion modal trigger & QA summary drawer toggle.
   - Zone 2: `src/components/dock/SpatialDock.tsx`:
     - 5-layer visibility toggles with icons from `src/components/common/icons.tsx`.
     - Transboundary mass-balance attribution split bar (Cross-Border vs Domestic).
     - 41-district statutory ranking table with current concentration, PEPC badge, IDW estimation indicator, and row-click map centering.
   - Zone 4: `src/components/inspector/ReceptorInspector.tsx`:
     - Station / District metadata card.
     - 9-parameter statutory table with 75% completeness rule badge (`QC_INCOMPLETE_75`).
     - 16-sector CPF Polar Wind Rose ($22.5^\circ$ sectors, calm wind exclusion, $P_{75}$ threshold, $N_k < 6$ small-sample suppression to muted 10px circular stub, 0.25 null circle).
     - 216h QC time-series chart with PEQS threshold line, highlighting 7h median spike and 3h logger hold anomalies.
   - Zone 5: `src/components/scrubber/TimelineScrubber.tsx`:
     - 216-hour timeline range slider with sub-hourly decimal positions ($fp \in [0.00, 215.00]$).
     - Transport controls (Play/Pause, Step ±1h, speed 0.35x, 0.8x, 1.6x) and keyboard shortcuts.
     - Max AQI horizon sparkline behind scrubber track.
     - Sub-hourly continuous lerp between hour $i$ and $i+1$ for smooth 60 FPS playback.
3. Formulate how all Zone components connect into `src/App.tsx` and `src/workstation/WorkstationView.tsx` within the rigid 100vw x 100vh 5-zone grid, strictly adhering to IBM Plex typography, WCAG 2.1 AAA contrast, zero emojis, and zero banned dependencies.
4. Document the exact component props, local/shared state contracts, and event handlers.

DO NOT write source code to production files. You are an Explorer. Write your comprehensive analysis and technical blueprint to `c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\explorer_m3m4_2\handoff.md` and send a completion message to the caller with a summary and the path.
