## 2026-11-10T11:17:51Z

You are the Data & Pipeline Architect (teamwork_worker).
Your working directory is: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\worker_data_pipelines\
Read ORIGINAL_REQUEST.md at: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\ORIGINAL_REQUEST.md
Read PROJECT.md at: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\orchestrator\PROJECT.md

Read input survey findings:
1. c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\spec_miner_sources\sources_catalog.md
2. c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\explorer_algorithms\transforms_report.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

STRICT CONSTRAINT: DO NOT modify index.html, collector/collector.py, or any existing codebase files. Your deliverables must be comprehensive, production-grade architectural and specification documents written in Markdown with complete formulas, payload schemas, tables, and Mermaid dataflow diagrams.

Write Ownership (You exclusively own and will create these files):
1. `c:\Users\Asif\Downloads\Punjab Air Quality\docs\DATA_SOURCES_AND_STREAMS.md`
   - Detailed specification for Requirement R1:
   - Full catalog of all 7 data streams (EPA Punjab, Aviation Weather METAR, WMO SYNOP, ECMWF IFS via Open-Meteo, NASA FIRMS, IQAir, and CAMS PM2.5 boundary flux).
   - Every endpoint URL, query parameter, HTTP method, headers, auth/API keys requirement.
   - Expected payload schemas (complete JSON structures, fields, types, units, coordinate systems WGS84).
   - Polling frequencies, cron cadences, and trigger conditions.
   - Quality control and sensor cleaning rules (7-hour median spike filter, 3-hour hold filter, anemometer bounds, zero suppression, Wazirabad vane blacklist, 75% completeness rule).
   - Multi-tier fallback mechanisms (Station -> METAR -> ECMWF -> IDW).

2. `c:\Users\Asif\Downloads\Punjab Air Quality\docs\TRANSFORMATION_LOGIC_SPEC.md`
   - Detailed specification for Requirement R2:
   - Algorithmic and mathematical extraction of all logic currently implemented in the client:
     * Discrete Geodesic IDW (Haversine distance, power p=2, 5 km singularity clamping).
     * Anisotropic Wind-Steered Continuous IDW (alignment cosine, downwind boost, softening epsilon=4px).
     * Planar Screen Canvas IDW (power p=3, softening epsilon=0.5px).
     * Vector Wind Blending (u, v components, scalar conversion).
     * CPF Polar Roses (16 sectors, meteorological wind direction FROM, P75 concentration threshold, calm cutoff 0.5 m/s, 0.25 isotropic baseline circle).
     * Physical Advection Flux (pair-wise transport: C * w * cos(d_theta) * exp(-d/LS), LS=100km, cone=35 deg, calm cutoff 0.5 m/s).
     * Transboundary Index (120 km border-belt evaluation, india_sectors matching, 117-point boundary normal flux).
     * Receptor CPF Pathway Coupling Score.
     * PEPC Breakpoints for PM2.5, PM10, SO2, NO2, CO, O3, sub-index linear interpolation equations, 7-tier EPA Punjab AQI categories, PEQS continuous color scales.
     * Hourly aggregation, moving median window schemas, and sub-hourly continuous time interpolation (lerp).
   - Provide exact LaTeX mathematical formulas, input schemas, step-by-step algorithms, edge cases, and output schemas for each.

3. `c:\Users\Asif\Downloads\Punjab Air Quality\docs\DATA_PIPELINES_ARCHITECTURE.md`
   - Detailed specification for Requirement R3:
   - Independent, modular data pipelines for each of the 7 streams:
     * Architecture of Ingestion Workers (Python / Celery / Temporal / cron).
     * Validation & Schema Enforcement (Pydantic / JSON Schema).
     * Normalization & Harmonization (converting heterogeneous raw feeds into unified TimescaleDB/PostgreSQL hypertable records).
     * Dead-Letter Queues (DLQ), failure handling, exponential backoff, jitter, and retry policies.
     * In-memory caching (Redis) for latest station observations and hourly pre-aggregated grids.
     * Live network access assumptions, rate limit handling, and graceful offline degradation.
   - Include complete Mermaid sequence and flowchart diagrams.

When finished, compile your handoff.md in your working directory and notify the orchestrator with send_message.
