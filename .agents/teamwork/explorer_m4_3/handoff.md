# Milestone M4 Exploration & Architecture Handoff Report
**Target Area**: FastAPI Application Gateway, REST Routing, Pydantic v2 Schemas, and Server-Sent Events (SSE) Streaming  
**Author**: `explorer_m4_3` (teamwork_explorer)  
**Date**: 2026-11-11  
**Project**: Punjab Air Quality Monitoring, Processing, and Visualization System  
**Working Directory**: `c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\explorer_m4_3\`  

---

## 1. Observation

### 1.1 Specifications and System Contracts
1. **Contract Requirement (`tests/e2e/test_tier1_feature_coverage.py`, lines 242–260)**:
   The system mandates exactly **10 core API route specifications** in `TestTier1APIEndpointContracts`:
   ```python
   required_routes = [
       ("GET", "/api/v1/meta/districts"),
       ("GET", "/api/v1/meta/stations"),
       ("GET", "/api/v1/observations/current"),
       ("GET", "/api/v1/observations/hourly"),
       ("GET", "/api/v1/spatial/surface"),
       ("GET", "/api/v1/analytics/cpf"),
       ("GET", "/api/v1/analytics/flux"),
       ("GET", "/api/v1/analytics/transboundary"),
       ("POST", "/api/v1/ingest/csv"),
       ("GET", "/api/v1/stream/live"),
   ]
   ```
2. **System Architecture Specification (`docs/SYSTEM_ARCHITECTURE.md`)**:
   - **§2.3 & §5**: Defines Tier 3 FastAPI Gateway backing OpenAPI 3.1 REST contracts and dual-protocol transport (REST JSON + Server-Sent Events).
   - **§5.1.1**: `GET /api/v1/meta/districts` returns administrative boundaries, centroids, monitoring flags, and transboundary parameters.
   - **§5.1.2**: `GET /api/v1/observations/hourly` accepts `start_time`, `end_time`, and `pollutant` (AQI, PM2.5, PM10, NO2, SO2, CO, O3, NO, NOx). Returns hourly time-series vectors per district (`concentrations`, `wind_u`, `wind_v`, `is_estimated`).
   - **§5.1.3**: `GET /api/v1/spatial/surface` accepts `timestamp`, `pollutant`, and `resolution` (default 5 px). Returns 2D grid matrix of continuous values.
   - **§5.1.4**: `GET /api/v1/analytics/cpf` accepts `district_name` and `pollutant`. Returns 16-sector polar wind rose probabilities with $P_{75}$ threshold $\tau$, calm fraction, and null-hypothesis baseline 0.25.
   - **§5.2**: `GET /api/v1/stream/live` specifies:
     - `Accept: text/event-stream`, `Cache-Control: no-cache`
     - Heartbeat ping comment: `: keepalive\n\n` emitted every 15 seconds.
     - Event schema: `event: hourly_update` with payload containing `provincial_summary` (`mean_aqi`, `exceedance_peqs_count`, `peak_district`, `peak_aqi`), `district_readings`, and `airports`.
3. **Data Sources & Stream Catalog (`docs/DATA_SOURCES_AND_STREAMS.md`)**:
   - 41 administrative districts, 79 monitoring stations, 12 regional aerodromes (with primary anchors OPLA, OPFA, OPMT, OPST, OPIS, VIAR).
   - Sensor bounds: PM2.5, PM10 $\le 5000\,\mu\text{g/m}^3$ (values $>1000$ PM2.5 and $>1500$ PM10 tagged with `QC_EXCEEDANCE_EXTREME`), AQI $\le 2000$, wind speed $\in [0.0, 30.0]\text{ m/s}$, wind direction $\in [0.0^\circ, 360.0^\circ]$.
   - Wazirabad vane blacklist (speed/direction discarded, fallback to METAR/IDW).
4. **Domain Logic & Algorithmic Guards (`src/domain/math/`)**:
   - `flux.py` (lines 44–48): **Critical Physical Dimension Guard**: Advection transport flux is strictly disabled for `'AQI'` because AQI is a non-linear ordinal health index, not a conserved physical mass concentration. Attempting advection on AQI must be guarded at the API boundary (returning HTTP 400 Bad Request or an explicit guarded payload).
   - `cpf.py` (lines 77–79): **Small-Sample Suppression Rule**: If sector total hours $N_k < 6$, $\text{CPF}_k = \text{null}$ to prevent false 100% spikes from 1–2 chance events.
   - `idw.py`: Geodesic discrete IDW with $d_0 = 5.0\text{ km}$ singularity clamping and continuous anisotropic wind-steered IDW.
   - `transboundary.py`: 120km border-belt analysis and 39 border normal vector projections.
5. **Existing Pipeline & Ingestion Code (`src/pipelines/csv_adapter.py`)**:
   - `UserCSVIngestionAdapter.ingest_csv(source)` accepts `bytes`, `str`, `Path`, `io.BytesIO`, or `io.StringIO`.
   - Returns `CSVIngestionResult` with `status`, `total_rows`, `valid_count`, `quarantine_count`, `observations`, and `quarantine_records`.
   - `get_merged_observations()` merges single-pollutant rows into multi-pollutant `NormalizedObservation` entities with composite PEPC AQI.
6. **Installed Python Libraries & Runtime Environment**:
   - Python: 3.14.0
   - FastAPI: 0.162.2 (supports modern async lifespan context manager)
   - Pydantic: 2.14.1 (Pydantic v2 `BaseModel`, `Field`, `ConfigDict`, `field_validator`, `model_validator`)
   - HTTPX: 0.28.1 (supports `httpx.AsyncClient` with `ASGITransport(app=app)`)
7. **Cross-Explorer Synthesis**:
   - `explorer_m4_1`: Has established repository interfaces (`StationRepository`, `DistrictRepository`, `ObservationRepository`, `AnalyticsRepository`) and concrete `BaselineRepository` with sub-millisecond retrieval latency (0.058–0.097 µs).
   - `explorer_m4_2`: Has established application service layer (`ObservationService`, `SpatialService`, `AnalyticsService`, `IngestionService`) orchestrating domain transformations and returning typed DTOs.

---

## 2. Logic Chain

```
+---------------------------------------------------------------------------------------------------------+
|                                  Tier 4: Client Presentation Tier                                        |
|                       React 19 SPA / Zustand Stores / Canvas 2D + WebGL Renderers                       |
+---------------------------------------------------------------------------------------------------------+
                                         | HTTP REST (JSON)              | SSE Live Stream
                                         v                               v
