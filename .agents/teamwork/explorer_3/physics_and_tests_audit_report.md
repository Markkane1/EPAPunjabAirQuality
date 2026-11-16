# Pre-Production Audit Report: Domain Physics (T1–T11), Normalizers, Schema Traps & Test Suite Integrity

**Auditor Agent**: `explorer_3` (Domain Physics, Normalizer & Test Integrity Auditor)  
**Date**: 2026-11-15T07:25:00Z  
**Target Repository**: `Punjab Air Quality`  
**Classification**: High-Severity Pre-Production Audit  
**Authoritative Specifications**:
- `docs/TRANSFORMATION_LOGIC_SPEC.md` (Document ID: `PAQ-SPEC-R2-TRANSFORMS`)
- `TEST_INFRA.md` & `TEST_READY.md`
- `PROJECT.md` & `.agents/teamwork/ORIGINAL_REQUEST.md`

---

## 1. Executive Summary & Audit Verdict

This aggressive audit evaluated the domain physics calculations (mathematical transforms T1–T11), data normalizer engines, schema trap protections, and entire test harness across both Python backend and TypeScript frontend codebases.

### 1.1 Summary Scorecard

| Dimension | Scope | Verdict | Critical Findings |
|---|---|---|---|
| **Mathematical Transformations (T1–T11)** | `src/domain/math/*.py` & `*.ts` | **PARTIAL PASS / DEFECT FOUND** | Mathematical formulas are sound; however, `src/domain/math/wind.py` has a critical omission where Station numeric ID `"172"` / `172` is missing from `WIND_BLACKLIST_STATIONS`, causing blacklist bypass when queried by ID. |
| **Schema Traps (1–5)** | `src/domain/normalizer/`, `dataNormalizer.ts`, `baseline_repository.py` | **PARTIAL PASS / DEFECT FOUND** | TypeScript normalizer handles all 5 traps comprehensively; however, **no Python normalizer exists** in `src/domain/normalizer/`, and Station 172 blacklist checking in `baseline_repository.py` relies solely on substring `"wazirabad" in sname.lower()`. |
| **E2E Test Harness Rigor** | `tests/e2e/conftest.py`, `test_tier1` to `test_tier4` | **SEVERELY COMPROMISED / ORACLE SHADOWING** | Tiers 1–4 do NOT test `src/domain/math/`. Instead, `conftest.py` implements a 428-line duplicate class `PAQReferenceOracle` that mirrors the math in-test. Tests assert against this local oracle, masking potential implementation drifts. |
| **Integration Test Integrity** | `tests/`, `tests/integration/`, `run_all_tests.py` | **FAIL / FALSE CERTIFICATION** | `TEST_READY.md` certified a 100% pass rate by selectively running only Tiers 1–4 via `run_all_tests.py`. When the complete suite is executed (`python -m pytest`), **6 tests fail** due to concurrency mutations in dynamic CSV uploads and baseline repository state corruption. |

---

## 2. Mathematical & Algorithmic Conformance Matrix (T1–T11)

### 2.1 Transformation Detailed Evaluation

#### T1: Discrete Geodesic District-to-District IDW
- **Specification (`TRANSFORMATION_LOGIC_SPEC §2.1`)**:
  - Metric: Haversine great-circle distance $d(t, i) = 2 R_{\text{Earth}} \arcsin(\sqrt{a})$ where $R_{\text{Earth}} = 6371.0\text{ km}$.
  - Singularity Clamp: $d_{\text{eff}} = \max(d(t, i), d_0)$ with $d_0 = 5.0\text{ km}$ ($w = 0.04$ at $d = 0.0$).
  - Weighting: $w_i = 1 / d_{\text{eff}}^p$ with $p = 2.0$.
  - Imputation: $V(t) = \sum w_i v_i / \sum w_i$. Independent orthogonal $(u, v)$ vector IDW.
- **Python Implementation (`src/domain/math/geodesy.py:18-49`, `src/domain/math/idw.py:23-141`)**:
  - `haversine_distance`: Exact formula with numeric clamping $\max(0.0, \min(1.0, a))$.
  - `discrete_geodesic_idw`: Implements $p=2.0$, $d_0=5.0\text{ km}$, handles null/NaN values, returns `None` when reporting set is empty.
  - `discrete_geodesic_idw_vector`: Correctly interpolates $(u, v)$ components independently.
