## 2026-11-15T19:50:51Z
You are Explorer 2 (Pipelines & Telemetry Integrity Specialist) for the Punjab Air Quality project.

## Mandatory Reading & Authoritative Sources
- Read ORIGINAL_REQUEST.md at: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\ORIGINAL_REQUEST.md
- Read PROJECT.md at: c:\Users\Asif\Downloads\Punjab Air Quality\PROJECT.md
- Working Directory: c:\Users\Asif\Downloads\Punjab Air Quality
- Your State Folder: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\explorer_pipelines_r3_2

## Mission & Specific Investigation Tasks
Investigate all data ingestion pipelines and backend/frontend telemetry services against the critical user mandate:
"Real Data, from All pipelines, no simulation Shit NOw. All pipelines (EPA Punjab, NOAA METAR, WMO SYNOP, ECMWF IFS, NASA FIRMS VIIRS, IQAir AirVisual, CAMS) must execute against real live data endpoints. Absolutely zero simulation generators, zero synthetic mocks, zero fake fallbacks. Ingest and display real telemetry. If an external service is unavailable or credentials missing, emit explicit degraded/unavailable status rather than generating synthetic simulation data."

1. EXAMINE ALL PIPELINES:
   - Search across `src/` (backend Python pipelines in `src/pipelines/`, `src/api/`, etc., and frontend services in `src/services/` or `src/domain/`).
   - Specifically examine each of the 7 required data pipelines:
     1. EPA Punjab
     2. NOAA METAR
     3. WMO SYNOP
     4. ECMWF IFS
     5. NASA FIRMS VIIRS
     6. IQAir AirVisual
     7. CAMS
2. IDENTIFY SIMULATION / SYNTHETIC MOCKS:
   - Enumerate all instances of random number generation (`random()`, `np.random`, synthetic oscillation formulas), mock dictionaries, simulated fallbacks, or placeholder generators.
   - Trace when and why they are called.
3. SPECIFY REAL LIVE DATA MECHANISM & DEGRADED STATE CONTRACT:
   - For each pipeline, identify the authentic real endpoint, API client, or open public feed (e.g. NOAA aviation weather METAR API, NASA FIRMS open API/CSV feeds, Open-Meteo/ECMWF CAMS open APIs, EPA Punjab scraper or API endpoints).
   - Define the explicit degraded/unavailable status contract: when credentials are absent or remote services fail, how the pipeline must return `status: "degraded"` or `status: "unavailable"` with reason and timestamp, rather than inventing synthetic numbers.
4. STRICT USER FEATURE PRESERVATION:
   - Ensure all existing pipelines, schema validations, DB tables, and routes are preserved. Zero deletions of existing user code.

Document all findings with exact file paths, line numbers, analysis, and implementation blueprints in:
`c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\explorer_pipelines_r3_2\handoff.md`.
Use send_message to report completion when done.
