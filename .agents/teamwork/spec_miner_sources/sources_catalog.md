# Data Source and Stream Inventory Catalog (Requirement R1)
**Project**: Punjab Air Quality Monitoring & Transboundary Inflow Dashboard  
**Author**: Data Sources Investigator (`spec_miner_sources`)  
**Date**: November 2026  
**Primary Source Artifacts**: `index.html` (9.6 MB monolithic bundle), `collector/collector.py` (hourly cloud task)  
**Status**: Authoritative Reference Specification  

---

## 1. Executive Summary & Inventory Architecture

The Punjab Air Quality system is an environmental monitoring and transboundary atmospheric transport intelligence platform covering the entire province of Punjab, Pakistan (41 administrative districts, 79 active monitoring stations), as well as bordering regions of Northern India (Punjab-IN, Rajasthan, Haryana, Jammu & Kashmir).

The system integrates seven primary data sources and streams:
1. **EPA Punjab Public Portal & Periodic AQMS Exports**: Real-time station feeds and verified historical periodic dumps for 9 pollutants, plus station meteorology.
2. **Aviation Weather METAR API**: Surface aviation weather observations from 12 key airports across Punjab and transboundary corridors (NOAA/NWS).
3. **WMO SYNOP Surface Observations**: Synoptic weather reports from 7 certified meteorological observatories via Ogimet.
4. **ECMWF IFS via Open-Meteo API**: High-resolution (0.25°) Integrated Forecasting System numerical weather prediction model wind fields at 10m and 925 hPa vertical levels.
5. **NASA FIRMS Thermal Anomaly Stream**: VIIRS satellite fire radiative power and agricultural crop residue burning detections from NOAA-20 and NOAA-21 satellites.
6. **IQAir Global Sensor Feed**: Real-time cross-border air quality monitoring network and model estimates across Pakistani and Indian border cities.
7. **Copernicus Atmosphere Monitoring Service (CAMS)**: ECMWF boundary particulate matter fields for transboundary mass flux estimation.

Live data ingestion operates on a dual-tier strategy:
- **Baseline Snapshot**: A comprehensive precomputed bundle embedded in `index.html` as `window.DATA` (covering 216 continuous hours from 2026-11-01 00:00 to 2026-11-09 23:00 PKT).
- **Dynamic Live Ingestion**: A background hourly cloud scraper (`collector/collector.py`) populating an internal document database (`db.collection('hours')`), which the client stream-subscribes to via reactive listeners (`onSnapshot`) and merges using `window.extendData()`.

---

## 2. Features Discovered