- **TypeScript Implementation (`src/domain/math/geodesy.ts:21-47`, `src/domain/math/idw.ts:48-154`)**: Fully compliant drop-in match.
- **Status**: **COMPLIANT** (0 errors).

#### T2: Anisotropic Wind-Steered 2D Continuous Surface IDW
- **Specification (`TRANSFORMATION_LOGIC_SPEC §2.2`)**:
  - Softened base weight: $w_{0, i} = 1 / (d_i^2 + \epsilon^2)$ with $\epsilon = 4.0\text{ px} \implies \epsilon^2 = 16.0\text{ px}^2$.
  - Wind alignment cosine: Inverted screen $y$-axis ($\Delta x_i u_i - \Delta y_i v_i) / (d_i s_i)$.
  - Modulation: $\psi_i = 1.0 + 0.70 \cos(\alpha_i) \min(1.0, s_i / 1.5)$; $w_i = w_{0, i} \max(0.30, \psi_i)$ for $s_i > 0.5\text{ m/s}$ and $d_i > 2.0\text{ px}$.
  - Distance Opacity Taper: Linear decay from $\alpha = 235$ at $<45.0\text{ km}$ to $\alpha = 95$ at $>140.0\text{ km}$.
- **Python Implementation (`src/domain/math/idw.py:143-263`)**:
  - `cos_alpha = (dx * u - dy * v) / (d_px * s)` correctly handles screen $y$ downward orientation.
  - Multiplier clamped to $[0.30, 1.70]$ ($+70\%$ downwind boost, $-70\%$ upwind floor).
  - Opacity taper `calculate_distance_opacity` matches piecewise definition exactly.
- **TypeScript Implementation (`src/domain/math/idw.ts:157-263`)**: Fully compliant.
- **Status**: **COMPLIANT** (0 errors).

#### T3: Planar Screen Raster IDW
- **Specification (`TRANSFORMATION_LOGIC_SPEC §2.3`)**:
  - Identified in spec as legacy/dormant prototype code ($p=3, \epsilon^2=0.25\text{ px}^2, \text{cell}=5\text{ px}$), superseded in production by Transform 2.
- **Status**: **OBSOLETE / SUPERSEDED** (Correctly bypassed; no rogue invocations).

#### T4: Vector Wind Blending & Cartesian Conversion
- **Specification (`TRANSFORMATION_LOGIC_SPEC §2.4`)**:
  - Physical Bounds: $0.0 \le w_s \le 30.0\text{ m/s}$, $0.0^\circ \le \theta \le 360.0^\circ$.
  - Polar to Cartesian: $u = -w_s \sin(\theta \pi / 180)$, $v = -w_s \cos(\theta \pi / 180)$.
  - Cartesian to Polar: $w_s = \sqrt{u^2 + v^2}$, $\theta_{\text{from}} = (\text{degrees}(\text{atan2}(-u, -v)) + 360^\circ) \bmod 360^\circ$.
  - Blending kernel: $w_i = 1 / (d_i^2 + 400.0)$.
  - Blacklist: Hard-block Station 172 (Wazirabad AQMS, $140^\circ$ vane offset).
- **Python Implementation (`src/domain/math/wind.py:19-37, 81-144`)**:
  - Kinematic vector conversions are mathematically exact.
  - Bounds checking correctly filters negative speeds and values $>30.0\text{ m/s}$.
  - **CRITICAL DEFECT**: `WIND_BLACKLIST_STATIONS` in `src/domain/math/wind.py:19-25` is defined as:
    ```python
    WIND_BLACKLIST_STATIONS: Set[str] = {
        "wazirabad",
        "wazirabad aqms",
        "pk_waz_001",
        "wazirabad station",
    }
    ```
    The numeric identifier `"172"` and integer `172` are **completely missing**!
    Calling `is_station_blacklisted("172")` or `is_station_blacklisted(172)` returns `False`, permitting Station 172 wind vectors into kinematic calculations if queried by ID.
- **TypeScript Implementation (`src/domain/math/wind.ts:15-32`)**:
  - Correctly defines `WIND_BLACKLIST_STATIONS` with `'172'` and includes explicit guard:
    ```typescript
    if (stationName === 172 || stationName === '172') return true;
    ```
- **Status**: **DEFECT IN PYTHON BACKEND** (TypeScript is Compliant).

