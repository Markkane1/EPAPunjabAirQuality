# Handoff Report: Domain Physics, Normalizer & Test Integrity Deep Audit

**Agent**: `explorer_3` (Domain Physics, Normalizer & Test Integrity Auditor)  
**Date**: 2026-11-15T07:27:00Z  
**Type**: Hard Handoff (Investigation & Pre-Production Audit Complete)  
**Recipient**: Orchestrator (`18f114c0-d178-4f99-85d5-04eaae8c00bb`)  
**Associated Detailed Report**: `.agents/teamwork/explorer_3/physics_and_tests_audit_report.md`  

---

## 1. Observation

1. **Station 172 Blacklist Omission in Python**:
   - `src/domain/math/wind.py:19-25`:
     ```python
     WIND_BLACKLIST_STATIONS: Set[str] = {
         "wazirabad",
         "wazirabad aqms",
         "pk_waz_001",
         "wazirabad station",
     }
     ```
     `"172"` and `172` are absent from `WIND_BLACKLIST_STATIONS`. `is_station_blacklisted("172")` returns `False`.
   - `src/domain/math/wind.ts:15-32` and `src/domain/normalizer/dataNormalizer.ts:29-47`:
     Includes `'172'`, `172`, and checks `if (stationName === 172 || stationName === '172') return true;`.
   - `src/infrastructure/repositories/baseline_repository.py:304`:
     Blacklist check is hardcoded as `is_wazirabad = "wazirabad" in sname.lower()`.

2. **Absence of Python Normalizer**:
   - Directory `src/domain/normalizer/` contains only `dataNormalizer.ts` (10,087 bytes). There is **no Python normalizer module** (`normalizer.py` does not exist).

3. **In-Test Duplicate Shadow Oracle in E2E Test Suite**:
   - `tests/e2e/conftest.py:95-428`: Implements a 333-line class `PAQReferenceOracle` defining duplicate versions of Haversine, discrete IDW, polar/Cartesian wind conversion, CPF roses, advection flux, PEPC AQI sub-indices, composite AQI, PEPC color scales, temporal QC filters, and Plate Carrée projection.
   - `tests/e2e/test_tier1_feature_coverage.py:22-100`, `test_tier2_boundary_corner.py:105-144`, and `test_tier3_pairwise_combinations.py:24-80`:
     All import and invoke `reference_oracle: PAQReferenceOracle` from `conftest.py` rather than importing from `src/domain/math/`.

4. **Tautological Tests with In-Test Mocks**:
   - `tests/e2e/test_tier4_real_world_scenarios.py:95-120`:
     Defines an internal function `def fallback_templating_engine(...)` inside the test body and tests that local function. It never calls `src/pipelines/fallback_engine.py`.
   - `tests/unit/test_data_normalizer.py:23-164`:
     Does not import any normalizer from `src/`. All tests perform inline list inversions and dictionary counts directly inside the test methods (e.g. `norm_c = [raw_c[1], raw_c[0]]`).