| # | Category | Feature | Description | Inputs | Outputs | Error Behavior | Discovered Via |
|---|----------|---------|-------------|--------|---------|----------------|----------------|
| 1 | Air Quality Station Feed | EPA Punjab Live Dashboard API | Polls all active EPA Punjab AQMS stations in a single call | HTTP GET to `/api/dashboard/current`, User-Agent `EMC-EPA-Punjab-AQ-dashboard/1.0` | JSON object containing array of station records (AQI, PM2.5, PM10, NO2, SO2, CO, O3, wind speed, wind direction, flags) | Returns HTTP error code or parse failure; logged in `src.portal`, falls back to district endpoints | `collector/collector.py` lines 94–105 |
| 2 | Air Quality Station Feed | EPA Punjab District Directory API | Lists all recognized districts to identify missing stations | HTTP GET to `/api/districts` | JSON list of district names | Silently caught, empty list returned | `collector/collector.py` lines 108–114 |
| 3 | Air Quality Station Feed | EPA Punjab District-Stations API | Fetches station readings for districts omitted from main dashboard feed | HTTP GET to `/api/district-stations/{district_name}` (URL encoded) | JSON array of station records tagged with `_extra=true` | Network/parse errors ignored per district | `collector/collector.py` lines 115–121 |
| 4 | Aviation Meteorology | Aviation Weather METAR API | Trailing 6-hour meteorological aerodrome reports for 12 airports | HTTP GET to `aviationweather.gov/api/data/metar?ids={ICAO}&format=json&hours=6` | JSON array of METAR records (wind dir, speed, gust, vis, temp, wx, rawOb) | Recorded in `src.metar`; falls back to district AQMS station wind | `collector/collector.py` lines 123–132 |
| 5 | Synoptic Meteorology | WMO SYNOP via Ogimet | Surface synoptic weather telegrams for blocks 415, 416, 417 | HTTP GET to `www.ogimet.com/cgi-bin/getsynop?block={blk}&begin={b}&end={e}` | Plain text lines in WMO FM-12 `AAXX` format | Logged in `src.wmo`; missing hours omitted from wind table | `collector/collector.py` lines 133–141 |
| 6 | Numerical Weather Prediction | ECMWF IFS 10-m Wind (Open-Meteo) | Hourly 10m wind speed and direction at 41 district centroids | HTTP GET to `api.open-meteo.com/v1/forecast` with lat/lon lists, model `ecmwf_ifs025` | JSON list of objects with hourly time series for `wind_speed_10m` and `wind_direction_10m` | Logged in `src.ecmwf`; falls back to IDW spatial wind interpolation | `collector/collector.py` lines 143–158 |
| 7 | Regional Wind Grid | ECMWF IFS 0.25° Grid (10m & 925 hPa) | 15×15 0.5° resolution meteorological grid covering Punjab and NW India | Precomputed 225-point grid: latitudes 27.5°–34.5°N, longitudes 69.0°–76.0°E | 2D vector arrays `u10`, `v10`, `u925`, `v925` across 216 hours | Falls back to calm / zero particle flow if ECMWF layer disabled | `index.html` line 262 (`DATA.ecm`), lines 252, 9562602 |
| 8 | Boundary Wind | Cross-Border Boundary Wind Flux | Transboundary perpendicular wind components evaluated along 39 boundary normal vectors | 39 border sample points `tbgeo.samples` with normal unit vectors and border distance | Precomputed hourly `xb10` and `xb925` scalar series | If wind speed < 0.5 m/s, flux is zero | `index.html` line 262 (`tbgeo`), lines 291–294 |
| 9 | Agricultural Fires | NASA FIRMS VIIRS Thermal Anomalies | Satellite-detected active fires (crop residue burning) by subnational region | Daily fire counts from NOAA-20 & NOAA-21 VIIRS (2–9 Nov) | Tabular counts for 11 regions + spatial point overlays on map figures | Footnoted caveats regarding gas flaring and partial daily passes | `index.html` lines 240–242, 228–231 |
| 10 | Cross-Border Air Quality | IQAir City Sensor Readings | Real-time ground sensor and model AQI for cities bordering Punjab | Station feeds and model estimates for Peshawar, Jammu, New Delhi, Bathinda, Jodhpur | US AQI, PM2.5 (µg/m³), contributor station count, 2-day forecast | Distinguishes physical sensors from daily model estimates | `index.html` lines 243–246 |
| 11 | Atmospheric Modeling | CAMS Regional PM2.5 Flux | Transboundary boundary inflow/outflow calculated with CAMS PM2.5 | 117 transboundary boundary points (~25 km spacing), CAMS PM2.5 × ECMWF 10m wind | Transboundary Inflow Index ranking border sectors and days | Not treated as absolute mass budget due to CAMS low bias | `index.html` line 226 |
| 12 | Real-Time Extension | Database Collection Live Listener | Real-time document stream synchronization using client DB SDK | `claude.use('db')` collection `'hours'`, limit 1000, `onSnapshot` | Array of hourly document snapshots passed to `window.extendData()` | 9-second timeout fallback to static baseline `window.DATA` | `index.html` lines 9608950–9609100 |
| 13 | Coordinate Mapping | Station Coordinate Correction | Manual overrides for corrupted GIS coordinates in EPA Punjab shapefile | Station names (Gulberg III, DC Office Sialkot, Wazirabad, Sahiwal, etc.) | Corrected latitude/longitude decimal degrees (WGS84) | Sahiwal, Rajanpur, Talagang, Khushab use approximate town centers | `index.html` line 254; `collector.py` lines 41–51 |
| 14 | Data Quality Control | Multi-stage Outlier & Flatline Filter | Real-time cleaning pipeline for station pollutant streams | Raw hourly time series per station and pollutant | Cleaned hourly arrays with outliers set to `null` | Evaluates 7-hour rolling median (>4× med & >3× ref) and 3-hour hold | `index.html` lines 316–328; `collector.py` line 213–218 |
| 15 | Meteorological Hierarchy | Three-tier Wind Fallback Chain | Determines best available wind vector for each district | Station vane -> Airport METAR -> ECMWF IFS -> IDW spatial interpolation | `[u, v]` wind vector in m/s (scaled by `ecm_ratio = 0.227` for model/METAR) | If all sources fail, sets district wind to `[null, null]` | `index.html` lines 330–342; `collector.py` lines 221–263 |

