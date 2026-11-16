# Pre-Production Audit Handoff Report: Backend & Data Pipelines

**Agent**: Explorer 1 (Backend & Data Pipelines Auditor)  
**Date**: 2026-11-15  
**Working Directory**: `c:\Users\Asif\Downloads\Punjab Air Quality`  
**State Folder**: `c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\explorer_1`  
**Recipient**: Orchestrator (`18f114c0-d178-4f99-85d5-04eaae8c00bb`) & Worker Agent  

---

## 1. Observation

Direct empirical observations across the codebase, test execution, and authoritative specifications:

1. **Test Suite Verification**:
   - Command: `python -m pytest tests/`
   - Output: `================ 717 passed, 35 warnings in 196.61s (0:03:16) ================`
   - All 717 unit, integration, and E2E tests are green.

2. **NASA FIRMS Active Fires (`src/pipelines/firms.py`)**:
   - Lines 93–94:
     ```python
     if self.worker_mode != "live" or not self.map_key:
         return self._generate_fixture_data()
     ```
   - Lines 201–214: `_generate_fixture_data()` generates static synthetic detections with hardcoded coordinates (`latitude: 31.55, longitude: 74.35`, FRP `38.5`, etc.).

3. **IQAir Cross-Border Indian Belt (`src/pipelines/iqair.py`)**:
   - Lines 162 & 166:
     ```python
     except Exception as exc:
         logger.warning(f"Failed to fetch live IQAir data: {exc}. Falling back to fixture dataset.")
         return self._generate_fixture_data()
     ```
   - Lines 235–245: Returns 6 hardcoded Indian border cities with fixed PM2.5 concentrations (Amritsar `128.5`, Firozpur `120.2`, Jalandhar `189.4`, Ludhiana `215.0`, Bathinda `165.8`, Delhi `335.0`).

4. **Copernicus CAMS Boundary Flux (`src/pipelines/cams.py`)**:
   - Lines 129–133:
     ```python
     u_wind = -1.8  # Easterly component (m/s)
     v_wind = -0.9  # Northerly component (m/s)
     pm25_boundary_conc = float(pm25_mean) * 2.2  # Boundary layer concentration multiplier
     ```
   - Line 178: `border_belt_index = float(raw_data.get("border_belt_index", 285.4))` (hardcoded default).

5. **Chronometric Staging Buffer Magic Numbers (`src/pipelines/staging_buffer.py`)**:
   - Line 432:
     ```python
     net_flux = cams_summary.net_flux_kg_per_s if cams_summary else 357.7
     ```
   - Line 265:
     ```python
     d_aqi = pepc_composite_aqi(i_pm25, i_pm10) or i_pm25 or 100
     ```

6. **Missing Top-Level Route Aliases (`src/api/routes/meta.py` vs specifications)**:
   - In `src/api/routes/meta.py` (line 18):
     `router = APIRouter(prefix="/meta", tags=["Metadata"])`
   - Included in `src/api/main.py` (line 183) with prefix `/api/v1/meta`.
   - Result: Only `/api/v1/meta/stations` and `/api/v1/meta/districts` exist. Direct calls to `/api/v1/stations` and `/api/v1/districts` return HTTP 404 Not Found.
   - Authoritative Spec (`DATA_SOURCES_AND_STREAMS.md` §3 and `PROJECT.md` §3) explicitly defines `/api/v1/stations` and `/api/v1/districts`.

7. **CORS Invalidation (`src/api/main.py`)**:
   - Line 146:
     ```python
     app.add_middleware(
         CORSMiddleware,
         allow_origins=["*"],
         allow_credentials=True,
         allow_methods=["*"],
         allow_headers=["*"],
     )
     ```

8. **Duplicate Method in `PipelineOrchestrator` (`src/pipelines/scheduler.py`)**:
   - Lines 150–184: `async def tick_async(self, timestamp: Optional[datetime] = None, mode: Optional[str] = None): ...`
   - Lines 331–368: Duplicate definition of `async def tick_async(self, timestamp: Optional[datetime] = None, mode: Optional[str] = None): ...` which shadows lines 150–184.

---

