## 2026-11-15T20:46:47Z
You are Challenger 1 (Frontend UI Empirical Challenger) for the Punjab Air Quality project.

## Mandatory Reading & Authoritative Sources
- Read ORIGINAL_REQUEST.md at: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\ORIGINAL_REQUEST.md
- Read PROJECT.md at: c:\Users\Asif\Downloads\Punjab Air Quality\PROJECT.md
- Read SCOPE.md at: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\orchestrator_3\SCOPE.md
- Read Worker 1's handoff report at: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\worker_ui_r3_1\handoff.md
- Working Directory: c:\Users\Asif\Downloads\Punjab Air Quality
- Your State Folder: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\challenger_ui_r3_1

## Mission & Empirical Stress-Testing Tasks
Write empirical stress-testing scripts and assertions to challenge Worker 1's frontend implementations:
1. Dynamic Timeline Advancement:
   - Stress-test timeline bounds: test hourIndex at 0, 215, 216, 383, 384, and dynamic totalHours.
   - Verify that `<Slider max={...}>` in `TimelineScrubber.tsx`, `scrubberReadout()` in `state.ts`, and `scrubRange.max` in `app.js` correctly handle dynamic hours without hardcoded 216 truncation.
   - Verify that stepping delta wraps correctly around `totalHours` and sub-hourly lerp functions smoothly.
2. Pollutant Species Bar Tab Scoping:
   - Simulate view switching across all 6 workstation tabs: `console`, `lahore`, `heatmap`, `transboundary`, `fires`, `grid`.
   - Assert that `.zone-2-pollutants` displays `'flex'` ONLY when `viewName === 'console'`, and `'none'` for all other 5 tabs.
3. Red Block Artifact in Header:
   - Inspect `.provincial-aqi-badge` in `tokens.css` and `ui.js`. Assert that background is translucent (`rgba(rgb, 0.18)`), border is present, and `.badge-dot` exists.
   - Verify that text contrast against the dark institutional background meets WCAG AAA standard (>= 7.0:1).
   - Inspect `CommandBar.tsx` hazardous alert badge; verify it uses outline styling without opaque red block background.
4. Hourly Heatmap Viewport Geometry:
   - Verify CSS sizing of `#panel-heatmap` and `.heatmap-container`: assert `height: calc(100vh - 72px)`, `overflow: hidden` on panel, and `overflow: auto` on container.
   - Assert `th.sticky-district` has `z-index: 5` to prevent overlap during diagonal scrolling.
5. Cross-Border Fallback Coordinates in `api.js`:
   - Inspect fallback array in `api.js`; assert that all 6 cities have non-null numeric `latitude` and `longitude` fields.
6. Run frontend tests:
   - `npm run build`
   - `npm run check:workstation`
   - `npx tsx tests/unit/test_challenger_m3m4.ts`

Deliver your verdict (APPROVE or REQUEST_CHANGES) with assertion counts and test outputs in:
`c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\challenger_ui_r3_1\handoff.md`.
Use send_message to report completion.
