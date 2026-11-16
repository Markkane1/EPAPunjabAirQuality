# Spec vs implementation gaps — SystemSpecs-16-11-2026-grok

**Document ID:** `SystemSpec-16-11-2026-grok-gaps`  
**Issued:** 16 November 2026  
**Input spec:** `docs/SystemSpecs-16-11-2026-grok.md` (Document ID `SystemSpecs-16-11-2026-grok`, 20 sections)  
**This file is a verification report.** It is not a restatement of the spec, not a chat recap, and not a copy of `docs/Issuestoday.md`, `docs/SystemSpecs-16-11-2026-Gemini.md`, or `docs/TRANSFORMATION_LOGIC_SPEC.md`. Those siblings were not used as sources of truth.

**Method.** Checkable claims were extracted from the grok spec (20 `##` sections, 77 `###` headings, 53 capability rows, named constants C01–C96). Each claim was compared to:

1. **Original System** — `original System/index.html` (9,609,848 bytes) by sectional parse of Method notes, `window.extendData`, `#mainsrc`, UI ids, and `window.DATA` *structure* (meta, inventories, CPF roses, `qa`, `tbgeo`, `ecm` keys). Hourly observation arrays were not inlined. Collector: `original System/collector/collector.py` (16,362 bytes).
2. **Current tree** — `src/domain/math/`, `src/pipelines/`, `src/api/`, `src/frontend/` (dashboard console), `src/workstation/` (Deck.gl workstation), `data/baseline/`, root `index.html`, `dist/workstation.html`. Root `frontend/` is not present in this checkout.

**Verdict vocabulary** (one per layer):

| Verdict | Meaning |
|---------|---------|
| **match** | Implementation agrees with the spec at the named constant, formula, id, or contract |
| **spec error** | Spec disagrees with `original System/` |
| **implementation gap** | Spec requires it; that layer does not provide it as specified |
| **absent from repo** | Named artifact is not in this tree |
| **out of baseline / N/A** | Spec §19 disclaimer, or the claim does not apply to that layer |

Scratch evidence (not part of the repo): `{SCRATCH}/spec_claims.txt`, `baseline_compare.txt`, `current_compare.txt`, `orig_extend.js`, `orig_mainsrc.js`, `orig_data_slice.txt`, `orig_cpf_attock.txt`, `current_needles.txt`.

---

## 0. How to read the current tree

The current checkout is **not one implementation**. Three surfaces must be named whenever they disagree:

| Surface | Path | Role vs the spec |
|---------|------|------------------|
| **Dashboard console** | `src/frontend/dashboard.html` + `static/js/{app,canvas,geo,api,ui}.js` | Closest port of the November canvas workstation (PEPC RGB, Surface/District radios, 0.35/0.8/1.6 speeds, transport/regional-wind checkboxes, 3×3 grid tab, Lahore tab) |
| **Workstation** | `src/workstation/` + root `index.html` / `dist/workstation.html` | Five-zone Deck.gl rewrite. Title `EPA Punjab Air Quality`. Legend is a different scale |
| **Pipelines / API / math** | `src/pipelines/`, `src/api/`, `src/domain/math/` (Python + TypeScript twins) | Live ingest + FastAPI `/api/v1/` + shared math. Live EPA worker hits `https://api.epd-aqms-pk.com` (38 stations), not `https://aqi.punjab.gov.pk` |

`data/baseline/stations.json` still has **79** stations and `districts.json` **41** districts — the frozen cube matches original `window.DATA` inventory even though the live catalog is 38 stations / ~19 cities.

Spec §19 already says `src/` is not the specified system. This report still scores it, because the objective is to verify the spec against the **actual implementation in the repo now**.

---

## 1. Headline findings

1. **Original System matches the grok spec.** Product identity, 216-hour cube, 79/41 network, EPA Punjab 7-tier RGB, PEPC upper bounds, transport `C × w × cos(Δ) × e^(−km/100)` with 180 km / ±35° / LS=100 / calm 0.5, CPF 16×22.5° P75 with n<6 suppression, IDW d0=5, `fieldAt` wind-weighted continuum, QC spike/hold/Wazirabad/ws>30, collector portal/METAR/SYNOP/ECMWF, `extendData` + 9 s `claude.use('db')` bootstrap, UI ids, autoplay + 66 ms/200 ms stall timer, empty `drawTB`, unused `drawNodes`/`wscale`, Lahore card in `<div hidden>`, `#xbAll` snapshots. **No material spec error** against `original System/` was found.
2. **Companion Word / named-download / October ancestor HTML files are absent from this repo.** Spec already says the Word files live in conversation deliveries, not inside `original System/`. Verdict: **absent from repo** on both layers.
3. **Current tree is a different product with a partial math port.** Flux/CPF/IDW/QC/projection constants largely match. Live EPA endpoint, station count, AQI *computation*, workstation legend, animation fallback, collector packaging, `#ecmLev` / `#apHr` / `#xbAll`, persistence×diurnal forecast, mixing-height section, and 26 May advisory are gaps.
4. **Two current UIs disagree with each other.** Dashboard `canvas.js` `AQI_B` matches the spec RGB; workstation `state.ts` `LEGEND` uses `#009966` / merged 101–200 Moderate / Poor / Very Poor / Severe.

---

## 2. Dual-tree architecture (named in the spec)

| Spec claim | Original System | Current tree |
|------------|-----------------|--------------|
| Offline single-file HTML + stdlib collector | **match** — `original System/index.html` + `collector/collector.py` | **implementation gap** — FastAPI + Vite/React + TimescaleDB path; viewing requires the app server |
| No application server required to *view* the baseline | **match** | **implementation gap** — root `index.html` loads `/src/main.tsx`; dashboard talks to `/api/v1/` |
| `window.DATA` / `window.extendData` / `#mainsrc type=text/plain` | **match** | **implementation gap** — none of those symbols exist under `src/` |
| Live hours collection `hours`, doc id `hYYYYMMDDHH`, fields `t/st/ap/wmo/ecm/src/upd` | **match** in collector + last script | **implementation gap** — TimescaleDB observations; no hour-docs |
| Spec §19: FastAPI/React/TimescaleDB/Deck.gl is out of baseline | **out of baseline / N/A** | **out of baseline / N/A** as a spec-coverage claim; scored below as the live implementation |

---

## 3. Section-by-section dual verdicts

### 3.1 §1 System identity

| Named item | Spec | Original | Current | Orig verdict | Current verdict |
|------------|------|----------|---------|--------------|-----------------|
| Product title (h1) | Punjab Air Quality, November 2026 | `<h1>` exact | Dashboard h1 `Punjab Air Quality Console`; workstation `EPA Punjab Air Quality`; root `<title>` `EPA Punjab Air Quality Monitoring, Processing, and Visualization System` | **match** | **implementation gap** |
| HTML `<title>` copy | Punjab Air Quality November 2026 (Copy) | exact | Dashboard `Punjab Air Quality Operational Console` | **match** | **implementation gap** |
| Eyebrow | EPA Punjab · Environmental Monitoring Center · AQMS network | present | Dashboard sub-org is `… Regional Airshed Telemetry` | **match** | **implementation gap** |
| Temporal extent | 2026-11-01 00:00 … 2026-11-09 23:00 PKT, 216 hours | `DATA.meta` + 216 `hours` strings | `HORIZON_START/END/HOURS=216`; dashboard `totalHours: 216` | **match** | **match** on frozen horizon; live EPA is a different clock |
| Geography | 41 official districts including Wazirabad, Murree, Talagang, Kot Addu, Taunsa | 41 keys, `est:false` all | `data/baseline/districts.json` len=41 | **match** | **match** (baseline); live catalog ~19 cities |
| Stations | 79 mapped (`meta.nstations`); Method also names 80-station export | 79 station names; OneNetwork skipped | baseline 79; `EPA_STATIONS_CATALOG` 38 | **match** | **implementation gap** (live) |
| Monitored / unmon | nmon=41, unmon=[] | exact | baseline all 41; live incomplete | **match** | **match** (baseline cube) |
| Default pollutant | AQI | `setPol('AQI')` | dashboard `pollutant: 'AQI'` | **match** | **match** (dashboard) |
| Calm | 0.5 m/s | `meta.calm: 0.5` | `CALM_WIND_THRESHOLD_MS = 0.5` | **match** | **match** |
| Time zone | Asia/Karachi UTC+5 | collector `PKT`; Open-Meteo timezone | PKT in schemas | **match** | **match** |
| Packaging | One HTML ~9.6 MB, optional live hours | 9,609,848 bytes | split app | **match** | **implementation gap** |

### 3.2 §2 Implemented capabilities

Every ask 1–55 is scored in **§4**. Summary: original System carries asks 1–42 and 55 (dashboard/collector) as **match**; asks 43–54 (Word / forecast / mixing / advisory) are **absent from repo** (conversation products, not inside `original System/`). Current tree: math-backed asks (transport, CPF, IDW, PEPC colours on the dashboard, QC) are **match** with caveats; identity/UI/live-ingest/report asks are **implementation gap** or **absent**.

### 3.3 §3 Packaging and artifacts

