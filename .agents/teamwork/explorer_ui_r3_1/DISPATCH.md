## 2026-11-15T19:50:43Z
You are Explorer 1 (Frontend UI & Layout specialist) for the Punjab Air Quality project.

## Mandatory Reading & Authoritative Sources
- Read ORIGINAL_REQUEST.md at: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\ORIGINAL_REQUEST.md
- Read PROJECT.md at: c:\Users\Asif\Downloads\Punjab Air Quality\PROJECT.md
- Working Directory: c:\Users\Asif\Downloads\Punjab Air Quality
- Your State Folder: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\explorer_ui_r3_1

## Mission & Specific Investigation Tasks
Investigate the frontend codebase thoroughly and produce verified evidence chains for:
1. DYNAMIC TIMELINE ADVANCEMENT:
   - Investigate timeline scrubbing & date management in `src/components/scrubber/TimelineScrubber.tsx`, `src/workstation/state.ts`, `src/domain/math/qc.ts`, `src/services/`, and any data files.
   - Identify where dates/timestamps are currently fixed/hardcoded to a historical date.
   - Propose a clean, production-grade architecture for dynamically adapting and extending the timeline day-to-day up to current time (Date.now()) while preserving historical data navigation.
2. POLLUTANT SPECIES BAR TAB SCOPING:
   - Locate where the pollutant species bar/selector is rendered (`src/components/command/CommandBar.tsx`, `src/App.tsx`, etc.).
   - Map workstation tab routing/state (Main Console vs other tabs/views).
   - Find why the pollutant species bar shows across all tabs and design a surgical fix so it displays exclusively on the Main Console tab.
3. RED BLOCK ARTIFACT IN HEADER:
   - Inspect the header and Zone 1 Command Bar components and styles.
   - Identify the exact HTML element, CSS class, or component causing a red block artifact (e.g. misconfigured error state, broken SVG, placeholder styling, or styling conflict).
4. HOURLY HEATMAP VIEWPORT FIT & SCROLLING:
   - Locate the Hourly Heatmap component (search across `src/components/` and related views).
   - Diagnose why it overflows or fails to scroll/fit cleanly in its container. Check flex/grid layouts, min-width/max-width, overflow properties, and CSS rules. Provide exact CSS/JSX fixes.
5. STRICT USER FEATURE PRESERVATION:
   - Check all files you inspect against the mandate: ZERO deletions of existing user features.

Document all file paths, exact line numbers, code snippets, and recommended surgical changes in your handoff report:
`c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\explorer_ui_r3_1\handoff.md`.
Use send_message to report completion when done.
