# Project: Punjab Air Quality Monitoring, Processing, and Visualization System

## Architecture
Decoupled Clean Architecture across 4 layers with strict dependency inversion:
1. **Domain Layer (`src/domain/`)**: Pure entities, mathematical transformation algorithms (IDW, anisotropic wind-steered surface, CPF polar roses, advection flux with physical AQI guards, PEPC breakpoint calculations, temporal QC filters, equirectangular projection), value objects, and repository interfaces. Completely decoupled from external frameworks, databases, and I/O.
2. **Application / Service Layer (`src/services/` & `src/pipelines/`)**: Ingestion pipeline services (EPA Punjab, AviationWeather METAR, WMO SYNOP, ECMWF Open-Meteo), schema-conforming fallback templating, user CSV ingestion and validation engine, spatial surface interpolation service, and analytics aggregation services.
3. **Infrastructure & Persistence Layer (`src/infrastructure/`)**: Storage adapters (in-memory, file-based baseline, TimescaleDB/PostGIS compatible models), HTTP clients with AWS full-jitter backoff and circuit breaking, and CSV stream parsers.
4. **Presentation & Delivery Layer (`src/api/` & `src/frontend/`)**: 
   - Backend API: FastAPI OpenAPI 3.1 REST endpoints and SSE live streaming server.
   - Frontend Dashboard: Component-driven UI hierarchy (5 zones), 5-layer decoupled canvas rendering engine (basemap, continuous field IDW rasterizer, wind particle advection ring buffer, dynamic transport vectors, collision-free station labels), Zustand state slices, and WCAG 2.1 AAA accessible theme system.

