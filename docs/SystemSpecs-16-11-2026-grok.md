# EPA Punjab Air Quality Workstation — System Specification (Grok)

**Document ID:** `SystemSpecs-16-11-2026-grok`  
**Issued:** 16 November 2026  
**Authoring method:** Forensic extraction from the Claude conversation (24 October–10 November 2026) and from the delivered artifacts in `original System/` (What Claude Actually Built).  
**Sources of truth:**

1. `C:\Users\Asif\Downloads\Claude Conversation.md` (55 `# you asked` turns plus the replies that implemented them).
2. `original System/index.html` — standalone November dashboard (`Punjab Air Quality, November 2026`), including Method notes, UI, `window.DATA` schema, `window.extendData`, and `#mainsrc`.
3. `original System/collector/collector.py` — machine-independent hourly collector.

This document specifies the **implemented system**: requirements, data, quality control, mathematics, user interface, ingestion, reports, and packaging. It is not a chat transcript, not an executive summary, and not a description of the later FastAPI / React / TimescaleDB tree under `src/` or `frontend/`. Hourly observation arrays from the 9.6 MB `window.DATA` payload are not inlined.

**Out of baseline.** Mentions of a later refactor belong only in §19.

---

## 1. System identity

The system is an **offline-capable, single-file Punjab air-quality workstation** plus a **small Python collector**. It is operated by EPA Punjab’s Environmental Monitoring Center (EMC).

| Property | Implemented value |
|----------|-------------------|
| Product title | Punjab Air Quality, November 2026 |
| HTML `<title>` in the delivered copy | Punjab Air Quality November 2026 (Copy) |
| Eyebrow | EPA Punjab · Environmental Monitoring Center · AQMS network |
| Temporal extent of the embedded record | 2026-11-01 00:00 through 2026-11-09 23:00 PKT, 216 hourly frames |
| Geography | 41 official Punjab districts (including Wazirabad, Murree, Talagang, Kot Addu, Taunsa) |
| AQMS stations in the embedded record | 79 mapped stations (`meta.nstations`); Method notes also name an 80-station 1–9 Nov export including 24 tehsil-level sites |
| Monitored districts | 41 of 41 (`meta.nmon=41`, `meta.unmon=[]`) |
| Default pollutant | AQI (EPA Punjab 7-tier categories) |
| Calm threshold | 0.5 m/s (airport definition of calm, about 1 knot) |
| Time zone | Asia/Karachi (PKT, UTC+5) |
| Packaging | One HTML file (~9.6 MB) that opens in a browser without a server; optional live hours from a cloud `hours` collection |

The same product line earlier existed as dated pages (`punjab_pm10_transport.html` / `punjab_pollutant_transport.html` for 23–24 Oct; `punjab_26oct.html` for 26 Oct; `punjab_live.html` for the IQAir/FIRMS/CAMS live prototype; `lahore_air_quality.html` for the 24 Oct Lahore station study). The **forensic baseline of this specification is the November dashboard + collector** in `original System/`. Capabilities first delivered on the October pages and then carried forward (animation fallback, transboundary chevrons, 9-map grid, PEPC colours, Lahore coordinates, Surface/Districts, airport METAR, CPF, transport index) are specified as **current system behavior** of that baseline.

---

## 2. Implemented capabilities

Every user request in the conversation is specified here as system behavior. Section references point to the detailed rules.

| # | When (PKT) | Request (paraphrase of the ask) | Implemented behavior | Spec |
|---|------------|---------------------------------|----------------------|------|
| 1 | 2026-10-24 15:41 | Animated Punjab graphics from PM10, wind, CPF, inter-district transport | Hourly (originally half-hourly) interpolated pollutant field, wind-flow particles, CPF rose, transport arrows between districts | §9, §11, §12 |
| 2 | 2026-10-24 15:51 | Animation not working | Playback starts on load. A backup timer advances the clock when `requestAnimationFrame` stalls (Windows “Animation effects” / reduced motion / throttled background tabs). Delivered November code: rAF loop + `setInterval` 66 ms if rAF gap > 200 ms | §12 |
| 3 | 2026-10-24 15:56 | Transboundary India–Pakistan factor | Indian plains drawn; dashed international border; animated chevrons; inflow/outflow index; border-district enrichment and CPF | §9.6, §11 |
| 4 | 2026-10-24 16:34 | Mark district boundaries and AQMS locations | Official 41-district polygons (`DATA.adm`) and 79 station markers | §4, §11 |
| 5 | 2026-10-24 16:35 | Hourly average PM10 district-wise, inter-district and transboundary transport | District hourly means; transport-index table; transboundary table | §9, §11 |
| 6 | 2026-10-24 16:37 | Reanalyze 36 districts / 56 AQMS | Network rebuilt onto the official district scheme; later expanded to 41 districts / 56 shapefile sites / 79 measured sites | §4 |
| 7 | 2026-10-24 16:40 | Get fresh data file | Dashboard is rebuilt from each new AQMS export; live hours append after `meta.exportEnd` | §5, §6, §10 |
| 8 | 2026-10-24 16:41 | 56 AQMS for 36 districts, then calculate unmonitored districts | Inverse-distance weighting of neighbouring **monitored** districts; estimated districts are receptors only in transport; shown with `~` and hatch | §9.2 |
| 9 | 2026-10-24 16:46 | Same format, district basis, hourly interval | One frame per clock hour, hour-beginning PKT | §4.1 |
| 10 | 2026-10-24 16:47 | Concise, without extra complexity | Map + side cards + hourly tables + short findings/method | §11 |
| 11 | 2026-10-24 16:52 | Each pollutant; Lahore AQMS popup separate | Nine parameters (AQI + eight concentrations); Lahore network is its own panel (later hidden by request 28, code retained) | §11.6 |
| 12 | 2026-10-24 16:52 | Provincial map needs clean | Collision-avoiding labels; at most 12 transport arrows; light wind streaks; small station dots | §11 |
| 13 | 2026-10-24 17:16 | Analyse PM2.5, PM10 and other pollutants for Lahore; insights | Lahore 13-station network on the map and (when shown) inset; findings name core vs edge, ozone titration, dust vs combustion | §11.6, §16 |
| 14 | 2026-10-24 17:17 | Also analyse wind data | Station vector-mean wind, airport METAR, calm statistics, direction–concentration | §9.4 |
| 15–16 | 2026-10-24 17:18–17:19 | Use the updated Lahore file | Full pollutant + weather columns ingested; frozen RH/temperature, PM2.5/PM10 ratio checks | §8 |
| 17 | 2026-10-24 17:22 | Exclude doubtful data; spatiotemporal Lahore; wind gusts | QC rules in §8; 5-minute gust-front analysis is a Lahore-study product; hourly wind remains on the workstation | §8, §13 |
| 18 | 2026-10-26 11:51 | Show district hourly average concentration instead of export indices | District values (or surface) are the map readout; transport arrows are a separate toggle | §11 |
| 19 | 2026-10-26 12:17 | Turn on transport arrows | `#tLinks` defaults to checked; suppressed when the selected pollutant is AQI | §11 |
| 20 | 2026-10-26 12:21 | Align Lahore AQMS network and wind rose on the same page | Rose sits in the side column with a district selector; Lahore inset canvas exists (hidden wrapper after request 28) | §11 |
| 21 | 2026-10-26 12:32 | Replicate provincial map for PM2.5, PM10, CO, NO2 in the same view | Comparison grid, same hour, own PEQS/PEPC scale | §11.5 |
| 22 | 2026-10-26 12:36 | Live dashboard, duplicate map for each pollutant | Nine synchronized mini-maps: AQI, PM2.5, PM10, NO2, SO2, CO, O3, NO, NOx | §11.5 |
| 23 | 2026-10-27 00:24 | Work on fresh data and refresh | Period replaced by each new export; 26 Oct evening inversion episode is historical context | §4.1 |
| 24 | 2026-10-27 00:28 | Mine wind from OPLA, Faisalabad, Multan and nearby airports | METAR for the ICAO set in §5.2, plotted as ✈ with wind arrows | §5.2, §11 |
| 25–26 | 2026-10-27 00:31–00:36 | Update provincial ranking and transport for 26 Oct | Ranking list, transport, airport cross-check; Wazirabad vane discarded (~140°) | §8.5, §11 |
| 27 | 2026-10-27 00:51 | Province-wise continuum | Wind-weighted inverse-distance **surface** from stations; fade with distance from nearest station; Surface / Districts switch | §9.3, §11 |
| 28 | 2026-10-27 01:01 | Remove Lahore AQMS network separate section | The Lahore card is wrapped in `<div hidden>` in the delivered HTML; `drawLahore` still runs against `#lmap` | §11.6 |
| 29 | 2026-10-27 12:57 | Update from available shapefiles | 41-district polygons and 56-station shapefile; Lat/Lon attribute errors overridden by point geometry | §4 |
| 30 | 2026-10-29 00:22 | Add AQI; EPA Punjab colour scheme | Seven EPA Punjab categories and hex colours from the Daily AQI Report legend; AQI is the default button | §9.7 |
| 31 | 2026-10-29 00:47 | Use aqi.punjab.gov.pk and IQAir | Portal is the live AQMS stream; IQAir supplies outside-Punjab city AQI in the all-sides section and in reports | §5 |
| 32 | 2026-10-29 00:47 | Airport meteorology, FIRMS thermal anomalies, ECMWF/other models, realtime continuum | METAR + WMO + ECMWF IFS 10 m / 925 hPa on the map; FIRMS and CAMS in the all-sides section and reports; hourly collector for portal/METAR/WMO/ECMWF | §5, §6, §11.8 |
| 33 | 2026-11-03 02:12 | Update for November 2026 | Embedded record is 1–9 Nov 2026 | §4.1 |
| 34 | 2026-11-03 02:14 | Update Lahore AQMS locations (11 Google-Maps query URLs) | Those 11 sites are stored as `coordsrc = "EMC confirmed"` and used for plotting | §4.4 |
| 35 | 2026-11-03 02:26 | Mine and plot airport winds (OPLA, Multan, Islamabad, Sialkot, Rahim Yar Khan, Bahawalpur, …) | Six airports embedded (OPLA, OPFA, OPMT, OPST, OPIS, VIAR); collector also requests OPRN, OPRK, OPBW, OPDG, OPSR, OPMI; `extendData` adds extras when they appear | §5.2, §10 |
| 36 | 2026-11-03 02:34 | Use PEPC parameter-wise breakpoints and colours | PM10, PM2.5, SO2, NO2, O3, CO use PEPC bands in the same seven colours as AQI; NO and NOx keep a continuous PEQS-multiple gradient | §9.7 |
| 37 | 2026-11-03 02:40 | Wind speed every hour at least at airport sites | `#apHr` table: METAR cells shaded; AQMS-fallback cells italic grey; Amritsar uses Lahore AQMS when METAR is missing | §11.7 |
| 38 | 2026-11-03 02:43 | Fetch from aqi.epaforecast.com in realtime | Diagnosed as sign-in-only (`/api/v1/stations`). **Not** the collector path. Public collection uses `aqi.punjab.gov.pk` | §5.1, §18 |
| 39 | 2026-11-03 02:48 | Read aqi.punjab.gov.pk for all AQMS pollutants and AQI; fetch airport and WMO winds; keep November dashboard hourly | Collector `fetch`/`build`; client `extendData`; live line under the title | §6, §10 |
| 40 | 2026-11-03 02:49 | Plan collection without depending on this machine | Collector is a stdlib Python CLI invoked with `python3 -I collector.py`; no GUI, no local browser session | §6 |
| 41 | 2026-11-03 07:33 | Go ahead | Collector + `hours` documents + `extendData` + 9 s live-bootstrap timeout shipped | §6, §10 |
| 42 | 2026-11-05 14:42 | Update from AQMS; pull meteorology for source-to-sink and transboundary movement | 79 stations, all 41 districts measured; ECMWF regional flow outside Punjab; transport index; ECMWF cross-border rows | §9 |
| 43 | 2026-11-05 15:08 | Daily AQI situation report for authority decisions | Visual-first Word situation report | §13 |
| 44 | 2026-11-05 15:22 | 3 Nov missing; reanalyze; visuals rather than description | 3 Nov included; charts/maps first; valid-PM AQI rule applied to the dashboard | §8.4, §13 |
| 45 | 2026-11-05 15:32 | Next 24 hours forecasting | District persistence × own hour-of-day profile; CAMS and ECMWF wind adjustments omitted after they worsened the hindcast | §14 |
| 46 | 2026-11-05 16:02 | Word document for the AQI situation report | `.docx` with charts redrawn as images, editable tables | §13 |
| 47 | 2026-11-09 23:16 | Incorporate attached data and live sources; nearby Indian cities from IQAir | 1–9 Nov 23:00 record; FIRMS fires; IQAir Indian (and later all-sides) cities | §11.8, §13 |
| 48 | 2026-11-09 23:37 | Update report and artifact | Dashboard and Word report through 9 Nov 23:00; forecast through 10 Nov | §13, §14 |
| 49 | 2026-11-09 23:45 | ECMWF and other sources for cross-border transport from **all sides**; IQAir outside Punjab; crop fires | 117 boundary points; ECMWF wind × CAMS PM2.5; FIRMS by region; 32-city IQAir table | §9.6, §11.8 |
| 50 | 2026-11-10 00:02 | Update the November artifact accordingly | `#xbAll` section above Key findings; charts are fixed images from that night | §11.8 |
| 51 | 2026-11-10 01:11 | Update situation report provincial/district averages and heatmap from official daily AQI reports | Official 31 Oct–8 Nov figures; 9 Nov* provisional by the same method as the published Punjab and Lahore averages | §13 |
| 52 | 2026-11-10 01:37 | Meteoblue mixing-layer height 10 Nov hourly for all districts, with wind, pressure, humidity | Meteoblue numerical export requires a paid licence (site shows images only). NOAA GFS mixing height via Open-Meteo, ECMWF IFS wind/humidity/pressure. Special report section | §15 |
| 53 | 2026-11-10 02:49 | Draft advisory and cover letter | Cover letter + technical advisory Word files dated 10 Nov 2026 | §16 |
| 54 | 2026-11-10 02:57 | Follow attached advisory style; pollutants and mitigatory measures; formal tone | Pollutant-by-pollutant advisory in the 26 May EPA format (letterhead, Times New Roman, four sections, Issued-by block) | §16 |
| 55 | 2026-11-10 15:40 | Standalone dashboard file for download | Single HTML (~9.4–9.6 MB) that opens offline; live collector does not attach; standard fonts if Google Fonts are unreachable | §17 |

---

## 3. Packaging and artifacts

### 3.1 Baseline files (this specification)

| Path | Role |
|------|------|
| `original System/index.html` | Entire workstation: CSS, HTML regions, Method notes, `window.DATA` (embedded 1–9 Nov record), `window.extendData`, deferred `#mainsrc` engine, live bootstrap |
| `original System/collector/collector.py` | `fetch` and `build` CLI; portal / METAR / SYNOP / ECMWF; hour-document writer |

The HTML is one document, ~9,609,848 bytes, 805 lines. Almost all bulk is the `window.DATA=...` JSON on one line. `#mainsrc` is stored as `type="text/plain"` and injected after live hours are applied (or after a 9 s timeout).

### 3.2 Companion products delivered in the conversation (specified in §13–§17)

| Artifact | Role |
|----------|------|
| `Punjab_AQI_Situation_Report_05Nov2026.docx` then `Punjab_AQI_Situation_Report_09Nov2026.docx` | Daily situation report |
| `Cover_Letter_Technical_Advisory_10Nov2026.docx` | Dispatch cover letter |
| `Technical_Advisory_Smog_Episode_10Nov2026.docx` | Pollutant-specific advisory |
| `Punjab_Air_Quality_November_2026_Dashboard.html` | Standalone download (same content family as `original System/index.html`) |
| `airport_wind_26Oct2026.csv`, `airport_wind_Nov2026.csv` | METAR extracts |
| `punjab_live.html` | Earlier live prototype (IQAir + FIRMS + CAMS layers). Its hourly task was later **repointed** to feed the November dashboard; the November file is the surviving live surface |

### 3.3 Runtime shape

```
Browser (offline)
  └── index.html
        ├── window.DATA          embedded 216-hour record
        ├── window.extendData    merges hour-docs newer than meta.exportEnd
        ├── #mainsrc             canvas engine, tables, CPF, transport
        └── live bootstrap       optional claude.use('db') collection "hours"

Collector host (any machine with Python 3 and curl)
  python3 -I collector.py fetch OUT
  python3 -I collector.py build OUT EXISTING
        └── OUT/raw.json, OUT/docs/hYYYYMMDDHH.json, OUT/batch.json
```

No application server, no database engine, and no Node toolchain are required to **view** the baseline. Live hours require the host that can write the `hours` collection the bootstrap reads.

---

## 4. Time, geography, and monitoring network

### 4.1 Temporal baseline

| Item | Value |
|------|--------|
| `meta.start` | `2026-11-01 00:00` |
| `meta.end` | `2026-11-09 23:00` |
| Frame count | 216 consecutive PKT hours |
| Frame meaning | Hour-beginning average (00:00 is 00:00–01:00 PKT) |
| Export composition (Method notes) | 1–4 Nov periodic export (56 stations); 4 Nov 00:00–5 Nov 11:00; 1–9 Nov periodic exports to 9 Nov 23:00 (80 stations / 24 new tehsil-level sites). 3 Nov is present in the delivered 216-hour record |
| Live continuation | Hourly portal snapshots after `meta.exportEnd`, padded as empty frames where the collector wrote nothing |

`DATA.hours` is a dense list of `"YYYY-MM-DD HH:00"` strings. `extendData` appends only timestamps strictly after `meta.exportEnd` and fills every missing hour in between with empty frames so the scrubber stays hourly.

### 4.2 Administrative geography

The map uses EPA Punjab’s own 41-district shapefile (`DATA.adm`: each district has `label [lon,lat]` and `polys`). The Punjab outline and the India–Pakistan border line come from the same geography. Neighbouring Pakistani provinces and Indian states are drawn from hardcoded GeoJSON-like rings in `#mainsrc` (`GEO` and `IND`).

**41 districts** (all `est: false` in the 1–9 Nov baseline): Attock, Bahawalnagar, Bahawalpur, Bhakkar, Chakwal, Chiniot, DG Khan, Faisalabad, Gujranwala, Gujrat, Hafizabad, Jhang, Jhelum, Kasur, Khanewal, Khushab, Kot Addu, Lahore, Layyah, Lodhran, Mandi Bahauddin, Mianwali, Multan, Murree, Muzaffargarh, Nankana Sahib, Narowal, Okara, Pakpattan, Rahim Yar Khan, Rajanpur, Rawalpindi, Sahiwal, Sargodha, Sheikhupura, Sialkot, Talagang, Taunsa, Toba Tek Singh, Vehari, Wazirabad.

Earlier October builds used a 36-district scheme in which Wazirabad counted in Gujranwala, Murree in Rawalpindi, Talagang in Chakwal and Kot Addu in Muzaffargarh. The baseline no longer does that.

