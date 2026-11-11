# Architecture & Systems Specification Mining Report (Handoff)

**Document ID:** `PAQ-HANDOFF-SPEC-ARCH-001`  
**Agent:** `spec_miner_architecture`  
**Working Directory:** `c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\spec_miner_architecture\`  
**Target Recipient:** Orchestrator (`c384b499-9dff-40dc-b63d-721df47da08f`) and downstream Implementers  
**Date:** 2026-11-10T12:44:30Z  

---

## 1. Observation

Direct forensic examination of the specification documents and existing workspace artifacts revealed the following authoritative architecture, interface, and data definitions:

1. **Master Architecture Synthesis (`docs/ARCHITECTURE_OVERVIEW.md`):**
   - Lines 18–43: Defines the decoupled 4-Tier Target Production Architecture:
     - *Tier 1:* Asynchronous Ingestion & Pipeline Microservices (EPA Punjab, METAR, WMO SYNOP, ECMWF IFS, NASA FIRMS, IQAir, CAMS).
     - *Tier 2:* Relational Time-Series & Geostatistical Processing Tier (PostgreSQL 16 + PostGIS 3.4 + TimescaleDB 2.14 Hypertables + Redis 7.2 Cache).
     - *Tier 3:* API & Application Service Gateway (FastAPI OpenAPI 3.1 + SSE/WebSocket live streaming).
     - *Tier 4:* Client Presentation Console (React 19 + TypeScript + Zustand + 5-Layer Canvas/WebGL rendering).
   - Lines 126–184: Formulates the 8 consolidated technical remediations:
     - (1) TimescaleDB `PRIMARY KEY (time, station_id)` and `ON CONFLICT DO UPDATE`.
     - (2) Pydantic upper bound `le=5000.0` with `QC_EXCEEDANCE_EXTREME` for readings $>1000.0\ \mu\text{g/m}^3$; `Optional[Any] = None` for `pollutant_flags`.
     - (3) CPF wind rose $N_k \ge 6$ small-sample suppression rule.
     - (4) PEPC continuous half-open intervals $(BP_{i-1}, BP_i]$ and operational AQI 500 cap.
     - (5) Step 0 zero/negative nullification; 3h logger hold $i \ge 2$ index guard (exempting composite AQI); anemometer $0–30\text{ m/s}$ bounds and Wazirabad $140^\circ$ vane offset purge.
     - (6) Advection transport disabled for dimensionless AQI; truncated to top 60 links; disambiguation of 39 border animation nodes from 117 CAMS perimeter nodes.
     - (7) `asyncio.gather` with `asyncio.Semaphore(10)` and 3s per-district timeout for fallback fan-out.
     - (8) WebGL/downsampled IDW $<3\text{ ms}$; pre-allocated `Float32Array` ring buffer for 1,300 particles.

2. **External Data Streams & QC Engine (`docs/DATA_SOURCES_AND_STREAMS.md`):**
   - Lines 70–80: Stream inventory summary (STR-01 to STR-07), protocols, cron cadences, endpoints, and destinations.
   - Lines 88–163: EPA Punjab REST endpoints (`/api/dashboard/current`, `/api/districts`, `/api/district-stations/{name}`), User-Agent `EMC-EPA-Punjab-AQ-dashboard/1.0`, payload schema with 9 pollutants + anemometer registers.
   - Lines 167–217: NOAA METAR stream covering 12 aerodromes (`OPLA, OPFA, OPMT, OPST, OPIS, OPRN, OPRK, OPBW, OPDG, OPSR, OPMI, VIAR`), knots-to-m/s conversion ($0.514444$), statute-to-meters visibility ($1609.344$) with metric override, present weather token decoding (`FU, HZ, BR, FG, DU, RA, TS`).
   - Lines 221–264: WMO FM-12 SYNOP stream via Ogimet (blocks 415, 416, 417), telegraphic decoding algorithm (`AAXX`, wind indicator $i_w$, group 4 `nddff`, group 3 `00fff`).
   - Lines 268–295: ECMWF IFS via Open-Meteo API (41 district centroids point query + $15\times15$ provincial grid at 10m and 925 hPa; roughness scaling factor $K_R = 0.22686$, fallback default $0.34$).
   - Lines 299–331: NASA FIRMS VIIRS 375m active fires, CSV area query, spatial partitioning across 11 subnational provinces, and industrial gas flaring suppression ($<27.0^\circ\text{N}$ in Rajasthan).
   - Lines 335–358: IQAir regional anchors (Peshawar, Jammu, New Delhi, Bathinda, Jodhpur) and US AQI-to-PEPC recalculation requirement.
   - Lines 362–374: CAMS PM2.5 boundary flux: 117 provincial perimeter nodes vs 39 international border vector nodes (`tbgeo.samples`).
   - Lines 408–440: Mathematical cleaning formulas:
     - 7-hour median spike filter: $v_i > 4 \times \text{median}(W_i)$ AND $v_i > 3 \times \text{ref}_p$.
     - 3-hour logger hold filter: $i \ge 2 \land p \ne \text{'AQI'} \land v_i = v_{i-1} = v_{i-2} \implies v_i = \text{null}$.
     - 75% completeness rule: $N_{\text{valid}} \ge \max(1, \text{round}(0.75 \times N_{\text{period}}))$.
   - Lines 444–458: Station GIS coordinate corrections (Gulberg III, DC Office Sialkot, Wazirabad, Sahiwal, Rajanpur, Talagang, Khushab, Safari Park-LHR; exclusion of OneNetwork Station 25).
   - Lines 462–486: 4-tier meteorological fallback: Tier 1 AQMS ($1.0$) $\to$ Tier 2 METAR within 60 km ($K_R = 0.22686$) $\to$ Tier 3 ECMWF IFS ($K_R = 0.22686$) $\to$ Tier 4 2D Geodesic IDW ($1.0$).

3. **Pipeline Architecture & Persistence (`docs/DATA_PIPELINES_ARCHITECTURE.md`):**
   - Lines 215–296: Pydantic v2 schemas: `RawStationMeasurement` and `NormalizedObservation`.
   - Lines 302–393: Relational DDL for TimescaleDB and PostGIS:
     - `spatial_districts`, `spatial_stations` with GIST spatial indexing.
     - `station_observations` hypertable (30-day chunk interval, LZ4 compression after 14 days, composite PK `(time, station_id)`).
     - `district_hourly_summary` hypertable (14-day chunks, composite PK `(time, district)`).
     - `advection_transport_flux` hypertable (14-day chunks, LZ4 compression, 180-day retention purge).
     - Strict requirement: PostGIS metric queries against SRID 4326 geometry MUST cast to geography: `ST_DWithin(geom::geography, ..., 60000)`.
   - Lines 401–410: Redis caching topology (`paq:latest:overview`, `paq:latest:stations`, `paq:surface:pm25:current`, `paq:surface:wind:current`, `paq:cpf:{district_id}:{pollutant}`, `paq:transboundary:inflow:latest`, `channel:telemetry:hourly`).
   - Lines 453–486: Fault tolerance: AWS Full Jitter backoff, 65s minimum backoff on HTTP 429, dynamic Redis lock with 30s heartbeat renewal, circuit breakers (15m open on 5 consecutive failures), dead-letter queue (`dlq:stream:failures`), and graceful offline degradation.

4. **System Architecture & Code Simplification (`docs/SYSTEM_ARCHITECTURE.md`):**
   - Lines 182–220: Entity separation and PostGIS geography rules.
   - Lines 334–464: OpenAPI 3.1 REST endpoints:
     - `GET /api/v1/meta/districts`
     - `GET /api/v1/observations/hourly` (`start_time`, `end_time`, `pollutant`)
     - `GET /api/v1/spatial/surface` (`timestamp`, `pollutant`, `resolution`)
     - `GET /api/v1/analytics/cpf` (`district_name`, `pollutant`)
   - Lines 467–492: SSE streaming contract: `GET /api/v1/stream/live`, 15s `: keepalive` heartbeat, payload `hourly_update`.
   - Lines 500–515: Elimination of 60+ global variables via modular Zustand stores.
   - Lines 517–586: Unified `SpatialInterpolationService` consolidating triplicated legacy IDW.
   - Lines 590–621: Single `AnimationLoop` using monotonic `performance.now()` clamped delta.

5. **UI/UX Specification (`docs/UI_UX_SPECIFICATION.md`):**
   - Lines 23–55: Five-zone information hierarchy (Command Header, Pollutant Switcher, Map Viewport & Scrubber Deck, Real-Time Sidebar, Deep-Dive Analytics).
   - Lines 122–171: Atmospheric theme tokens (Dark & Light modes), WCAG 2.1 AAA contrast ratios.
   - Lines 174–190: Official PEPC 7-tier continuous color ramp (Tiers 0–6: Good `#00B050`, Satisfactory `#92D050`, Moderate `#FFFF00`, Unhealthy Sensitive `#ED7D31`, Unhealthy `#FF0000`, Very Unhealthy `#7030A0`, Hazardous `#C00000`).
   - Lines 192–215: Typography hierarchy (Barlow Condensed, Source Sans 3, JetBrains Mono with mandatory `tabular-nums`) and 8pt spatial grid ($2, 4, 8, 16, 24, 32, 48\text{px}$).
   - Lines 222–303: Zustand reactive store slices (`Temporal`, `Spatial`, `Pollutant`, `Layer`, `Telemetry`) and sub-hourly continuous lerp engine decoupled from React component tree.
   - Lines 308–397: 5-layer decoupled rendering architecture:
     - Layer 0: Static Vector Basemap (Path2D TopoJSON).
     - Layer 1: Continuous Field Rasterizer (WebGL 2.0 fragment shader $<0.4\text{ ms}$ or downsampled $150\times175$ offscreen canvas $<2.2\text{ ms}$).
     - Layer 2: Dual Wind Particle Advection Engine (1,300 particles, pre-allocated `Float32Array` ring buffer, zero GC).
     - Layer 3: Dynamic Transport Vector Overlay (top 60 links, quadratic Bezier, 39 border chevrons).
     - Layer 4: Station Glyphs & Greedy AABB Collision-Free Labeling.
     - Dynamic 16-Sector CPF Polar Rose ($22.5^\circ$ sectors, $N_k \ge 6$ cutoff, $0.25$ null circle).
   - Lines 402–446: Responsive breakpoints (>980px desktop, 560–980px tablet, <560px mobile) and WCAG 2.1 AAA accessibility (ARIA live regions, focus rings, canvas fallback DOM tree, colorblind glyphs).

