# Baseline Survey & Existing Workspace Investigation Report

**Document ID**: `PAQ-SURVEY-EXISTING-R1`  
**Explorer**: `explorer_survey_existing`  
**Date**: 2026-11-10T12:50:00Z  
**Target Root**: `c:\Users\Asif\Downloads\Punjab Air Quality\`  

---

## Executive Summary

The existing workspace contains a monolithic 9.6 MB client-side dashboard (`index.html`) featuring an embedded 216-hour (1–9 Nov 2026) multi-pollutant dataset across all 41 districts of Punjab, paired with a standalone Python polling utility (`collector/collector.py`). Both artifacts are completely self-contained and ready for non-destructive relocation into `original System/` under Requirement R1, leaving `docs/` and `.agents/` preserved in the workspace root.

---

## 1. Observation

### 1.1 Root Directory Inventory
A complete scan of `c:\Users\Asif\Downloads\Punjab Air Quality\` reveals four items:
- `.agents/` (Directory) — Teamwork coordination metadata and agent working states.
- `docs/` (Directory) — Authoritative production specifications (6 architecture markdown files, 189 KB total).
- `collector/` (Directory) — Legacy collection script (`collector.py`, 16,362 bytes).
- `index.html` (File) — Monolithic application and embedded database (9,609,848 bytes, 805 lines).

### 1.2 Inspection of `collector/collector.py`
- **File Metrics**: 292 lines, 16,362 bytes, UTF-8 Python 3 script.
- **Standard CLI Commands**:
  - `python3 -I collector.py fetch OUT`: Pulls raw data from four external feeds into `OUT/raw.json`.
  - `python3 -I collector.py build OUT EXISTING`: Merges `OUT/raw.json` with existing hourly database documents from `EXISTING/<id>.json`, outputting normalized documents to `OUT/docs/<id>.json` and database operations to `OUT/batch.json`.
- **Target External Endpoints**:
  1. *EPA Punjab Portal*: `https://aqi.punjab.gov.pk/api/dashboard/current`, `https://aqi.punjab.gov.pk/api/districts`, `https://aqi.punjab.gov.pk/api/district-stations/{district}`.
     - User-Agent header: `EMC-EPA-Punjab-AQ-dashboard/1.0`.
  2. *NOAA Aviation Weather METAR*: `https://aviationweather.gov/api/data/metar?ids=OPLA,OPFA,OPMT,OPST,OPIS,OPRN,OPRK,OPBW,OPDG,OPSR,OPMI,VIAR&format=json&hours=6`.
  3. *WMO Synoptic Observations via Ogimet*: Blocks `415`, `416`, `417` covering Punjab via `https://www.ogimet.com/cgi-bin/getsynop?block={blk}&begin={b}&end={e_}`. Targeted WMO stations: 41640 (Lahore PBO), 41641 (Lahore Airport), 41571 (Islamabad), 41598 (Jhelum), 41600 (Sialkot), 41675 (Multan), 41700 (Bahawalpur).
  4. *ECMWF IFS 10-m Wind via Open-Meteo*: Multi-coordinate single GET query for 41 district centroids via `https://api.open-meteo.com/v1/forecast?latitude=...&longitude=...&hourly=wind_speed_10m,wind_direction_10m&models=ecmwf_ifs025&wind_speed_unit=ms&timezone=Asia%2FKarachi&past_days=1&forecast_days=1`.
- **Station Mapping (`PMAP`)**:
  - Contains 53 hardcoded ID-to-station mappings (e.g. `"10": "DHQ Sheikhupura"`, `"12": "FMDRC-LHR"`, `"27": "Gulberg III Lahore - Mobile 1"`).
  - Fallback name dictionary: `NAME_FALLBACK = {"Chiniot": "Chiniot"}`.
- **District Centroids (`DIST`)**:
  - Explicit geographic centroids `[latitude, longitude]` for 41 districts (Attock through Wazirabad).
