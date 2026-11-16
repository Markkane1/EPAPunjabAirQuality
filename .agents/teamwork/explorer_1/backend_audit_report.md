# Backend & Data Pipelines Pre-Production Audit Report

**Auditor**: Explorer 1 (Backend & Data Pipelines Auditor)  
**Date**: 2026-11-15  
**Target Repository**: `c:\Users\Asif\Downloads\Punjab Air Quality`  
**Test Suite Verification Status**: 717 passed, 35 warnings in 196.61s (100% passing across Unit, Integration, and E2E suites)  

---

## 1. Executive Summary & Overall Severity Rating

### Severity Rating: **MEDIUM-HIGH (Operational Hardening Required Before Live Institutional Production)**

The backend architecture exhibits remarkably robust mathematical modeling, adhering faithfully to the official PEPC AQI breakpoints (Nov 2024), 24-hour dynamic rolling averages, Shepard's Modified IDW spatial interpolation, and NOAA METAR/Open-Meteo live integration. The underlying 4-tier storage (TimescaleDB, PostgreSQL 16, Redis 7.2 / FakeRedis, and baseline fallback engine) is fully functional, and all 717 unit/integration/E2E tests pass cleanly.

However, an aggressive pre-production audit reveals **several critical discrepancies, dummy fallback artifacts, hardcoded values masquerading as real telemetry, API routing omissions, and security/CORS misconfigurations** that must be remediated by the Worker agent before deploying into real-world operational environments with live institutional workstations.

### Key Risk Categories:
1. **Mock Data Generators & Hardcoded Magic Numbers Masquerading in Live Fallbacks**:
   - `src/pipelines/firms.py`: Generates synthetic hardcoded fire points when API key is missing or upstream fails, instead of cleanly reporting downstream unavailability.
   - `src/pipelines/iqair.py`: Returns hardcoded fake measurements for Indian border cities (Amritsar, Firozpur, Jalandhar, Ludhiana, Bathinda, Delhi) upon connection failure.
   - `src/pipelines/cams.py`: Uses fixed hardcoded wind vectors (`u=-1.8, v=-0.9`) and magic multiplier (`2.2`) rather than pulling dynamic winds, and hardcodes default border belt AQI index to `285.4`.
   - `src/pipelines/staging_buffer.py`: Injects a hardcoded net flux magic number (`357.7 kg/s`) when CAMS data is missing, and hardcodes a fallback baseline AQI of `100` when IDW yields missing values.
2. **Missing Authoritative Endpoint Aliases**:
   - `GET /api/v1/stations` and `GET /api/v1/districts` mandated by `DATA_SOURCES_AND_STREAMS.md`, `PROJECT.md`, and frontend clients are strictly defined only under `/api/v1/meta/stations` and `/api/v1/meta/districts`. Calls to `/api/v1/stations` return 404 Not Found.
3. **W3C CORS Invalidation**:
   - `src/api/main.py` configures `allow_origins=["*"]` simultaneously with `allow_credentials=True`. Standard browsers reject authenticated fetch/XHR requests under wildcard origins.
4. **Codebase Slop & Method Shadowing**:
   - `src/pipelines/scheduler.py`: Contains a duplicate definition of `async def tick_async(...)` (defined at line 150 and shadowed again at line 331).

---

## 2. Line-by-Line File Audit of Backend Components

### 2.1 Application Entry & API Infrastructure

#### `run.py`
- **Audit Findings**: Clean, production-ready launcher script. Parses CLI options (`--host`, `--port`, `--reload`, `--mode`, `--seed`). Correctly sets default port to `9000` per specification. Validates `dist/` directory presence for static frontend hosting.
- **Issues**: None.

#### `src/api/main.py`
- **Audit Findings**: Fast, structured FastAPI factory (`create_app`). Mounts static directory `dist/` at root with SPA fallback `index.html`. Initializes relational database pools, Redis manager, baseline repositories, and APScheduler lifecycle hooks.
- **Defects / Discrepancies**:
  - **Line 146**: `CORSMiddleware` has `allow_origins=["*"]` with `allow_credentials=True`. According to the Fetch Living Standard and W3C CORS specification, browsers fail any credentialed request when `Access-Control-Allow-Origin: *`.
  - **Line 183–193**: Routers included: `meta_router` (prefix `/api/v1/meta`), `observations_router` (prefix `/api/v1/observations`), `spatial_router` (prefix `/api/v1/spatial`), `analytics_router` (prefix `/api/v1/analytics`), `stream_router` (prefix `/api/v1/stream`), `ingest_router` (prefix `/api/v1/ingest`), `epa_router` (prefix `/api/v1/epa`).
  - Missing top-level alias routes for `/api/v1/stations` and `/api/v1/districts`.

