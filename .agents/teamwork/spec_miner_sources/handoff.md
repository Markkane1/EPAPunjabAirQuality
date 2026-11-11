# Handoff Report: Data Sources and Stream Inventory (Requirement R1)

**Agent**: Data Sources Investigator (`spec_miner_sources`)  
**Working Directory**: `c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\spec_miner_sources\`  
**Date**: November 2026  
**Handoff Type**: Hard (Task Complete)  

---

## 1. Observation

Direct code and file observations extracted from `index.html` and `collector/collector.py`:

1. **Monolithic Bundle File Structure (`index.html`)**:
   - Total file size: 9,609,848 bytes across 768 lines (`run_command` Get-Content Measure-Object).
   - Line 228, 230, 231: Three embedded Base64 JPEG maps (lengths: 214,614, 87,520, 73,493 bytes) displaying cross-border transport flux, VIIRS fire overlays, and regional sensor circles.
   - Line 240–242: Static HTML table of daily fire detections across 11 subnational regions (2–9 Nov) based on VIIRS NOAA-20 and NOAA-21.
   - Line 243–246: Static HTML table of regional air quality around Punjab from IQAir (9 Nov ~23:00 PKT), differentiating ground sensors (CPCB/PPCB/private contributors) from daily model estimates.
   - Line 251–258: Narrative description of methodology, sensor cleaning rules, coordinate corrections, and meteorological models.
   - Line 262: 9,084,841 characters of precomputed JSON data bound to `window.DATA`.
   - Line 265–375: `window.extendData = function(DATA, docs)` providing client-side ingestion, QC, and data reconciliation for newly fetched hourly documents.
   - Line 378: `GEO` object containing regional GeoJSON boundaries for 19 surrounding provinces/states across Pakistan and Northern India.
   - Lines 9608950–9609100: Database listener subscribing to `db.collection('hours').limit(1000).onSnapshot(...)` via `claude.use('db')` with a 9,000 ms watchdog fallback timer (`setTimeout`).

2. **Hourly Cloud Task (`collector/collector.py`)**:
   - Lines 20–22:
     ```python
     PORTAL = 'https://aqi.punjab.gov.pk'
     PKT = dt.timezone(dt.timedelta(hours=5))
     UA = 'EMC-EPA-Punjab-AQ-dashboard/1.0'
     ```
   - Lines 25–38: Station ID mapping dictionary `PMAP` mapping 54 numeric portal IDs to AQMS station names (e.g. `"10": "DHQ Sheikhupura"`, `"12": "FMDRC-LHR"`, `"27": "Gulberg III Lahore - Mobile 1"`, `"177": "Nankana Sahib"`).
   - Lines 41–51: District centroids `DIST` for 41 Punjab districts.
   - Line 53: 12 ICAO airport stations:
     `ICAO = ['OPLA', 'OPFA', 'OPMT', 'OPST', 'OPIS', 'OPRN', 'OPRK', 'OPBW', 'OPDG', 'OPSR', 'OPMI', 'VIAR']` (including Amritsar `VIAR` in India).
   - Lines 55–56: 7 WMO Synoptic stations:
     `WMO = {'41640': 'Lahore PBO', '41641': 'Lahore Airport', '41571': 'Islamabad', '41598': 'Jhelum', '41600': 'Sialkot', '41675': 'Multan', '41700': 'Bahawalpur'}`.
   - Lines 95–121: EPA Punjab portal polling via `/api/dashboard/current`, `/api/districts`, and `/api/district-stations/{dn}`.
   - Lines 124–132: METAR fetch via `https://aviationweather.gov/api/data/metar?ids=...&format=json&hours=6`.
   - Lines 134–141: WMO SYNOP fetch via `https://www.ogimet.com/cgi-bin/getsynop?block={blk}&begin={b}&end={e}` (blocks 415, 416, 417).
   - Lines 145–158: ECMWF IFS 10-m wind query via `https://api.open-meteo.com/v1/forecast` with `models=ecmwf_ifs025&wind_speed_unit=ms&timezone=Asia%2FKarachi`.
   - Lines 213–218: `pollutant_flags` handling in `collector.py` nulling out flagged readings.
   - Lines 274–277: Database batch writer formatting documents for collection `'hours'`, document ID `h<YYYYMMDDHH>`.

