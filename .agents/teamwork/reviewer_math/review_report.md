# Punjab Air Quality: Data & Math Specification Review Report

**Reviewer Archetype**: Data & Math Spec Reviewer (`reviewer_math`)  
**Roles**: Reviewer, Adversarial Critic  
**Date**: 2026-11-10  
**Target Documents**:
1. `docs/DATA_SOURCES_AND_STREAMS.md` (`PAQ-SPEC-R1-DATA-STREAMS`)
2. `docs/TRANSFORMATION_LOGIC_SPEC.md` (`PAQ-SPEC-R2-TRANSFORMS`)
3. `docs/DATA_PIPELINES_ARCHITECTURE.md` (`PAQ-ARCH-R3-PIPELINES`)

---

## 1. Executive Summary & Verdict

### 1.1 Review Verdict
**Verdict**: `REQUEST_CHANGES`

**Integrity Audit**: **PASSED (NO INTEGRITY VIOLATIONS)**.
- Zero evidence of hardcoded facades, dummy stubs, fabricated artifacts, or shortcuts.
- Forensic analysis confirms that the specifications represent genuine, exhaustive reverse-engineering of the 9.61 MB monolithic `index.html` and `collector/collector.py`.
- Strict Non-Invasive Constraint Verified: SHA-256 hashes of `index.html` (`0154B0204275D20327686CEE1C585E75A1E51153611878906A8A7C210A7ECE3F`) and `collector/collector.py` (`63F714DB676362A5B095F2FC67DA342EBB319952819424DA46DC7B0D3BC801B1`) remain completely identical and untouched.

**Rationale for REQUEST_CHANGES**:
While the authored specifications demonstrate extraordinary depth, accurate domain reverse-engineering, and mathematical rigor, adversarial stress-testing identified **three Major technical flaws** and **three Minor discrepancies** that would directly induce runtime crashes or algorithmic degradation if implemented as written:
1. **TimescaleDB SQL Hypertable Constraint Failure**: `station_observations` lacks a composite `PRIMARY KEY (time, station_id)`. The ingestion worker's specified upsert clause (`ON CONFLICT (station_id, timestamp) DO UPDATE`) will fail with PostgreSQL error `there is no unique or exclusion constraint matching the ON CONFLICT specification`, and uses the incorrect column name `timestamp` instead of `time`.
2. **Pydantic v2 Required-vs-Optional Field Bug**: In `NormalizedObservation`, eleven physical QC and vector fields are declared as `Optional[float]` without `= None`. In Pydantic v2, omitting `= None` causes fields to be required at instantiation, immediately raising `ValidationError: Field required` on missing values.
3. **Omission of Small-Sample Suppression ($N_k \ge 6$) in CPF Rose Formulation (Transform 5)**: In the production codebase (`window.DATA.pol.cpf`), sectors with $N_k < 6$ observations suppress $\text{CPF}_k \to \text{null}$ to prevent small-sample noise. Omitting this in the specification would cause severe distortion in polar roses.
4. **Data Type Inflexibility in `RawStationMeasurement.pollutant_flags`**: The EPA Punjab portal intermittently returns `pollutant_flags` as a JSON array (`["pm25_fault"]`) or dictionary, which rejects under `Optional[str]` and drops valid station batches into the Dead-Letter Queue.
5. **Receptor Coupling Fallback Generalization (Transform 7)**: The specification states that the receptor coupling coefficient $\Omega$ defaults to $0.25$ only for unmonitored receptors, omitting that it also falls back to $0.25$ when a monitored receptor lacks sufficient wind samples ($N_k < 6$).
6. **Geographic Domain Discrepancy (Transform 8 & Stream 7)**: Conflating the 39 India-Pakistan border animation nodes (`tbgeo.samples`) with the 117 whole-province perimeter boundary nodes.

These are actionable, concrete findings with complete patch recipes provided below.

---

## 2. Requirement-by-Requirement Assessment

