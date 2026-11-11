# Milestone M4 Review & Adversarial Challenge Report

## Review Summary

**Verdict**: **APPROVE**  
**Reviewer**: reviewer_m4_2 (Archetype: teamwork_reviewer / critic)  
**Target Milestone**: M4 (Core Backend Services & API Gateway)  
**Overall Risk Assessment**: LOW  

---

## 1. Observation

1. **Mandated Route Contracts & OpenAPI 3.1 Verification**:
   - Inspected `src/api/routes/` and verified all 10 mandated routes mounted under `/api/v1/`:
     - `GET /api/v1/meta/districts` (`src/api/routes/meta.py:12-42`)
     - `GET /api/v1/meta/stations` (`src/api/routes/meta.py:45-76`)
     - `GET /api/v1/observations/current` (`src/api/routes/observations.py:13-29`)
     - `GET /api/v1/observations/hourly` (`src/api/routes/observations.py:31-53`)
     - `GET /api/v1/spatial/surface` (`src/api/routes/spatial.py:13-33`)
     - `GET /api/v1/analytics/cpf` (`src/api/routes/analytics.py:13-36`)
     - `GET /api/v1/analytics/flux` (`src/api/routes/analytics.py:38-75`)
     - `GET /api/v1/analytics/transboundary` (`src/api/routes/analytics.py:77-95`)
     - `POST /api/v1/ingest/csv` (`src/api/routes/ingest.py:11-52`)
     - `GET /api/v1/stream/live` (`src/api/routes/stream.py:79-97`)
   - Queried `/api/v1/openapi.json`: confirmed 100% of the 10 paths and their respective HTTP methods are published in the OpenAPI 3.1 specification.

2. **Domain Guard: Physical Mass Flux on AQI**:
   - In `src/api/routes/analytics.py:53-62`:
     ```python
     if pollutant.strip().upper() == "AQI":
         raise HTTPException(
             status_code=400,
             detail=(
                 "Advection transport mass flux is physically undefined for dimensionless ordinal index 'AQI'. "
                 "Mass conservation requires conserved physical concentrations. "
                 "Query a mass pollutant species such as PM2.5, PM10, NO2, SO2, CO, or O3."
             ),
         )
     ```
   - In `src/services/analytics_service.py:192-197`, an identical defense-in-depth guard is also enforced at the domain service layer.
   - Tested variations: `pollutant=AQI`, `pollutant=aqi`, `pollutant=Aqi`, `pollutant=%20aqi%20`, `pollutant=AQI%20`. All verbatim returned HTTP 400 Bad Request with the required physical explanation.

3. **Domain Guard: CPF Small-Sample Suppression ($N_k < 6 \implies \text{None}$)**:
   - In `src/domain/math/cpf.py:151-155`:
     ```python
     for k in range(DEFAULT_SECTOR_COUNT):
         if sector_n[k] >= min_samples:
             sectors.append(round(sector_m[k] / sector_n[k], 4))
         else:
             sectors.append(None)  # Small-sample suppression
     ```
   - Inspected `src/api/schemas/analytics.py:14-16` (`cpf_probability: Optional[float] = Field(None, description="Conditional probability (mk / Nk), or None if Nk < 6 (suppressed)")`).
   - Verified on API endpoint `GET /api/v1/analytics/cpf?district=Lahore&pollutant=PM2.5`: Every sector where $N_k < 6$ had `cpf_probability == None`; every sector where $N_k \ge 6$ had a valid float probability. Calm wind threshold $< 0.5\text{ m/s}$ was excluded from directional bins.
   - Unknown district handling: `district=Atlantis` returns HTTP 400 Bad Request with `"Unknown administrative district: 'Atlantis'"`.

4. **SSE Stream Protocol Verification**:
   - In `src/api/routes/stream.py:89-97`:
     ```python
     return StreamingResponse(
         sse_event_generator(request, obs_service, max_events=max_events),
         media_type="text/event-stream",
         headers={
             "Cache-Control": "no-cache",
             "Connection": "keep-alive",
             "X-Accel-Buffering": "no",
         },
     )
     ```
   - Direct inspection and runtime testing of `GET /api/v1/stream/live?max_events=1`:
     - Content-Type: `text/event-stream; charset=utf-8`
     - Headers: `Cache-Control: no-cache`, `Connection: keep-alive`, `X-Accel-Buffering: no`
     - Payload frame 0: `event: hourly_update\ndata: { ... }\n\n` containing latest provincial summary, district readings, and aerodromes.
   - Tested 15-second keepalive timer: After simulated $>15$s interval, the generator explicitly emitted comment `: keepalive\n\n`.
   - Client disconnect check: `await request.is_disconnected()` checked every 2.0s, cleanly terminating loop on disconnect.