6. **Existing Workspace Artifacts (`index.html`, `collector/collector.py`):**
   - `collector/collector.py`:
     - Line 25–38: Authoritative `PMAP` dictionary mapping portal IDs (`10` to `186`) to network station names.
     - Line 41–51: Authoritative `DIST` dictionary of 41 district names and centroid coordinates `[lat, lon]`.
     - Line 53–56: `ICAO` array of 12 airport codes and `WMO` dictionary of 7 synoptic observatories.
     - Line 57: `POLF` array: `['aqi', 'pm25', 'pm10', 'no2', 'so2', 'co', 'o3']`.
     - Line 209: Fallback station resolution `PMAP.get(str(r.get('station_id'))) or NAME_FALLBACK.get(r.get('station_name'))`.
   - `index.html`:
     - Contains embedded `window.DATA` covering 216 historical hours across all 41 districts and stations. Serves as baseline data template for offline running and test assertions.

---

## 2. Logic Chain

1. **Premise:** The user request (R1–R6) requires building a modular, decoupled, clean-architecture Punjab Air Quality monitoring, processing, and visualization system supporting both live external streams and custom user datasets.
2. **Step 1 (Ingestion & Pipelines):** The 7 external data streams defined in `docs/DATA_SOURCES_AND_STREAMS.md` have distinct endpoints, cadences, and failure modes. Under clean architecture, each stream must be encapsulated in an independent Ingestion Worker implementing a common Ingestion Interface, with Pydantic validation enforcing physical plausibility and standard SI units.
3. **Step 2 (Baseline & Template Fallback):** When live external endpoints are unreachable or in development/offline mode, the system cannot stall. The station metadata (`PMAP`, `DIST`, `ICAO`, `WMO`) and 216-hour historical records extracted from `collector.py` and `index.html` provide the exact schema-conforming fallback template to seed the database and drive tests.
4. **Step 3 (User Dataset & CSV Ingestion):** To fulfill R2 and Acceptance Criteria, a dedicated CSV Ingestion Adapter must accept user-supplied observations, validate against the Pydantic schema, apply canonical coordinate correction, route malformed records to a Dead-Letter Queue (DLQ), and feed valid rows into the harmonization engine.
5. **Step 4 (Quality Control & Harmonization):** Environmental sensors generate zero-glitches, stuck values, and spike surges. The 5 QC filters (Step 0 zero-purge, 7h median spike filter, 3h logger hold filter, anemometer sanity bounds, Wazirabad blacklist, and 75% completeness rule) must execute as pure, decoupled domain functions before persistence.
6. **Step 5 (Clean Backend Architecture):** The system must separate Core Domain Entities (`Station`, `Observation`, `DistrictSummary`, `TransportFlux`) from Repository Interfaces (`StationRepository`, `ObservationRepository`, `SummaryRepository`), Application Services (`IngestionService`, `SpatialInterpolationService`, `AnalyticsService`, `StreamService`), and Presentation Gateways (FastAPI REST & SSE).
7. **Step 6 (Persistence Strategy):** High-frequency time-series observations require partition chunking (TimescaleDB 30-day hypertables) and delta compression, spatial queries require PostGIS geography casts to avoid degree-meter calculation bugs, and real-time reads require Redis in-memory caching with sub-10ms response times.
8. **Step 7 (UI/UX Real-Time Console):** The frontend requires a mission-critical console architecture: Zustand store slices isolating temporal scrubbing from React re-renders, a 60 FPS multi-layer rendering pipeline (Path2D basemap, WebGL/downsampled IDW $<3\text{ ms}$, 1,300-particle typed ring buffer, quadratic Bezier flux curves), PEPC 7-tier continuous color ramps, virtualized tables, and WCAG 2.1 AAA accessibility.
9. **Conclusion:** All architectural, schema, API, and UI components are fully specified across the documentation suite and can be deterministically implemented in accordance with Clean Architecture principles.