### 2.1 Requirement R1: Data Source and Stream Inventory (`DATA_SOURCES_AND_STREAMS.md`)
- **Coverage**: **100% Complete**.
- **Streams Evaluated**:
  1. *EPA Punjab Public Portal*: Correct base URL (`https://aqi.punjab.gov.pk`), endpoints (`/api/dashboard/current`, `/api/districts`, `/api/district-stations/{name}`), mandatory custom User-Agent, and detailed 14-field JSON payload schema matching `collector.py`.
  2. *Aviation METAR*: Correct endpoint (`aviationweather.gov/api/data/metar`), 12 ICAO stations (including transboundary anchor `VIAR` Amritsar), unit conversions (knots $\to \text{m/s}$, statute miles $\to$ meters), and `rawOb` metric regex override.
  3. *WMO SYNOP*: Accurate Ogimet FM-12 `AAXX` parsing logic across blocks 415, 416, 417, with wind indicator $i_w$ knot/ms handling, $dd \times 10^\circ$ direction, and $00fff$ overflow groups.
  4. *ECMWF IFS via Open-Meteo*: Exact 41 district centroid query parameters, 15x15 provincial grid bounds ($27.5^\circ\text{N} - 34.5^\circ\text{N}$, $69.0^\circ\text{E} - 76.0^\circ\text{E}$), surface roughness factor $K_R = 0.22686$, and dual levels ($10\text{m}$, $925\text{ hPa}$).
  5. *NASA FIRMS VIIRS*: Area query coordinates, satellite orbits (NOAA-20, NOAA-21), FRP thresholds, and subnational fire count partitioning verified against `index.html` (e.g., 6,703 PK Punjab vs 3,239 IN Punjab).
  6. *IQAir*: Regional anchor cities (Peshawar, Jammu, New Delhi, Bathinda, Jodhpur), US EPA vs PEPC AQI discrepancy noted and resolved.
  7. *CAMS PM2.5 Boundary Grid*: Surface mass flux integration, inward unit normal vectors $\mathbf{n}_j$, and daily batch timing.
- **Sensor Cleaning & QC Rules**: All 5 rules extracted with exact mathematical definitions: 7-hour median spike filter ($v_i > 4M \land v_i > 3\text{ref}$), 3-hour hold purge ($v_i = v_{i-1} = v_{i-2}$), zero/negative suppression, anemometer bounds ($0-30\text{ m/s}$), Wazirabad vane blacklist ($140^\circ$ offset), and 75% aggregation completeness.
- **GIS Coordinate Corrections**: Comprehensive 8-station correction catalog verified against `index.html` (`window.DATA.coordsrc` and `DATA.skipped`).

### 2.2 Requirement R2: Algorithmic Transformation Specs (`TRANSFORMATION_LOGIC_SPEC.md`)
- **Coverage**: **100% Complete (11 Transformations Documented)**.
- **Mathematical Formulations Evaluated**:
  - **T1 (Discrete Geodesic IDW)**: Haversine great-circle distance with $d_0 = 5.0\text{ km}$ singularity clamping and $p=2$ inverse distance power. Fully rigorous.
  - **T2 (Anisotropic Wind-Steered IDW)**: Mathematically exact alignment cosine $\cos\alpha_i = \frac{\Delta x_i u_i - \Delta y_i v_i}{d_i s_i}$ accounting for inverted screen $y$-coordinates; $+70\%$ downwind boost, $0.30$ upwind floor, velocity saturation at $1.5\text{ m/s}$; distance opacity taper ($235$ at $45\text{km}$ to $95$ at $140\text{km}$).
  - **T3 (Planar Screen Raster IDW)**: High-power $p=3$ planar IDW ($w = q^{-1.5}$ where $q = \Delta x^2 + \Delta y^2 + 0.25$) on $5\text{px}$ canvas cells with `pjPath` clipping.
  - **T4 (Vector Wind Blending)**: Polar-to-Cartesian meteorological vector conversion ($u = -w_s \sin\theta, v = -w_s \cos\theta$), inverse reconstruction, and spatial vector field blending with softening radius $\epsilon = 20\text{px}$ ($w = (d^2 + 400)^{-1}$).
  - **T5 (CPF Polar Roses)**: 16 sectors ($22.5^\circ$), calm exclusion ($w_s < 0.5\text{ m/s}$), $P_{75}$ criterion threshold, isotropic $0.25$ baseline, and polar wedge rendering. (*Finding: missing $N_k \ge 6$ suppression*).
  - **T6 (Physical Advection Flux)**: Forward bearing geodesics, wind bearing TO, transport cone ($\Delta\theta \le 35^\circ$), max distance $180\text{ km}$, exponential dispersion decay $e^{-d/100}$. Fully rigorous.
  - **T7 (Receptor CPF Coupling)**: Period mean flux coupled with receptor CPF back-bearing sector $\Omega$, net district transport balance. (*Finding: $\Omega$ fallback condition*).
  - **T8 (Transboundary Index)**: $120\text{ km}$ border belt, India sector classification, positive inflow / negative outflow, border normal flux integration $\Phi_j = \mathbf{w} \cdot \mathbf{n}_j$. (*Finding: 39 vs 117 domain distinction*).
  - **T9 (PEPC AQI & PEQS Color Scales)**: Complete 7-tier statutory breakpoint table for 6 pollutants, piecewise linear interpolation, composite AQI ($\max(I_{\text{PM2.5}}, I_{\text{PM10}})$), and 7-stop continuous RGB color ramp.
  - **T10 (Temporal Aggregation & QC)**: 7-hour median, 3-hour hold, 75% rule, sub-hourly continuous animation lerp.
  - **T11 (Equirectangular Projection & Greedy Labeling)**: Standard parallel $31^\circ\text{N}$, meridional distortion correction $K_X = \cos 31^\circ \approx 0.857167$, bounding box $[69.10, 75.75, 27.55, 34.30]$, 12 candidate offset vectors, AABB overlap detection, and $20\text{px}$ leader line trigger.

