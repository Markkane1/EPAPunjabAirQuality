# Task Assignment: Milestone M3 — Data Pipelines & CSV Ingestion Engine

You are `worker_m3_pipeline` (Type: `teamwork_worker`).
Your working directory is: `c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\worker_m3_pipeline\`

## Authoritative Specifications
You MUST read:
1. `c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\ORIGINAL_REQUEST.md`
2. `c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\orchestrator\PROJECT.md`
3. `c:\Users\Asif\Downloads\Punjab Air Quality\docs\DATA_SOURCES_AND_STREAMS.md`
4. `c:\Users\Asif\Downloads\Punjab Air Quality\docs\DATA_PIPELINES_ARCHITECTURE.md`
5. `c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\spec_miner_architecture\handoff.md`

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## File Ownership
You exclusively own:
- `src/domain/schemas/` (Pydantic models for raw measurements, normalized observations, and user CSV records)
- `src/pipelines/` (all ingestion microservices, fallback template engine, and CSV adapter)
  - `src/pipelines/__init__.py`
  - `src/pipelines/base.py` (IngestionWorker interface)
  - `src/pipelines/epa_punjab.py`
  - `src/pipelines/metar.py`
  - `src/pipelines/synop.py`
  - `src/pipelines/open_meteo.py`
  - `src/pipelines/fallback_engine.py` (seeds schema-conforming templates from `data/baseline/`)
  - `src/pipelines/csv_adapter.py` (accepts, validates, and normalizes user CSVs)
- `tests/integration/test_pipelines.py`
- `tests/integration/test_csv_adapter.py`

Do NOT modify `src/domain/math/` (owned by M2 worker).

## Objectives
1. Implement Pydantic v2 schemas in `src/domain/schemas/`:
   - `RawStationMeasurement`: includes physical limits (`le=5000.0`, extreme smog tagging $>1000.0\ \mu\text{g/m}^3$).
   - `NormalizedObservation`: standard SI units, station coordinates, quality control flags.
   - `UserCSVRow`: validates custom user datasets (timestamp formats, station name/id, district, Punjab coordinate boundaries $[27.0, 35.5]^\circ\text{N}, [69.0, 76.5]^\circ\text{E}$, pollutant name in `['aqi', 'pm25', 'pm10', 'no2', 'so2', 'co', 'o3', 'no', 'nox']`, value $\ge 0, \le 5000.0$, optional wind speed/direction).
2. Implement Modular Ingestion Engine in `src/pipelines/`:
   - `base.py`: Abstract `BaseIngestionWorker` with `fetch()`, `parse()`, `normalize()`, and retry/backoff logic.
   - `epa_punjab.py`: Connects to live EPA Punjab endpoints with `EMC-EPA-Punjab-AQ-dashboard/1.0` User-Agent; gracefully falls back to `fallback_engine.py` when live endpoint returns 404/500/network error.
   - `metar.py`: Ingests 12 aerodromes from AviationWeather, parses knots to m/s ($0.514444$) and visibility to meters ($1609.344$).
   - `synop.py`: Parses Ogimet SYNOP telegrams for blocks 415, 416, 417.
   - `open_meteo.py`: Ingests 10m and 925hPa wind fields for 41 district centroids from Open-Meteo ECMWF IFS.
   - `fallback_engine.py`: Uses `data/baseline/` (`stations.json`, `districts.json`, `baseline_data.json`) to generate schema-conforming fallback observations.
   - `csv_adapter.py`: Ingests user CSV files, performs row-by-row validation using `UserCSVRow`, collects validation errors, sanitizes negative values, and normalizes observations.
3. Automated Tests:
   - Implement `tests/integration/test_pipelines.py` testing live/mock ingestion, fallback templating on failure, and schema conformance.
   - Implement `tests/integration/test_csv_adapter.py` testing valid CSV datasets, missing column errors, out-of-bounds coordinate rejections, extreme value warnings, and normalization.
   - Run tests via pytest (`python -m pytest tests/integration/`) and verify 100% pass with zero failures.
4. Report results in `handoff.md` and notify orchestrator.

## 2026-11-10T13:21:19Z
You are worker_m3_pipeline.
Working directory: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\worker_m3_pipeline\
Read c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\worker_m3_pipeline\DISPATCH.md, c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\ORIGINAL_REQUEST.md, c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\orchestrator\PROJECT.md, docs/DATA_SOURCES_AND_STREAMS.md, and docs/DATA_PIPELINES_ARCHITECTURE.md.

MANDATORY INTEGRITY WARNING: DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Execute Milestone M3:
1. Implement Pydantic v2 schemas in src/domain/schemas/ (RawStationMeasurement, NormalizedObservation, UserCSVRow).
2. Implement Modular Ingestion Engine in src/pipelines/ (base.py, epa_punjab.py, metar.py, synop.py, open_meteo.py, fallback_engine.py, csv_adapter.py).
3. Implement tests in tests/integration/test_pipelines.py and tests/integration/test_csv_adapter.py.
4. Run tests and verify 100% pass.
5. Report in handoff.md and notify orchestrator.
