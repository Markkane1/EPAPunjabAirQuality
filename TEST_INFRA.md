# E2E Test Infrastructure & Test Suite Specification (`TEST_INFRA.md`)
**Document Version:** 1.0.0  
**Project:** Punjab Air Quality Monitoring, Processing, and Visualization System  
**Test Track:** End-to-End (E2E) Verification & Certification  
**Authoritative Specifications:** `docs/TRANSFORMATION_LOGIC_SPEC.md`, `docs/DATA_SOURCES_AND_STREAMS.md`, `docs/DATA_PIPELINES_ARCHITECTURE.md`, `docs/SYSTEM_ARCHITECTURE.md`, `docs/UI_UX_SPECIFICATION.md`, `PROJECT.md`, `ORIGINAL_REQUEST.md`

---

## 1. Test Philosophy & Engineering Principles

### 1.1 Opaque-Box & Requirement-Driven Integrity
All test suites across Tiers 1–4 are engineered as **strict, opaque-box, requirement-driven verification suites**. Tests are designed exclusively from the mathematical and architectural specifications laid out in `docs/` and `PROJECT.md`, completely decoupled from specific implementation internals. No test is permitted to mock away real logic or serve as an unassertive facade. Every assertion verifies an observable system behavior, mathematical invariant, schema boundary, or end-to-end data pipeline outcome.

### 1.2 Formal Test Methodologies Applied
1. **Category-Partition Method (TSL - Test Specification Language):**  
   Every input domain (concentrations, wind speeds, bearings, coordinates, temporal sequences) is partitioned into mutually exclusive, exhaustive equivalence classes.
2. **Boundary Value Analysis (BVA):**  
   Rigorous boundary probing on all physical and operational thresholds:
   - Concentration cap: $C = 0.0, 5000.0, 5000.1\ \mu\text{g/m}^3$
   - Calm wind boundary: $w_s = 0.499\text{ m/s}$ (aerodynamic calm, excluded) vs $w_s = 0.500\text{ m/s}$ (valid wind vector, included)
   - Maximum transport distance: $d = 180.0\text{ km}$ (in cone) vs $d = 180.1\text{ km}$ (exceeded)
   - Angular transport cone: $\Delta\theta = 35.0^\circ$ (included) vs $\Delta\theta = 35.001^\circ$ (excluded)
   - Singularity distance clamp: $d = 0.0\text{ km} \to d_{\text{clamped}} = 5.0\text{ km}$
   - PEPC AQI continuous half-open intervals ($BP_{i-1} < C \le BP_i$) with operational cap at 500 when $\text{PM}_{2.5} > 350.0\ \mu\text{g/m}^3$
   - 75% temporal completeness rule: $N_{\text{valid}} \ge \max(1, \text{round}(0.75 \times H))$
   - Index guard on 3h logger hold filter: $i \ge 2$ precondition preventing negative index wrap
3. **Pairwise & Combinatorial Testing:**  
   Orthogonal parameter combinations of meteorological conditions (calm, light breeze, gale force), pollutant types (particulate vs gaseous vs dimensionless AQI), and data quality flags (valid, null, hold, spike).
4. **Workload & Real-World Application Scenarios (Tier 4):**  
   Multi-step realistic end-to-end user and environmental workflows mirroring actual atmospheric episodes in Punjab.

---

## 2. Multi-Tier Test Architecture

```
tests/
├── fixtures/                                # Authoritative Test Fixtures & Datasets
│   ├── valid_station_observations.csv       # Schema-valid 79-station multi-pollutant dataset
│   ├── severe_smog_event.csv                # Extreme smog inversion episode (PM2.5 > 400)
│   ├── border_transport_plume.csv           # Transboundary easterly inflow plume dataset
│   ├── multistation_lahore_cluster.csv      # 13-station localized micro-airshed dataset
│   ├── boundary_calm_and_extremes.csv       # Boundary values (ws=0.0, ws=0.5, C=5000.0)
│   ├── sensor_freeze_spike_series.csv       # Temporal QC test series (spikes, holds, zeroes)
│   ├── invalid_missing_columns.csv          # Corrupted CSV schema (missing coordinate columns)
│   ├── invalid_out_of_bounds.csv            # Values exceeding boundaries (C > 5000, lat > 35.0)
│   └── reference_expected_outputs.json      # Precomputed analytical oracle solutions
└── e2e/                                     # Comprehensive E2E Verification Suites
    ├── __init__.py
    ├── conftest.py                          # Fixture loaders, mock servers, and test harness
    ├── test_tier1_feature_coverage.py       # Tier 1: Core feature & contract coverage
    ├── test_tier2_boundary_corner.py        # Tier 2: Boundary, corner, and limit cases
    ├── test_tier3_pairwise_combinations.py  # Tier 3: Cross-feature & pairwise interactions
    ├── test_tier4_real_world_scenarios.py   # Tier 4: Real-world operational scenarios
    └── run_all_tests.py                     # Standalone CLI test runner with JSON reporting
```