---

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| F01 | Workspace Archival (R1) | Relocate `index.html` and `collector/` to `original System/` while preserving `docs/` and `.agents/` | M1 | ORIGINAL_REQUEST §R1 |
| F02 | Baseline Data Extraction | Extract 79 stations, 41 districts, 6 airports, and 216-hour historical dataset from `index.html` into structured JSON | M1 | ORIGINAL_REQUEST §R2 |
| F03 | Discrete Geodesic IDW (T1) | Haversine $R=6371\text{ km}, p=2, d_0=5\text{ km}$ spatial imputation for unmonitored districts | M2 | TRANSFORMATION_LOGIC_SPEC §2.1 |
| F04 | Anisotropic Continuous Surface IDW (T2) | Wind-steered 2D continuous field with $\epsilon^2=16\text{ px}^2, \cos\alpha$, velocity saturation, $[0.3, 1.7]$ multiplier, $[95, 235]$ opacity | M2 | TRANSFORMATION_LOGIC_SPEC §2.2 |
| F05 | Vector Wind Conversion & QC (T4) | Polar-to-Cartesian $(u, v)$ conversion, bounds $[0, 30\text{ m/s}]$, Wazirabad $140^\circ$ sensor offset blacklist | M2 | TRANSFORMATION_LOGIC_SPEC §2.4 |
| F06 | CPF Polar Wind Roses (T5) | 16 sectors ($22.5^\circ$), pooled station-hour $P_{75}$ threshold $\tau$, calm $<0.5\text{ m/s}$ exclusion, $N_k < 6$ small-sample suppression | M2 | TRANSFORMATION_LOGIC_SPEC §2.5 |
| F07 | Advection Transport Flux (T6) | Physical mass flux for inter-district transport ($d \le 180\text{ km}, \Delta\theta \le 35^\circ, L_S=100\text{ km}$), physical dimension guard disabling for AQI | M2 | TRANSFORMATION_LOGIC_SPEC §2.6 |
| F08 | Receptor CPF Pathway Coupling (T7) | Coupling flux with receptor wind rose feedback $\Omega$, $0.25$ isotropic fallback, top 60 pathway ranking | M2 | TRANSFORMATION_LOGIC_SPEC §2.7 |
| F09 | Transboundary Cross-Border Index (T8) | 120 km border belt, 39 normal vector nodes, 117 CAMS perimeter nodes, net inflow/outflow metrics | M2 | TRANSFORMATION_LOGIC_SPEC §2.8 |
| F10 | PEPC Breakpoints & Color Mapping (T9) | Piecewise linear AQI interpolation across continuous half-open intervals, 500 cap, $\max(I_{\text{PM2.5}}, I_{\text{PM10}})$, 7-stop continuous RGB ramp | M2 | TRANSFORMATION_LOGIC_SPEC §2.9 |
| F11 | Temporal QC & Scrubbing (T10) | Zero/negative purge, 7h median spike filter ($>4M_i \land >3\text{ref}_p$), 3h logger hold ($i \ge 2$ guard), 75% completeness rule, sub-hourly continuous lerp | M2 | TRANSFORMATION_LOGIC_SPEC §2.10 |
| F12 | Equirectangular Projection & Labels (T11) | Plate Carrée $K_X=\cos 31^\circ$, greedy 12-offset AABB collision-free label search with leader lines | M2 | TRANSFORMATION_LOGIC_SPEC §2.11 |
| F13 | Modular Ingestion Architecture | Unified Ingestion Worker interface and orchestration for multi-feed polling | M3 | DATA_SOURCES_AND_STREAMS §1 |
| F14 | EPA Punjab REST Ingestion | Live feed client for EPA Punjab dashboard API with custom User-Agent and error handling | M3 | DATA_SOURCES_AND_STREAMS §2.1 |
| F15 | NOAA METAR Ingestion | AviationWeather METAR feed parser for 12 aerodromes, knots-to-m/s and statute miles conversion | M3 | DATA_SOURCES_AND_STREAMS §2.2 |
| F16 | WMO SYNOP Ingestion | Ogimet SYNOP telegram decoder for Punjab blocks 415, 416, 417 | M3 | DATA_SOURCES_AND_STREAMS §2.3 |
| F17 | ECMWF IFS Open-Meteo Ingestion | Multi-point centroid query for 41 districts (10m and 925 hPa wind vectors) | M3 | DATA_SOURCES_AND_STREAMS §2.4 |
| F18 | Fallback Baseline Templating Engine | Schema-conforming fallback templating engine seeded from original system baseline data on 404/failure | M3 | ORIGINAL_REQUEST §R2 |
| F19 | User CSV Ingestion Adapter | Ingestion adapter accepting and validating user-provided CSV datasets | M3 | ORIGINAL_REQUEST §R2 |
| F20 | CSV Schema Validation & Normalization | Pydantic v2 validation enforcing required columns, coordinate boundaries, timestamp formats, and physical limits | M3 | DATA_PIPELINES_ARCHITECTURE §2 |
| F21 | Clean Architecture Domain Models | Isolated domain entities for stations, districts, observations, spatial grids, and transport links | M4 | SYSTEM_ARCHITECTURE §1 |
| F22 | Abstract Repository Interfaces | Decoupled data access interfaces for station metadata, time-series observations, and analytical caches | M4 | SYSTEM_ARCHITECTURE §2 |
| F23 | File & In-Memory Repository Implementation | Production-grade repository implementation supporting offline baseline, live updates, and user CSV data | M4 | SYSTEM_ARCHITECTURE §2 |
| F24 | District Metadata API | `GET /api/v1/meta/districts` returning 41 districts with coordinates, monitoring status, and polygons | M4 | SYSTEM_ARCHITECTURE §3.1 |
| F25 | Station Metadata API | `GET /api/v1/meta/stations` returning 79 stations with metadata, networks, and sensor types | M4 | SYSTEM_ARCHITECTURE §3.1 |
| F26 | Current Observations API | `GET /api/v1/observations/current` returning latest readings across all stations and districts | M4 | SYSTEM_ARCHITECTURE §3.2 |
| F27 | Hourly Time-Series API | `GET /api/v1/observations/hourly` returning historical time-series with pollutant filtering | M4 | SYSTEM_ARCHITECTURE §3.2 |
| F28 | Spatial Surface API | `GET /api/v1/spatial/surface` serving continuous interpolated raster/grid fields | M4 | SYSTEM_ARCHITECTURE §3.3 |
| F29 | CPF Analytics API | `GET /api/v1/analytics/cpf` returning 16-sector wind roses with calm ratio and threshold $\tau$ | M4 | SYSTEM_ARCHITECTURE §3.4 |
| F30 | Advection Flux Analytics API | `GET /api/v1/analytics/flux` returning top inter-district transport vectors and net balances | M4 | SYSTEM_ARCHITECTURE §3.4 |
| F31 | Transboundary Analytics API | `GET /api/v1/analytics/transboundary` returning border belt inflow/outflow metrics | M4 | SYSTEM_ARCHITECTURE §3.4 |
| F32 | CSV Upload & Validation API | `POST /api/v1/ingest/csv` accepting user datasets, validating schema, and loading into system | M4 | SYSTEM_ARCHITECTURE §3.5 |
| F33 | Server-Sent Events (SSE) Live Stream | `GET /api/v1/stream/live` providing continuous push updates with 15s keepalive heartbeat | M4 | SYSTEM_ARCHITECTURE §3.6 |
| F34 | Command Header & Live Status (Zone 1) | UI navigation, live clock, system health indicator, data source switcher (Live/Baseline/CSV) | M5 | UI_UX_SPECIFICATION §1.1 |
| F35 | Pollutant Switcher & Metric Selector (Zone 2) | Selector for 9 pollutants (AQI, PM2.5, PM10, NO2, SO2, CO, O3, NO, NOX) with active badges | M5 | UI_UX_SPECIFICATION §1.2 |
| F36 | Map Viewport & Time Scrubber Deck (Zone 3) | Interactive map console with 216-hour scrubber, animation controls, speed slider, mode radios | M5 | UI_UX_SPECIFICATION §1.3 |
| F37 | 5-Layer Canvas/Vector Map Renderer | Layer 0 (basemap), Layer 1 (continuous IDW), Layer 2 (1300 wind particles), Layer 3 (transport vectors), Layer 4 (labels) | M5 | UI_UX_SPECIFICATION §3 |
| F38 | Real-Time Sidebar & District Roster (Zone 4) | Province KPI cards, exceedance counter, highest district, airport winds, searchable district ranking | M5 | UI_UX_SPECIFICATION §1.4 |
| F39 | Deep-Dive Analytics & CPF Rose Deck (Zone 5) | Interactive 16-sector CPF rose canvas, small multiples, hourly tabular views, transboundary satellite card | M5 | UI_UX_SPECIFICATION §1.5 |
| F40 | Theme Tokens & WCAG 2.1 AAA Accessibility | Dark/Light themes, PEPC 7-stop palette, high-contrast text, tabular figures, ARIA live regions | M5 | UI_UX_SPECIFICATION §2 |
| F41 | Comprehensive Automated Test Suite (R6) | Unit, integration, API contract, and UI tests covering ingestion, math transforms, backend, and dashboard | M6 | ORIGINAL_REQUEST §R6 |
| F42 | Aspect-Ratio Adaptive Punjab Projection | Fit entire Punjab bbox (69.1°E-75.75°E, 27.55°N-34.3°N) with balanced padding in any canvas aspect ratio without clipping south | M7 | ORIGINAL_REQUEST Follow-up §1 |
| F43 | Interactive Map Navigation Controls | Pan, wheel zoom, zoom in (+), zoom out (-), reset view (⛶), fullscreen toggle with smooth bounds clamping | M7 | ORIGINAL_REQUEST Follow-up §2 |
| F44 | Fluid Responsive Layout & Zero Dead Space | Responsive CSS Grid/Flexbox eliminating black void below 1100px down to mobile 320px | M7 | ORIGINAL_REQUEST Follow-up §3 |
| F45 | Tier-1 UI/UX Craftsmanship & Anti-Slop Elevation | Figma/x.ai/Windy standard typography, spacing, micro-interactions, dark visual hierarchy per /taste-skill & /impeccable | M7 | ORIGINAL_REQUEST Follow-up §4 |
| F46 | Map Controls & Responsive Layout Test Suite | Automated unit & integration tests covering projection fitting, map controls, touch/wheel, and responsive layouts | M7 | ORIGINAL_REQUEST Follow-up §5 |