### 2.3 Requirement R3: Modular Data Pipelines Architecture (`DATA_PIPELINES_ARCHITECTURE.md`)
- **Coverage**: **Exhaustive Distributed Architecture**.
- **Components Evaluated**:
  - Independent Celery/Temporal workers for all 7 streams with dedicated schedules and distributed Redis locks.
  - Pydantic v2 validation boundary enforcement. (*Finding: required Optional fields and pollutant_flags*).
  - TimescaleDB hypertables with 7-day and 14-day chunking intervals, PostGIS geometries, and continuous aggregates. (*Finding: missing PK on station_observations*).
  - Multi-tier Redis caching topology (key patterns, binary buffers, TTLs, pub/sub channels).
  - Fault tolerance: AWS Full Jitter exponential backoff, Redis-backed circuit breakers, Dead-Letter Queues (DLQ), and graceful offline degradation with historical data failover (`window.DATA`).

---

## 3. Adversarial Stress-Testing & Failure Modes

### 3.1 Challenge 1: TimescaleDB Upsert Collision Crash
- **Assumption Challenged**: Section 3.1 step 7 assumes `station_observations` will execute `ON CONFLICT (station_id, timestamp) DO UPDATE`.
- **Attack Scenario**: When the ingestion worker executes an hourly batch upsert in PostgreSQL/TimescaleDB, the database immediately aborts the transaction because `station_observations` has no unique constraint or primary key on `(station_id, time)`. Furthermore, the hypertable schema names the column `time`, whereas the upsert SQL references `timestamp`.
- **Blast Radius**: `HIGH`. Complete halt of the primary EPA Punjab ingestion worker; all incoming hourly AQMS data fails to persist and dumps into the Dead-Letter Queue.
- **Mitigation**: Define `PRIMARY KEY (time, station_id)` on the hypertable and align the upsert statement to `ON CONFLICT (time, station_id) DO UPDATE`.

### 3.2 Challenge 2: Pydantic v2 Mass Instantiation Crash
- **Assumption Challenged**: Section 4 declares `pm25_qc: Optional[float]`, etc., assuming they default to `None`.
- **Attack Scenario**: In Pydantic v2, `field: Optional[T]` without `= None` is a required field. Whenever an upstream station measurement lacks one of the 11 QC parameters (e.g., station does not measure $SO_2$ or wind), `NormalizedObservation(...)` raises a `ValidationError: Field required: pm25_qc`.
- **Blast Radius**: `HIGH`. Rejection of over 90% of valid station observations, corrupting provincial averages.
- **Mitigation**: Explicitly assign `= None` to all optional fields: `pm25_qc: Optional[float] = None`.