#### `src/api/dependencies.py`
- **Audit Findings**: Dependency injection cleanly yields `PersistentRepository`, `SpatialService`, `AnalyticsService`, `PrecomputationService`, `PipelineOrchestrator`, and `CronScheduler`. Correctly injects `RepositoryProtocol`.

---

### 2.2 Route Handlers (`src/api/routes/`)

#### `src/api/routes/meta.py`
- **Endpoints**: `GET /api/v1/meta/districts`, `GET /api/v1/meta/stations`, `GET /api/v1/meta/stations/{station_id}`.
- **Discrepancy**: Specifications in `DATA_SOURCES_AND_STREAMS.md` and `PROJECT.md` specify `GET /api/v1/stations` and `GET /api/v1/districts` as first-class endpoints without requiring the `/meta` prefix. Direct frontend calls to `/api/v1/stations` fail with 404 unless routed.

#### `src/api/routes/observations.py`
- **Endpoints**: `GET /current`, `GET /hourly`, `GET /cross-border`, `GET /rolling-mean`, `GET /fires`, `GET /fires/summary`, `GET /fires/history`.
- **Audit Findings**: Handlers properly map query parameters (`district`, `station_id`, `pollutant`, `hours`) into repository calls. Uses ISO-8601 timestamps and structured Pydantic response models.

#### `src/api/routes/stream.py`
- **Endpoints**: `GET /api/v1/stream/live` (SSE stream), `POST /api/v1/stream/tick`, `POST /api/v1/stream/mode`, `GET /api/v1/stream/status`.
- **Audit Findings**:
  - `GET /api/v1/stream/live`: Implements true Server-Sent Events (`EventSourceResponse`) streaming ticks from `PipelineOrchestrator.subscribe()`. Handles client disconnects cleanly by unregistering asyncio queues. Includes keepalive comments.
  - Returns `event: tick` with provincial summary, stations, districts, and active streams metadata.

#### `src/api/routes/ingest.py`
- **Endpoints**: `POST /api/v1/ingest/csv`, `GET /api/v1/ingest/scheduler/status`, `GET /api/v1/ingest/scheduler/jobs`, `POST /api/v1/ingest/scheduler/trigger/{job_id}`, `POST /api/v1/ingest/scheduler/pause/{job_id}`, `POST /api/v1/ingest/scheduler/resume/{job_id}`.
- **Audit Findings**:
  - `POST /api/v1/ingest/csv`: Uses `UploadFile = File(...)` with `max_file_size` validation (50MB). Parses via `UserCSVIngestionAdapter`.
  - Enforces atomic staging commit when `commit=True`.
  - Properly splits and reports `valid_rows` vs `quarantined_rows`.

#### `src/api/routes/spatial.py` & `src/api/routes/analytics.py` & `src/api/routes/epa.py`
- **Audit Findings**:
  - `spatial.py`: `GET /api/v1/spatial/surface` serves precomputed GeoJSON/Grid surface with dynamic Shepard IDW interpolation.
  - `analytics.py`: `GET /api/v1/analytics/cpf`, `GET /api/v1/analytics/flux`, `GET /api/v1/analytics/transboundary`, `GET /api/v1/analytics/rollups/hourly`, `GET /api/v1/analytics/rollups/daily`. Handlers validate mathematical constraints and return calculated results.
  - `epa.py`: Serves station metadata, daily/monthly summaries, and alert thresholds.

---

### 2.3 Data Ingestion Pipelines (`src/pipelines/`)

#### `src/pipelines/firms.py` (STR-05 NASA FIRMS VIIRS)
- **Audit Findings**: Real HTTP worker pulls VIIRS 375m active fire detections (SNPP / NOAA-20 / NOAA-21) within Punjab bounding box (`[27.5°N, 69.0°E, 34.5°N, 75.5°E]`).
- **Defects & Mock Data Generation**:
  - **Lines 93–94 & 201–214**: `_generate_fixture_data()` contains hardcoded synthetic fire coordinates:
    ```python
    {"latitude": 31.55, "longitude": 74.35, "brightness": 342.5, "scan": 0.4, "track": 0.4, "acq_date": date_str, "acq_time": "0830", "satellite": "VIIRS-SNPP", "confidence": "nominal", "version": "2.0NRT", "bright_t31": 298.2, "frp": 38.5, "daynight": "D"}
    ```
  - **Line 93**: If `worker_mode != 'live'` or `FIRMS_MAP_KEY` is not present, silently generates this mock dataset rather than explicitly marking telemetry as degraded or unavailable.