---

## 3. Feature Inventory & Tier Coverage Mapping

| Feature ID | Feature Name | Description | Test Tier | Primary Test Class / Function | Specification Reference |
|---|---|---|---|---|---|
| **F01** | Workspace Archival | Relocate legacy assets to `original System/` | Tier 1 | `test_workspace_archival_structure` | `ORIGINAL_REQUEST §R1` |
| **F02** | Baseline Data Extraction | 79 stations, 41 districts, 6 airports, 216h | Tier 1 | `test_baseline_catalog_extraction` | `ORIGINAL_REQUEST §R2` |
| **F03** | Discrete Geodesic IDW (T1) | Haversine $R=6371\text{ km}, p=2, d_0=5\text{ km}$ | Tier 1, 2 | `test_discrete_geodesic_idw_math`, `test_idw_zero_distance_clamping` | `TRANSFORMATION_LOGIC_SPEC §2.1` |
| **F04** | Anisotropic Surface IDW (T2) | Wind-steered 2D field, $\epsilon^2=16\text{px}^2, \cos\alpha$ | Tier 1, 3 | `test_anisotropic_idw_downwind_amplification` | `TRANSFORMATION_LOGIC_SPEC §2.2` |
| **F05** | Vector Wind Conversion (T4) | Polar-to-Cartesian $(u, v)$, Wazirabad blacklist | Tier 1, 2 | `test_vector_wind_conversion`, `test_wazirabad_blacklist` | `TRANSFORMATION_LOGIC_SPEC §2.4` |
| **F06** | CPF Polar Wind Roses (T5) | 16 sectors, $P_{75}$ threshold $\tau$, calm $<0.5\text{m/s}$ | Tier 1, 2 | `test_cpf_rose_calculation`, `test_cpf_calm_exclusion` | `TRANSFORMATION_LOGIC_SPEC §2.5` |
| **F07** | Advection Transport Flux (T6) | Physical mass flux, $d \le 180\text{km}, \Delta\theta \le 35^\circ$ | Tier 1, 2 | `test_advection_flux_calculation`, `test_aqi_flux_physical_guard` | `TRANSFORMATION_LOGIC_SPEC §2.6` |
| **F08** | Receptor CPF Coupling (T7) | Coupling flux with receptor rose $\Omega$, top 60 | Tier 1, 3 | `test_receptor_cpf_coupling`, `test_top60_pathway_truncation` | `TRANSFORMATION_LOGIC_SPEC §2.7` |
| **F09** | Transboundary Index (T8) | 120km border belt, 39 normal vectors, 117 CAMS | Tier 1, 4 | `test_transboundary_border_flux`, `test_scenario_4_cross_border` | `TRANSFORMATION_LOGIC_SPEC §2.8` |
| **F10** | PEPC AQI & Color (T9) | Piecewise linear sub-indices, 500 cap, $\max(\text{PM}_{2.5}, \text{PM}_{10})$ | Tier 1, 2 | `test_pepc_aqi_calculation`, `test_pepc_operational_ceiling_cap` | `TRANSFORMATION_LOGIC_SPEC §2.9` |
| **F11** | Temporal QC Filters (T10) | 7h median spike, 3h hold ($i \ge 2$), 75% rule | Tier 1, 2 | `test_temporal_qc_cleaning`, `test_hold_filter_index_guard` | `TRANSFORMATION_LOGIC_SPEC §2.10` |
| **F12** | Plate Carrée & Labels (T11) | Plate Carrée $K_X=\cos 31^\circ$, greedy AABB placement | Tier 1 | `test_equirectangular_projection`, `test_greedy_aabb_labeling` | `TRANSFORMATION_LOGIC_SPEC §2.11` |
| **F13** | Modular Ingestion Base | Unified worker interface and orchestration | Tier 1 | `test_ingestion_worker_contracts` | `DATA_SOURCES_AND_STREAMS §1` |
| **F14** | EPA Punjab Ingestion | EPA Punjab REST scraper with User-Agent & timeout | Tier 1, 3 | `test_epa_punjab_ingestion` | `DATA_SOURCES_AND_STREAMS §2.1` |
| **F15** | NOAA METAR Ingestion | 12 aerodromes, knots-to-m/s, visibility miles-to-m | Tier 1 | `test_metar_ingestion_and_normalization` | `DATA_SOURCES_AND_STREAMS §2.2` |
| **F16** | WMO SYNOP Ingestion | Ogimet SYNOP telegram decoder (Blocks 415, 416, 417) | Tier 1 | `test_wmo_synop_decoding` | `DATA_SOURCES_AND_STREAMS §2.3` |
| **F17** | ECMWF IFS Ingestion | 41 centroid coordinates, 10m and 925hPa wind vectors | Tier 1 | `test_ecmwf_open_meteo_ingestion` | `DATA_SOURCES_AND_STREAMS §2.4` |
| **F18** | Fallback Baseline Engine | Baseline fallback templating on HTTP 404/failure | Tier 1, 4 | `test_fallback_templating_engine`, `test_scenario_2_offline_fallback` | `ORIGINAL_REQUEST §R2` |
| **F19** | User CSV Ingestion Adapter | Streaming ingestion of custom user CSV datasets | Tier 1, 3 | `test_csv_adapter_valid_file`, `test_csv_to_idw_pipeline` | `ORIGINAL_REQUEST §R2` |
| **F20** | CSV Schema Validation | Pydantic v2 validation enforcing schema limits | Tier 1, 2 | `test_csv_schema_enforcement`, `test_csv_boundary_rejection` | `DATA_PIPELINES_ARCHITECTURE §2` |
| **F21** | Clean Domain Models | Station, District, Observation entities | Tier 1 | `test_domain_entity_models` | `SYSTEM_ARCHITECTURE §1` |
| **F22** | Abstract Repository Layer | Decoupled data access abstractions | Tier 1 | `test_repository_interfaces` | `SYSTEM_ARCHITECTURE §2` |
| **F23** | In-Memory / File Repository | Offline baseline + live updates + user CSV data | Tier 1, 3 | `test_repository_crud_operations` | `SYSTEM_ARCHITECTURE §2` |
| **F24** | District Metadata API | `GET /api/v1/meta/districts` returning 41 districts | Tier 1 | `test_api_meta_districts` | `SYSTEM_ARCHITECTURE §3.1` |
| **F25** | Station Metadata API | `GET /api/v1/meta/stations` returning 79 stations | Tier 1 | `test_api_meta_stations` | `SYSTEM_ARCHITECTURE §3.1` |
| **F26** | Current Observations API | `GET /api/v1/observations/current` | Tier 1 | `test_api_observations_current` | `SYSTEM_ARCHITECTURE §3.2` |
| **F27** | Hourly Time-Series API | `GET /api/v1/observations/hourly` | Tier 1 | `test_api_observations_hourly` | `SYSTEM_ARCHITECTURE §3.2` |
| **F28** | Spatial Surface API | `GET /api/v1/spatial/surface` (interpolated grid) | Tier 1, 3 | `test_api_spatial_surface` | `SYSTEM_ARCHITECTURE §3.3` |
| **F29** | CPF Analytics API | `GET /api/v1/analytics/cpf` | Tier 1 | `test_api_analytics_cpf` | `SYSTEM_ARCHITECTURE §3.4` |
| **F30** | Advection Flux API | `GET /api/v1/analytics/flux` | Tier 1, 2 | `test_api_analytics_flux` | `SYSTEM_ARCHITECTURE §3.4` |
| **F31** | Transboundary API | `GET /api/v1/analytics/transboundary` | Tier 1, 4 | `test_api_analytics_transboundary` | `SYSTEM_ARCHITECTURE §3.4` |
| **F32** | CSV Upload & Validation API | `POST /api/v1/ingest/csv` multipart upload | Tier 1, 4 | `test_api_csv_upload_valid`, `test_scenario_3_user_csv_reinterpolate` | `SYSTEM_ARCHITECTURE §3.5` |
| **F33** | SSE Live Streaming API | `GET /api/v1/stream/live` continuous event stream | Tier 1 | `test_api_stream_live_heartbeat` | `SYSTEM_ARCHITECTURE §3.6` |
| **F34–F40**| UI/UX Contract Validation | 5 Zones, 5 Canvas Layers, WCAG 2.1 AAA Tokens | Tier 1, 4 | `test_ui_theme_tokens_contrast`, `test_scenario_1_severe_smog` | `UI_UX_SPECIFICATION §1–§3` |
| **F41** | Comprehensive Verification | 100% test pass rate across Tiers 1–4 | All | `run_all_tests.py` | `ORIGINAL_REQUEST §R6` |

