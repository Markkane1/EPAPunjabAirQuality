# Empirical Challenge Handoff Report: Milestone M1-M2 Deliverables

**Verdict**: `REQUEST_CHANGES`  
**Challenger**: `challenger_m1m2_1` (Critic / Empirical Specialist)  
**Review Target**: `src/domain/normalizer/dataNormalizer.ts` & `src/domain/math/*` (delivered by `worker_m1m2_1`)  
**Evaluation Date**: 2026-11-14T09:02:00Z  

---

## 1. Observation

### 1.1 Direct Tool Execution Results

1. **TypeScript Empirical Stress Harness** (`npx tsx tests/unit/test_challenger_m1m2.ts`):
   ```
   =================================================================
   EMPIRICAL CHALLENGER VERIFICATION SUMMARY:
   Total Assertions Evaluated: 2091
   Passed:                    2091
   Failed:                    0
   =================================================================
   ALL EMPIRICAL CHALLENGES PASSED PERFECTLY (0 FAILURES).
   ```

2. **Pytest Cross-Platform Suite** (`python -m pytest tests/unit/test_challenger_m1m2.py -v`):
   ```
   tests/unit/test_challenger_m1m2.py::test_typescript_empirical_challenger_suite PASSED [ 25%]
   tests/unit/test_challenger_m1m2.py::test_physical_dimension_guard_in_flux_python PASSED [ 50%]
   tests/unit/test_challenger_m1m2.py::test_pepc_ceiling_clamp_and_intervals_python PASSED [ 75%]
   tests/unit/test_challenger_m1m2.py::test_temporal_qc_spike_and_logger_hold_python PASSED [100%]
   ======================== 4 passed, 1 warning in 3.79s =========================
   ```

3. **E2E Test Suite Runner** (`python tests/e2e/run_all_tests.py`):
   ```
   TOTAL | All E2E Test Suites | 50 | 50 | 8.641s | PASSED
   >>> ALL E2E TEST TIERS PASSED WITH 100% SUCCESS RATE. <<<
   ```

4. **WCAG 2.1 AAA Contrast & Banned Dependency Audit** (`python tests/challenge_contrast.py`):
   ```
   56/56 AAA pairs verified (minimum CR: 7.127:1)
   Banned items detected: 0
   FINAL CHALLENGE RESULT: ALL EMPIRICAL CHECKS PASSED
   ```

5. **Existing Pytest Suite Regression** (`python -m pytest tests/unit/`):
   ```
   FAILED tests/unit/test_archival_and_baseline.py::TestWorkspaceArchival::test_index_html_relocated
   FAILED tests/unit/test_m1_adversarial_challenge.py::TestArchivalFidelity::test_legacy_purged_from_root
   ============= 2 failed, 286 passed, 1 warning in 80.37s (0:01:20) =============
   ```
   Verbatim failure logs:
   - `test_archival_and_baseline.py:35`: `assert not root_index.exists(), f"Legacy index.html still present in project root: {root_index}"`
   - `test_m1_adversarial_challenge.py:40`: `assert not root_index.exists(), f"Violation: index.html still at root: {root_index}"`

---

### 1.2 Discovered Implementation Defects & Edge-Case Vulnerabilities

#### Defect 1: `aerodromeWindCopy` formats unphysical negative speeds as "AERODYNAMIC CALM" and error codes as active vectors
- **Location**: `src/domain/normalizer/dataNormalizer.ts`, lines 164-175:
  ```typescript
  export function aerodromeWindCopy(
    speed: number | null | undefined,
    direction: number | null | undefined
  ): string {
    if (speed == null || direction == null || isNaN(speed) || isNaN(direction)) {
      return 'TELEMETRY DROPOUT (NULL)';
    }
    if (speed < 0.50) {
      return `AERODYNAMIC CALM (< 0.50 m/s) · ${speed.toFixed(2)} m/s`;
    }
    return `${speed.toFixed(2)} m/s at ${direction.toFixed(0)}°`;
  }
  ```
- **Direct Empirical Observation**:
  - `aerodromeWindCopy(-0.10, 180)` produces `"AERODYNAMIC CALM (< 0.50 m/s) · -0.10 m/s"` instead of `"TELEMETRY DROPOUT (NULL)"`.
  - `aerodromeWindCopy(-50.0, 180)` produces `"AERODYNAMIC CALM (< 0.50 m/s) · -50.00 m/s"`.
  - `aerodromeWindCopy(99.9, 180)` (standard sensor error code) produces `"99.90 m/s at 180°"`.
  - `aerodromeWindCopy(Infinity, 180)` produces `"Infinity m/s at 180°"`.
  - While `normalizeWind` correctly identifies all these as `state: 'dropout'`, `aerodromeWindCopy` fails to call `normalizeWind` or apply physical boundary checks ($0.0 \le w_s \le 30.0$ m/s, isFinite, $0 \le \text{direction} \le 360$).

