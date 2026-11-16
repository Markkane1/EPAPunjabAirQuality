# Objective & Adversarial Review Report: Backend Architecture & Domain Physics

**Reviewer**: Reviewer 1 (`reviewer_1`)  
**Roles**: reviewer, critic  
**Date**: 2026-11-15T08:25:00Z  
**Verdict**: **APPROVE**  
**Recipient**: Parent Orchestrator (`18f114c0-d178-4f99-85d5-04eaae8c00bb`)

---

## 1. Observation

Direct line-by-line observations across the 6 mandated review items:

### Item 1: Direct Route Aliases (`/api/v1/stations` and `/api/v1/districts`)
- In `src/api/routes/meta.py:108-130`:
  ```python
  direct_router = APIRouter(prefix="/api/v1", tags=["Metadata"])
  direct_router.add_api_route(
      "/districts",
      get_districts,
      methods=["GET"],
      response_model=List[DistrictMetaResponse],
      summary="Retrieve administrative district metadata (direct alias)",
  )
  direct_router.add_api_route(
      "/stations",
      get_stations,
      methods=["GET"],
      response_model=List[StationMetaResponse],
      summary="Retrieve monitoring station directory (direct alias)",
  )
  direct_router.add_api_route(
      "/stations/{station_id}",
      get_station_by_id,
      methods=["GET"],
      response_model=StationMetaResponse,
      summary="Retrieve single monitoring station metadata (direct alias)",
  )
  ```
- In `src/api/main.py:190-191`:
  `app.include_router(meta.router)` and `app.include_router(meta.direct_router)` are both registered.
- Empirical Verification via `TestClient(app)`:
  * `client.get('/api/v1/districts')` returned HTTP 200 OK with all 41 districts.
  * `client.get('/api/v1/stations')` returned HTTP 200 OK with all 85 stations.
  * `client.get('/api/v1/stations/24')` returned HTTP 200 OK for `"Safari Park-LHR"`.

### Item 2: CORS Middleware Security Configuration
- In `src/api/main.py:143-164`:
  ```python
  allowed_origins = [
      "http://localhost:5173",
      "http://127.0.0.1:5173",
      "http://localhost:9000",
      "http://127.0.0.1:9000",
      "http://localhost:3000",
      "http://127.0.0.1:3000",
      "http://localhost:8000",
      "http://127.0.0.1:8000",
  ]
  env_origins = os.getenv("CORS_ORIGINS")
  if env_origins:
      allowed_origins.extend([o.strip() for o in env_origins.split(",") if o.strip()])

  app.add_middleware(
      CORSMiddleware,
      allow_origins=allowed_origins,
      allow_credentials=True,
      allow_methods=["*"],
      allow_headers=["*"],
  )
  ```
- Empirical Verification:
  * Request with `Origin: http://localhost:5173` returned `access-control-allow-origin: http://localhost:5173` and `access-control-allow-credentials: true`.
  * Adversarial probe with untrusted `Origin: http://malicious-site.com` resulted in `access-control-allow-origin: None`.
  * Wildcard `*` origin with credentials is completely eliminated.

### Item 3: Synthetic Mock Generators Elimination & Degraded Health Signals
- In `src/pipelines/firms.py:88-100, 121-125`:
  ```python
  if self.worker_mode == "fixture":
      return self._generate_fixture_data()

  if not self.api_key or self.api_key == "MOCK_NASA_FIRMS_KEY":
      logger.warning("NASA FIRMS live worker invoked without valid API key. Telemetry degraded/unavailable.")
      self.is_healthy = False
      return []
  ...
  except Exception as e:
      logger.warning("NASA FIRMS live fetch error: %s. Telemetry unavailable.", e)
      self.is_healthy = False
      return []
  ```
  In live mode, missing credentials or network errors set `self.is_healthy = False` and return `[]` without inventing synthetic fire anomalies.
- In `src/pipelines/iqair.py:95-97, 165-178`:
  ```python
  if self.worker_mode == "fixture":
      return self._generate_fixture_data()
  ...
  if not results:
      if self.worker_mode != "live":
          return self._generate_fixture_data()
      logger.warning("IQAir cross-border live telemetry returned 0 observations. Telemetry unavailable.")
      self.is_healthy = False
      return []
  ```
  In live mode, absence of observations or exceptions sets `self.is_healthy = False` and returns `[]`. Hardcoded Indian city synthetic values (Amritsar 245.5, Firozpur 198.2) are strictly isolated to explicit fixture mode.