| Artifact | Spec | Original | Current | Orig | Current |
|----------|------|----------|---------|------|---------|
| `original System/index.html` | Entire workstation, 9,609,848 bytes, 805 lines, `#mainsrc type=text/plain`, 9 s timeout | FILE 9,609,848; mainsrc plain; `setTimeout(...,9000)` at line 790 | N/A as runtime | **match** | **out of baseline / N/A** (file still in tree, not what runs) |
| `original System/collector/collector.py` | 16,362 bytes; `python3 -I collector.py fetch\|build` | FILE 16,362; CLI exact | Not the live ingest | **match** | **implementation gap** |
| `Punjab_AQI_Situation_Report_05Nov2026.docx` | 5 Nov Word edition | not in `original System/` | not in repo | **absent from repo** | **absent from repo** |
| `Punjab_AQI_Situation_Report_09Nov2026.docx` | 9 Nov Word edition | not in folder | not in repo | **absent from repo** | **absent from repo** |
| `Cover_Letter_Technical_Advisory_10Nov2026.docx` | cover letter | not in folder | not in repo | **absent from repo** | **absent from repo** |
| `Technical_Advisory_Smog_Episode_10Nov2026.docx` | advisory | not in folder | not in repo | **absent from repo** | **absent from repo** |
| `Punjab_Air_Quality_November_2026_Dashboard.html` | named download, no live extend | named file missing; surviving `index.html` still has `claude.use('db')` | named file missing; `dist/workstation.html` is a Vite shell | **absent from repo** (named file); surviving HTML is the live-bootstrap original, which **matches §3.1** not the ask-55 download | **absent from repo** |
| `airport_wind_26Oct2026.csv` / `airport_wind_Nov2026.csv` | METAR extracts | absent | absent | **absent from repo** | **absent from repo** |
| Ancestor pages `punjab_pm10_transport.html`, `punjab_pollutant_transport.html`, `punjab_26oct.html`, `punjab_live.html`, `lahore_air_quality.html` | specified as ancestors | absent from this tree (capabilities carried into November `index.html`) | absent | **absent from repo** as files; **match** as behaviour folded into November HTML | **absent from repo** |
| Runtime shape: Browser(offline) + collector CLI | diagram in §3.3 | **match** | FastAPI `/api/v1/` + SSE | **match** | **implementation gap** |

### 3.4 §4 Time, geography, and monitoring network

| Named item | Original | Current | Orig | Current |
|------------|----------|---------|------|---------|
| §4.1 `meta.start/end`, 216 consecutive PKT hours, hour-beginning | hours_first/last and count 216 extracted | `HORIZON_*`; dashboard scrubber `max=215` | **match** | **match** (frozen cube) |
| Live continuation after `meta.exportEnd` | `extendData` pads empty frames | no `exportEnd` / hour-docs | **match** | **implementation gap** |
| §4.2 41 district names including the five new ones; all `est:false` | 41 keys, `est_true:0` | baseline 41 | **match** | **match** (baseline) |
| Unmonitored IDW engine idle but retained | `idw()` in extendData; hatch in mainsrc | `idw.py` + hatch in dashboard Districts mode | **match** | **match** (engine present) |
| Chiniot / Lodhran no valid PM; AQI suppressed | `qa.Chiniot` AQI n=5, wind_valid=9; `Gymkhana Lodhran` AQI=0, PM10=0, PM2.5=0 | live path uses computed PEPC composite | **match** | **implementation gap** (different AQI rule) |
| §4.3 projection `B={lo0:69.1,lo1:75.75,la0:27.55,la1:34.3}`, `KX=cos(31°)`, `P=(lon-lo0)*KX*S` | `#mainsrc` `const B=...` | `projection.py` same bounds; `geo.js` same `B`/`KX` | **match** | **match** |
| Lahore inset `LB={lo0:74.08,lo1:74.64,la0:31.34,la1:31.70}` | in mainsrc | Lahore tab canvas exists; LB constants not verified as identical | **match** | **implementation gap** (panel present, inset bounds not the same named `LB`) |
| §4.4 79 stations; 11 EMC-confirmed Lahore coords | `EMC confirmed count: 11`; 79 names | baseline 79; live 38 | **match** | **implementation gap** (live) |
| Shapefile Lat/Lon overrides (Gulberg III, Sialkot, Wazirabad) | Method text + coords in DATA | baseline coords follow original | **match** | **match** (baseline) |
| `OneNetwork Station 25` skipped | `"location not known"` in HTML | `EXCLUDED_STATIONS` / epa_punjab comment | **match** | **match** |
| Lahore 13 stations, 5 mobile | inventory in DATA | dashboard Lahore tab | **match** | **match** (dashboard plots Lahore set from baseline) |
| §4.5 collector `DIST` 41 centroids | exact table in `collector.py` | open_meteo queries 41 centroids | **match** | **match** (count/role); confirm coordinate table independently if a future audit needs cell-by-cell |
| §4.6 `PMAP` including `186 → Murree`; `NAME_FALLBACK={"Chiniot":"Chiniot"}` | in collector.py | no `NAME_FALLBACK`; live catalog is station-id API | **match** | **implementation gap** |
| §4.7 station / district / network(56) / qa inventories | 79 stations, 41 districts, 56 network names, qa snippets match spec examples (Lodhran AQI 0, Wazirabad wind_valid 0, Chakwal/Khanewal wind_valid 0) | baseline JSON 79/41; no `window.DATA.qa` blob | **match** | **match** on counts (baseline); **implementation gap** on embedded `qa` object |

### 3.5 §5 Data sources and streams

| Stream | Spec | Original | Current | Orig | Current |
|--------|------|----------|---------|------|---------|
| §5.1 Public portal `https://aqi.punjab.gov.pk` + `/api/dashboard/current` + `/api/districts` + `/api/district-stations/<D>` | collector | `PORTAL` and three paths | `epa_punjab.py` `DEFAULT_BASE_URL = https://api.epd-aqms-pk.com`, API key, GET `/latest_hour`, 38 stations, cron `3 * * * *` | **match** | **implementation gap** |
| UA `EMC-EPA-Punjab-AQ-dashboard/1.0` | collector | `UA = ...` | same string on EPA/METAR/SYNOP/Open-Meteo/CAMS workers | **match** | **match** |
| Portal pollutants AQI+PM+gases+wind; **not** NO/NOx | `POLF` | `POLF=['aqi','pm25','pm10','no2','so2','co','o3']` | live EPA schema includes more species; dashboard still has NO/NOx buttons | **match** | **implementation gap** (different feed) |
| `pollutant_flags` null named species | collector stringify | present | live path uses `status_*` Incomplete/N/A/Invalid | **match** | **implementation gap** (different flag contract) |
| `aqi.epaforecast.com` gated, unused | diagnosed | not called | not called under `src/` | **match** | **match** (still unused) |
| §5.2 METAR aviationweather.gov, 12 ICAO, hours=6, nearest ≤35 min, kt×0.514, vis×1609.34 | collector | ICAO list exact; `gap > 35*60`; vis 1609.34; client ×0.514 | `TARGET_ICAO_CODES` same 12; `KNOTS_TO_MS=0.514444`; vis 1609.344; window **[-35 min, +25 min]**; timeout 20 s (collector 40 s) | **match** | **implementation gap** (window + knots + timeout) |
| Embedded six airports; extras via extendData | DATA.airports + AP_EXTRA | **match** | dashboard Airport Weather Matrix card | **match** | **implementation gap** (no `#apHr` heatmap; extras not the same extendData path) |
| §5.3 Ogimet blocks 415/416/417; 7 WMO ids; iw 3/4 ×0.5144 | collector `synop_wind` | exact | `synop.py` same blocks and 7 ids; `KNOTS_TO_MS=0.514444`; 65 s 429 backoff extra | **match** | **match** on endpoint/ids; **implementation gap** on 0.5144 vs 0.514444 |
| §5.4 Open-Meteo `ecmwf_ifs025` 10 m at 41 centroids | collector URL | exact | `open_meteo.py` same model | **match** | **match** |
| Embedded `DATA.ecm` 15×15, 0.5°, `u10/v10/u925/v925`, `xb10/xb925` | spec table | `la`/`lo` 15; keys `u925`/`v925` present | no `ecmLev`; workstation notes 10 m and 925 hPa windGrid | **match** | **implementation gap** (dashboard has no 925 toggle; grid may exist in memory notes only) |
| `meta.ecm_ratio = 0.22686365412534343`; fallback 0.34 | DATA.meta; extendData `KR=...||0.34` | exact | `ROUGHNESS_SCALING_FACTOR = 0.22686`; `DEFAULT_FALLBACK_FACTOR = 0.34` | **match** | **implementation gap** (rounded KR) |
| `DATA.wscale` stored, unused by `#mainsrc` | spec §5.4 / §18 | `wscale` present | N/A | **match** | **out of baseline / N/A** |
| §5.5 FIRMS VIIRS, not in hourly collector; `#xbAll` + Word | HTML `#xbAll` FIRMS table/images; collector has no FIRMS | **match** | `firms.py` worker, bbox `69.0,27.5,76.5,34.5`; dashboard live fire card (counts 48/88/19, not the 2–9 Nov table 6,703/…) | **match** | **implementation gap** (live worker vs snapshot table; different numbers) |
| §5.6 IQAir US AQI snapshot, 32 cities, compare US-to-US only | `#xbAll` table (Peshawar 471 present) | **match** | `iqair.py` converts US AQI / PM2.5 into `pepc_calculate_aqi`; 6 Indian cities + Peshawar, not 32 | **match** | **implementation gap** |
| §5.7 CAMS×ECMWF **rank index**, 117 points, not a mass budget | `#xbAll` hint | **match** | `cams.py` `inflow_kg_per_s` / `outflow_kg_per_s`, 117 nodes, ADS URL, fixture mode | **match** | **implementation gap** |
| §5.8 Meteoblue requested; NOAA GFS mixing height used in Word §15 | not a dashboard layer | not in HTML | no mixing-height / GFS PBL pipeline under `src/pipelines/` | **absent from repo** (as a dashboard layer, as specified) | **absent from repo** |
| §5.9 `src={portal,metar,wmo,ecmwf}` status strings; live line ticks | collector + `liveLine` | **match** | different worker statuses; dashboard `LIVE SYNC: ACTIVE` | **match** | **implementation gap** |
| No invented values | collector docstring | **match** | `FallbackTemplateEngine` generates fixture rows with `is_estimated=True` | **match** | **implementation gap** |

