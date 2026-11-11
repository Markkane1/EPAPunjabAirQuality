## 2026-11-10T13:53:59Z

You are worker_m3_pipeline_active (Archetype: teamwork_worker). Your working directory is c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\worker_m3_pipeline_active\

MANDATORY FIRST STEP: Read the following authoritative documents before writing code:
1. c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\ORIGINAL_REQUEST.md
2. c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\orchestrator\PROJECT.md
3. c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\spec_miner_architecture\handoff.md
4. docs/DATA_SOURCES_AND_STREAMS.md
5. docs/DATA_PIPELINES_ARCHITECTURE.md
6. docs/SYSTEM_ARCHITECTURE.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

OBJECTIVE:
Implement Milestone M3: Data Pipelines & CSV Ingestion Engine.
Build the ingestion architecture, external feed workers with fallback, and the user CSV ingestion/validation adapter adhering to Clean Architecture.

EXCLUSIVE FILE OWNERSHIP:
- src/domain/schemas/__init__.py
- src/domain/schemas/measurement.py (Pydantic v2 RawStationMeasurement with upper bound le=5000.0, extreme exceedance tag)
- src/domain/schemas/csv_schema.py (Pydantic v2 UserCSVRow, lat [27.0, 35.0], lon [69.0, 76.0], 9 pollutants, wind bounds)
- src/pipelines/__init__.py
- src/pipelines/base.py (BaseIngestionWorker abstract class)
- src/pipelines/epa_punjab.py (EPA Punjab live feed client with custom User-Agent, retry, and fallback)
- src/pipelines/metar.py (AviationWeather METAR client for 12 aerodromes, knots-to-m/s (0.514444), statute-to-meters)
- src/pipelines/synop.py (WMO SYNOP decoder for Punjab blocks 415, 416, 417)
- src/pipelines/open_meteo.py (ECMWF IFS Open-Meteo client for 41 district centroids)
- src/pipelines/fallback_engine.py (FallbackTemplateEngine seeded from data/baseline/ files: baseline_data.json, stations.json, districts.json, airports.json)
- src/pipelines/csv_adapter.py (User CSV ingestion adapter, validation against schema, row-level error reporting/quarantine, normalized domain observation output)
- tests/integration/test_pipelines.py
- tests/integration/test_csv_adapter.py

TESTING REQUIREMENTS:
1. Integration tests in test_pipelines.py must test live worker initialization, parsing, error handling, and graceful fallback to FallbackTemplateEngine with is_estimated = True.
2. Integration tests in test_csv_adapter.py must test parsing valid CSVs (e.g., from tests/fixtures/valid_station_observations.csv), detecting malformed CSVs (missing columns, out-of-bounds coords, negative values), quarantine reporting, and row normalization.
3. Run: python -m pytest tests/integration/test_pipelines.py tests/integration/test_csv_adapter.py -v
4. Run full test suite: python -m pytest tests/ -v (must achieve 100% pass with zero regressions)
5. Keep progress.md updated in your working directory.
6. When complete, write handoff.md following the Handoff Protocol and message back.