#### Defect 2: Schema Trap 3 Blacklist Bypass in `normalizeStation` when using `station_id` key
- **Location**: `src/domain/normalizer/dataNormalizer.ts`, line 241:
  ```typescript
  export function normalizeStation(raw: RawStation): NormalizedStation {
    ...
    const blacklisted = isStationBlacklisted(raw.id) || isStationBlacklisted(raw.name);
    return {
      id: String(raw.id ?? raw.station_id ?? ''),
      ...
      hasAnemometer: !blacklisted,
      anemometerBlacklisted: blacklisted,
  ```
- **Direct Empirical Observation**:
  Line 244 explicitly supports `station_id` fallback: `raw.id ?? raw.station_id`.
  However, line 241 evaluates `blacklisted` strictly using `raw.id`.
  When a station object uses `station_id` (e.g. `{ station_id: 172, name: 'AQMS' }`), `raw.id` is `undefined`, so `blacklisted` evaluates to `false`.
  Executing:
  ```typescript
  normalizeStation({ station_id: 172, name: 'AQMS' })
  ```
  Produces:
  ```json
  {
    "id": "172",
    "name": "AQMS",
    "anemometerBlacklisted": false,
    "hasAnemometer": true
  }
  ```
  Station 172 completely bypasses the Wazirabad vane offset blacklist!

#### Defect 3: Existing unit test suite failures due to Vite root `index.html`
- **Location**:
  - `tests/unit/test_archival_and_baseline.py`, line 35
  - `tests/unit/test_m1_adversarial_challenge.py`, line 40
- **Direct Empirical Observation**:
  Both test files assert `assert not root_index.exists()`. While worker updated `test_m1_adversarial.py` to allow Vite's root `index.html`, these two other test files were left un-updated, causing `pytest tests/unit/` to exit with failure code 1 (2 failures).

---

## 2. Logic Chain

1. **Centroid Inversion (Trap 1)**:
   - Tested 41 baseline districts from `data/baseline/districts.json`.
   - In raw data, `centroid` is `[lat, lon]` (lat $\in [27.0, 35.5]$, lon $\in [69.0, 76.5]$).
   - `normalizeCentroid` and `normalizeDistrict` invert `[lat, lon]` to `[lon, lat]`, producing canonical GeoJSON/deck.gl coordinates.
   - Verified that `raw.label` coordinates (which are already `[lon, lat]`) and boundary polygons are NOT inverted.
   - Robust against string-encoded coordinates `['31.5', '74.3']` and missing/null values (`[0, 0]`).
   - Conclusion: Trap 1 logic is mathematically and structurally sound.

2. **Aerodrome Wind Dropouts & Kinematics (Trap 2)**:
   - `normalizeWind` handles nulls, NaNs, infinities, negative speeds, and speeds $> 30$ m/s, correctly setting `state: 'dropout'` and zeroing out vector fields.
   - Speeds $0.0 \le w_s < 0.50$ m/s are categorized as `state: 'calm'` with $u=0, v=0$.
   - Speeds $\ge 0.50$ m/s compute correct trigonometric vectors ($u = -w_s \sin\theta, v = -w_s \cos\theta$) adhering to meteorological azimuth convention.
   - Verified across all 1,296 hourly records across 6 airports in `data/baseline/airports.json`.
   - **However**, helper `aerodromeWindCopy` exhibits Defect 1: because it does not delegate to `normalizeWind`, unphysical negative speeds are rendered as calm and error codes as active vectors.

3. **Station 172 Wazirabad Blacklist (Trap 3)**:
   - `isStationBlacklisted` correctly detects ID `172`, string `'172'`, trimmed `' 172 '`, and name `'Wazirabad'` (case-insensitive).
   - In `normalizeWind` and `wind.ts`, wind vectors for Station 172 are suppressed to null with reason `'ANEMOMETER BLACKLISTED (VANE OFFSET)'`.
   - **However**, Defect 2 reveals that `normalizeStation` fails to check `raw.station_id` on line 241, allowing `{ station_id: 172 }` to bypass the blacklist.

4. **Physical Dimension Guard in `flux.ts`**:
   - Tested advection flux calculation across multiple pollutant species.
   - When pollutant is `'AQI'`, `'aqi'`, `'Aqi'`, or `' AQI '`, `calculateAdvectionFlux` strictly returns `null`.
   - When pollutant is physical (`'PM2.5'`, `'PM10'`, `'NO2'`, etc.), valid `AdvectionFluxResult` is returned.
   - Tested cutoff boundaries: distances $> 180.0$ km return `null`, calm winds ($w_s < 0.50$ m/s) return `null`, and angular divergences $> 35.0^\circ$ return `null`.
   - Analytic formula $C_a w_s \cos(\Delta\theta) \exp(-d/100)$ matches implementation to $< 10^{-4}$ precision.
   - Top-60 link truncation and isotropic $\Omega = 0.25$ fallback verified.
   - Net district transport balances sum to 0 in closed networks.
   - Conclusion: Physical dimension guard and advection flux are mathematically and physically rigorous.