### 3.6 §6 Collector contract

| Named item | Original `collector.py` | Current | Orig | Current |
|------------|-------------------------|---------|------|---------|
| CLI `python3 -I collector.py fetch OUT` / `build OUT EXISTING` | `__main__` | FastAPI workers / celery / cron | **match** | **implementation gap** |
| `get` via curl, timeout 40 s | `timeout=40` | httpx; METAR 20 s; EPA 30 s; Open-Meteo 60 s | **match** | **implementation gap** |
| `fetch`: portal + METAR + SYNOP + ECMWF; hours from portal stamps (6 h); portal-down records last completed PKT hour for winds | implemented | different workers, different cadences | **match** | **implementation gap** |
| `build`: merge old+new per field; skip empty docs; `hYYYYMMDDHH`; fields `t/st/ap/wmo/ecm/src/upd` | implemented | TimescaleDB rows | **match** | **implementation gap** |
| `synop_wind` decode dd×10, iw 3/4 ×0.5144, dd 99/>36 null, ff 99 → 00fff | implemented | `synop.py` decoder present | **match** | **match** (decode role); knots constant gap |
| `fnum`, `parse_ts`, `PMAP`, `DIST`, `ICAO`, `WMO`, `POLF` | implemented | split across modules; no `PMAP` | **match** | **implementation gap** |
| Unmapped portal rows listed and dropped | `unmapped_stations` | EPA catalog is fixed 38 | **match** | **implementation gap** |

### 3.7 §7 Embedded `window.DATA` schema

| Named item | Original | Current | Orig | Current |
|------------|----------|---------|------|---------|
| Top-level keys meta/hours/stations/districts/network/pol/wind/airports/ecm/tbgeo/qa/adm/coordsrc/wscale | present (meta, hours 216, stations 79, districts 41, network 56, ecm, tbgeo, qa, wscale) | split JSON under `data/baseline/` and `src/frontend/static/data/` | **match** | **implementation gap** (no single `window.DATA`) |
| `pol` keys AQI, PM2.5, PM10, NO2, SO2, CO, O3, NO, NOX with frames/stations/cpf/daily/links | present; CPF Attock extracted | observations by pollutant in DB | **match** | **implementation gap** |
| `tbgeo.samples` 39 `[lon,lat,nx,ny]` | `samples_len 39` | `transboundary.py` documents 39 nodes | **match** | **match** (count) |
| Belt `border_km<=120` | 19 districts ≤120 of 24 tbgeo district rows | `BORDER_CORRIDOR_LIMIT_KM = 120` | **match** | **match** |
| Airport series occupancy for six embedded sites | DATA.airports | dashboard airport table | **match** | **implementation gap** (schema) |
| Network phases Operational / Air-Safe 18 / Air-Safe 08, 51 fixed + 5 mobile | DATA.network 56 | workstation `countStationNetworks` | **match** | **implementation gap** (not the shapefile catalog UI) |

### 3.8 §8 Quality control

| Rule | Original | Current | Orig | Current |
|------|----------|---------|------|---------|
| Non-positive → null | extendData `!(v>0)` | `qc.py` step 0 `v<=0` → None | **match** | **match** |
| 7-hour median; drop if `v>4×med` **and** `v>3×ref` | extendData `spk=med!=null&&v>4*med&&v>lim` with `lim=3*(ref\|\|100)` | `SPIKE_MEDIAN_MULTIPLIER=4`, `SPIKE_REF_MULTIPLIER=3`, window ±3, need ≥3 | **match** | **match** |
| 3-hour hold, not AQI | `hold=p!=='AQI'&&full[i-1]===v&&full[i-2]===v` | same, plus `i>=2` index guard | **match** | **match** (guard is compatible) |
| Portal flags | collector `pollutant_flags` | `status_*` strings | **match** | **implementation gap** |
| Wazirabad NOWIND; concentration kept | `NOWIND={'Wazirabad'}`; `qa.Wazirabad.wind_valid=0`, AQI=216 | `WIND_BLACKLIST_STATIONS` includes wazirabad aliases | **match** | **match** |
| `ws<0` or `ws>30`; `wd` outside 0–360 | extendData | `MAX_WIND_SPEED_MS=30`, dir 0–360 | **match** | **match** |
| Chakwal / Khanewal wind_valid=0 | qa snippets | intended by ws>30 / 99.9 | **match** | **match** (rule); live catalog may not include those sites |
| Coordinate QC / EMC-confirmed / OneNetwork | Method + DATA | baseline coords; exclusion list | **match** | **match** (baseline / exclusion) |
| **Valid-PM AQI:** station AQI used only with valid PM2.5 **or** PM10; `extendData` does **not** recompute AQI | Method text present; Lodhran/Kallar AQI n=0 with gases present; extendData copies portal AQI index 0 | `qc.py` has **no** valid-PM gate; `pepc_composite_aqi = max(I_PM2.5, I_PM10)` in `pepc_aqi.py`, `csv_adapter.py`, `staging_buffer.py` | **match** | **implementation gap** (computes AQI from PM instead of gating portal AQI) |
| District mean of finite stations; estimated IDW | extendData | staging / observation services | **match** | **match** (role) |
| Wind fallback AQMS → METAR×KR → ECMWF×KR; estimated IDW then unscaled ECMWF | extendData DAP map + KR | split across wind/open_meteo | **match** | **implementation gap** (chain not the same named DAP/`wsrc` object) |
| Rounding CO 2 dp, others 1 dp, wind 3 dp, airport uv 2 dp | extendData `r()` | various | **match** | **implementation gap** (not the same `r()` helper) |
| §8.7 Lahore study QC / 5-min gusts | specified as 24 Oct product `lahore_air_quality.html` | file absent; hourly wind remains | **absent from repo** (study HTML) | **absent from repo** |

### 3.9 §9 Mathematics

