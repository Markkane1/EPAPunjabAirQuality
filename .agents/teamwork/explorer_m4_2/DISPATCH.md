## 2026-11-11T04:30:34Z
You are explorer_m4_2 (Archetype: teamwork_explorer).
Working directory: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\explorer_m4_2\
Project root: c:\Users\Asif\Downloads\Punjab Air Quality
Original request path: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\ORIGINAL_REQUEST.md
Scope document: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\orchestrator\PROJECT.md

Your role is to explore, design, and formulate the implementation strategy for Milestone M4:
Target Area: Application Services Layer (`src/services/`).

Reference specifications to study:
- docs/SYSTEM_ARCHITECTURE.md (§2, §3, §4, §5)
- docs/TRANSFORMATION_LOGIC_SPEC.md
- src/domain/entities/models.py
- src/domain/math/ (geodesy, idw, cpf, flux, transboundary, pepc_aqi, qc, projection)
- src/pipelines/csv_adapter.py

Tasks:
1. Design the business application services:
   - `observation_service.py`: Service to query current and hourly time-series observations, calculate province-wide summary statistics (mean AQI, PEQS exceedance counts, peak district, peak station), and filter by pollutant and district.
   - `spatial_service.py`: Service to compute 2D spatial surface interpolation matrices using `discrete_geodesic_idw` from `src/domain/math/idw.py` for requested timestamp, pollutant, and resolution.
   - `analytics_service.py`: Service to compute 16-sector CPF wind roses (`src/domain/math/cpf.py`), inter-district advection flux matrices and ranking (`src/domain/math/flux.py`), and transboundary mass balance index (`src/domain/math/transboundary.py`).
   - `ingestion_service.py`: Service to orchestrate user CSV file ingestion using `UserCSVIngestionAdapter` and update repository state dynamically.
2. Define class structures, method signatures, mathematical transformation invocations, input validation, and caching/optimization considerations.
3. Detail how domain entities and math modules connect cleanly to services without leaks.

DO NOT write source code in src/ — you are an explorer. Provide your findings, architecture diagrams, method signatures, and recommendations in your handoff report:
c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\explorer_m4_2\handoff.md
Update progress.md as you work and send a completion message to orchestrator.