**Unmonitored-district imputation** remains in the engine (`D[n].est`, IDW, hatch, italic table rows, `~` prefix). In this 1–9 Nov snapshot every district has at least one assigned station, so `unmon` is empty. Chiniot and Lodhran still report **no valid PM** for most hours; their AQI is suppressed by the valid-PM rule (§8.4) and their period means may be `null`.

### 4.3 Map projection

Equirectangular with a cosine scale at 31°N:

```
B = {lo0: 69.1, lo1: 75.75, la0: 27.55, la1: 34.3}
KX = cos(31°)
P(lon, lat) = [(lon - lo0) * KX * S, (la1 - lat) * S]
```

`S` is chosen so the canvas fills the map box, capped so height does not exceed `max(440, innerHeight - 110)` on viewports wider than 980 px. Device pixel ratio is clamped at 2.

Lahore inset bounds used by `drawLahore` (and historically a dashed box on the main map):

```
LB = {lo0: 74.08, lo1: 74.64, la0: 31.34, la1: 31.70}
```

Hit-testing uses an offscreen canvas (`hit.isPointInPath`) against `admPaths`.

### 4.4 AQMS locations

Plotting uses `DATA.stations` (79). A parallel `DATA.network` array holds the 56 shapefile sites (51 Fixed, 5 Mobile; phases Operational / Air-Safe 18 / Air-Safe 08). `DATA.coordsrc` records how each of the 79 plot positions was obtained.

**EMC-confirmed Lahore coordinates** (ask 34; applied on every dashboard):

| Station | lat | lon |
|---------|-----|-----|
| Safari Park-LHR | 31.382315 | 74.218173 |
| Kahna Nau Hospital-LHR | 31.370969 | 74.365098 |
| PKLI-LHR | 31.455944 | 74.463773 |
| FMDRC-LHR | 31.535903 | 74.435188 |
| UET-LHR | 31.579826 | 74.355003 |
| LWMC-LHR | 31.463797 | 74.225942 |
| Punjab University-LHR | 31.479659 | 74.266087 |
| Govt. Teaching Hospital Shahdara-LHR | 31.638126 | 74.285182 |
| Gulberg III Lahore - Mobile 1 | 31.495861 | 74.333417 |
| Wagha Border LHR - Mobile 3 | 31.602342 | 74.54495 |
| Egerton Road - Mobile 4 | 31.561035 | 74.330999 |

Lathepur LHR - Mobile 2 (31.718129, 74.389718) and BHU Jandiala Kalsan LHR - Mobile 5 (31.849951, 74.515707) keep shapefile geometry and remain assigned to Lahore.

**Shapefile Lat/Lon attribute errors** (geometry used instead): Gulberg III showed 31.22 instead of ~31.50; DC Office Sialkot duplicated Gujranwala; Wazirabad showed 28.77, 77.51 (a point in India).

**Approximate coordinates** (not in the station shapefile, or tehsil sites placed at town centre): Sahiwal, Rajanpur, Talagang, Khushab, plus the 24 tehsil-level sites listed in `coordsrc` as `approximate (town centre)` or town-from-shapefile.

**Skipped:** `OneNetwork Station 25` — `{"OneNetwork Station 25":"location not known"}`.

Lahore has 13 stations in the embedded record (11 EMC-confirmed + Lathepur + Jandiala Kalsan). Five of the 79 are `mobile: true` (the five Lahore mobiles).

The full 79-row and 41-row inventories are in §4.7.

### 4.5 Collector district centroids (ECMWF query points)

`collector.py` requests ECMWF 10 m wind at these 41 points (order = request order). They are **not** identical to `DATA.districts` centroids.

| District | lat | lon |
|----------|-----|-----|
| Attock | 33.773 | 72.362 |
| Bahawalnagar | 29.618 | 73.025 |
| Bahawalpur | 29.389 | 71.728 |
| Bhakkar | 31.617 | 71.08 |
| Chakwal | 32.925 | 72.805 |
| Chiniot | 31.72 | 72.989 |
| DG Khan | 30.052 | 70.63 |
| Faisalabad | 31.436 | 73.102 |
| Gujranwala | 32.216 | 74.176 |
| Gujrat | 32.585 | 74.079 |
| Hafizabad | 32.068 | 73.711 |
| Jhang | 31.271 | 72.324 |
| Jhelum | 32.943 | 73.74 |
| Kasur | 31.116 | 74.467 |
| Khanewal | 30.302 | 71.929 |
| Khushab | 32.297 | 72.352 |
| Kot Addu | 30.503 | 70.956 |
| Lahore | 31.549 | 74.364 |
| Layyah | 30.994 | 71.28 |
| Lodhran | 29.649 | 71.775 |
| Mandi Bahauddin | 32.543 | 73.48 |
| Mianwali | 32.584 | 71.546 |
| Multan | 30.214 | 71.505 |
| Murree | 33.905 | 73.402 |
| Muzaffargarh | 30.076 | 71.19 |
| Nankana Sahib | 31.448 | 73.698 |
| Narowal | 32.097 | 74.894 |
| Okara | 30.801 | 73.426 |
| Pakpattan | 30.362 | 73.382 |
| Rahim Yar Khan | 28.423 | 70.318 |
| Rajanpur | 29.104 | 70.33 |
| Rawalpindi | 33.593 | 73.055 |
| Sahiwal | 30.664 | 73.106 |
| Sargodha | 32.055 | 72.688 |
| Sheikhupura | 31.712 | 73.976 |
| Sialkot | 32.407 | 74.528 |
| Talagang | 32.928 | 72.415 |
| Taunsa | 30.897 | 70.619 |
| Toba Tek Singh | 30.955 | 72.535 |
| Vehari | 30.05 | 72.357 |
| Wazirabad | 32.32 | 73.956 |

### 4.6 Station-id map (collector `PMAP`)

Portal `station_id` → network name, matched on coordinates and names on 3 Nov 2026. `NAME_FALLBACK = {"Chiniot": "Chiniot"}` covers the district-stations feed when the main dashboard omits Chiniot.

| id | Network name | id | Network name |
|----|--------------|----|--------------|
| 1 | ARID University Rawalpindi | 24 | Safari Park-LHR |
| 2 | BISE Sargodha | 25 | UET-LHR |
| 3 | BZU Multan | 27 | Gulberg III Lahore - Mobile 1 |
| 4 | DC Office DG Khan | 28 | Lathepur LHR - Mobile 2 |
| 5 | DC Office Faisalabad | 29 | Wagha Border LHR - Mobile 3 |
| 6 | DC Office Gujranwala | 30 | Egerton Road - Mobile 4 |
| 7 | DC Office Rawalpindi | 31 | BHU Jandiala Kalsan LHR - Mobile 5 |
| 8 | DC Office Sargodha | 32 | DC Office Kasur |
| 9 | DC Office Sialkot | 33 | DC Office Narowal |
| 10 | DHQ Sheikhupura | 34 | DC Office Hafizabad |
| 11 | Drug Testing Laboratory Rawalpindi | 35 | DC Office Gujrat |
| 12 | FMDRC-LHR | 36 | DC Office Chakwal |
| 13 | GCU Faisalabad | 37 | DC Office Khanewal |
| 14 | GCW Gujranwala | 38 | DC Office Muzaffargarh |
| 15 | Govt. Teaching Hospital Shahdara-LHR | 39 | DC Office Rahim Yar Khan |
| 16 | IUB (Baghdad Campus) Bahawalpur | 169 | Pakpattan |
| 17 | IUB (Khawaja Fareed Campus) Bahawalpur | 170 | Okara |
| 18 | Kahna Nau Hospital-LHR | 171 | Sahiwal |
| 19 | LWMC-LHR | 172 | Wazirabad |
| 20 | M. Nawaz Sharif University of Engineering & Technology Multan | 173 | Mandi Bahauddin |
| 21 | NTU Faisalabad | 174 | Rajanpur |
| 22 | PKLI-LHR | 175 | Vehari |
| 23 | Punjab University-LHR | 176 | Jhelum |
| 177 | Nankana Sahib | 178 | Jhang |
| 179 | Attok | 180 | Kot Addu |
| 181 | Bhakkar | 183 | Talagang |
| 184 | Khushab | 185 | Mianwali |
| 186 | Murree | | |

Conversation notes additional **name aliases** seen on the portal (Barki Road → FMDRC, DHA Phase 6 → PKLI, GT Road → UET, Multan Road → LWMC). The collector matches by `station_id` through `PMAP`, so those aliases resolve once the portal IDs are in the map. Unmapped portal rows are listed in `unmapped_stations` and **dropped** (no invented names).

The 24 tehsil-level stations added in the 1–5 / 1–9 Nov exports are **not** all in `PMAP`. Method notes state the first successful collector run must list unknown portal IDs so they can be added. Until then, live hours for those sites are omitted.

### 4.7 Full station, district, shapefile, and QC inventories

The following tables are extracted from `window.DATA` without hourly arrays.

### Station inventory (window.DATA.stations, 79 rows)

| Station | District | lat | lon | Mobile | Coordinate source |
|---------|----------|-----|-----|--------|-------------------|
| Safari Park-LHR | Lahore | 31.382315 | 74.218173 | no | EMC confirmed |
| PKLI-LHR | Lahore | 31.455944 | 74.463773 | no | EMC confirmed |
| FMDRC-LHR | Lahore | 31.535903 | 74.435188 | no | EMC confirmed |
| UET-LHR | Lahore | 31.579826 | 74.355003 | no | EMC confirmed |
| LWMC-LHR | Lahore | 31.463797 | 74.225942 | no | EMC confirmed |
| Govt. Teaching Hospital Shahdara-LHR | Lahore | 31.638126 | 74.285182 | no | EMC confirmed |
| Gulberg III Lahore - Mobile 1 | Lahore | 31.495861 | 74.333417 | yes | EMC confirmed |
| Lathepur LHR - Mobile 2 | Lahore | 31.718129 | 74.389718 | yes | shapefile |
| Wagha Border LHR - Mobile 3 | Lahore | 31.602342 | 74.54495 | yes | EMC confirmed |
| Egerton Road - Mobile 4 | Lahore | 31.561035 | 74.330999 | yes | EMC confirmed |
| BHU Jandiala Kalsan LHR - Mobile 5 | Lahore | 31.849951 | 74.515707 | yes | shapefile |
| DC Office Faisalabad | Faisalabad | 31.430876 | 73.088288 | no | shapefile |
| GCU Faisalabad | Faisalabad | 31.416246 | 73.070003 | no | shapefile |
| NTU Faisalabad | Faisalabad | 31.462113 | 73.148547 | no | shapefile |
| GCW Gujranwala | Gujranwala | 32.258159 | 74.157828 | no | shapefile |
| DC Office Gujranwala | Gujranwala | 32.174674 | 74.194953 | no | shapefile |
| Wazirabad | Wazirabad | 32.32045799874081 | 73.95627161090476 | no | shapefile |
| BZU Multan | Multan | 30.262346 | 71.512538 | no | shapefile |
| M. Nawaz Sharif University of Engineering & Technology Multan | Multan | 30.165442 | 71.4969 | no | shapefile |
| IUB (Baghdad Campus) Bahawalpur | Bahawalpur | 29.378984 | 71.765149 | no | shapefile |
| IUB (Khawaja Fareed Campus) Bahawalpur | Bahawalpur | 29.398271 | 71.690796 | no | shapefile |
| DC Office Sargodha | Sargodha | 32.074811 | 72.675612 | no | shapefile |
| BISE Sargodha | Sargodha | 32.035115 | 72.70054 | no | shapefile |
| DC Office Sialkot | Sialkot | 32.407349229182145 | 74.52776451204882 | no | shapefile |
| DC Office DG Khan | DG Khan | 30.05179 | 70.629661 | no | shapefile |
| DC Office Rawalpindi | Rawalpindi | 33.584625 | 73.068916 | no | shapefile |
| ARID University Rawalpindi | Rawalpindi | 33.650618 | 73.080671 | no | shapefile |
| Drug Testing Laboratory Rawalpindi | Rawalpindi | 33.542264 | 73.01392 | no | shapefile |
| Murree | Murree | 33.90465 | 73.402133 | no | shapefile |
| Pakpattan | Pakpattan | 30.362089 | 73.381944 | no | shapefile |
| Okara | Okara | 30.800608 | 73.425744 | no | shapefile |
| Sahiwal | Sahiwal | 30.664 | 73.106 | no | approximate (not in shapefile) |
| Mandi Bahauddin | Mandi Bahauddin | 32.54285 | 73.479958 | no | shapefile |
| Rajanpur | Rajanpur | 29.104 | 70.33 | no | approximate (not in shapefile) |
| Vehari | Vehari | 30.0504 | 72.357033 | no | shapefile |
| Jhelum | Jhelum | 32.943439 | 73.739536 | no | shapefile |
| Nankana Sahib | Nankana Sahib | 31.448039 | 73.697517 | no | shapefile |
| Jhang | Jhang | 31.271281 | 72.3241 | no | shapefile |
| Attok | Attock | 33.773017 | 72.361703 | no | shapefile |
| Kot Addu | Kot Addu | 30.502606 | 70.956297 | no | shapefile |
| Bhakkar | Bhakkar | 31.616775 | 71.079689 | no | shapefile |
| Talagang | Talagang | 32.928 | 72.415 | no | approximate (not in shapefile) |
| Khushab | Khushab | 32.297 | 72.352 | no | approximate (not in shapefile) |
| Kahna Nau Hospital-LHR | Lahore | 31.370969 | 74.365098 | no | EMC confirmed |
| Punjab University-LHR | Lahore | 31.479659 | 74.266087 | no | EMC confirmed |
| DC Office Kasur | Kasur | 31.115567 | 74.467289 | no | shapefile |
| DC Office Narowal | Narowal | 32.096819 | 74.894167 | no | shapefile |
| DC Office Hafizabad | Hafizabad | 32.0676 | 73.711336 | no | shapefile |
| DC Office Gujrat | Gujrat | 32.584725 | 74.078939 | no | shapefile |
| DC Office Chakwal | Chakwal | 32.925367 | 72.805453 | no | shapefile |
| DC Office Khanewal | Khanewal | 30.301792 | 71.929103 | no | shapefile |
| DC Office Muzaffargarh | Muzaffargarh | 30.075614 | 71.190331 | no | shapefile |
| DC Office Rahim Yar Khan | Rahim Yar Khan | 28.422725 | 70.318247 | no | shapefile |
| Chiniot | Chiniot | 31.720289 | 72.988881 | no | shapefile |
| DHQ Sheikhupura | Sheikhupura | 31.711938 | 73.976367 | no | shapefile |
| Mianwali | Mianwali | 32.584106 | 71.54595 | no | shapefile |
| DC Office Layyah | Layyah | 30.983786 | 70.964064 | no | shapefile (Deputy Commissioner Office, Layyah) |
| DC Office Toba Tek Singh | Toba Tek Singh | 30.965872 | 72.486181 | no | shapefile (Deputy Commissioner Office, TT Singh) |
| Gymkhana Lodhran | Lodhran | 29.537075 | 71.627592 | no | approximate (town of Lodhran, from shapefile) |
| DD Development Bahawalnagar | Bahawalnagar | 30.010853 | 73.255711 | no | approximate (town of Bahawalnagar, from shapefile) |
| AC Office Choa Saidan Shah | Chakwal | 32.719 | 72.979 | no | approximate (town centre) |
| AC Office Pind Dadan Khan | Jhelum | 32.588 | 73.045 | no | approximate (town centre) |
| AC Office Sharaqpur | Sheikhupura | 31.462 | 74.101 | no | approximate (town centre) |
| AC Office Taunsa | Taunsa | 30.704 | 70.651 | no | approximate (town centre) |
| GHSS Kolo Tarar | Hafizabad | 32.06 | 73.4 | no | approximate (town centre) |
| Govt Boys College Quaidabad | Khushab | 32.33 | 71.91 | no | approximate (town centre) |
| Govt Girls College Ladhewala | Gujranwala | 32.215 | 74.115 | no | approximate (town centre) |
| Govt Girls College Mian Channu | Khanewal | 30.44 | 72.355 | no | approximate (town centre) |
| Govt. High School Dajal | Rajanpur | 29.557 | 70.377 | no | approximate (town centre) |
| Gujar Khan | Rawalpindi | 33.253 | 73.304 | no | approximate (town centre) |
| Kot Naina Shakargarh | Narowal | 32.47 | 75.09 | no | approximate (town centre) |
| MC Office Kallar Kahar | Chakwal | 32.78 | 72.698 | no | approximate (town centre) |
| Maryam Nawaz Clinic DG Khan | DG Khan | 30.04 | 70.65 | no | approximate (town centre) |
| Narang Mandi | Sheikhupura | 31.903 | 74.517 | no | approximate (town centre) |
| PS Ganda Singh Wala | Kasur | 31.04 | 74.54 | no | approximate (town centre) |
| PS Harappa | Sahiwal | 30.627 | 72.87 | no | approximate (town centre) |
| Suthra Punjab Office Fateh Jang | Attock | 33.565 | 72.64 | no | approximate (town centre) |
| THQ Alipur | Muzaffargarh | 29.382 | 70.912 | no | approximate (town centre) |
| THQ Haroonabad | Bahawalnagar | 29.61 | 73.138 | no | approximate (town centre) |

### District inventory (window.DATA.districts, 41 rows; est=false for all in the 1–9 Nov baseline)

