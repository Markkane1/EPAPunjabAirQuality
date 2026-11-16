# BRIEFING — 2026-11-15T20:10:00Z

## Mission
Investigate frontend codebase for dynamic timeline advancement, pollutant bar tab scoping, header red block artifact, and hourly heatmap viewport fit & scrolling.

## 🔒 My Identity
- Archetype: Teamwork explorer
- Roles: Frontend UI & Layout specialist
- Working directory: c:\Users\Asif\Downloads\Punjab Air Quality
- State folder: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\explorer_ui_r3_1
- Original parent: f2fa7191-2b95-4f46-b1cb-ef6f552d742b
- Milestone: Investigation & Analysis

## 🔒 Key Constraints
- Read-only investigation — do NOT implement
- Strict user feature preservation: ZERO deletions of existing user features
- Strict file isolation: write ONLY to `.agents/teamwork/explorer_ui_r3_1/`

## Current Parent
- Conversation ID: f2fa7191-2b95-4f46-b1cb-ef6f552d742b
- Updated: 2026-11-15T20:10:00Z

## Investigation State
- **Explored paths**:
  - `src/App.tsx`, `src/workstation/state.ts`, `src/workstation/assemble.ts`, `src/workstation/WorkstationView.tsx`, `src/components/scrubber/TimelineScrubber.tsx`, `src/components/command/CommandBar.tsx`
  - `src/domain/math/qc.ts`, `src/services/api.ts`, `src/services/observation_service.py`
  - `src/frontend/dashboard.html`, `src/frontend/static/js/app.js`, `src/frontend/static/js/ui.js`, `src/frontend/static/css/tokens.css`
  - `tests/integration/test_frontend.py`
- **Key findings**:
  1. Dynamic Timeline Advancement: Found hardcoded 216/215 bounds in `src/workstation/state.ts` (lines 4-6, 225), `src/components/scrubber/TimelineScrubber.tsx` (line 138), `src/App.tsx` (lines 332, 338), `src/frontend/dashboard.html` (lines 119, 273), `src/frontend/static/js/app.js` (line 41), and `src/frontend/static/js/ui.js` (lines 1027-1028). Baseline data was already extended to 384 hours (Nov 1-16). Designed dynamic architecture extending to `now` (Date.now()) with dynamic totalHours.
  2. Pollutant Species Bar Scoping: Located in `src/frontend/dashboard.html` (lines 65-70) and toggled in `src/frontend/static/js/ui.js` (lines 405-409). Currently set to `polNav.style.display = (viewName === 'grid') ? 'none' : 'flex'`. Changing condition to `(viewName === 'console') ? 'flex' : 'none'` strictly confines it to Main Console.
  3. Red Block Artifact in Header: Identified in `src/frontend/dashboard.html` (`#provincialAqiBadge`, line 35) & `src/frontend/static/css/tokens.css` (lines 370-382) where `background-color: var(--pepc-very-unhealthy)` and `ui.js` line 572 dynamically sets `style.backgroundColor = 'rgb(192, 0, 0)'` (Hazardous red). In React `CommandBar.tsx` (lines 118-128), hazardous alert badge is rendered with solid `#C00000` background.
  4. Hourly Heatmap Viewport Fit & Scrolling: Located in `src/frontend/dashboard.html` (`#panel-heatmap`, `#heatmapContainer`, `#heatmapTable`) and `src/frontend/static/css/tokens.css` (lines 1424-1470). Conflict between `min-height: 480px` and `max-height: calc(100vh - 220px)` on `.heatmap-container` causes vertical window overflow. Table needs `flex: 1 1 0; min-height: 0; overflow: auto;` and `th.sticky-district` needs `z-index: 5` to prevent header corner clipping.
  5. Strict Feature Preservation: Verified all existing DOM IDs and capabilities match `test_frontend.py` contract.
- **Unexplored areas**: None, all 5 mission requirements investigated with line-numbered evidence chains.

## Key Decisions Made
- Confirmed that the FastAPI gateway serves `src/frontend/dashboard.html` as the primary operational dashboard at `GET /`, while also maintaining the React workstation build. Documented exact surgical fixes for both representations.

## Artifact Index
- DISPATCH.md — Initial dispatch message
- BRIEFING.md — Persistent context
- progress.md — Liveness heartbeat
- handoff.md — Final investigation report