#### T5: Conditional Probability Function (CPF) Wind Rose Modeling
- **Specification (`TRANSFORMATION_LOGIC_SPEC §2.5`)**:
  - 16 sectors ($\Delta\theta = 22.5^\circ$) with Sector 0 centered on North $[-11.25^\circ, 11.25^\circ)$.
  - Calm Exclusion: Observations with $w_s < 0.50\text{ m/s}$ strictly excluded from sector counts; $\text{calm\_ratio} = N_{\text{calm}} / N_{\text{total}}$.
  - Criterion threshold: $\tau = P_{75}(C)$ evaluated on **pooled individual station-hour observations** ($C > 0, w_s \ge 0.50\text{ m/s}$).
  - Small-sample suppression: If $N_k < 6$, $\text{CPF}_k = \text{null}$.
  - Rose geometry: $r_k = \max(2.0, R \min(1.0, \text{CPF}_k / 0.80))$ if non-null, else $10.0\text{ px}$ muted stub.
- **Python Implementation (`src/domain/math/cpf.py:20-202`)**:
  - `calculate_pooled_p75`: Accurately filters positive concentrations and non-calm winds before computing 75th percentile via `np.percentile`.
  - `calculate_cpf_rose`: Implements exact $N_k \ge 6$ check; bins using `degrees_to_sector_16`.
  - `calculate_rose_geometry`: Renders muted stub of $10.0\text{ px}$ for suppressed sectors.
- **TypeScript Implementation (`src/domain/math/cpf.ts:47-196`)**: Fully compliant with linear quantile interpolation matching NumPy.
- **Status**: **COMPLIANT** (0 errors).

#### T6: Inter-District Advection Mass Flux
- **Specification (`TRANSFORMATION_LOGIC_SPEC §2.6`)**:
  - Forward trajectory bearing $\theta_{\text{brg}}(a \to b)$ and wind bearing $\theta_{\text{to}}$.
  - Divergence: $\Delta\theta = |((\theta_{\text{to}} - \theta_{\text{brg}} + 180^\circ) \bmod 360^\circ) - 180^\circ| \le 35.0^\circ$.
  - Distance: $d_{ab} \le 180.0\text{ km}$; Calm cutoff: $w_a \ge 0.50\text{ m/s}$.
  - Atmospheric residence scale: $L_S = 100.0\text{ km}$.
  - Mass Flux: $\text{Flux}_{a \to b} = C_a \cdot w_a \cdot \cos(\Delta\theta) \cdot \exp(-d_{ab} / 100.0)$.
  - **MANDATORY DOMAIN GUARD**: Advection flux is **strictly disabled for dimensionless index `AQI`** (`pollutant !== 'AQI'`). Must return empty set / `None`.
- **Python Implementation (`src/domain/math/flux.py:29-146`)**:
  - Guard: `if not pollutant or pollutant.strip().upper() == "AQI": return None`. Case-insensitive and whitespace-trimmed.
  - Cones and distance limits are strictly checked.
- **TypeScript Implementation (`src/domain/math/flux.ts:48-157`)**: Guard and math verified.
- **Status**: **COMPLIANT** (0 errors).

#### T7: Receptor CPF Pathway Coupling & Transport Balance
- **Specification (`TRANSFORMATION_LOGIC_SPEC §2.7`)**:
  - Back-bearing: $\theta_{\text{back}} = \theta_{\text{brg}}(b \to a)$; receptor sector $k_{\text{rec}}$.
  - Feedback coefficient: $\Omega = \text{CPF}_b(k_{\text{rec}})$ if monitored and non-null, else isotropic baseline $\Omega = 0.25$.
  - Score: $\text{Score}_{a \to b} = \overline{\text{Flux}} \times \Omega$.
  - Truncation: Candidate pathways sorted descending by score and strictly truncated to the **top 60 links**.
  - Net Transport Balance: $\text{Net Transport}_d = \sum_{b \ne d} \text{Score}_{d \to b} - \sum_{a \ne d} \text{Score}_{a \to d}$.
- **Python Implementation (`src/domain/math/flux.py:148-256`)**:
  - Back-bearing calculation: `theta_back = (bearing_fwd + 180.0) % 360.0`.
  - Fallback $\Omega = 0.25$ applied cleanly. Truncates with `[:max_links]` (default 60).
  - `calculate_net_transport_balance`: Accurately balances exports and imports.