| Named formula | Original | Current | Orig | Current |
|---------------|----------|---------|------|---------|
| Haversine R=6371, bearing atan2 | extendData `R_=6371` | `geodesy.py` R=6371, 16 sectors | **match** | **match** |
| Meteorological `u=−ws sin`, `v=−ws cos` | extendData / mainsrc | `wind.py` | **match** | **match** |
| §9.1 district hourly mean | extendData | services | **match** | **match** (role) |
| §9.2 IDW `w=1/max(km,5)²`; estimated **receptors only** (`pairs` from MON) | `idw()`; `for a of MON` | `discrete_geodesic_idw` d0=5 p=2; `analytics_service.calculate_flux` iterates **all** districts as sources | **match** | **match** on IDW weights; **implementation gap** on source restriction when `is_estimated` districts exist (idle on the all-monitored 1–9 Nov cube) |
| §9.3 `fieldAt`: `w=1/(d²+16)`; downwind `max(0.3, 1+0.7·c·min(1,sp/1.5))`; alpha 235/95/45–140 km; cache `pol\|round(fpos*12)\|W` | mainsrc exact | `canvas.js` same + extra `min(1.70, psi)` (equivalent at cap); `app.js` minis path **without** the 1.70 clamp (matches original); `idw.py` `MAX_ANISOTROPIC_MULTIPLIER=1.70` | **match** | **match** (dashboard + math); workstation uses Deck layers, not this canvas field |
| Retained `drawSurface` `w=1/(q√q)` unused by live Surface | mainsrc | not the live path | **match** | **out of baseline / N/A** |
| §9.4 `windAt` `w=1/(d²+400)`; particle k=1.4 S/100; count min(700, W H/650); regional k=2.2, min(600, W H/900); bilinear `ecmAt` | mainsrc | dashboard particle engine present (1300-particle comment in canvas.js header); no `#ecmLev` | **match** | **implementation gap** (constants/level toggle) |
| §9.5 flux `C·w·cos(Δ)·exp(−km/100)`; CALM 0.5; MAXD 180; CONE 35; LS 100; off for AQI; map top 12 ≥8% MAXF; minis top 8; period top 60; omega 0.25 if CPF null | extendData + mainsrc `topLinks` | `flux.py` same constants, AQI returns None, `MAX_PATHWAY_LINKS=60`, omega 0.25; API HTTP 400 on AQI; dashboard `slice(0,12)` | **match** | **match** |
| §9.6 chevrons 39 samples, skip \|c\|<0.25, ph+=0.012; belt tbVal; estimated belt excluded from hourly total; ECMWF xbRow 10/925 | samples_len 39; tbVal in extendData; `if(TBG[d].est) continue` | `FLOW_NORMAL_THRESHOLD_MS=0.25`; 39 nodes; `is_estimated` **parameter unused** in `calculate_district_transboundary_flux`; extra `border_km>120 → 0` inside the function | **match** | **match** on 120/100/0.25/39; **implementation gap** on estimated exclusion and xbRow 925 |
| `#xbAll` 117 pts × CAMS PM2.5, fixed images, India 56% copy | HTML section + images | cams kg/s; no `#xbAll` | **match** | **implementation gap** |
| §9.7 CPF 16×22.5°, P75, calm <0.5, null when n small | Attock AQI `thr=166`, `calm=0.898`, n=5 null, n=6 cpf=0.333/0.167, n=7 cpf=0.0 → suppression is **n<6** | `MIN_SECTOR_SAMPLES=6`; pooled P75 | **match** | **match** |
| Rose muted arc when cpf null; rings 0.2/0.4/0.6/0.8; dashed 0.25 | mainsrc `drawRose` | dashboard `roseCanvas` | **match** | **match** (dashboard role) |
| §9.8 EPA Punjab 7-tier RGB `#00B050`…`#C00000`; USG 151–200; Hazardous 401+ (`1e9` in original) | `AQI_B` exact RGB and labels including `Unhealthy for Sensitive Groups` | **Dashboard** `AQI_B` exact (Hazardous max 9999 in `PEPC_TIERS`, `1e9` in `AQI_B`); **pepc_aqi.py** hex match, label `Unhealthy (Sensitive)`, **computes** sub-index with leading-0 breakpoints and **500 cap**; **workstation `LEGEND`**: Good `#009966`, Satisfactory `#58B947`, Moderate **101–200** `#FFDE33`, Poor / Very Poor / Severe / Hazardous 500+ | **match** | **implementation gap** (workstation legend + computed AQI + 500 cap + shortened USG label). Dashboard colour table **match** |
| PEPC upper bounds PM10 75…550 … CO 2.5…40 | `const BP={...}` exact, no leading 0 | dashboard `BP` same **plus `NO:[40,80,130,180,280,400]`**; `pepc_aqi.py` / workstation `SUBINDEX_BREAKS` insert leading 0.0 | **match** | **implementation gap** (NO PEPC table; leading 0 used to *compute* AQI) |
| NO/NOx continuous PEQS MULT/RGB `[58,165,93]…[90,21,48]`, NO ref 40 | mainsrc MULT/RGB | canvas.js `MULT`/`RGB` match; extra BP.NO fights the continuous rule | **match** | **implementation gap** (dashboard BP.NO); PEQS stops **match** in canvas.js and pepc_aqi.py |
| Legend titles / KPI “Unhealthy or worse (AQI>200)” / heat-table white on AQI>200 | mainsrc | dashboard analogous KPIs | **match** | **implementation gap** (wording/ids) |
| §9.9 lerp `at(fpos)`; playing=true; speed {0.35, 0.8 selected, 1.6}; dt cap 0.1; wrap; live start last 24 h | mainsrc | dashboard `isPlaying:true`, `playbackSpeed:0.8`, those three speeds; rAF dt-based; **no** 66 ms stall timer; workstation `PlaybackRate` 1x\|2x\|4x\|8x | **match** | **implementation gap** (stall timer; workstation speeds) |
| §9.10 projection, GEO/IND rings, INDIA/PAKISTAN labels, border dash `[8,4]`, hit-test | mainsrc | `geo.js` B/KX; dashboard Path2D; workstation MapLibre | **match** | **match** (dashboard projection constants); workstation **implementation gap** (map stack) |

### 3.10 §10 Live extension

| Named item | Original | Current | Orig | Current |
|------------|----------|---------|------|---------|
| `window.extendData(DATA, docs)` pipeline (filter t, pad hours, airports, QC, winds, frames, top 60, tbh, meta.live) | full function extracted | no symbol | **match** | **implementation gap** |
| PI index AQI=0…O3=6; NO/NOx stay null on live hours | extendData | N/A | **match** | **implementation gap** |
| `#mainsrc type=text/plain`; inject after live or 9 s | last script | N/A | **match** | **implementation gap** |
| `claude.use('db')` collection `hours` limit 1000 onSnapshot | last script exact messages | FastAPI + SSE | **match** | **implementation gap** |
| `__liveState` timeout / no db / empty / onSnapshot error copy | last script | different live badge | **match** | **implementation gap** |
| Live line “Live: latest portal hour …” | mainsrc `liveLine` | `LIVE SYNC: ACTIVE` | **match** | **implementation gap** |
| Standalone download does not attach collector | named file absent; original HTML *does* attach | N/A | **absent from repo** (named file) | **absent from repo** |

### 3.11 §11 User interface

Original HTML ids extracted (`apHr`, `ecmLev`, `xbAll`, `minis`, `polBtns`, `tLinks`, `play`, `rose`, `lmap`, `findings`, …) — **match**.

Current dashboard (closer port) vs workstation (rewrite):

| Spec surface | Original | Dashboard console | Workstation |
|--------------|----------|-------------------|-------------|
| Document chrome title/h1/fonts Barlow Condensed + Source Sans 3 + JetBrains Mono; wrap 1320 / 1fr 360px / 980 stack; colour tokens | **match** | Barlow/Source/JetBrains linked; dark default `data-theme="dark"`; different title | IBM Plex on root `index.html`; title rewrite |
| `#polBtns` nine species, AQI default | **match** | `#pollutantStrip` injected | command-bar pollutant keys |
| `#map` canvas + clock `#cday/#ctime/#cpol` | **match** | `#mainMapCanvas`; `#clockReadout` | MapLibre `#map-canvas` |
| Play Pause on load; `#scrub` step 0.01 | **match** | `#playBtn` label Pause; `#scrubRange` step 0.01 max 215 | temporal-scrubber; rates 1x–8x |
| Surface default / District radio | **match** | `mapMode` surface checked | different layer dock |
| `#tLinks` checked; `#tReg` checked | **match** | `#toggleTransportLinks` / `#toggleRegionalWinds` checked | layer visibility record |
| `#ecmLev` 10 / 925 | **match** | **absent** | no equivalent control found |
| Speeds 0.35 / 0.8 / 1.6 | **match** | `#speedSelect` exact | 1x/2x/4x/8x |
| Extra current controls | — | `#liveToggleBtn`, `+1h Tick`, `#toggleFireAnomalies`, CSV upload | five zones, dimension guard |
| Side KPIs, airport card, ranked list, selected-district table, CPF rose | **match** | Provincial Summary, Airport Weather Matrix, District Concentrations, roseCanvas | receptor-inspector |
| `#apHr` METAR heatmap | **match** | **absent** (airport table this-hour only) | **absent** |
| Nine-map `#minis` 3-column, CMP nine species | **match** | `#minis` present `display:none`; separate `data-view="grid"` 3×3 tab | **absent** |
| Lahore card `<div hidden>`; `drawLahore` still runs | **match** | Lahore is a **visible tab** (`data-view="lahore"`, `#lahoreMapCanvas`) | not the hidden inset |
| Hourly district tabs concentration / transport / transboundary + `xbRow` | **match** | heatmap / transboundary **tabs**, not the same `#hrTable` contract | not present |
| `#xbAll` above findings, fixed images, 32-city IQAir, FIRMS 11-region table | **match** | no `#xbAll`; live FIRMS card with different counts | not present |
| `#findings` four bullets | **match** | not the same generator | not present |
| Method seven paragraphs | **match** (verbatim in HTML) | not shipped as operator Method card | not present |
| Accessibility roles / focus-visible / sticky first column | specified | partial | different |
| `drawNodes` defined unused; `drawTB` empty; `wscale` unused | **match** | N/A | N/A |

**Orig verdict for §11:** **match**.  
**Current verdict:** **implementation gap** (workstation rewrite + missing ecmLev/apHr/xbAll/Method/findings). Dashboard is a **partial match** on Surface/District, speeds, transport toggles, PEPC colours, rose, minis/grid, Lahore (but un-hidden).

#### §11.13 Engine functions

Every named function exists in original `#mainsrc` as specified (`colArr`, `legend`, `build`, `resize`, `at`, `drawSurface`, `seed`, `windAt`, `ecmAt`, `rStep`, `stepDraw`, `topLinks`, `drawLinks`, `drawCross`, `drawField`/`stationPts`/`fieldAt`/`renderField`, `drawChoro`, `drawValues`, `drawMinis`, `apWind`, `apHourly`, `render`, `panel`, `districtList`, `polTable`, `chart`, `drawRose`, `select`, `drawLahore`, `lahoreTable`, `buildHourly`, `xbRow`, `findings`, `setPol`, `togglePlay`, `tick`, `loop`, `liveLine`, `__liveRefresh`, plus `drawNodes` unused, `drawTB` empty, `apTable`, `markHour`, `readTokens`).

| Orig | Current |
|------|---------|
| **match** | **implementation gap** as named `#mainsrc` functions. Dashboard `CanvasMapEngine` / `App` reimplements a subset under different names (`fieldAt` inlined in `canvas.js`/`app.js`). Workstation does not call this engine |

### 3.12 §12 Animation and reduced-motion fallback