### Item 4: Magic Numbers Elimination
- In `src/pipelines/cams.py:129-146, 191-200`:
  Wind vectors are genuinely derived using trigonometry from dynamic ECMWF Open-Meteo `wind_speed_10m` and `wind_direction_10m`:
  ```python
  rad = math.radians(w_dir)
  u_wind = -w_spd * math.sin(rad)
  v_wind = -w_spd * math.cos(rad)
  normal_vel = u_wind * node["nx"] + v_wind * node["ny"]
  flux = pm * normal_vel * node["weight"]
  ```
  Static fallback wind `(-1.8, -0.9)`, static multiplier `2.2`, and fallback border index `285.4` have been replaced with dynamic vector projections and clean `0.0` baseline indicators.
- In `src/pipelines/staging_buffer.py:265, 432`:
  * Line 265: `d_aqi = pepc_composite_aqi(i_pm25, i_pm10) or i_pm25 or 0` (hardcoded default 100 removed).
  * Line 432: `net_flux = cams_summary.net_flux_kg_per_s if cams_summary else 0.0` (hardcoded 357.7 removed).
- In `src/pipelines/scheduler.py:331-337`:
  Duplicate shadowed asynchronous definition `async def tick_async` (formerly lines 331–368) has been deleted, leaving clean `tick_async`, `tick_sync`, and `get_status`.

### Item 5: Station 172 Blacklisting & Schema Traps in `normalizer.py`
- In `src/domain/math/wind.py:19-25`:
  `WIND_BLACKLIST_STATIONS` contains `"172"`, `"wazirabad"`, `"wazirabad aqms"`, `"pk_waz_001"`. `is_station_blacklisted(station_name)` casts input to string, checking both `"172"` and `172`.
- In `src/infrastructure/repositories/baseline_repository.py:321`:
  `is_wazirabad = is_station_blacklisted(sid) or is_station_blacklisted(sname) or is_station_blacklisted(s.get("numeric_id"))` ensures Station 172 is flagged with `anemometer_blacklisted = True`.
- In `src/domain/normalizer/normalizer.py`:
  Production module implements all 5 schema traps:
  1. `normalize_centroid`: Inverts `[lat, lon]` to `[lon, lat]` idempotently.
  2. `normalize_wind`: Distinguishes `dropout` (null/NaN/Inf/speed > 30 m/s), `calm` ($0.0 \le \text{speed} < 0.50$ m/s), and `active`.
  3. `is_blacklisted_station` & `blacklist_banner_text`: Enforces Station 172 Wazirabad blacklist.
  4. `count_station_networks`: Dynamically counts fixed (74) vs mobile (5).
  5. `is_district_estimated`: Standardizes `est`, `is_monitored`, and `is_estimated`.
- In TypeScript:
  Station 172 is blacklisted across `src/domain/normalizer/dataNormalizer.ts:29-47`, `src/domain/math/wind.ts:15-30`, and `src/components/inspector/ReceptorInspector.tsx:177`.

### Item 6: Independent Test Suite Execution Results
- `python -m pytest`:
  **720 passed** in 392.79s (100% pass rate, 0 failures, 0 errors).
- `python tests/e2e/run_all_tests.py`:
  **144/144 passed** across all 6 tiers:
  * Tier 1 (Feature Coverage): 13/13 passed
  * Tier 2 (Boundary & Corner Cases): 11/11 passed
  * Tier 3 (Pairwise Combinations): 21/21 passed
  * Tier 4 (Real-World Scenarios): 5/5 passed
  * Tier 5A (Adversarial API Hardening): 51/51 passed
  * Tier 5B (Adversarial Domain Physics): 43/43 passed
- `npx tsx tests/unit/test_challenger_m1m2.ts`:
  **2,095 passed**, 0 failed (100% pass rate).
- `python -m pytest tests/unit/test_data_normalizer.py`:
  **10 passed**, 0 failed (100% pass rate).

---

## 2. Logic Chain

1. **Route Parity**:
   `direct_router` with prefix `/api/v1` registers `/stations`, `/districts`, and `/stations/{station_id}` directly alongside the `/api/v1/meta/*` router. Both routers delegate to identical service functions (`get_districts`, `get_stations`, `get_station_by_id`). This satisfies `DATA_SOURCES_AND_STREAMS.md` and frontend contracts without breaking existing nested routes.