| District | lat | lon | Stations |
|----------|-----|-----|----------|
| Attock | 33.669 | 72.501 | Attok, Suthra Punjab Office Fateh Jang |
| Bahawalnagar | 29.81 | 73.197 | DD Development Bahawalnagar, THQ Haroonabad |
| Bahawalpur | 29.389 | 71.728 | IUB (Baghdad Campus) Bahawalpur, IUB (Khawaja Fareed Campus) Bahawalpur |
| Bhakkar | 31.617 | 71.08 | Bhakkar |
| Chakwal | 32.808 | 72.827 | DC Office Chakwal, AC Office Choa Saidan Shah, MC Office Kallar Kahar |
| Chiniot | 31.72 | 72.989 | Chiniot |
| DG Khan | 30.046 | 70.64 | DC Office DG Khan, Maryam Nawaz Clinic DG Khan |
| Faisalabad | 31.436 | 73.102 | DC Office Faisalabad, GCU Faisalabad, NTU Faisalabad |
| Gujranwala | 32.216 | 74.156 | GCW Gujranwala, DC Office Gujranwala, Govt Girls College Ladhewala |
| Gujrat | 32.585 | 74.079 | DC Office Gujrat |
| Hafizabad | 32.064 | 73.556 | DC Office Hafizabad, GHSS Kolo Tarar |
| Jhang | 31.271 | 72.324 | Jhang |
| Jhelum | 32.766 | 73.392 | Jhelum, AC Office Pind Dadan Khan |
| Kasur | 31.078 | 74.504 | DC Office Kasur, PS Ganda Singh Wala |
| Khanewal | 30.371 | 72.142 | DC Office Khanewal, Govt Girls College Mian Channu |
| Khushab | 32.313 | 72.131 | Khushab, Govt Boys College Quaidabad |
| Kot Addu | 30.503 | 70.956 | Kot Addu |
| Lahore | 31.549 | 74.364 | Safari Park-LHR, PKLI-LHR, FMDRC-LHR, UET-LHR, LWMC-LHR, Govt. Teaching Hospital Shahdara-LHR, Gulberg III Lahore - Mobile 1, Lathepur LHR - Mobile 2, Wagha Border LHR - Mobile 3, Egerton Road - Mobile 4, BHU Jandiala Kalsan LHR - Mobile 5, Kahna Nau Hospital-LHR, Punjab University-LHR |
| Layyah | 30.984 | 70.964 | DC Office Layyah |
| Lodhran | 29.537 | 71.628 | Gymkhana Lodhran |
| Mandi Bahauddin | 32.543 | 73.48 | Mandi Bahauddin |
| Mianwali | 32.584 | 71.546 | Mianwali |
| Multan | 30.214 | 71.505 | BZU Multan, M. Nawaz Sharif University of Engineering & Technology Multan |
| Murree | 33.905 | 73.402 | Murree |
| Muzaffargarh | 29.729 | 71.051 | DC Office Muzaffargarh, THQ Alipur |
| Nankana Sahib | 31.448 | 73.698 | Nankana Sahib |
| Narowal | 32.283 | 74.992 | DC Office Narowal, Kot Naina Shakargarh |
| Okara | 30.801 | 73.426 | Okara |
| Pakpattan | 30.362 | 73.382 | Pakpattan |
| Rahim Yar Khan | 28.423 | 70.318 | DC Office Rahim Yar Khan |
| Rajanpur | 29.33 | 70.354 | Rajanpur, Govt. High School Dajal |
| Rawalpindi | 33.508 | 73.117 | DC Office Rawalpindi, ARID University Rawalpindi, Drug Testing Laboratory Rawalpindi, Gujar Khan |
| Sahiwal | 30.646 | 72.988 | Sahiwal, PS Harappa |
| Sargodha | 32.055 | 72.688 | DC Office Sargodha, BISE Sargodha |
| Sheikhupura | 31.692 | 74.198 | DHQ Sheikhupura, AC Office Sharaqpur, Narang Mandi |
| Sialkot | 32.407 | 74.528 | DC Office Sialkot |
| Talagang | 32.928 | 72.415 | Talagang |
| Taunsa | 30.704 | 70.651 | AC Office Taunsa |
| Toba Tek Singh | 30.966 | 72.486 | DC Office Toba Tek Singh |
| Vehari | 30.05 | 72.357 | Vehari |
| Wazirabad | 32.32 | 73.956 | Wazirabad |

### Shapefile network catalog (window.DATA.network, 56 rows)

| Shapefile name | District | Type | Phase | lat | lon |
|----------------|----------|------|-------|-----|-----|
| Gulberg III | Lahore | Mobile | Operational | 31.50494 | 74.33488 |
| Lathe Pur | Lahore | Mobile | Operational | 31.71813 | 74.38972 |
| Wahga Border | Lahore | Mobile | Operational | 31.60234 | 74.54495 |
| Egerton Road | Lahore | Mobile | Operational | 31.56104 | 74.331 |
| BHU Jandiala Kalasan | Lahore | Mobile | Operational | 31.84995 | 74.51571 |
| LWMC | Lahore | Fixed | Operational | 31.46387 | 74.22509 |
| Punjab University | Lahore | Fixed | Operational | 31.47966 | 74.26603 |
| UET | Lahore | Fixed | Operational | 31.57763 | 74.35739 |
| FMDRC | Lahore | Fixed | Operational | 31.53573 | 74.43563 |
| PKLI | Lahore | Fixed | Operational | 31.45397 | 74.46317 |
| Kahna Hospital | Lahore | Fixed | Operational | 31.37108 | 74.36493 |
| Shahdara | Lahore | Fixed | Operational | 31.63821 | 74.28411 |
| Safari Park | Lahore | Fixed | Operational | 31.38604 | 74.21164 |
| Sheikhupura | Sheikhupura | Fixed | Operational | 31.71194 | 73.97637 |
| DC Office Faisalabad | Faisalabad | Fixed | Operational | 31.43088 | 73.08829 |
| GCU Faisalabad | Faisalabad | Fixed | Operational | 31.41625 | 73.07 |
| NTU Faisalabad | Faisalabad | Fixed | Operational | 31.46211 | 73.14855 |
| BZU Multan | Multan | Fixed | Operational | 30.26235 | 71.51254 |
| MNS University of Engineering & Technology Multan | Multan | Fixed | Operational | 30.16544 | 71.4969 |
| IUB (Baghdad Campus) Bahawalpur | Bahawalpur | Fixed | Operational | 29.37898 | 71.76515 |
| IUB (Abbasia Campus) Bahawalpur | Bahawalpur | Fixed | Operational | 29.39827 | 71.6908 |
| DC Office DG Khan | DG Khan | Fixed | Operational | 30.05179 | 70.62966 |
| DC Office Rawalpindi | Rawalpindi | Fixed | Operational | 33.58463 | 73.06892 |
| ARID University Rawalpindi | Rawalpindi | Fixed | Operational | 33.65062 | 73.08067 |
| Drug Testing Laboratory Rawalpindi | Rawalpindi | Fixed | Operational | 33.54226 | 73.01392 |
| DC Office Sargodha | Sargodha | Fixed | Operational | 32.07481 | 72.67561 |
| BISE Sargodha | Sargodha | Fixed | Operational | 32.03511 | 72.70054 |
| GCW Gujranwala | Gujranwala | Fixed | Operational | 32.25816 | 74.15783 |
| DC Office Gujranwala | Gujranwala | Fixed | Operational | 32.17467 | 74.19495 |
| DC Office Sialkot | Sialkot | Fixed | Operational | 32.40735 | 74.52776 |
| Deputy Commissioner Office, Gujrat | Gujrat | Fixed | Air-Safe 08 | 32.58472 | 74.07894 |
| Deputy Commissioner Office, Hafizabad | Hafizabad | Fixed | Air-Safe 08 | 32.0676 | 73.71134 |
| Deputy Commissioner Office, Chakwal | Chakwal | Fixed | Air-Safe 08 | 32.92537 | 72.80545 |
| Deputy Commissioner Office, Khanewal | Khanewal | Fixed | Air-Safe 08 | 30.30179 | 71.9291 |
| Deputy Commissioner Office, RY Khan | Rahim Yar Khan | Fixed | Air-Safe 08 | 28.42272 | 70.31825 |
| Deputy Commissioner Office, Narowal | Narowal | Fixed | Air-Safe 08 | 32.09682 | 74.89417 |
| Deputy Commissioner Office, Muzaffargarh | Muzaffargarh | Fixed | Air-Safe 08 | 30.07561 | 71.19033 |
| Deputy Commissioner Office, Kasur | Kasur | Fixed | Air-Safe 08 | 31.11557 | 74.46729 |
| Deputy Commissioner Office, Attock | Attock | Fixed | Air-Safe 18 | 33.77302 | 72.3617 |
| Deputy Commissioner Office, Jhelum | Jhelum | Fixed | Air-Safe 18 | 32.94344 | 73.73954 |
| Deputy Commissioner Office, Murree | Murree | Fixed | Air-Safe 18 | 33.90465 | 73.40213 |
| Deputy Commissioner Office, MB Din | Mandi Bahauddin | Fixed | Air-Safe 18 | 32.54285 | 73.47996 |
| Deputy Commissioner Office, Nankana Sahib | Nankana Sahib | Fixed | Air-Safe 18 | 31.44804 | 73.69752 |
| Deputy Commissioner Office, Okara | Okara | Fixed | Air-Safe 18 | 30.80061 | 73.42574 |
| Deputy Commissioner Office, Bahawalnagar | Bahawalnagar | Fixed | Air-Safe 18 | 30.01085 | 73.25571 |
| Deputy Commissioner Office, Kot Addu | Kot Addu | Fixed | Air-Safe 18 | 30.50261 | 70.9563 |
| Deputy Commissioner Office, Mianwali | Mianwali | Fixed | Air-Safe 18 | 32.58411 | 71.54595 |
| Deputy Commissioner Office, Bhakkar | Bhakkar | Fixed | Air-Safe 18 | 31.61678 | 71.07969 |
| Deputy Commissioner Office, Layyah | Layyah | Fixed | Air-Safe 18 | 30.98379 | 70.96406 |
| Deputy Commissioner Office, Lodhran | Lodhran | Fixed | Air-Safe 18 | 29.53708 | 71.62759 |
| Deputy Commissioner Office, Pakpattan | Pakpattan | Fixed | Air-Safe 18 | 30.36209 | 73.38194 |
| Deputy Commissioner Office, Wazirabad | Wazirabad | Fixed | Air-Safe 18 | 32.32046 | 73.95627 |
| Deputy Commissioner Office, Vehari | Vehari | Fixed | Air-Safe 18 | 30.0504 | 72.35703 |
| Deputy Commissioner Office, Chiniot | Chiniot | Fixed | Air-Safe 18 | 31.72029 | 72.98888 |
| Deputy Commissioner Office, TT Singh | Toba Tek Singh | Fixed | Air-Safe 18 | 30.96587 | 72.48618 |
| Deputy Commissioner Office, Jhang | Jhang | Fixed | Air-Safe 18 | 31.27128 | 72.3241 |

### Per-station QC counts (window.DATA.qa; hours with a finite value after cleaning)

| Station | n | wind_valid | AQI | AQI_spk | PM10 | PM10_spk | PM2.5 | PM2.5_spk | NO2 | NO2_spk | SO2 | SO2_spk | CO | CO_spk | O3 | O3_spk | NO | NO_spk | NOX | NOX_spk |
|---------|---|------------|-----|---------|------|----------|-------|-----------|-----|---------|-----|---------|----|--------|----|--------|----|--------|-----|---------|
| Safari Park-LHR | 216 | 216 | 215 | 0 | 215 | 0 | 215 | 0 | 216 | 0 | 216 | 0 | 213 | 0 | 190 | 0 | 216 | 0 | 216 | 0 |
| PKLI-LHR | 216 | 216 | 216 | 0 | 216 | 0 | 213 | 0 | 216 | 0 | 216 | 0 | 216 | 0 | 212 | 0 | 216 | 0 | 216 | 0 |
| FMDRC-LHR | 216 | 216 | 214 | 0 | 210 | 0 | 212 | 0 | 209 | 0 | 213 | 2 | 216 | 0 | 212 | 0 | 192 | 1 | 203 | 1 |
| UET-LHR | 216 | 216 | 215 | 0 | 207 | 0 | 215 | 0 | 214 | 0 | 214 | 0 | 208 | 0 | 216 | 0 | 215 | 1 | 215 | 0 |
| LWMC-LHR | 216 | 216 | 216 | 0 | 215 | 0 | 216 | 0 | 213 | 0 | 209 | 0 | 211 | 0 | 216 | 0 | 208 | 6 | 214 | 2 |
| Govt. Teaching Hospital Shahdara-LHR | 216 | 216 | 215 | 0 | 215 | 0 | 211 | 1 | 216 | 0 | 216 | 0 | 213 | 0 | 216 | 0 | 216 | 0 | 216 | 0 |
| Gulberg III Lahore - Mobile 1 | 216 | 216 | 216 | 0 | 204 | 0 | 215 | 0 | 212 | 0 | 202 | 0 | 213 | 0 | 203 | 0 | 211 | 1 | 212 | 0 |
| Lathepur LHR - Mobile 2 | 216 | 213 | 208 | 0 | 208 | 0 | 204 | 0 | 210 | 0 | 211 | 0 | 211 | 0 | 211 | 0 | 211 | 0 | 211 | 0 |
| Wagha Border LHR - Mobile 3 | 216 | 213 | 207 | 0 | 205 | 0 | 205 | 0 | 211 | 0 | 211 | 0 | 209 | 0 | 211 | 0 | 210 | 1 | 211 | 0 |
| Egerton Road - Mobile 4 | 216 | 215 | 213 | 0 | 211 | 0 | 213 | 0 | 209 | 0 | 210 | 0 | 211 | 0 | 211 | 0 | 211 | 0 | 211 | 0 |
| BHU Jandiala Kalsan LHR - Mobile 5 | 216 | 205 | 202 | 0 | 202 | 0 | 176 | 0 | 192 | 0 | 192 | 0 | 192 | 0 | 187 | 0 | 192 | 0 | 192 | 0 |
| DC Office Faisalabad | 216 | 214 | 213 | 0 | 211 | 0 | 213 | 0 | 211 | 0 | 205 | 2 | 212 | 0 | 212 | 0 | 212 | 0 | 212 | 0 |
| GCU Faisalabad | 216 | 214 | 213 | 0 | 213 | 0 | 210 | 0 | 210 | 0 | 211 | 0 | 211 | 0 | 211 | 0 | 210 | 0 | 210 | 0 |
| NTU Faisalabad | 216 | 209 | 210 | 0 | 207 | 0 | 210 | 0 | 160 | 0 | 199 | 1 | 206 | 0 | 205 | 0 | 160 | 0 | 160 | 0 |
| GCW Gujranwala | 216 | 211 | 212 | 0 | 205 | 0 | 212 | 0 | 208 | 0 | 208 | 0 | 208 | 0 | 208 | 0 | 207 | 1 | 208 | 0 |
| DC Office Gujranwala | 216 | 213 | 213 | 0 | 210 | 0 | 213 | 0 | 210 | 0 | 209 | 0 | 210 | 0 | 210 | 0 | 210 | 0 | 210 | 0 |
| Wazirabad | 216 | 0 | 216 | 0 | 208 | 0 | 216 | 0 | 215 | 0 | 216 | 0 | 213 | 0 | 178 | 0 | 216 | 0 | 216 | 0 |
| BZU Multan | 216 | 214 | 213 | 0 | 211 | 0 | 211 | 0 | 211 | 0 | 212 | 0 | 212 | 0 | 212 | 0 | 211 | 0 | 211 | 0 |
| M. Nawaz Sharif University of Engineering & Technology Multan | 216 | 212 | 203 | 0 | 203 | 0 | 203 | 0 | 201 | 0 | 199 | 0 | 201 | 0 | 201 | 0 | 201 | 0 | 201 | 0 |
| IUB (Baghdad Campus) Bahawalpur | 216 | 212 | 212 | 0 | 206 | 0 | 212 | 0 | 209 | 0 | 209 | 0 | 209 | 0 | 209 | 0 | 209 | 0 | 209 | 0 |
| IUB (Khawaja Fareed Campus) Bahawalpur | 216 | 210 | 209 | 0 | 209 | 0 | 209 | 0 | 207 | 0 | 207 | 0 | 207 | 0 | 207 | 0 | 207 | 0 | 207 | 0 |
| DC Office Sargodha | 216 | 215 | 216 | 0 | 214 | 0 | 216 | 0 | 210 | 0 | 213 | 0 | 207 | 0 | 213 | 0 | 213 | 0 | 213 | 0 |
| BISE Sargodha | 216 | 215 | 214 | 0 | 214 | 0 | 214 | 0 | 212 | 0 | 212 | 0 | 212 | 0 | 212 | 0 | 212 | 0 | 212 | 0 |
| DC Office Sialkot | 216 | 215 | 215 | 0 | 215 | 0 | 215 | 0 | 211 | 0 | 212 | 0 | 212 | 0 | 212 | 0 | 210 | 2 | 212 | 0 |
| DC Office DG Khan | 216 | 213 | 208 | 0 | 206 | 0 | 207 | 0 | 209 | 0 | 209 | 0 | 210 | 0 | 208 | 0 | 210 | 0 | 210 | 0 |
| DC Office Rawalpindi | 216 | 213 | 214 | 0 | 210 | 0 | 213 | 0 | 209 | 0 | 209 | 0 | 209 | 0 | 207 | 0 | 207 | 2 | 209 | 0 |
| ARID University Rawalpindi | 216 | 210 | 204 | 0 | 204 | 0 | 204 | 0 | 200 | 0 | 195 | 0 | 200 | 0 | 200 | 0 | 200 | 0 | 200 | 0 |
| Drug Testing Laboratory Rawalpindi | 216 | 216 | 216 | 0 | 214 | 0 | 216 | 0 | 213 | 0 | 213 | 0 | 210 | 0 | 213 | 0 | 211 | 2 | 213 | 0 |
| Murree | 216 | 216 | 210 | 0 | 210 | 0 | 210 | 0 | 215 | 0 | 213 | 0 | 181 | 0 | 216 | 0 | 216 | 0 | 216 | 0 |
| Pakpattan | 216 | 216 | 216 | 0 | 202 | 0 | 216 | 0 | 216 | 0 | 216 | 0 | 211 | 0 | 151 | 0 | 216 | 0 | 216 | 0 |
| Okara | 216 | 195 | 197 | 0 | 189 | 0 | 197 | 0 | 216 | 0 | 216 | 0 | 213 | 0 | 216 | 0 | 216 | 0 | 216 | 0 |
| Sahiwal | 216 | 213 | 212 | 0 | 211 | 0 | 204 | 0 | 212 | 0 | 210 | 0 | 212 | 0 | 160 | 0 | 213 | 0 | 213 | 0 |
| Mandi Bahauddin | 216 | 193 | 214 | 0 | 214 | 0 | 213 | 0 | 216 | 0 | 213 | 0 | 213 | 0 | 216 | 0 | 213 | 0 | 216 | 0 |
| Rajanpur | 216 | 187 | 172 | 0 | 166 | 0 | 172 | 0 | 187 | 0 | 184 | 0 | 187 | 0 | 187 | 0 | 187 | 0 | 187 | 0 |
| Vehari | 216 | 216 | 216 | 0 | 215 | 0 | 216 | 0 | 215 | 0 | 213 | 0 | 212 | 0 | 213 | 0 | 216 | 0 | 216 | 0 |
| Jhelum | 216 | 211 | 185 | 0 | 185 | 0 | 116 | 0 | 191 | 0 | 185 | 0 | 181 | 0 | 190 | 0 | 188 | 0 | 191 | 0 |
| Nankana Sahib | 216 | 216 | 187 | 0 | 157 | 0 | 187 | 0 | 216 | 0 | 216 | 0 | 213 | 0 | 216 | 0 | 216 | 0 | 216 | 0 |
| Jhang | 216 | 214 | 193 | 0 | 193 | 0 | 187 | 0 | 214 | 0 | 214 | 0 | 213 | 0 | 214 | 0 | 214 | 0 | 214 | 0 |
| Attok | 216 | 216 | 214 | 0 | 213 | 0 | 214 | 0 | 215 | 0 | 213 | 0 | 216 | 0 | 178 | 0 | 213 | 0 | 216 | 0 |
| Kot Addu | 216 | 216 | 216 | 0 | 216 | 0 | 215 | 0 | 216 | 0 | 210 | 0 | 216 | 0 | 167 | 0 | 216 | 0 | 216 | 0 |
| Bhakkar | 216 | 211 | 201 | 0 | 37 | 0 | 201 | 0 | 210 | 0 | 211 | 0 | 211 | 0 | 176 | 0 | 211 | 0 | 211 | 0 |
| Talagang | 216 | 210 | 185 | 0 | 185 | 0 | 183 | 1 | 210 | 0 | 200 | 0 | 201 | 0 | 209 | 0 | 207 | 0 | 210 | 0 |
| Khushab | 216 | 216 | 213 | 0 | 213 | 0 | 212 | 0 | 216 | 0 | 216 | 0 | 213 | 0 | 38 | 0 | 216 | 0 | 216 | 0 |
| Kahna Nau Hospital-LHR | 216 | 216 | 214 | 0 | 214 | 0 | 211 | 0 | 216 | 0 | 215 | 0 | 216 | 0 | 216 | 0 | 214 | 2 | 216 | 0 |
| Punjab University-LHR | 216 | 216 | 216 | 0 | 215 | 0 | 216 | 0 | 214 | 0 | 216 | 0 | 216 | 0 | 216 | 0 | 216 | 0 | 216 | 0 |
| DC Office Kasur | 216 | 199 | 160 | 0 | 88 | 0 | 159 | 0 | 98 | 0 | 146 | 0 | 198 | 0 | 170 | 0 | 102 | 0 | 109 | 0 |
| DC Office Narowal | 216 | 201 | 201 | 0 | 191 | 0 | 201 | 0 | 81 | 3 | 79 | 0 | 116 | 0 | 100 | 2 | 49 | 22 | 110 | 3 |
| DC Office Hafizabad | 216 | 216 | 210 | 0 | 206 | 0 | 203 | 0 | 60 | 0 | 94 | 0 | 214 | 0 | 151 | 0 | 41 | 0 | 111 | 0 |
| DC Office Gujrat | 216 | 211 | 196 | 0 | 195 | 0 | 196 | 0 | 86 | 0 | 36 | 0 | 208 | 0 | 149 | 0 | 14 | 0 | 96 | 0 |
| DC Office Chakwal | 216 | 0 | 211 | 0 | 211 | 0 | 211 | 0 | 69 | 0 | 42 | 0 | 210 | 0 | 176 | 0 | 15 | 0 | 92 | 0 |
| DC Office Khanewal | 216 | 0 | 211 | 0 | 185 | 0 | 211 | 0 | 121 | 0 | 78 | 0 | 210 | 0 | 154 | 0 | 85 | 0 | 136 | 0 |
| DC Office Muzaffargarh | 216 | 214 | 206 | 0 | 183 | 1 | 206 | 1 | 181 | 0 | 183 | 0 | 214 | 0 | 207 | 0 | 156 | 0 | 175 | 0 |
| DC Office Rahim Yar Khan | 216 | 215 | 215 | 0 | 201 | 0 | 215 | 0 | 99 | 0 | 128 | 0 | 198 | 0 | 165 | 0 | 100 | 0 | 110 | 1 |
| Chiniot | 216 | 9 | 5 | 0 | 5 | 0 | 5 | 0 | 8 | 0 | 8 | 0 | 8 | 0 | 8 | 0 | 8 | 0 | 8 | 0 |
| DHQ Sheikhupura | 216 | 216 | 216 | 0 | 216 | 0 | 216 | 0 | 216 | 0 | 216 | 0 | 211 | 0 | 216 | 0 | 216 | 0 | 216 | 0 |
| Mianwali | 216 | 216 | 214 | 0 | 206 | 0 | 214 | 0 | 216 | 0 | 216 | 0 | 212 | 0 | 161 | 0 | 214 | 2 | 216 | 0 |
| DC Office Layyah | 216 | 216 | 128 | 0 | 91 | 0 | 128 | 0 | 216 | 0 | 216 | 0 | 216 | 0 | 216 | 0 | 216 | 0 | 216 | 0 |
| DC Office Toba Tek Singh | 216 | 212 | 153 | 0 | 153 | 0 | 153 | 0 | 212 | 0 | 212 | 0 | 212 | 0 | 67 | 0 | 212 | 0 | 212 | 0 |
| Gymkhana Lodhran | 216 | 216 | 0 | 0 | 0 | 0 | 0 | 0 | 215 | 0 | 216 | 0 | 216 | 0 | 216 | 0 | 200 | 0 | 216 | 0 |
| DD Development Bahawalnagar | 216 | 84 | 84 | 0 | 84 | 0 | 84 | 0 | 84 | 0 | 0 | 0 | 84 | 0 | 80 | 0 | 84 | 0 | 84 | 0 |
| AC Office Choa Saidan Shah | 216 | 216 | 149 | 0 | 149 | 0 | 148 | 0 | 216 | 0 | 0 | 0 | 0 | 0 | 216 | 0 | 216 | 0 | 216 | 0 |
| AC Office Pind Dadan Khan | 216 | 182 | 80 | 0 | 80 | 0 | 49 | 0 | 182 | 0 | 178 | 1 | 182 | 0 | 182 | 0 | 182 | 0 | 182 | 0 |
| AC Office Sharaqpur | 216 | 216 | 216 | 0 | 216 | 0 | 216 | 0 | 216 | 0 | 216 | 0 | 105 | 0 | 216 | 0 | 215 | 1 | 216 | 0 |
| AC Office Taunsa | 216 | 208 | 202 | 0 | 201 | 0 | 201 | 0 | 208 | 0 | 207 | 1 | 208 | 0 | 205 | 0 | 208 | 0 | 208 | 0 |
| GHSS Kolo Tarar | 216 | 216 | 207 | 0 | 207 | 0 | 206 | 0 | 216 | 0 | 216 | 0 | 216 | 0 | 216 | 0 | 216 | 0 | 216 | 0 |
| Govt Boys College Quaidabad | 216 | 216 | 215 | 0 | 35 | 0 | 215 | 0 | 216 | 0 | 216 | 0 | 216 | 0 | 216 | 0 | 216 | 0 | 216 | 0 |
| Govt Girls College Ladhewala | 216 | 175 | 119 | 0 | 119 | 0 | 21 | 0 | 175 | 0 | 174 | 0 | 175 | 0 | 175 | 0 | 175 | 0 | 175 | 0 |
| Govt Girls College Mian Channu | 216 | 216 | 216 | 0 | 216 | 0 | 216 | 0 | 216 | 0 | 197 | 0 | 214 | 2 | 191 | 0 | 216 | 0 | 216 | 0 |
| Govt. High School Dajal | 216 | 185 | 148 | 0 | 68 | 0 | 148 | 0 | 185 | 0 | 185 | 0 | 185 | 0 | 185 | 0 | 185 | 0 | 185 | 0 |
| Gujar Khan | 216 | 216 | 216 | 0 | 216 | 0 | 216 | 0 | 216 | 0 | 216 | 0 | 213 | 0 | 216 | 0 | 216 | 0 | 216 | 0 |
| Kot Naina Shakargarh | 216 | 108 | 108 | 0 | 108 | 0 | 108 | 0 | 108 | 0 | 64 | 1 | 108 | 0 | 35 | 0 | 108 | 0 | 108 | 0 |
| MC Office Kallar Kahar | 216 | 216 | 0 | 0 | 0 | 0 | 0 | 0 | 215 | 0 | 148 | 0 | 216 | 0 | 136 | 0 | 216 | 0 | 216 | 0 |
| Maryam Nawaz Clinic DG Khan | 216 | 216 | 216 | 0 | 216 | 0 | 216 | 0 | 216 | 0 | 164 | 6 | 216 | 0 | 114 | 0 | 216 | 0 | 216 | 0 |
| Narang Mandi | 216 | 172 | 170 | 0 | 170 | 0 | 170 | 1 | 172 | 0 | 165 | 0 | 172 | 0 | 115 | 0 | 172 | 0 | 172 | 0 |
| PS Ganda Singh Wala | 216 | 216 | 216 | 0 | 215 | 0 | 216 | 0 | 216 | 0 | 195 | 8 | 216 | 0 | 216 | 0 | 216 | 0 | 216 | 0 |
| PS Harappa | 216 | 216 | 216 | 0 | 216 | 0 | 216 | 0 | 216 | 0 | 216 | 0 | 216 | 0 | 120 | 0 | 216 | 0 | 216 | 0 |
| Suthra Punjab Office Fateh Jang | 216 | 207 | 207 | 0 | 207 | 0 | 207 | 0 | 207 | 0 | 11 | 0 | 52 | 0 | 207 | 0 | 207 | 0 | 207 | 0 |
| THQ Alipur | 216 | 216 | 216 | 0 | 216 | 0 | 216 | 0 | 216 | 0 | 210 | 0 | 216 | 0 | 204 | 0 | 216 | 0 | 216 | 0 |
| THQ Haroonabad | 216 | 169 | 70 | 0 | 69 | 1 | 58 | 0 | 169 | 0 | 169 | 0 | 166 | 0 | 166 | 0 | 169 | 0 | 169 | 0 |

