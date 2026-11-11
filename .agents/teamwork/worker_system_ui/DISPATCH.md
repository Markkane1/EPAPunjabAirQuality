## 2026-11-10T11:18:08Z

You are the System & UI Architect (teamwork_worker).
Your working directory is: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\worker_system_ui\
Read ORIGINAL_REQUEST.md at: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\ORIGINAL_REQUEST.md
Read PROJECT.md at: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\orchestrator\PROJECT.md

Read input survey findings:
1. c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\explorer_architecture\architecture_ui_report.md
2. c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\explorer_algorithms\transforms_report.md
3. c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\spec_miner_sources\sources_catalog.md

Review specialized design skills:
- Code Simplification: C:\Users\Asif\.gemini\config\plugins\agent-skills\skills\code-simplification\SKILL.md
- Impeccable UI Design: C:\Users\Asif\.gemini\config\skills\impeccable\SKILL.md
- API & Interface Design: C:\Users\Asif\.gemini\config\plugins\agent-skills\skills\api-and-interface-design\SKILL.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

STRICT CONSTRAINT: DO NOT modify index.html, collector/collector.py, or any existing codebase files. Your deliverables must be comprehensive, production-grade architectural and specification documents written in Markdown with complete Mermaid system flowcharts, schemas, component hierarchies, and visual design token tables.

Write Ownership (You exclusively own and will create these files):
1. `c:\Users\Asif\Downloads\Punjab Air Quality\docs\SYSTEM_ARCHITECTURE.md`
   - Detailed specification for Requirement R4:
   - Clean, decoupled, multi-tier system architecture replacing monolithic 9.61 MB index.html:
     * Ingestion Tier, Data Storage & Analytics Tier, API Service Tier, Client Presentation Tier.
     * Service boundaries, data contracts, and interaction models.
     * Database schema design: TimescaleDB hypertables for hourly observations, spatial postgis tables for district/station geometries, Redis geospatial cache.
     * API design: REST endpoints and WebSocket/SSE real-time streams (complete OpenAPI / JSON schemas).
     * Code Simplification (/code-simplification): Eliminating 60+ global variables, redundant animation loops, string-based innerHTML DOM thrashing, triplicated IDW calculations, and bloated embedded Base64/JSON.
     * Comprehensive Mermaid diagrams: End-to-end dataflow, deployment architecture, and component dependency graphs.

2. `c:\Users\Asif\Downloads\Punjab Air Quality\docs\UI_UX_SPECIFICATION.md`
   - Detailed specification for Requirement R5:
   - Impeccable UI/UX architecture tailored specifically for air quality and meteorological monitoring (/impeccable):
     * Information architecture & visual hierarchy (Command header, KPI summary strips, interactive multi-layer map canvas, temporal scrubber/playback controller, detailed station telemetry drawer, transboundary plume analytics panel).
     * Visual design system: Color tokens (PEQS / EPA Punjab AQI continuous ramps, dark-mode atmospheric palette, high-contrast accessibility WCAG AAA), typography scale, spacing grid (8pt).
     * State management architecture: Single source of truth reactive store (Zustand / Redux Toolkit / Vue Pinia pattern), time slice slicing, optimistic updates, query caching.
     * High-performance real-time visualization layer: Decoupled multi-layered canvas/WebGL architecture (static vector basemap layer, GPU-accelerated continuous field rasterizer, 1300-particle wind advection engine, interactive station glyphs, dynamic CPF polar rose renderer).
     * Interaction models: Scrubbing 216+ hours with sub-hourly lerp, station selection, pollutant switching, spatial boundary inspection, mobile responsive layout breakpoints (desktop, tablet, mobile).

3. `c:\Users\Asif\Downloads\Punjab Air Quality\docs\ARCHITECTURE_OVERVIEW.md`
   - Master architecture blueprint & synthesis:
   - Executive architectural summary bridging R1, R2, R3, R4, R5, and R6.
   - Comprehensive cross-reference index to all specifications in `docs/`.
   - Migration roadmap: Phase-by-phase implementation guide from legacy index.html to modern decoupled stack.
   - Non-invasive compliance verification summary.

When finished, compile your handoff.md in your working directory and notify the orchestrator with send_message.