- **Normalized Hourly Document Schema (`h<YYYYMMDDHH>.json`)**:
  - `t`: `"YYYY-MM-DD HH:00"` (PKT timestamp, UTC+5).
  - `st`: Station map `{<station_name>: [AQI, PM2.5, PM10, NO2, SO2, CO, O3, ws_ms, wd_deg]}` (9 elements).
  - `ap`: METAR map `{<ICAO>: [dir, ws_kt, vis_m, temp_c, weather_desc, gust_kt, obs_time_utc]}`.
  - `wmo`: WMO map `{<WMO_ID>: [dir_deg, ws_ms, obs_time_utc]}`.
  - `ecm`: ECMWF map `{<district>: [ws_ms, wd_deg]}`.
  - `src`: Feed status strings `{portal, metar, wmo, ecmwf}`.
  - `upd`: ISO UTC timestamp of collector run.

### 1.3 Live Feed Network Verification
- **Open-Meteo API**: Verified reachable (HTTP 200).
- **AviationWeather METAR API**: Verified reachable (HTTP 200).
- **EPA Punjab Portal**: `https://aqi.punjab.gov.pk/api/dashboard/current` returned HTTP 404 at test time.
- **Windows Networking Note**: Windows PowerShell maps `curl` to `Invoke-WebRequest`; native `curl.exe` is present and functional (`curl 8.21.0`). Python standard `urllib` on Windows requires SSL certificate configuration (`ssl._create_unverified_context()` in restricted proxy environments).