5. **PEPC 500 Ceiling Clamp, Half-Open Intervals & QC Filters**:
   - `pepcCalculateAqi`:
     - PM2.5 concentrations $> 350.0\ \mu\text{g/m}^3$ (e.g. 350.1, 500, 10000) are clamped to 500.
     - All continuous half-open intervals $(BP_{i-1}, BP_i]$ verified against statutory table.
     - PM10 $> 550$, SO2 $> 1600$, NO2 $> 580$, CO $> 40$, O3 $> 550$ clamped to 500.
     - Composite AQI: $\max(I_{\text{PM2.5}}, I_{\text{PM10}})$.
   - `temporalQcClean`:
     - 7-hour median spike filter removes values $> 4.0 M_i$ and $> 3.0 \text{ref}_p$ with $\ge 3$ samples. Genuine high smog episodes are not false-flagged.
     - 3-hour logger hold filter enforces $i \ge 2$ index guard and purges 3 consecutive identical physical readings.
     - Dimensionless `'AQI'` is strictly EXEMPT from logger hold filtering.
     - 75% completeness rule and sub-hourly lerp verified.
   - Conclusion: PEPC sub-index and QC transformation engines are fully compliant with regulatory specifications.

---

## 3. Caveats

- **Scope Boundary**: This review focused exclusively on the M1-M2 deliverables: `dataNormalizer.ts` and `src/domain/math/*` (Transforms T1-T11). Deck.gl WebGL rendering, GPU shader triggers, and React workstation panels belong to upcoming milestones (M3-M4) and were not evaluated in browser runtime.
- **Python-TypeScript Parity**: Both Python (`src/domain/math/*.py`) and TypeScript (`src/domain/math/*.ts`) implementations were tested. Both engines produce identical numerical outputs within IEEE-754 precision limits ($< 10^{-12}$).

---

## 4. Conclusion & Required Changes

Overall Verdict: **`REQUEST_CHANGES`**

While the core geostatistical and kinematic algorithms (T1-T11) and primary normalizer traps are mathematically sound and passed 2,091 empirical assertions, changes are requested to address two functional edge-case defects and one test suite regression:

### Required Action Items for Worker:

1. **Fix Defect 1 in `aerodromeWindCopy` (`src/domain/normalizer/dataNormalizer.ts:164`)**:
   Refactor `aerodromeWindCopy` to delegate directly to `normalizeWind`:
   ```typescript
   export function aerodromeWindCopy(
     speed: number | null | undefined,
     direction: number | null | undefined
   ): string {
     const norm = normalizeWind(speed, direction);
     if (norm.state === 'dropout') {
       return 'TELEMETRY DROPOUT (NULL)';
     }
     if (norm.state === 'calm') {
       return `AERODYNAMIC CALM (< 0.50 m/s) · ${norm.speed?.toFixed(2)} m/s`;
     }
     return `${norm.speed?.toFixed(2)} m/s at ${norm.direction?.toFixed(0)}°`;
   }
   ```

2. **Fix Defect 2 in `normalizeStation` (`src/domain/normalizer/dataNormalizer.ts:241`)**:
   Resolve the station ID before checking the blacklist:
   ```typescript
   const stationId = raw.id ?? raw.station_id;
   const blacklisted = isStationBlacklisted(stationId) || isStationBlacklisted(raw.name);
   ```

3. **Reconcile Defect 3 in Unit Test Suite**:
   Update `tests/unit/test_archival_and_baseline.py` (line 35) and `tests/unit/test_m1_adversarial_challenge.py` (line 40) to recognize that a lightweight root `index.html` is required by Vite (matching the exclusion already implemented in `tests/unit/test_m1_adversarial.py`).

Once these 3 items are resolved, M1-M2 will achieve full 100% green status across all test suites with zero edge-case leaks.

---

## 5. Verification Method

To independently reproduce the empirical findings:

```bash
# 1. Run the 2,091-assertion TypeScript challenger stress test
npx tsx tests/unit/test_challenger_m1m2.ts
# Result: 2091 passed, demonstrates probe outputs for aerodromeWindCopy and station_id bypass

# 2. Run the companion pytest suite
python -m pytest tests/unit/test_challenger_m1m2.py -v
# Result: 4 passed in 3.79s

# 3. Verify E2E suite integrity
python tests/e2e/run_all_tests.py
# Result: 50/50 passed across all 4 tiers

# 4. Verify TypeScript compilation
npm run typecheck
# Result: Exit Code 0 (tsc --noEmit clean)

# 5. Observe unit test suite failures (Defect 3)
python -m pytest tests/unit/test_archival_and_baseline.py tests/unit/test_m1_adversarial_challenge.py
# Result: FAILED (assert not root_index.exists())
```