---

## 3. Detailed Data Stream & API Endpoint Specifications

### 3.1 Stream 1: EPA Punjab Public Portal & Periodic Exports

#### 3.1.1 Network Endpoints
- **Base URL**: `https://aqi.punjab.gov.pk`
- **Endpoints**:
  1. `GET /api/dashboard/current` — Current readings for all primary AQMS stations.
  2. `GET /api/districts` — List of all active districts.
  3. `GET /api/district-stations/{district_name}` — Specific station readings for a given district.
- **HTTP Method**: `GET`
- **Query Parameters**: None.
- **Headers**:
  - `User-Agent`: `EMC-EPA-Punjab-AQ-dashboard/1.0`
- **Authentication**: None (open public API).
- **Transport Security**: HTTPS (TLS 1.2+).
- **Client Implementation**: Executed via system `curl -sS -L --max-time 40` in `collector.py`.

#### 3.1.2 Request & Response Schema
- **Request Payload**: None.
- **Response Format**: JSON.
- **Top-level Structure**:
  ```json
  {
    "status": "success",
    "data": [
      {
        "station_id": 10,
        "station_name": "DHQ Sheikhupura",
        "district": "Sheikhupura",
        "timestamp": "2026-11-09T23:00:00.000Z",
        "aqi": 215.0,
        "pm25": 165.2,
        "pm10": 280.5,
        "no2": 45.1,
        "so2": 12.3,
        "co": 1.8,
        "o3": 25.4,
        "wind_speed": 1.2,
        "wind_direction": 180.0,
        "pollutant_flags": null
      }
    ]
  }
  ```
- **Fields, Units, and Valid Ranges**:
  | Field | Type | Unit | Valid Range | Description |
  |---|---|---|---|---|
  | `station_id` | Integer/String | Dimensionless | 1–200 | Numeric portal identifier |
  | `station_name` | String | Dimensionless | Text | Display name of the monitoring station |
  | `district` | String | Dimensionless | Text | District name (41 districts in Punjab) |
  | `timestamp` | String (ISO-8601) | UTC/PKT | ISO format | Stamped hour of observation |
  | `aqi` | Float | Index (PEPC) | 0–500+ | Composite Punjab Air Quality Index |
  | `pm25` | Float | µg/m³ | 0–1000 | Fine particulate matter (≤ 2.5 µm) |
  | `pm10` | Float | µg/m³ | 0–1500 | Coarse particulate matter (≤ 10 µm) |
  | `no2` | Float | µg/m³ | 0–500 | Nitrogen dioxide |
  | `so2` | Float | µg/m³ | 0–500 | Sulfur dioxide |
  | `co` | Float | mg/m³ | 0–50 | Carbon monoxide |
  | `o3` | Float | µg/m³ | 0–400 | Ground-level ozone |
  | `wind_speed` | Float | m/s | 0.0–30.0 | Surface wind speed |
  | `wind_direction` | Float | Degrees | 0.0–360.0 | Wind origin direction (azimuth) |
  | `pollutant_flags` | Object/List | Dimensionless | String tags | Automated hardware/sensor error flags |

#### 3.1.3 Polling Frequency & Refresh Cadence
- **Cadence**: Hourly (triggered at :05 to :15 minutes past every hour to allow sensor ingestion).
- **Batch Exports**: Periodic official dumps:
  - 1–4 November periodic export: 56 stations.
  - 4 Nov 00:00 to 5 Nov 11:00 interim update.
  - 1–9 November periodic export: 80 stations (incorporating 24 new tehsil-level sites).

