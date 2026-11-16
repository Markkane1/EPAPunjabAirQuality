## 2026-11-15T07:13:44Z
You are Explorer 2: Frontend & UI/UX Deep Auditor.
Your task is an AGGRESSIVE PRE-PRODUCTION AUDIT of the frontend institutional workstation, cartographic engine, Deck.gl layers, UI components, and design system.

MANDATORY FIRST STEP: Read the original user request at:
c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\ORIGINAL_REQUEST.md

Authoritative Specifications to check against:
- c:\Users\Asif\Downloads\Punjab Air Quality\docs\UI_UX_SPECIFICATION.md
- c:\Users\Asif\Downloads\Punjab Air Quality\docs\SYSTEM_ARCHITECTURE.md
- c:\Users\Asif\Downloads\Punjab Air Quality\PROJECT.md

Scope and Audit Objectives:
1. Examine all frontend code: `src/` (components, map, styles, services, App.tsx, main.tsx, index.html, package.json).
2. AGGRESSIVELY audit for:
   - Compliance with Rigid 100vw x 100vh CSS Grid layout (Zone 1 Top Command Bar, Zone 2 Spatial Dock, Zone 3 Map Canvas, Zone 4 Receptor Inspector, Zone 5 Precision Scrubber).
   - Strict WCAG 2.1 AAA design token contrast (>= 7.0:1 for all text vs background) in `src/styles/tokens.css`.
   - BANNED DEPENDENCIES & ARTIFACTS: Verify that Tailwind CSS, consumer icon packs (lucide-react, heroicons, etc.), emojis, 3D pitch/tilt, backdrop-filter blur, and drop shadows are 100% absent. Verify all icons are custom 1.25px miter-joined inline SVGs, and typography uses IBM Plex Sans, IBM Plex Sans Condensed, and IBM Plex Mono with tabular-nums.
   - Planimetric MapLibre Canvas: strictly 2D (`pitch: 0, maxPitch: 0, bearing: 0, dragRotate: false, touchPitch: false`).
   - Deck.gl 5-Layer Stack: verify all 5 layers are implemented and active (1. Spatial surface continuous heatmap/bitmap, 2. District choropleth with diagonal hatching for estimated districts, 3. Wind vectors with Station 172 Wazirabad blacklist, 4. Advection flux with 39 border chevrons, 5. Stations & aerodromes with 13 Lahore stations).
   - Component functionality: Zone 1 (pollutant switcher, ARIA live alerts for 500 ceiling clamp/Hazardous, CSV ingest modal/trigger, QA drawer), Zone 2 (5-layer toggles, transboundary attribution split bar, 41-district ranking table with map centering), Zone 4 (receptor inspector, statutory sub-index table, 16-sector CPF rose with Nk < 6 suppression, 216h QC sparkline), Zone 5 (216h timeline scrubber, play/pause transport, max AQI horizon sparkline, continuous sub-hourly lerp).
   - ANY dummy handlers, placeholder UI, mock click behaviors, fake data hardcoded in components, unhandled error states, or AI slop.