5. **Test Failures in Full Repository Test Run**:
   - Running the full pytest suite (`python -m pytest`) executes 717 items and produces **6 test failures**:
     - `tests/integration/test_m4_adversarial.py::TestConcurrentRepositoryOperations::test_concurrent_reads_and_dynamic_csv_mutations`:
       Fails with `AssertionError: Missing concurrent station 'CONC_ST_0' from catalog`.
     - 5 cascading failures due to concurrent repository JSON decode corruption (`json.decoder.JSONDecodeError` on `baseline_data.json` during concurrent writes).
   - In contrast, `tests/e2e/run_all_tests.py` selectively runs only Tiers 1–4 (which test `conftest.py`'s `PAQReferenceOracle`) and declared a false 100% pass certification in `TEST_READY.md`.

---

## 2. Logic Chain

1. **Mathematical Invariant Verification**:
   - Comparing the equations in `docs/TRANSFORMATION_LOGIC_SPEC.md` against both Python (`src/domain/math/*.py`) and TypeScript (`src/domain/math/*.ts`) reveals that the core equations for T1, T2, T5, T6, T7, T8, T9, T10, and T11 are implemented with high mathematical precision:
     - T1 uses Haversine with $R = 6371.0\text{ km}$, $p=2$, $d_0=5.0\text{ km}$.
     - T2 uses $\epsilon^2 = 16.0\text{ px}^2$, inverted screen $y$ advection cosine, $1.5\text{ m/s}$ velocity saturation, $[0.30, 1.70]$ multipliers, and $[45, 140]\text{ km}$ opacity taper.
     - T5 uses 16 sectors, $0.50\text{ m/s}$ calm cutoff, pooled $P_{75}$, $N_k < 6$ suppression, and $10.0\text{ px}$ muted stubs.
     - T6 strictly enforces the physical dimension guard (`pollutant === 'AQI' -> None`), $35^\circ$ cone, $180\text{ km}$ distance limit, and $100\text{ km}$ residence decay.
     - T7 enforces top 60 link truncation and $\Omega=0.25$ isotropic fallback.
     - T8 enforces $120\text{ km}$ border corridor, 39 border normal vector dot products ($\pm 0.25\text{ m/s}$ threshold), and excludes estimated districts from regional aggregates.
     - T9 implements continuous half-open intervals $(BP_{i-1}, BP_i]$, operational 500 ceiling cap, particulate-only composite AQI, and 7 statutory hex colors.
     - T10 enforces zero-purge, 7h median spike filter ($>4M$ and $>3\text{ref}$), 3h hold filter with index guard $i \ge 2$ and AQI exemption, 75% completeness rule, and sub-hourly lerp.
     - T11 implements Plate Carrée with standard parallel $31^\circ\text{N}$ ($K_X = \cos 31^\circ$), greedy 12-offset AABB placement, and $20\text{ px}$ leader line detection.

2. **Defect Deduction**:
   - The omission of `"172"` and `172` in `src/domain/math/wind.py:19-25` means any backend pipeline or API query identifying Station 172 by ID rather than display name bypasses the blacklist filter, violating Specification §2.4.0 and Schema Trap 3.
   - The lack of an imported normalizer in `tests/unit/test_data_normalizer.py` means the Python normalizer was never tested; the test merely tested local inline expressions.
   - The duplication of oracle code in `tests/e2e/conftest.py` decouples E2E tests from `src/domain/math/`, allowing implementation code to drift or fail undetected.
   - The failure of `test_concurrent_reads_and_dynamic_csv_mutations` demonstrates that dynamic CSV uploads do not update the station catalog in `station_repo.list_stations()`, and concurrent read/writes to `baseline_data.json` cause `JSONDecodeError`.

---

## 3. Caveats

1. The test execution errors in `test_staging_and_orchestrator.py` and `test_standing_cron_scheduler.py` only occur when run as part of the full suite alongside `test_m4_adversarial.py` (which mutates shared state); when run in isolation, they pass.
2. The TypeScript test harness (`tests/unit/*.ts`) has 100% pass rates across all 6 test scripts (>97,000 assertions evaluated), proving that the TypeScript frontend domain physics and normalizers are strictly compliant.

---

## 4. Conclusion

1. **Domain Physics (T1–T11)**: Pure mathematics is verified sound across both languages, but `src/domain/math/wind.py` requires immediate remediation to add `"172"` and `172` to `WIND_BLACKLIST_STATIONS`.
2. **Schema Traps**: Handled comprehensively in TypeScript (`dataNormalizer.ts`), but Python lacks a dedicated normalizer in `src/domain/normalizer/` and has a Station 172 ID-lookup gap.
3. **Test Integrity**: The E2E test harness (`tests/e2e/`) must be refactored to remove the duplicate `PAQReferenceOracle` in `conftest.py` and import directly from `src/domain/math/`.
4. **Integration Rigor**: The concurrency defect in `POST /api/v1/ingest/csv` station catalog registration must be resolved so that all 717 tests pass with 0 failures across the entire repository.

---

## 5. Verification Method

To independently verify these audit findings:

1. **Verify Station 172 Bug in Python**:
   ```bash
   python -c "from src.domain.math.wind import is_station_blacklisted; print('Station 172 Blacklisted:', is_station_blacklisted('172'))"
   # Output: Station 172 Blacklisted: False  (Defect confirmed!)
   ```
2. **Verify Station 172 in TypeScript**:
   ```bash
   npx tsx -e "import { isStationBlacklisted } from './src/domain/math/wind'; console.log('Station 172:', isStationBlacklisted('172'));"
   # Output: Station 172: true  (Compliant!)
   ```
3. **Verify E2E Test Suite Oracle Duplication**:
   Inspect `tests/e2e/test_tier1_feature_coverage.py:22` and observe that every test uses `reference_oracle: PAQReferenceOracle` defined in `tests/e2e/conftest.py:95`.
4. **Verify Test Failures in Full Repository Suite**:
   ```bash
   python -m pytest -v
   # Observe 6 failures: test_concurrent_reads_and_dynamic_csv_mutations and cascading JSONDecodeErrors
   ```
5. **Verify Isolated Concurrent Mutation Failure**:
   ```bash
   python -m pytest tests/integration/test_m4_adversarial.py -k test_concurrent_reads_and_dynamic_csv_mutations -v
   # Output: FAILED with AssertionError: Missing concurrent station 'CONC_ST_0' from catalog.
   ```
6. **Verify TypeScript Test Suite**:
   ```bash
   npx tsx tests/unit/test_challenger_m1m2.ts
   npx tsx tests/unit/test_challenger_m3m4.ts
   npx tsx tests/unit/test_challenger_m5.ts
   # Output: All empirical challenger tests passed (0 failures)
   ```
