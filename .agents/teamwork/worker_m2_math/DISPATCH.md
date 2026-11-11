## 2026-11-10T13:18:40Z
[Message] timestamp=2026-11-10T13:18:40Z sender=dfe9ab49-5b73-4c71-b636-dccdcc9080ee priority=MESSAGE_PRIORITY_HIGH content=You are worker_m2_math (Archetype: teamwork_worker). Your working directory is c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\worker_m2_math\

MANDATORY FIRST STEP: Read the following authoritative documents before writing any code:
1. c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\ORIGINAL_REQUEST.md
2. c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\orchestrator\PROJECT.md
3. c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\spec_miner_math\handoff.md
4. docs/TRANSFORMATION_LOGIC_SPEC.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

OBJECTIVE:
Implement Milestone M2: Scientific Transformation Engine.
Create clean architecture domain models and pure mathematical transformation functions with zero framework dependencies (Python standard library and numpy only). Pair them with comprehensive, deterministic unit tests matching all formulas, edge cases, and numerical test fixtures from docs/TRANSFORMATION_LOGIC_SPEC.md and spec_miner_math/handoff.md.

EXCLUSIVE FILE OWNERSHIP:
- src/domain/__init__.py
- src/domain/entities/__init__.py
- src/domain/entities/models.py
- src/domain/math/__init__.py
- src/domain/math/geodesy.py (Haversine distance, bearings, angular divergence, sector mapping)
- src/domain/math/wind.py (polar-to-cartesian (u, v), cartesian-to-polar, anemometer bounds [0, 30 m/s], Wazirabad blacklist)
- src/domain/math/idw.py (T1: discrete geodesic IDW with d0=5km clamp; T2: anisotropic wind-steered 2D continuous IDW with epsilon^2=16.0 px^2, cos(alpha), velocity saturation 1.5 m/s, [0.30, 1.70] multiplier, [95, 235] opacity taper)
- src/domain/math/cpf.py (T5: 16-sector polar wind rose, 22.5 deg bins, pooled station-hour P75 threshold, calm <0.5 m/s exclusion, small-sample suppression returning None if Nk < 6)
- src/domain/math/flux.py (T6: physical advection transport flux with d <= 180km, delta_theta <= 35 deg, L_S = 100km, STRICTLY disabled for 'AQI'; T7: receptor CPF coupling Omega feedback, 0.25 isotropic fallback, top 60 ranking truncation, net transport balance)
- src/domain/math/transboundary.py (T8: 120km border belt, 39 normal vector nodes dot products, 117 CAMS perimeter nodes)
- src/domain/math/pepc_aqi.py (T9: official PEPC piecewise linear AQI interpolation for PM2.5, PM10, SO2, NO2, O3, CO across continuous half-open intervals, 500 operational cap, composite max(I_PM2.5, I_PM10), 7-stop continuous PEQS RGB ramp)
- src/domain/math/qc.py (T10: Step 0 zero/negative purge, 7h median spike filter (>4M and >3ref), 3h logger hold purge (i >= 2 guard, AQI exempt), 75% completeness rule, sub-hourly continuous lerp)
- src/domain/math/projection.py (T11: Equirectangular Plate Carree with standard parallel 31 deg N, greedy 12-offset AABB collision-free label search with leader lines)
- tests/unit/test_transformations.py
- tests/unit/test_pepc_aqi.py
- tests/unit/test_qc_filters.py

TESTING REQUIREMENTS:
1. Implement rigorous unit tests asserting exact fixtures from spec_miner_math/handoff.md Section 4 (PEPC breakpoints, Lahore-Sheikhupura geodesic distance 22.3583 km, IDW reference 186.7488, flux reference 585.864 ug/(m^2*s), Attock CPF rose with Nk < 6 suppression).
2. Run your unit tests: python -m pytest tests/unit/test_transformations.py tests/unit/test_pepc_aqi.py tests/unit/test_qc_filters.py -v
3. Run the full test suite to ensure 0 regressions: python -m pytest tests/ -v
4. Keep progress.md updated in your working directory with timestamps.
5. When complete, write handoff.md in your working directory following the Handoff Protocol (Observation, Logic Chain, Caveats, Conclusion, Verification Method) and message back.