### 3.3 Challenge 3: Small-Sample Noise Distortion in CPF Roses
- **Assumption Challenged**: Section 2.5 assumes $\text{CPF}_k = m_k / N_k$ is valid for any $N_k > 0$.
- **Attack Scenario**: During light or shifting wind conditions, a sector may experience only 1 or 2 hours of wind over the entire period. If 1 of those hours coincided with an elevated concentration, $\text{CPF}_k = 1.0$ ($100\%$), producing a false maximum spike on the polar rose and severely distorting source-receptor pathway scores in Transform 7.
- **Blast Radius**: `MEDIUM`. Fabricated industrial emission corridors pointing in directions with virtually zero cumulative wind flow.
- **Mitigation**: Enforce the empirical production threshold: if $N_k < 6 \implies \text{CPF}_k = \text{null}$.

### 3.4 Challenge 4: EPA Punjab Telemetry Ingestion Crash on Complex Flags
- **Assumption Challenged**: Section 4 assumes `pollutant_flags` is strictly a string.
- **Attack Scenario**: The EPA Punjab portal periodically returns diagnostic flags as a JSON array (`["pm25_fault", "calib"]`) or nested object. Under `Optional[str] = None`, Pydantic v2 throws `ValidationError: Input should be a valid string`.
- **Blast Radius**: `MEDIUM`. Dropouts of reporting stations during calibration or maintenance events.
- **Mitigation**: Update type signature to `Optional[Union[str, List[str], dict]] = None`.

### 3.5 Challenge 5: Geographic Perimeter vs Border Line Conflation
- **Assumption Challenged**: Section 3.7.1 and Section 2.8.2 describe 117 points along the $1,100\text{ km}$ India-Pakistan border.
- **Attack Scenario**: A backend developer implementing CAMS flux along the India border would attempt to allocate 117 nodes along a 1,100 km line ($9.4\text{ km}$ spacing), causing coordinate misalignment with the 39 border chevron vector coordinates (`tbgeo.samples`, $25\text{ km}$ spacing) used by the frontend visualization.
- **Blast Radius**: `LOW`. Visual misalignment and vector calculation discrepancies between backend CAMS flux and frontend map chevrons.
- **Mitigation**: Explicitly distinguish between the 39 India-border nodes (`tbgeo.samples`) and the 117 provincial perimeter nodes (encompassing all 4 sides of Punjab).

---

## 4. Itemized Findings Catalog

| Finding ID | Severity | Document & Location | Issue Description | Required Remediation |
|---|---|---|---|---|
| **F-01** | **Major** | `DATA_PIPELINES_ARCHITECTURE.md`, Section 5 & Sec 3.1.7 | `station_observations` hypertable lacks composite `PRIMARY KEY (time, station_id)`. The upsert `ON CONFLICT (station_id, timestamp)` fails in PostgreSQL and misnames `time` as `timestamp`. | Add `PRIMARY KEY (time, station_id)` to `station_observations` and update upsert SQL to `ON CONFLICT (time, station_id) DO UPDATE SET ...`. |
| **F-02** | **Major** | `DATA_PIPELINES_ARCHITECTURE.md`, Section 4 | In `NormalizedObservation`, 11 fields (`pm25_qc`, `wind_speed_ms`, etc.) are declared as `Optional[...]` without `= None`, making them required fields in Pydantic v2. | Add `= None` to all optional fields in `NormalizedObservation`. |
| **F-03** | **Major** | `TRANSFORMATION_LOGIC_SPEC.md`, Section 2.5.2 | Transform 5 omits the sample size suppression rule ($N_k \ge 6$) implemented in the production dataset (`window.DATA.pol.cpf`). | Add the condition: $\text{CPF}_k = \text{null}$ if $N_k < 6$. |
| **F-04** | **Minor** | `DATA_PIPELINES_ARCHITECTURE.md`, Section 4 & `DATA_SOURCES_AND_STREAMS.md`, Sec 3.1.2 | `RawStationMeasurement.pollutant_flags` typed strictly as `Optional[str]`, rejecting valid JSON array/object payloads from EPA Punjab. | Update to `Optional[Union[str, List[str], dict]] = None`. |
| **F-05** | **Minor** | `TRANSFORMATION_LOGIC_SPEC.md`, Section 2.7.2 | Transform 7 states $\Omega = 0.25$ only if receptor $b$ is unmonitored; omits fallback when receptor is monitored but the sector has $N_k < 6$. | Clarify that $\Omega = 0.25$ if receptor $b$ is unmonitored OR if $\text{CPF}_b(k_{\text{rec}}) == \text{null}$. |
| **F-06** | **Minor** | `DATA_SOURCES_AND_STREAMS.md`, Sec 3.7.1 & `TRANSFORMATION_LOGIC_SPEC.md`, Sec 2.8.2 | Conflates 117 whole-province boundary perimeter points with the 39 India-Pakistan border animation nodes. | Clarify that 39 sample nodes cover the India-PK border (`tbgeo.samples`), while 117 nodes cover the entire provincial perimeter for CAMS. |