---

## 5. Data sources and streams

The November workstation consumes six live or archival families. Each family has a distinct role; none invents a missing reading.

### 5.1 EPA Punjab AQMS (concentrations and AQI)

| Property | Implemented contract |
|----------|----------------------|
| Public portal | `https://aqi.punjab.gov.pk` |
| Primary live endpoint | `GET /api/dashboard/current` |
| District catalogue | `GET /api/districts` |
| District fill-in | `GET /api/district-stations/<District>` (space encoded as `%20`) when a district is absent from the dashboard feed |
| User-Agent | `EMC-EPA-Punjab-AQ-dashboard/1.0` |
| Pollutants on the portal | AQI, PM2.5, PM10, NO2, SO2, CO, O3, plus station wind speed and direction |
| Pollutants **not** on the portal | NO, NOx |
| Station matching | portal `station_id` → network name through collector `PMAP` (coordinates and names matched 3 Nov 2026); `NAME_FALLBACK` maps district-stations name `"Chiniot"` → `"Chiniot"` |
| Periodic export | Hourly CSV/XLS from the AQMS logger (1–4 Nov 56 stations; 4 Nov 00:00–5 Nov 11:00; 1–9 Nov 80-station / 24 tehsil-site exports). The embedded `window.DATA` is built from these exports. Live hours **append** after `meta.exportEnd`. |
| Sign-in portal (not used) | `https://aqi.epaforecast.com/` (`/api/v1/stations`) requires a session. Ask 38 diagnosed it as gated. The collector never calls it. |

Portal rows that cannot be mapped to a network name are listed in `unmapped_stations` and dropped. Aliases seen on the portal (Barki Road → FMDRC, DHA Phase 6 → PKLI, GT Road → UET, Multan Road → LWMC) resolve through `station_id`, not through the display name.

`pollutant_flags` on a portal row nulls the named pollutant (the collector stringifies the flags and looks for `aqi`, `pm25`/`pm2.5`, `pm10`, `no2`, `so2`, `co`, `o3`).

### 5.2 Airport METAR (aviationweather.gov)

| Property | Implemented contract |
|----------|----------------------|
| Endpoint | `https://aviationweather.gov/api/data/metar?ids=<ICAO>&format=json&hours=6` |
| Collector ICAO set | `OPLA, OPFA, OPMT, OPST, OPIS, OPRN, OPRK, OPBW, OPDG, OPSR, OPMI, VIAR` |
| Embedded `DATA.airports` | Six sites: OPLA Lahore (31.522, 74.404), OPFA Faisalabad (31.365, 72.995), OPMT Multan (30.203, 71.419), OPST Sialkot (32.536, 74.364), OPIS Islamabad (33.551, 72.827), VIAR Amritsar (India) (31.707, 74.801) |
| Extra airports added by `extendData` when they appear in a live hour | OPRK Rahim Yar Khan (28.384, 70.280), OPBW Bahawalpur (29.348, 71.718), OPDG Dera Ghazi Khan (29.961, 70.486), OPSR Sargodha PAF (32.049, 72.665), OPMI Mianwali PAF (32.563, 71.571) |
| Hour assignment | Report nearest the PKT hour, gap ≤ 35 minutes |
| Wind | `wdir` degrees, `wspd` knots; `VRB` kept as `"VRB"`; `CALM` when speed and direction are both 0/null |
| Speed conversion in the client | knots × 0.514 → m/s; meteorological components `u = −ms·sin(dir)`, `v = −ms·cos(dir)` |
| Visibility | numeric `visib` treated as statute miles × 1609.34; otherwise a 4-digit metres group in `rawOb` |
| Weather codes | `FU` smoke, `HZ` haze, `BR` mist, `FG` fog, `DU` dust, `RA` rain, `TS` thunderstorm |
| Hourly table fallback | If METAR `u,v` is missing, the district AQMS vector (`AP_D` map) is used; those cells render italic grey with `(AQMS)`. VIAR falls back to Lahore AQMS. OPIS/OPRN fall back to Rawalpindi. |

Ask 24 and ask 35 required airport winds as a meteorological cross-check and as map markers. The workstation plots them as ✈ triangles with an accent-coloured shaft and arrowhead.

### 5.3 WMO SYNOP (Ogimet)

| Property | Implemented contract |
|----------|----------------------|
| Endpoint | `https://www.ogimet.com/cgi-bin/getsynop?block={415\|416\|417}&begin=YYYYMMDDHH00&end=YYYYMMDDHH59` |
| Window | Last 7 hours UTC |
| Kept stations | `41640` Lahore PBO, `41641` Lahore Airport, `41571` Islamabad, `41598` Jhelum, `41600` Sialkot, `41675` Multan, `41700` Bahawalpur |
| Decode (`synop_wind`) | `AAXX` group; `dd` × 10 degrees (`dd==0` → 0; `dd==99` or `dd>36` → null); `ff` knots if indicator `iw` is `3` or `4` (× 0.5144), else m/s if `iw` is `0` or `1`; `ff==99` takes the next `00fff` group |
| Client | WMO rows appear in the hourly wind table when a live hour carries them. `extendData` adds `W<id>` airport-like rows with `wmo:true`. Calm if speed < 0.25 m/s. |

Other WMO identifiers found in the blocks are listed in `other_wmo_ids` and not stored.

### 5.4 ECMWF IFS via Open-Meteo

Two products share the ECMWF IFS 0.25° model through Open-Meteo.

**Collector (district 10 m wind, live hours)**

```
https://api.open-meteo.com/v1/forecast
  ?latitude=<41 centroids>
  &longitude=<41 centroids>
  &hourly=wind_speed_10m,wind_direction_10m
  &models=ecmwf_ifs025
  &wind_speed_unit=ms
  &timezone=Asia/Karachi
  &past_days=1
  &forecast_days=1
```

Centroids are the `DIST` table in §4.5. One request returns 41 points. Hour-document field `ecm[district] = [ws m/s, wd deg]`.

**Embedded regional grid (`DATA.ecm`)**

| Field | Shape |
|-------|--------|
| `la` | 15 values, 27.5°N … 34.5°N step 0.5° |
| `lo` | 15 values, 69.0°E … 76.0°E step 0.5° |
| `u10`, `v10`, `u925`, `v925` | 216 hours × 225 grid points (row-major `y*15+x`) |
| `xb10`, `xb925` | 216 hours × `[mean_cross_border_ms, spread]`; positive = India → Pakistan |

The regional particle field outside Punjab bilinear-interpolates `u{lev}/v{lev}` at the selected `#ecmLev` (`10` or `925`). Method notes state 925 hPa is the level where smoke travels furthest.

`meta.ecm_ratio = 0.22686365412534343` is the period ECMWF-to-AQMS wind-speed scale. Live METAR and ECMWF district winds are multiplied by `KR = meta.ecm_ratio || 0.34` before they fill a monitored district. Unmonitored districts that fall through to ECMWF take the **unscaled** model wind. `DATA.wscale` stores 216 `[a,b]` pairs in the range about 0.06–0.58; `#mainsrc` does not read `wscale` (the ratio is already baked into `meta.ecm_ratio` and into the embedded `DATA.wind`).

### 5.5 NASA FIRMS (thermal anomalies / crop fires)

FIRMS is **not** in the hourly collector. It is a report and `#xbAll` product.

| Property | Implemented contract |
|----------|----------------------|
| Product | VIIRS NOAA-20 and NOAA-21, South Asia 7-day files |
| Period in the delivered dashboard | 2–9 Nov 2026 (9 Nov partial) |
| Regions tabulated | Punjab (PK) 6,703; Punjab (IN) 3,239; Rajasthan 2,834; Sindh 409; Haryana 363; Khyber Pakhtunkhwa 248; Himachal Pradesh 128; Jammu & Kashmir (IN) 59; Balochistan 52; Azad Kashmir 9; Islamabad 0 |
| Note | Rajasthan detections lie mostly far from Punjab (1,507 south of 27°N, including Barmer gas-flare candidates; a Bikaner cluster ~120 km from the border; only 276 north of 28.5°N) |
| Role | Situation-report fire charts; `#xbAll` fire table; map dots on the all-sides figure (fixed image) |

### 5.6 IQAir (cities outside Punjab)

IQAir is **not** in the hourly collector. City pages were read on 9 Nov about 23:00 PKT.

| Property | Implemented contract |
|----------|----------------------|
| Scale | US AQI (US EPA), **not** EPA Punjab AQI. Compare IQAir cities with each other only. |
| Table | 32 cities in `#xbAll` and in the 9 Nov situation report |
| Columns | City, Region, US AQI, PM2.5, Source, 10 / 11 Nov |
| Station vs estimate | Cities with no IQAir station are marked “IQAir estimate (no station)” and drawn as squares on the all-sides map |
| Pakistani caveat | IQAir Pakistani readings include low-cost private sensors (example: Peshawar 471) |

Ask 31 named IQAir as a live source; the implemented November product uses it as a **snapshot table** around Punjab, not as an hourly AQMS substitute.

### 5.7 CAMS (all-sides transport)

CAMS global PM2.5 (Open-Meteo) is combined with ECMWF 10 m wind at 117 points about 25 km apart along Punjab’s whole boundary, 1–12 Nov (10–12 Nov forecast). The product is a **rank index**, not a mass budget. Method and `#xbAll` hint both state that CAMS reads lower than AQMS, so side-to-side comparison holds better than absolute values.

Inflow shares on 1–9 Nov: India 56% (Rajasthan 29%, Indian Punjab 22%, Jammu 5%); Khyber Pakhtunkhwa + Islamabad + AJK 28%; Balochistan + Sindh 17%. Rajasthan is the largest net source (into Bahawalnagar–Bahawalpur). Over nine days more air left toward Indian Punjab than arrived; on 8–9 Nov that reversed (inflow more than doubled, ~3× outflow on that stretch). KP is a net source across DI Khan–Bhakkar–Layyah. Punjab is a net exporter to Sindh, Balochistan and AJK.

### 5.8 NOAA GFS mixing height (Meteoblue requested)

Ask 52 requested Meteoblue mixing-layer height. The Meteoblue site shows images only; numerical export needs a paid licence. The implemented report section uses:

- NOAA GFS mixing height via Open-Meteo
- ECMWF IFS wind, humidity and sea-level pressure via Open-Meteo
- Retrieved 10 Nov about 01:45 PKT
- All 41 districts, hourly, 10 November

If EMC later holds a Meteoblue licence, that export replaces the GFS column; the report says so.

### 5.9 Source status strings

Every collector run records `src = {portal, metar, wmo, ecmwf}` as human status (`ok N …` or `blocked/unreachable: …` or a parse error). The live line under the title prints `portal ✓/✗ · METAR ✓/✗ · WMO ✓/✗ · ECMWF ✓/✗`. No value is invented when a source fails: that field is simply omitted from the hour document.