---

### 3.2 Stream 2: Aviation Weather METAR Stream

#### 3.2.1 Network Endpoints
- **Base URL**: `https://aviationweather.gov`
- **Endpoint**: `GET /api/data/metar`
- **HTTP Method**: `GET`
- **Query Parameters**:
  - `ids`: `OPLA,OPFA,OPMT,OPST,OPIS,OPRN,OPRK,OPBW,OPDG,OPSR,OPMI,VIAR`
  - `format`: `json`
  - `hours`: `6`
- **Headers**:
  - `User-Agent`: `EMC-EPA-Punjab-AQ-dashboard/1.0`
- **Authentication**: None.
- **Client Implementation**: `curl -sS -L --max-time 40` in `collector.py`.

#### 3.2.2 Station Roster & Coverage
| ICAO | Airport Name | City / District | Latitude | Longitude | Role |
|---|---|---|---|---|---|
| `OPLA` | Allama Iqbal International Airport | Lahore | 31.522°N | 74.404°E | Primary provincial hub |
| `OPFA` | Faisalabad International Airport | Faisalabad | 31.365°N | 72.995°E | Central industrial belt |
| `OPMT` | Multan International Airport | Multan | 30.203°N | 71.419°E | South-central Punjab |
| `OPST` | Sialkot International Airport | Sialkot | 32.535°N | 74.364°E | Northeast industrial triangle |
| `OPIS` | Islamabad International Airport | Rawalpindi/Islamabad | 33.565°N | 72.852°E | Northern plateau |
| `OPRN` | Benazir Bhutto International (Old) | Rawalpindi | 33.616°N | 73.099°E | Northern backup |
| `OPRK` | Shaikh Zayed International Airport | Rahim Yar Khan | 28.384°N | 70.280°E | Southern gateway |
| `OPBW` | Bahawalpur Airport | Bahawalpur | 29.348°N | 71.718°E | Cholistan border corridor |
| `OPDG` | Dera Ghazi Khan Airport | D.G. Khan | 29.961°N | 70.486°E | Trans-Indus western corridor |
| `OPSR` | PAF Base Mushaf | Sargodha | 32.049°N | 72.666°E | Central agricultural belt |
| `OPMI` | PAF Base Mianwali | Mianwali | 32.563°N | 71.524°E | Western salt range corridor |
| `VIAR` | Sri Guru Ram Dass Jee Intl Airport | Amritsar (India) | 31.709°N | 74.797°E | **Transboundary baseline anchor** |

#### 3.2.3 Response Schema & Transformation
- **Response Format**: JSON Array of METAR objects.
- **Extracted Fields**:
  - `wdir`: integer degrees (0–360) or `"VRB"`.
  - `wspd`: wind speed in knots (converted to m/s via `* 0.5144`).
  - `wgst`: wind gust in knots.
  - `visib`: visibility in statute miles (converted to meters via `* 1609.34`) or parsed from METAR 4-digit metric group (`rawOb`).
  - `temp`: temperature in °C.
  - `wxString`: decoded meteorological string:
    - `"FU"` -> `smoke`
    - `"HZ"` -> `haze`
    - `"BR"` -> `mist`
    - `"FG"` -> `fog`
    - `"DU"` -> `dust`
    - `"RA"` -> `rain`
    - `"TS"` -> `thunderstorm`
- **Output Document Array**: `[dir deg | "CALM" | "VRB", speed kt, vis m, temp C, wx string, gust kt, obs time UTC ISO]`.
- **Temporal Alignment**: Nearest observation within 35 minutes of the target PKT hour.

---

### 3.3 Stream 3: WMO SYNOP Surface Meteorological Stream

#### 3.3.1 Network Endpoints
- **Base URL**: `https://www.ogimet.com`
- **Endpoint**: `GET /cgi-bin/getsynop`
- **HTTP Method**: `GET`
- **Query Parameters**:
  - `block`: `415`, `416`, `417`
  - `begin`: `YYYYMMDDHH00` (trailing 7 hours UTC)
  - `end`: `YYYYMMDDHH59`