---

## 3. Caveats

1. **Live External Endpoint Accessibility:** Public government portals (`aqi.punjab.gov.pk`, `ogimet.com`) may intermittently throttle, geoblock, or experience downtime. The architecture explicitly mandates fallback to embedded baseline templates and cached NWP data when endpoints are unreachable.
2. **API Keys for Secondary Feeds:** NASA FIRMS requires an Earthdata `MAP_KEY`, and IQAir requires an AirVisual API key. When API keys are not supplied in the environment, the system gracefully falls back to synthetic or baseline data without breaking core provincial monitoring.
3. **Database Driver Prerequisites:** In local environments without live PostgreSQL/TimescaleDB/Redis daemons running, the clean architecture repository interfaces must support lightweight in-memory / SQLite / file-backed fallback adapters so unit and integration test suites execute deterministically without external infrastructure dependencies.

---

## 4. Features Discovered

| # | Category | Feature | Description | Inputs | Outputs | Error Behavior | Discovered Via |
|---|----------|---------|-------------|--------|---------|----------------|----------------|
| 1 | Ingestion | STR-01 EPA Punjab Worker | Queries provincial AQMS portal for live station measurements | HTTP GET `/api/dashboard/current`, User-Agent header | Raw JSON station measurements | 3 retries (2s, 8s, 20s), short-circuit fallback, circuit breaker 15m | `DATA_SOURCES_AND_STREAMS.md` §3.1 |
| 2 | Ingestion | EPA District Fallback Fan-Out | Asynchronous query for missing districts | HTTP GET `/api/district-stations/{name}` | Supplementary station array | `asyncio.Semaphore(10)`, 3s timeout, abort after 3 timeouts | `DATA_PIPELINES_ARCHITECTURE.md` §3.1 |
| 3 | Ingestion | STR-02 NOAA METAR Worker | Parses aerodrome meteorology from 12 regional airports | ICAO codes, HTTP GET `/api/data/metar` | Normalized wind (m/s), visibility (m), wx tokens | Selects report in $[-35\text{m}, +25\text{m}]$, falls to ECMWF | `DATA_SOURCES_AND_STREAMS.md` §3.2 |
| 4 | Ingestion | STR-03 WMO SYNOP Decoder | Decodes FM-12 AAXX synoptic telegraphic bulletins | WMO Blocks 415, 416, 417, HTTP GET Ogimet | Station wind speed (m/s) and azimuth (deg) | Sequential querying, 65s HTTP 429 backoff floor | `DATA_SOURCES_AND_STREAMS.md` §3.3 |
| 5 | Ingestion | STR-04 ECMWF IFS Worker | Queries Open-Meteo for 41 district centroids and 15x15 provincial grid | Lat/Lon coordinate arrays, 10m and 925 hPa | Cartesian $(u, v)$ vectors, roughness scaled | 60s timeout, fallback to cached 24h cycle or IDW | `DATA_SOURCES_AND_STREAMS.md` §3.4 |
| 6 | Ingestion | STR-05 NASA FIRMS Worker | Ingests VIIRS 375m active fire detections | Bounding box CSV, NASA Map Key | Geo-partitioned fire counts, FRP sums | Retains previous day's counts on network failure | `DATA_SOURCES_AND_STREAMS.md` §3.5 |
| 7 | Ingestion | STR-06 IQAir Worker | Cross-border regional baseline monitoring | City queries (Peshawar, Jammu, Delhi, etc.) | Raw concentrations, recalculated PEPC sub-index | HTTP 429 circuit breaker 60m, suppress cards | `DATA_SOURCES_AND_STREAMS.md` §3.6 |
| 8 | Ingestion | STR-07 CAMS Boundary Flux | Daily transboundary PM2.5 boundary mass flux | NetCDF/ADS API, 117 perimeter nodes | Boundary normal flux $\Phi_j(t)$ | Interpolates previous cycle on missing run | `DATA_SOURCES_AND_STREAMS.md` §3.7 |
| 9 | Fallback | Station Metadata & Baseline Template | Extracts baseline registry and historical hours from legacy artifacts | `PMAP`, `DIST`, `ICAO`, `WMO` from `collector.py`; `window.DATA` | Seeded database documents & template fallbacks | Validates schema conformance before seeding | `collector.py` & `ORIGINAL_REQUEST.md` R2 |
| 10 | Fallback | 4-Tier Meteorological Fallback | Priority resolution for district wind vectors | District ID, timestamp, radius 60 km | Calibrated wind vector $(u, v, w_s, w_d)$ and source tag | Tier 1 AQMS $\to$ Tier 2 METAR $\to$ Tier 3 ECMWF $\to$ Tier 4 IDW $\to$ NULL | `DATA_SOURCES_AND_STREAMS.md` §6 |
| 11 | CSV Adapter | User Dataset CSV Ingestion | Ingests and validates custom user CSV datasets | CSV file path or byte stream | Batch validation result, parsed entities, DLQ errors | Emits row-level validation errors, reject/quarantine | `ORIGINAL_REQUEST.md` R2 / Acceptance Criteria |
| 12 | QC Engine | Step 0 Zero & Negative Suppression | Discards impossible zero or negative chemical readings | Raw value $v$ | Valid positive float or `null` | Discards $v \le 0$ as `ZERO_OR_RANGE` | `DATA_SOURCES_AND_STREAMS.md` §4.1 |
| 13 | QC Engine | Extreme Exceedance Tagging | Preserves extreme episodic smog crisis peaks | $\text{PM}_{2.5} > 1000.0$, $\text{PM}_{10} > 1500.0$ | Admitted float with `QC_EXCEEDANCE_EXTREME` | Not dropped to DLQ; marked for auditing | `ARCHITECTURE_OVERVIEW.md` §3.1 |
| 14 | QC Engine | 7-Hour Median Spike Filter | Rejects single-hour electrical or hardware surge spikes | 7-hour sliding window $W_i$, PEQS reference limits | Valid float or `null` | Discards if $v_i > 4M \land v_i > 3\text{ref}_p$ | `DATA_SOURCES_AND_STREAMS.md` §4.2 |
| 15 | QC Engine | 3-Hour Logger Hold Purge | Detects frozen datalogger registers | Sequential 3-hour readings, index guard $i \ge 2$ | Valid float or `null` | Discards if $v_i = v_{i-1} = v_{i-2}$ (exempts integer AQI) | `DATA_SOURCES_AND_STREAMS.md` §4.3 |
| 16 | QC Engine | Anemometer Sanity & Vane Blacklist | Validates physical wind bounds and purges misaligned vanes | $w_s \in [0, 30]\text{ m/s}$, $w_d \in [0, 360^\circ]$, station name | Cleaned wind or `null` | Wazirabad purged unconditionally ($140^\circ$ offset) | `DATA_SOURCES_AND_STREAMS.md` §4.4 |
| 17 | QC Engine | 75% Completeness Rule | Determines validity of multi-hour or 24-hour averages | Array of hourly measurements | Arithmetic mean or `null` | Requires $N_{\text{valid}} \ge \max(1, \text{round}(0.75 \times N))$ | `DATA_SOURCES_AND_STREAMS.md` §4.5 |
| 18 | QC Engine | Continuous PEPC Breakpoints | Piecewise linear AQI interpolation without gaps | Pollutant concentration $C_p$, breakpoint matrix | Integer PEPC AQI $(0–500+)$ | Clamps to 500 when $\text{PM}_{2.5} > 350.0\ \mu\text{g/m}^3$ | `DATA_SOURCES_AND_STREAMS.md` §4.6 |
| 19 | QC Engine | Station Coordinate Correction | Canonical lookup resolving corrupted registry GPS | Station name, district | Corrected (lat, lon) in WGS84 | Excludes OneNetwork Station 25 | `DATA_SOURCES_AND_STREAMS.md` §5 |
| 20 | Domain | Clean Architecture Domain Entities | Isolated core models independent of frameworks | Domain attributes | Validated immutable entities | Domain validation exceptions | `SYSTEM_ARCHITECTURE.md` §2, §3 |
| 21 | Persistence | TimescaleDB Hypertables | Partitioned time-series tables with LZ4 compression | Time, station_id, pollutant metrics | Hypertable records, continuous aggregates | Handled by SQL constraints, upsert conflicts | `DATA_PIPELINES_ARCHITECTURE.md` §5 |
| 22 | Persistence | PostGIS Spatial Tables | Spatial reference tables for districts and stations | Geometry points/multipolygons (SRID 4326) | Spatial entities, proximity queries | Mandatory `::geography` cast for metric distance | `SYSTEM_ARCHITECTURE.md` §4.1 |
| 23 | Persistence | Redis Caching Topology | Low-latency in-memory cache for state and binary surfaces | Keys (`paq:slice:*`, `paq:surface:*`, etc.) | JSON snapshots, Float32 binary buffers | Cache-aside transparent database fallback | `SYSTEM_ARCHITECTURE.md` §4.3 |
| 24 | API | OpenAPI 3.1 REST Metadata | Endpoints for district and station metadata | HTTP GET `/api/v1/meta/districts`, `/meta/stations` | TopoJSON boundaries, station GeoJSON | HTTP 404 / 500 standardized JSON | `SYSTEM_ARCHITECTURE.md` §5.1.1 |
| 25 | API | OpenAPI 3.1 Hourly Observations | Queries historical district/station observations | `start_time`, `end_time`, `pollutant` | Continuous hourly time-series array | HTTP 400 on invalid format or date range | `SYSTEM_ARCHITECTURE.md` §5.1.2 |
| 26 | API | OpenAPI 3.1 Spatial Surface | Serves precomputed continuous pollution raster | `timestamp`, `pollutant`, `resolution` | 2D normalized grid matrix, min/max values | Returns empty/interpolated on missing hour | `SYSTEM_ARCHITECTURE.md` §5.1.3 |
| 27 | API | OpenAPI 3.1 CPF Analytics | Serves 16-sector CPF wind rose analysis | `district_name`, `pollutant` | Sector azimuths, probabilities, $P_{75}$ threshold | Sectors with $N_k < 6$ returned as `null` | `SYSTEM_ARCHITECTURE.md` §5.1.4 |
| 28 | API | SSE Real-Time Streaming | Pushes hourly delta packets to connected clients | HTTP GET `/api/v1/stream/live` | `text/event-stream`, 15s keepalive, delta payload | Client reconnection with backoff | `SYSTEM_ARCHITECTURE.md` §5.2 |
| 29 | UI/UX | 5-Zone Information Architecture | Clear cognitive hierarchy for mission-critical monitoring | System state, active pollutant, timestamp | Responsive dashboard layout | Graceful layout reflow across breakpoints | `UI_UX_SPECIFICATION.md` §2 |
| 30 | UI/UX | 9-Pollutant Persistent Switcher | Instant switching between statutory pollutants | Active pollutant selection | Updates map, charts, and tables synchronously | Preserves current temporal playback position | `UI_UX_SPECIFICATION.md` §2.2 |
| 31 | UI/UX | 5-Layer Stacked Map Engine | Decoupled canvas/WebGL rendering pipeline | Map layers (0: Basemap, 1: IDW, 2: Wind, 3: Flux, 4: Stations) | 60 FPS composite visual output | Layer-specific fallbacks (WebGL $\to$ downsampled) | `UI_UX_SPECIFICATION.md` §5 |
| 32 | UI/UX | GPU / Downsampled IDW Rasterizer | Fast wind-steered continuous raster field | Station coordinates, concentrations, wind $(u, v)$ | Continuous color field in $<3\text{ ms}$ | Downsampled $150\times175$ canvas bilinear fallback | `UI_UX_SPECIFICATION.md` §5.2 |
| 33 | UI/UX | Dual Wind Particle Engine | Particle advection for local (700) and regional (600) winds | Station and ECMWF wind flowfields | 1,300 animating particle streaks | Pre-allocated `Float32Array` ring buffer, zero GC | `UI_UX_SPECIFICATION.md` §5.3 |
| 34 | UI/UX | Dynamic Transport Vector Overlay | Quadratic Bezier flux curves and 39 border chevrons | Inter-district flux scores, border normals | Animated arrows, colored inflow/outflow chevrons | Truncated to top 60 links; disabled for AQI | `UI_UX_SPECIFICATION.md` §5.4 |
| 35 | UI/UX | Sub-Hourly Continuous Lerp Engine | Smooth scrubber navigation across 216+ hours | Scrubber position `fpos` $(0.00–215.00)$ | Interpolated concentrations and wind vectors | Reads via refs/Zustand transient subscriptions | `UI_UX_SPECIFICATION.md` §4.1 |
| 36 | UI/UX | 16-Sector CPF Polar Rose View | Displays directional upwind source enrichment | Selected district hourly observations, $P_{75}$ | Polar wedge canvas with $0.25$ baseline circle | Sectors with $N_k < 6$ rendered as neutral stubs | `UI_UX_SPECIFICATION.md` §5.6 |
| 37 | UI/UX | Virtualized Hourly Heatmap Matrix | High-performance 41 districts $\times$ 216 hours matrix | District time-series data, active tab | Virtualized scrolling table with sticky headers | Column cursor highlights active simulation hour | `UI_UX_SPECIFICATION.md` §2.5, §7 |
| 38 | UI/UX | Lahore Inset Network Focus | Hyper-local 11-station fixed and mobile AQMS focus | Lahore station array, Wagha border coordinates | Detailed inset map and station table | Highlights active mobile monitoring units | `UI_UX_SPECIFICATION.md` §2.5, §7 |
| 39 | UI/UX | Design Tokens & WCAG 2.1 AAA Palette | Dark/light themes, 8pt grid, PEPC color ramps | CSS variables, typography classes | High-contrast, accessible UI controls | Contrast ratio $\ge 7:1$, ARIA live announcements | `UI_UX_SPECIFICATION.md` §3 |
| 40 | UI/UX | Zustand Modular State Store | Decoupled state management across 5 domain slices | Actions (setTime, selectDistrict, setPollutant, etc.) | Reactive state subscribers | Eliminates 60+ legacy global variables | `UI_UX_SPECIFICATION.md` §4 |

