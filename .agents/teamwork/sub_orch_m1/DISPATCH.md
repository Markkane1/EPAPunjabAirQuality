# Dispatch Assignment: Milestone 1 Sub-Orchestrator

## Role: Sub-Orchestrator for Milestone 1 (Foundation, Tooling & Design Tokens)
## Working Directory: c:\Users\Asif\Downloads\Punjab Air Quality
## State Folder: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\sub_orch_m1
## Scope Document: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\sub_orch_m1\SCOPE.md
## Global Project Document: c:\Users\Asif\Downloads\Punjab Air Quality\PROJECT.md
## Original Request Path: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\ORIGINAL_REQUEST.md

## Scope & Objective
Own and complete **Milestone 1: Foundation, Tooling & Design Tokens** for the EPA Punjab Air Quality Institutional Frontend Workstation.

### Specific Deliverables
1. **Tooling & Dependencies (`package.json`, `tsconfig.json`, `vite.config.ts`)**:
   - Initialize clean React 18 + TypeScript + Vite project at project root.
   - Install production dependencies: `react`, `react-dom`, `maplibre-gl`, `@deck.gl/core`, `@deck.gl/layers`, `@deck.gl/mapbox`, etc.
   - Strictly prohibit and verify absence of banned dependencies: `tailwindcss`, `lucide-react`, `heroicons`, `feather-icons`.
   - Setup `npm run build` and `tsc` ensuring clean build with zero errors.
2. **Typography & Entrypoint (`index.html`, `src/styles/typography.css`)**:
   - `index.html` loading exclusively `IBM Plex Sans`, `IBM Plex Sans Condensed`, and `IBM Plex Mono` (via Google Fonts or @font-face).
   - Zero emojis in HTML, title, or code.
   - Enforce `font-variant-numeric: tabular-nums` on all numeric readouts in `src/styles/typography.css`.
3. **WCAG 2.1 AAA Design Tokens (`src/styles/tokens.css`)**:
   - All text/surface color pairs must achieve $\ge 7.0:1$ luminance contrast.
   - Fix existing failures identified in survey: `--ink-secondary` (dark & light), `--ink-tertiary`, and light mode `--accent`.
   - Structural hairlines (1px solid), 0px border-radius / crisp scientific instrument aesthetics, no drop shadows or backdrop-filter blurs.
4. **Workstation Layout Shell (`src/styles/grid.module.css`, `src/App.tsx`, `src/main.tsx`)**:
   - Rigid 100vw x 100vh CSS Grid container with 5 discrete zones: Command Bar, Spatial Dock, Map Canvas, Receptor Inspector, Temporal Scrubber.
   - Scoped CSS Modules.
5. **Shared TypeScript Contracts (`src/domain/types/index.ts`)**:
   - Define canonical types for Stations, Districts, Observations, WindVectors, Airsheds, LayerIds, PEPCGrades.

### Workflow
As Sub-Orchestrator, follow the Project Pattern iteration loop:
1. Initialize `SCOPE.md`, `BRIEFING.md`, and `progress.md`.
2. Spawn 3 Explorers in parallel to design the implementation and file layout.
3. Spawn a Worker to implement all deliverables and run build/test commands.
4. Spawn 2 Reviewers independently to verify WCAG AAA contrast, build, typography, and lack of banned dependencies.
5. Spawn 2 Challengers to empirically verify contrast ratios and build artifacts.
6. Spawn a Forensic Auditor (`teamwork_auditor`) to ensure genuine implementation with zero cheating or hardcoded bypasses.
7. Record gate verdicts in `GATE_STATUS.md`. Pass only if all checks pass and audit is clean.
8. Deliver handoff to parent (`854942e9-be47-4067-87d5-db3fbea7749d`).