---

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Workspace Archival & Baseline Extraction | F01, F02: Relocate `index.html` and `collector/` to `original System/`, preserve `docs/` and `.agents/`, extract structured JSON baseline | none | DONE |
| M2 | Scientific Transformation Engine | F03–F12: Implement pure functions for all 11 scientific transformations and automated math unit tests | M1 | DONE |
| M3 | Data Pipelines & CSV Ingestion Engine | F13–F20: Ingestion workers (EPA, METAR, SYNOP, ECMWF), fallback template engine, user CSV adapter & validator | M1 | DONE |
| M4 | Core Backend Services & API Gateway | F21–F33: Clean architecture domain models, repositories, FastAPI REST endpoints, CSV upload API, SSE streaming | M2, M3 | DONE |
| M5 | Component-Driven UI/UX Dashboard | F34–F40: 5-zone UI hierarchy, 5-layer canvas renderer, wind particle simulation, CPF rose canvas, theme tokens | M4 | DONE |
| M6 | Final E2E Integration, Verification & Audit | F41: 100% pass of E2E test suite (Tiers 1-4), Tier 5 adversarial coverage hardening, forensic audit verification | M1, M2, M3, M4, M5 | DONE |
| M7 | UI/UX & Map Controls Overhaul | F42–F46: Adaptive projection, map navigation controls, fluid responsive layouts, tier-1 craftsmanship, zero regressions | M5, M6 | IN_PROGRESS |

