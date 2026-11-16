## 2026-11-15T20:13:15Z
You are Worker 1 (Frontend UI & Layout Specialist) for the Punjab Air Quality project.

## Mandatory Reading & Authoritative Sources
- Read ORIGINAL_REQUEST.md at: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\ORIGINAL_REQUEST.md
- Read PROJECT.md at: c:\Users\Asif\Downloads\Punjab Air Quality\PROJECT.md
- Read SCOPE.md at: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\orchestrator_3\SCOPE.md
- Read Explorer 1's detailed handoff report at: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\explorer_ui_r3_1\handoff.md
- Working Directory: c:\Users\Asif\Downloads\Punjab Air Quality
- Your State Folder: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\worker_ui_r3_1

## MANDATORY INTEGRITY WARNING
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## CRITICAL USER PRESERVATION DIRECTIVE
"I HAVE IMPLEMENTED A LOT OF FEATURES, IF YOU WANT TO DELETE ANY OF THE CODE VERIFY THAT FROM ME FIRST. I DONT WANT YOU FUCKING EVERYTHING UP."
Strictly preserve all existing user-implemented features, components, routes, pipelines, or domain logic with zero deletions and zero dummies. Do NOT delete or strip out existing code or features.

## Exclusive Write Ownership
You own and may ONLY edit the following frontend files:
- `src/frontend/static/css/tokens.css`
- `src/frontend/static/js/ui.js`
- `src/frontend/static/js/app.js`
- `src/frontend/static/js/api.js`
- `src/workstation/state.ts`
- `src/components/scrubber/TimelineScrubber.tsx`
- `src/components/command/CommandBar.tsx`
- `src/App.tsx`
DO NOT touch any backend or pipeline files.

## Detailed Tasks to Implement
1. DYNAMIC TIMELINE ADVANCEMENT:
   - Follow Explorer 1's blueprint: Remove rigid 216/215 bounds in `state.ts`, `TimelineScrubber.tsx`, `App.tsx`, and `app.js`.
   - Update `state.ts` `scrubberReadout()` to accept `totalHours` (defaults to 216).
   - Update `TimelineScrubber.tsx` to accept `totalHours?: number` and set `<Slider max={Math.max(0, totalHours - 1)}>`.
   - Update `App.tsx` to calculate `totalHours = Math.max(hours.length, 216)` and use it in `onStep` and `onScrub`.
   - Update `app.js` to dynamically set `scrubRange.max` and `gridScrubRange.max` from `this.state.totalHours = hourly.hours ? hourly.hours.length : 216;`. In live mode, default to latest hour while allowing scrubbing to past hours.
   - Update `ui.js` heatmap column rendering to `totalCols = hours.length` (don't clamp to 216).
2. POLLUTANT SPECIES BAR TAB SCOPING:
   - In `src/frontend/static/js/ui.js` (around lines 405-410), update the tab check so `.zone-2-pollutants` displays ONLY when `viewName === 'console'`:
     `polNav.style.display = (viewName === 'console') ? 'flex' : 'none';`
   - It must be hidden on `lahore`, `heatmap`, `transboundary`, `fires`, and `grid`.
3. RED BLOCK ARTIFACT REMOVAL IN HEADER:
   - In `src/frontend/static/css/tokens.css` (lines 370-382), refactor `.provincial-aqi-badge` into an institutional status pill:
     `font-size: 13px; font-weight: 700; padding: 3px 8px; border-radius: var(--radius-sm); background-color: rgba(112, 48, 160, 0.18); color: #ffffff; border: 1px solid var(--border-subtox); display: inline-flex; align-items: center; gap: 6px; letter-spacing: 0.04em; text-transform: uppercase;`
     Add `.provincial-aqi-badge .badge-dot { width: 7px; height: 7px; border-radius: 50%; display: inline-block; }`.
   - In `src/frontend/static/js/ui.js` (lines 561-578), update `#provincialAqiBadge` so that instead of solid `style.backgroundColor = rgb(tier.color)`, set `style.backgroundColor = rgba(rgb, 0.18)`, `style.borderColor = rgba(rgb, 0.8)`, and inject the indicator dot `<span class="badge-dot" style="background: rgb(${rgb})"></span>`.
   - In `src/components/command/CommandBar.tsx` (lines 118-128), update the hazardous alert badge to `variant="outline" border border-red-500/60 bg-red-500/15 text-red-400`.
4. HOURLY HEATMAP VIEWPORT FIT & SCROLLING:
   - In `src/frontend/static/css/tokens.css` (lines 1424-1471):
     Set `#panel-heatmap` to:
     `height: calc(100vh - 72px); max-height: calc(100vh - 72px); min-height: 0; display: flex; flex-direction: column; padding: 10px 14px; box-sizing: border-box; overflow: hidden;`
     Set `.heatmap-container` to:
     `flex: 1 1 0; min-height: 0; max-height: none; width: 100%; overflow: auto; overscroll-behavior: contain; border: 1px solid var(--border-subtle); background: var(--bg-panel);`
     Set `table.heatmap-table th.sticky-district` corner to `z-index: 5;`
5. CROSS-BORDER FALLBACK COORDINATES IN API.JS:
   - In `src/frontend/static/js/api.js` (lines 143-150), ensure the fallback array includes `latitude` and `longitude` fields for all 6 anchor cities.