---

## 6. Collector contract (`original System/collector/collector.py`)

The collector is a stdlib Python 3 CLI. It does not open a browser, does not read the user’s PC, and is invoked with isolated mode:

```
python3 -I collector.py fetch OUT
python3 -I collector.py build OUT EXISTING
```

`fetch` writes `OUT/raw.json` and prints JSON `{status, hours, doc_ids, t_values}`.  
`build` reads `OUT/raw.json`, merges with `EXISTING/<id>.json` when present, writes `OUT/docs/<id>.json` and `OUT/batch.json`, and prints `{status, writes, hours, unmapped_stations, flagged_values, other_wmo_ids, top_aqi_latest}`.

HTTP is `curl -sS -L --max-time TIMEOUT -A UA -w \n%{http_code}`. Default timeout 40 s (ECMWF 60 s). `get()` returns `(body, '')` on HTTP 200, else `(None, error note)`.

### 6.1 `fetch(out)`

1. Timestamp `fetched` in UTC ISO seconds.
2. Portal dashboard current → `raw.stations` (dicts with `station_name`). If any districts are missing, pull `/api/districts` then `/api/district-stations/<name>` and tag those rows `_extra: true`.
3. METAR last 6 h for the 12 ICAO codes.
4. SYNOP blocks 415, 416, 417; keep lines containing `AAXX`.
5. ECMWF 10 m at 41 `DIST` centroids (one Open-Meteo call).
6. Hours to write: each PKT hour stamped by a portal station in the last 6 h. If the portal returned no stations, still record the **last completed PKT hour** so the wind table keeps going.
7. Dump `raw.json`. Print doc ids `hYYYYMMDDHH`.

### 6.2 `build(out, existing)`

For each hour in `raw.hours`, assemble:

| Field | Content |
|-------|---------|
| `t` | `"YYYY-MM-DD HH:00"` PKT, hour as stamped by the portal |
| `st` | `{network name: [AQI, PM2.5, PM10, NO2, SO2, CO, O3, ws m/s, wd deg]}` rounded to 3 decimals; nulls preserved |
| `ap` | `{ICAO: [dir deg \| "CALM" \| "VRB", kt, vis m, temp C, weather, gust kt, obs UTC]}` |
| `wmo` | `{WMO id: [dir deg \| null, m/s, obs UTC]}` |
| `ecm` | `{district: [ws m/s, wd deg]}` |
| `src` | the four status strings from this fetch |
| `upd` | `raw.fetched` |

Merge rule: `{**old.field, **new.field}` per `st`/`ap`/`wmo`/`ecm`. Empty documents (all four maps empty) are skipped. Existing ArtifactData versions are passed through as `if_version` on the batch op.

`batch.json` is a list of `{op:"set", collection:"hours", doc_id, file_path, if_version?}`.

**Hour-document identifier:** `h` + `t` with separators stripped, first 10 digits of the compact stamp, e.g. `2026-11-09 23:00` → `h2026110923`. Collection name: `hours`.

**Invariant (collector docstring):** No values are invented: anything that cannot be fetched is left out and its status says why. Missing fetches stay missing; `src` records the reason.

### 6.3 Functions and helpers

| Name | Role |
|------|------|
| `get(url, timeout=40)` | curl GET through the workspace proxy |
| `fnum(x)` | float or None (NaN → None) |
| `parse_ts(s)` | ISO timestamp; naive → UTC |
| `fetch(out)` | §6.1 |
| `synop_wind(line)` | Ogimet CSV line → `(id, obs UTC iso, dir\|None, m/s)` or None |
| `build(out, existing)` | §6.2 |

Constants: `PORTAL`, `PKT` (UTC+5), `UA`, `PMAP`, `NAME_FALLBACK`, `DIST`, `ICAO`, `WMO`, `POLF = ['aqi','pm25','pm10','no2','so2','co','o3']`.

---

## 7. Embedded `window.DATA` schema

The November HTML assigns `window.DATA = {…}` on one line (~9.08 MB). This specification names keys, types, and shapes. Hourly observation arrays are **not** inlined.

### 7.1 Top-level keys

| Key | Type | Role |
|-----|------|------|
| `meta` | object | Period, counts, calm, ECMWF ratio, optional `live` after extend |
| `hours` | string[216] | `"YYYY-MM-DD HH:00"` PKT, 2026-11-01 00:00 … 2026-11-09 23:00 |
| `districts` | `{name: {lat, lon, stations[], est}}` | 41 districts; `est=false` in this snapshot |
| `wind` | `{district: [u, v]}` per hour | Meteorological m/s; null components allowed |
| `stations` | `{name, d, lat, lon, mobile}[79]` | Plotting positions |
| `adm` | `{district: {label:[lon,lat], polys}}` | 41-district shapefile rings |
| `tbgeo` | object | Border geometry, samples, per-district India sectors |
| `pol` | `{AQI, PM10, PM2.5, NO2, SO2, CO, O3, NO, NOX}` | Per-pollutant cube |
| `qa` | `{station: {n, wind_valid, <pol>, <pol>_spk, …}}` | Post-QC finite-hour counts |
| `network` | `{name, district, type, phase, lat, lon}[56]` | Shapefile catalogue (51 Fixed, 5 Mobile) |
| `coordsrc` | `{station: string}` | How each of the 79 plot positions was obtained |
| `skipped` | `{ "OneNetwork Station 25": "location not known" }` | Dropped site |
| `airports` | `{id, name, lat, lon, u[], v[], obs[]}[6]` | METAR series, 216 hours |
| `apLatest` | list | Latest METAR captions; empty `[]` in the delivered snapshot |
| `wsrc` | `{district: "aqms"\|"metar"\|"ecmwf"\|"idw"}` per hour | Wind provenance. Counts in this snapshot: aqms 8317, ecmwf 537, metar 2 |
| `wscale` | `[number, number][216]` | Hourly ECMWF↔AQMS scale pairs (~0.06–0.58). Unused by `#mainsrc` |
| `ecm` | object | Regional u/v grids and India–Pakistan cross-border series |

`meta` in the delivered file:

```
start: "2026-11-01 00:00"
end:   "2026-11-09 23:00"
nstations: 79
ndistricts: 41
nmon: 41
unmon: []
calm: 0.5
ecm_ratio: 0.22686365412534343
```

After a successful live extend, `meta.exportEnd` is set (defaults to `meta.end`), `meta.end` advances, and `meta.live = {from, n, last, upd, src, stations, spikes}`.

### 7.2 Per-pollutant object `DATA.pol[P]`

| Field | Meaning |
|-------|---------|
| `scale` | `"aqi"` (AQI) or `"conc"` |
| `unit` | `index`, `µg/m³`, or `mg/m³` (CO) |
| `ref` | PEQS / category threshold used for “hours over” (AQI 200, PM10 150, PM2.5 35, NO2 80, SO2 120, CO 5, O3 130, NO 40, NOX `null`) |
| `refavg` | `"AQI"`, `"24-h"`, `"8-h"`, `"1-h"`, or `""` for NOX |
| `frames[h]` | `{ c: {district: value}, l: [[src, rcv, flux], …] }` |
| `cpf[district]` | `{ thr, calm, sectors[16] }` with `{n, k, cpf}` per 22.5° sector; `cpf` may be `null` when `n` is small |
| `links` | Top 60 pathways `{src, rcv, km, flux, hours, cpf, score}` sorted by score |
| `net` | Period source(+) / receptor(−) score per district |
| `tb` | Per-district India-side enrichment (`valid`, `enrich`, `n_india`, …) |
| `series[h]` | `[inflow, outflow]` transboundary index for the belt |
| `tbh[district]` | Hourly signed transboundary index |
| `wagha` | `{c_india, c_other}` at Wagha Border (small object; used by Key findings) |
| `daily[district]` | `{mean, n, max, over}` — `mean` is null unless ≥ 75% of active hours are valid |
| `links_h` | Hourly flux per `src|rcv` key (feeds the Inter-district table, top 20 by period total) |
| `stations[name]` | Length-216 series (nulls for missing/QC) |

Period-mean rule (export pipeline and `extendData`):

```
NA = count of hours in which any monitored district has a value
mean is kept iff n_valid >= max(1, round(0.75 * NA))
```

That is why Chiniot (`n=5`), Lodhran (`n=0` for AQI), Layyah and Toba Tek Singh can show `daily.mean = null` even though they have assigned stations.

### 7.3 `tbgeo`

| Field | Content |
|-------|---------|
| `districts[name]` | `{border_km, india_sectors[], est}` |
| `samples` | 39 `[lon, lat, nx, ny]` chevron anchors (unit inward normal) |
| `border` | 440 `[lon, lat]` vertices of the India–Pakistan line (first 74.4035, 32.7747; last 70.1821, 27.8731) |

Border-belt for the signed transboundary index: districts with `border_km <= 120`. In this snapshot that is Bahawalnagar (15), Kasur (5), Lahore (19), Narowal (19), Sialkot (17), Sheikhupura (27), Gujrat (37), Pakpattan (43), Rahim Yar Khan (44), Gujranwala (55), Okara (61), Wazirabad (66), Nankana Sahib (80), Sahiwal (87), Mandi Bahauddin (90), Bahawalpur (94), Hafizabad (96), Vehari (100), Lodhran (113). Chiniot (142), Faisalabad (132), Khanewal (130), Rajanpur (142), Toba Tek Singh (143) are recorded in `tbgeo` but fall outside the 120 km belt.

`india_sectors` are 0…15 CPF sector indices that face Indian Punjab / Haryana / Rajasthan from that centroid.

### 7.4 Network phases

`DATA.network` (56 shapefile sites): type `Fixed` (51) or `Mobile` (5); phase `Operational` (30), `Air-Safe 18` (18), or `Air-Safe 08` (8). The five Lahore mobiles (Gulberg III, Lathe Pur, Wahga Border, Egerton Road, BHU Jandiala Kalasan) are Operational. Air-Safe 08 covers the eight DC-office sites Gujrat, Hafizabad, Chakwal, Khanewal, RY Khan, Narowal, Muzaffargarh, Kasur.

### 7.5 Airport series occupancy (embedded 216 hours)

| ICAO | Non-null `u,v` |
|------|----------------|
| OPLA | 179 |
| OPFA | 216 |
| OPMT | 216 |
| OPST | 216 |
| OPIS | 216 |
| VIAR | 159 `u,v` (216 `obs` slots; calm/missing wind still stores an obs) |

---

## 8. Quality control

QC is applied in the **export pipeline** that builds `window.DATA`, and again in **`extendData`** for live hours. The Method block is the operator-facing statement of the same rules.

### 8.1 Reject / null rules (concentrations)

| Rule | Implementation |
|------|----------------|
| Non-positive | `v == null \|\| !(v > 0)` → null (zeros and negatives dropped) |
| Isolated spike | 7-hour window `full[i-3 … i+3]`; median of finite values in that window (need ≥ 3); drop if `v > 4 × median` **and** `v > 3 × ref` (`ref` is 200 for AQI, else the PEQS/ref in §7.2, else 100) |
| Logger hold | Three consecutive equal values (`full[i-2] === full[i-1] === v`); **not applied to AQI** |
| Portal flags | `pollutant_flags` nulls the named species |
| Flagged / export flags | Method: “Flagged values, zeros, isolated spikes and values repeated three hours running are removed.” |

`DATA.qa[station].<pol>_spk` counts spikes removed per species. Examples in this snapshot: DC Office Narowal NO 22 spikes; PS Ganda Singh Wala SO2 8; LWMC-LHR NO 6; Maryam Nawaz Clinic DG Khan SO2 6.

### 8.2 Wind QC

| Rule | Implementation |
|------|----------------|
| Wazirabad vane | ~140° off; `NOWIND = {'Wazirabad'}`. `qa.Wazirabad.wind_valid = 0`. Concentration is kept. |
| Speed range | `ws < 0` or `ws > 30` discarded (wind speeds above 30 m/s). DC Office Chakwal writes direction in the speed field; DC Office Khanewal reports 99.9. Both have `wind_valid = 0`. |
| Direction range | `wd < 0` or `wd > 360` discarded |
| Calm | Speed < 0.5 m/s (airport definition of calm, ~1 knot). Calms are excluded from CPF sectors and yield null transport flux. |
| Chiniot | Almost no valid hours (`wind_valid = 9`, AQI `n = 5`) |

### 8.3 Coordinate QC

| Case | Action |
|------|--------|
| Shapefile Lat/Lon wrong | Use point geometry: Gulberg III (was 31.22, true ~31.50), DC Office Sialkot (had duplicated Gujranwala), Wazirabad (was 28.77, 77.51 in India) |
| Not in station shapefile | Approximate town centre: Sahiwal, Rajanpur, Talagang, Khushab, plus 24 tehsil-level sites |
| Unknown location | `OneNetwork Station 25` skipped |
| EMC-confirmed Lahore | Eleven Google-Maps positions in §4.4 (`coordsrc = "EMC confirmed"`) |

### 8.4 Valid-PM AQI rule

A station’s AQI is used only in hours with a valid PM2.5 **or** PM10 reading. Ask 44 applied this after 3 Nov was restored, so Layyah and Lodhran no longer show falsely clean AQI. Lodhran AQI `qa.n = 0` in this snapshot; Gymkhana Lodhran still reports NO2/SO2/CO/O3/NO/NOx. MC Office Kallar Kahar likewise has AQI `n = 0` (no valid PM).

The live portal already publishes an AQI; `extendData` does not recompute AQI from PM. Month-end verified export replaces provisional portal AQI.

### 8.5 District aggregation after QC

- **Concentration / AQI:** arithmetic mean of that district’s stations that still have a finite value in the hour. No stations → null for monitored districts; estimated districts use IDW of monitored neighbours (§9.2).
- **Wind:** vector mean of valid station `(u, v)`. Fallback chain for a **monitored** district: AQMS vector mean → district airport METAR × `ecm_ratio` → ECMWF 10 m × `ecm_ratio`. For an **estimated** district: IDW of monitored winds → unscaled ECMWF.
- District–airport map used by `extendData`: Lahore OPLA, Faisalabad OPFA, Multan OPMT, Sialkot OPST, Rawalpindi OPIS, Rahim Yar Khan OPRK, Bahawalpur OPBW, DG Khan OPDG, Sargodha OPSR, Mianwali OPMI.

### 8.6 Rounding

| Species | Rounding |
|---------|----------|
| CO | 2 decimal places |
| Other concentrations / AQI / flux | 1 decimal place (`extendData` `r()`) |
| Wind components stored on districts | 3 decimal places |
| Airport `u,v` | 2 decimal places |

### 8.7 Lahore study QC (24 Oct product, still specified)

Ask 17 required exclusion of doubtful Lahore data and a gust-front analysis. Frozen RH/temperature sensors, implausible PM2.5/PM10 ratios, and held logger values were dropped. The 5-minute gust-front timing is a Lahore-study product (`lahore_air_quality.html`); the November workstation keeps hourly wind and the (hidden) 13-station Lahore panel.

---

## 9. Mathematics

All distances use a spherical Earth, radius 6371 km.

```
geo(A, B) → [km, bearing_deg]
  haversine great-circle km
  initial bearing = atan2( sinΔλ·cosφ2, cosφ1·sinφ2 − sinφ1·cosφ2·cosΔλ )
  bearing in [0, 360)
```

Meteorological wind (direction **from** which the air blows):

```
u = −ws · sin(wd · π/180)
v = −ws · cos(wd · π/180)
speed = hypot(u, v)
to_direction = (atan2(u, v) · 180/π + 360) mod 360
```

### 9.1 District hourly mean

For each pollutant `P` and hour `h`:

```
c[d] = mean{ station series of d that are finite at h }   if d is monitored
c[d] = IDW(d, {monitored c})                               if d.est and any monitored value exists
c[d] = null                                                otherwise
```

This is `PD.frames[h].c[d]`. The map, ranking bars, KPIs, mini-maps, and hourly concentration table all read this field.

### 9.2 Unmonitored-district IDW (ask 8)

Estimated districts are **receptors only** in transport (they never appear as `src` in `pairs`, because `pairs` iterate `a ∈ MON`). They render with a `~` prefix, italic type, and a hatch overlay in Districts mode.

```
idw(target, vals) =
  Σ_d  w_d · vals[d]  /  Σ_d w_d
  w_d = 1 / max( geo(centroid(target), centroid(d))_km , 5 )²
```

In the 1–9 Nov snapshot every district has `est: false`, so this branch is idle until a live hour or a future export marks a district estimated. The engine, hatch pattern, list hint, and table separator row remain.

### 9.3 Wind-weighted station continuum (ask 27)

Surface mode (`MODE = 'surface'`, default) paints a 5 px grid clipped to the Punjab path.

```
stationPts(Q, fpos):
  for each station with a finite interpolated value v:
    take that hour’s district wind (u, v_north)
    emit {x, y, v, u, w: v_north}

fieldAt(x, y, pts):
  for each station p:
    d² = dx² + dy² ; d = √d²
    w = 1 / (d² + 16)
    if p has wind and d > 2 and speed > 0.5:
      c = (dx·u − dy·v_north) / (d · speed)     # downwind stretch
      w *= max(0.3, 1 + 0.7 · c · min(1, speed/1.5))
    accumulate w, w·v
  return [vs/ws, dmin]

alpha by distance from nearest station:
  km = dmin · (111 / S)          # S = canvas metres per degree of latitude
  α = 235                         if km < 45
    = 95                          if km > 140
    = 235 − 140·(km−45)/95        otherwise
```

The field is cached under key `pol|round(fpos*12)|W` (main map) or `round(fpos*4)|miniWidth` (mini-maps, cell 4). `#lgMode` reads “Surface = continuous field from stations, wind-weighted; paler = far from any station”.

A retained helper `drawSurface` interpolates from **district centroids** with `w = 1/(q·√q)`, `q = dx²+dy²+0.25`. The live Surface path uses `drawField` / `renderField` (stations + wind stretch). Mini-maps share `renderField`.

### 9.4 District wind field used by particles

Inside Punjab, particles sample `windAt(x,y,st)`: inverse-distance of monitored district winds **and** airport `(u,v)` with `w = 1/(dx²+dy²+400)`. Advection:

```
k = 1.4 · S / 100
x ← x + u·k
y ← y − v·k          # canvas y grows south
trail length ≤ 8
respawn if age > 120 or the point leaves Punjab
count = min(700, W·H / 650)
```

Outside Punjab (toggle `#tReg`, default on), `rStep` advects a second set of particles on the ECMWF grid:

```
k = 2.2 · S / 100
count = min(600, W·H / 900)
even-odd clip: canvas rectangle minus Punjab
bilinear ecmAt(lon, lat, hour) on u{10|925}, v{10|925}
```

### 9.5 Inter-district transport index (asks 1, 5, 19, 42)

Pairs: every monitored source `a` to every district `b ≠ a` with `km ≤ 180`.

```
CALM = 0.5 m/s
MAXD = 180 km
CONE = 35°
LS   = 100 km

flux(c, u, v, km, brg) =
  null                           if c is null or u is null or hypot(u,v) < CALM
  null                           if |Δ| > 35°
  c · w · cos(Δ) · exp(−km / 100) otherwise

Δ = smallest angle between wind-to direction and the bearing of b from a
```