---

## Interface Contracts

### 1. Mathematical Transformation Function Signatures (`src/domain/math/`)
- `haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float` (km)
- `discrete_geodesic_idw(target: tuple[float, float], stations: list[dict], power: float = 2.0, d0: float = 5.0) -> Optional[float]`
- `anisotropic_idw(target_px: tuple[float, float], stations: list[dict], wind_vector: tuple[float, float], scale: float) -> tuple[float, float, int]` -> `(value, d_min, alpha)`
- `polar_to_cartesian_wind(speed_ms: float, dir_deg: float) -> tuple[float, float]` -> `(u, v)` with QC bounds $[0, 30]$
- `calculate_cpf_rose(observations: list[dict], threshold_p75: float, calm_threshold: float = 0.5) -> dict` -> `{sectors: list[Optional[float]], calm_ratio: float, threshold: float}`
- `calculate_advection_flux(source_station: dict, receptor_coords: tuple[float, float], pollutant: str) -> Optional[dict]` -> `None` if pollutant == `'AQI'`
- `calculate_receptor_coupling(flux_series: list[dict], receptor_cpf: dict) -> list[dict]` -> Top 60 ranked pathway links
- `calculate_transboundary_index(border_districts: list[dict], border_normals: list[dict]) -> dict`
- `pepc_calculate_aqi(pollutant: str, concentration: float) -> Optional[int]` (0–500 cap, continuous half-open intervals)
- `pepc_composite_aqi(pm25_aqi: Optional[int], pm10_aqi: Optional[int]) -> Optional[int]` -> $\max(I_{\text{PM2.5}}, I_{\text{PM10}})$
- `pepc_get_color(aqi: int) -> str` (Hex / RGB continuous 7-stop PEQS ramp)
- `temporal_qc_clean(series: list[float], ref_limit: float, pollutant: str) -> tuple[list[Optional[float]], int]`

### 2. Ingestion & Validation Schemas (`src/domain/schemas/`)
- `RawMeasurement`: Pydantic model for station measurement with upper bound `le=5000.0`.
- `UserCSVRow`: Pydantic model for CSV ingestion:
  - `timestamp`: ISO-8601 or `YYYY-MM-DD HH:MM`
  - `station_id`: str, `station_name`: str, `district`: str
  - `latitude`: float (in $[27.0, 35.0]$), `longitude`: float (in $[69.0, 76.0]$)
  - `pollutant`: str (one of `aqi, pm25, pm10, no2, so2, co, o3, no, nox`)
  - `value`: float ($\ge 0, \le 5000.0$)
  - `wind_speed`: Optional[float] ($[0, 30.0]$), `wind_direction`: Optional[float] ($[0, 360.0]$)