- **Headers**: User-Agent `EMC-EPA-Punjab-AQ-dashboard/1.0`.
- **Authentication**: None.

#### 3.3.2 Monitored Synoptic Stations
| WMO ID | Station Name | Latitude | Longitude | Block |
|---|---|---|---|---|
| `41640` | Lahore PBO | 31.550°N | 74.330°E | 416 |
| `41641` | Lahore Airport | 31.520°N | 74.400°E | 416 |
| `41571` | Islamabad | 33.620°N | 73.100°E | 415 |
| `41598` | Jhelum | 32.930°N | 73.720°E | 415 |
| `41600` | Sialkot | 32.500°N | 74.530°E | 416 |
| `41675` | Multan | 30.200°N | 71.430°E | 416 |
| `41700` | Bahawalpur | 29.400°N | 71.680°E | 417 |

#### 3.3.3 Telegram Parsing Rules (FM-12 SYNOP)
- Filter line containing `AAXX`.
- Extract group 1 wind indicator `iw` (last digit):
  - `0` / `1`: wind speed in m/s (estimated / anemometer).
  - `3` / `4`: wind speed in knots (estimated / anemometer).
- Extract group 4 `nddff`:
  - `dd`: wind direction in tens of degrees (00 = calm, 01–36 = 10°–360°, 99 = variable/null).
  - `ff`: wind speed. If `ff == 99`, inspect overflow group `00fff`.
- Speed conversion:
  - If `iw in ('3', '4')`: `ms = ff * 0.5144`
  - If `iw in ('0', '1')`: `ms = ff`
- Output Schema: `[dir deg | null, speed m/s, obs time UTC ISO]`.

---

### 3.4 Stream 4: ECMWF IFS Atmospheric Model via Open-Meteo

#### 3.4.1 Point Forecast Query (Collector District Centroids)
- **Base URL**: `https://api.open-meteo.com`
- **Endpoint**: `GET /v1/forecast`
- **Query Parameters**:
  - `latitude`: Comma-delimited list of 41 district centroid latitudes.
  - `longitude`: Comma-delimited list of 41 district centroid longitudes.
  - `hourly`: `wind_speed_10m,wind_direction_10m`
  - `models`: `ecmwf_ifs025`
  - `wind_speed_unit`: `ms`
  - `timezone`: `Asia/Karachi`
  - `past_days`: `1`
  - `forecast_days`: `1`
- **Response**: Array of 41 JSON objects matching order of coordinates, each containing hourly timestamps, wind speeds, and directions.
- **Timeout**: 60 seconds (`subprocess.run` timeout 70s).

#### 3.4.2 Provincial Grid (Embedded `DATA.ecm`)
- **Spatial Bounds**: 27.5°N to 34.5°N (15 grid steps of 0.5°), 69.0°E to 76.0°E (15 grid steps of 0.5°).
- **Total Points**: 225 nodes covering all Punjab districts and surrounding international territory.
- **Vertical Levels**:
  - `10 m` surface canopy level (`u10`, `v10` arrays: 216 hours × 225 cells).
  - `925 hPa` boundary layer transport level (~750 m altitude, `u925`, `v925` arrays: 216 hours × 225 cells).
- **Model Scaling**:
  - Surface roughness adjustment factor: `KR = DATA.meta.ecm_ratio` (0.22686 in baseline data, fallback default 0.34).
  - Applied to reconcile model free-atmosphere winds with sheltered urban ground stations.

---

### 3.5 Stream 5: NASA FIRMS Thermal Anomalies (Active Fires)

#### 3.5.1 Satellite Platform & Sensors
- **Sensors**: VIIRS (Visible Infrared Imaging Radiometer Suite) 375 m resolution.
- **Satellites**: NOAA-20 (JPSS-1) and NOAA-21 (JPSS-2).
- **Payload Coverage**: Daily daytime and nighttime overpasses from 2 November to 9 November 2026.
- **Jurisdictional Breakdown**:
  - Punjab (Pakistan): 6,703 detections (matching official EMC FIRMS archive).
  - Punjab (India): 3,239 detections.
  - Rajasthan (India): 2,834 detections (1,507 south of 27°N, gas flares in Barmer, 276 north of 28.5°N).
  - Sindh (Pakistan): 409 detections.
  - Haryana (India): 363 detections.
  - Khyber Pakhtunkhwa: 248 detections.
  - Himachal Pradesh: 128 detections.
  - Jammu & Kashmir (India): 59 detections.
  - Balochistan: 52 detections.
  - Azad Kashmir: 9 detections.
  - Islamabad: 0 detections.