`PD.frames[h].l` stores `[src, rcv, rounded_flux]`. The map draws the strongest 12 links of the current hour that are at least 8% of the period maximum (`MAXF`). Quadratic Bézier with a coloured shaft, a dashed overlay, and a filled arrowhead. **Suppressed when the selected pollutant is AQI** (`isAQI(PD)`), because AQI is an index. `#tLinks` defaults to checked (ask 19). Mini-maps draw at most 8 links.

Period pathway score:

```
flux_period = total_flux / NA
score       = flux_period · (cpf_of_receptor_in_back-bearing_sector, or 0.25 if CPF is null)
net[src]   += score
net[rcv]   -= score
links kept = top 60 by score
```

### 9.6 Transboundary index (asks 3, 49)

**Chevron layer (map):** for each of 39 `tbgeo.samples` `[lon, lat, nx, ny]`, take `windAt` at that point. Cross-border component `c = u·nx + v·ny`. Skip if `|c| < 0.25`. Sign of `c` chooses inflow (`--inflow` crimson) or outflow (`--outflow` teal). Chevrons march with phase `ph += 0.012` per frame.

**Belt index (tables, findings, series):**

```
BELT = districts with border_km ≤ 120

tbVal(d, c, u, v) =
  0                                              if calm
  val = c · w · exp(−border_km / 100)
  +val if the FROM-sector is in india_sectors     # India → PK
  −val if the opposite sector (k+8) mod 16 is     # PK → India
  0    otherwise                                  # along-border

FROM-sector k = floor( ((from_dir + 11.25) mod 360) / 22.5 )
from_dir = atan2(−u, −v)
```

Estimated belt members are excluded from the hourly total. `PD.series[h] = [sum of positive tbVal, sum of |negative tbVal|]`. The Transboundary tab colours + red / − teal, lists In / Out / Net, and appends two ECMWF rows (`xbRow('925')`, `xbRow('10')`) with “+ India → Pakistan” and the share of hours with inflow > 0.2 m/s.

**All-sides product (ask 49, `#xbAll`):** 117 boundary points × ECMWF 10 m × CAMS PM2.5, 1–12 Nov. Charts are **fixed images** from the 9–10 Nov build; they do not advance with the scrubber. Findings quote: India 56% of inflow; Rajasthan largest net source; 8–9 Nov doubling from India; KP net source; Punjab net exporter to Sindh, Balochistan, AJK.

No Indian AQMS monitors are in `window.DATA`. The belt index shows **when** cross-border air arrived, not how much mass it carried.

### 9.7 CPF — Conditional Probability Function (ask 1)

16 sectors of 22.5°. Calm hours (`< 0.5 m/s`) excluded. Threshold = district 75th percentile of the pollutant.

```
sector k = floor( ((from_dir + 11.25) mod 360) / 22.5 )     # k = 0…15
cpf[k] = k_exceedances / n_hours_in_sector
cpf[k] = null when n is too small to support a rate
```

Attock AQI sample in this snapshot: `thr = 166`, `calm = 0.898` (89.8% calm), most sectors `cpf = null` with `n` of 0–7; sector 9 has `n=6, k=2, cpf=0.333`. The rose draws a muted open arc when `cpf` is null, a filled petal otherwise, coloured by `col(thr · (0.6 + 1.4·cpf))`. Rings at 0.2, 0.4, 0.6, 0.8. A dashed circle marks 0.25. Estimated districts show “No station in this export”.

The same P75 threshold is the Method’s threshold for transport/cross-border discussion; the flux formula itself uses concentration, not the P75 cut.

### 9.8 Colour scales — EPA Punjab AQI and PEPC (asks 30, 36)

Seven EPA Punjab categories, RGB from the Daily AQI Report legend. `aqiCat` uses `Math.round(v)` against the upper bound.

| Band | AQI range | Name | RGB | Hex |
|------|-----------|------|-----|-----|
| 0 | 0–50 | Good | 0, 176, 80 | `#00B050` |
| 1 | 51–100 | Satisfactory | 146, 208, 80 | `#92D050` |
| 2 | 101–150 | Moderate | 255, 255, 0 | `#FFFF00` |
| 3 | 151–200 | Unhealthy for Sensitive Groups | 237, 125, 49 | `#ED7D31` |
| 4 | 201–300 | Unhealthy | 255, 0, 0 | `#FF0000` |
| 5 | 301–400 | Very Unhealthy | 112, 48, 160 | `#7030A0` |
| 6 | 401+ | Hazardous | 192, 0, 0 | `#C00000` |

PEPC-approved **upper bounds** of the first six categories (`BP` in `#mainsrc`). Category 6 is anything above the last bound. Colours are the same seven RGB triples as AQI (`AQI_B[bpIdx(v)]`).

| Pollutant | Breakpoints (upper of Good … Very Unhealthy) | Unit |
|-----------|-----------------------------------------------|------|
| PM10 | 75, 150, 250, 350, 450, 550 | µg/m³ |
| PM2.5 | 15, 35, 70, 140, 250, 350 | µg/m³ |
| SO2 | 60, 120, 220, 320, 800, 1600 | µg/m³ |
| NO2 | 40, 80, 130, 180, 380, 580 | µg/m³ |
| O3 | 65, 130, 195, 260, 450, 550 | µg/m³ |
| CO | 2.5, 5, 7.5, 10, 25, 40 | mg/m³ |

NO and NOx have no PEPC table. They use a **continuous PEQS-multiple gradient**:

```
MULT = [0, 0.5, 1, 1.5, 2.5, 4, 6]
RGB  = [58,165,93], [156,204,58], [242,194,48], [240,122,38], [214,52,44], [142,59,143], [90,21,48]
ref  = Q.ref || 100     # NO uses 40; NOX uses 100
```

Linear interpolation between adjacent MULT stops. Null values paint `rgba(128,128,128,α)`.

Legend titles:

- AQI: “AQI · EPA Punjab categories”, ticks 0, 51, 101, 151, 201, 301, 401+
- PEPC species: “{name} {unit} · PEPC breakpoints (Good → Hazardous)”
- NO/NOx: continuous bar, ticks at 0, 1, 2.5, 4, 6 × ref

KPI “Districts above PEQS” becomes “Districts Unhealthy or worse (AQI > 200)” when AQI is selected. Heat-table text is white on AQI > 200, on PEPC category ≥ 4, or on values > 2.5 × ref.

### 9.9 Time interpolation

The scrubber is continuous. `at(fpos)` linearly interpolates district concentration and wind between `floor(fpos)` and `ceil(fpos)`; a null side takes the other. Particles and chevrons use the interpolated field. Hourly tables and KPIs use `round(fpos)`.

Playback:

```
playing = true                 # default; Pause is the visible button label
speed ∈ {0.35 Slow, 0.8 Normal (selected), 1.6 Fast}
fpos += dt · speed             # dt capped at 0.1 s
if fpos > N-1: fpos = 0        # wrap
```

If `meta.live` exists at bootstrap, `fpos` starts at `max(0, N-24)` (last day).

### 9.10 Map projection

```
B = { lo0: 69.1, lo1: 75.75, la0: 27.55, la1: 34.3 }
KX = cos(31°)
P(lon, lat) = [ (lon − lo0) · KX · S, (la1 − lat) · S ]
```

`S` fills the map box; height is capped at `max(440, innerHeight − 110)` when `innerWidth > 980`. Device pixel ratio is clamped at 2. Hit-testing uses an offscreen canvas `isPointInPath` against `admPaths`. Neighbour rings: `GEO` (Sind, Baluchistan, Azad Kashmir, Northern Areas, N.W.F.P., F.A.T.A., F.C.T., Punjab) and `IND` (Himachal Pradesh, Delhi, Uttar Pradesh, Haryana, Punjab, Chandigarh, Rajasthan, Jammu and Kashmir, Gujarat, Ladakh, Uttarakhand). “INDIA” is drawn at (75.0, 30.3), “PAKISTAN” at (69.35, 31.9). The international border is a red dashed stroke `[8,4]` of `tbgeo.border`.

Lahore inset: `LB = {lo0:74.08, lo1:74.64, la0:31.34, la1:31.70}`.

---

## 10. Live extension (`window.extendData` + bootstrap)

### 10.1 `window.extendData(DATA, docs)`

Comment in the file: *“Live extension: appends hourly EPA Punjab portal snapshots (db collection `hours`) to the 1–2 Nov AQMS export, applying the same QC, district averaging, IDW estimates, transport and cross-border calculations as the export pipeline.”* The delivered snapshot already contains 1–9 Nov; live hours still append strictly after `meta.exportEnd`.

Pipeline:

1. Require `docs[i].t` matching `^\d{4}-\d\d-\d\d \d\d:00$` and `t > meta.exportEnd`. Sort ascending.
2. Pad a **continuous** hourly sequence from the last known hour to the newest snapshot (gaps stay empty frames).
3. Airports: extend `u,v,obs`; add `AP_EXTRA` / WMO rows when those ids appear.
4. Station QC per pollutant (`PI` index into the 9-tuple: AQI=0, PM2.5=1, PM10=2, NO2=3, SO2=4, CO=5, O3=6). NO and NOx have no portal index, so new hours stay null for those two.
5. District winds with the fallback chain in §8.5. `DATA.wsrc` records `aqms` / `metar` / `ecmwf` / `idw`.
6. Rebuild `frames`, `daily`, `links` (top 60), `net`, `links_h`, `series`, `tbh` over the **whole** record.
7. Set `meta.end`, `meta.live`, `apLatest`. Return the number of new hours (0 if none).

Haversine, flux, belt, and CPF-scoring formulas are the same constants as §9 (`CALM=meta.calm||0.5`, `MAXD=180`, `CONE=35`, `LS=100`).

### 10.2 Live bootstrap (last script)

`#mainsrc` is stored as `type="text/plain"`. A 9 second timer starts the engine if live hours never arrive.

```
window.__liveState messages:
  timeout:  "Live hours could not be loaded in this view; showing the AQMS exports."
  no db:    "Live hours are not available in this view; showing the AQMS exports."
  empty:    "Live collector: no hourly portal snapshots stored yet."
  onSnapshot error: "Live hours could not be loaded; showing the AQMS exports."

db = await claude.use('db')
db.collection('hours').limit(1000).onSnapshot(...)
  first snapshot: apply extendData, then inject #mainsrc
  later snapshots: extendData then window.__liveRefresh()
```

`__liveRefresh` rebuilds `N`, scrubber max, mini-map means, subline, live line, airport hourly table, and calls `setPol(pol)`.

Standalone download (ask 55) **does not** attach this collector. Its live line states that the copy will not pick up new hours.

### 10.3 Live line copy

When `meta.live` is present:

```
Live: latest portal hour {day} {HH}:00 PKT, {n} stations · {n} live hours stored · sources portal ✓/✗ · METAR ✓/✗ · WMO ✓/✗ · ECMWF ✓/✗
```

Method notes: live hours are **provisional** and are replaced by the verified AQMS export at month end.
---

## 11. User interface

The delivered HTML is a single-page “field-instrument console”: pollutant switch on top, animated map with a readout column, comparison grid, hourly tables, all-sides section, findings and Method. Layout CSS comment: *“Layout: field-instrument console. Pollutant switch on top, clean animated map with a readout column, Lahore network panel and hourly tables below.”*

### 11.1 Document chrome

| Item | Implemented value |
|------|-------------------|
| `<title>` | Punjab Air Quality November 2026 (Copy) |
| `<h1>` | Punjab Air Quality, November 2026 |
| Eyebrow | EPA Punjab · Environmental Monitoring Center · AQMS network |
| `#subline` | Built by `SUBLINE()`: hourly averages, wind flow, inter-district transport and India–Pakistan cross-border flow for `{ndistricts}` districts and `{nstations}` AQMS stations, `{start}` to `{end+1h}` PKT. Surface vs Districts hint. Click a district for all its pollutants. |
| `#liveline` | Live collector status or the bootstrap fallback sentence |
| Fonts (online) | Google Fonts: Barlow Condensed 500/600/700, Source Sans 3 400/600/700, JetBrains Mono 400/600 |
| Font fallback | `"Barlow Condensed","Arial Narrow",system-ui,sans-serif` / `"Source Sans 3",system-ui,-apple-system,"Segoe UI",sans-serif` / `"JetBrains Mono",ui-monospace,"SFMono-Regular",Menlo,monospace` |
| Wrap | `max-width: 1320px`; main grid `1fr 360px`; stacks to one column at 980 px |
| Colour tokens (light) | `--bg #eef1ef`, `--panel #fbfcfb`, `--ink #17221f`, `--muted #5b6964`, `--sea #e3e8e5`, `--land #eceeec`, `--punjab #f8f9f8`, `--accent #0d6e72`, `--flow #18302f`, `--particle rgba(20,40,40,.32)`, `--border #a3261f`, `--inflow #c4312a`, `--outflow #0d6e72`, `--india #efe8d8` |
| Dark | `@media (prefers-color-scheme: dark)` and `:root[data-theme="dark"]`. A `MutationObserver` on `data-theme` plus `matchMedia` re-reads tokens and redraws. |

Viewport: `width=device-width, initial-scale=1, viewport-fit=cover` plus `claude:viewport-fit-sides=cover`. Safe-area padding on html/body.

### 11.2 Pollutant switch (`#polBtns`)

Buttons for AQI, PM2.5, PM10, NO₂, SO₂, CO, O₃, NO, NOx (`POLNAME`). `aria-pressed` marks the active species. Bootstrap calls `setPol('AQI')` so **AQI is the default view** even though the engine initialises `pol='PM10'` before that call. Switching rebuilds the legend, hourly tables, findings, KPIs, surface cache, and the selected-district table.

### 11.3 Map canvas and clock

| Control | Id / behaviour |
|---------|----------------|
| Canvas | `#map` — pollutant field, wind flow, transport, chevrons, airports, labels |
| Clock | `#cday` weekday+date · PKT; `#ctime` `HH:00–HH:00`; `#cpol` `{name} · hourly average` |
| Legend | `#lgTitle`, `#lgbar`, `#lgticks`, `#lgMode` |
| Play | `#play` — label **Pause** on load (`playing=true`); toggles with `#play2` |
| Scrubber | `#scrub` `min=0 max=N-1 step=0.01` |
| Mode | radio `name=mode` values `surface` (default) / `district` |
| Transport arrows | `#tLinks` checkbox, **checked** |
| Regional wind | `#tReg` checkbox, **checked** |
| ECMWF level | `#ecmLev` options `10` (10 m) / `925` (925 hPa) |
| Speed | `#speed` 0.35 Slow / **0.8 Normal** / 1.6 Fast |

Click on a district polygon selects it (`admPaths` hit-test). Selected district gets a 2.2–2.6 px ink outline. Collision-avoiding labels: name always; numeric value in Districts mode (with `~` if estimated). Surface mode draws 3.6 px station dots coloured by the station value. Districts mode draws 3.2 px ink squares for non-Lahore stations. Airports: filled triangle, accent shaft, `✈ ICAO speed` label (special placement for OPMT centred, OPRN/OPFA above).

`drawNodes` remains in the source (station squares, district discs, Lahore dashed box). The live `render()` path uses `drawChoro` + `drawValues` instead of `drawNodes`.

### 11.4 Side column

**Province this hour**

- `#kMean` district mean of the current hour (`MEANS[fr]`)
- `#kOver` districts above PEQS, or Unhealthy-or-worse when AQI
- `#kTop` highest district name and value
- `#spark` 70 px provincial-mean sparkline with a PEQS/200 dashed line and a vertical playhead

**Airport winds this hour** (`#apBody`)

Columns: site, wind, visibility km, temp °C, weather. METAR text uses 8-point compass. AQMS fallback labelled `(AQMS)`. `#apNote` prints `apLatest` captions when live hours have filled them.

**All districts this hour** (`#dList`)

Ranked bars, highest first. Dashed ref line at AQI 200 or the PEQS limit. Italic estimated names. Click a row to `select`.

**Selected district all-pollutant table** (`#dPol`, heading `#dName2`, default Lahore)

This hour, period mean, PEQS/category. Swatch uses that species’ scale. The active pollutant row is bold.

**CPF wind rose** (`#rose`, selector `#dSel`, meta `#dMeta`)

Default district Lahore. `#dMeta` reports station count, period mean, max hour, P75, calm fraction — or the estimated-district sentence.

### 11.5 Nine-map comparison grid (asks 21–22)

Section heading “All pollutants, same hour”. `#mtime`, `#play2`, `#scrub2` stay in lock-step with the main playhead (`fpos` is shared). `#minis` is a 3-column grid (2 columns ≤ 1150 px, 1 column ≤ 560 px). Order `CMP = ['AQI','PM2.5','PM10','NO2','SO2','CO','O3','NO','NOX']`. Each figure has its own PEQS/PEPC/AQI legend. Mini-maps use the same Surface/Districts mode, clip to a slightly inset Punjab box `P(69.25,34.1)…P(75.45,27.62)`, draw up to 8 transport links (not on AQI), and select a district on click.

### 11.6 Lahore AQMS network (asks 11, 13, 20, 28, 34)

The card “Lahore AQMS network” exists in the HTML **inside `<div hidden>`** (ask 28). `drawLahore` and `lahoreTable` still run against `#lmap` / `#lBody` every frame.

| Item | Behaviour |
|------|-----------|
| Stations | 13 Lahore sites (`DATA.stations.filter(s => s.d==='Lahore')`) |
| Markers | ■ 12×12 square fixed; ▲ triangle mobile |
| Labels | Short names (GTH Shahdara, Jandiala Kalsan, Gulberg III, …) with collision offsets |
| Wind badge | Compass at lower left of the inset, district wind |
| Table | Station, glyph, this hour, 24-h mean (mean requires ≥ 75% valid hours) |
| Hint | “11 stations, coloured by hourly {pol}. ■ fixed · ▲ mobile. Wagha Border sits on the India border.” (copy still says 11; the inset plots all 13, including Lathepur and Jandiala Kalsan) |

EMC-confirmed coordinates in §4.4 apply on this inset and on the provincial map.

### 11.7 Hourly wind-speed table (ask 37)

`#apHr` is a heatmap: one row per airport, one column per hour. METAR cells have a teal background whose alpha grows with speed (`rgba(13,110,114, min(0.55, 0.08+s/6))`). AQMS-fallback cells are italic muted. Calm if speed < 0.25 m/s. The current hour is outlined (`.cur`). `apWind` implements the METAR-then-AQMS fallback using `AP_D`.

### 11.8 Hourly district tables (asks 5, 18)

Heading “Hourly district averages”. Three tabs (`data-tab`):

| Tab | `tab` | Content |
|-----|-------|---------|
| Concentration | `c` (default) | District × hour coloured by the PEPC/AQI/continuous scale. Period mean, max, hours > 200 or hours > PEQS. Estimated block separated by a header row. Period mean shown when ≥ 75% of hours are valid. |
| Inter-district transport | `lk` | Top 20 `src → rcv` pathways by period total. Blank = wind not pointing at the receptor. Hint quotes the index: source concentration × wind speed × alignment × distance decay. |
| Transboundary | `tb` | Border-belt districts sorted by `border_km`. + red India→PK, − teal PK→India, 0 calm/along-border. In / Out / Net. Belt total row. ECMWF 925 hPa and 10 m cross-border wind rows (`xbRow`). |