---

## 4. Tier 4 Real-World Operational Scenarios

### Scenario 1: Severe Smog Inversion Episode
- **Atmospheric Trigger:** Intense nocturnal radiation inversion over central Punjab (Lahore, Kasur, Gujranwala, Sheikhupura).
- **Observed Metrics:** Hourly $\text{PM}_{2.5}$ surges to $480.0\ \mu\text{g/m}^3$, with easterly advection ($w_s = 2.4\text{ m/s}, \theta = 85^\circ$).
- **Expected System Response:**
  1. Statutory sub-index $I_{\text{PM2.5}}$ calculates to $>400$, triggering operational ceiling clamp at 500 (`Hazardous`).
  2. PEPC composite AQI reflects $\max(I_{\text{PM2.5}}, I_{\text{PM10}}) = 500$.
  3. Visual continuous color ramp maps to Deep Maroon (`#901530` / `#C00000`).
  4. Inter-district advection flux generates active eastward-to-westward transport vectors ($d < 180\text{ km}$, $\Delta\theta \le 35^\circ$).
  5. UI dashboard triggers hazardous alerts with ARIA live region notification.

### Scenario 2: Offline Fallback & Graceful Degradation
- **Network Trigger:** EPA Punjab government portal experiences an unannounced outage, returning HTTP 404 / 503 gateway timeout.
- **Expected System Response:**
  1. Ingestion circuit breaker trips gracefully without thread starvation or unhandled exceptions.
  2. System seamlessly transitions to Fallback Baseline Templating Engine seeded from the 79-station baseline catalog.
  3. All API endpoints (`/api/v1/observations/current`, `/api/v1/spatial/surface`) remain responsive with HTTP 200.
  4. District and station summary payloads include `is_estimated: true` or `fallback: true` diagnostic flags.
  5. Dashboard UI displays amber system status banner without crashing.