| Named item | Original | Current | Orig | Current |
|------------|----------|---------|------|---------|
| `playing = true`; Play shows Pause | `playing=true` | dashboard `isPlaying: true`, Pause button | **match** | **match** (dashboard) |
| rAF `loop` + `tick`; dt cap 0.1; wrap | mainsrc | rAF dt hour-advance in `app.js` | **match** | **implementation gap** (no documented 0.1 cap / wrap contract verified as identical) |
| `setInterval(66)` if `now-lastRaf>200` | present | **no** `setInterval` / `lastRaf` under `src/` (the `66` hits in `state.ts` are `#009966`) | **match** | **implementation gap** |
| No `prefers-reduced-motion` in `#mainsrc` | `prefers-reduced-motion in html: False` | not used as a playback gate (vendor CSS in dist only) | **match** | **match** (still ungated) |
| Particles `dash -= 0.6`, `ph += 0.012` | mainsrc | dashboard transport/chevrons exist | **match** | **implementation gap** (constants not shown as identical) |
| Workstation playback 1x/2x/4x/8x | N/A | `PlaybackRate` | — | **implementation gap** vs spec speeds |

### 3.13 §13 Daily AQI situation report

| Named item | Original System folder | Current repo | Orig | Current |
|------------|------------------------|--------------|------|---------|
| Word files 05 Nov / 09 Nov | not in folder (spec says conversation deliveries) | glob ABSENT | **absent from repo** | **absent from repo** |
| Visual-first structure, 3 Nov included, valid-PM | specified as Word content | no generator | **absent from repo** | **absent from repo** |
| Official daily AQI table (Punjab 303, Lahore 374 on 9 Nov*) | **not** in HTML (`official 303 in html: False`) — spec §13.5 says official figures live in the Word report, dashboard stays on hourly AQMS | not present | **match** (HTML correctly omits official 303) | **absent from repo** (Word) |
| Distinction official daily vs hourly cube | Method + this report | not wired | **match** | **implementation gap** |

### 3.14 §14 Next-24-hour forecast

Persistence × own hour-of-day profile; CAMS/ECMWF adjustment omitted after hindcast fail; dashboard has **no** forecast layer.

| Orig | Current |
|------|---------|
| **absent from repo** (Word-report product; no forecast layer in HTML, as specified) | **absent from repo** — `persistence` in `persistent_repository.py` is DB persist, not diurnal AQI. No `forecast.py` / diurnal module |

### 3.15 §15 Mixing height, PBL, ventilation

Meteoblue unpaid; NOAA GFS via Open-Meteo; Word section 11; **not** a dashboard layer.

| Orig | Current |
|------|---------|
| **absent from repo** as files; **match** as “not a dashboard layer” | **absent from repo** (no mixing-height pipeline; `Meteoblue` needle 0 under `src/`) |

### 3.16 §16 Technical advisory and cover letter

26 May style (letterhead, Times New Roman, four sections, `EPA/DIREMC/O/261110/____`), pollutant table, sector controls A–E, emergency bands.

| Orig | Current |
|------|---------|
| **absent from repo** | **absent from repo** |

### 3.17 §17 Packaging and standalone download

Covered in §3.3. Original `index.html` **matches** the live-bootstrap packaged file. The named ask-55 download without `extendData` is **absent from repo**. Current `dist/workstation.html` is a Vite bundle, not a 9.4 MB offline original.

### 3.18 §18 Limits, non-goals, diagnosed dead ends

These are specified behaviours. Scoring whether the implementation still honours the non-goal:

| Topic | Orig | Current |
|-------|------|---------|
| `aqi.epaforecast.com` unused | **match** | **match** |
| Meteoblue numerical not retrieved | **match** (not in HTML) | **match** (not retrieved) |
| CAMS/ECMWF forecast adjustment omitted | **match** (no forecast layer) | **match** (no such forecast) |
| No Indian AQMS in cube | **match** | **match** (IQAir cities only) |
| Portal no NO/NOx on live hours | **match** | live EPA is a different API |
| OneNetwork 25 skipped | **match** | **match** |
| Tehsil sites vs incomplete `PMAP` | **match** (collector comment) | live 38-station catalog |
| `#xbAll` charts fixed | **match** | section missing |
| Official daily AQI not on HTML | **match** | **match** (still not on HTML) |
| No forecast / mixing layers on map | **match** | **match** |
| `drawNodes` unused, `drawTB` empty, `wscale` unused | **match** | N/A |
| `prefers-reduced-motion` not consulted | **match** | **match** |
| Invented values forbidden | **match** | **implementation gap** (`FallbackTemplateEngine`) |

### 3.19 §19 Out of baseline

| Orig | Current |
|------|---------|
| **out of baseline / N/A** — original *is* the baseline | **out of baseline / N/A** as a spec-coverage statement. This report still scores `src/` because the objective requires verifying the spec against the repo now. Spec’s mention of a root `frontend/` does not match this checkout: **root `frontend/` is absent**; `src/frontend/` exists |

### 3.20 §20 Coverage matrix

The spec’s own completeness rule is satisfied by this gaps file: every ask in §20.1, every collector inventory row in §20.2, and every `index.html` inventory row in §20.3 has a dual verdict in §4–§7 below. Skip of raw 216-hour telemetry rows is required and was observed (arrays not pasted).

---

## 4. Capability-row matrix (asks 1–55)

Columns: **O** = original System; **C** = current tree (D=dashboard, W=workstation, P=pipelines/math). Where D and W split, the cell names both.

| Ask | Capability | O | C | Evidence |
|-----|------------|---|---|----------|
| 1 | Animated field, particles, CPF, transport | **match** | D partial **match** / W **implementation gap** | original mainsrc; dashboard canvas; workstation Deck |
| 2 | Autoplay + 66 ms / 200 ms rAF stall | **match** | **implementation gap** | original setInterval 66; no lastRaf in src |
| 3 | Transboundary India–PK (plains, dashed border, chevrons, belt) | **match** | D partial / W chevrons **implementation gap** vs full belt table | original drawCross + tb tab |
| 4 | 41 polygons + 79 markers | **match** | baseline **match**; live 38 **implementation gap** | DATA.stations 79; catalog 38 |
| 5 | Hourly district means + transport + TB tables | **match** | D tabs partial; W **implementation gap** | original `#hrTable` |
| 6 | 36/56 then 41/79 rebuild | **match** | baseline 41/79 **match** | inventories |
| 7 | Fresh export rebuild; live append after exportEnd | **match** | **implementation gap** | extendData vs FastAPI |
| 8 | Unmonitored IDW; receptors only; `~` hatch | **match** | IDW **match**; source restriction **implementation gap** when est | idw.py; analytics_service all-sources |
| 9 | Hourly hour-beginning PKT | **match** | **match** (cube) | 216 hours |
| 10 | Concise map + cards + tables + findings/method | **match** | **implementation gap** (findings/Method missing) | original Method card |
| 11 | Nine pollutants; Lahore panel separate | **match** | D **match** (tab); hidden-wrapper **implementation gap** | ask 28 conflict in current |
| 12 | Clean map: labels, ≤12 arrows, light wind, small dots | **match** | D partial **match** | topLinks 12; canvas.js |
| 13 | Lahore multi-pollutant insights | **match** | D Lahore tab; findings **implementation gap** | original findings |
| 14 | Wind analysis (vector mean, METAR, calm, CPF) | **match** | P/D partial **match** | wind.py; airport card |
| 15–16 | Updated Lahore file / full columns | **match** (folded into Nov cube) | **implementation gap** as a named ingest | original DATA |
| 17 | Strict QC; gust-front is Lahore-study | **match** on hourly QC; gust HTML **absent from repo** | QC math **match**; gust file **absent** | qc.py; lahore_air_quality.html missing |
| 18 | District concentration as map readout | **match** | D Surface/District **match** | mapMode radios |
| 19 | `#tLinks` on; off for AQI | **match** | D toggle + flux AQI guard **match** | analytics HTTP 400; original isAQI |
| 20 | Lahore network + rose same page | **match** (Lahore hidden, rose visible) | D both visible as tabs/cards | roseCanvas |
| 21 | Four maps same view | **match** (superseded by nine) | D 3×3 tab | minis/grid |
| 22 | Nine synchronized maps | **match** | D grid tab; `#minis` display:none | dashboard.html |
| 23 | Refresh on new export | **match** | live SSE **implementation gap** vs export rebuild | — |
| 24 | Airport METAR OPLA/Faisalabad/Multan/nearby | **match** | D airport matrix; P metar.py 12 ICAO **match** with window gap | metar.py |
| 25–26 | Ranking + transport; Wazirabad vane | **match** | wind blacklist **match** | wind.py |
| 27 | Continuum; Surface/Districts | **match** | D **match**; W **implementation gap** | fieldAt in canvas.js |
| 28 | Remove Lahore section (`<div hidden>`) | **match** | **implementation gap** (Lahore tab shown) | dashboard nav |
| 29 | 41-district shapefiles | **match** | baseline **match** | districts.json |
| 30 | AQI default; EPA Punjab 7-tier `#00B050`…`#C00000` | **match** | D **match**; W **implementation gap** | AQI_B vs LEGEND |
| 31 | aqi.punjab.gov.pk + IQAir | **match** | portal **implementation gap**; IQAir worker converts scale **implementation gap** | epa_punjab.py; iqair.py |
| 32 | Airports, FIRMS, ECMWF, CAMS, realtime continuum | **match** | P workers exist; FIRMS/CAMS semantics **implementation gap**; no 925 toggle | firms.py cams.py |
| 33 | November 2026 1–9 Nov | **match** | horizon constants **match** | HORIZON_* |
| 34 | EMC-confirmed Lahore coords (11 URLs) | **match** (11) | baseline **match** | orig EMC confirmed count 11 |
| 35 | Plot airport winds including extras | **match** | D this-hour table; no `#apHr` | dashboard.html |
| 36 | PEPC parameter-wise colours | **match** | D **match** + extra BP.NO **implementation gap**; W legend **implementation gap** | canvas.js BP |
| 37 | Hourly airport wind table `#apHr` | **match** | **implementation gap** | id absent in src |
| 38 | aqi.epaforecast.com realtime — gated unused | **match** | **match** | no hits in src |
| 39 | Public portal + airports + WMO; keep Nov hourly | **match** | **implementation gap** (different EPA API) | collector vs epa_punjab |
| 40 | Machine-independent collector `python3 -I` | **match** | **implementation gap** | FastAPI workers |
| 41 | collector + hours + extendData + 9 s timeout | **match** | **implementation gap** | last script vs SSE |
| 42 | 79/41; ECMWF 10 m and 925; source-to-sink | **match** | 925 toggle **implementation gap**; live 38 **implementation gap** | ecmLev absent |
| 43 | Daily AQI situation report | **absent from repo** | **absent from repo** | no docx |
| 44 | 3 Nov; visual-first; valid-PM | HTML valid-PM **match**; Word **absent** | valid-PM **implementation gap**; Word **absent** | qa Lodhran AQI 0 |
| 45 | Next 24 h persistence × diurnal | **absent from repo** (Word); no map layer **match** | **absent from repo** | no forecast module |
| 46 | Word document of situation report | **absent from repo** | **absent from repo** | — |
| 47 | 1–9 Nov + FIRMS + Indian IQAir | HTML snapshots **match** | live FIRMS/IQAir **implementation gap** vs snapshot contract | xbAll vs firms.py |
| 48 | Complete 9 Nov 23:00; forecast through 10 Nov | cube **match**; forecast **absent** | cube horizon **match**; forecast **absent** | — |
| 49 | All-sides ECMWF×CAMS, FIRMS, IQAir | `#xbAll` **match** | **implementation gap** (kg/s CAMS, converted IQAir, no xbAll) | cams.py |
| 50 | `#xbAll` on November artifact | **match** | **implementation gap** | id absent |
| 51 | Official daily AQI provincial/district/heatmap | Word **absent**; HTML correctly omits **match** | **absent from repo** | 303 not in HTML |
| 52 | Mixing height 10 Nov (Meteoblue requested, GFS used) | **absent from repo** (Word) | **absent from repo** | no pipeline |
| 53 | Advisory + cover letter | **absent from repo** | **absent from repo** | — |
| 54 | 26 May style, pollutant-specific, formal | **absent from repo** | **absent from repo** | — |
| 55 | Standalone offline HTML ~9.4 MB, no live extend | named file **absent**; original index is live-bootstrap **match** of §3.1 | named file **absent** | glob |