- **Decoupled API Contract**:
  - Base: `https://firms.modaps.eosdis.nasa.gov/api/area/csv/{MAP_KEY}/VIIRS_NOAA20_NRT/{min_lon,min_lat,max_lon,max_lat}/{days}`.

---

### 3.6 Stream 6: IQAir Sensor Network & Regional Readings

#### 3.6.1 City & Station Inventory
- **Benchmark Timestamp**: 2026-11-09 ~23:00 PKT.
- **Reporting Cities**:
  - Peshawar (KPK): US AQI 471, PM2.5 311.0 µg/m³ (9 low-cost sensors across 4 community contributors).
  - Jammu (J&K): US AQI 277, PM2.5 202.2 µg/m³ (CPCB/PPCB continuous reference station).
  - New Delhi (Delhi): US AQI 271, PM2.5 196.0 µg/m³ (CPCB/DPCC regulatory network).
  - Bathinda (Punjab, India): US AQI 250+, PM2.5 ~180 µg/m³ (PPCB monitoring station).
  - Jodhpur (Rajasthan): US AQI 70, PM2.5 19.5 µg/m³ (5 CPCB stations).
- **Scale Distinction**: Uses US EPA AQI breakpoints, distinct from EPA Punjab AQI breakpoints.
- **Model Fallback**: Cities without physical sensor hardware display IQAir daily numerical model estimates.

---

### 3.7 Stream 7: Internal Real-Time Database Stream (`claude.use('db')`)

#### 3.7.1 Database Architecture
- **Engine**: Internal document datastore accessed via SDK `claude.use('db')`.
- **Target Collection**: `'hours'`
- **Document Key Convention**: `h<YYYYMMDDHH>` (e.g. `h2026110923`).
- **Subscription API**: `db.collection('hours').limit(1000).onSnapshot(callback, errorCallback)`
- **Timeout**: 9,000 ms watchdog timer (`setTimeout(..., 9000)`).
- **Document Payload Structure**:
  ```json
  {
    "t": "2026-11-09 23:00",
    "st": {
      "Safari Park-LHR": [215, 165.2, 280.5, 45.1, 12.3, 1.8, 25.4, 1.2, 180.0]
    },
    "ap": {
      "OPLA": [180.0, 4.0, 2000, 22.0, "smoke, haze", null, "2026-11-09T18:00:00Z"]
    },
    "wmo": {
      "41640": [180.0, 2.0, "2026-11-09T18:00:00Z"]
    },
    "ecm": {
      "Lahore": [2.15, 175.0]
    },
    "src": {
      "portal": "ok 79 stations",
      "metar": "ok 12 reports",
      "wmo": "ok 7 reports",
      "ecmwf": "ok 41 points"
    },
    "upd": "2026-11-09T23:15:02Z"
  }
  ```

---

## 4. Quality Control, Outlier Detection, & Anomaly Handling

Both `collector/collector.py` and `window.extendData()` implement rigorous data cleaning rules:

### 4.1 Missing Values, Zeros, & Flagged Readings
1. **Pollutant Flags**: If `pollutant_flags` exists on the portal record, any pollutant mentioned in the flag string (e.g., `pm25`, `pm2.5`, `no2`) is set to `null`.
2. **Zeros and Negative Values**: Any concentration reading `<= 0` or non-numeric (`NaN`) is discarded (`null`).
3. **Valid Hour Constraint**: A station's composite AQI is calculated and admitted into the hourly average **only if that station has a valid PM2.5 or PM10 reading** in that hour.