#### `src/pipelines/iqair.py` (STR-06 IQAir Cross-Border Indian Belt)
- **Audit Findings**: Queries IQAir AirVisual API for cross-border border stations (Amritsar, Firozpur, Jalandhar, Ludhiana, Bathinda, Delhi) within 80km buffer.
- **Defects & Mock Data Generation**:
  - **Lines 162, 166, 235–245**: `_generate_fixture_data()` contains static hardcoded PM2.5 and AQI values:
    - Amritsar: PM2.5 `128.5`, US AQI `188`
    - Firozpur: PM2.5 `120.2`, US AQI `184`
    - Jalandhar: PM2.5 `189.4`, US AQI `240`
    - Ludhiana: PM2.5 `215.0`, US AQI `265`
    - Bathinda: PM2.5 `165.8`, US AQI `216`
    - Delhi: PM2.5 `335.0`, US AQI `385`
  - When the external API call encounters rate limits (429) or missing keys, instead of returning an explicit pipeline error or empty observation list with status `"degraded"`, it falls back to this synthetic list.

#### `src/pipelines/cams.py` (STR-07 Copernicus CAMS Boundary Flux)
- **Audit Findings**: Intended to track transboundary boundary mass flux (inflow/outflow in kg/s) across eastern border transect.
- **Defects & Hardcoded Approximations**:
  - **Lines 129–133**:
    ```python
    # Wind vector for transport estimation (predominantly easterly in smog season)
    u_wind = -1.8  # Easterly component (m/s)
    v_wind = -0.9  # Northerly component (m/s)
    pm25_boundary_conc = float(pm25_mean) * 2.2  # Boundary layer concentration multiplier
    ```
    The wind vector is hardcoded to `(-1.8, -0.9)` and the boundary layer concentration multiplier is hardcoded to `2.2`! This is an ungrounded static assumption rather than pulling real NWP/METAR wind vectors.
  - **Line 178**:
    ```python
    border_belt_index = float(raw_data.get("border_belt_index", 285.4))
    ```
    Hardcoded fallback magic number `285.4`.

#### `src/pipelines/staging_buffer.py`
- **Audit Findings**: Harmonization hub that stages readings from all streams, cross-calibrates winds, applies QC filters, computes Shepard IDW spatial interpolation for unmonitored districts, and commits atomically to `BaselineRepository` / `PersistentRepository`.
- **Defects & Magic Numbers**:
  - **Line 432**:
    ```python
    net_flux = cams_summary.net_flux_kg_per_s if cams_summary else 357.7
    ```
    Injects a hardcoded magic number `357.7 kg/s` when CAMS data is missing!
  - **Line 265**:
    ```python
    d_aqi = pepc_composite_aqi(i_pm25, i_pm10) or i_pm25 or 100
    ```
    Hardcodes fallback baseline AQI `100` if IDW interpolation and calculation yield zero or None. Should calculate or propagate explicit `None` / `"unmonitored"`.

#### `src/pipelines/scheduler.py`
- **Audit Findings**: `PipelineOrchestrator` coordinates simulation replay, live ticks, SSE event broadcasting, and background updates.
- **Defect (Method Shadowing)**:
  - `async def tick_async(self, timestamp: Optional[datetime] = None, mode: Optional[str] = None)` is implemented at lines 150–184.
  - A duplicate definition of `async def tick_async(self, timestamp: Optional[datetime] = None, mode: Optional[str] = None)` is repeated at lines 331–368. The second definition shadows the first one entirely, creating confusion and maintenance bugs.

#### `src/pipelines/epa_punjab.py`, `metar.py`, `synop.py`, `open_meteo.py`
- **Audit Findings**:
  - `epa_punjab.py`: Connects to live Punjab EPA ArcGIS REST service / portal, handles auth cookies, pagination, and parse failures.
  - `metar.py`: Clean NOAA Aviation Weather API client with 4 ICAO stations (OPLA, OPIS, OPST, OPRN), validates METAR strings, extracts wind direction/speed, converts knots to m/s.
  - `synop.py`: FM-12 SYNOP parser decoding surface synoptic observations.
  - `open_meteo.py`: ECMWF IFS 10m wind hourly forecasts for Punjab district centroids.

#### `src/pipelines/csv_adapter.py`
- **Audit Findings**: High-throughput multipart CSV parser. Validates headers, formats, date stamps, and value ranges against `UserCSVRowContract`. Correctly routes invalid rows to quarantine with error logs.