---

## 5. Named constants C01–C96

| ID | Claim | Orig | Current | Notes |
|----|-------|------|---------|-------|
| C01 | h1 Punjab Air Quality, November 2026 | **match** | **implementation gap** | |
| C02 | title … (Copy) | **match** | **implementation gap** | |
| C03 | start 2026-11-01 00:00 | **match** | **match** (horizon) | |
| C04 | end 2026-11-09 23:00 | **match** | **match** (horizon) | |
| C05 | nstations 79 | **match** | **implementation gap** live 38; baseline **match** | |
| C06 | ndistricts 41 | **match** | **match** baseline | |
| C07 | nmon 41 | **match** | **match** baseline | |
| C08 | unmon [] | **match** | **match** baseline | |
| C09 | calm 0.5 | **match** | **match** | |
| C10 | ecm_ratio 0.22686365412534343 | **match** | **implementation gap** 0.22686 | |
| C11 | 216 hours | **match** | **match** | |
| C12 | Good `#00B050` | **match** | D/pepc **match**; W `#009966` **implementation gap** | |
| C13 | Satisfactory `#92D050` | **match** | D **match**; W `#58B947` **implementation gap** | |
| C14 | Moderate `#FFFF00` | **match** | D **match**; W `#FFDE33` and 101–200 **implementation gap** | |
| C15 | USG `#ED7D31` | **match** | D **match**; pepc label shortened; W merged band | |
| C16 | Unhealthy `#FF0000` | **match** | D **match**; W “Poor” | |
| C17 | Very Unhealthy `#7030A0` | **match** | D **match**; W “Very Poor” `#CC0033` | |
| C18 | Hazardous `#C00000` | **match** | D **match** 401+; W 500+ only | |
| C19 | PEPC PM10 75…550 | **match** | D **match**; compute-path leading 0 | |
| C20 | PEPC PM2.5 15…350 | **match** | same | |
| C21 | PEPC SO2 60…1600 | **match** | same | |
| C22 | PEPC NO2 40…580 | **match** | same | |
| C23 | PEPC O3 65…550 | **match** | same | |
| C24 | PEPC CO 2.5…40 | **match** | same | |
| C25 | MAXD 180 km | **match** | **match** flux.py | |
| C26 | CONE 35° | **match** | **match** | |
| C27 | LS 100 km | **match** | **match** | |
| C28 | C × w × cos(Δ) × e^(−km/100) | **match** | **match** | |
| C29 | CPF 16×22.5° | **match** | **match** | |
| C30 | P75 | **match** | **match** | |
| C31 | https://aqi.punjab.gov.pk | **match** | **implementation gap** | |
| C32 | /api/dashboard/current | **match** | **implementation gap** | |
| C33 | aviationweather.gov | **match** | **match** host | |
| C34 | ogimet.com | **match** | **match** host | |
| C35 | ecmwf_ifs025 | **match** | **match** | |
| C36 | UA EMC-EPA-Punjab-AQ-dashboard/1.0 | **match** | **match** | |
| C37 | hour-doc t/st/ap/wmo/ecm/src/upd | **match** | **implementation gap** | |
| C38 | hYYYYMMDDHH | **match** | **implementation gap** | |
| C39 | window.extendData | **match** | **implementation gap** | |
| C40 | claude.use('db') | **match** | **implementation gap** | |
| C41 | rAF 66/200 | **match** | **implementation gap** | |
| C42 | playing = true | **match** | D **match** | |
| C43 | #tLinks | **match** | D renamed toggle **match**; W gap | |
| C44 | #ecmLev | **match** | **implementation gap** | |
| C45 | Surface default | **match** | D **match** | |
| C46 | #xbAll | **match** | **implementation gap** | |
| C47 | 117 points | **match** (xbAll product) | cams 117 count **match**; semantics gap | |
| C48 | belt 120 km | **match** | **match** | |
| C49 | 7-hour median | **match** | **match** | |
| C50 | 3-hour hold | **match** | **match** | |
| C51 | valid PM2.5 or PM10 | **match** | **implementation gap** | |
| C52 | Wazirabad ~140° | **match** | **match** | |
| C53 | ws > 30 m/s discard | **match** | **match** | |
| C54 | METAR 35 min | **match** (±35) | **implementation gap** [-35,+25] | |
| C55 | knots × 0.514 | **match** (client) | **implementation gap** 0.514444 | |
| C56 | SYNOP × 0.5144 | **match** | **implementation gap** 0.514444 | |
| C57 | No values invented | **match** | **implementation gap** fixtures | |
| C58 | aqi.epaforecast.com gated | **match** | **match** unused | |
| C59 | Meteoblue | **absent from repo** | **absent from repo** | |
| C60 | Situation_Report_09Nov docx | **absent from repo** | **absent from repo** | |
| C61 | Technical_Advisory docx | **absent from repo** | **absent from repo** | |
| C62 | Cover_Letter docx | **absent from repo** | **absent from repo** | |
| C63 | named standalone Dashboard.html | **absent from repo** | **absent from repo** | |
| C64 | index 9,609,848 | **match** | file still in tree | |
| C65 | collector 16,362 | **match** | file still in tree | |
| C66 | official Punjab 303 | Word **absent**; HTML omit **match** | **absent from repo** | |
| C67 | official Lahore 374 | same | **absent from repo** | |
| C68 | drawTB empty | **match** | N/A | |
| C69 | drawNodes unused | **match** | N/A | |
| C70 | wscale unused | **match** | N/A | |
| C71 | Lahore `<div hidden>` | **match** | **implementation gap** | |
| C72 | #minis | **match** | D present/hidden + grid tab | |
| C73 | FIRMS | **match** snapshot | **implementation gap** live worker | |
| C74 | IQAir | **match** US AQI table | **implementation gap** PEPC convert | |
| C75 | CAMS rank index | **match** | **implementation gap** kg/s | |
| C76 | 925 hPa | **match** | **implementation gap** no toggle | |
| C77 | fieldAt | **match** | D **match** | |
| C78 | IDW d0=5 | **match** | **match** | |
| C79 | receptors only | **match** | **implementation gap** if est sources | |
| C80 | 75% period mean | **match** | **match** qc.py 0.75 | |
| C81 | PMAP 186 Murree | **match** | **implementation gap** | |
| C82 | NAME_FALLBACK Chiniot | **match** | **implementation gap** | |
| C83 | python3 -I collector.py | **match** | **implementation gap** | |
| C84 | 9 s live timeout | **match** | **implementation gap** | |
| C85 | mainsrc text/plain | **match** | **implementation gap** | |
| C86 | forecast persistence×diurnal | **absent from repo** | **absent from repo** | |
| C87 | 26 May style | **absent from repo** | **absent from repo** | |
| C88 | OneNetwork Station 25 skip | **match** | **match** | |
| C89 | POLF no NO/NOx | **match** | live API different | |
| C90 | ICAO 12 OPLA…VIAR | **match** | **match** | |
| C91 | WMO 41640 | **match** | **match** | |
| C92 | ecm 15×15 | **match** | **implementation gap** (no ecmLev UI) | |
| C93 | border samples 39 | **match** | **match** (module) | |
| C94 | speed 0.35/0.8/1.6 | **match** | D **match**; W gap | |
| C95 | Google Fonts Barlow Condensed | **match** | D **match**; W IBM Plex | |
| C96 | PEQS RGB [58,165,93]… | **match** | D + pepc_aqi **match** | |