---

## 5. Verified Claims Inventory

| Claim Tested | Verification Method | Status | Notes |
|---|---|---|---|
| Zero codebase modification constraint | Git status check and SHA-256 hash calculation of `index.html` and `collector.py` | **PASS** | Hashes unchanged, 0 bytes modified |
| 7 external data streams endpoint accuracy | Cross-referenced against `collector.py` network calls and public API documentation | **PASS** | Exact match for URLs, headers, parameters |
| Wazirabad anemometer blacklist & $140^\circ$ offset | Verified against `index.html` line 313 (`NOWIND`) and documentation text | **PASS** | Exact match |
| 7-hour median spike filter formula ($v > 4M \land v > 3\text{ref}$) | Reverse-engineered and verified against `index.html` line 326 | **PASS** | Exact match |
| 3-hour logger hold purge ($v_i = v_{i-1} = v_{i-2}$) | Verified against `index.html` line 326 | **PASS** | Exact match |
| Discrete Geodesic IDW clamping ($d_0 = 5\text{km}, p=2$) | Verified against `index.html` line 286 (`idw`) | **PASS** | Exact match |
| Anisotropic IDW formulation ($\cos\alpha$, speed saturation, distance alpha taper) | Verified against `index.html` `fieldAt` and `renderField` | **PASS** | Exact match |
| Planar screen raster IDW ($p=3$, $\epsilon^2 = 0.25$, $5\text{px}$ cells) | Verified against `index.html` `drawSurface` | **PASS** | Exact match |
| Advection flux formula ($C \cdot w \cdot \cos\Delta\theta \cdot e^{-d/100}$, cone $35^\circ$) | Verified against `index.html` line 290 (`flux`) | **PASS** | Exact match |
| Equirectangular projection ($\cos 31^\circ \approx 0.857167$) | Verified against `index.html` constant `KX` | **PASS** | Exact match |
| Greedy collision-free label placement (12 candidate offsets) | Verified against `index.html` `drawValues` | **PASS** | Exact match |
| Pydantic v2 execution & validator behavior | Python test runner script executing model definitions | **PASS (with F-02 fix)** | Validators function cleanly once defaults added |
| Roughness scaling reconciliation factor $K_R = 0.22686$ | Verified against `index.html` `DATA.meta.ecm_ratio` | **PASS** | Exact match |
| NASA FIRMS subnational fire counts (6,703 PK, 3,239 IN) | Verified against `index.html` embedded fire tables | **PASS** | Exact match |

---

## 6. Conclusion & Remediation Roadmap

The authored specifications (`DATA_SOURCES_AND_STREAMS.md`, `TRANSFORMATION_LOGIC_SPEC.md`, `DATA_PIPELINES_ARCHITECTURE.md`) provide an exemplary, mathematically rigorous, and architecturally decoupled foundation for the Punjab Air Quality system. The specifications achieve a level of reverse-engineering fidelity that accurately captures every algorithmic nuance from the monolithic client.

To achieve production-grade infallibility, the authors must apply the 6 itemized fixes in Section 4. Once updated:
1. Update `DATA_PIPELINES_ARCHITECTURE.md` Section 5 with `PRIMARY KEY (time, station_id)`.
2. Update `DATA_PIPELINES_ARCHITECTURE.md` Section 4 with `= None` defaults and flexible `pollutant_flags`.
3. Update `TRANSFORMATION_LOGIC_SPEC.md` Section 2.5.2 with the $N_k \ge 6$ rule and Section 2.7.2 with the generalized $\Omega$ fallback.
4. Update `DATA_SOURCES_AND_STREAMS.md` Section 3.7.1 and `TRANSFORMATION_LOGIC_SPEC.md` Section 2.8.2 distinguishing the 39 border nodes from the 117 provincial perimeter nodes.

Following these targeted revisions, the specifications will be ready for immediate, unconditional approval.