### 4.2 Spike Filtering
- Evaluated over a 7-hour rolling window centered on hour $i$: $[i-3, \dots, i+3]$.
- Computes the window median of valid readings ($med$).
- A reading $v$ is flagged as an invalid spike and set to `null` if:
  $$v > 4 \times med \quad \text{AND} \quad v > 3 \times \text{ref}$$
  Where $\text{ref}$ is the statutory pollutant limit ($\text{AQI}=200, \text{PM}_{2.5}=35, \text{PM}_{10}=150, \text{NO}_2=80, \text{SO}_2=120, \text{CO}=5, \text{O}_3=130, \text{NO}=40$).

### 4.3 Logger Hold (Stuck Sensor) Detection
- For all chemical pollutants (excluding aggregate `AQI`):
  $$\text{If } v_{i} = v_{i-1} = v_{i-2} \implies v_i = \text{null}$$
  Eliminates field datalogger artifacts where a communications failure causes the datalogger to repeat its last known value indefinitely.

### 4.4 Anemometer Anomaly Rejection
1. **Wazirabad Vane Blacklist**: Wazirabad AQMS wind vane was verified to have an approximate 140° physical misalignment. Its wind values are blacklisted (`NOWIND = new Set(['Wazirabad'])`).
2. **Extreme Speed Threshold**: Discards any wind reading with $\text{speed} < 0$ or $\text{speed} > 30 \text{ m/s}$ (e.g. DC Office Chakwal erroneously transmitting wind direction in the speed register; DC Office Khanewal transmitting error code `99.9`).
3. **Calm Threshold**: Wind speeds $< 0.5 \text{ m/s}$ (~1 knot) are treated as aerodynamic calms (`CALM`). Direction is omitted from directional flux and CPF calculations.

---

## 5. Fallback Mechanisms, Timeouts, and Reliability Matrices

### 5.1 Meteorological Fallback Hierarchy
When calculating district-level wind for spatial interpolation and transboundary flux:
```
           [ Monitored District ]
                     │
           ┌─────────┴─────────┐
    Station Wind Valid?       NO
           │                   │
         [YES]           Airport METAR Available?
           │                   │
     Use Vector Mean         [YES]           NO
     of Station Winds          │              │
                        Scale METAR     ECMWF IFS 10-m
                        by ecm_ratio      Wind Available?
                                              │
                                            [YES]           NO
                                              │              │
                                         Scale ECMWF    Mark District
                                        by ecm_ratio     Wind as NULL
```
For unmonitored / estimated districts (`est = true`):
1. Inverse Distance Weighting (IDW) interpolation of surrounding monitored district winds.
2. If IDW fails (insufficient monitored winds): Direct ECMWF IFS 10-m model wind.
3. If both fail: `[null, null]`.

### 5.2 Network Resilience & Timeout Matrix
| Network Call | Timeout | Retry Policy | Fallback Behavior |
|---|---|---|---|
| `aqi.punjab.gov.pk/api/dashboard/current` | 40 seconds | Single curl invocation, follows redirects (`-L`) | Retries district endpoints; if entirely down, records status in `src.portal` and writes meteorology-only doc |
| `aviationweather.gov/api/data/metar` | 40 seconds | Single curl invocation | Status logged; district wind falls back to station wind or ECMWF |
| `ogimet.com/cgi-bin/getsynop` | 40 seconds | Sequential iteration across 3 blocks | If empty or block fails, proceeds with available telegrams |
| `api.open-meteo.com/v1/forecast` | 60 seconds | Single multi-coordinate batch request | Fallback to IDW spatial interpolation; logs error |
| `claude.use('db')` stream | 9,000 ms (9s) | Watchdog timer (`setTimeout`) | Automatically clears listener and initializes UI using precomputed `window.DATA` |

---

## 6. Comprehensive Edge Cases Table