### Scenario 3: Custom User CSV Upload & Dynamic Re-Interpolation
- **User Action:** Environmental analyst uploads a custom 48-hour monitoring CSV dataset (`tests/fixtures/valid_station_observations.csv`) containing non-standard rural monitoring coordinates.
- **Expected System Response:**
  1. `POST /api/v1/ingest/csv` validates schema: timestamps, coordinate bounds $[27, 35]^\circ\text{N}, [69, 76]^\circ\text{E}$, concentrations $[0, 5000]\ \mu\text{g/m}^3$.
  2. Data normalization applies zero-purging and unit reconciliation.
  3. Spatial interpolation engine dynamically recalculates 2D IDW continuous surface covering newly supplied coordinates.
  4. District summaries update in-memory and are immediately queryable via REST APIs.

### Scenario 4: Cross-Border Plume Inflow Analysis
- **Atmospheric Trigger:** Massive stubble-burning plume transported across the international border into eastern Punjab during NWP easterly wind regime.
- **Expected System Response:**
  1. Border-belt districts ($\mathcal{B} \le 120\text{ km}$) detect wind from India inflow sectors ($k \in \text{india\_sectors}_d$).
  2. Positive transboundary flux values $\text{TBVal}_d(t) > 0$ are calculated along the border corridor.
  3. 39 border animation nodes calculate normal vector dot product $\Phi_j(t) = \mathbf{w}_j \cdot \mathbf{n}_j > +0.25\text{ m/s}$, triggering red inflow chevron indicators.
  4. Regional net mass balance correctly attributes transboundary inflow vs internal domestic emissions.

### Scenario 5: Multi-Station District Disaggregation (Lahore 13 Stations vs Single Station)
- **Data Scenario:** High-density urban district (Lahore with 13 discrete monitoring sites exhibiting micro-climate gradients) vs single-station rural district (Attock).
- **Expected System Response:**
  1. $P_{75}$ criterion threshold $\tau$ for Lahore CPF rose is computed on the **pooled station-hour observations** ($N \approx 2,700$ site-hours) rather than smoothed district arithmetic averages, preserving localized emission peaks.
  2. Attock single-station calculates standard time-series statistics.
  3. Spatial IDW distinguishes localized hot spots within the Lahore urban core (Gulberg, Town Hall) while maintaining provincial continuity.

---

## 5. Execution & Verification Standards

### 5.1 Test Execution Commands
The complete E2E test suite can be executed in two official modes:

```bash
# Mode 1: Standard Pytest Runner
python -m pytest tests/e2e/ -v --tb=short

# Mode 2: Enterprise Automated Test Runner with JSON Summary
python tests/e2e/run_all_tests.py
```

### 5.2 Quality Gates & Acceptance Thresholds
- **Suite Pass Rate:** $100\%$ required. Zero tolerated failures or regressions.
- **Mathematical Accuracy:** Tolerances strictly bounded by $\epsilon = 10^{-5}$ for continuous numerical transforms; exact integer matching for PEPC statutory AQI calculations.
- **Execution Budget:** Entire E2E test suite (Tiers 1–4) must execute in $< 30$ seconds.
- **Output Artifacts:** Automated generation of `test_results_e2e.json` containing timestamped test counts, execution metrics, and tier-by-tier breakdowns.