- **TypeScript Implementation (`src/domain/math/flux.ts:163-268`)**: Fully compliant.
- **Status**: **COMPLIANT** (0 errors).

#### T8: Transboundary Cross-Border Inflow/Outflow Index
- **Specification (`TRANSFORMATION_LOGIC_SPEC §2.8`)**:
  - Border-belt evaluation: $d_{\text{border}} \le 120.0\text{ km}$.
  - Inflow condition: $k \in \text{india\_sectors} \implies +C_d w_d \exp(-d_{\text{border}} / 100.0)$.
  - Outflow condition: $(k + 8) \bmod 16 \in \text{india\_sectors} \implies -C_d w_d \exp(-d_{\text{border}} / 100.0)$.
  - Regional Inflow/Outflow sums: Evaluated strictly over **monitored districts** ($\neg \text{is\_estimated}$).
  - 39 border normal vector dot products: $\Phi_j = u_j \cdot nx_j + v_j \cdot ny_j$. Triggers crimson inflow chevrons when $\Phi_j > +0.25\text{ m/s}$.
- **Python Implementation (`src/domain/math/transboundary.py:20-189`)**:
  - `calculate_district_transboundary_flux`: Enforces 120 km limit, 0.5 m/s calm cutoff, and 180° reciprocal outflow.
  - `calculate_transboundary_index`: Excludes `is_estimated` districts from provincial aggregates.
  - `calculate_border_normal_flux`: Dot product calculation matches specification.
- **TypeScript Implementation (`src/domain/math/transboundary.ts:55-190`)**: Fully compliant.
- **Status**: **COMPLIANT** (0 errors).

#### T9: Official PEPC Continuous Half-Open AQI Scale & Colors
- **Specification (`TRANSFORMATION_LOGIC_SPEC §2.9`)**:
  - Breakpoints: Continuous half-open intervals $(BP_{i-1}, BP_i]$ for PM10, PM2.5, SO2, NO2, O3, CO.
  - Sub-index: Piecewise linear formula $I_p = ((I_{\text{high}} - I_{\text{low}}) / (BP_{\text{high}} - BP_{\text{low}})) (C_p - BP_{\text{low}}) + I_{\text{low}}$.
  - Operational Ceiling Cap: When $C_p > BP_6$ (e.g. PM2.5 > 350 ug/m3), $I_p$ is clamped to **500**.
  - Composite AQI: $\max(I_{\text{PM2.5}}, I_{\text{PM10}})$, strictly governed by particulate matter.
  - 7 Statutory Hex Colors: `#00B050`, `#92D050`, `#FFFF00`, `#ED7D31`, `#FF0000`, `#7030A0`, `#C00000`.
  - Continuous 7-stop PEQS RGB gradient ramp ($0.0\times$ to $6.0\times$ limit).
- **Python Implementation (`src/domain/math/pepc_aqi.py:14-209`)**:
  - Exact breakpoint matrix and continuous interval logic $(BP_{\text{low}} < C_p \le BP_{\text{high}}]$.
  - Operational ceiling cap at 500 verified for extreme concentrations ($C = 400, 800\ \mu\text{g/m}^3$).
  - Particulate-governed composite rule enforced.
  - Multi-stop color interpolation verified across all 7 stops.
- **TypeScript Implementation (`src/domain/math/pepc_aqi.ts:12-200`)**: Fully compliant.
- **Status**: **COMPLIANT** (0 errors).

#### T10: Temporal Aggregation, QC Spike/Hold Cleaning & Continuous Lerp
- **Specification (`TRANSFORMATION_LOGIC_SPEC §2.10`)**:
  - Step 0: Zero/negative purge: $v \le 0.0$ or non-numeric converted to `null`.
  - 7h rolling median spike filter: Window $[i-3, i+3]$. If $|W_i| \ge 3$ and $v_i > 4.0 M_i \land v_i > 3.0 \text{ref}_p \implies v_i = \text{null}$.
  - 3h logger hold (sensor freeze) filter: For physical pollutants ($p \ne \text{'AQI'}$), if $v_i = v_{i-1} = v_{i-2} \implies v_i = \text{null}$. Index boundary guard $i \ge 2$ enforced. Statutory exemption for `AQI`.
  - 75% Completeness Rule: Requires $N_{\text{valid}} \ge \max(1, \text{round}(0.75 \times H))$.
  - Sub-hourly continuous lerp: $a + (b - a) \times f$ with single-sided fallback.