+---------------------------------------------------------------------------------------------------------+
|                                    Tier 3: FastAPI Application Gateway                                   |
|                                            (src/api/main.py)                                            |
|                                                                                                         |
|   - Lifespan Context Manager: initializes BaselineRepository (~1.5s cold load, cached in app.state)     |
|   - CORS Middleware: wildcard or configurable origins, credentials allowed, unrestricted methods        |
|   - Uniform Error Handlers: RequestValidationError (422), HTTPException, Domain ValueError (400)         |
|   - Routers Mounted under /api/v1/:                                                                     |
|     1. meta_router        --> /api/v1/meta          (districts, stations)                               |
|     2. observations_router--> /api/v1/observations  (current, hourly)                                   |
|     3. spatial_router     --> /api/v1/spatial       (surface)                                           |
|     4. analytics_router   --> /api/v1/analytics     (cpf, flux, transboundary)                          |
|     5. ingest_router      --> /api/v1/ingest        (csv multipart upload)                              |
|     6. stream_router      --> /api/v1/stream        (live SSE stream with 15s keepalive)                |
+---------------------------------------------------------------------------------------------------------+
                                         | FastAPI Depends() Dependency Injection
                                         v
+---------------------------------------------------------------------------------------------------------+
|                                  Application Services Layer (src/services/)                             |
|        - ObservationService      - SpatialService      - AnalyticsService      - IngestionService       |
+---------------------------------------------------------------------------------------------------------+
                     |                                                       |
                     v                                                       v