---

## 5. Edge Cases

| # | Feature | Input / Condition | Observed / Mandated Behavior |
|---|---------|-------------------|-----------------------------|
| 1 | Step 0 QC | Raw sensor reading $\le 0.0$ or non-numeric (`NaN`) | Immediately nullified (`v = null`) with flag `ZERO_OR_RANGE` prior to statistical filters. |
| 2 | Extreme Smog | Genuine crisis peak: $\text{PM}_{2.5} > 1000.0\ \mu\text{g/m}^3$ (up to $5000.0$) | Admitted to database; tagged with `QC_EXCEEDANCE_EXTREME`; never dropped to DLQ. |
| 3 | Spike Filter | Isolated surge: $v_i > 4 \times M$ and $v_i > 3 \times \text{ref}_p$ ($W_i$ has $\ge 3$ points) | Discarded as hardware spike (`v = null`) with flag `SPIKE_7H`. |
| 4 | Spike Filter | Sparse window: Fewer than 3 valid samples in 7-hour window $W_i$ | Window median $M$ cannot be computed; spike filter is bypassed to avoid false drops. |
| 5 | Hold Filter | Consecutive readings $v_i = v_{i-1} = v_{i-2}$ with $i \ge 2$ on chemical pollutant | Sensor freeze detected; $v_i$ set to `null` with flag `HOLD_3H`. |
| 6 | Hold Filter | Consecutive readings on composite integer `AQI` | Exempt from hold filter: legitimate steady index value is preserved. |
| 7 | Hold Filter | Window check at array head ($i=0$ or $i=1$) | Index boundary guard $i \ge 2$ prevents negative array index wraparound bugs. |
| 8 | Anemometer QC | Wind speed $< 0.0$ or $> 30.0\text{ m/s}$ (e.g. Chakwal azimuth in speed register) | Discarded as hardware fault (`ws = null`, `wd = null`) with flag `SPEED_ERR`. |
| 9 | Anemometer QC | Aerodynamic calm wind: $w_s < 0.5\text{ m/s}$ (~1 knot) | Speed set to $0.0\text{ m/s}$, classified `CALM`, excluded from directional transport. |
| 10 | Vane Blacklist | Any wind measurement originating from Wazirabad AQMS site | Unconditionally purged (`NOWIND = {'Wazirabad'}`) due to physical $140^\circ$ vane offset. |
| 11 | Fallback Chain | Station anemometer offline, nearest METAR airport within 60 km active | Tier 2 METAR wind substituted, calibrated by roughness factor $K_R = 0.22686$. |
| 12 | Fallback Chain | Station and airport offline, ECMWF IFS model wind available | Tier 3 ECMWF model wind substituted, calibrated by $K_R = 0.22686$. |
| 13 | Fallback Chain | All station, airport, and model feeds offline | Tier 4 2D Geodesic IDW imputer estimates vector; if $<3$ points, returns `[null, null]`. |
| 14 | PostGIS Query | Distance radius search on SRID 4326 geometries (e.g. airport 60 km) | Must cast to `::geography` (`ST_DWithin(geom::geography, ..., 60000)`). Degrees eval fails. |
| 15 | Rate Limiting | External API returns HTTP 429 without `Retry-After` header | Enforces minimum backoff floor of $65\text{ seconds}$ to prevent 24h IP firewall bans. |
| 16 | Fallback Fan-Out| Primary EPA dashboard returns partial district roster (<40 stations) | Fan-out queries districts via `Semaphore(10)` with 3s timeout; aborts on 3 consecutive timeouts. |
| 17 | Corrupted GPS | Sahiwal registry coordinates `(0.0000, 0.0000)` or Gulberg III inverted | Corrected via canonical GIS lookup table (`(30.6682, 73.1114)` for Sahiwal). |
| 18 | Unlocatable Site| OneNetwork Station 25 in EPA directory without physical coordinates | Excluded unconditionally from provincial spatial surfaces and maps. |
| 19 | Gas Flaring | Active thermal detection in Rajasthan with latitude $< 27.0^\circ\text{N}$ and persistent FRP | Classified as industrial petrochemical flaring; suppressed from agricultural fire counts. |
| 20 | CPF Small-Sample| Wind rose sector $k$ with total observations $N_k < 6$ | CPF probability assigned `null`; rendered as neutral stub to prevent false 100% spikes. |
| 21 | CPF Multi-Station| District with multiple stations (e.g. Lahore with 13 stations) | $P_{75}$ threshold and sector counts calculated across pooled station-hour basis ($N \approx 2,700$). |
| 22 | Advection Flux | Active pollutant set to dimensionless composite `AQI` | Advection flux is strictly disabled (active only for physical mass concentrations $\mu\text{g/m}^3$). |
| 23 | Advection Flux | Pathway count across 41 districts exceeds visual/CPU budget | Truncated to the top 60 links by composite score (`slice(0, 60)`). |
| 24 | Border Vectors | Distinction between border animation chevrons and provincial balance | 39 nodes (`tbgeo.samples` at $\sim 25\text{ km}$ on Indo-Pak border) vs 117 perimeter nodes encircling province. |
| 25 | PEPC Breakpoint | PM2.5 concentration falling in boundary interval $(15.0, 15.1)$ | Continuous half-open bracket $(BP_{i-1}, BP_i]$ ensures seamless sub-index evaluation. |
| 26 | PEPC Capping | PM2.5 concentration exceeds $350.0\ \mu\text{g/m}^3$ | PEPC AQI is operationally capped at 500 matching EPA Punjab portal practice. |
| 27 | Client Lerp | Rapid timeline scrubbing at 60 FPS in React 19 Concurrent Mode | Frame loop reads `fpos` via mutable refs/transient subscriptions; UI consumes immutable snapshots. |
| 28 | Client Particles| Dynamic array manipulation (`push`/`shift`) for 1,300 particle trails | Flat pre-allocated `Float32Array` ring buffer eliminates 78,000 allocations/sec and GC stutter. |
| 29 | GPU Context | Mobile browser runs out of WebGL contexts on 3x3 comparison grid | Clamps DPR to 1.5; inactive grid cells render as static PNGs, releasing WebGL contexts. |
| 30 | Offline System | Severed internet connectivity or external APIs completely down | Serves cached state; after 24h mounts embedded 216h baseline template (`window.DATA`). |