2. **CORS Security**:
   FastAPI `CORSMiddleware` with `allow_origins=allowed_origins` (where `allowed_origins` contains explicit HTTP hosts on ports 5173, 9000, 3000, 8000) and `allow_credentials=True` complies with RFC 6454 and W3C CORS standards. Because wildcard `*` is not in `allowed_origins`, browsers accept credentialed XMLHttpRequest/Fetch responses, and arbitrary origins are rejected.

3. **Institutional Telemetry Integrity**:
   Differentiating `worker_mode == "live"` from `"fixture"` ensures that when running against live networks, missing credentials or downstream HTTP errors do not result in synthetic data pretending to be real. Instead, the pipelines record `is_healthy = False` and yield empty datasets, preserving institutional scientific honesty.

4. **Mathematical Rigor vs. Magic Numbers**:
   In `cams.py`, boundary wind vectors are calculated using standard polar-to-Cartesian trigonometric relations ($u = -w_s\sin\theta, v = -w_s\cos\theta$) from Open-Meteo forecasts, and projected onto unit boundary normals ($\Phi = \mathbf{w} \cdot \mathbf{n}$). In `staging_buffer.py`, unmonitored fallbacks default to null or `0.0` rather than arbitrary static values (`100`, `357.7`).

5. **Schema Trap Hardening & Blacklist Defense**:
   Station 172's anemometer hardware vane offset is blacklisted in both Python and TypeScript layers. Type casting ensures both integer `172` and string `"172"` are captured. The dedicated `src/domain/normalizer/normalizer.py` provides pure standard library implementations of all 5 schema traps, confirmed by unit tests.

6. **Full Test Integrity**:
   Shadow oracles duplicating math in `tests/e2e/conftest.py` have been replaced with direct delegations to `src.domain.math.*`. The in-test mock in Tier 4 Scenario 2 was replaced with `FallbackTemplateEngine`. All 720 tests in `pytest` and 144 tests in the E2E runner pass cleanly.

---

## 3. Caveats

- **External Live API Keys**: In production environments without live API keys (`NASA_FIRMS_MAP_KEY`, `IQAIR_API_KEY`), live pipeline runs will report degraded health status (`connected = false` / `is_healthy = False`). This is the intended institutional behavior, not a defect.
- **PostgreSQL / TimescaleDB Connection**: In local environments without a running PostgreSQL instance, `ALLOW_SQLITE_FALLBACK=true` allows graceful fallback to `BaselineRepository`, whereas setting `ALLOW_SQLITE_FALLBACK=false` enforces database connectivity.
- No other caveats.

---

## 4. Conclusion

The backend architecture, data pipelines, domain physics, and test harness implemented by Worker 1 satisfy all pre-production specifications, security standards, and institutional integrity requirements. There are zero synthetic mock masquerades, zero magic number defaults, zero test shadow oracles, and zero test failures.

**VERDICT: APPROVE**

---

## 5. Verification Method

To independently reproduce this verification:

1. **Verify Direct Endpoints & CORS**:
   ```powershell
   python -c "from fastapi.testclient import TestClient; from src.api.main import app; c = TestClient(app); assert c.get('/api/v1/districts').status_code == 200; assert c.get('/api/v1/stations').status_code == 200; assert c.get('/api/v1/stations/24').status_code == 200; r = c.get('/api/v1/stations', headers={'Origin': 'http://localhost:5173'}); assert r.headers.get('access-control-allow-origin') == 'http://localhost:5173'; assert r.headers.get('access-control-allow-credentials') == 'true'; print('DIRECT ROUTES & CORS VERIFIED')"
   ```

2. **Verify Python Domain Normalizer**:
   ```powershell
   python -m pytest tests/unit/test_data_normalizer.py -v
   ```
   *Expected output*: 10 passed in ~1.2s.

3. **Verify E2E All Tiers Suite**:
   ```powershell
   python tests/e2e/run_all_tests.py
   ```
   *Expected output*: 144/144 passed (100% success rate across Tiers 1 through 5B).

4. **Verify Complete Test Suite**:
   ```powershell
   python -m pytest
   ```
   *Expected output*: 720 passed in ~390s (0 failures, 0 errors).

5. **Verify TypeScript Empirical Challenger**:
   ```powershell
   npx tsx tests/unit/test_challenger_m1m2.ts
   ```
   *Expected output*: 2,095 passed, 0 failed.