## 2. Logic Chain

1. **Premise 1 (Mathematical & Storage Rigor)**: Observation 1 confirms that the PEPC AQI formula (Nov 2024 breakpoints), IDW spatial grid calculations, 24h rolling averages, TimescaleDB schema, Redis/FakeRedis caching, and 717 test assertions are functionally green and sound.
2. **Premise 2 (Operational Reality vs Mock Masquerade)**: Observations 2, 3, 4, and 5 show that when external keys are not provided or remote endpoints experience network delays/failures, workers silently return hardcoded static data rather than surfacing accurate pipeline health telemetry. In an institutional operational setting, displaying fixed fires or hardcoded Indian city pollution without a degraded status warning compromises institutional trust.
3. **Premise 3 (API Contract Compliance)**: Observation 6 shows that frontend requests relying on the contract specification `/api/v1/stations` or `/api/v1/districts` fail with 404 because these routes are buried under `/api/v1/meta/`.
4. **Premise 4 (Browser Security Standards)**: Observation 7 violates W3C CORS specifications (wildcard `*` cannot accompany `allow_credentials=True`), causing standard modern browsers to block authenticated XHR/Fetch API requests.
5. **Premise 5 (Code Hygiene)**: Observation 8 causes dead code and shadowing in `PipelineOrchestrator`.
6. **Deduction**: While the project's algorithmic foundation is complete and tested, operational pre-production readiness requires eliminating dummy fallbacks, binding direct API route aliases, correcting CORS origin policies, and resolving duplicate code definitions.

---

## 3. Caveats

- **External Live Credentials**: During this audit, no live commercial NASA FIRMS API key (`FIRMS_MAP_KEY`) or IQAir AirVisual API key was configured in the environment. Tests deliberately ran in simulation/fixture mode or with mock stubs.
- **PostgreSQL / TimescaleDB Engine**: The test suite validates both SQLite in-memory and PostgreSQL on port 5433 (`DATABASE_URL=postgresql+psycopg://postgres@127.0.0.1:5433/punjab_air_quality`). In production environments without a running local PostgreSQL instance, `USE_DATABASE_BACKEND=false` seamlessly engages the baseline repository.
- **Scope Limit**: Frontend React/TypeScript UI visual components were not audited by this explorer (delegated to Explorer 2).

---

## 4. Conclusion

The backend is structurally mature and mathematically rigorous, passing 100% of its 717 automated tests. However, it is **not yet production-clean** due to 4 high-severity operational issues:
1. Synthetic mock data generators masquerading as live responses in FIRMS and IQAir pipelines.
2. Missing direct `/api/v1/stations` and `/api/v1/districts` endpoint aliases.
3. CORS configuration invalidating authenticated browser requests (`allow_origins=["*"]` + `allow_credentials=True`).
4. Hardcoded physics magic numbers in CAMS and staging buffer (`357.7 kg/s` flux, `u=-1.8, v=-0.9` wind, baseline AQI `100`).

Detailed line-by-line findings and the concrete remediation roadmap are documented in:
`c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\explorer_1\backend_audit_report.md`.

---

## 5. Verification Method

To independently verify these findings:

1. **Verify Test Suite**:
   ```powershell
   python -m pytest tests/
   ```
   Must output 717 passed.

2. **Verify Missing Direct Endpoint Aliases**:
   Inspect `src/api/routes/meta.py:18` and `src/api/main.py:183`. Run:
   ```powershell
   python -c "from src.api.main import create_app; app = create_app(); print([r.path for r in app.routes if 'station' in r.path])"
   ```
   Notice that `/api/v1/stations` is absent; only `/api/v1/meta/stations` exists.

3. **Verify CORS Wildcard + Credentials Issue**:
   Inspect `src/api/main.py:146-152`.

4. **Verify Mock Generators & Magic Numbers**:
   - `src/pipelines/firms.py:93-94, 201-214`
   - `src/pipelines/iqair.py:162-166, 235-245`
   - `src/pipelines/cams.py:129-133, 178`
   - `src/pipelines/staging_buffer.py:265, 432`
   - `src/pipelines/scheduler.py:150, 331`