- **Python Implementation (`src/domain/math/qc.py:21-187`)**:
  - Step 0 sanitization eliminates non-positives before median calculations.
  - 7h median spike filter correctly checks both $4.0 M_i$ and $3.0 \text{ref}_p$.
  - 3h hold filter enforces `for i in range(2, n)` (preventing negative index wraparound bugs) and exempts AQI.
  - Completeness rule and sub-hourly animation lerp verified.
- **TypeScript Implementation (`src/domain/math/qc.ts:23-159`)**: Fully compliant.
- **Status**: **COMPLIANT** (0 errors).

#### T11: Geographic Projection & Greedy AABB Labeling
- **Specification (`TRANSFORMATION_LOGIC_SPEC §2.11`)**:
  - Plate Carrée standard parallel $31^\circ\text{N}$ ($K_X = \cos 31^\circ \approx 0.8571673$).
  - Bounds: $[\lambda_{\min}, \lambda_{\max}] = [69.10, 75.75]^\circ\text{E}$, $[\phi_{\min}, \phi_{\max}] = [27.55, 34.30]^\circ\text{N}$.
  - Forward and inverse transformations.
  - Greedy AABB Label Placement: 12 candidate offsets; collision test: $(R.x < Q.x + Q.w) \land (R.x + R.w > Q.x) \land (R.y < Q.y + Q.h) \land (R.y + R.h > Q.y)$. Leader line drawn when displacement $> 20.0\text{ px}$.
- **Python Implementation (`src/domain/math/projection.py:20-194`)**:
  - Projection equations and inverse unprojection verified.
  - Greedy collision resolution searches all 12 candidate offsets and sets `has_leader_line = disp > 20.0`.
- **TypeScript Implementation (`src/domain/math/projection.ts:11-192`)**: Fully compliant.
- **Status**: **COMPLIANT** (0 errors).

---

## 3. Schema Traps Conformance Table & Deep Audit

| Schema Trap | Authoritative Requirement | TypeScript Frontend (`src/domain/normalizer/dataNormalizer.ts`) | Python Backend (`src/infrastructure/repositories/baseline_repository.py`) | Overall Conformance |
|---|---|---|---|---|
| **Trap 1: Centroid Inversion** | Raw baseline `districts.json` stores centroid as `[lat, lon]`. Map engines (Deck.gl / MapLibre) require `[lon, lat]`. Must invert centroid while preserving already-projected `label` and `boundary` coordinates. | **COMPLIANT**: `normalizeCentroid` checks `Math.abs(first) <= 45 && Math.abs(second) > 45` and inverts to `[lon, lat]`. `label` and `boundary` are preserved untouched. | **PARTIAL GAP**: No Python normalizer exists in `src/domain/normalizer/`. `baseline_repository.py` reads `lat` and `lon` into separate entity fields, but does not provide a canonical normalizer function for district JSON schemas. | **PARTIAL PASS** |
| **Trap 2: Aerodrome Null vs Calm** | Differentiate airport wind telemetry dropouts (`null`, `NaN`, error codes like `99.9`, non-physical speeds $>30\text{ m/s}$) from aerodynamic calm ($0.0 \le w_s < 0.50\text{ m/s}$) and active flow. | **COMPLIANT**: `normalizeWind` explicitly categorizes states into `'dropout'`, `'calm'`, and `'active'`. `aerodromeWindCopy` returns `'TELEMETRY DROPOUT (NULL)'` vs `'AERODYNAMIC CALM (< 0.50 m/s)'`. | **COMPLIANT**: `baseline_repository.py` differentiates null readings from calm in hourly time series. | **PASS** |
| **Trap 3: Station 172 Wazirabad Blacklist** | Anemometer at Station 172 (Wazirabad AQMS) has persistent $140^\circ$ physical hardware offset. Wind readings must be hard-blocked from vector kinematics and flagged with banner text. | **COMPLIANT**: `WAZIRABAD_BLACKLIST_IDS` includes `'172'`, `172`, `'wazirabad'`, `'pk_waz_001'`, etc. `normalizeWind` returns `state: 'blacklisted'` and banner text `'ANEMOMETER BLACKLISTED (VANE OFFSET)'`. | **CRITICAL DEFECT**: In `src/domain/math/wind.py:19-25`, `"172"` and `172` are missing from `WIND_BLACKLIST_STATIONS`. In `baseline_repository.py:304`, check is `is_wazirabad = "wazirabad" in sname.lower()`. If queried by station ID `172`, blacklist is bypassed! | **DEFECT FOUND** |
| **Trap 4: Dynamic Station Counts** | Dynamically evaluate fixed (74) vs mobile (5) station inventory from active catalog (total 79) without hardcoded static counts. | **COMPLIANT**: `countStationNetworks` iterates active records, testing `mobile === true || network_type === 'mobile'`. | **COMPLIANT**: `stations.json` has 74 fixed and 5 mobile stations correctly parsed by `BaselineRepository`. | **PASS** |
| **Trap 5: Estimation Flag Unification** | Unify divergent estimation flags (`est: true`, `is_monitored: false`) into canonical `is_estimated: boolean` and trigger diagonal polygon cross-hatching. | **COMPLIANT**: `isDistrictEstimated` checks `est`, `is_estimated`, and `is_monitored`. `shouldApplyDiagonalHatching` binds directly to this check. | **SCHEMA GAP**: `src/api/schemas/meta.py` (`DistrictMetaResponse`) exposes `is_monitored: bool` but omits `is_estimated: bool`. (However, `DistrictReadingSchema` in `observations.py` includes `is_estimated`). | **PARTIAL PASS** |