`#tabNote` restates the rule for the active tab. The current hour column is outlined on both `#hrTable` and `#apHr`.

### 11.9 All-sides section `#xbAll` (asks 49–50)

Placed above Key findings. Heading “Cross-border transport from all sides of Punjab”.

Hint (verbatim contract): hourly ECMWF 10-m wind across the provincial boundary × CAMS PM2.5 just outside (inflow) or just inside (outflow), at 117 points about 25 km apart, 1–12 Nov (10–12 Nov forecast). The index ranks sides and days; it is not a mass budget, and CAMS reads lower than AQMS. Fires: NASA FIRMS VIIRS (NOAA-20, NOAA-21), 2–9 Nov. Air quality outside Punjab: IQAir US AQI, 9 Nov about 23:00 PKT (US EPA scale, not EPA Punjab AQI).

Contents:

1. **Map figure** — net transport arrows (red into Punjab, blue out), VIIRS fire dots 2–9 Nov, IQAir circles (station) and squares (estimate).
2. **Bar chart** — inflow/outflow index by neighbouring region, 1–9 Nov (Rajasthan net +4.2, Indian Punjab net −4.8, Jammu +0.5, KP +1.7, Islamabad +0.2, AJK −0.7, Balochistan −1.5, Sindh −1.7; units thousands of the CAMS×wind index).
3. **Daily inflow chart** — India / KP+Islamabad+AJK / Balochistan+Sindh stacked, 1–12 Nov, with 10–12 Nov marked ECMWF/CAMS forecast.
4. **Key points list** — India 56% of inflow; Rajasthan largest net source; 8–9 Nov doubling; KP net source; Punjab net exporter to Sindh, Balochistan, AJK; 10–12 Nov forecast.
5. **Fire table** — 11 regions × 2–9 Nov + Total (values in §5.5).
6. **IQAir 32-city table** — Peshawar 471, Jammu 277, New Delhi 271, Bathinda 251, Ludhiana 220, Srinagar 214, Dera Ismail Khan 211 (estimate), Sri Ganganagar 206, Hisar 204, Mandi Gobindgarh 199, Fazilka 196 (estimate), Patiala 194, Hanumangarh 194, Amritsar 187, Bannu 183 (estimate), Rupnagar 180, Muzaffarabad 176, Chandigarh 168, Islamabad 166, Jalandhar 165, Kabul 165, Sukkur 163 (estimate), Nowshera 161 (estimate), Mardan 158 (estimate), Larkana 158 (estimate), Quetta 157, Jaipur 153, Abbottabad 131, Karachi 129, Bikaner 127, Hyderabad 92, Jodhpur 70.

The three figures are **fixed images** from the 9–10 Nov build. They do not animate with `fpos`.

### 11.10 Key findings (`#findings`)

`findings()` rebuilds four bullets whenever the pollutant changes:

1. **Hotspots** — highest period means; AQI category counts or PEQS-exceedance sentence.
2. **Inter-district transport** — top four pathways (hidden for AQI, replaced by a sentence that AQI is an index).
3. **Transboundary** — hours of India-side wind; Wagha `c_india` vs `c_other`; belt enrichment ≥ 1.05 with `n_india ≥ 30`; time-of-day of India-side hours; OPLA afternoon vs night wind; ECMWF 925 hPa inflow/outflow hours and mean. Hidden for AQI.
4. **Coverage** — 79 stations / 41 districts; Chiniot and Lodhran no valid PM; live-hour sentence when `meta.live` exists.

### 11.11 Method notes

The dashboard Method card is operator-facing specification, copied here from the delivered HTML (seven paragraphs). The engine rules in §8–§9 implement this text.

**Hourly values.** EPA Punjab's hourly AQMS exports: the 1–4 November periodic export (56 stations), 4 Nov 00:00 to 5 Nov 11:00, and the 1–9 November periodic exports to 9 Nov 23:00 (80 stations, including 24 new tehsil-level sites, which bring every one of the 41 districts under measurement). A station's AQI is used only in hours with a valid PM2.5 or PM10 reading. The record continues hourly from the public portal when the cloud collector can reach it (see Live hours). Flagged values, zeros, isolated spikes and values repeated three hours running (logger holding its last value) are removed. The district value is the mean of its stations; wind is their vector mean. Wazirabad's vane was earlier found about 140° off, so its wind is not used; wind speeds above 30 m/s (DC Office Chakwal reports direction in the speed field, DC Office Khanewal reports 99.9) are discarded. Where a district has no valid station wind in an hour, the airport METAR for that district is used, then ECMWF 10-m wind. New stations not in the network shapefile are placed at their town centre (approximate; listed in the station popups); OneNetwork Station 25 is left out because its location is not known.

**Meteorology.** Airport METARs (aviationweather.gov) for Lahore, Faisalabad, Multan, Sialkot, Islamabad and Amritsar cover the whole period hourly; each hour is the vector mean of that hour's reports, plotted as ✈ markers. ECMWF IFS 0.25° winds (Open-Meteo) on a 0.5° grid over Punjab and the Indian side drive the regional flow lines outside Punjab (10 m or 925 hPa, the level where smoke travels furthest), and give the cross-border wind: the ECMWF wind component across the India–Pakistan border, averaged along it, positive when air moves from India into Pakistan.

**Live hours (from 3 Nov).** A cloud task reads the EPA Punjab public portal (aqi.punjab.gov.pk) every hour and stores each station's hourly AQI, PM2.5, PM10, NO₂, SO₂, CO, O₃ and station wind. The same cleaning rules apply (zeros, spikes against a 7-hour median, values held three hours). Portal stations are matched to network stations by coordinates and name; the portal does not report NO or NOx. District wind is the vector mean of station winds; where a district has none, the airport METAR (aviationweather.gov) is used, then ECMWF IFS 10-m wind (Open-Meteo). WMO synoptic winds (Ogimet) appear in the hourly wind table. These are provisional real-time values and will be replaced by the verified AQMS export at month end.

**Geography.** District boundaries (41 districts, including Wazirabad, Murree, Talagang, Kot Addu and Taunsa) and station locations come from EPA Punjab's own shapefiles. Point geometry is used where the Lat/Lon attributes were wrong (Gulberg III, DC Office Sialkot, Wazirabad). Sahiwal, Rajanpur, Talagang and Khushab stations report data but are not in the station shapefile, so they use approximate coordinates.

**Transport.** Each hour, district A sends load to district B (within 180 km) when A's wind points within ±35° of B. Index = concentration × wind speed × cos(angle) × e^(−km/100).

**CPF.** From hourly readings: share above the district's 75th percentile per 22.5° wind sector, calms below 0.5 m/s (the airport definition of calm, about 1 knot) excluded; the same threshold applies to transport and cross-border flow.

**Transboundary.** Same index for border-belt districts whose wind came from, or blew toward, Indian Punjab, Haryana or Rajasthan. No Indian monitors are in this data, so it shows when cross-border air arrived, not how much it carried. Colour scales are set relative to the Punjab EQS limit for each pollutant.

### 11.12 Accessibility and interaction

- `role="group"` on the pollutant switch; `aria-label` on the map, rose, minis, Lahore canvas, all-sides section.
- Focus-visible 2 px accent outline on buttons, selects, inputs.
- Heat tables: first column sticky.
- District list max-height 340 px, scrollable.
- `#play` / `#play2` share `togglePlay`.
- Resize is debounced 120 ms; rebuilds projection, Lahore inset, minis, and static panels.

### 11.13 Engine functions in `#mainsrc`

Every function named in the index inventory is specified here as implemented behaviour. `drawNodes`, `drawSurface` and `drawTB` remain in the source; the live `render()` path does not call the first two, and `drawTB` is empty.

| Function | Implemented behaviour |
|----------|------------------------|
| `colArr` | RGB triple from AQI category, PEPC band, or PEQS-multiple gradient |
| `legend` | Fills `#lgTitle`, `#lgbar`, `#lgticks`, `#lgMode` for the active pollutant |
| `build` | Builds `Path2D` rings for `GEO`/`IND`, Punjab clip `pjPath`, `admPaths`, hatch pattern |
| `resize` | Canvas size, `S`, projection of districts/stations/airports/samples, `seed()`, `sizeMinis()`, `lresize()` |
| `at` | Linear interpolation of district concentration and wind at `fpos` |
| `drawSurface` | Retained district-centroid IDW (`w = 1/(q·√q)`). **Not** the live Surface path |
| `seed` | Spawns up to 700 in-Punjab particles (`np`) and clears regional particles |
| `windAt` | Inverse-distance district + airport wind at a canvas point (`w = 1/(d²+400)`) |
| `ecmAt` | Bilinear ECMWF `u/v` at lon/lat for the selected 10 m or 925 hPa level |
| `rStep` | Advects regional particles outside Punjab on the ECMWF grid |
| `stepDraw` | Calls `rStep`, then draws in-Punjab particle trails (length ≤ 8) |
| `topLinks` | Strongest 12 transport links of the hour at ≥ 8% of period `MAXF` |
| `drawLinks` | Quadratic Bézier shafts + dashed overlay + filled arrowheads; `dash -= 0.6` |
| `drawCross` | 39-sample India–Pakistan chevrons; `ph += 0.012` |
| `drawField` | Cached wind-weighted station continuum (`renderField` / `stationPts` / `fieldAt`) |
| `drawChoro` | Surface → `drawField`; Districts → filled `admPaths` with hatch on estimated |
| `drawValues` | Collision-avoiding labels; Surface dots; Districts squares; airport ✈ triangles |
| `drawMinis` | Nine comparison canvases, same `fpos`, own scale, up to 8 links |
| `apWind` | METAR `(u,v)` else district AQMS vector via `AP_D` |
| `apHourly` | Builds `#apHr` heatmap for every airport and hour |
| `render` | `drawChoro` → `stepDraw` → airports → `drawCross` → `drawLinks` → `drawValues` → `drawLahore` → `drawMinis` → `panel` → `apTable` → `lahoreTable` → `markHour` |
| `panel` | Clock (`#cday` `#ctime` `#cpol`), KPIs (`#kMean` `#kOver` `#kTop`), sparkline |
| `districtList` | Ranked `#dList` bars, highest first |
| `polTable` | Selected-district all-pollutant `#dPol` |
| `chart` | Sparkline / series canvas helper (`#spark`) |
| `drawRose` | CPF 16-petal rose on `#rose` |
| `select` | Sets `selected`, `#dSel` `#dName` `#dName2`, `#dMeta`, redraws rose and `#dPol` |
| `drawLahore` | Hidden Lahore inset `#lmap` (still invoked every frame) |
| `lahoreTable` | Hidden Lahore station table `#lBody` |
| `buildHourly` | Concentration / transport / transboundary `#hrTable` |
| `xbRow` | ECMWF 10 m and 925 hPa cross-border rows on the transboundary tab |
| `findings` | Rebuilds `#findings` bullets |
| `setPol` | Switches `pol`/`PD`, rebuilds legend, tables, findings, KPIs, surface cache |
| `togglePlay` | Flips `playing`; labels `#play` and `#play2` Pause/Play |
| `tick` | Advances `fpos` by `dt·speed` (dt cap 0.1 s), wraps at `N-1`, `render()` |
| `loop` | `requestAnimationFrame` loop; records `lastRaf` |
| `liveLine` | Fills `#liveline` from `meta.live` or `__liveState` |
| `__liveRefresh` | After a later `hours` snapshot: update `N`, scrubbers, minis, subline, live line, `#apHr`, `setPol` |

Supporting helpers used by those functions and specified elsewhere: `stationPts` / `fieldAt` / `renderField` (§9.3), `drawNodes` (defined, unused by `render`), `drawTB` (empty, called from `refreshStatic`), `apTable` (airport card `#apBody`), `markHour` (outlines the current hour on `#hrTable` and `#apHr`), `readTokens` (CSS custom properties, dark-mode redraw).

---

## 12. Animation and reduced-motion fallback (ask 2)

Ask 2 (“animation not working”) was the office-PC failure mode: Windows **Animation effects** / reduced motion / background-tab throttling froze `requestAnimationFrame`, so the clock stayed at the first frame.

**Delivered November behaviour**

```
playing = true                         # autoplay on load
function tick():
  dt = min(0.1, (now − last) / 1000)
  if playing: fpos += dt · speed; wrap at N-1
  render()

function loop():
  lastRaf = performance.now()
  tick()
  requestAnimationFrame(loop)

setInterval(66 ms):
  if performance.now() − lastRaf > 200:
    tick()                             # backup timer
```

There is **no** `prefers-reduced-motion` media-query gate in `#mainsrc`. Autoplay plus the 66 ms stall detector is the implemented fallback. Particles, dashed transport overlay (`dash -= 0.6`), and chevron phase (`ph += 0.012`) all advance inside `render()`, so when the clock moves, the continuum moves.

The Play button shows **Pause** on load because playback has already started.

---

## 13. Daily AQI situation report (asks 43, 44, 46, 47, 48, 51)

A visual-first Word product for authority decision-making. Charts are redrawn as images so they print. Tables remain editable.

### 13.1 Files

| File | Role |
|------|------|
| `Punjab_AQI_Situation_Report_05Nov2026.docx` | First visual-first edition (6 A4 pages) covering 1–5 Nov including 3 Nov |
| `Punjab_AQI_Situation_Report_09Nov2026.docx` | Current edition (10 pages after mixing-height and all-sides sections) |

These Word files live in the conversation deliveries. They are **not** inside `original System/`. They are specified here because the conversation requested them and Claude built them as part of the same system.

### 13.2 Visual-first 5 Nov edition (asks 43–44, 46)

Ask 44 required 3 Nov (missing in an earlier draft), visuals rather than description, and the valid-PM AQI rule. Opening: one-line headline, four key numbers, four actions. Body:

- District counts by AQI category, 1–5 Nov
- District maps for 3, 4, 5 Nov
- Hourly AQI for south Punjab against the Lahore–Gujranwala belt
- Heatmap of every district for every day
- Average AQI by hour of day for three regions
- Each pollutant as a multiple of its PEQS limit
- Wind outlook grid by city
- Transport map with source/receptor districts

With 3 Nov included, that day was the 1–5 Nov peak among districts that reported all five days (province mean AQI 260 vs 230 / 256 / 243). The Word file follows the same order as the (then) online report.

### 13.3 9 Nov edition (asks 47–48)

Rebuild from the 1–9 Nov AQMS export (through 23:00), FIRMS 1–8 Nov (then 2–9 Nov in the dashboard table), and IQAir Indian (later all-sides) cities.

Hourly-AQMS narrative in the 23:32 / 23:39 drafts (later **superseded for provincial/Lahore averages** by official daily reports in §13.4): 9 Nov province mean 315 from the hourly set of 37 districts; 16 of 37 above 300; nine Hazardous; worst Nankana Sahib 487, Kasur 456, Jhang 451. Crop fires 1–8 Nov: Punjab (PK) 7,417, Punjab (IN) 3,262, Haryana 347; Jhang, Hafizabad, Nankana Sahib, Sheikhupura, Bahawalnagar, Okara ~three-quarters of Punjab (PK). Smoke from India on 8–9 Nov at the surface and ~750 m. IQAir nearby: Jammu 277, New Delhi 271, Bathinda 251, Ludhiana 220, Amritsar 187 (US AQI). Seven stations with no valid PM in the last 48 hours listed for repair: Chiniot, Gymkhana Lodhran, DD Development Bahawalnagar, Choa Saidan Shah, Ladhewala, Kot Naina Shakargarh, Kallar Kahar.

IQAir US AQI is a different scale from EPA Punjab AQI. Pakistani IQAir readings include cheap private sensors (Multan 844, Kasur 505 on IQAir).

### 13.4 Official daily AQI figures (ask 51)

Ask 51 required provincial and district averages and the heatmap from the **official Daily AQI Reports**. Each report covers the previous day, so reports dated 1–9 Nov give 31 Oct–8 Nov. 9 Nov* is provisional, computed from hourly AQMS by a method that **reproduces the published Punjab and Lahore averages** for every day 31 Oct–8 Nov. Charts hatch 9 Nov*.

| | 31 Oct | 1 Nov | 2 Nov | 3 Nov | 4 Nov | 5 Nov | 6 Nov | 7 Nov | 8 Nov | 9 Nov* |
|---|--------|-------|-------|-------|-------|-------|-------|-------|-------|--------|
| Punjab average | 219 | 220 | 242 | 247 | 242 | 231 | 226 | 226 | 246 | **303** |
| Lahore (10 AQMS) | 283 | 353 | 435 | 360 | 329 | 345 | 301 | 273 | 314 | **374** |
| Districts above 300 | 2 | 3 | 7 | 9 | 8 | 8 | 10 | 10 | 8 | **16** |

Report changes: new provincial/Lahore trend chart; district category chart with the published provincial average printed above each day; district maps for 7 and 8 Nov from official figures; heatmap 31 Oct–9 Nov* for 39 districts (Punjab and Lahore averages in the top two rows; Chiniot and Lodhran omitted — no valid data on any day). Headline: 9 Nov provincial average 303, highest this month (earlier official peak 247 on 3 Nov). An earlier hourly figure of 315 used a different district set; **303 is the figure to quote**.

The forecast, regional, pollutant, and cross-border sections of the Word report continue to use hourly AQMS (which tracks the daily reports closely for most districts). The November HTML dashboard Method and KPIs remain on the **hourly AQMS** cube; official daily averages live in the Word report.

### 13.5 Distinction: official daily AQI vs hourly AQMS

| Product | Averaging | Use |
|---------|-----------|-----|
| Daily AQI Report (31 Oct–8 Nov official; 9 Nov* provisional) | EPA Punjab published method; Lahore from 10 AQMS | Situation-report headline, category chart, district maps, heatmap |
| `window.DATA` hourly cube | Station-hour mean → district-hour mean; valid-PM AQI; 75% rule for period means | Dashboard map, KPIs, tables, CPF, transport |

Both are specified. They must not be silently substituted for each other.

---

## 14. Next-24-hour forecast (ask 45)

Each district’s **latest observed level**, shaped by **that district’s own measured hour-of-day profile** (persistence × diurnal). No CAMS air-quality forecast and no ECMWF wind adjustment: both **worsened** a hindcast against the last 24 hours (first CAMS/ECMWF variant ran 52 AQI points high and lost to plain persistence).

**Hindcast skill (quoted from the 5 Nov build, tested on 3 and 4 Nov):** typically off by about 40 AQI points per hour and 25–30 points on the daily mean; about two-thirds of districts in the right category.

**Later 9 Nov tests:** the same method ran 18–53 AQI points too low on the last three days, so the published forecast is a **floor**.

**9 Nov 23:00 forecast through 10 Nov 23:00** (situation report):

- Overnight 00:00–06:00: 17 districts expected above 300
- Afternoon break: province average ~215 around 16:00, about 6 districts above 300
- Evening peak: average ~360 by 21:00; 24 districts above 300 between 18:00 and 24:00

