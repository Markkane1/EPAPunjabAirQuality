## 2026-11-10T11:43:16Z
[Message] timestamp=2026-11-10T11:43:16Z sender=85d6ae91-e4ec-476d-a001-4cedffd96841 priority=MESSAGE_PRIORITY_HIGH content=You are the Architecture Remediation Specialist (teamwork_worker).
Your working directory is: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\worker_remediation\
Read ORIGINAL_REQUEST.md at: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\ORIGINAL_REQUEST.md
Read PROJECT.md at: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\orchestrator\PROJECT.md
Read GATE_STATUS.md at: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\orchestrator\GATE_STATUS.md

Read input review and challenge reports for exact remediation details:
1. c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\reviewer_math\review_report.md
2. c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\challenger_algorithms\challenge_report.md
3. c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\challenger_architecture\challenge_report.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

STRICT CONSTRAINT: DO NOT modify index.html or collector/collector.py. You are updating and remediating the architectural and mathematical specification documents in `docs/`.

Task: Apply the 8 consolidated technical remediations across all 6 documents in `docs/`:

1. In `c:\Users\Asif\Downloads\Punjab Air Quality\docs\DATA_SOURCES_AND_STREAMS.md`:
   - Update `RawStationMeasurement` Pydantic model: change upper bound from `le=1000.0` to `le=5000.0` with validation severity flags to preserve real extreme Lahore/Punjab smog values (>1,000 µg/m³).
   - Change `pollutant_flags` type to `Optional[Any] = None` (allowing string, list, or dict).
   - Add physical anemometer speed bounds ($0 \le ws \le 30\text{ m/s}$), direction bounds ($0 \le wd \le 360^\circ$), and station vane misalignment blacklist (`Wazirabad`).
   - Explicitly document continuous half-open PEPC breakpoint brackets ($BP_{i-1} < C \le BP_i$) to eliminate statutory decimal dead zones in $(15.0, 15.1)$.
   - Clarify 39 India-Pakistan border animation vector nodes vs 117 CAMS boundary perimeter nodes.

2. In `c:\Users\Asif\Downloads\Punjab Air Quality\docs\TRANSFORMATION_LOGIC_SPEC.md`:
   - Transform 5 (CPF Roses): Add mandatory $N_k \ge 6$ small-sample suppression rule (sectors with $N_k < 6$ are assigned `null` to prevent false spike distortion). Note that CPF $P_{75}$ and sector binning are calculated over pooled station observations ($N \approx 2700$), not district hourly means.
   - Clarify receptor coupling $\Omega$ default to 0.25 when $N_k < 6$.
   - PEPC Breakpoints: Formalize continuous half-open intervals ($BP_{i-1} < C \le BP_i$) and operational AQI capping at 500 when PM2.5 $C > 350\ \mu\text{g/m}^3$.
   - Transform 6 (3-Hour Hold Filter): Add explicit index guard $i \ge 2$ to prevent Python negative index wraparound; exempt `AQI` from hold filter; sanitize $v \le 0$ to `null`.
   - Transform 6 (Completeness): Fix formula to `round(0.75 * NA)` matching `index.html`.
   - Transform 7 (Advection Flux): Explicitly document that advection transport is strictly disabled for dimensionless ordinal index `AQI`; document the 60-pathway limit (`slice(0, 60)`).
   - Mark Transform 3 (Planar Screen Canvas IDW) as legacy uncalled/superseded by Transform 2.

3. In `c:\Users\Asif\Downloads\Punjab Air Quality\docs\DATA_PIPELINES_ARCHITECTURE.md`:
   - Ingestion Pipeline 1: Fix `station_observations` hypertable DDL to include `PRIMARY KEY (time, station_id)` and fix upsert to `ON CONFLICT (time, station_id) DO UPDATE`.
   - Update Pydantic schemas: Add default `= None` to all `Optional[...]` fields in `NormalizedObservation`.
   - EPA Fallback Fanout: Replace serial loop with asynchronous concurrent fan-out (`asyncio.gather` with `asyncio.Semaphore(10)` and 3s per-district timeout) to prevent the 1,710s worker starvation cascade.
   - Set Redis lock TTL dynamically with jitter and circuit breaker policies.

4. In `c:\Users\Asif\Downloads\Punjab Air Quality\docs\SYSTEM_ARCHITECTURE.md`:
   - Update TimescaleDB DDL for `station_observations` with `PRIMARY KEY (time, station_id)`.
   - Add compression policy and hypertable retention settings for `advection_fluxes`.
   - Document PostGIS geography casting `ST_DWithin(geom::geography, ...)` to fix 4326 degree vs meter radius queries.

5. In `c:\Users\Asif\Downloads\Punjab Air Quality\docs\UI_UX_SPECIFICATION.md`:
   - Performance optimization for IDW Surface: Mandate downsampled compute grid (e.g. 150x175 or 0.25x scale) with bilinear texture upsampling on Canvas, or WebGL fragment shader, guaranteeing execution time < 3 ms and preserving the 16.67 ms 60 FPS frame budget.
   - Zustand State Store: Decouple temporal lerp animation frame updates from React component state tree using refs / subscription channels to eliminate state tearing during high-speed scrubbing.

6. In `c:\Users\Asif\Downloads\Punjab Air Quality\docs\ARCHITECTURE_OVERVIEW.md`:
   - Update master overview reflecting all 8 remediations, performance guarantees, and full compliance with R1–R6.

## 2026-11-10T11:53:57Z
[Message] timestamp=2026-11-10T11:53:57Z sender=85d6ae91-e4ec-476d-a001-4cedffd96841 priority=MESSAGE_PRIORITY_HIGH content=**Context**: Iteration 2 Architecture Remediation
**Content**: Status check. Please report your current progress on updating the 6 specification documents in docs/ with the 8 consensus remediations.
**Action**: Please update your progress.md and notify the orchestrator when completed.