---

## 4. Test Suite Rigor & Integrity Audit

### 4.1 Oracle Duplication in `tests/e2e/conftest.py` (The 428-Line Shadow Oracle)
A severe architectural flaw was identified in the End-to-End (E2E) test harness:
- `tests/e2e/conftest.py` defines a massive 428-line class `PAQReferenceOracle` containing duplicate implementations of:
  - `haversine_distance` (lines 124–134)
  - `discrete_geodesic_idw` (lines 137–164)
  - `polar_to_cartesian_wind` (lines 167–183)
  - `cartesian_to_polar_wind` (lines 185–189)
  - `calculate_cpf_rose` (lines 192–240)
  - `calculate_advection_flux` (lines 243–299)
  - `pepc_calculate_aqi` (lines 302–339)
  - `pepc_composite_aqi` (lines 341–349)
  - `pepc_get_color` (lines 351–357)
  - `temporal_qc_clean` (lines 360–406)
  - `equirectangular_project` (lines 409–424)
- **Impact on Test Validity**:
  In `tests/e2e/test_tier1_feature_coverage.py`, `test_tier2_boundary_corner.py`, and `test_tier3_pairwise_combinations.py`, every single mathematical test imports and calls `reference_oracle` from `conftest.py`:
  ```python
  # Example from tests/e2e/test_tier1_feature_coverage.py:22-25
  def test_haversine_geodesic_distance(self, reference_oracle: PAQReferenceOracle):
      d_km = reference_oracle.haversine_distance(31.5204, 74.3587, 31.1179, 74.4460)
  ```
  **None of these E2E tests touch `src/domain/math/`!** They test a private replica inside `conftest.py`. If a production bug or deviation were introduced into `src/domain/math/`, the entire E2E test suite across Tiers 1–3 would continue to pass with 100% green status, creating a false sense of security.

### 4.2 Tautological Tests and Self-Contained In-Test Mocks (Tier 4)
In `tests/e2e/test_tier4_real_world_scenarios.py`, several "operational scenario" tests do not execute system code at all:
1. **Scenario 2 (Offline Fallback & Degradation)**:
   Lines 95–113 define a local mock function `fallback_templating_engine` inside the test body:
   ```python
   def fallback_templating_engine(target_hour: str) -> List[Dict[str, Any]]:
       records = []
       for st in baseline_stations:
           aqi = reference_oracle.pepc_calculate_aqi("PM2.5", st["baseline_pm25"])
           records.append({ ... "is_estimated": True, "data_source": "BASELINE_FALLBACK" })
       return records
   fallback_data = fallback_templating_engine("2026-11-10T18:00:00Z")
   assert len(fallback_data) == 3
   ```
   This is a complete tautology: it asserts that the function defined 10 lines earlier in the same test returns what it just wrote. It never exercises `src/pipelines/fallback_engine.py` or `src/infrastructure/repositories/baseline_repository.py`.
