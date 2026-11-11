# Plan: Punjab Air Quality System

## Phase 0: Survey & Scope Mapping
- [ ] Dispatch 3 Explorers / Spec Miners in parallel:
  - Explorer 1: Examine existing workspace (`index.html`, `collector/`, archive requirements R1, and baseline data extraction)
  - Explorer 2: Examine scientific specs (`docs/TRANSFORMATION_LOGIC_SPEC.md`, mathematical models: IDW, CPF, Flux, PEPC)
  - Explorer 3: Examine system architecture, data pipelines, backend APIs, and UI/UX specs (`docs/ARCHITECTURE_OVERVIEW.md`, `docs/DATA_SOURCES_AND_STREAMS.md`, `docs/DATA_PIPELINES_ARCHITECTURE.md`, `docs/SYSTEM_ARCHITECTURE.md`, `docs/UI_UX_SPECIFICATION.md`)
- [ ] Synthesize explorer findings into `PROJECT.md` at project root with full Feature Inventory, Architecture, Milestones, and Interface Contracts.

## Phase 1: Dual Track Decomposition & Execution
- Implementation Track:
  - M1: Archival of original system (`index.html`, `collector/` -> `original System/`)
  - M2: Scientific Transformation Engine (IDW, CPF polar rose, flux, PEPC breakpoints with pure functions)
  - M3: Data Pipelines & Ingestion Engine (Live external feeds, CSV import/validation adapter, baseline templates from original artifacts)
  - M4: Core Services, Domain Models, & Backend APIs (Clean architecture, REST/FastAPI or Node/Express endpoints for station metadata, live readings, historical data, spatial interpolation)
  - M5: Component-Driven UI/UX Dashboard (Map, station filters, pollutant breakdown, wind/flux indicators, historical trends)
  - M6: Final Integration & E2E Validation (100% tests passing, adversarial coverage hardening)
- E2E Testing Track:
  - Independent E2E Test Suite design (Tiers 1-4: Feature, Boundary, Pairwise, Real-World Scenarios) -> `TEST_READY.md`

## Phase 2: Final Verification & Reporting
- [ ] Pass 100% E2E test suite.
- [ ] Adversarial coverage hardening (Tier 5).
- [ ] Forensic integrity audit.
- [ ] Final human report and send_message to parent.
