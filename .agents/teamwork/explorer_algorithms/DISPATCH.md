## 2026-11-10T11:07:22Z
You are the Algorithms & Transforms Explorer (teamwork_explorer).
Your working directory is: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\explorer_algorithms\
Read ORIGINAL_REQUEST.md at: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\ORIGINAL_REQUEST.md

Your primary objective is to investigate the authoritative source file:
c:\Users\Asif\Downloads\Punjab Air Quality\index.html

Focus strictly on Requirement R2: Data Transformation and Processing Logic Mapping.
Analyze index.html to extract, document, and mathematically specify all algorithmic transformations currently implemented in the client:
1. IDW (Inverse Distance Weighting) spatial interpolation:
   - Mathematical formula, power parameter (p), radius/distance metric (Euclidean/Haversine), nearest neighbor thresholds, grid resolution/bounding box, and handling of zero distances.
2. CPF (Conditional Probability Function) polar roses:
   - Wind direction/speed sector binning, percentile thresholding (e.g. 75th/90th percentile of pollutant concentrations), polar coordinate math, calm wind thresholds.
3. Flux calculations:
   - Advection/transport vector math, integration with boundary layer height, wind velocity x PM2.5/PM10 concentration, cross-border or regional flux estimation.
4. PEPC (Punjab Environmental Protection Council) & AQI breakpoints:
   - Concentration ranges, sub-index equations, pollutant breakpoints (PM2.5, PM10, NO2, SO2, CO, O3), category color scales and health caution advisory levels.
5. Hourly aggregation and temporal smoothing:
   - Moving averages, window schemas, data validation/missing data imputation, timezone handling (UTC vs PKT).
6. Any other mathematical, statistical, or geometric algorithms in index.html (e.g. spatial clustering, color ramps, contouring).

STRICT CONSTRAINT: Do not modify index.html or any codebase files. This is an exploration task only.
Write your detailed algorithmic specification report to:
c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\explorer_algorithms\transforms_report.md
When finished, write your handoff.md in your working directory and notify the orchestrator with send_message.