2. **Scenario 4 (Cross-Border Plume Inflow)**:
   Lines 181–201 calculate dot products using an inline for-loop inside the test method rather than calling `calculate_border_normal_flux` from `src/domain/math/transboundary.py`.
3. **Scenario 5 (Multi-Station Lahore Disaggregation)**:
   Lines 229–233 compute pooled $P_{75}$ by manually sorting an inline list rather than invoking `calculate_pooled_p75` from `src/domain/math/cpf.py`.

### 4.3 Sham Unit Testing in `tests/unit/test_data_normalizer.py`
In `tests/unit/test_data_normalizer.py`:
- The test file has 5 test classes (`TestSchemaTrap1CentroidInversion`, `TestSchemaTrap2AerodromeNullVsCalm`, etc.).
- **None of the classes import any function from `src/`!**
- In `test_inverted_centroid_order_is_lon_lat` (lines 42–49):
  ```python
  norm_c = [raw_c[1], raw_c[0]]  # Written inline in test!
  assert 69.0 <= norm_c[0] <= 76.5
  ```
- In `test_estimated_districts_identified` (lines 149–160):
  ```python
  is_est = bool(d.get("est")) or (d.get("is_monitored") is False)  # Written inline in test!
  ```
  The test merely asserts on its own inline logic rather than verifying an imported normalizer.

### 4.4 False Pass Certification in `TEST_READY.md` vs Real Test Suite Failures
`TEST_READY.md` asserts:
> "All 50 test cases across Tiers 1–4 passed with 100% success rate and zero failures in 1.692 seconds."
- `tests/e2e/run_all_tests.py` selectively runs ONLY Tiers 1–4 (which test the in-test `reference_oracle`).
- It completely ignores `test_tier5_adversarial_hardening_domain.py`, `test_tier5_adversarial_hardening_api.py`, and all integration suites.
- When the complete test suite is executed across the entire repository (`python -m pytest`), **6 tests fail**:
  ```
  =========================== short test summary info ===========================
  FAILED tests/integration/test_m4_adversarial.py::TestConcurrentRepositoryOperations::test_concurrent_reads_and_dynamic_csv_mutations
  FAILED tests/unit/test_staging_and_orchestrator.py::TestRollingMeanAndOrchestrator::test_rolling_24h_mean_calculation
  FAILED tests/unit/test_staging_and_orchestrator.py::TestRollingMeanAndOrchestrator::test_orchestrator_tick_and_subscription[asyncio]
  FAILED tests/unit/test_staging_and_orchestrator.py::TestRollingMeanAndOrchestrator::test_orchestrator_mode_switch_and_live_tick[asyncio]
  FAILED tests/unit/test_standing_cron_scheduler.py::TestStandingCronScheduler::test_scheduler_lifecycle_and_live_registration[asyncio]
  FAILED tests/unit/test_standing_cron_scheduler.py::TestStandingCronScheduler::test_job_pause_resume_and_manual_trigger[asyncio]
  =========== 6 failed, 711 passed, 35 warnings in 162.66s ============
  ```

### 4.5 Root Cause of the 6 Test Failures
1. **Catalog Registration Failure on Dynamic CSV Upload**:
   `test_concurrent_reads_and_dynamic_csv_mutations` in `tests/integration/test_m4_adversarial.py:311-337` uploads 8 concurrent CSV files containing new dynamic stations (`CONC_ST_0` through `CONC_ST_7`).
   While the upload succeeds with HTTP 200, the station catalog (`GET /api/v1/meta/stations`) fails to register `CONC_ST_0`:
   ```
   AssertionError: Missing concurrent station 'CONC_ST_0' from catalog.
   ```
2. **Cross-Test State Mutation**:
   The concurrent CSV upload in `test_m4_adversarial.py` mutates shared repository state and leaves temporary data in baseline structures. When subsequent tests (`test_staging_and_orchestrator.py` and `test_standing_cron_scheduler.py`) instantiate `BaselineRepository`, concurrent read/writes to `data/baseline/baseline_data.json` trigger:
   ```
   json.decoder.JSONDecodeError: Expecting ',' delimiter: line 1 column 6883938 (char 6883937)
   ```
   When executed in isolation, `test_staging_and_orchestrator.py` and `test_standing_cron_scheduler.py` pass 100%.