The dashboard itself does **not** draw a forecast layer. The forecast is a situation-report product. Possible bias noted: stronger northwest winds may bring the north and centre in lower than shown.

---

## 15. Mixing height, PBL and ventilation (ask 52)

Special situation-report section 11, “Mixing height and weather, 10 November”, covering all 41 districts hour by hour.

Meteoblue was requested; NOAA GFS mixing height is what was retrieved (Open-Meteo), with ECMWF IFS wind, humidity and pressure (retrieved 10 Nov ~01:45 PKT). A note states that a Meteoblue numerical export can replace the GFS column if EMC holds a licence.

**Mixing height**

- Below 100 m for 15 of 24 hours (17:00–08:00); 10–50 m overnight in most districts
- Rises to about 1,900 m by 15:00 and collapses at sunset
- Deepest afternoon: Rahim Yar Khan 2,890 m, Lodhran 2,520 m
- Shallowest afternoon: Attock 1,150 m, Taunsa 1,210 m

**Wind:** district averages 0.7–2.2 m/s all day. Talagang, Hafizabad, Khushab, Lahore, Rahim Yar Khan have 6–8 calm hours.

**Humidity:** 90–94% before dawn in 11 districts (Narowal, Talagang, Mianwali, Mandi Bahauddin and others) — favours haze and fog.

**Pressure:** SLP ~1,017 hPa at 09:00 to ~1,012 hPa at 16:00 (weak stable high).

**Dispersion = mixing height × wind speed**

- “Poor” for most of the day everywhere; “adequate” only for a few afternoon hours
- Sahiwal and Multan never get even halfway to adequate
- Worst-ventilated: Sahiwal, Toba Tek Singh, Jhang, Talagang, Pakpattan, Attock, Multan, Taunsa (Sahiwal, Jhang, Pakpattan already Hazardous on 9 Nov)

Visuals: hourly chart of mixing height, dispersion, humidity, wind and pressure; colour grid of mixing height for every district and hour; colour-coded summary table sorted worst-to-best dispersion.

This section is **not** a dashboard layer. It lives in the Word report.

---

## 16. Technical advisory and cover letter (asks 53–54)

Word pair dated 10 November 2026, rewritten to follow the EPA 26 May advisory.

| File | Role |
|------|------|
| `Cover_Letter_Technical_Advisory_10Nov2026.docx` | One page, DDs/ADs (Field), same CC list as the 26 May letter |
| `Technical_Advisory_Smog_Episode_10Nov2026.docx` | Four pages, pollutant-specific mitigatory controls |

### 16.1 Form (ask 54 — 26 May style)

- EPA letterhead with logo
- Times New Roman, justified
- Four sections (analysis; pollutant-by-pollutant mitigatory controls by sector; emergency action plan; compliance / Issued-by)
- Formal tone
- Dispatch number left blank: `EPA/DIREMC/O/261110/____`
- Faint May watermark not reproduced (letterhead template supplies it)

Title (version 2): **Technical Advisory: Pollutant-Specific Mitigatory Controls for the Smog Episode Across Punjab**.

Cover letter: summarises the situation, requires immediate action under the advisory’s control and emergency sections, requests the daily compliance report by 11:00.

### 16.2 Pollutant-by-pollutant analysis (9 Nov hourly, provisional)

Station figures are provisional hourly AQMS for 9 Nov (they tracked official district values on earlier days). 8 Nov provincial figures in the advisory are from the official report.

| Theme | Specified content |
|-------|-------------------|
| Fine particles (PM2.5), crop-burning belt | Main pollutant at 56 of 69 stations. Sahiwal AQI 455.5 (PM2.5 dominant 71% of the day), Jhang 450.9, Vehari 440.9, Okara 436.2, Pakpattan 430.4 (PM2.5 509 µg/m³) |
| Smoke from across the border | PS Ganda Singh Wala 453.5, Wagha Border 360.4, PM2.5 dominant all day |
| Coarse particles (PM10), urban/industrial | Nankana Sahib 487.1 (PM10 849 µg/m³), LWMC-LHR 431.6, BZU Multan 396.6, NTU Faisalabad 363.7, GCW Gujranwala 314.2, DHQ Sheikhupura 308.1 |
| SO₂ above limit | LWMC-LHR 157.4, DC Office Faisalabad 137.6, GCU Faisalabad 134.0, NTU Faisalabad 131.3 µg/m³ — industrial fuel |
| NO₂ above limit | Gulberg III Lahore 90.9, LWMC-LHR 83.2, DC Office Rawalpindi 81.7 µg/m³ — traffic |
| CO | DC Office Hafizabad 5.5 mg/m³, linked to crop residue (1,250 fires in Hafizabad) |
| O₃ | High only at Murree (165 µg/m³) |

Headline context used in the first draft: provincial average AQI 303 on 9 Nov* (provisional); sixteen districts above 300, nine Hazardous; three causes named (crop burning, smoke from India on 8–9 Nov, still air at night). PM2.5 averaging 5.1 times the PEQS limit on 8 Nov while NO2, SO2 and CO stayed within limits in that official-report summary.

### 16.3 Sector mitigatory controls

- **A. Agriculture** — crop burning (PM2.5 and CO). EMC sends satellite fire locations daily; field teams check each one within 24 hours.
- **B. Industry and energy** — fuel quality, brick kilns, generators (SO₂ and particles).
- **C. Traffic** — NO₂ and vehicle smoke.
- **D. Municipal** — dust (PM10), construction, waste burning.
- **E. Coordination** — across the border through the federal government; with EPA Khyber Pakhtunkhwa and Islamabad EPA.

### 16.4 Emergency actions and legal frame

Automatic triggers in districts above AQI 400; a table of steps at AQI 201–300, 301–400 and above 400, with the districts currently in each band named. Steps outside EPA’s own powers (school measures, suspending kilns) are recommendations to the competent authorities. Daily compliance reporting to EMC by 11:00. Issued-by block as in the May advisory. Legal citation: Punjab Environmental Protection Act, 1997 generally for action on crop burning; particular sections or smog rules to be added by EMC if that is house style.

Public-health advice was present in the first (7-section) draft; the 26 May rewrite folds operational content into the four-section May skeleton.

---

## 17. Packaging and standalone download (ask 55)

| Artifact | Size / behaviour |
|----------|------------------|
| `original System/index.html` | 9,609,848 bytes, 805 lines. Opens in a browser. Live bootstrap attempts `claude.use('db')` for 9 s, then runs on the embedded 1–9 Nov record. |
| `Punjab_Air_Quality_November_2026_Dashboard.html` | ~9.4 MB conversation download. Same content family. **No live extend.** Subtitle states the copy will not pick up new hours. Offline it uses the browser’s standard fonts (Arial Narrow / system-ui / SFMono), so it looks slightly different from the Google-Fonts online view. |
| `original System/collector/collector.py` | 16,362 bytes. `python3 -I collector.py fetch\|build`. |

No application server, no Node toolchain, and no database engine are required to **view** the baseline. Live hours require a host that can write the `hours` collection.

Earlier dated pages in the same product line (specified as ancestors whose capabilities were carried into the November file):

| Page | Period / role |
|------|----------------|
| `punjab_pm10_transport.html` | 23–24 Oct, originally half-hour frames; animation fallback, transboundary chevrons, CPF, transport |
| `punjab_pollutant_transport.html` | Multi-pollutant 36-district rebuild |
| `punjab_26oct.html` | 26 Oct evening inversion; Surface/Districts; Lahore section later removed |
| `punjab_live.html` | IQAir + FIRMS + CAMS live prototype; hourly task later **repointed** at the November dashboard |
| `lahore_air_quality.html` | 24 Oct Lahore station study (gust front, frozen sensors) |

Companion extracts: `airport_wind_26Oct2026.csv`, `airport_wind_Nov2026.csv`.

---

## 18. Limits, non-goals of the baseline, and diagnosed dead ends

These are specified behaviours, not omissions.

| Topic | What the system does |
|-------|----------------------|
| `aqi.epaforecast.com` | Diagnosed sign-in-only. **Not** a collector endpoint. Public collection is `aqi.punjab.gov.pk`. |
| Meteoblue numerical mixing height | Not retrieved (images only / paid licence). NOAA GFS used. |
| CAMS/ECMWF forecast adjustment of next-24h AQI | Built, hindcast-failed, **omitted** from the published forecast. |
| Indian AQMS | None in the cube. Transboundary is wind-timing plus CAMS×ECMWF rank index plus IQAir city snapshots. |
| Portal NO / NOx | Not reported; live hours leave those series empty. |
| `OneNetwork Station 25` | Location unknown; skipped. |
| Tehsil sites vs `PMAP` | 24 tehsil-level export stations are not all in `PMAP`. Until unknown portal IDs are added, live hours for those sites are omitted. |
| `#xbAll` charts | Fixed images; they do not follow live hours. |
| Official daily AQI on the HTML dashboard | Not wired. Official 31 Oct–8 Nov / 9 Nov* figures live in the Word situation report. |
| Forecast layer on the map | Not drawn. Forecast is a Word-report product. |
| Mixing-height layer on the map | Not drawn. Mixing height is a Word-report product. |
| `drawNodes` | Defined, not called from `render()`. |
| `drawTB` | Empty function (`const drawTB=()=>{}`). |
| `wscale` | Stored on `DATA`, unused by `#mainsrc`. |
| `prefers-reduced-motion` | Not consulted; rAF + 66 ms backup is the fallback. |
| Invented values | Forbidden. Missing fetches stay missing. |

---

## 19. Out of baseline

A later FastAPI / React / TimescaleDB / Deck.gl workstation exists under `src/`, `frontend/`, and related docs (`SYSTEM_ARCHITECTURE.md`, `TRANSFORMATION_LOGIC_SPEC.md`, `docs/SystemSpecs-16-11-2026-Gemini.md`). **That tree is not this specification.** Mentions of it belong only here. Reconstructing the Claude-built system means reconstructing `original System/index.html` + `collector.py` plus the Word report/advisory/forecast/mixing-height products named in §13–§16.

---

## 20. Coverage matrix

Every conversation ask and every original-system subsystem maps to a spec section. A coverage audit is a search for the **named capability specified**, not merely listed in §2.

### 20.1 Conversation asks → spec

| Ask | Capability | Section |
|-----|------------|---------|
| 1 | Animated PM10 / wind / CPF / inter-district transport | §9.3–§9.7, §11.3, §12 |
| 2 | Autoplay + reduced-motion / rAF-stall backup timer (66 ms / 200 ms) | §12 |
| 3 | India–Pakistan transboundary layer (Indian side, dashed border, chevrons, belt table) | §9.6, §11.3, §11.8 |
| 4 | District boundaries and AQMS locations | §4, §11.3 |
| 5 | Hourly district means + inter-district + transboundary tables | §9.1, §11.8 |
| 6 | 36-district / 56-station framework (later 41 / 79) | §4.2, §4.4 |
| 7 | Fresh AQMS export rebuild | §5.1, §7 |
| 8 | Unmonitored-district IDW; receptors only; `~` and hatch | §9.2, §11.3 |
| 9 | Hourly (not half-hour) frames, hour-beginning PKT | §4.1 |
| 10 | Concise layout: map, side cards, tables, findings, Method | §11 |
| 11 | Multi-pollutant selector; Lahore panel separate | §11.2, §11.6 |
| 12 | Clean provincial map (labels, ≤12 arrows, light wind, small dots) | §9.5, §11.3 |
| 13 | Lahore multi-pollutant insights | §11.6, §11.10, §16.2 |
| 14 | Wind analysis | §8.2, §9.4, §11.4 |
| 15–16 | Updated Lahore file / full columns | §8.7 |
| 17 | Strict QC; spatiotemporal Lahore; gusts | §8, §8.7 |
| 18 | District concentration as the map readout | §11.3, §11.8 |
| 19 | Transport arrows on by default | §11.3 (`#tLinks` checked); off for AQI |
| 20 | Lahore network and rose on the same page | §11.4, §11.6 |
| 21 | Four maps same view | §11.5 |
| 22 | Nine synchronized provincial maps | §11.5 |
| 23 | Refresh on new export (26 Oct context) | §4.1, §17 |
| 24 | Airport METAR OPLA, Faisalabad, Multan, nearby | §5.2, §11.3 |
| 25–26 | Ranking and transport on full export; Wazirabad vane | §8.2, §11.4 |
| 27 | Province-wide continuum; Surface / Districts | §9.3, §11.3 |
| 28 | Remove separate Lahore section (`<div hidden>`) | §11.6 |
| 29 | Official 41-district shapefiles; new districts | §4.2, §4.4 |
| 30 | AQI default; EPA Punjab 7-tier colours `#00B050`…`#C00000` | §9.8, §11.2 |
| 31 | aqi.punjab.gov.pk + IQAir | §5.1, §5.6 |
| 32 | Airports, FIRMS, ECMWF/Open-Meteo/CAMS, realtime continuum | §5.2–§5.7, §6, §9.3 |
| 33 | November 2026 dashboard 1–9 Nov | §4.1 |
| 34 | EMC-confirmed Lahore coordinates | §4.4 |
| 35 | Plot airport winds (OPLA, Multan, Islamabad, Sialkot, RYK, Bahawalpur, …) | §5.2, §11.3 |
| 36 | PEPC parameter-wise breakpoints | §9.8 |
| 37 | Hourly wind speed at airport sites | §11.7 |
| 38 | aqi.epaforecast.com realtime — diagnosed gated, unused | §5.1, §18 |
| 39 | Public portal + airports + WMO; keep November hourly | §5, §6, §10 |
| 40 | Machine-independent collector plan | §6 |
| 41 | Implement collector.py + hours store + extendData | §6, §10 |
| 42 | 79 stations / 41 districts; ECMWF 10 m and 925 hPa; source-to-sink | §4, §5.4, §9.4–§9.6 |
| 43 | Daily AQI situation report | §13 |
| 44 | Include 3 Nov; visual-first; valid-PM AQI | §8.4, §13.2 |
| 45 | Next-24h forecast (persistence × diurnal; CAMS/ECMWF dropped) | §14 |
| 46 | Word document of the situation report | §13.1 |
| 47 | 1–9 Nov + FIRMS + nearby Indian IQAir | §5.5, §5.6, §13.3 |
| 48 | Complete 9 Nov 23:00; forecast through 10 Nov | §13.3, §14 |
| 49 | All-sides ECMWF × CAMS, FIRMS, IQAir outside Punjab | §5.7, §9.6, §11.9 |
| 50 | `#xbAll` on the November artifact | §11.9 |
| 51 | Official daily AQI provincial/district/heatmap | §13.4 |
| 52 | Mixing height 10 Nov all districts (Meteoblue requested, GFS used) | §15 |
| 53 | Advisory + cover letter | §16 |
| 54 | 26 May style, pollutant-specific mitigations, formal tone | §16.1–§16.4 |
| 55 | Standalone offline HTML download ~9.4 MB | §17 |

### 20.2 Collector inventory → spec

| Inventory item | Section |
|----------------|---------|
| CLI `fetch OUT` / `build OUT EXISTING` | §6 |
| UA `EMC-EPA-Punjab-AQ-dashboard/1.0` | §5.1, §6 |
| PORTAL `https://aqi.punjab.gov.pk` | §5.1 |
| `/api/dashboard/current`, `/api/districts`, `/api/district-stations/<District>` | §5.1, §6.1 |
| METAR `aviationweather.gov` 12 ICAO, `hours=6` | §5.2 |
| SYNOP Ogimet blocks 415/416/417 | §5.3 |
| ECMWF Open-Meteo `models=ecmwf_ifs025`, 10 m, Asia/Karachi | §5.4 |
| `get`, `fnum`, `parse_ts`, `fetch`, `synop_wind`, `build` | §6.3 |
| Hour-doc `t/st/ap/wmo/ecm/src/upd` | §6.2 |
| Doc id `hYYYYMMDDHH`, collection `hours` | §6.2 |
| `PMAP`, `NAME_FALLBACK` Chiniot, `DIST` 41, `ICAO`, `WMO`, `POLF` | §4.5–§4.6, §6 |
| No invented values | §6.2, §18 |
| `pollutant_flags` null the flagged pollutant | §5.1, §8.1 |
| METAR nearest hour within 35 min | §5.2 |
| SYNOP `iw` 3/4 knots ×0.5144; `dd×10`; `dd` 99/>36 → null | §5.3 |
| Merge old+new per field; skip empty docs | §6.2 |
| Portal-down: last completed PKT hour for winds | §6.1 |

### 20.3 `index.html` inventory → spec

| Inventory item | Section |
|----------------|---------|
| Title / h1 / eyebrow | §1, §11.1 |
| `meta.start/end/nstations/ndistricts/nmon/unmon/calm/ecm_ratio` | §4.1, §7.1 |
| DATA top-level keys | §7.1 |
| `pol` keys AQI…NOX and subkeys | §7.2 |
| Method: hourly values, valid-PM AQI, flags/zeros/spikes/3-hour hold, district mean, vector-mean wind, Wazirabad 140°, ws>30, METAR then ECMWF, OneNetwork Station 25 | §8, §11.11 |
| Method: METAR set, ECMWF IFS 0.25 on 0.5° grid, 10 m / 925 hPa, cross-border component | §5.2, §5.4, §9.6 |
| Method: live hours from 3 Nov, 7-hour median, portal no NO/NOx, WMO in wind table, provisional | §8.1, §10 |
| Method: 41-district shapefile, Lat/Lon overrides, approximate sites | §4.4 |
| Method: transport 180 km ±35° `C × w × cos(Δ) × e^(−km/100)` | §9.5 |
| Method: CPF 22.5°, P75, calm 0.5 m/s | §9.7 |
| Method: transboundary belt, no Indian monitors, PEQS-relative colours | §9.6, §9.8 |
| UI regions listed in the index inventory | §11.1–§11.11 |
| `window.DATA`, `window.extendData`, `#mainsrc type=text/plain`, live bootstrap `claude.use('db')` collection `hours` | §7, §10 |
| rAF loop + `setInterval` 66 ms if rAF stall > 200 ms; `playing` default true; wrap `fpos` | §12 |
| Engine functions `colArr legend build resize at drawSurface seed windAt ecmAt rStep stepDraw topLinks drawLinks drawCross drawField drawChoro drawValues drawMinis apWind apHourly render panel districtList polTable chart drawRose select drawLahore lahoreTable buildHourly xbRow findings setPol togglePlay tick loop liveLine __liveRefresh` | §11.13 (catalogue) plus §9–§12 |

### 20.4 Completeness rule

Skip of a named capability, rule, or surface in this matrix is a fail. Skip of raw 216-hour telemetry rows is required.

---

*End of SystemSpecs-16-11-2026-grok. Forensic stamp: derived 16 Nov 2026 from `Claude Conversation.md` (55 `# you asked` turns, 24 Oct–10 Nov 2026) and `original System/{index.html, collector/collector.py}` by sectional parse of Method notes, `window.extendData`, `#mainsrc`, and collector source. Hourly `window.DATA` arrays were not inlined. The later FastAPI/React tree and `docs/SystemSpecs-16-11-2026-Gemini.md` were not sources of truth.*
