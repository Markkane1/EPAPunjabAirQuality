# Plan: Remediation & Production Hardening of User Mandates

## Objectives
Address all 7 user mandates with production rigor:
1. Dynamic Timeline Advancement (system must adapt and extend day to day up to now).
2. Pollutant Species Bar scoped exclusively to Main Console tab.
3. Remove red block artifact in header.
4. Hourly Heatmap scrolling / viewport fit.
5. Cross-border AQI anchor cities displaying distinct, accurate anchor values.
6. Real Data from ALL pipelines (zero simulation generators, zero synthetic mocks, zero fake fallbacks; explicit degraded/unavailable status on failure).
7. Strict preservation of all existing user-implemented features (zero deletions, zero dummies).

## Phases

### Phase 1: Parallel Exploration (3 Explorers)
- **Explorer 1 (Frontend UI & Layout Focus)**:
  - Investigate Timeline Scrubber date handling across frontend & backend. Identify where fixed dates are hardcoded and how to make the timeline dynamic (sliding window up to `Date.now()`).
  - Investigate Pollutant Species Bar visibility across tabs (find tab routing/state and ensure it renders only in Main Console).
  - Investigate Header elements to find the "red block artifact" (CSS, HTML, styling, or misrendered badge).
  - Investigate Hourly Heatmap component layout, parent container CSS, scrolling, flex/grid overflow.
- **Explorer 2 (Real Data Pipelines & Simulation Elimination Focus)**:
  - Scan all pipeline code in backend and frontend: EPA Punjab, NOAA METAR, WMO SYNOP, ECMWF IFS, NASA FIRMS VIIRS, IQAir AirVisual, CAMS.
  - Locate any synthetic generators, mocks, simulated fallback values, or random/dummy math.
  - Formulate real endpoint ingestion mechanisms and explicit degraded/unavailable status flags (e.g. `service_status: "degraded" | "unavailable"` or similar) instead of fake data.
- **Explorer 3 (Cross-Border Anchor Cities & Preservation Audit Focus)**:
  - Investigate Cross-border AQI anchor cities (Amritsar, Jalandhar, Ludhiana, Bathinda, Firozpur, etc.) and where their fallback/telemetry values are assigned or duplicated.
  - Map every existing user feature, component, endpoint, and route to establish a strict preservation baseline so zero user code is accidentally deleted or damaged.

### Phase 2: Synthesis & Milestone Decomposition
- Synthesize findings from Explorers 1, 2, and 3.
- Define precise file boundaries and implementation steps in `SCOPE.md`.

### Phase 3: Worker Implementation (Surgical, Non-Destructive)
- Dispatch Worker(s) with Mandatory Integrity Warnings.
- Strictly preserve all existing user components, logic, and routes.
- Execute builds and tests.

### Phase 4: Independent Verification Panel & Gate
- 2 Reviewers.
- 2 Challengers.
- 1 Forensic Auditor (Binary Veto).
- Gate evaluation.

### Phase 5: Synthesis & Comprehensive Completion Claim
- Report back to parent orchestrator via `send_message`.