### 1.4 Inspection of `index.html`
- **File Metrics**: 805 lines, 9,609,848 bytes.
- **Structure Breakdown**:
  - Lines 1–120: CSS design system and layout styling (support for automatic dark/light mode, custom variables `--bg`, `--sea`, `--punjab`, `--accent`, `--border`, typography tokens Barlow Condensed, Source Sans 3, JetBrains Mono).
  - Lines 122–260: HTML5 layout components:
    - Navigation header with live timestamp display.
    - Pollutant selector group (`AQI`, `PM10`, `PM2.5`, `NO2`, `SO2`, `CO`, `O3`, `NO`, `NOX`).
    - Main interactive map console (`<canvas id="map">`, time scrubber `<input type="range" id="scrub">`, animation controls, mode radios `surface` vs `districts`, transport arrow toggles, ECMWF layer toggle).
    - KPI readout cards: Province hourly mean, exceedance count, highest district, sparkline canvas (`#spark`).
    - Airport winds table (`#apBody`).
    - All districts ranking and clickable selector (`#dList`).
    - District deep-dive panel: Pollutant table, polar wind rose canvas (`#rose`).
    - Nine synchronous provincial small-multiples (`#minis`).
    - Hourly wind speed table at airports (`#apHr`).
    - Hourly district tabular views (`#hrTable` with tabs: Concentration, Inter-district transport, Transboundary).
    - Cross-border transport card with embedded base64 satellite figures, fire detection tables, and IQAir regional readings.
    - Key findings and methodology summary text.
  - Line 262: Massive embedded JSON payload: `<script>window.DATA={...};</script>` (9,084,824 characters).
  - Line 264–376 (Script #2): `window.extendData = function(DATA, docs)` (10,997 characters) — client-side dynamic delta aggregator and spatial mathematics engine.
  - Line 378–787 (Script #3): Main application logic, Equirectangular canvas projection ($cos(31^\circ)$ scaling), wind particle simulation, IDW raster field generator, event bindings, chart rendering (102,855 characters).
  - Line 789–803 (Script #4): Database bootstrap hook (`claude.use('db')`) with graceful fallback to offline AQMS baseline state.

### 1.5 Embedded Baseline Dataset Inventory (`window.DATA`)
- **Metadata (`meta`)**:
  - `start`: `"2026-11-01 00:00"`, `end`: `"2026-11-09 23:00"` (216 sequential hourly steps = 9 days $\times$ 24 hours).
  - `nstations`: 79, `ndistricts`: 41, `nmon`: 41, `unmon`: 0, `calm`: 0.5 m/s threshold, `ecm_ratio`: 0.2268.
- **Administrative Districts (`districts` & `adm`)**:
  - Exactly 41 administrative districts.
  - Every district contains: centroid coordinates (`[lat, lon]`), monitoring status flag (`est: false` for all 41 districts in final dataset), assigned stations list, label placement anchor, and polygon boundary coordinates.
- **Airports (`airports`)**:
  - 6 stations: OPLA (Lahore), OPFA (Faisalabad), OPMT (Multan), OPST (Sialkot), OPIS (Islamabad), VIAR (Amritsar, India).
  - Each entry has coordinates and an array of 216 hourly wind vector $(u, v)$ components.
- **ECMWF Regional Grid (`ecm`)**:
  - 15 $\times$ 15 latitude/longitude coordinate grid covering $27.5^\circ\text{N} - 34.5^\circ\text{N}$ and $69.0^\circ\text{E} - 76.0^\circ\text{E}$.
  - Contains 216 hourly grid frames for: $u_{10}, v_{10}$ (10-meter wind), $u_{925}, v_{925}$ (925 hPa wind), and boundary cross-border wind arrays $xb_{10}, xb_{925}$.
- **Transboundary Geometry (`tbgeo`)**:
  - 24 border-belt districts with distance to border (`border_km`), directional sector masks (`india_sectors`), and 440 border boundary points with 117 outward normal vectors (`samples`).

### 1.6 Station Metadata Catalog Summary
- **Total Stations**: 79 stations across all 41 districts.
- **Network Breakdown**:
  - Fixed Stations: 74 stations.
  - Mobile Monitoring Units: 5 stations (Mobile 1 at Gulberg III, Mobile 2 at Lathepur, Mobile 3 at Wagha Border, Mobile 4 at Egerton Road, Mobile 5 at BHU Jandiala Kalsan).
- **Spatial Distribution by District**:
  - Lahore: 13 stations (8 fixed + 5 mobile).
  - Rawalpindi: 4 stations.
  - Faisalabad, Gujranwala, Chakwal, Sheikhupura: 3 stations each.
  - Attock, Bahawalnagar, Bahawalpur, DG Khan, Hafizabad, Jhelum, Kasur, Khanewal, Khushab, Multan, Muzaffargarh, Narowal, Rajanpur, Sahiwal, Sargodha: 2 stations each.
  - Bhakkar, Chiniot, Gujrat, Jhang, Kot Addu, Layyah, Lodhran, Mandi Bahauddin, Mianwali, Murree, Nankana Sahib, Okara, Pakpattan, Rahim Yar Khan, Sialkot, Talagang, Taunsa, Toba Tek Singh, Vehari, Wazirabad: 1 station each.
- **Coordinate Provenance (`coordsrc`)**:
  - EMC Confirmed (GPS verified): 11 stations.
  - Shapefile (official EPA boundary shapefiles): 44 stations.
  - Approximate (Town Centre / Landmark): 24 tehsil stations.
  - Skipped: 1 station ("OneNetwork Station 25", unknown location).
- **Station Resolution Gap**:
  - `collector.py` only statically mapped 53 stations in `PMAP`. The full baseline dataset in `index.html` incorporates 79 stations (the 55 original AQMS plus 24 new tehsil-level stations added in November 2026).

### 1.7 Historical Pollutant Statistics (216 Hours across 79 Stations)

| Pollutant | Scale | Unit | Ref Limit | Valid Readings | Missing | Min | Max | Mean |
|---|---|---|---|---|---|---|---|---|
| **AQI** | aqi | index | 200 (PEPC) | 14,996 | 2,068 | 42.0 | 500.0 | 257.41 |
| **PM2.5** | conc | µg/m³ | 35 (24-h) | 14,704 | 2,360 | 2.2 | 995.2 | 183.29 |
| **PM10** | conc | µg/m³ | 150 (24-h) | 14,242 | 2,822 | 6.4 | 1,342.7 | 337.70 |
| **NO2** | conc | µg/m³ | 80 (24-h) | 15,162 | 1,902 | 0.0 | 307.7 | 35.19 |
| **SO2** | conc | µg/m³ | 120 (24-h) | 14,426 | 2,638 | 0.0 | 622.5 | 21.16 |
| **CO** | conc | mg/m³ | 5 (8-h) | 15,406 | 1,658 | 0.0 | 33.18 | 1.92 |
| **O3** | conc | µg/m³ | 130 (1-h) | 14,549 | 2,515 | 0.0 | 1,798.3 | 40.13 |
| **NO** | conc | µg/m³ | 40 (24-h) | 14,885 | 2,179 | 0.0 | 1,100.5 | 22.04 |
| **NOX** | conc | µg/m³ | None | 15,321 | 1,743 | 0.0 | 1,713.2 | 68.39 |

---

## 2. Logic Chain

1. **Self-Containment of Existing Artifacts**:
   - *Observation*: `index.html` loads all styling and baseline data internally via inline `<style>` and `<script>` tags, referencing external URLs only for Google Fonts and an optional artifact DB (`claude.use('db')`). `collector/collector.py` is executed via CLI with input/output path arguments. Neither file imports or references root workspace paths.
   - *Deduction*: Moving `index.html` and `collector/` into an `original System/` directory preserves their code and execution semantics without side effects on remaining root items.

2. **Root Workspace Preservation**:
   - *Observation*: `docs/` contains 6 authoritative production specification documents. `.agents/` contains active teamwork context and agent memory.
   - *Deduction*: Preserving `docs/` and `.agents/` in the project root maintains direct alignment with requirement R1 and keeps reference documentation immediately accessible to build tools, tests, and developers.

3. **Necessity of Schema-Conforming Baseline Templates (Requirement R2)**:
   - *Observation*: Live testing demonstrated that `aqi.punjab.gov.pk/api/dashboard/current` returns HTTP 404, while `Open-Meteo` and `AviationWeather` remain operational.
   - *Deduction*: A live-only pipeline would immediately fail during test execution or when the portal server experiences downtime. To guarantee robust automated testing (Requirement R6) and deterministic operation, baseline data templates must be seeded directly from the historical records in `index.html`.

4. **Station Mapping Discrepancy**:
   - *Observation*: `collector.py`'s `PMAP` maps 53 stations. `index.html` contains 79 stations (including 24 tehsils like `AC Office Choa Saidan Shah`, `Chiniot`, `THQ Alipur`, etc.).
   - *Deduction*: Ingestion pipelines in the new architecture must not rely solely on `collector.py`'s partial `PMAP`. They must implement the complete 79-station registry extracted from `index.html`.

5. **Decoupled Transformation Implementation (Requirement R3)**:
   - *Observation*: The core algorithms (Great-Circle Haversine, IDW interpolation, physical advection flux with exponential decay $e^{-d/100}$, CPF polar wind roses with $P_{75}$ threshold, transboundary cross-border index, and PEPC breakpoint calculations) are implemented in pure JavaScript inside `index.html` (Script #2 & Script #3) and formally specified in `docs/TRANSFORMATION_LOGIC_SPEC.md`.
   - *Deduction*: These pure mathematical functions can be extracted and implemented as clean, decoupled Python or TypeScript modules with 100% unit test coverage, decoupled from UI rendering.

---

## 3. Caveats

1. **Portal Endpoint Status**: The public endpoint `https://aqi.punjab.gov.pk/api/dashboard/current` returned HTTP 404 at the time of this survey. Downstream ingestion modules must implement the fallback chain (`station -> metar -> ecmwf -> baseline template`) specified in `docs/DATA_SOURCES_AND_STREAMS.md`.
2. **Approximate Tehsil Coordinates**: 24 tehsil stations lack shapefile boundary records and are geocoded to approximate town centers. This matches the legacy system's documented methodology.
3. **Station 25 Omission**: "OneNetwork Station 25" is omitted from calculations in both legacy and new specifications because its physical geographic coordinates are unknown.
4. **Database Abstraction**: The legacy `claude.use('db')` call is proprietary to the original container. The new backend architecture will use standard decoupled persistence (TimescaleDB / SQLite / In-Memory adapter) as designed in `docs/SYSTEM_ARCHITECTURE.md`.

---

## 4. Conclusion & Recommendations

### 4.1 Requirement R1 Execution Plan
Execute the following directory reorganization:
1. Create directory `original System/` at `c:\Users\Asif\Downloads\Punjab Air Quality\original System\`.
2. Relocate `index.html` to `original System\index.html`.
3. Relocate `collector\` to `original System\collector\`.
4. Leave `docs/` and `.agents/` untouched in the workspace root.

```
c:\Users\Asif\Downloads\Punjab Air Quality\
├── .agents/                    <-- PRESERVED in root
├── docs/                       <-- PRESERVED in root
└── original System/            <-- CREATED for R1
    ├── index.html              <-- MOVED from root
    └── collector/              <-- MOVED from root
        └── collector.py
```

### 4.2 Baseline Data Seeding Plan for Requirement R2
To prevent redundant parsing of the 9.6 MB `index.html` file by test runners, extract clean, standardized fixtures:
1. `stations.json`: Machine-readable catalog of all 79 stations with names, districts, coordinates, sensor types, and coordinate provenance.
2. `districts.json`: Geometry, centroids, and border indices for all 41 districts.
3. `baseline_sample_fixture.json`: A representative 24-hour slice (or full 216-hour series) formatted as schema-conforming CSV and JSON fixtures for pipeline and transformation unit testing.

---

## 5. Verification Method

To independently verify the observations and findings in this report, execute the following commands in PowerShell from the project root `c:\Users\Asif\Downloads\Punjab Air Quality\`:

```powershell
# 1. Verify existing file locations and sizes
Get-ChildItem -Path . -Force | Select-Object Name, Length, Mode

# 2. Verify collector.py integrity
python -c "import py_compile; py_compile.compile('collector/collector.py', doraise=True); print('collector.py syntax OK')"

# 3. Verify total stations in index.html (Output should be 79)
python -c "
import json
with open('index.html', 'r', encoding='utf-8') as f:
    line = [l for l in f if 'window.DATA=' in l][0]
data = json.loads(line.split('window.DATA=')[1].rstrip(';\n</script>'))
print('Stations count:', len(data['stations']))
print('Districts count:', len(data['districts']))
print('Hours count:', len(data['hours']))
print('Pollutants:', list(data['pol'].keys()))
"

# 4. Verify live external API connectivity
curl.exe -s -o NUL -w "Open-Meteo HTTP %{http_code}\n" "https://api.open-meteo.com/v1/forecast?latitude=31.5&longitude=74.3&hourly=wind_speed_10m&models=ecmwf_ifs025"
curl.exe -s -o NUL -w "AviationWeather HTTP %{http_code}\n" "https://aviationweather.gov/api/data/metar?ids=OPLA&format=json&hours=1"
curl.exe -s -o NUL -w "Punjab Portal HTTP %{http_code}\n" -A "EMC-EPA-Punjab-AQ-dashboard/1.0" "https://aqi.punjab.gov.pk/api/dashboard/current"
```

**Invalidation Conditions**:
- Station count in `window.DATA` differs from 79.
- District count differs from 41.
- `index.html` references relative files in `collector/` or root outside of standard self-contained styling.
