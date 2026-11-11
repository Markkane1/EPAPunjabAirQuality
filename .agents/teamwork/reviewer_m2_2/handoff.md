# Milestone M2 Independent Review & Adversarial Quality Report

**Document ID**: `PAQ-HANDOFF-M2-REVIEW-2`  
**Reviewer Agent**: `reviewer_m2_2` (Archetype: `teamwork_reviewer`, Roles: `reviewer`, `critic`)  
**Working Directory**: `c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\reviewer_m2_2\`  
**Target Reviewed Work**: Milestone M2 (Scientific Transformation Engine) implemented by `worker_m2_math`  
**Target Files Inspected**:
- `src/domain/entities/models.py`
- `src/domain/math/geodesy.py`
- `src/domain/math/wind.py`
- `src/domain/math/idw.py`
- `src/domain/math/cpf.py`
- `src/domain/math/flux.py`
- `src/domain/math/transboundary.py`
- `src/domain/math/pepc_aqi.py`
- `src/domain/math/qc.py`
- `src/domain/math/projection.py`
- `tests/unit/test_transformations.py`
- `tests/unit/test_pepc_aqi.py`
- `tests/unit/test_qc_filters.py`
- `tests/e2e/test_tier1_feature_coverage.py`
- `tests/e2e/test_tier2_boundary_corner.py`
- `tests/e2e/conftest.py`  
**Date**: 2026-11-10T13:42:00Z  
**Verdict**: **REQUEST_CHANGES**

---

## 1. Observation

### 1.1 Direct Code Inspection
1. **Authoritative Contracts & Numerical Guards**:
   - `docs/TRANSFORMATION_LOGIC_SPEC.md` §2.1.2 defines Haversine distance with great-circle metric $R=6371\text{ km}$, power $p=2$, and singularity clamping $d_0 = 5.0\text{ km}$.
   - `src/domain/math/geodesy.py` lines 46–49:
     ```python
     a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * (math.sin(dlam / 2.0) ** 2)
     # Clamp argument to asin to [0.0, 1.0] for numerical stability
     c = 2.0 * math.asin(math.sqrt(max(0.0, min(1.0, a))))
     return r_earth * c
     ```
     Observed: `asin` argument is strictly clamped to $[0.0, 1.0]$, preventing `ValueError: math domain error` on antipodal points.
   - `src/domain/math/idw.py` lines 78–82:
     ```python
     dist = haversine_distance(t_lat, t_lon, s_lat, s_lon)
     d_eff = max(dist, d0)
     weight = 1.0 / (d_eff ** power)
     ```
     Observed: $d_0 = 5.0\text{ km}$ clamping is properly enforced for $d=0$ coincident points.
   - `src/domain/math/idw.py` lines 246–248:
     ```python
     psi = 1.0 + 0.70 * cos_alpha * sat
     mult = max(MIN_ANISOTROPIC_MULTIPLIER, psi)
     weight = w0 * mult
     ```
     Observed: While `MIN_ANISOTROPIC_MULTIPLIER = 0.30` is enforced via `max(0.30, psi)`, `MAX_ANISOTROPIC_MULTIPLIER = 1.70` (declared in line 20) is not applied as an upper ceiling clamp (`min(1.70, ...)` is omitted).

2. **Physical Dimension Restrictions**:
   - `src/domain/math/flux.py` lines 68–69:
     ```python
     if not pollutant or pollutant.strip().upper() == "AQI":
         return None  # Physical dimension guard
     ```
     Observed: Physical advection mass flux is strictly disabled for dimensionless ordinal `'AQI'` across case variations.
   - `src/domain/math/flux.py` line 121:
     ```python
     if w_speed < CALM_WIND_THRESHOLD_MS:
         return None  # Aerodynamic calm cutoff
     ```
     Observed: Winds $<0.5\text{ m/s}$ are excluded.
   - `src/domain/math/wind.py` lines 19–37, 66–67:
     ```python
     WIND_BLACKLIST_STATIONS: Set[str] = {
         "wazirabad", "wazirabad aqms", "pk_waz_001", "wazirabad station",
     }
     if is_station_blacklisted(station_name):
         return False
     ```
     Observed: Anemometer station `"Wazirabad"` is unconditionally blacklisted due to the $140^\circ$ physical installation misalignment.

3. **Temporal QC 3-Hour Logger Hold Filter**:
   - `src/domain/math/qc.py` lines 96–104:
     ```python
     # Step 2: 3-Hour Logger Hold (Sensor Freeze) Filter with Index Guard (i >= 2)
     # Physical pollutants only; dimensionless integer 'AQI' is exempt
     if pollutant.strip().upper() != "AQI":
         for i in range(2, n):
             v0 = cleaned[i]
             v1 = cleaned[i - 1]
             v2 = cleaned[i - 2]
             if v0 is not None and v1 is not None and v2 is not None:
                 if v0 == v1 == v2:
                     cleaned[i] = None
     ```
     Observed: The loop modifies `cleaned` **in-place** while iterating forward through $i$.
     Observed Execution Result: When evaluated on an array representing a 5-hour sustained logger hold:
     `series = [50.0, 50.0, 50.0, 50.0, 50.0]`
     `temporal_qc_clean(series, 35.0, "PM2.5")` returns:
     `[50.0, 50.0, None, 50.0, 50.0]`
     At $i=2$, `cleaned[2]` becomes `None`. At $i=3$, `v1 = cleaned[2]` is `None`, so `v0 == v1 == v2` fails. Thus `cleaned[3]` remains `50.0`. At $i=4$, `v2 = cleaned[2]` is `None`, so `cleaned[4]` remains `50.0`.
     Observed Legacy Reference (`original System/index.html` lines 323–327):
     ```javascript
     const full=base.concat(rawv), out=rawv.slice();
     for(let k=0;k<rawv.length;k++){ const i=N0+k, v=full[i]; if(v==null) continue;
       const hold=p!=='AQI'&&full[i-1]===v&&full[i-2]===v;
       if(spk||hold){ out[k]=null; ... } }
     ```
     In the reference system, `full` is immutable. Every frozen reading after the initial 2 hours ($k=2, 3, 4$) evaluates to `full[i-1] === 50 && full[i-2] === 50 && v === 50` and is set to `null` in `out`.

4. **Test Suite Execution**:
   - Command: `python -m pytest tests/unit/test_transformations.py tests/unit/test_pepc_aqi.py tests/unit/test_qc_filters.py -v`
     - Result: `85 passed, 1 warning in 0.14s` (Exit code 0)
   - Command: `python -m pytest tests/ -v`
     - Result: `177 passed, 1 warning in 1.54s` (Exit code 0)
   - Command: `python tests/e2e/run_all_tests.py`
     - Result: `50/50 passed in 1.863s` (Exit code 0)
   - Test Coverage Inspection in `tests/unit/test_qc_filters.py` line 90:
     ```python
     series = [45.0, 50.0, 50.0, 50.0, 60.0]
     ```
     Both `test_qc_filters.py` and `tests/e2e/test_tier2_boundary_corner.py:224` only tested series with **exactly three** consecutive identical values followed by a different value (`60.0`). Neither test suite included 4 or 5 consecutive identical values, which masked the in-place mutation defect.

5. **Integrity Violation Inspection**:
   - Examined `geodesy.py`, `wind.py`, `idw.py`, `cpf.py`, `flux.py`, `pepc_aqi.py`, `qc.py`, `projection.py`.
   - Hardcoded test outputs: **None found**. All functions evaluate equations dynamically.
   - Facade or dummy implementations: **None found**. Full domain mathematics implemented.
   - External tool shortcuts: **None found**. Pure Python standard library and numpy.
   - Fabricated verification outputs: **None found**. Tests run genuinely and produce reproducible results.

---

## 2. Logic Chain

1. **Verification of Core Implementations**:
   - The worker correctly implemented 10 of the 11 scientific transformations with high fidelity, pure mathematical formulas, and clean architecture isolation (`src/domain/entities/models.py` and `src/domain/math/*.py`).
   - Numerical stability guards (asin clamping, Haversine $d_0=5\text{ km}$, calm wind threshold $0.5\text{ m/s}$, Wazirabad $140^\circ$ blacklist, AQI physical flux disable, PEPC continuous half-open intervals and 500 cap) are all present and operational.

2. **Analysis of the Step 2 Hold Filter Defect**:
   - `docs/TRANSFORMATION_LOGIC_SPEC.md` §2.10.1 line 457 mandates:
     $$\text{For } i \ge 2 \text{ and } p \ne \text{'AQI'}: \quad \text{If } v_i = v_{i-1} = v_{i-2} \land v_i \ne \text{null} \implies v_i = \text{null}$$
   - When a physical sensor freezes (e.g. ADC lockup or serial communication hang), it outputs a constant value indefinitely across multiple consecutive hours ($H \ge 3$).
   - Because `src/domain/math/qc.py` modifies the array in-place, nulling index $i=2$ breaks the condition `cleaned[i-1] != None` for index $i=3$ and index $i=4$.
   - Consequently, for a 5-hour freeze `[50, 50, 50, 50, 50]`, the filter produces `[50, 50, None, 50, 50]`. The frozen sensor data at hours 3 and 4 leaks into downstream aggregations, spatial IDW, and exposure KPIs.
   - This defect was masked because the test suite only tested a 3-hour freeze immediately followed by a transition to a new value (`[45, 50, 50, 50, 60]`).

3. **Impact on Production Integrity**:
   - While not an integrity violation (it is an honest implementation bug, not cheating), leaving a flawed QC filter in place would allow invalid flatline data to pollute downstream pipelines (Milestones M3 and M4).
   - Therefore, engineering quality requires requesting changes before Milestone M2 is certified.

---

## 3. Findings

### Finding 1: [Major] In-place mutation in 3-Hour Logger Hold Filter allows sustained sensor freezes ($>3$ hours) to leak through
- **What**: In `src/domain/math/qc.py` lines 97–104, Step 2 mutates `cleaned[i] = None` in-place while iterating forward. For a sensor freeze of 4 or more hours, nulling index 2 breaks the `v1 is not None and v2 is not None` condition for index 3 and 4, causing subsequent frozen readings to be preserved.
- **Where**: `src/domain/math/qc.py`, lines 97–104
- **Why**: A 5-hour freeze `[50.0, 50.0, 50.0, 50.0, 50.0]` produces `[50.0, 50.0, None, 50.0, 50.0]`. 66% of the frozen data leaks through, defeating the physical sensor hold filter.
- **Suggestion**: Use an immutable snapshot of the pre-hold array before entering the loop:
  ```python
  if pollutant.strip().upper() != "AQI":
      pre_hold = list(cleaned)
      for i in range(2, n):
          v0 = pre_hold[i]
          v1 = pre_hold[i - 1]
          v2 = pre_hold[i - 2]
          if v0 is not None and v1 is not None and v2 is not None:
              if v0 == v1 == v2:
                  cleaned[i] = None
  ```
  This ensures that for any freeze of length $K \ge 3$, all indices from $i=2$ to $K-1$ are purged to `None`.

### Finding 2: [Minor] Missing test coverage for sustained logger holds in unit tests
- **What**: `tests/unit/test_qc_filters.py:90` only tests a 3-hour hold `[45.0, 50.0, 50.0, 50.0, 60.0]`.
- **Where**: `tests/unit/test_qc_filters.py`, line 90
- **Why**: Failed to test sustained holds ($\ge 4$ or $\ge 5$ hours), masking Finding 1.
- **Suggestion**: Add a test case with 4 and 5 consecutive identical values asserting `[50.0, 50.0, 50.0, 50.0, 50.0] -> [50.0, 50.0, None, None, None]`.

### Finding 3: [Minor] Declared `MAX_ANISOTROPIC_MULTIPLIER` is unused in `idw.py`
- **What**: In `src/domain/math/idw.py`, line 20 declares `MAX_ANISOTROPIC_MULTIPLIER: float = 1.70`, but line 247 only applies `mult = max(MIN_ANISOTROPIC_MULTIPLIER, psi)`.
- **Where**: `src/domain/math/idw.py`, lines 20, 247
- **Why**: Upper bound is not explicitly clamped, risking potential float precision drift above 1.70.
- **Suggestion**: Change to `mult = min(MAX_ANISOTROPIC_MULTIPLIER, max(MIN_ANISOTROPIC_MULTIPLIER, psi))`.

---

## 4. Verified Claims

| Feature / Subsystem | Claimed Property | Verification Method | Result |
|---|---|---|---|
| Geodesy | Haversine distance, bearings, asin clamping | `test_transformations.py`, python CLI | PASS |
| Discrete IDW (T1) | $d_0=5\text{ km}$ clamp, 186.7488 fixture | `test_transformations.py:212` | PASS |
| Anisotropic IDW (T2) | $[95, 235]$ opacity, directional weighting | `test_transformations.py:249` | PASS |
| Wind Kinematics (T4) | Polar-to-Cartesian, bounds, Wazirabad blacklist | `test_transformations.py:138` | PASS |
| CPF Wind Rose (T5) | 16 sectors, calm $<0.5\text{ m/s}$ exclusion, $N_k < 6$ suppression | `test_transformations.py:285` | PASS |
| Advection Flux (T6) | Physical mass flux, $585.864$ fixture, $35^\circ$ cone, $180\text{ km}$ limit | `test_transformations.py:367` | PASS |
| Advection Flux Guard | Disabled for `'AQI'` | `test_transformations.py:410` | PASS |
| Receptor Coupling (T7) | $\Omega = 0.25$ isotropic fallback, top 60 truncation | `test_transformations.py:452` | PASS |
| Transboundary (T8) | 120km belt, 39 normal vector nodes | `test_transformations.py:490` | PASS |
| PEPC AQI (T9) | Continuous half-open intervals, 500 cap, particulate max composite | `test_pepc_aqi.py:21` (36 fixtures) | PASS |
| Temporal QC (T10) | Zero/negative purge, 7h median spike filter, lerp | `test_qc_filters.py:21` | PASS |
| Temporal QC (T10) | 3h hold filter index guard $i \ge 2$, AQI exemption | `test_qc_filters.py:82` | PASS |
| Temporal QC (T10) | 3h hold filter on sustained holds ($>3$ consecutive hours) | Adversarial stress test | **FAIL** (Finding 1) |

---

## 5. Caveats

1. **Scope of Rejection**: The vast majority (10 of 11 modules) of the scientific transformation engine is implemented with exceptional mathematical accuracy and passes 177 automated tests. The rejection is specifically scoped to the in-place mutation flaw in Step 2 of `src/domain/math/qc.py` and its accompanying test coverage in `tests/unit/test_qc_filters.py`.
2. **Framework Isolation**: Zero framework dependencies exist in `src/domain/math/`, which conforms strictly to Clean Architecture.

---

## 6. Conclusion

The implementation of Milestone M2 (Scientific Transformation Engine) exhibits strong mathematical foundation and clean architectural boundaries. There are no integrity violations or shortcut facades. However, adversarial challenge testing uncovered a functional bug in `src/domain/math/qc.py` where in-place array mutation during the 3-hour logger hold filter allows sustained sensor freeze events ($>3$ consecutive hours) to leak through as valid data.

**Verdict**: **REQUEST_CHANGES**

**Action Items for Worker**:
1. Update `src/domain/math/qc.py` Step 2 to use an immutable snapshot `pre_hold = list(cleaned)` so that sustained holds of 4, 5, or more consecutive identical values have all hours from index 2 onward purged to `None`.
2. In `src/domain/math/idw.py` line 247, apply the explicit upper clamp `min(MAX_ANISOTROPIC_MULTIPLIER, ...)`.
3. In `tests/unit/test_qc_filters.py`, add explicit test cases testing 4 and 5 consecutive identical values to verify that all subsequent frozen hours are purged.

---

## 7. Verification Method

To verify the issue and confirm its resolution once changes are applied:

1. **Reproduce the Defect**:
   ```bash
   python -c "
   from src.domain.math.qc import temporal_qc_clean
   series = [50.0, 50.0, 50.0, 50.0, 50.0]
   cleaned, _ = temporal_qc_clean(series, ref_limit=35.0, pollutant='PM2.5')
   print('Current Output:', cleaned)
   assert cleaned == [50.0, 50.0, None, None, None], 'Failed to purge sustained hold!'
   "
   ```
   *Expected on current code: AssertionError (`cleaned` equals `[50.0, 50.0, None, 50.0, 50.0]`).*
   *Expected after fix: Clean pass with `[50.0, 50.0, None, None, None]`.*

2. **Run Unit and E2E Suites**:
   ```bash
   python -m pytest tests/unit/test_qc_filters.py -v
   python -m pytest tests/ -v
   python tests/e2e/run_all_tests.py
   ```