---

## 6. Technical Stack & Clean Architecture Alignment

To deliver the specified system with high maintainability, testability, and decoupled concerns, the implementation stack should be aligned as follows:

```
+---------------------------------------------------------------------------------------------------+
| CLEAN ARCHITECTURE LAYERING                                                                       |
+---------------------------------------------------------------------------------------------------+
| 1. DOMAIN LAYER (Innermost - Zero External Dependencies)                                          |
|    - Entities: Station, Observation, DistrictSummary, TransportFlux, ActiveFire, CAMSNode         |
|    - Value Objects: Coordinates, PollutantConcentration, WindVector, PEPCBreakpoints              |
|    - Pure Domain Functions: 7h median filter, 3h hold filter, PEPC index math, IDW formula        |
+---------------------------------------------------------------------------------------------------+
| 2. USE CASES / APPLICATION SERVICES LAYER                                                         |
|    - IngestionUseCase: orchestrates stream ingestion, validation, and harmonization               |
|    - CsvIngestionUseCase: parses and validates user-supplied CSV files into domain entities       |
|    - SpatialInterpolationUseCase: computes unmonitored district values and continuous grids       |
|    - AnalyticsUseCase: computes 16-sector CPF wind roses, advection flux, and border balances     |
|    - TelemetryQueryUseCase: retrieves historical slices and summary metrics                       |
+---------------------------------------------------------------------------------------------------+
| 3. INTERFACES / ADAPTERS LAYER                                                                    |
|    - Ingestion Gateway Adapters: EpapunjabAdapter, MetarAdapter, SynopAdapter, EcmwfAdapter, etc. |
|    - Storage Repository Interfaces: StationRepository, ObservationRepository, FluxRepository    |
|    - Cache Adapter Interface: CacheRepository (Redis with in-memory fallback)                     |
|    - Presentation Controllers: FastAPI REST routers, SSE Streaming handler                        |
+---------------------------------------------------------------------------------------------------+
| 4. INFRASTRUCTURE & FRAMEWORKS LAYER (Outermost)                                                  |
|    - Database: TimescaleDB / PostgreSQL 16 + PostGIS 3.4 (with in-memory/SQLite mock for tests)   |
|    - HTTP Client: Async httpx with connection pooling and full-jitter retry policies             |
|    - Schema Validation: Pydantic v2                                                               |
|    - Frontend: React 19 + TypeScript + Zustand + HTML5 Canvas 2D / WebGL 2.0                      |
+---------------------------------------------------------------------------------------------------+
```