| # | Feature | Input / Condition | Observed Behavior |
|---|---------|-------------------|-------------------|
| 1 | Portal Station Mapping | New station appears in portal feed with unmapped `station_id` (e.g. ID `250`) | Station is appended to `unknown` list; excluded from district averaging to prevent misallocation |
| 2 | DC Office Chakwal Wind | Station transmits direction (e.g. `270`) in the `wind_speed` register | Filtered out by `ws > 30` m/s sanity check; district wind falls back to METAR/ECMWF |
| 3 | DC Office Khanewal Wind | Station transmits hardware error code `99.9` in `wind_speed` | Filtered out by `ws > 30` m/s rule; treated as invalid |
| 4 | Wazirabad Station Wind | Valid wind speed and direction reported by Wazirabad anemometer | Completely suppressed by `NOWIND.has('Wazirabad')` set; uses METAR/ECMWF |
| 5 | Airport Wind Calm | METAR reports `wspd = 0` or string `"CALM"` | Vector converted to `u = 0, v = 0`; excluded from directional transport flux |
| 6 | Airport Variable Wind | METAR reports `wdir = "VRB"` | Velocity recorded as variable; directional vector set to null |
| 7 | Metric Visibility Group | METAR `rawOb` contains 4-digit metric group (e.g. `1200`) while `visib` is statute miles | Regex `\s(\d{4})\s` extracts exact metric integer meters over statute mile conversion |
| 8 | WMO SYNOP Variable Wind | Group `nddff` has `dd = 99` | Parsed as `dir = null`, preventing erroneous 990° direction |
| 9 | WMO SYNOP Speed Overflow | Group `nddff` has `ff = 99` | Parser inspects auxiliary group `00fff` to extract speed > 99 kt |
| 10 | Complete Portal Outage | EPA Punjab portal server blocked, unreachable, or HTTP 500 | Scraper generates fallback hourly document stamped with latest hour; records METAR, WMO, and ECMWF winds |
| 11 | Sensor Flatline / Freeze | Station datalogger hangs, transmitting identical non-zero value for 3+ consecutive hours | Outlier filter suppresses 3rd and subsequent identical readings (`hold = true`) |
| 12 | Extreme Isolated Spike | Chemical sensor registers brief transient spike > 4× 7-hr median and > 3× PEQS | Filter zeroes out spike (`spk = true`), logged in `spikes[p]` counter |
| 13 | Cross-Border Normal Wind | Wind blowing parallel to the international border ($\Delta \theta = 90^\circ$) | Normal dot product equals zero; zero cross-border flux recorded |
| 14 | Database Connection Failure | Client runtime has no access to `claude.use('db')` (e.g. standalone browser) | Catch block catches exception; immediately displays static baseline `window.DATA` |
| 15 | Live Subscription Timeout | Live database query hangs or exceeds 9 seconds | Timer triggers, cancels pending load, displays warning banner, and boots dashboard with static export |
| 16 | OneNetwork Station 25 | Station 25 present in network exports | Excluded from provincial calculations due to completely unknown geographic coordinates |
| 17 | New Tehsil Stations | 24 tehsil stations reporting data without shapefile entries | Assigned approximate town-center coordinates to allow full 41-district spatial coverage |

---

## 7. Conclusions & Architectural Recommendations for Pipeline Decoupling (R3 / R4)

1. **Eliminate Monolithic Single-File Ingestion**:  
   The current system bundles 9.6 MB of static data directly into `index.html`. This must be extracted into independent, modular data pipelines running in asynchronous scheduled services.
2. **Dedicated Micro-Pipelines per Stream**:
   - `EPA-Punjab-Pipeline`: Dedicated scraper for portal endpoints + shapefile GIS reconciliation.
   - `Aviation-Weather-Pipeline`: Dedicated NOAA METAR consumer with resilient retry and schema validation.
   - `Synoptic-Meteorology-Pipeline`: WMO SYNOP decoder parsing raw GTS telegrams.
   - `Atmospheric-Model-Pipeline`: Asynchronous ECMWF IFS batch fetcher via Open-Meteo with caching.
   - `Thermal-Anomaly-Pipeline`: Scheduled NASA FIRMS API consumer replacing manual table updates.
   - `Regional-AirQuality-Pipeline`: Automated IQAir API poller for border baseline verification.
3. **Canonical Normalization Schema**:  
   All streams must normalize into a standardized geo-temporal record structure (WGS84 decimal coordinates, SI metric units: m/s, µg/m³, mg/m³, UTC timestamps with PKT presentation layer).
4. **Resilient Local Persistence**:  
   Replace in-memory document blobs with an indexed time-series database (e.g., PostgreSQL/TimescaleDB or DuckDB/SQLite), decoupling the UI completely from the raw collection infrastructure.