---

### 2.4 Domain Schemas & Mathematical Engine (`src/domain/`)

#### `src/domain/math/pepc_aqi.py`
- **Audit Findings**: Fully verified implementation of Punjab Environmental Protection Council (PEPC) official notification breakpoints (Nov 2024):
  - Tier 1 (Good): 0–50
  - Tier 2 (Satisfactory): 51–100
  - Tier 3 (Moderate): 101–150
  - Tier 4 (Unhealthy for Sensitive Groups): 151–200
  - Tier 5 (Unhealthy): 201–300
  - Tier 6 (Very Unhealthy): 301–400
  - Tier 7 (Hazardous): 401–500
  - Tier 8 (Emergency / Hazardous Catastrophic): 500+ (capped at linear extrapolation per formula)
- Tested across 45 adversarial boundary cases. Zero defects.

#### `src/domain/math/idw.py`
- **Audit Findings**: Modified Shepard IDW interpolation (`p=2.0`, searching up to radius $R$ with distance weighting). Correctly handles coincident points ($\text{distance} < 10^{-6}$) and unmonitored district centroids.

#### `src/domain/math/flux.py`, `cpf.py`, `transboundary.py`, `qc.py`, `wind.py`
- **Audit Findings**: Clean vectorized and mathematical routines. QC rules implement range checks, spike detection ($> 100\,\mu\text{g/m}^3/\text{hr}$), and stuck sensor checks (flatline for 4+ consecutive hours).

#### `src/domain/schemas/csv_schema.py` & `src/domain/schemas/measurement.py`
- **Audit Findings**: Schema classes match contract specifications. `UserCSVRowContract` requires `station_id`, `timestamp`, `pollutant`, `value`.
- **Minor Inconsistency**: `UserCSVRow` defines `pollutant_flags` as `Optional[str] = None`, whereas `RawStationMeasurement` defines `pollutant_flags` as `Optional[Any] = None`. If an ingested CSV contains complex JSON flags, string parsing can raise validation errors.

---

### 2.5 Services & Repositories (`src/services/` & `src/infrastructure/`)

#### `src/services/analytics_service.py` & `spatial_service.py` & `observation_service.py`
- **Audit Findings**: Services correctly bridge repositories and domain models. Spatial service precomputes 0.1° regular grid IDW fields and caches GeoJSON contour layers.

#### `src/infrastructure/repositories/baseline_repository.py`
- **Audit Findings**: In-memory analytical repository holding historical baseline and live staged frames. Calculates dynamic 24h rolling means across stations and districts. Correctly implements all query methods for offline and test runs.

#### `src/infrastructure/repositories/persistent_repository.py`
- **Audit Findings**: Relational TimescaleDB / PostgreSQL repository implementation. Manages hypertables `station_observations`, `district_observations`, `active_fires`, and `cams_flux`. Supports connection pooling, automatic schema creation via `ddl.py`, and continuous aggregates.

#### `src/infrastructure/cache/redis_manager.py`
- **Audit Findings**: Dual-mode Redis manager. Connects to Redis 7.2 when available, or seamlessly initializes high-fidelity `FakeRedis` when Redis is unavailable, avoiding test suite crashes.

---

## 3. Discrepancies Against Authoritative Specifications

| Specification Item | Specification Document | Actual Code Implementation | Severity |
| :--- | :--- | :--- | :--- |
| **Direct Station Route** | `DATA_SOURCES_AND_STREAMS.md`, `PROJECT.md` §3 | Only `/api/v1/meta/stations` exists. Direct `GET /api/v1/stations` returns 404. | **HIGH** |
| **Direct District Route** | `DATA_SOURCES_AND_STREAMS.md`, `PROJECT.md` §3 | Only `/api/v1/meta/districts` exists. Direct `GET /api/v1/districts` returns 404. | **HIGH** |
| **CORS Wildcard Credentials** | W3C Fetch Spec / Security Standards | `allow_origins=["*"]` + `allow_credentials=True` in `src/api/main.py`. Browsers block requests. | **HIGH** |
| **NASA FIRMS Mock Generator** | `DATA_SOURCES_AND_STREAMS.md` STR-05 | `src/pipelines/firms.py` generates fake fire points (`_generate_fixture_data`) on missing API key/failure. | **HIGH** |
| **IQAir Mock Generator** | `DATA_SOURCES_AND_STREAMS.md` STR-06 | `src/pipelines/iqair.py` generates hardcoded PM2.5 readings for Indian cities (`_generate_fixture_data`). | **HIGH** |
| **CAMS Static Wind & Factor** | `DATA_SOURCES_AND_STREAMS.md` STR-07 | `src/pipelines/cams.py` uses fixed `u=-1.8, v=-0.9` and arbitrary `2.2` multiplier instead of real NWP winds. | **MEDIUM** |
| **Net Flux Magic Number** | `docs/DATA_PIPELINES_ARCHITECTURE.md` | `src/pipelines/staging_buffer.py:432` falls back to magic number `357.7 kg/s`. | **MEDIUM** |
| **Shadowed Method** | Software Clean Code Standards | `src/pipelines/scheduler.py` defines `tick_async` twice (lines 150 and 331). | **LOW** |