---

## 7. User CSV Ingestion Specification

To satisfy Requirement R2 and the Acceptance Criteria for user-provided CSV datasets:

1. **Required & Optional CSV Columns:**
   - `station_id` (string, required): Unique identifier.
   - `station_name` (string, required): Station display name.
   - `district` (string, required): Administrative district in Punjab.
   - `timestamp` (ISO-8601 string, required): UTC observation time.
   - `latitude` (float, optional if in station registry, $27.0 \le \text{lat} \le 35.0$).
   - `longitude` (float, optional if in station registry, $69.0 \le \text{lon} \le 76.0$).
   - `pm25` (float, optional, $\mu\text{g/m}^3$, $0.1 \le v \le 5000.0$).
   - `pm10` (float, optional, $\mu\text{g/m}^3$, $0.1 \le v \le 5000.0$).
   - `no2` (float, optional, $\mu\text{g/m}^3$, $0.1 \le v \le 500.0$).
   - `so2` (float, optional, $\mu\text{g/m}^3$, $0.1 \le v \le 500.0$).
   - `co` (float, optional, $\text{mg/m}^3$, $0.01 \le v \le 50.0$).
   - `o3` (float, optional, $\mu\text{g/m}^3$, $0.1 \le v \le 400.0$).
   - `wind_speed` (float, optional, $\text{m/s}$, $0.0 \le v \le 30.0$).
   - `wind_direction` (float, optional, degrees, $0.0 \le v \le 360.0$).
   - `pollutant_flags` (string, optional).