5. **CSV Ingestion Multipart Upload & DLQ Quarantine**:
   - In `src/api/routes/ingest.py:16-52`, file extension `.csv` and non-empty file contents are enforced with HTTP 400 guards.
   - In `src/services/ingestion_service.py:57-90`, parsing delegates to `UserCSVIngestionAdapter`.
   - Injected adversarial CSV containing 2 valid rows and 3 malformed rows (out-of-bounds latitude `99.9999`, negative value `-10.0`, unknown pollutant `unknown_pol`):
     - Endpoint returned HTTP 200 with `status: "partial_quarantine"`.
     - `total_rows`: 5, `valid_rows`: 2, `quarantined_rows`: 3.
     - DLQ records preserved exact row numbers (2, 3, 4), error types (`CoordinateOutOfBoundsError`, `PhysicalRangeExceededError`, `SchemaValidationError`), error messages, and raw record dictionaries.
     - Valid rows were ingested and newly discovered station dynamically appeared in `/api/v1/meta/stations?district=Lahore`.

6. **Test Suite Execution**:
   - `python -m pytest tests/integration/test_api_endpoints.py -v`:
     `15 passed, 1 warning in 1.93s`.
   - `python -m pytest tests/ -v`:
     `391 passed, 1 warning in 29.53s` (0 failures, 0 regressions across all tiers).
   - Independent adversarial suite (`.agents/teamwork/reviewer_m4_2/test_adversarial.py`):
     10 out of 10 adversarial checks passed.

7. **Integrity & Clean Architecture Scan**:
   - Automated codebase scan across `src/services/`, `src/api/`, and `src/infrastructure/repositories/`:
     0 instances of hardcoded expected outputs, dummy facades, stub bypasses, or mocked responses.
   - Domain interfaces in `src/domain/interfaces/repositories.py` import strictly from standard library (`abc`, `datetime`, `typing`) and domain entities; 0 dependencies on FastAPI, Starlette, or Pydantic.

---

## 2. Logic Chain

1. **Route Completeness**: The 10 mandated routes correspond exactly to features F24–F33 in `PROJECT.md`. The OpenAPI 3.1 specification reflects all 10 endpoints with fully typed Pydantic v2 request/response schemas.
2. **Domain Integrity**: Physical mass conservation dictates that advective flux $\vec{J} = C \cdot \vec{u}$ requires a conserved mass concentration $[M/L^3]$. Because AQI is a non-linear ordinal piecewise scale, mass advection cannot mathematically be defined on AQI. The guard rejects any casing or whitespace variant of "AQI" before reaching calculation, preserving mathematical integrity.
3. **Statistical Robustness**: In CPF source apportionment, small wind direction sample sizes ($N_k < 6$) lead to spurious 100% conditional probabilities from chance isolated spikes. The small-sample suppression logic correctly substitutes `None`, preventing false-positive source attribution.
4. **Resilient Streaming**: The SSE implementation conforms to WHATWG EventSource standards. The presence of `X-Accel-Buffering: no` ensures reverse proxies (e.g., Nginx, Cloudflare) do not buffer the stream, and the 15-second keepalive comment prevents intermediate stateful firewalls/NATs from dropping idle TCP connections.
5. **Fault Isolation via DLQ**: The ingestion service isolates invalid CSV rows into `QuarantineRecord` objects without terminating or corrupting valid rows, maintaining system availability while providing full diagnostic feedback to users.
6. **Regression Invariance**: Passing all 391 tests in 29.53s proves that the addition of M4 application services and FastAPI gateway introduced 0 regressions to M1, M2, and M3 functionality.

---

## 3. Caveats

1. **Starlette Deprecation Warning**: In `src/api/main.py:94`, the custom validation exception handler uses `status.HTTP_422_UNPROCESSABLE_ENTITY`. Modern Starlette issues a deprecation warning recommending `HTTP_422_UNPROCESSABLE_CONTENT`. This does not affect runtime behavior or HTTP status code (both are 422).
2. **In-Memory Cache Lifecycle**: Dynamic additions from `POST /api/v1/ingest/csv` are held in the in-memory repository for the process lifetime; persistent disk syncing will be connected in future milestones.

---

## 4. Conclusion

Milestone M4 (Core Backend Services & API Gateway) has been implemented to an exemplary standard. The codebase strictly adheres to Clean Architecture principles, exhibits high-performance indexing, implements robust domain guards and dead-letter quarantine isolation, passes all 391 automated tests with 0 regressions, and successfully withstands all adversarial edge-case stress tests.

**Final Verdict**: **APPROVE**

---

## 5. Verification Method

To independently reproduce the review findings:

1. **Run API Integration Test Suite**:
   ```powershell
   python -m pytest tests/integration/test_api_endpoints.py -v
   ```
   *Expected outcome*: 15 passed in ~2s.

2. **Run Full System Test Suite**:
   ```powershell
   python -m pytest tests/ -v
   ```
   *Expected outcome*: 391 passed in ~30s with 0 failures, 0 regressions.

3. **Run Reviewer Adversarial Stress Test**:
   ```powershell
   python .agents/teamwork/reviewer_m4_2/test_adversarial.py
   ```
   *Expected outcome*: All 10 adversarial checks pass with exit code 0.