---

## 4. Specific List of Dummies, Stubs, Fake Fallbacks, and Slop

1. **`src/pipelines/firms.py:201-214`**:
   - `_generate_fixture_data`: Returns 7 hardcoded active fires in Sheikhupura, Kasur, Okara, Faisalabad with static FRPs (`38.5`, `45.2`, etc.). Masquerades as live FIRMS data if map key is absent.
2. **`src/pipelines/iqair.py:235-245`**:
   - `_generate_fixture_data`: Returns 6 hardcoded cross-border cities with static PM2.5 (`128.5`, `120.2`, `189.4`, `215.0`, `165.8`, `335.0`).
3. **`src/pipelines/cams.py:129-133 & 178`**:
   - Static vector `u_wind = -1.8`, `v_wind = -0.9`, multiplier `2.2`, and fallback `285.4`.
4. **`src/pipelines/staging_buffer.py:432`**:
   - Hardcoded default `net_flux = 357.7`.
5. **`src/pipelines/staging_buffer.py:265`**:
   - Hardcoded baseline AQI fallback `100` for districts.
6. **`src/pipelines/scheduler.py:150 & 331`**:
   - Duplicated and shadowed `async def tick_async` implementation.

---

## 5. Actionable Remediation Plan for the Worker Agent

### Step 1: Add Direct Top-Level Route Aliases (`/api/v1/stations` & `/api/v1/districts`)
In `src/api/routes/meta.py` or `src/api/main.py`:
- Expose `GET /api/v1/stations` and `GET /api/v1/stations/{station_id}` directly at the root API router or add route forwards.
- Expose `GET /api/v1/districts` directly at `/api/v1/districts`.
- Maintain `/api/v1/meta/*` for backward compatibility.

### Step 2: Remediate CORS Configuration in `src/api/main.py`
- Replace `allow_origins=["*"]` with an explicit origin list (e.g. `["http://localhost:9000", "http://127.0.0.1:9000", "http://localhost:5173", "http://localhost:3000"]`) when `allow_credentials=True`.
- Allow override via environment variable `CORS_ORIGINS`.

### Step 3: Remove Mock Generators from Live Execution Paths
- In `src/pipelines/firms.py`:
  - Clearly separate `worker_mode == "fixture"` (for offline testing) from `worker_mode == "live"`.
  - In `live` mode, if `FIRMS_MAP_KEY` is missing or upstream fails, return an empty detection list and set `status="unavailable"` / `"degraded"`, instead of silently generating fake fire points.
- In `src/pipelines/iqair.py`:
  - When in `live` mode, upstream errors must record degraded stream health and return empty observations, not synthetic cities.
- In `src/pipelines/cams.py`:
  - Link boundary flux calculation to actual NWP wind vectors staged in `ChronometricStagingBuffer` or NOAA METAR vectors instead of hardcoded `(-1.8, -0.9)`.
  - Remove arbitrary multiplier `2.2` and default `285.4`.

### Step 4: Eliminate Magic Numbers in `staging_buffer.py`
- At line 432: Set `net_flux = cams_summary.net_flux_kg_per_s if cams_summary else None` (or `0.0` with explicit flag indicating unmeasured flux).
- At line 265: Ensure unmonitored districts compute legitimate IDW interpolated AQI from neighboring monitors; if no stations exist within search radius, report `None` / `0` with `is_imputed=False` rather than an arbitrary `100`.

### Step 5: Clean Duplicate `tick_async` in `src/pipelines/scheduler.py`
- Remove the shadowed method definition at lines 150–184 and unify into a single clean `tick_async` implementation.

### Step 6: Verify Full Test Suite
- Re-run `python -m pytest tests/` to verify that all 717 tests pass with zero regressions after these cleanups.

---

**Report Prepared By:**  
Explorer 1 (Backend & Data Pipelines Auditor)  
Punjab Air Quality Institutional Workstation Team