### 3. API REST Endpoints (`src/api/routes/`)
- `GET /api/v1/meta/districts` -> `list[DistrictMetaResponse]`
- `GET /api/v1/meta/stations` -> `list[StationMetaResponse]`
- `GET /api/v1/observations/current?pollutant={p}` -> `CurrentObservationsResponse`
- `GET /api/v1/observations/hourly?district={d}&pollutant={p}&start={s}&end={e}` -> `HourlyObservationsResponse`
- `GET /api/v1/spatial/surface?pollutant={p}&timestamp={t}&resolution={r}` -> `SpatialSurfaceResponse`
- `GET /api/v1/analytics/cpf?district={d}&pollutant={p}` -> `CPFRoseResponse`
- `GET /api/v1/analytics/flux?pollutant={p}&timestamp={t}` -> `FluxTransportResponse`
- `GET /api/v1/analytics/transboundary?timestamp={t}` -> `TransboundaryResponse`
- `POST /api/v1/ingest/csv` -> Multipart form file upload -> `{status: "success", rows_ingested: int, errors: list[str]}`
- `GET /api/v1/stream/live` -> SSE stream (`text/event-stream`)

---

## Code Layout
```
c:\Users\Asif\Downloads\Punjab Air Quality\
├── original System/             # Archived legacy files (index.html, collector/)
│   ├── index.html
│   └── collector/
│       └── collector.py
├── docs/                        # Architecture & system specifications (preserved)
├── data/
│   ├── baseline/                # Extracted baseline JSON records & station catalog
│   └── samples/                 # Sample valid and invalid user CSV datasets
├── src/
│   ├── domain/                  # Clean architecture domain entities & math pure functions
│   │   ├── entities/            # Station, District, Observation, Metric entities
│   │   ├── math/                # IDW, anisotropic, CPF, flux, PEPC, QC pure algorithms
│   │   └── schemas/             # Pydantic data contracts & CSV validation schemas
│   ├── pipelines/               # Ingestion microservices & fallback templating
│   │   ├── base.py              # Ingestion interface
│   │   ├── epa_punjab.py        # EPA Punjab live scraper
│   │   ├── metar.py             # NOAA AviationWeather METAR client
│   │   ├── synop.py             # WMO Ogimet SYNOP parser
│   │   ├── open_meteo.py        # ECMWF IFS 10m/925hPa client
│   │   ├── fallback_engine.py   # Baseline template fallback engine
│   │   └── csv_adapter.py       # User CSV dataset ingestion & validator
│   ├── infrastructure/          # Storage & HTTP infrastructure
│   │   ├── repositories/        # In-memory / file baseline / SQLite repositories
│   │   └── http_client.py       # Robust HTTP client with retry/jitter/backoff
│   ├── services/                # Application business logic
│   │   ├── spatial_service.py   # IDW surface generator service
│   │   ├── analytics_service.py # CPF & transport flux analytics service
│   │   └── observation_service.py # Time-series aggregation & station queries
│   ├── api/                     # Backend API presentation layer
│   │   ├── app.py               # FastAPI application setup & middleware
│   │   └── routes/              # Modular API routers (meta, observations, spatial, analytics, ingest, sse)
│   └── frontend/                # Interactive UI Dashboard
│       ├── public/              # Static assets & icons
│       └── src/                 # Component-driven dashboard
│           ├── components/      # UI components (Header, Map, Scrubber, Sidebar, Rose, Tables)
│           ├── renderers/       # 5-layer Canvas rendering engine & particle simulation
│           ├── stores/          # Zustand reactive state slices
│           └── theme/           # Design tokens, PEPC palette, typography, WCAG AAA styles
└── tests/                       # Comprehensive automated verification suite
    ├── unit/
    │   ├── test_transformations.py # Deterministic mathematical tests
    │   ├── test_pepc_aqi.py        # PEPC breakpoint and color tests
    │   └── test_qc_filters.py      # Spike and logger hold tests
    ├── integration/
    │   ├── test_pipelines.py       # Ingestion & fallback templating tests
    │   ├── test_csv_adapter.py     # User CSV ingestion & validation tests
    │   └── test_api_endpoints.py   # FastAPI endpoint contract tests
    └── e2e/                        # End-to-end user workflows & test runner
        ├── test_e2e_scenarios.py
        └── run_all_tests.py
```
