## 2026-11-11T08:18:06Z
You are explorer_m5_arch, a read-only exploration agent.
Your working directory is: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\explorer_m5_arch
Orchestrator conversation ID: dfe9ab49-5b73-4c71-b636-dccdcc9080ee

MANDATORY INPUTS:
- ORIGINAL_REQUEST.md: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\ORIGINAL_REQUEST.md
- PROJECT.md: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\orchestrator\PROJECT.md
- docs/UI_UX_SPECIFICATION.md: c:\Users\Asif\Downloads\Punjab Air Quality\docs\UI_UX_SPECIFICATION.md
- docs/SYSTEM_ARCHITECTURE.md: c:\Users\Asif\Downloads\Punjab Air Quality\docs\SYSTEM_ARCHITECTURE.md
- original System/index.html: c:\Users\Asif\Downloads\Punjab Air Quality\original System\index.html
- Skills to incorporate:
  - impeccable: C:\Users\Asif\.gemini\config\skills\impeccable\SKILL.md
  - taste-skill: C:\Users\Asif\.gemini\config\skills\taste-skill\SKILL.md
  - frontend-ui-engineering: C:\Users\Asif\.gemini\config\plugins\agent-skills\skills\frontend-ui-engineering\SKILL.md

MISSION:
Investigate and design the complete UI/UX and Component Architecture for Milestone M5:
1. Examine docs/UI_UX_SPECIFICATION.md and original System/index.html to specify the 5-zone UI hierarchy:
   - Zone 1: Command Header & Navigation Strip (status pulse, composite AQI badge, PKT clock, sub-view navigation).
   - Zone 2: Primary Pollutant Switcher (9 statutory pollutants: AQI, PM2.5, PM10, NO2, SO2, CO, O3, NO, NOx).
   - Zone 3: Geographic Map Viewport Console (canvas container, floating HUD legend, 216-hour scrubber deck, animation controls).
   - Zone 4: Telemetry Sidebar (Provincial summary card, 24h sparkline, METAR airport cards, ranked district list, selected district drawer with 16-sector CPF polar rose).
   - Zone 5: Deep-Dive Panels (Synchronized 3x3 multi-pollutant grid, Lahore network focus drawer, virtualized 41x216 hourly heatmap matrix, transboundary remote sensing hub).
2. Incorporate /impeccable and /taste-skill standards:
   - Clean, mission-critical scientific instrument aesthetic.
   - Atmospheric dark/light theme tokens, 8pt spatial grid, high-contrast typography (Barlow Condensed, Source Sans 3, JetBrains Mono).
   - PEPC continuous 7-stop color ramp (0-50, 51-100, 101-150, 151-200, 201-300, 301-400, 401-500+) with WCAG 2.1 AAA text contrast.
3. Design the Component Hierarchy and State Management:
   - Modular, component-driven architecture (Vanilla ES Modules / Component Architecture or lightweight React/preact/Zustand pattern that can run directly in the browser without complex bundling).
   - Reactive state slices: Temporal (current hour 0-215, fractional lerp, play/pause, speed), Spatial (bounds, zoom, active district/station), Pollutant (active pollutant species), Telemetry (current readings, station cache, summary KPIs).
4. DO NOT WRITE OR MODIFY CODE. You are read-only.
5. Write your comprehensive architectural blueprint to c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\explorer_m5_arch\handoff.md and send a completion message back to the orchestrator.
