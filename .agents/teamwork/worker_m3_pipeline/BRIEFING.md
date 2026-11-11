# BRIEFING — 2026-11-10T13:22:00Z

## Mission
Implement Milestone M3: Pydantic v2 schemas for raw/normalized observations and user CSVs, modular ingestion engines (EPA Punjab, METAR, SYNOP, Open-Meteo, Fallback template engine, CSV adapter), and integration tests.

## 🔒 My Identity
- Archetype: worker
- Roles: implementer, qa, specialist
- Working directory: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\worker_m3_pipeline\
- Original parent: c384b499-9dff-40dc-b63d-721df47da08f
- Milestone: M3 (Data Pipelines & CSV Ingestion Engine)

## 🔒 Key Constraints
- DO NOT CHEAT: Genuine implementation only. No hardcoded test results, no dummy facade implementations, no circumventing logic.
- File ownership: Exclusively own `src/domain/schemas/`, `src/pipelines/`, `tests/integration/test_pipelines.py`, `tests/integration/test_csv_adapter.py`.
- Do NOT touch `src/domain/math/` (owned by M2 worker).
- Standard SI units, Pydantic v2 validation, Punjab coordinate boundaries [27.0, 35.5]°N, [69.0, 76.5]°E, physical limits (le=5000.0, smog tagging >1000 ug/m3).
- EpA Punjab User-Agent `EMC-EPA-Punjab-AQ-dashboard/1.0`, fallback on network failure to baseline templates.

## Current Parent
- Conversation ID: c384b499-9dff-40dc-b63d-721df47da08f
- Updated: 2026-11-10T13:22:00Z

## Task Summary
- **What to build**:
  - `src/domain/schemas/`: `RawStationMeasurement`, `NormalizedObservation`, `UserCSVRow`
  - `src/pipelines/`: `base.py`, `epa_punjab.py`, `metar.py`, `synop.py`, `open_meteo.py`, `fallback_engine.py`, `csv_adapter.py`
  - `tests/integration/`: `test_pipelines.py`, `test_csv_adapter.py`
- **Success criteria**: 100% pass on pytest with comprehensive genuine logic, fallback handling, error collection, coordinate clipping/tagging, and unit conversions.
- **Interface contracts**: `docs/DATA_SOURCES_AND_STREAMS.md`, `docs/DATA_PIPELINES_ARCHITECTURE.md`, `PROJECT.md`
- **Code layout**: `PROJECT.md`

## Key Decisions Made
- [TBD - will document during investigation and design]

## Artifact Index
- `src/domain/schemas/` — Pydantic schemas
- `src/pipelines/` — Ingestion pipeline workers and adapters
- `tests/integration/` — Integration test suite

## Change Tracker
- **Files modified**: None yet
- **Build status**: Untested
- **Pending issues**: Initial design and implementation pending

## Quality Status
- **Build/test result**: Pending
- **Lint status**: Clean
- **Tests added/modified**: Pending

## Loaded Skills
None