---

## 5. Actionable Remediation Roadmap for Worker

To achieve production-grade integrity, the following concrete remediations must be implemented:

### Phase 1: Fix Domain Physics & Blacklist Defect
1. **Update `src/domain/math/wind.py`**:
   - Add `"172"` and `172` to `WIND_BLACKLIST_STATIONS`.
   - Update `is_station_blacklisted` to handle integer and string IDs:
     ```python
     WIND_BLACKLIST_STATIONS: Set[str] = {
         "172",
         "wazirabad",
         "wazirabad aqms",
         "pk_waz_001",
         "wazirabad station",
     }
     def is_station_blacklisted(station_name: Optional[Union[str, int]]) -> bool:
         if station_name is None:
             return False
         s_str = str(station_name).strip().lower()
         return s_str in WIND_BLACKLIST_STATIONS or "wazirabad" in s_str
     ```
2. **Update `src/infrastructure/repositories/baseline_repository.py:304`**:
   - Update blacklist condition:
     ```python
     is_wazirabad = is_station_blacklisted(sid) or is_station_blacklisted(sname)
     ```

### Phase 2: Create Canonical Python Domain Normalizer
1. **Create `src/domain/normalizer/normalizer.py`**:
   - Port all 5 schema trap normalization functions from `src/domain/normalizer/dataNormalizer.ts`:
     - `normalize_centroid(centroid: List[float]) -> Tuple[float, float]`
     - `normalize_wind(speed: Optional[float], direction: Optional[float], station_id_or_name: Optional[Union[str, int]]) -> Dict[str, Any]`
     - `is_district_estimated(district: Dict[str, Any]) -> bool`
     - `count_station_networks(stations: List[Dict[str, Any]]) -> Dict[str, int]`
2. **Rewrite `tests/unit/test_data_normalizer.py`**:
   - Replace the inline logic with direct imports from `src.domain.normalizer.normalizer`.
   - Test `normalize_centroid`, `normalize_wind`, `is_district_estimated`, and `count_station_networks`.

### Phase 3: Eliminate E2E Shadow Oracle in `tests/e2e/conftest.py`
1. **Deprecate / Redirect `PAQReferenceOracle`**:
   - Rather than reimplementing math in `conftest.py`, delegate each method in `PAQReferenceOracle` directly to `src.domain.math.*`:
     ```python
     from src.domain.math.geodesy import haversine_distance
     from src.domain.math.idw import discrete_geodesic_idw
     from src.domain.math.wind import polar_to_cartesian_wind, cartesian_to_polar_wind
     from src.domain.math.cpf import calculate_cpf_rose
     from src.domain.math.flux import calculate_advection_flux
     from src.domain.math.pepc_aqi import pepc_calculate_aqi, pepc_composite_aqi, pepc_get_color
     from src.domain.math.qc import temporal_qc_clean
     from src.domain.math.projection import equirectangular_project
     ```
   - This ensures all E2E tests execute the real production domain logic.
2. **Rewrite Tautological Scenarios in `test_tier4_real_world_scenarios.py`**:
   - Scenario 2: Test real `FallbackTemplateEngine` from `src.pipelines.fallback_engine` rather than an inline mock function.
   - Scenario 4: Call `calculate_border_normal_flux` from `src.domain.math.transboundary`.
   - Scenario 5: Call `calculate_pooled_p75` from `src.domain.math.cpf`.

### Phase 4: Fix Concurrent Dynamic CSV Station Catalog Ingestion
1. **Update Station Catalog Updating in `src/services/ingestion_service.py` / `BaselineRepository`**:
   - When a user uploads a valid CSV with dynamic stations, ensure the stations are committed to the repository's thread-safe station index with a thread lock so that `GET /api/v1/meta/stations` immediately reflects newly added stations.
2. **Isolate Concurrent Tests**:
   - Ensure `test_concurrent_reads_and_dynamic_csv_mutations` operates on an isolated/cloned repository fixture rather than mutating shared baseline state.

### Phase 5: Update `run_all_tests.py` and `TEST_READY.md`
1. Include Tier 5 (`test_tier5_adversarial_hardening_api.py`, `test_tier5_adversarial_hardening_domain.py`) in `run_all_tests.py`.
2. Add unit and integration test verification gates.
3. Update `TEST_READY.md` with true, uncompromised test metrics.