2. **Validation & Processing Rules:**
   - Empty or negative values parsed as `null`.
   - Timestamps without timezone converted from PKT (`Asia/Karachi`) to UTC.
   - Coordinates checked against Punjab bounding box; known station registry overrides applied if coordinates missing.
   - Records pass through Step 0 sanitization, spike filter, hold filter, and anemometer sanity checks.
   - Malformed rows recorded in Dead-Letter validation report without halting valid rows.

---

## 8. Conclusion

All specifications required for the architecture, data ingestion pipelines, fallback templates, CSV validation interfaces, clean domain models, persistence schemas, REST/SSE APIs, and UI/UX dashboard components have been extracted and documented. The findings directly support immediate, robust implementation without ambiguity.

---

## 9. Verification Method

To independently verify these findings:
1. **Spec Inspection:** Review the direct references in `docs/ARCHITECTURE_OVERVIEW.md`, `docs/DATA_SOURCES_AND_STREAMS.md`, `docs/DATA_PIPELINES_ARCHITECTURE.md`, `docs/SYSTEM_ARCHITECTURE.md`, and `docs/UI_UX_SPECIFICATION.md`.
2. **Artifact Verification:** Inspect `collector/collector.py` lines 25–57 to verify station mapping dictionaries (`PMAP`, `DIST`, `ICAO`, `WMO`), and `index.html` lines 200–230 to confirm historical data keys.
3. **Automated Test Coverage:** Downstream test runners (`pytest`, `npm test`) will assert that:
   - Ingestion workers and CSV adapters validate payloads against the Pydantic schemas.
   - The 5 QC filters correctly sanitize edge cases (zero suppression, spikes, holds, anemometer bounds, Wazirabad purge).
   - API endpoints conform strictly to OpenAPI 3.1 schemas and SSE streaming formats.
   - UI components mount and respond to state changes according to the component hierarchy.