---

## 6. Collector inventory → spec (§20.2)

| Inventory item | Orig | Current |
|----------------|------|---------|
| CLI fetch/build | **match** | **implementation gap** |
| UA | **match** | **match** |
| PORTAL aqi.punjab.gov.pk | **match** | **implementation gap** |
| /api/dashboard/current, /api/districts, /api/district-stations | **match** | **implementation gap** |
| METAR 12 ICAO hours=6 | **match** | **match** host/ICAO; hours window gap |
| SYNOP 415/416/417 | **match** | **match** |
| ECMWF Open-Meteo ecmwf_ifs025 10 m Asia/Karachi | **match** | **match** |
| get, fnum, parse_ts, fetch, synop_wind, build | **match** | split / renamed |
| Hour-doc fields + hYYYYMMDDHH + collection hours | **match** | **implementation gap** |
| PMAP, NAME_FALLBACK, DIST 41, ICAO, WMO, POLF | **match** | **implementation gap** (no PMAP/NAME_FALLBACK) |
| No invented values | **match** | **implementation gap** |
| pollutant_flags | **match** | status_* **implementation gap** |
| METAR nearest within 35 min | **match** | [-35,+25] **implementation gap** |
| SYNOP iw 3/4 ×0.5144; dd×10; dd 99/>36 null | **match** | knots 0.514444 **implementation gap** |
| Merge old+new; skip empty | **match** | **implementation gap** |
| Portal-down: last completed PKT hour for winds | **match** | **implementation gap** |

---

## 7. `index.html` inventory → spec (§20.3)

| Inventory item | Orig | Current |
|----------------|------|---------|
| Title / h1 / eyebrow | **match** | **implementation gap** |
| meta.start/end/nstations/ndistricts/nmon/unmon/calm/ecm_ratio | **match** | horizon + KR rounded |
| DATA top-level keys / pol subkeys | **match** | **implementation gap** |
| Method: valid-PM, flags/zeros/spikes/hold, district mean, vector wind, Wazirabad 140°, ws>30, METAR then ECMWF, OneNetwork 25 | **match** (verbatim) | **implementation gap** (no Method card) |
| Method: METAR set, ECMWF 0.25 on 0.5° grid, 10 m/925, cross-border | **match** | 925 UI **implementation gap** |
| Method: live hours from 3 Nov, 7-hour median, portal no NO/NOx, WMO in wind table, provisional | **match** | **implementation gap** |
| Method: 41 shapefile, Lat/Lon overrides, approximate sites | **match** | baseline **match** |
| Method: transport 180 km ±35° formula | **match** | math **match** |
| Method: CPF 22.5°, P75, calm 0.5 | **match** | math **match** |
| Method: TB belt, no Indian monitors, PEQS-relative colours | **match** | colours D **match** / W gap |
| UI regions §11.1–§11.11 | **match** | see §3.11 |
| window.DATA, extendData, mainsrc text/plain, claude.use hours | **match** | **implementation gap** |
| rAF + 66/200; playing true; wrap fpos | **match** | D playing **match**; 66/200 **implementation gap** |
| Engine function catalogue §11.13 | **match** | **implementation gap** as named functions |

---

## 8. Spec errors versus `original System/`

**None material.** The grok spec was forensically extracted from this baseline. Cross-checks that could have produced a spec error, and did not:

| Check | Result |
|-------|--------|
| Title, h1, meta.start/end, 79/41/216, calm 0.5, ecm_ratio full float | identical |
| AQI_B RGB and labels; BP six-species upper bounds | identical |
| Transport CALM/MAXD/CONE/LS; fieldAt; IDW d0=5 | identical |
| Collector PORTAL, UA, ICAO 12, WMO 7, POLF, PMAP 186, NAME_FALLBACK, 35×60 s, 0.5144 SYNOP | identical |
| Live bootstrap `setTimeout(...,9000)` + `claude.use('db')` | present at original lines 790–800 (an earlier scratch regex missed nested `<script>`; the spec is correct) |
| `drawTB` empty, `drawNodes` defined, `playing=true`, no `prefers-reduced-motion` in mainsrc | identical |
| `tbgeo.samples` length 39; `ecm` 15×15 with `u925`/`v925` keys | identical |
| Attock AQI CPF: n<6 null, n=6 computed (0.333), n=7 can be 0.0 | spec said “null when n is too small” and quoted n=6 cpf=0.333 — **match**. Spec did not write the integer 6; that is underspecification, not a contradiction |
| Lodhran / Kallar AQI n=0 with gases present | valid-PM **match** |
| Official 303/374 not in the HTML | **match** with §13.5 |

**Underspecification (not scored as spec error):** CPF small-n integer is 6 in the snapshot; spec describes it in words. Current `MIN_SECTOR_SAMPLES=6` agrees with the snapshot.

---

## 9. Current-tree implementation-gap rollup

Group A — **identity / packaging**

- Titles, fonts (workstation), single-file offline runtime, `extendData` / `claude.use` / hour-docs, `python3 -I collector.py`.

Group B — **live EPA product substitution**

- `api.epd-aqms-pk.com` + API key + 38 stations vs public portal 79/`PMAP`.
- Computed PEPC AQI (`pepc_calculate_aqi`, 500 cap, composite max(PM2.5, PM10)) vs portal AQI + valid-PM gate.
- Fixture fallback invents values.

Group C — **two UIs**

- Workstation `LEGEND` is a different 7-tier scale (US-like CPCB bands/hex, merged 101–200).
- Dashboard is the closer port but: Lahore un-hidden, extra `BP.NO`, no `#ecmLev` / `#apHr` / `#xbAll` / Method / findings, minis hidden in favour of a grid tab, no 66 ms stall timer, extra LIVE/+1h/FIRMS/CSV chrome.
- Root `frontend/` named in spec §19 is **absent**; `src/frontend/` is what exists.

Group D — **constants drifted**

- KR 0.22686 vs 0.22686365412534343.
- Knots 0.514444 vs 0.514 / 0.5144.
- METAR window [-35,+25] vs ±35 min.
- Hazardous 500 cap vs 401+ unbounded display.
- Flux pair builder may use estimated districts as sources.

Group E — **side-channel products with different semantics**

- IQAir converted to PEPC vs US-AQI snapshot table.
- CAMS kg/s vs rank index.
- FIRMS live bbox worker vs 2–9 Nov `#xbAll` table (6,703 / 3,239 / …).

Group F — **math that does match** (so they are not gaps)

- flux 180/35/100/0.5, AQI guard, top 60, omega 0.25.
- CPF 16×22.5 P75, n<6, calm 0.5.
- IDW d0=5 p=2; fieldAt weights + 45/140 km alpha.
- QC 7-hour 4×/3×, 3-hour hold AQI-exempt, 75% completeness.
- Projection B and KX; transboundary 120 km / 0.25 m/s / 39 nodes.
- Wazirabad blacklist; ws>30; OneNetwork skip.
- Dashboard `AQI_B` / PEPC `BP` (except NO) / PEQS RGB.
- UA string; METAR 12 ICAO; SYNOP 7 ids + blocks 415–417; Open-Meteo `ecmwf_ifs025`.
- Frozen `data/baseline` 79 stations / 41 districts / 216 h.

---

## 10. Absent from repo

These spec-named files are not in this checkout (workspace `rglob`):

- `Punjab_AQI_Situation_Report_05Nov2026.docx`
- `Punjab_AQI_Situation_Report_09Nov2026.docx`
- `Cover_Letter_Technical_Advisory_10Nov2026.docx`
- `Technical_Advisory_Smog_Episode_10Nov2026.docx`
- `Punjab_Air_Quality_November_2026_Dashboard.html`
- `airport_wind_26Oct2026.csv`, `airport_wind_Nov2026.csv`
- `punjab_pm10_transport.html`, `punjab_pollutant_transport.html`, `punjab_26oct.html`, `punjab_live.html`, `lahore_air_quality.html`

Also absent as *modules*: persistence×diurnal forecast, mixing-height/GFS PBL ingest, 26 May advisory renderer.

Present and specified: `original System/index.html`, `original System/collector/collector.py`.

---

## 11. Out of baseline / not applicable

- Spec §19: reconstructing the Claude-built system means reconstructing original HTML + collector + named Word/forecast/mixing products. The FastAPI/React/TimescaleDB/Deck.gl tree is **out of baseline** for that reconstruction. This gaps report still scored it as the current implementation.
- `DATA.wscale`, unused `drawNodes`/`drawSurface` live path, empty `drawTB` — specified dead code in original; N/A to the current engines.
- Hourly `window.DATA` arrays — required skip; not a gap.