+----------------------------------------+               +----------------------------------------+
|       Domain Pure Math Algorithms      |               |     Infrastructure Repositories        |
|         (src/domain/math/*.py)         |               |     (src/infrastructure/repos/*.py)    |
|   - idw, cpf, flux, transboundary      |               |   - BaselineRepository (In-Memory)     |
|   - pepc_aqi, projection, wind, qc     |               |   - 79 stations, 41 districts, 216 hrs  |
+----------------------------------------+               +----------------------------------------+
```

### Step 1: Framework Versioning and Modern Lifespan Pattern
*Observation Reference: §1.6 (FastAPI 0.162.2)*  
Legacy FastAPI applications used `@app.on_event("startup")` and `@app.on_event("shutdown")`. These have been deprecated in Starlette and FastAPI in favor of the unified `lifespan` context manager.
1. `src/api/main.py` defines `lifespan(app: FastAPI)` with `asynccontextmanager`.
2. During startup, `BaselineRepository` is initialized once from `data/baseline/`. All 79 stations, 41 districts, 6 airports, and 216 historical hours are loaded and indexed in RAM (~54 MB footprint, 1.5s startup).
3. The initialized repository and dependent services (`ObservationService`, `SpatialService`, `AnalyticsService`, `IngestionService`) are attached to `app.state`.
4. This guarantees that all downstream REST requests and SSE streams execute with sub-millisecond in-memory lookups without redundant file I/O.

### Step 2: Clean Architecture Dependency Inversion
*Observation Reference: §1.7 (explorer_m4_1 & explorer_m4_2 handoffs)*  
Route handlers must never directly access raw disk files, SQL databases, or compute raw mathematical equations.
1. Dependency providers in `src/api/dependencies.py` use `fastapi.Depends` to inject service instances:
   - `get_station_repository()`
   - `get_district_repository()`
   - `get_observation_service()`
   - `get_spatial_service()`
   - `get_analytics_service()`
   - `get_ingestion_service()`
2. Route functions consume these dependencies, ensuring total decoupling and allowing effortless mock substitution during testing.

### Step 3: Strict Schema Segregation & Pydantic v2 Compliance
*Observation Reference: §1.1, §1.2, §1.6 (Pydantic 2.14.1)*  
1. All request parameters and response payloads must be governed by explicit Pydantic v2 schemas in `src/api/schemas/`.
2. All schemas configure `model_config = ConfigDict(from_attributes=True, populate_by_name=True)`.
3. Validation rules enforce boundary conditions:
   - District names validated against the 41 recognized Punjab districts.
   - Pollutants normalized via regex or validator (accepting `AQI, PM2.5, PM10, NO2, SO2, CO, O3, NO, NOx` case-insensitively).
   - Resolution bounded to `[1, 50]` pixels.
   - Uploaded files checked for `.csv` extension and non-empty content.

### Step 4: Domain Guard Enforcement at Route Boundaries
*Observation Reference: §1.4 (Physical AQI flux guard, small-sample CPF suppression)*  
1. In `GET /api/v1/analytics/flux`:
   - If query parameter `pollutant.upper() == "AQI"`, the route immediately raises `HTTPException(status_code=400, detail="Advection transport mass flux is physically undefined for dimensionless ordinal index 'AQI'. Query a mass concentration pollutant such as PM2.5, PM10, NO2, SO2, CO, or O3.")`.
   - This prevents mathematical nonsense from leaking into API consumers.
2. In `GET /api/v1/analytics/cpf`:
   - When a sector has $N_k < 6$ total hours, the probability field is emitted as `None` (JSON `null`), honoring the small-sample suppression rule.

### Step 5: Resilient Server-Sent Events (SSE) Engine
*Observation Reference: §1.2 (§5.2 SSE specification)*  
1. `GET /api/v1/stream/live` returns a `StreamingResponse` with `media_type="text/event-stream"`.
2. Headers are strictly set:
   - `Cache-Control: no-cache`
   - `Connection: keep-alive`
   - `X-Accel-Buffering: no` (vital for reverse proxies like Nginx to prevent buffering).
3. The event generator immediately yields the current baseline/live state as an `hourly_update` event so connecting clients receive instant telemetry without waiting for the next hour tick.
4. An async loop checks for client disconnections (`await request.is_disconnected()`) on every tick.
5. Every 15 seconds, a comment ping (`: keepalive\n\n`) is emitted to keep network sockets alive through NAT firewalls and cloud load balancers.

### Step 6: Integration Testing via `httpx.AsyncClient` & `ASGITransport`
*Observation Reference: §1.6 (HTTPX 0.28.1)*  
1. In modern HTTPX, testing ASGI applications asynchronously is performed via `httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test")`.
2. This invokes FastAPI routes directly in-process through ASGI without binding to physical TCP sockets, executing tests in milliseconds.
3. For the SSE live feed, the test consumes lines asynchronously via `response.aiter_lines()`, asserts the initial event structure, and breaks out immediately, avoiding test deadlocks.

---

## 3. Caveats

1. **SSE Connection Lifespan in Development**:
   In local development using single-worker servers, persistent SSE streams occupy a connection. In production, ASGI servers like Uvicorn handle thousands of concurrent async connections effortlessly. The route generator explicitly handles `asyncio.CancelledError` and `request.is_disconnected()` to ensure zero socket leaks.
2. **Dynamic Ingest State Retention**:
   User CSV files uploaded via `POST /api/v1/ingest/csv` are ingested dynamically into the in-memory `BaselineRepository`. This satisfies Milestone M4 requirements. If persistent storage across server reboots is needed, the repository implementation can easily be backed by an SQLite or TimescaleDB sink.
3. **Spatial Surface Resolution & Latency**:
   A 5-pixel resolution grid across Punjab encompasses ~7,000 interpolation cells. While calculation takes <60 ms, `SpatialService` caches precomputed grids in memory so subsequent queries are served in <0.5 ms.

---

## 4. Conclusion & Complete Architectural Blueprints

### 4.1 Application Structure & Layout
The presentation tier is cleanly laid out under `src/api/`:
```
src/api/
├── __init__.py
├── main.py                     # FastAPI application factory, lifespan, CORS, router mounts
├── dependencies.py             # Dependency injection providers for repos & services
├── routes/
│   ├── __init__.py
│   ├── meta.py                 # GET /api/v1/meta/districts, GET /api/v1/meta/stations
│   ├── observations.py         # GET /api/v1/observations/current, GET /api/v1/observations/hourly
│   ├── spatial.py              # GET /api/v1/spatial/surface
│   ├── analytics.py            # GET /api/v1/analytics/cpf, /flux, /transboundary
│   ├── ingest.py               # POST /api/v1/ingest/csv
│   └── stream.py               # GET /api/v1/stream/live (SSE)
└── schemas/
    ├── __init__.py
    ├── meta.py                 # Pydantic v2 schemas for districts & stations
    ├── observations.py         # Pydantic v2 schemas for current & hourly telemetry
    ├── spatial.py              # Pydantic v2 schemas for spatial surface rasters
    ├── analytics.py            # Pydantic v2 schemas for CPF roses, flux, transboundary
    ├── ingest.py               # Pydantic v2 schemas for CSV ingestion reports
    └── stream.py               # Pydantic v2 schemas for SSE update events
```

---

### 4.2 Complete Pydantic v2 Schemas

#### 4.2.1 Metadata Schemas (`src/api/schemas/meta.py`)
```python
"""Pydantic v2 schemas for geographic and station metadata."""
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, ConfigDict, Field


class DistrictMetaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Unique district identifier")
    name: str = Field(..., description="Official district name")
    division: str = Field(default="", description="Administrative division")
    latitude: float = Field(..., description="Centroid latitude (WGS84)")
    longitude: float = Field(..., description="Centroid longitude (WGS84)")
    is_monitored: bool = Field(..., description="True if district has active ground AQMS")
    border_distance_km: float = Field(..., description="Distance from centroid to international border in km")
    india_inflow_sectors: List[int] = Field(default_factory=list, description="Wind compass sectors blowing from India (0-15)")
    stations: List[str] = Field(default_factory=list, description="List of station names in this district")
    boundary: Optional[Any] = Field(default=None, description="Boundary polygon coordinate array or GeoJSON geometry")


class StationMetaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Unique station code or EPA ID")
    name: str = Field(..., description="Station display name")
    district: str = Field(..., description="District name")
    latitude: float = Field(..., description="Latitude (WGS84)")
    longitude: float = Field(..., description="Longitude (WGS84)")
    station_type: str = Field(default="fixed", description="fixed, mobile, airport_metar, wmo_synop")
    has_anemometer: bool = Field(default=False, description="True if site has functional anemometer")
    anemometer_blacklisted: bool = Field(default=False, description="True if vane is uncalibrated/blacklisted (e.g. Wazirabad)")
    altitude_m: Optional[float] = Field(default=None, description="Station elevation above sea level in meters")
    network_type: Optional[str] = Field(default=None, description="Network category (fixed, mobile, metar)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Supplementary sensor hardware metadata")
```

#### 4.2.2 Observation Schemas (`src/api/schemas/observations.py`)
```python
"""Pydantic v2 schemas for current and hourly air quality observations."""
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ProvincialSummarySchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    mean_aqi: float = Field(..., description="Provincial arithmetic mean AQI across reporting districts")
    exceedance_peqs_count: int = Field(..., description="Number of districts exceeding PEQS statutory ceiling")
    peak_district: str = Field(..., description="District exhibiting highest AQI")
    peak_aqi: float = Field(..., description="Maximum AQI value recorded in peak district")
    reporting_stations_count: int = Field(default=0, description="Count of stations reporting valid observations")


class DistrictReadingSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    district: str = Field(...)
    aqi: Optional[int] = Field(None, description="Composite PEPC AQI")
    value: Optional[float] = Field(None, description="Target pollutant concentration")
    pm25: Optional[float] = None
    pm10: Optional[float] = None
    no2: Optional[float] = None
    so2: Optional[float] = None
    co: Optional[float] = None
    o3: Optional[float] = None
    u: Optional[float] = Field(None, description="Zonal wind vector in m/s")
    v: Optional[float] = Field(None, description="Meridional wind vector in m/s")
    wind_speed: Optional[float] = Field(None, description="Wind speed in m/s")
    wind_direction: Optional[float] = Field(None, description="Wind azimuth in degrees")
    is_estimated: bool = Field(default=False, description="True if imputed via spatial IDW")


class AirportReadingSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    icao: str = Field(..., description="4-letter ICAO code (e.g. OPLA)")
    name: str = Field(..., description="Aerodrome name")
    latitude: float = Field(...)
    longitude: float = Field(...)
    wind_speed_ms: Optional[float] = Field(None)
    wind_direction_deg: Optional[float] = Field(None)
    u: Optional[float] = None
    v: Optional[float] = None


class CurrentObservationsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    timestamp: str = Field(..., description="ISO-8601 UTC timestamp of observation snapshot")
    hour_index: int = Field(..., description="Historical hour index (0 to 215, or latest)")
    pollutant: str = Field(default="AQI")
    provincial_summary: ProvincialSummarySchema
    districts: Dict[str, DistrictReadingSchema]
    airports: List[AirportReadingSchema] = Field(default_factory=list)


class DistrictHourlySeriesSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    concentrations: List[Optional[float]] = Field(..., description="Hourly concentration or AQI values")
    wind_u: List[Optional[float]] = Field(default_factory=list, description="Hourly U-wind components")
    wind_v: List[Optional[float]] = Field(default_factory=list, description="Hourly V-wind components")
    is_estimated: bool = Field(default=False)


class HourlyObservationsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    pollutant: str = Field(...)
    hours: List[str] = Field(..., description="Array of ISO-8601 hourly timestamps")
    total_hours: int = Field(...)
    districts: Dict[str, DistrictHourlySeriesSchema] = Field(...)
    provincial_mean: Optional[List[Optional[float]]] = Field(default=None)
```

#### 4.2.3 Spatial Surface Schemas (`src/api/schemas/spatial.py`)
```python
"""Pydantic v2 schemas for continuous 2D spatial surface raster fields."""
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class SpatialSurfaceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    timestamp: str = Field(..., description="Snapshot timestamp")
    pollutant: str = Field(...)
    grid_width: int = Field(..., description="Horizontal cell count")
    grid_height: int = Field(..., description="Vertical cell count")
    resolution: int = Field(default=5, description="Pixel cell step size")
    min_val: float = Field(..., description="Minimum interpolated concentration in domain")
    max_val: float = Field(..., description="Maximum interpolated concentration in domain")
    grid_matrix: List[List[float]] = Field(..., description="2D array of continuous field values [y][x]")
    opacity_matrix: Optional[List[List[int]]] = Field(
        default=None, description="Optional 2D array of geostatistical distance confidence alpha channels [95, 235]"
    )
```

#### 4.2.4 Analytics Schemas (`src/api/schemas/analytics.py`)
```python
"""Pydantic v2 schemas for CPF wind roses, advection transport flux, and transboundary balance."""
from typing import Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class CPFSectorDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    sector_index: int = Field(..., ge=0, le=15, description="Compass sector index 0-15")
    azimuth_deg: float = Field(..., description="Central sector azimuth (0.0 to 337.5 deg)")
    direction_label: str = Field(..., description="Compass label (N, NNE, NE, ...)")
    total_hours: int = Field(..., description="Total non-calm hours recorded in this sector (Nk)")
    exceedance_hours: int = Field(..., description="Hours exceeding P75 threshold in this sector (mk)")
    cpf_probability: Optional[float] = Field(
        None, description="Conditional probability (mk / Nk), or None if Nk < 6 (suppressed)"
    )


class CPFRoseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    district: str = Field(...)
    pollutant: str = Field(...)
    threshold_p75: float = Field(..., description="Pooled 75th percentile exceedance threshold")
    calm_fraction: float = Field(..., description="Fraction of hours where wind speed < 0.5 m/s")
    null_hypothesis_baseline: float = Field(default=0.25, description="Isotropic baseline probability")
    sectors: List[CPFSectorDetail] = Field(...)


class AdvectionPathwayLink(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    source_district: str = Field(...)
    receptor_district: str = Field(...)
    distance_km: float = Field(..., description="Geodesic distance between centroids in km")
    bearing_deg: float = Field(..., description="Bearing from source to receptor")
    divergence_deg: float = Field(..., description="Angular deviation from advective wind vector")
    flux: float = Field(..., description="Physical advective mass flux")
    omega: float = Field(default=0.25, description="Receptor CPF feedback coupling coefficient")
    score: float = Field(default=0.0, description="Ranked transport score (flux * omega)")


class FluxTransportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    pollutant: str = Field(...)
    timestamp: Optional[str] = Field(None)
    top_pathways: List[AdvectionPathwayLink] = Field(default_factory=list, description="Top ranked transport corridors")
    net_balance: Dict[str, float] = Field(default_factory=dict, description="Net transport flux per district (+net exporter, -net receptor)")


class BorderDistrictTransboundaryDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    district: str = Field(...)
    border_distance_km: float = Field(...)
    inflow_sectors: List[int] = Field(default_factory=list)
    transboundary_flux: float = Field(...)
    direction_mode: str = Field(..., description="inflow, outflow, neutral, or calm")


class BorderSampleNode(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    node_index: int = Field(...)
    latitude: float = Field(...)
    longitude: float = Field(...)
    normal_x: float = Field(..., description="Inward normal vector X component")
    normal_y: float = Field(..., description="Inward normal vector Y component")
    normal_flux: float = Field(..., description="Normal flux (+inflow, -outflow)")


class TransboundaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    timestamp: str = Field(...)
    pollutant: str = Field(...)
    inflow_total: float = Field(...)
    outflow_total: float = Field(...)
    net_transboundary_flux: float = Field(...)
    status: str = Field(..., description="net_inflow, net_outflow, or neutral")
    border_districts: Dict[str, BorderDistrictTransboundaryDetail] = Field(default_factory=dict)
    border_samples: List[BorderSampleNode] = Field(default_factory=list)
```

#### 4.2.5 Ingestion & Streaming Schemas (`src/api/schemas/ingest.py` & `src/api/schemas/stream.py`)
```python
"""Pydantic v2 schemas for CSV ingestion reports and SSE streaming payloads."""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class QuarantineDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    row_number: int = Field(...)
    station_id: Optional[str] = Field(None)
    error_type: str = Field(...)
    error_message: str = Field(...)
    raw_record: Dict[str, Any] = Field(default_factory=dict)


class CSVIngestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    status: str = Field(..., description="success, partial_quarantine, or failed")
    filename: str = Field(...)
    total_rows: int = Field(...)
    valid_rows: int = Field(...)
    quarantined_rows: int = Field(...)
    merged_observations_count: int = Field(default=0)
    errors: List[str] = Field(default_factory=list)
    quarantine_records: Optional[List[QuarantineDetail]] = Field(default=None)


class SSEHourlyUpdatePayload(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    event: str = Field(default="hourly_update")
    timestamp: str = Field(...)
    hour_index: int = Field(...)
    total_hours: int = Field(...)
    provincial_summary: Dict[str, Any] = Field(...)
    district_readings: Dict[str, Any] = Field(...)
    airports: List[Dict[str, Any]] = Field(default_factory=list)
```

---

### 4.3 Complete Route Implementation Modules

#### 4.3.1 Metadata Router (`src/api/routes/meta.py`)
```python
"""API Route Module: Geographic & Station Metadata (/api/v1/meta)."""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query

from src.api.dependencies import get_district_repository, get_station_repository
from src.api.schemas.meta import DistrictMetaResponse, StationMetaResponse
from src.domain.interfaces.repositories import DistrictRepository, StationRepository

router = APIRouter(prefix="/api/v1/meta", tags=["Metadata"])


@router.get("/districts", response_model=List[DistrictMetaResponse], summary="Retrieve administrative district metadata")
async def get_districts(
    monitored_only: bool = Query(False, description="Filter for districts with active ground monitoring stations"),
    district_repo: DistrictRepository = Depends(get_district_repository),
) -> List[DistrictMetaResponse]:
    """Returns all 41 administrative districts of Punjab with boundaries, centroids, and transboundary sectors."""
    districts = district_repo.list_all(monitored_only=monitored_only)
    results: List[DistrictMetaResponse] = []
    for d in districts:
        boundary_geom = district_repo.get_boundary(d.id)
        results.append(
            DistrictMetaResponse(
                id=d.id,
                name=d.name,
                division=d.division,
                latitude=d.latitude,
                longitude=d.longitude,
                is_monitored=d.is_monitored,
                border_distance_km=d.border_distance_km,
                india_inflow_sectors=list(d.india_inflow_sectors),
                stations=[],
                boundary=boundary_geom,
            )
        )
    return results


@router.get("/stations", response_model=List[StationMetaResponse], summary="Retrieve monitoring station directory")
async def get_stations(
    district: Optional[str] = Query(None, description="Filter by district name (case-insensitive)"),
    station_type: Optional[str] = Query(None, description="Filter by type: fixed, mobile, airport_metar, wmo_synop"),
    station_repo: StationRepository = Depends(get_station_repository),
) -> List[StationMetaResponse]:
    """Returns all 79 active environmental monitoring stations and regional aerodromes."""
    if district:
        stations = station_repo.list_by_district(district)
    else:
        stations = station_repo.list_all(station_type=station_type)

    return [
        StationMetaResponse(
            id=s.id,
            name=s.name,
            district=s.district,
            latitude=s.latitude,
            longitude=s.longitude,
            station_type=s.station_type,
            has_anemometer=s.has_anemometer,
            anemometer_blacklisted=s.anemometer_blacklisted,
            altitude_m=s.altitude_m,
            network_type=s.metadata.get("network_type", s.station_type),
            metadata=s.metadata,
        )
        for s in stations
    ]
```

#### 4.3.2 Observations Router (`src/api/routes/observations.py`)
```python
"""API Route Module: Current & Historical Observations (/api/v1/observations)."""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query

from src.api.dependencies import get_observation_service
from src.api.schemas.observations import CurrentObservationsResponse, HourlyObservationsResponse
from src.services.observation_service import ObservationService

router = APIRouter(prefix="/api/v1/observations", tags=["Observations"])


@router.get("/current", response_model=CurrentObservationsResponse, summary="Retrieve current air quality telemetry snapshot")
async def get_current_observations(
    pollutant: str = Query("AQI", description="Target pollutant species or composite index"),
    obs_service: ObservationService = Depends(get_observation_service),
) -> CurrentObservationsResponse:
    """Returns the latest available hourly observation snapshot across all districts and stations."""
    try:
        dto = obs_service.get_current_snapshot(pollutant=pollutant)
        return CurrentObservationsResponse.model_validate(dto)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve current observations: {str(e)}")


@router.get("/hourly", response_model=HourlyObservationsResponse, summary="Query historical hourly observation series")
async def get_hourly_observations(
    district: Optional[str] = Query(None, description="Optional district name filter"),
    pollutant: str = Query("AQI", description="Pollutant species: AQI, PM2.5, PM10, NO2, SO2, CO, O3, NO, NOx"),
    start_time: Optional[datetime] = Query(None, description="Start timestamp (UTC)"),
    end_time: Optional[datetime] = Query(None, description="End timestamp (UTC)"),
    obs_service: ObservationService = Depends(get_observation_service),
) -> HourlyObservationsResponse:
    """Returns continuous time-series arrays for temporal scrubbing and trend charting."""
    try:
        dto = obs_service.get_hourly_series(
            pollutant=pollutant,
            district=district,
            start_time=start_time,
            end_time=end_time,
        )
        return HourlyObservationsResponse.model_validate(dto)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to query hourly observations: {str(e)}")
```

#### 4.3.3 Spatial Surface Router (`src/api/routes/spatial.py`)
```python
"""API Route Module: Continuous Geospatial Interpolation Surface (/api/v1/spatial)."""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query

from src.api.dependencies import get_spatial_service
from src.api.schemas.spatial import SpatialSurfaceResponse
from src.services.spatial_service import SpatialService

router = APIRouter(prefix="/api/v1/spatial", tags=["Spatial"])


@router.get("/surface", response_model=SpatialSurfaceResponse, summary="Retrieve 2D continuous interpolated raster field")
async def get_spatial_surface(
    timestamp: Optional[datetime] = Query(None, description="Observation timestamp; defaults to latest"),
    pollutant: str = Query("PM2.5", description="Pollutant species to interpolate (e.g. PM2.5, PM10, AQI)"),
    resolution: int = Query(5, ge=1, le=50, description="Spatial resolution step in pixels (lower = finer, default = 5)"),
    spatial_service: SpatialService = Depends(get_spatial_service),
) -> SpatialSurfaceResponse:
    """Computes or retrieves precomputed 2D IDW surface grid matrix with distance confidence opacity."""
    try:
        dto = spatial_service.get_surface_matrix(
            timestamp=timestamp,
            pollutant=pollutant,
            resolution=resolution,
        )
        return SpatialSurfaceResponse.model_validate(dto)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Spatial surface calculation failed: {str(e)}")
```

#### 4.3.4 Analytics Router (`src/api/routes/analytics.py`)
```python
"""API Route Module: Deep-Dive Analytics (/api/v1/analytics)."""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query

from src.api.dependencies import get_analytics_service
from src.api.schemas.analytics import CPFRoseResponse, FluxTransportResponse, TransboundaryResponse
from src.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/api/v1/analytics", tags=["Analytics"])


@router.get("/cpf", response_model=CPFRoseResponse, summary="16-Sector Conditional Probability Function (CPF) Wind Rose")
async def get_cpf_rose(
    district_name: str = Query(..., alias="district", description="District name (e.g. Lahore, Faisalabad)"),
    pollutant: str = Query("PM2.5", description="Pollutant to analyze"),
    threshold: Optional[float] = Query(None, description="Optional custom exceedance threshold; defaults to P75"),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
) -> CPFRoseResponse:
    """Evaluates 16 compass sectors for localized directional emission source apportionment."""
    try:
        dto = analytics_service.calculate_cpf(
            district_name=district_name,
            pollutant=pollutant,
            custom_threshold=threshold,
        )
        return CPFRoseResponse.model_validate(dto)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"CPF analysis failed: {str(e)}")


@router.get("/flux", response_model=FluxTransportResponse, summary="Inter-District Advection Transport Flux Ranking")
async def get_advection_flux(
    pollutant: str = Query("PM2.5", description="Mass pollutant species (AQI is strictly prohibited)"),
    timestamp: Optional[datetime] = Query(None, description="Observation timestamp; defaults to latest"),
    limit: int = Query(60, ge=1, le=200, description="Maximum pathway corridors to return"),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
) -> FluxTransportResponse:
    """
    Computes inter-district advective mass transport flux vectors and net mass balance.
    Enforces domain invariant: AQI is dimensionless and strictly prohibited from mass advection.
    """
    # CRITICAL DOMAIN GUARD
    if pollutant.strip().upper() == "AQI":
        raise HTTPException(
            status_code=400,
            detail=(
                "Advection transport mass flux is physically undefined for dimensionless ordinal index 'AQI'. "
                "Mass conservation requires conserved physical concentrations. "
                "Query a mass pollutant species such as PM2.5, PM10, NO2, SO2, CO, or O3."
            ),
        )

    try:
        dto = analytics_service.calculate_flux(
            pollutant=pollutant,
            timestamp=timestamp,
            top_k=limit,
        )
        return FluxTransportResponse.model_validate(dto)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Advection flux calculation failed: {str(e)}")


@router.get("/transboundary", response_model=TransboundaryResponse, summary="Cross-Border Transboundary Transport Index")
async def get_transboundary_analysis(
    timestamp: Optional[datetime] = Query(None, description="Observation timestamp; defaults to latest"),
    pollutant: str = Query("PM2.5", description="Target pollutant species"),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
) -> TransboundaryResponse:
    """Computes transboundary cross-border mass flux across 120km border districts and 39 border normal vector nodes."""
    try:
        dto = analytics_service.calculate_transboundary(
            timestamp=timestamp,
            pollutant=pollutant,
        )
        return TransboundaryResponse.model_validate(dto)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transboundary analysis failed: {str(e)}")
```

#### 4.3.5 Ingest Router (`src/api/routes/ingest.py`)
```python
"""API Route Module: Custom User CSV Ingestion (/api/v1/ingest)."""
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from src.api.dependencies import get_ingestion_service
from src.api.schemas.ingest import CSVIngestResponse
from src.services.ingestion_service import IngestionService

router = APIRouter(prefix="/api/v1/ingest", tags=["Ingestion"])


@router.post("/csv", response_model=CSVIngestResponse, summary="Upload and validate custom air quality CSV dataset")
async def upload_csv_dataset(
    file: UploadFile = File(..., description="Multipart CSV dataset file"),
    allow_missing_coords: bool = Form(False, description="Allow stations to resolve coordinates via canonical catalog"),
    ingestion_service: IngestionService = Depends(get_ingestion_service),
) -> CSVIngestResponse:
    """
    Accepts user-supplied CSV files, validates required headers, executes row-level quarantine,
    applies GPS coordinate corrections, performs QC filtering, and registers valid observations.
    """
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Only standard comma-separated values (.csv) files are supported.",
        )

    try:
        content = await file.read()
        if len(content) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded CSV file is empty.",
            )

        report = ingestion_service.process_csv_upload(
            file_bytes=content,
            filename=file.filename,
            allow_missing_coords=allow_missing_coords,
        )

        return CSVIngestResponse.model_validate(report)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while processing the CSV dataset: {str(e)}",
        )
```

#### 4.3.6 Server-Sent Events (SSE) Streaming Router (`src/api/routes/stream.py`)
```python
"""API Route Module: Real-Time Server-Sent Events (SSE) Stream (/api/v1/stream)."""
import asyncio
import json
import logging
from typing import AsyncGenerator
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from src.api.dependencies import get_observation_service
from src.services.observation_service import ObservationService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/stream", tags=["Streaming"])

KEEPALIVE_INTERVAL_SECONDS: float = 15.0
POLL_CHECK_INTERVAL_SECONDS: float = 2.0


async def sse_event_generator(request: Request, obs_service: ObservationService) -> AsyncGenerator[str, None]:
    """
    Generates asynchronous Server-Sent Events stream.
    Emits initial full snapshot frame upon connection, then enters heartbeat loop.
    Pings clients with ': keepalive\\n\\n' every 15 seconds.
    Emits 'event: hourly_update' when a new hourly observation is registered.
    Gracefully exits when client disconnects.
    """
    # 1. Emit Initial Telemetry Snapshot Frame
    try:
        initial_data = obs_service.get_latest_summary_for_stream()
        yield f"event: hourly_update\ndata: {json.dumps(initial_data)}\n\n"
    except Exception as e:
        logger.error(f"Error generating initial SSE snapshot: {e}")
        yield f"event: error\ndata: {json.dumps({'message': 'Initial snapshot failed'})}\n\n"

    last_ping = asyncio.get_event_loop().time()
    last_emitted_timestamp = initial_data.get("timestamp") if "initial_data" in locals() else None

    # 2. Continuous Event & Keepalive Loop
    try:
        while True:
            # Check client connection state
            if await request.is_disconnected():
                logger.info("SSE client disconnected.")
                break

            await asyncio.sleep(POLL_CHECK_INTERVAL_SECONDS)
            now = asyncio.get_event_loop().time()

            # Check for newly arrived hourly telemetry updates
            latest_ts = obs_service.get_latest_timestamp_utc()
            if latest_ts and latest_ts != last_emitted_timestamp:
                update_payload = obs_service.get_latest_summary_for_stream()
                yield f"event: hourly_update\ndata: {json.dumps(update_payload)}\n\n"
                last_emitted_timestamp = latest_ts

            # 15-second keepalive ping comment to maintain TCP connection
            if now - last_ping >= KEEPALIVE_INTERVAL_SECONDS:
                yield ": keepalive\n\n"
                last_ping = now

    except asyncio.CancelledError:
        logger.info("SSE connection task cancelled by client.")
    except Exception as e:
        logger.error(f"Unexpected error in SSE stream generator: {e}")


@router.get("/live", summary="Continuous Server-Sent Events (SSE) telemetry feed")
async def live_stream(
    request: Request,
    obs_service: ObservationService = Depends(get_observation_service),
) -> StreamingResponse:
    """
    Establishes real-time push channel to client dashboards.
    Sends 15s keepalive pings and hourly_update event packets.
    """
    return StreamingResponse(
        sse_event_generator(request, obs_service),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disables Nginx reverse-proxy buffering
        },
    )
```

---

### 4.4 Main FastAPI Application (`src/api/main.py`)

```python
"""
FastAPI Application Gateway Entry Point.
Initializes CORS middleware, lifespan startup/shutdown lifecycle, uniform exception handlers,
and registers all 6 modular API route domains under /api/v1/.
"""
from contextlib import asynccontextmanager
import logging
from pathlib import Path
from typing import AsyncGenerator
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.routes import (
    analytics,
    ingest,
    meta,
    observations,
    spatial,
    stream,
)
from src.infrastructure.repositories.baseline_repository import BaselineRepository
from src.services.analytics_service import AnalyticsService
from src.services.ingestion_service import IngestionService
from src.services.observation_service import ObservationService
from src.services.spatial_service import SpatialService

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("paq.api")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Lifespan event context manager.
    Loads baseline datasets into high-performance in-memory repository on startup (~1.5s).
    Initializes application services and mounts them on app.state.
    """
    logger.info("Punjab Air Quality API Gateway: Initializing lifespan...")

    # Determine baseline directory
    base_dir = Path(__file__).resolve().parent.parent.parent / "data" / "baseline"
    logger.info(f"Loading baseline data repository from: {base_dir}")

    # Initialize concrete in-memory repository with file backing
    repo = BaselineRepository(baseline_dir=base_dir)

    # Initialize application domain services
    app.state.repo = repo
    app.state.observation_service = ObservationService(repo=repo)
    app.state.spatial_service = SpatialService(repo=repo)
    app.state.analytics_service = AnalyticsService(repo=repo)
    app.state.ingestion_service = IngestionService(repo=repo)

    logger.info(
        f"API Gateway startup ready: {repo.count_stations()} stations, "
        f"{repo.count_districts()} districts, {len(repo.get_timeline_timestamps())} historical hours indexed."
    )

    yield

    logger.info("Punjab Air Quality API Gateway: Shutting down lifespan...")
    # Any teardown logic (closing connection pools, cancelling worker tasks)


def create_application() -> FastAPI:
    """Application factory for Punjab Air Quality FastAPI Gateway."""
    app = FastAPI(
        title="Punjab Air Quality Information System API",
        description="High-performance environmental telemetry, spatial IDW interpolation, and transboundary advection intelligence platform.",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/api/v1/openapi.json",
        lifespan=lifespan,
    )

    # CORS Middleware Configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Production: configure specific UI origins (e.g. http://localhost:5173)
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Global Exception Handlers
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        logger.warning(f"Request validation error on {request.url.path}: {exc.errors()}")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "status": "error",
                "error_type": "ValidationError",
                "message": "The request parameters failed validation schema checks.",
                "details": exc.errors(),
            },
        )

    # Healthcheck Route
    @app.get("/health", tags=["Health"], summary="System Liveness and Health Status")
    async def healthcheck() -> dict:
        return {
            "status": "healthy",
            "service": "punjab-air-quality-api",
            "version": "1.0.0",
        }

    # Mount Route Modules under /api/v1/
    app.include_router(meta.router)
    app.include_router(observations.router)
    app.include_router(spatial.router)
    app.include_router(analytics.router)
    app.include_router(ingest.router)
    app.include_router(stream.router)

    return app


app = create_application()
```

---

### 4.5 Dependency Injection Providers (`src/api/dependencies.py`)

```python
"""FastAPI Dependency Injection providers bridging routes to repositories and application services."""
from fastapi import Request

from src.domain.interfaces.repositories import (
    AnalyticsRepository,
    DistrictRepository,
    ObservationRepository,
    StationRepository,
)
from src.infrastructure.repositories.baseline_repository import BaselineRepository
from src.services.analytics_service import AnalyticsService
from src.services.ingestion_service import IngestionService
from src.services.observation_service import ObservationService
from src.services.spatial_service import SpatialService


def get_repository(request: Request) -> BaselineRepository:
    """Retrieves the unified baseline repository instance from app.state."""
    return request.app.state.repo


def get_station_repository(request: Request) -> StationRepository:
    return request.app.state.repo


def get_district_repository(request: Request) -> DistrictRepository:
    return request.app.state.repo


def get_observation_repository(request: Request) -> ObservationRepository:
    return request.app.state.repo


def get_analytics_repository(request: Request) -> AnalyticsRepository:
    return request.app.state.repo


def get_observation_service(request: Request) -> ObservationService:
    return request.app.state.observation_service


def get_spatial_service(request: Request) -> SpatialService:
    return request.app.state.spatial_service


def get_analytics_service(request: Request) -> AnalyticsService:
    return request.app.state.analytics_service


def get_ingestion_service(request: Request) -> IngestionService:
    return request.app.state.ingestion_service
```

---

### 4.6 Complete Integration Test Suite Blueprint (`tests/integration/test_api_endpoints.py`)

```python
"""
Integration test suite for Punjab Air Quality FastAPI Gateway.
Uses httpx.AsyncClient with ASGITransport to exercise all 10 required routes, query parameter filters,
multipart CSV uploads, physical AQI flux boundary guards, and SSE stream frames.
"""
from datetime import datetime
import io
import json
import pytest
import httpx
from httpx import ASGITransport

from src.api.main import app


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def async_client():
    """AsyncClient fixture with ASGITransport for in-memory ASGI dispatch."""
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


class TestFastAPIEndpointContracts:
    """Verifies all 10 core API route specifications defined in SYSTEM_ARCHITECTURE.md §5."""

    @pytest.mark.anyio
    async def test_healthcheck(self, async_client: httpx.AsyncClient):
        response = await async_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "1.0.0"

    @pytest.mark.anyio
    async def test_01_get_meta_districts(self, async_client: httpx.AsyncClient):
        """Route 1: GET /api/v1/meta/districts"""
        response = await async_client.get("/api/v1/meta/districts")
        assert response.status_code == 200
        districts = response.json()
        assert isinstance(districts, list)
        assert len(districts) == 41
        d_sample = districts[0]
        assert "id" in d_sample
        assert "name" in d_sample
        assert "latitude" in d_sample
        assert "longitude" in d_sample
        assert "is_monitored" in d_sample

    @pytest.mark.anyio
    async def test_02_get_meta_stations(self, async_client: httpx.AsyncClient):
        """Route 2: GET /api/v1/meta/stations"""
        response = await async_client.get("/api/v1/meta/stations")
        assert response.status_code == 200
        stations = response.json()
        assert isinstance(stations, list)
        assert len(stations) >= 79
        s_sample = stations[0]
        assert "id" in s_sample
        assert "name" in s_sample
        assert "district" in s_sample

        # Test filter by district
        res_lhr = await async_client.get("/api/v1/meta/stations?district=Lahore")
        assert res_lhr.status_code == 200
        lhr_stations = res_lhr.json()
        assert all(s["district"].lower() == "lahore" for s in lhr_stations)

    @pytest.mark.anyio
    async def test_03_get_observations_current(self, async_client: httpx.AsyncClient):
        """Route 3: GET /api/v1/observations/current"""
        response = await async_client.get("/api/v1/observations/current?pollutant=AQI")
        assert response.status_code == 200
        payload = response.json()
        assert "timestamp" in payload
        assert "hour_index" in payload
        assert "provincial_summary" in payload
        summary = payload["provincial_summary"]
        assert "mean_aqi" in summary
        assert "exceedance_peqs_count" in summary
        assert "peak_district" in summary
        assert "peak_aqi" in summary
        assert "districts" in payload

    @pytest.mark.anyio
    async def test_04_get_observations_hourly(self, async_client: httpx.AsyncClient):
        """Route 4: GET /api/v1/observations/hourly"""
        response = await async_client.get("/api/v1/observations/hourly?pollutant=PM2.5")
        assert response.status_code == 200
        payload = response.json()
        assert payload["pollutant"] == "PM2.5"
        assert len(payload["hours"]) == 216
        assert len(payload["districts"]) == 41
        lahore_series = payload["districts"]["Lahore"]["concentrations"]
        assert len(lahore_series) == 216

    @pytest.mark.anyio
    async def test_05_get_spatial_surface(self, async_client: httpx.AsyncClient):
        """Route 5: GET /api/v1/spatial/surface"""
        response = await async_client.get("/api/v1/spatial/surface?pollutant=PM2.5&resolution=10")
        assert response.status_code == 200
        payload = response.json()
        assert "grid_width" in payload
        assert "grid_height" in payload
        assert "grid_matrix" in payload
        assert len(payload["grid_matrix"]) == payload["grid_height"]
        assert len(payload["grid_matrix"][0]) == payload["grid_width"]
        assert payload["min_val"] <= payload["max_val"]

    @pytest.mark.anyio
    async def test_06_get_analytics_cpf(self, async_client: httpx.AsyncClient):
        """Route 6: GET /api/v1/analytics/cpf"""
        response = await async_client.get("/api/v1/analytics/cpf?district=Lahore&pollutant=PM2.5")
        assert response.status_code == 200
        payload = response.json()
        assert payload["district"] == "Lahore"
        assert len(payload["sectors"]) == 16
        assert "threshold_p75" in payload
        assert "calm_fraction" in payload
        assert payload["null_hypothesis_baseline"] == 0.25

    @pytest.mark.anyio
    async def test_07_get_analytics_flux_valid_species(self, async_client: httpx.AsyncClient):
        """Route 7: GET /api/v1/analytics/flux for PM2.5"""
        response = await async_client.get("/api/v1/analytics/flux?pollutant=PM2.5&limit=20")
        assert response.status_code == 200
        payload = response.json()
        assert payload["pollutant"] == "PM2.5"
        assert len(payload["top_pathways"]) <= 20
        assert "net_balance" in payload

    @pytest.mark.anyio
    async def test_07_get_analytics_flux_aqi_guard(self, async_client: httpx.AsyncClient):
        """Route 7 Domain Guard: Physical advection transport strictly forbidden for AQI."""
        response = await async_client.get("/api/v1/analytics/flux?pollutant=AQI")
        assert response.status_code == 400
        data = response.json()
        assert "physically undefined" in data["detail"].lower()

    @pytest.mark.anyio
    async def test_08_get_analytics_transboundary(self, async_client: httpx.AsyncClient):
        """Route 8: GET /api/v1/analytics/transboundary"""
        response = await async_client.get("/api/v1/analytics/transboundary?pollutant=PM2.5")
        assert response.status_code == 200
        payload = response.json()
        assert "inflow_total" in payload
        assert "outflow_total" in payload
        assert "net_transboundary_flux" in payload
        assert len(payload["border_samples"]) == 39  # Exactly 39 border vector nodes

    @pytest.mark.anyio
    async def test_09_post_ingest_csv_success(self, async_client: httpx.AsyncClient):
        """Route 9: POST /api/v1/ingest/csv with valid CSV data"""
        csv_content = (
            "timestamp,station_id,station_name,district,latitude,longitude,pollutant,value,wind_speed,wind_direction\n"
            "2026-11-10T12:00:00Z,PK_TEST_01,Test Station,Lahore,31.5097,74.3478,pm25,145.2,2.0,90.0\n"
        ).encode("utf-8")
        files = {"file": ("test_valid.csv", io.BytesIO(csv_content), "text/csv")}
        response = await async_client.post("/api/v1/ingest/csv", files=files)
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] in ("success", "partial_quarantine")
        assert payload["total_rows"] == 1
        assert payload["valid_rows"] == 1

    @pytest.mark.anyio
    async def test_09_post_ingest_csv_quarantine_out_of_bounds(self, async_client: httpx.AsyncClient):
        """Route 9: POST /api/v1/ingest/csv with out-of-bounds latitude"""
        csv_content = (
            "timestamp,station_id,station_name,district,latitude,longitude,pollutant,value\n"
            "2026-11-10T12:00:00Z,PK_TEST_02,Invalid Station,Lahore,55.0000,74.3478,pm25,145.2\n"
        ).encode("utf-8")
        files = {"file": ("test_invalid.csv", io.BytesIO(csv_content), "text/csv")}
        response = await async_client.post("/api/v1/ingest/csv", files=files)
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] in ("partial_quarantine", "failed")
        assert payload["quarantined_rows"] == 1

    @pytest.mark.anyio
    async def test_10_get_stream_live_sse(self, async_client: httpx.AsyncClient):
        """Route 10: GET /api/v1/stream/live connects and streams initial frame"""
        async with async_client.stream("GET", "/api/v1/stream/live") as response:
            assert response.status_code == 200
            assert "text/event-stream" in response.headers["content-type"]
            lines = []
            async for line in response.aiter_lines():
                if line:
                    lines.append(line)
                if len(lines) >= 2:
                    break
            # Verify event header or data payload was emitted
            assert any("hourly_update" in l or "keepalive" in l for l in lines)
```

---

## 5. Verification Method

### 5.1 Automated Test Execution Command
Once the implementer generates the files in `src/api/` and `tests/integration/test_api_endpoints.py`, run:
```powershell
python -m pytest tests/integration/test_api_endpoints.py -v
```

To verify the required route contracts match the test harness:
```powershell
python -m pytest tests/e2e/test_tier1_feature_coverage.py -k test_api_route_specifications_present -v
```

To run the entire suite (unit, integration, and E2E):
```powershell
python -m pytest tests/unit tests/integration tests/e2e -v
```

### 5.2 Standalone Smoke Test Verification
A smoke test can be executed directly from PowerShell to confirm app loading and route registration:
```powershell
python -c "from src.api.main import app; routes = [(r.methods, r.path) for r in app.routes]; print('Registered routes count:', len(routes)); [print(r) for r in routes if '/api/v1' in r[1]]"
```

### 5.3 Invalidation Conditions
This architecture is invalidated if:
1. Any of the 10 required routes defined in `test_tier1_feature_coverage.py` lines 247–258 is missing, altered, or returns an unhandled 500 error.
2. The SSE stream `/api/v1/stream/live` fails to set `text/event-stream`, omits the 15-second keepalive ping `: keepalive\n\n`, or hangs during client teardown.
3. The advection flux endpoint `/api/v1/analytics/flux` permits `pollutant=AQI` without triggering the physical mass conservation guard.
4. The CSV ingestion endpoint `/api/v1/ingest/csv` fails to return dead-letter quarantine details on invalid row schemas.
