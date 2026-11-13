## 2026-11-11T13:15:11Z
You are an Explorer investigating Workstation Layout Shell, HTML Entrypoint, and Shared TypeScript Domain Contracts for Milestone 1 of the EPA Punjab Air Quality Workstation.
Working directory: c:\Users\Asif\Downloads\Punjab Air Quality
State folder: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\explorer_m1_3

MANDATORY READING:
- c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\ORIGINAL_REQUEST.md
- c:\Users\Asif\Downloads\Punjab Air Quality\PROJECT.md
- c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\sub_orch_m1\SCOPE.md
- Relevant docs: docs/SYSTEM_ARCHITECTURE.md, docs/TRANSFORMATION_LOGIC_SPEC.md, docs/UI_UX_SPECIFICATION.md

Tasks:
1. Examine the required 5-zone workstation layout:
   - Rigid 100vw x 100vh CSS Grid container
   - Zone 1: Command Bar (top)
   - Zone 2: Spatial Control Dock (left)
   - Zone 3: Central Map Canvas (center)
   - Zone 4: Receptor Inspector (right)
   - Zone 5: Temporal Playback Scrubber (bottom)
   - Scoped CSS Modules (src/styles/grid.module.css)
   - Main layout container components (src/App.tsx, src/main.tsx)
2. Examine index.html:
   - Proper viewport, UTF-8, title without emojis
   - Google Fonts links or web font loading for IBM Plex Sans, IBM Plex Sans Condensed, IBM Plex Mono
   - Root mount element #root
3. Define Canonical TypeScript Contracts in src/domain/types/index.ts:
   - Station (fixed vs mobile, aerodrome flags, coordinates [lon, lat])
   - District (id, name, centroid [lon, lat], boundary GeoJSON / coordinates, is_estimated, etc.)
   - Observation & Telemetry (9 statutory pollutants: AQI, PM2.5, PM10, NO2, SO2, CO, O3, NO, NOX; timestamp, quality flags)
   - WindVector (speed, direction, u, v, calm, dropout, blacklisted)
   - BorderNode (transboundary vector & normal vector)
   - PEPCGrade & Color scale types
   - LayerId and Workstation UI state contracts
4. Write your detailed handoff report with exact component structures and TypeScript definitions to:
   c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\explorer_m1_3\handoff.md
5. Notify the orchestrator with send_message when complete.