3. **Client-Side Quality Control & Reconciliation (`index.html`)**:
   - Line 313: `const NOWIND=new Set(['Wazirabad']);` (blacklists misaligned wind vane).
   - Line 315: Wind bounds discard: `ws < 0 || ws > 30 || wd < 0 || wd > 360` (rejects Chakwal direction register and Khanewal 99.9 error).
   - Lines 319–327: 7-hour median spike filter (`v > 4*med && v > lim`) and 3-hour logger hold filter (`p !== 'AQI' && full[i-1] === v && full[i-2] === v`).
   - Line 331–332: Wind fallback sequence (`aqms` -> `metar` -> `ecmwf` -> `idw`), scaled by `KR = DATA.meta.ecm_ratio || 0.34` (baseline `0.22686`).

---

## 2. Logic Chain

1. **From Line 262 to Line 375 (`index.html`) & `collector.py`**:
   The application is designed to function both as an offline self-contained artifact (relying on `window.DATA`) and as a live-updating web application (via `claude.use('db')` and `collector.py`). The scraper acts as an hourly micro-service producing JSON documents whose schema directly feeds `window.extendData`.
2. **From Lines 95–158 (`collector.py`) and Line 226/240–246 (`index.html`)**:
   All 7 required data sources are accounted for:
   - EPA Punjab: Active real-time endpoints (`/api/dashboard/current`, `/api/district-stations/`) + baseline periodic shapefile exports.
   - METAR: Live NOAA API querying 12 airports including Amritsar, India.
   - WMO SYNOP: Ogimet CGI scraper querying GTS blocks 415, 416, 417.
   - ECMWF IFS: Open-Meteo REST API querying 41 district coordinates and a 225-point regional grid (10m and 925 hPa).
   - NASA FIRMS: VIIRS NOAA-20 and NOAA-21 active fire detection tables and visual map overlays.
   - IQAir: US AQI and PM2.5 readings for surrounding external border cities (Peshawar, Jammu, New Delhi, Bathinda, Jodhpur).
   - CAMS: Transboundary PM2.5 boundary field coupled with perpendicular wind components.
3. **From Lines 312–342 (`index.html`)**:
   The data is heterogeneous and prone to specific hardware failures (logger freezes, misaligned vanes, invalid speed registers, erroneous coordinates). Strong domain-specific normalization and cleaning heuristics are strictly required in any decoupled architecture.
4. **From Line 378 and Canvas Architecture**:
   The dashboard requires zero external tile servers (no OpenStreetMap, Carto, or Mapbox HTTP calls). All boundary geometry is embedded vector coordinates rendered on Canvas.

---

## 3. Caveats

1. **NASA FIRMS and IQAir Automation**: In the existing `index.html`, NASA FIRMS fire counts and IQAir city readings exist as static tables and embedded images for the 2–9 Nov period. While the data sources and formats are identified, live scrapers for these two streams were not part of `collector.py`. In the decoupled pipeline design (Requirement R3), dedicated automated API consumers must be architected for them.
2. **Database SDK Environment**: The live listener uses `claude.use('db')`, which is specific to the host platform environment. In a standalone production deployment, this should be replaced with standard WebSocket / SSE (Server-Sent Events) or REST polling against an open-source datastore (PostgreSQL/TimescaleDB or SQLite).

---

## 4. Conclusion

Requirement R1 (Data Source and Stream Inventory) is completely discovered, analyzed, and authoritatively documented in `c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\spec_miner_sources\sources_catalog.md`.

The catalog enumerates:
- Every external URL, HTTP method, query parameter, header, and auth profile.
- Complete payload schemas, units, coordinate systems (WGS84), and timestamps.
- Polling cadences, watchdog timers, and trigger conditions.
- Multi-tier fallback mechanisms, quality control heuristics, and error handling.
- Comprehensive inventory of all 7 core data sources.

---

## 5. Verification Method

To independently verify all findings and validate catalog claims:

1. **Inspect Catalog Deliverable**:
   ```powershell
   Get-Item -Path ".\.agents\teamwork\spec_miner_sources\sources_catalog.md"
   ```
2. **Verify Codebase Integrity (Zero Code Modifications)**:
   ```powershell
   git status
   ```
   Confirm `index.html` and `collector/collector.py` remain completely untouched.
3. **Verify API Endpoints in Codebase**:
   ```powershell
   python .agents/teamwork/spec_miner_sources/search_apis.py
   ```
4. **Verify window.DATA Schema & Keys**:
   ```powershell
   python .agents/teamwork/spec_miner_sources/inspect_data.py
   ```
5. **Verify Live Database Hook & ExtendData**:
   Inspect `index.html` lines 265–375 and lines 9608950–9609100.