---

## 12. Coverage audit (this report)

| Spec slice | Count in spec | Verdict rows in this report |
|------------|---------------|-----------------------------|
| `##` sections 1–20 | 20 | §3.1–§3.20 |
| `###` headings | 77 | each parent section scored; UI 11.1–11.13 and 13.1–13.5, 16.1–16.4 called out |
| §2 capability rows | 53 (asks 1–55 including ranges) | §4 table, one row per ask id |
| Named constants C01–C96 | 96 | §5 table |
| Collector inventory §20.2 | 16 rows | §6 |
| index.html inventory §20.3 | 14 rows | §7 |
| Engine functions §11.13 | catalogue | §3.11 list |

Zero unnamed skips of those slices. Hourly telemetry rows were not copied.

---

## 13. H3 heading index (every spec `###`)

Every `###` heading in the grok spec is listed. Verdicts repeat the dual-layer score from §3–§7 so a heading search cannot skip a named item.

| Spec `###` | Orig | Current |
|------------|------|---------|
| 3.1 Baseline files (this specification) | **match** (`index.html` 9,609,848; collector 16,362) | files present in tree; not the running app |
| 3.2 Companion products delivered in the conversation (specified in §13–§17) | **absent from repo** | **absent from repo** |
| 3.3 Runtime shape | **match** (offline HTML + CLI) | **implementation gap** (FastAPI/Vite) |
| 4.1 Temporal baseline | **match** 216 hours 1–9 Nov | **match** horizon; live clock different |
| 4.2 Administrative geography | **match** 41 `est:false` | **match** baseline |
| 4.3 Map projection | **match** B/KX | **match** `projection.py` / `geo.js` |
| 4.4 AQMS locations | **match** 79 + 11 EMC-confirmed | baseline **match**; live 38 **implementation gap** |
| 4.5 Collector district centroids (ECMWF query points) | **match** `DIST` | **match** 41-point Open-Meteo |
| 4.6 Station-id map (collector `PMAP`) | **match** including 186 Murree | **implementation gap** |
| 4.7 Full station, district, shapefile, and QC inventories | **match** | counts **match** in baseline; no embedded `qa` |
| Station inventory (window.DATA.stations, 79 rows) | **match** 79 names | baseline 79; live 38 **implementation gap** |
| District inventory (window.DATA.districts, 41 rows; est=false for all in the 1–9 Nov baseline) | **match** | **match** baseline |
| Shapefile network catalog (window.DATA.network, 56 rows) | **match** 56 | **implementation gap** (no `DATA.network` UI) |
| Per-station QC counts (window.DATA.qa; hours with a finite value after cleaning) | **match** (Lodhran AQI 0, Wazirabad wind_valid 0, Chiniot wind_valid 9) | **implementation gap** (no `qa` blob) |
| 5.1 EPA Punjab AQMS (concentrations and AQI) | **match** aqi.punjab.gov.pk | **implementation gap** api.epd-aqms-pk.com |
| 5.2 Airport METAR (aviationweather.gov) | **match** | host **match**; window/knots **implementation gap** |
| 5.3 WMO SYNOP (Ogimet) | **match** | blocks/ids **match**; 0.514444 **implementation gap** |
| 5.4 ECMWF IFS via Open-Meteo | **match** 15×15 + 925 | model **match**; 925 UI **implementation gap** |
| 5.5 NASA FIRMS (thermal anomalies / crop fires) | **match** `#xbAll` snapshot | **implementation gap** live worker |
| 5.6 IQAir (cities outside Punjab) | **match** US AQI 32-city table | **implementation gap** PEPC convert, 6 cities |
| 5.7 CAMS (all-sides transport) | **match** rank index | **implementation gap** kg/s |
| 5.8 NOAA GFS mixing height (Meteoblue requested) | **absent from repo** (Word) | **absent from repo** |
| 5.9 Source status strings | **match** | **implementation gap** |
| 6.1 `fetch(out)` | **match** | **implementation gap** |
| 6.2 `build(out, existing)` | **match** | **implementation gap** |
| 6.3 Functions and helpers | **match** get/fnum/parse_ts/synop_wind | split across workers |
| 7.1 Top-level keys | **match** | **implementation gap** (no window.DATA) |
| 7.2 Per-pollutant object `DATA.pol[P]` | **match** | **implementation gap** |
| 7.3 `tbgeo` | **match** 39 samples | 39 nodes **match** |
| 7.4 Network phases | **match** 56 shapefile sites | **implementation gap** |
| 7.5 Airport series occupancy (embedded 216 hours) | **match** | **implementation gap** (no `#apHr`) |
| 8.1 Reject / null rules (concentrations) | **match** | **match** qc.py |
| 8.2 Wind QC | **match** | **match** wind.py |
| 8.3 Coordinate QC | **match** | **match** baseline / OneNetwork skip |
| 8.4 Valid-PM AQI rule | **match** | **implementation gap** |
| 8.5 District aggregation after QC | **match** | role **match**; DAP/`wsrc` **implementation gap** |
| 8.6 Rounding | **match** | **implementation gap** |
| 8.7 Lahore study QC (24 Oct product, still specified) | study HTML **absent from repo** | **absent from repo** |
| 9.1 District hourly mean | **match** | **match** (role) |
| 9.2 Unmonitored-district IDW (ask 8) | **match** | weights **match**; receptors-only **implementation gap** if est sources |
| 9.3 Wind-weighted station continuum (ask 27) | **match** | D **match**; W **implementation gap** |
| 9.4 District wind field used by particles | **match** | **implementation gap** (k, 925) |
| 9.5 Inter-district transport index (asks 1, 5, 19, 42) | **match** | **match** flux.py |
| 9.6 Transboundary index (asks 3, 49) | **match** | 120/0.25/39 **match**; estimated exclusion / xbRow **implementation gap** |
| 9.7 CPF — Conditional Probability Function (ask 1) | **match** n<6 | **match** MIN_SECTOR_SAMPLES=6 |
| 9.8 Colour scales — EPA Punjab AQI and PEPC (asks 30, 36) | **match** | D **match**; W **implementation gap**; extra BP.NO |
| 9.9 Time interpolation | **match** | D speeds **match**; 66/200 **implementation gap** |
| 9.10 Map projection | **match** | D **match**; W map stack **implementation gap** |
| 10.1 `window.extendData(DATA, docs)` | **match** | **implementation gap** |
| 10.2 Live bootstrap (last script) | **match** 9 s + claude.use | **implementation gap** |
| 10.3 Live line copy | **match** | **implementation gap** |
| 11.1 Document chrome | **match** | **implementation gap** (titles) |
| 11.2 Pollutant switch (`#polBtns`) | **match** | D strip **match**; id renamed |
| 11.3 Map canvas and clock | **match** | D canvas **match**; ids renamed |
| 11.4 Side column | **match** | D cards partial **match** |
| 11.5 Nine-map comparison grid (asks 21–22) | **match** | D grid tab; `#minis` display:none |
| 11.6 Lahore AQMS network (asks 11, 13, 20, 28, 34) | **match** hidden | **implementation gap** (tab shown) |
| 11.7 Hourly wind-speed table (ask 37) | **match** `#apHr` | **implementation gap** |
| 11.8 Hourly district tables (asks 5, 18) | **match** | **implementation gap** vs `#hrTable` |
| 11.9 All-sides section `#xbAll` (asks 49–50) | **match** | **implementation gap** |
| 11.10 Key findings (`#findings`) | **match** | **implementation gap** |
| 11.11 Method notes | **match** | **implementation gap** |
| 11.12 Accessibility and interaction | **match** | **implementation gap** (partial) |
| 11.13 Engine functions in `#mainsrc` | **match** | **implementation gap** as named functions |
| 13.1 Files | Word **absent from repo** | **absent from repo** |
| 13.2 Visual-first 5 Nov edition (asks 43–44, 46) | **absent from repo** | **absent from repo** |
| 13.3 9 Nov edition (asks 47–48) | **absent from repo** | **absent from repo** |
| 13.4 Official daily AQI figures (ask 51) | HTML omit **match**; Word **absent** | **absent from repo** |
| 13.5 Distinction: official daily AQI vs hourly AQMS | **match** | **implementation gap** |
| 16.1 Form (ask 54 — 26 May style) | **absent from repo** | **absent from repo** |
| 16.2 Pollutant-by-pollutant analysis (9 Nov hourly, provisional) | **absent from repo** | **absent from repo** |
| 16.3 Sector mitigatory controls | **absent from repo** | **absent from repo** |
| 16.4 Emergency actions and legal frame | **absent from repo** | **absent from repo** |
| 20.1 Conversation asks → spec | scored in §4 | scored in §4 |
| 20.2 Collector inventory → spec | scored in §6 | scored in §6 |
| 20.3 `index.html` inventory → spec | scored in §7 | scored in §7 |
| 20.4 Completeness rule | this report | this report |

---

*End of SystemSpec-16-11-2026-grok-gaps. Independent verification, 16 Nov 2026, from `docs/SystemSpecs-16-11-2026-grok.md` against `original System/{index.html,collector/collector.py}` and the current `src/` + `data/baseline/` tree. No runtime code was changed.*

