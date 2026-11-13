# Specification Mining & Architecture Survey Report

**State Folder**: `c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\spec_miner_survey_1`  
**Working Directory**: `c:\Users\Asif\Downloads\Punjab Air Quality`  
**Authoritative Documents**: `docs/TRANSFORMATION_LOGIC_SPEC.md`, `docs/UI_UX_SPECIFICATION.md`, `docs/SYSTEM_ARCHITECTURE.md`, `docs/DATA_PIPELINES_ARCHITECTURE.md`, `TEST_INFRA.md`, `ORIGINAL_REQUEST.md`  
**Data Fixtures**: `data/baseline/baseline_data.json`, `data/baseline/districts.json`, `data/baseline/stations.json`, `data/baseline/airports.json`  

---

## 1. Observation

Direct observations and evidence extracted from authoritative specification files, baseline datasets, and the test suite:

1. **`ORIGINAL_REQUEST.md` §R1–§R5 & Acceptance Criteria (lines 19–70)**:
   - "Build a rigid 100vw x 100vh CSS Grid five-zone workstation interface using strictly scoped CSS Modules backed by WCAG 2.1 AAA tokens in `src/styles/tokens.css` (>= 7.0:1 contrast). Load exclusively IBM Plex Sans, IBM Plex Sans Condensed, and IBM Plex Mono typography, enforcing tabular-nums formatting on all numeric readouts."
   - "Do not use Tailwind CSS, generic fonts, consumer icon packs (lucide-react, heroicons), emojis, 3D tilted map perspectives, backdrop-filter blur, or drop shadows; use crisp 1.25px miter-joined inline SVGs or deck.gl primitives and 1px solid structural hairlines."
   - "MapLibre pitch is permanently locked to 0 with rotation disabled (`pitch: 0, maxPitch: 0, bearing: 0, dragRotate: false, touchPitch: false`)."
   - Deck.gl 5-layer stack: Layer 1 Spatial Surface (IDW bitmap Plate Carrée $K_X = \cos 31^\circ$), Layer 2 District Choropleth (PEPC colors, diagonal hatching for estimated districts, Greedy AABB collision labels), Layer 3 Wind Vector Field (3 states: null dropout, calm $<0.50$ m/s, active vectors; Station 172 Wazirabad blacklisted), Layer 4 Advection Flux & Transboundary Belt (top 60 links, $d \le 180.0$ km, cone $\le 35.0^\circ$, physical dimension guard locking flux to PM2.5 when AQI selected, 39 border normal chevrons triggering crimson when $\Phi_j > +0.25$ m/s), Layer 5 Stations & Aerodromes (79 stations: 74 fixed circles, 5 mobile diamonds, 6 ICAO aerodrome crosshairs, 13 Lahore stations individually pickable).
   - Zone 1 Top Command Bar, Zone 2 Spatial Control Dock, Zone 4 Receptor Inspector, Zone 5 Temporal Playback Scrubber (216h baseline: 2026-11-01 00:00 to 2026-11-09 23:00, horizon sparkline of provincial max AQI).
   - Five Schema Traps: (1) Invert district centroid `[lat, lon]` to `[lon, lat]` while keeping `label` and `boundary` `[lon, lat]` unchanged; (2) Differentiate aerodrome `null` wind outages from aerodynamic calm; (3) Hard-block wind vector rendering for station 172 (Wazirabad); (4) Compute fixed vs. mobile station counts dynamically; (5) Unify estimation flags and apply diagonal hatching to estimated polygons.

2. **`docs/TRANSFORMATION_LOGIC_SPEC.md`**:
   - **T1: Discrete Geodesic IDW (lines 72–83)**: Haversine distance with $R_{\text{Earth}} = 6371.0\text{ km}$, power $p = 2$, singularity clamping $d_0 = 5.0\text{ km}$ ($d_{\text{clamped}} = \max(d, 5.0)$, $w_i = 1 / d_{\text{clamped}}^2$).
   - **T2: Anisotropic Wind-Steered Continuous IDW (lines 124–151)**: Softening $\epsilon = 4.0\text{ px}$ ($\epsilon^2 = 16.0$), downwind alignment cosine $\cos(\alpha_i) = (\Delta x_i u_i - \Delta y_i v_i) / (d_i s_i)$ (accounting for inverted screen Y axis where $v > 0$ carries pollution towards $-y$). For $s_i > 0.5\text{ m/s}$ and $d_i > 2.0\text{ px}$: $\psi_i = 1.0 + 0.70 \cos(\alpha_i) \min(1.0, s_i / 1.5)$, weight $w_i = w_{0,i} \max(0.30, \psi_i)$. Distance alpha taper: $\alpha = 235$ if $d < 45.0\text{ km}$, $\alpha = 95$ if $d > 140.0\text{ km}$, linear lerp between.
   - **T3: Planar Screen Raster IDW (lines 164–180)**: Legacy uncalled / dormant status ($p=3$, $\epsilon^2=0.25$, superseded by T2).
   - **T4: Vector Wind Blending & Cartesian Conversion (lines 184–209)**: Physical sanity: $0 \le w_s \le 30.0\text{ m/s}$, $0 \le \theta \le 360^\circ$. Wazirabad anemometer blacklist ($140^\circ$ physical installation offset). Meteorological convention: $u = -w_s \sin(\theta \pi / 180)$, $v = -w_s \cos(\theta \pi / 180)$. Spatial blending with $\epsilon_{\text{wind}}^2 = 400.0\text{ px}^2$.
   - **T5: CPF Polar Wind Rose (lines 218–262)**: 16 sectors of width $22.5^\circ$ centered on $k \cdot 22.5^\circ$ ($k = \lfloor (\theta + 11.25^\circ) \bmod 360^\circ / 22.5^\circ \rfloor$). Calm cutoff $w_s < 0.5\text{ m/s}$ excluded. Threshold $\tau = P_{75}(C)$ evaluated on **pooled individual station-hour observations** ($\mathcal{O}_d$) for multi-station districts (Lahore $N \approx 2,700$). Small-sample suppression: $\text{CPF}_k = m_k / N_k$ if $N_k \ge 6$, else `null`. Null renders as muted 10px circular arc stub.
   - **T6: Physical Advection Transport Flux (lines 285–313)**: Maximum distance $d_{ab} \le 180.0\text{ km}$, angular cone divergence $\Delta \theta \le 35.0^\circ$, calm cutoff $w_a \ge 0.5\text{ m/s}$, characteristic $e$-folding scale $L_S = 100.0\text{ km}$. $\text{Flux} = C_a w_a \cos(\Delta\theta \pi / 180) \exp(-d_{ab} / 100.0)$. **Physical dimension guard**: strictly disabled for `AQI` (returns empty set `[]` / `null`).
   - **T7: Receptor CPF Pathway Coupling (lines 322–347)**: Composite score $\text{Score}_{a \to b} = \overline{\text{Flux}}_{a \to b} \times \Omega$. Coupling coefficient $\Omega = \text{CPF}_b(k_{\text{rec}})$ if valid, else $0.25$ fallback (for unmonitored districts or $N_k < 6$). Sort descending and strictly truncate to top 60 links. Net Transport Balance $= \sum_{\text{export}} \text{Score} - \sum_{\text{import}} \text{Score}$.
   - **T8: Transboundary Index (lines 356–380)**: Border belt $d_{\text{border}} \le 120.0\text{ km}$. Directional classification: Inflow if $k \in \text{india\_sectors}_d$ ($\text{TBVal} = +C w \exp(-d / 100)$), Outflow if $(k + 8) \bmod 16 \in \text{india\_sectors}_d$ ($\text{TBVal} = -C w \exp(-d / 100)$). 39 border animation nodes (`tbgeo.samples` $[lon, lat, nx, ny]$) evaluated via dot product $\Phi_j = u_j nx_j + v_j ny_j$: $\Phi_j > +0.25\text{ m/s}$ (crimson chevron inflow), $\Phi_j < -0.25\text{ m/s}$ (teal chevron outflow). 117 CAMS perimeter nodes for closed reanalysis flux integration.
   - **T9: PEPC AQI Scale & Colors (lines 392–436)**: Continuous half-open intervals ($BP_{i-1} < C \le BP_i$). Piecewise linear sub-index $I_p = ((I_{\text{high}} - I_{\text{low}}) / (BP_{\text{high}} - BP_{\text{low}})) \cdot (C_p - BP_{\text{low}}) + I_{\text{low}}$. Breakpoints: PM2.5 $[15, 35, 70, 140, 250, 350]$, PM10 $[75, 150, 250, 350, 450, 550]$, NO2 $[40, 80, 130, 180, 380, 580]$, SO2 $[60, 120, 220, 320, 800, 1600]$, CO $[2.5, 5, 7.5, 10, 25, 40]$, O3 $[65, 130, 195, 260, 450, 550]$. Operational ceiling cap: clamped to 500 when $C_p > BP_6$ (e.g. PM2.5 $> 350\ \mu\text{g/m}^3$). Composite AQI $= \max(I_{\text{PM2.5}}, I_{\text{PM10}})$. Statutory PEPC Hex colors: Good `#00B050`, Satisfactory `#92D050`, Moderate `#FFFF00`, Unhealthy Sensitive `#ED7D31`, Unhealthy `#FF0000`, Very Unhealthy `#7030A0`, Hazardous `#C00000`.
   - **T10: Temporal Aggregation & QC (lines 442–476)**: Zero/negative sanitization: $v \le 0 \to \text{null}$. 7h median spike filter: window $W_i = [i-3, i+3]$ ($|W_i| \ge 3$), spike flagged if $v_i > 4.0 \cdot M_i$ AND $v_i > 3.0 \cdot \text{ref}_p$. 3h logger hold filter: $i \ge 2$ index guard, if $v_i = v_{i-1} = v_{i-2} \ne \text{null}$, $v_i \to \text{null}$; **AQI is strictly exempt**. 75% completeness rule: required valid hours $\ge \max(1, \text{round}(0.75 \times H))$. Sub-hourly animation lerp: continuous fraction $f = fp - \lfloor fp \rfloor$, $\text{lerp}(a, b, f)$.
   - **T11: Geographic Projection & Greedy AABB Labeling (lines 483–513)**: Equirectangular Plate Carrée bounding box $[69.10^\circ\text{E}, 75.75^\circ\text{E}], [27.55^\circ\text{N}, 34.30^\circ\text{N}]$, standard parallel $31^\circ\text{N}$, $K_X = \cos(31^\circ) \approx 0.8571673007$. Scaling $S = W / ((\lambda_{\max} - \lambda_{\min}) K_X)$. Greedy collision-free search over 12 candidate offsets: $[0,0], [0,14], [0,-14], [16,0], [-16,0], [0,26], [0,-26], [30,8], [-30,8], [24,-20], [-24,-20], [0,38]$. If offset displacement $> 20.0\text{ px}$, draw leader line with terminal dot.

3. **Baseline Data Verification**:
   - `data/baseline/districts.json`: 41 districts. Centroids are formatted as `[lat, lon]` (e.g. Attock: `[33.669, 72.501]`), whereas `label` and `boundary` are `[lon, lat]` (e.g. Attock label: `[72.425, 33.501]`).
   - `data/baseline/stations.json`: 79 stations. 74 fixed (`mobile: False, network_type: "fixed"`), 5 mobile (`mobile: True, network_type: "mobile"`). Lahore has 13 stations (8 fixed, 5 mobile). Station 172 is named `Wazirabad` (`id: "172"`).
   - `data/baseline/airports.json`: 6 airports (`OPLA, OPFA, OPMT, OPST, OPBW, OPRK`). Wind arrays contain `None` values (telemetry dropouts), $0.0$ (calm), and active velocity components.
   - `data/baseline/baseline_data.json`: 216 hours from `2026-11-01 00:00` to `2026-11-09 23:00`. Contains `tbgeo.samples` (39 border nodes with `[lon, lat, nx, ny]`).

4. **`TEST_INFRA.md` & Backend Execution**:
   - `python tests/e2e/run_all_tests.py` runs 50 tests across 4 tiers in 2.27s with 100% pass rate.
   - Tests enforce exact tolerances ($\epsilon = 10^{-5}$), statutory PEPC integer calculations, boundary clamping, and zero crashes.
   - Pydantic v2 `UserCSVRowContract`: lat $[27.0, 35.0]$, lon $[69.0, 76.0]$, value $[0.0, 5000.0]$, wind speed $[0.0, 30.0]$, wind direction $[0.0, 360.0]$.

---

## 2. Features Discovered

| # | Category | Feature | Description | Inputs | Outputs | Error Behavior | Discovered Via |
|---|----------|---------|-------------|--------|---------|----------------|----------------|
| 1 | Geostatistics & Physics | T1: Discrete Geodesic IDW | Imputes pollutant concentration / wind $(u, v)$ for unmonitored districts using Haversine distance ($R = 6371\text{ km}$, $p = 2$) and singularity clamp ($d_0 = 5.0\text{ km}$). | Target coordinates $(\phi_t, \lambda_t)$, active monitored nodes with values $v_i$. | Imputed scalar concentration or wind component. | Returns `null` if monitored set is empty. Division by zero prevented by $d_0 = 5\text{ km}$ clamp. | `TRANSFORMATION_LOGIC_SPEC §2.1`, `TEST_INFRA §F03` |
| 2 | Geostatistics & Physics | T2: Anisotropic Wind-Steered Continuous IDW | Generates continuous 2D concentration surface modulated by wind velocity and plume dispersion physics ($\epsilon = 4.0\text{ px}$, $\cos\alpha$). Up to $+70\%$ downwind boost, floor $0.30$ upwind, saturation at $1.5\text{ m/s}$. Linear distance alpha taper between $45\text{ km}$ and $140\text{ km}$ ($235 \to 95$). | Query coordinates $(x, y)$, reporting stations with positions, concentrations, wind vectors $(u, v)$. | Continuous interpolated concentration and alpha opacity $[95, 235]$. | If $s_i \le 0.5\text{ m/s}$ or $d_i \le 2\text{ px}$, falls back to isotropic weight. Screen-Y inversion handled. | `TRANSFORMATION_LOGIC_SPEC §2.2`, `TEST_INFRA §F04` |
| 3 | Geostatistics & Physics | T3: Planar Screen Raster IDW | Legacy raster IDW kernel ($p = 3, \epsilon^2 = 0.25\text{ px}^2, 5\text{ px}$ grid). Dormant status with 0 invocations in production; superseded by T2. | Station screen coordinates and values. | 2D raster grid. | Superseded by T2. Documented for historical reference. | `TRANSFORMATION_LOGIC_SPEC §2.3` |
| 4 | Kinematics & QC | T4: Vector Wind Blending & Cartesian Conversion | Converts meteorological polar wind reports (speed, direction FROM) into Cartesian vectors $(u, v)$, and fuses station and airport reports with softening $\epsilon^2 = 400\text{ px}^2$. Enforces anemometer bounds $[0, 30]\text{ m/s}$ and Station 172 Wazirabad blacklist. | Polar wind speed $w_s$, direction $\theta$, station/airport coordinates. | Cartesian $(u, v)$ flow vectors pointing in direction wind blows TO. | Discards unphysical speeds ($>30\text{ m/s}$); unconditions exclusion of Station 172 Wazirabad due to $140^\circ$ vane offset. | `TRANSFORMATION_LOGIC_SPEC §2.4`, `TEST_INFRA §F05` |
| 5 | Source Apportionment | T5: Conditional Probability Function (CPF) Wind Rose | Evaluates 16 compass sectors ($22.5^\circ$ bins) for directional source enrichment exceeding criterion threshold $\tau = P_{75}(C)$ over pooled station-hours ($\mathcal{O}_d$). Excludes aerodynamic calm ($<0.50\text{ m/s}$). Enforces small-sample suppression ($N_k < 6$). | Hourly time-series of pollutant concentration and wind vector for district stations. | 16-sector CPF probabilities, calm ratio. Sector probability is `null` if $N_k < 6$. | Sectors with $N_k < 6$ are assigned `null` and rendered as muted 10px circular arc stubs. | `TRANSFORMATION_LOGIC_SPEC §2.5`, `TEST_INFRA §F06` |
| 6 | Transport Kinematics | T6: Inter-District Advection Mass Flux | Calculates pairwise inter-district mass transfer flux: $\text{Flux} = C_a w_a \cos(\Delta\theta) \exp(-d_{ab} / 100)$. Enforces maximum distance $d \le 180.0\text{ km}$, angular cone divergence $\Delta\theta \le 35.0^\circ$, calm cutoff $w_a \ge 0.5\text{ m/s}$. Physical dimension guard locks to PM2.5 when AQI selected. | Source/receptor coordinates, concentration $C_a$, wind vector $(u_a, v_a)$, pollutant key. | Hourly mass transport flux between district pairs. | Strictly disabled for `AQI` (returns empty set `[]` / `null` to prevent unphysical ordinal flux). | `TRANSFORMATION_LOGIC_SPEC §2.6`, `TEST_INFRA §F07` |
| 7 | Source Apportionment | T7: Receptor CPF Pathway Coupling & Transport Balance | Weights inter-district flux by receptor's CPF probability $\Omega$ for incoming wind sector. Defaults $\Omega = 0.25$ if receptor unmonitored or $N_k < 6$. Truncates candidate links to top 60. Computes Net Transport Balance (export - import). | Pairwise advection fluxes, receptor CPF roses. | Top 60 scored transport links and net district balances (exporter vs importer). | Fallback to isotropic $\Omega = 0.25$ prevents division or null failure. | `TRANSFORMATION_LOGIC_SPEC §2.7`, `TEST_INFRA §F08` |
| 8 | Border Intelligence | T8: Transboundary Cross-Border Index & Border Normals | Quantifies international transport across $120\text{ km}$ border belt ($\mathcal{B}$) based on India wind sectors. Computes dot product $\Phi_j = \mathbf{w}_j \cdot \mathbf{n}_j$ across 39 border nodes (`tbgeo.samples`). Crimson chevrons trigger when $\Phi_j > +0.25\text{ m/s}$; teal when $\Phi_j < -0.25\text{ m/s}$. | Border district readings, wind vectors, 39 border normal vector coordinates. | Regional inflow/outflow time series, 39 animated border chevron vectors. | Neutral/parallel flow when $|\Phi_j| \le 0.25\text{ m/s}$. 117 CAMS perimeter nodes for closed reanalysis. | `TRANSFORMATION_LOGIC_SPEC §2.8`, `TEST_INFRA §F09` |
| 9 | Regulatory Indexing | T9: PEPC Piecewise Linear AQI Scale & Colors | Computes statutory AQI sub-indices using continuous half-open intervals ($BP_{i-1} < C \le BP_i$) across 6 pollutants. Clamps sub-index to 500 when concentration exceeds Category 6 upper limit ($C > BP_6$). Composite AQI $= \max(I_{\text{PM2.5}}, I_{\text{PM10}})$. Maps to 7 statutory PEPC hex colors. | Measured concentration $C_p$, pollutant key. | Integer sub-index $I_p \in [0, 500]$, composite AQI, statutory hex color. | Values $> BP_6$ (e.g. PM2.5 $> 350\ \mu\text{g/m}^3$) clamped strictly at 500. Decimal dead-zone gaps eliminated by half-open design. | `TRANSFORMATION_LOGIC_SPEC §2.9`, `TEST_INFRA §F10` |
| 10 | Quality Control | T10: Temporal Aggregation, QC Filters & Lerp | Performs: (0) zero/negative purge ($v \le 0 \to \text{null}$); (1) 7h rolling median spike filter ($v_i > 4 M_i \land v_i > 3 \text{ref}_p \to \text{null}$); (2) 3h logger hold filter with $i \ge 2$ index guard ($v_i \to \text{null}$; AQI exempt); (3) 75% completeness rule ($\ge \max(1, \text{round}(0.75 H))$); (4) continuous sub-hourly animation lerp. | Raw hourly concentration stream, pollutant key, reference statutory limit. | Cleaned time series, spike diagnostic counters, sub-hourly interpolated snapshot. | Boundary precondition $i \ge 2$ prevents negative array indexing in Python/JS. AQI explicitly exempted from hold purging. | `TRANSFORMATION_LOGIC_SPEC §2.10`, `TEST_INFRA §F11` |
| 11 | Cartography & Collision | T11: Equirectangular Projection & Greedy AABB Labeling | Projects coordinates via Plate Carrée with standard parallel $31^\circ\text{N}$ ($K_X = \cos 31^\circ \approx 0.8571673007$). Resolves label collisions across 41 districts using greedy AABB search across 12 candidate offsets. Emits leader line if offset displacement $> 20\text{ px}$. | WGS84 coordinates $(\phi, \lambda)$, canvas dimensions, text bounding boxes. | Projected screen coordinates $(X, Y)$, non-overlapping label anchor positions. | If initial offset collides, cycles through priority offsets until first free slot; draws leader line if displaced. | `TRANSFORMATION_LOGIC_SPEC §2.11`, `TEST_INFRA §F12` |
| 12 | Workstation UI/UX | Zone 1: Top Command Bar | Institutional command strip displaying system identity, live telemetry sync pulse (`LIVE SYNC`, `T+04 min`, or `FALLBACK ARCHIVE`), provincial composite AQI badge with PEPC tier color, UTC+5 temporal clock, 9-pollutant statutory switcher buttons (`AQI, PM2.5, PM10, NO2, SO2, CO, O3, NO, NOX`), CSV ingest trigger, and QA drawer toggle. | System telemetry state, clock, active pollutant. | Interactive header bar, pollutant selection event, live ARIA announcements. | In live streaming, alerts trigger assertive ARIA live region when composite AQI enters Hazardous tier ($>400$) or hits 500 clamp. | `ORIGINAL_REQUEST §R3`, `UI_UX_SPECIFICATION §2.1` |
| 13 | Workstation UI/UX | Zone 2: Spatial Control Dock | 5-layer deck.gl stack toggles, transboundary mass-balance attribution split bar (cross-border easterly inflow vs. domestic emissions), and 41-district statutory ranking table sorted by exceedance with row selection centering/zooming map. | Layer visibility states, regional mass balance metrics, district ranking array. | Interactive toggles, attribution split meter, selectable district table. | Selecting district updates active viewport and opens Zone 4 receptor inspector. | `ORIGINAL_REQUEST §R3`, `UI_UX_SPECIFICATION §2.2` |
| 14 | Workstation UI/UX | Zone 3: Central Planimetric Map Canvas | Strict 2D planimetric MapLibre GL canvas (`pitch: 0, maxPitch: 0, bearing: 0, dragRotate: false, touchPitch: false`) with interleaved Deck.gl MapboxOverlay rendering 5 layers: IDW continuous surface, district choropleth with diagonal hatching, 3-state wind vector field, advection flux & border chevrons, stations & aerodromes. | MapLibre camera state, Deck.gl layer stack configurations. | Hardware-accelerated 2D geospatial visualization at 60 FPS. | Pitch and rotation permanently disabled; pan/zoom bounded to Punjab bounding box $[27.55, 34.30]^\circ\text{N}, [69.10, 75.75]^\circ\text{E}$. | `ORIGINAL_REQUEST §R2`, `UI_UX_SPECIFICATION §5` |
| 15 | Workstation UI/UX | Zone 4: Receptor Inspector & Telemetry Sidebar | Fixed 360px desktop sidebar rendering selected station/district metadata, 9-parameter statutory sub-index and QA table with 75% completeness enforcement, 16-sector CPF polar wind rose with small-sample suppression ($N_k < 6$) and calm exclusion, and 216-hour time-series QC chart highlighting 7h median spikes and 3h holds (AQI exempt). | Selected district/station ID, hourly observations, CPF sector probabilities. | Detailed telemetry cards, interactive CPF rose canvas, 216h sparkline chart. | Unmonitored districts display `IDW ESTIMATE` badge and diagonal hatch notice. Insufficient wind samples render muted stub. | `ORIGINAL_REQUEST §R3`, `UI_UX_SPECIFICATION §2.4` |
| 16 | Workstation UI/UX | Zone 5: Temporal Playback Scrubber Deck | Precision scrubber covering 216h baseline (2026-11-01 00:00 to 2026-11-09 23:00) with transport controls (Play/Pause, spacebar shortcut, $0.35\times, 0.8\times, 1.6\times$ speed stepper), horizon sparkline of provincial max AQI for rapid episode navigation, sub-hourly continuous lerp ($fp \in [0.00, 215.00]$), GPU update triggers decoupling scrubbing from CPU geometry re-parsing. | Timeline array, active $fp$, playback state. | Synchronous timeline scrubbing driving MapLibre/Deck.gl and UI snapshot. | Scrubbing past bounds clamped to $[0, 215]$. Frame drops clamped via monotonic timebase. | `ORIGINAL_REQUEST §R4`, `UI_UX_SPECIFICATION §4.1` |
| 17 | Data Normalization | Schema Trap 1: Centroid Inversion | Inverts district centroid coordinates from `[lat, lon]` in source data to `[lon, lat]` required by Deck.gl/GeoJSON, while leaving `label` and `boundary` coordinates (already `[lon, lat]`) unaltered. | District record with `centroid: [lat, lon]`, `label: [lon, lat]`, `boundary: [lon, lat]`. | Normalized district entity with all coordinates standardized to `[lon, lat]`. | Prevents inverted latitude/longitude displacement where districts render in the Indian Ocean. | `ORIGINAL_REQUEST §R5`, `TEST_INFRA §F21` |
| 18 | Data Normalization | Schema Trap 2: Aerodrome Wind Outage vs Calm | Explicitly differentiates airport METAR wind array `null` (telemetry dropouts) from aerodynamic calm ($0.0 \le w_s < 0.500\text{ m/s}$). | Airport hourly wind vector $(u, v)$ where components may be `null` or $0.0$. | 3-state vector display: missing telemetry dropout glyph (`null`), calm circle ($<0.50\text{ m/s}$), or directional vector ($\ge 0.50\text{ m/s}$). | Prevents misrepresenting station offline sensor outages as calm air. | `ORIGINAL_REQUEST §R5`, `TEST_INFRA §F15` |
| 19 | Data Normalization | Schema Trap 3: Station 172 Wazirabad Blacklist | Hard-blocks wind vector rendering and surface advection for Station 172 (Wazirabad) due to a persistent $140^\circ$ physical installation offset. Flags record as `ANEMOMETER BLACKLISTED (VANE OFFSET)`. | Station observation for Station 172. | Wind vectors suppressed; wind imputed via METAR or IDW interpolation. | Wind speed/direction for Station 172 discarded from vector fields and CPF roses. | `ORIGINAL_REQUEST §R5`, `TRANSFORMATION_LOGIC_SPEC §2.4` |
| 20 | Data Normalization | Schema Trap 4: Dynamic Station Count Computation | Dynamically calculates active fixed vs. mobile station counts (74 fixed circles, 5 mobile diamonds across 79 total stations) rather than relying on stale hardcoded metadata constants. | Full station directory list from `stations.json`. | Computed `{ total: 79, fixed: 74, mobile: 5 }`. | Adapts automatically to custom user CSV uploads and newly registered monitors. | `ORIGINAL_REQUEST §R5`, `TEST_INFRA §F02` |
| 21 | Data Normalization | Schema Trap 5: Estimation Flag Unification & Hatching | Unifies divergent boolean estimation flags (`est: true`, `is_monitored: false`, `station_count == 0`) into a canonical `is_estimated` property. Automatically triggers diagonal cross-hatching fill pattern on district polygons. | District metadata record. | Canonical `is_estimated: boolean` and diagonal hatch rendering trigger. | Ensures unmonitored districts (where concentrations are IDW-imputed) are clearly flagged to compliance officers. | `ORIGINAL_REQUEST §R5`, `TEST_INFRA §F21` |
| 22 | Data Ingestion | User CSV Ingestion Adapter | Supports multipart CSV file upload (`POST /api/v1/ingest/csv`), validates rows against `UserCSVRowContract`, sanitizes non-numeric and out-of-bounds records into dead-letter quarantine, and triggers dynamic 2D IDW surface recalculation. | Multipart form-data `.csv` file. | JSON ingestion summary `{ total, valid, quarantined, observations }` and dynamic surface. | Rows with invalid coordinates, missing required fields, or values $>5000\ \mu\text{g/m}^3$ quarantined with row-level error diagnostic. | `ORIGINAL_REQUEST §R5`, `TEST_INFRA §F19, §F20, §F32` |
| 23 | API Gateway | REST API Routes (`/api/v1/*`) | FastAPI backend routes delivering metadata (`/api/v1/meta/districts`, `/api/v1/meta/stations`), observations (`/api/v1/observations/current`, `/api/v1/observations/hourly`), spatial grids (`/api/v1/spatial/surface`), and analytics (`/api/v1/analytics/cpf`, `/api/v1/analytics/flux`, `/api/v1/analytics/transboundary`). | HTTP query parameters (pollutant, timestamp, district). | Schema-validated JSON responses adhering to OpenAPI 3.1. | Returns HTTP 422 on validation error, HTTP 404 on missing entity, with structured error JSON. | `SYSTEM_ARCHITECTURE §5.1`, `TEST_INFRA §F24–§F31` |
| 24 | API Gateway | Server-Sent Events (SSE) Live Feed | Lightweight real-time streaming endpoint (`GET /api/v1/stream/live`) emitting `event: hourly_update` JSON packets (<20 KB) with 15-second keepalive heartbeat comments (`: keepalive\n\n`). | Client HTTP connection with `Accept: text/event-stream`. | Continuous SSE stream advancing simulation hour and streaming latest telemetry. | Automatic reconnection; fallback to in-memory baseline when stream disconnected. | `SYSTEM_ARCHITECTURE §5.2`, `TEST_INFRA §F33` |
| 25 | Visual Design System | Institutional Styling & Design Tokens | Rigid 100vw x 100vh CSS Grid, scoped CSS Modules backed by `tokens.css` with WCAG 2.1 AAA contrast ($\ge 7.0:1$). Typography exclusively IBM Plex Sans, IBM Plex Sans Condensed, IBM Plex Mono (`tabular-nums`). 1px solid structural hairlines, 1.25px miter-joined inline SVGs. Strictly bans Tailwind CSS, consumer icon packs (lucide-react, heroicons), emojis, tilted 3D pitch, backdrop-filter blur, drop shadows. | Design tokens in `src/styles/tokens.css` and CSS Modules. | High-contrast, zero-slop scientific instrument console ("Operate" mode). | Banned dependencies or non-AAA text contrast fail build and test audits. | `ORIGINAL_REQUEST §R1`, `UI_UX_SPECIFICATION §1, §3` |

---

## 3. Edge Cases & Boundary Behaviors

| # | Feature | Input | Observed Behavior |
|---|---------|-------|-------------------|
| 1 | T1: Geodesic IDW | Target coincides with monitored node ($d = 0.0\text{ km}$). | Haversine distance $0.0\text{ km}$ is clamped to $d_0 = 5.0\text{ km}$. Weight is $w = 1 / 25 = 0.04$, preventing division by zero while preserving predominant contribution of local monitor ($245 \le val \le 250$). |
| 2 | T1: Geodesic IDW | Filtered monitored node list is empty ($\mathcal{M} = \emptyset$). | Returns `null` without throwing an unhandled exception. Downstream consumer falls back to Tier 3 NWP (ECMWF IFS) wind or baseline archive. |
| 3 | T2: Anisotropic IDW | Wind speed $w_s \le 0.50\text{ m/s}$ or distance $d \le 2.0\text{ px}$. | Skips anisotropic directional modulation and retains isotropic base weight $w_0 = 1 / (d^2 + 16)$. |
| 4 | T2: Anisotropic IDW | Upwind location ($\cos\alpha = -1.0$) with strong wind ($s = 5.0\text{ m/s}$). | Directional multiplier reaches floor clamp at $0.30$ (70% reduction in weight against wind), never producing negative or zero weights. |
| 5 | T2: Anisotropic IDW | Query point distance to nearest station $d_{\min} < 45\text{ km}$ vs $> 140\text{ km}$. | For $d_{\min} < 45\text{ km}$, alpha channel is 235 (near full opacity). For $d_{\min} > 140\text{ km}$, alpha channel decays to 95 (muted). Linear gradient between 45 and 140 km. |
| 6 | T4: Vector Wind | Wind speed $w_s = 30.1\text{ m/s}$ or error code `99.9`. | Discarded as unphysical ($w_s > 30.0\text{ m/s}$); vector set to `null` and flagged in QC diagnostics. |
| 7 | T4: Vector Wind | Wind speed $w_s = 0.0\text{ m/s}$, direction $\theta = 0.0^\circ$. | Polar to Cartesian conversion yields $u = 0.0\text{ m/s}, v = 0.0\text{ m/s}$. Direction reconstructs cleanly. |
| 8 | T4: Vector Wind | Station identifier is Station 172 (Wazirabad). | Wind vector is hard-blocked and excluded from all flow fields and roses due to $140^\circ$ physical vane offset; imputed via METAR or IDW. |
| 9 | T5: CPF Wind Rose | Wind speed $w_s = 0.49\text{ m/s}$ vs $w_s = 0.50\text{ m/s}$. | $w_s = 0.49\text{ m/s}$ is classified as aerodynamic calm and excluded from directional sector counts ($N_{\text{calm}}$ incremented). $w_s = 0.50\text{ m/s}$ is classified as active wind and included in directional bin. |
| 10 | T5: CPF Wind Rose | Sector $k$ has $N_k = 5$ valid hours (all exceeding $P_{75}$). | Even though 100% of samples exceeded threshold, $N_k < 6$ triggers small-sample suppression; $\text{CPF}_k$ returns `null` and renders as a neutral 10px circular arc stub. |
| 11 | T5: CPF Wind Rose | Multi-station district (Lahore with 13 stations). | $P_{75}$ criterion threshold $\tau$ and directional bins are evaluated over the pooled set of all valid station-hour observations ($N \approx 2,700$), preserving localized hotspots (Wagah, Town Hall) rather than flattening them with district averages. |
| 12 | T6: Advection Flux | Distance between districts $d_{ab} = 180.1\text{ km}$. | Distance exceeds maximum transport cutoff $180.0\text{ km}$; advection flux returns `null`. |
| 13 | T6: Advection Flux | Wind vector bearing diverges from trajectory by $\Delta\theta = 35.1^\circ$. | Angular divergence exceeds transport cone limit $35.0^\circ$; advection flux returns `null`. |
| 14 | T6: Advection Flux | Pollutant parameter selected is `'AQI'`. | Physical dimension guard trips: returns empty set `[]` / `null` because multiplying dimensionless ordinal index by physical velocity ($m/s$) is unphysical and violates mass conservation. Calculations lock to PM2.5. |
| 15 | T7: Receptor Coupling | Receptor district is unmonitored (`is_estimated = true`) or sector has $N_k < 6$. | Coupling coefficient $\Omega$ gracefully defaults to the isotropic null-hypothesis baseline of $0.25$. |
| 16 | T7: Receptor Coupling | Candidate transport links exceed 60 across the province. | Links are sorted in descending order of composite score and strictly truncated to the top 60 links (`slice(0, 60)`). |
| 17 | T8: Transboundary Index | Border normal vector dot product $\Phi_j = +0.250\text{ m/s}$ vs $+0.251\text{ m/s}$. | $\Phi_j \le +0.25\text{ m/s}$ is classified as neutral/parallel flow. $\Phi_j > +0.25\text{ m/s}$ triggers crimson transboundary inflow chevron vector. $\Phi_j < -0.25\text{ m/s}$ triggers teal outflow chevron. |
| 18 | T9: PEPC AQI Scale | Measured PM2.5 concentration $C = 15.0\ \mu\text{g/m}^3$ vs $15.001\ \mu\text{g/m}^3$. | Continuous half-open intervals ($BP_{i-1} < C \le BP_i$): $15.0$ falls in Category 0 (Good, AQI 50); $15.001$ enters Category 1 (Satisfactory, AQI $>50$). Eliminates decimal lookup dead zones. |
| 19 | T9: PEPC AQI Scale | Measured PM2.5 concentration $C = 350.0\ \mu\text{g/m}^3$ vs $350.1\ \mu\text{g/m}^3$. | $C = 350.0$ calculates to AQI 400 (Very Unhealthy). $C = 350.1$ triggers statutory operational ceiling clamp and is clamped strictly to 500 (Hazardous). |
| 20 | T9: PEPC AQI Scale | Gaseous pollutant (e.g. SO2 or NO2) has high sub-index ($I = 450$), while PM2.5 ($I = 150$) and PM10 ($I = 120$). | Statutory Rule: Composite AQI is strictly governed by particulate matter: $\text{AQI}_{\text{composite}} = \max(I_{\text{PM2.5}}, I_{\text{PM10}}) = 150$. Gaseous pollutants are monitored individually. |
| 21 | T10: Temporal QC | Raw measurement $v(t) = 0.0$ or $v(t) = -5.0$. | Zero and negative concentrations are converted to `null` during Step 0 sanitization prior to executing rolling filters. |
| 22 | T10: Temporal QC | Raw measurement at time index $i = 0$ equals subsequent values ($v_0 = v_1 = v_2$). | Logger hold filter checks precondition $i \ge 2$. At $i = 0$ and $i = 1$, the hold filter does NOT execute, preventing negative array indexing (`v[-1]`, `v[-2]`). At $i = 2$, hold condition triggers and $v_2$ is nulled. |
| 23 | T10: Temporal QC | Logger hold filter applied to integer `'AQI'` series ($150, 150, 150$). | AQI is strictly exempt from logger hold purging because discrete integer index values can legitimately remain constant over multiple hours. Value is preserved. |
| 24 | T10: Temporal QC | 24-hour aggregation window contains 17 valid hours vs 18 valid hours. | 75% completeness rule requires $\max(1, \text{round}(0.75 \times 24)) = 18$ hours. 17 valid hours returns `null`; 18 valid hours returns valid arithmetic mean. |
| 25 | T11: Greedy Placement | Text label overlaps existing bounding box at candidate offset $[0, 0]$. | Algorithm steps through priority list: $[0, 14], [0, -14], [16, 0], \dots$. First collision-free slot is assigned. If offset displacement $\sqrt{\Delta x^2 + \Delta y^2} > 20\text{ px}$, leader line with terminal node dot is drawn. |
| 26 | Data Normalization | Aerodrome METAR reports $u = \text{null}, v = \text{null}$. | Differentiated from calm ($0.0\text{ m/s}$); renders as missing telemetry dropout glyph rather than calm circle. |
| 27 | CSV Ingestion | User CSV upload contains row with latitude $26.9^\circ\text{N}$ or value $5000.1\ \mu\text{g/m}^3$. | Fails `UserCSVRowContract` Pydantic validation (lat must be $\ge 27.0$, value must be $\le 5000.0$). Row is rejected into dead-letter quarantine report; valid rows continue to be processed. |

---

## 4. Logic Chain

1. **Step 1 (Ground Truth from Monolith & Architecture Deconstruction)**:
   Analysis of `docs/SYSTEM_ARCHITECTURE.md` and `docs/ARCHITECTURE_OVERVIEW.md` reveals that the original prototype (`index.html`) was an unmaintainable 9.61 MB monolith containing 9.08 MB inlined data (`window.DATA`), 60+ global variables, 3 conflicting IDW routines, and unconstrained CPU canvas loops dropping frame rates to 12 FPS. The architecture deconstructs this into a 4-tier system: Tier 1 Ingestion, Tier 2 Storage/Analytics, Tier 3 FastAPI, and Tier 4 React/TypeScript Workstation.
   *(Reference: Observation 1, Observation 2)*

2. **Step 2 (Rigorous Mathematical Grounding in `docs/TRANSFORMATION_LOGIC_SPEC.md`)**:
   Every algorithmic equation across the 11 transforms was validated against physical units, boundary constraints, and dimensional constants. Specifically:
   - Geodesic IDW (T1) requires clamping distance to $d_0 = 5.0\text{ km}$ to prevent division by zero.
   - Anisotropic IDW (T2) accounts for screen-space Y inversion and incorporates a 45–140 km alpha taper to indicate spatial uncertainty.
   - Vector wind (T4) must convert meteorological direction (FROM) to advective flow (TO), with speed clamped to $\le 30\text{ m/s}$ and Station 172 Wazirabad blacklisted.
   - CPF roses (T5) require calm exclusion ($<0.50\text{ m/s}$), pooled station observations for multi-station districts (Lahore), and small-sample suppression ($N_k < 6$).
   - Advection flux (T6) enforces distance $\le 180\text{ km}$, cone $\le 35^\circ$, and an absolute physical guard locking to PM2.5 when AQI is selected.
   - Transboundary chevrons (T8) require normal vector dot product $\Phi_j > +0.25\text{ m/s}$ across 39 border nodes.
   - PEPC AQI (T9) requires continuous half-open intervals $(BP_{i-1}, BP_i]$, composite AQI governed strictly by particulates, and operational ceiling clamping to 500 when PM2.5 $> 350\ \mu\text{g/m}^3$.
   - Temporal QC (T10) requires zero-purge, 7h median spike filter, 3h logger hold with $i \ge 2$ index guard and AQI exemption, and the 75% completeness rule.
   - Projection (T11) requires Plate Carrée with standard parallel $31^\circ\text{N}$ ($K_X = \cos 31^\circ$) and greedy AABB collision search across 12 priority offsets with leader lines.
   *(Reference: Observation 2)*

3. **Step 3 (Reconciliation of Five Schema Traps from Actual Data)**:
   Inspection of `data/baseline/districts.json`, `stations.json`, `airports.json`, and `baseline_data.json` confirmed all 5 schema traps:
   - Trap 1: `districts.json` stores centroids as `[lat, lon]` (e.g. `[33.669, 72.501]`) while labels and boundaries are `[lon, lat]`. Failure to invert centroids causes map markers to render in the Indian Ocean.
   - Trap 2: `airports.json` contains explicit `None` values for missing observations alongside `0.0` for aerodynamic calm. They must be rendered with distinct visual glyphs.
   - Trap 3: Station 172 (Wazirabad) exists in `stations.json` with `wind_valid: 0` in its QA summary and must be hard-blocked from wind rendering due to its $140^\circ$ vane offset.
   - Trap 4: `stations.json` contains 74 fixed and 5 mobile stations across 79 total stations, with 13 stations in Lahore. Counts must be computed dynamically.
   - Trap 5: Estimation status is represented via divergent flags (`est: true`, `is_monitored: false`, `station_count == 0`), which must be normalized to `is_estimated` with diagonal hatching on unmonitored district polygons.
   *(Reference: Observation 3)*

4. **Step 4 (Visual Design, Typography & Accessibility Standards)**:
   Review of `ORIGINAL_REQUEST.md` and `docs/UI_UX_SPECIFICATION.md` confirms that the interface must be an institutional atmospheric physics workstation:
   - Rigid 100vw x 100vh CSS Grid divided into 5 zones.
   - Strictly scoped CSS Modules backed by `tokens.css` with WCAG 2.1 AAA text contrast ($\ge 7.0:1$).
   - Exclusively IBM Plex typography (IBM Plex Sans, IBM Plex Sans Condensed, IBM Plex Mono) with `tabular-nums` formatting on all numeric readouts.
   - Strict ban on Tailwind CSS, consumer icon packs (`lucide-react`, `heroicons`), emojis, 3D tilted map perspective, backdrop-filter blur, or drop shadows; use 1.25px miter-joined inline SVGs or deck.gl primitives and 1px solid structural hairlines.
   - Central map canvas must be permanently 2D planimetric (`pitch: 0, maxPitch: 0, bearing: 0, dragRotate: false, touchPitch: false`).
   *(Reference: Observation 1, Observation 4)*

5. **Step 5 (Validation via Test Infrastructure & Zero Regressions)**:
   Verification of `TEST_INFRA.md` and successful execution of `tests/e2e/run_all_tests.py` confirms that 50/50 backend tests across 4 tiers execute in 2.27s with 100% pass rate. Every mathematical formula, boundary clamp, and schema contract has an existing oracle test. All future implementations must preserve 100% pass rate on this test suite.
   *(Reference: Observation 4)*

---

## 5. Caveats

- **Legacy Transform 3 (Planar Screen Raster IDW)**: While Transform 3 is documented in `docs/TRANSFORMATION_LOGIC_SPEC.md §2.3`, it has 0 active invocations and is superseded by Transform 2 (Anisotropic IDW). Implementations should bypass T3.
- **Backend Service URL**: Production backend queries `http://127.0.0.1:9000/api/v1/*`. In offline development or when the FastAPI backend is not running, the dashboard must cleanly fallback to in-memory baseline fixtures (`baseline_data.json` and `airports.json`).
- **Font Availability**: IBM Plex fonts (`IBM Plex Sans`, `IBM Plex Sans Condensed`, `IBM Plex Mono`) must be imported via `@font-face` or Google Fonts in `index.html`/CSS tokens, and generic fallbacks must be strictly bounded to system sans/monospace without introducing unapproved font families.

---

## 6. Conclusion

The specification mining survey is complete. All mathematical, cartographic, regulatory, architectural, UI/UX, and data normalization requirements have been extracted, cross-referenced with production code and baseline data, and verified against the backend test suite.

Key requirements for subsequent implementation phases:
1. **Workstation Shell**: 100vw x 100vh rigid CSS Grid with 5 Zones, scoped CSS Modules, WCAG 2.1 AAA contrast ($\ge 7.0:1$), IBM Plex typography, `tabular-nums`, and 1px hairlines.
2. **Planimetric Canvas**: Strictly 2D MapLibre GL (`pitch: 0, dragRotate: false`) with 5-layer Deck.gl stack (IDW surface, district choropleth with diagonal hatching, 3-state wind field, advection flux with 39 crimson/teal border chevrons, 79 stations/aerodromes).
3. **PEPC Scale & Mathematical Exactness**: Continuous half-open piecewise linear AQI scale clamped at 500 when PM2.5 $> 350\ \mu\text{g/m}^3$, particulate-governed composite AQI, $d \le 180\text{ km}$ and cone $\le 35^\circ$ flux with physical dimension guard locking to PM2.5, 16-sector CPF rose with calm exclusion and $N_k < 6$ suppression, and temporal QC (7h median spike, 3h logger hold with $i \ge 2$ index guard).
4. **Data Normalization**: `dataNormalizer.ts` addressing all 5 schema traps (centroid inversion, aerodrome null vs calm, Wazirabad blacklist, dynamic station counts, unified estimation hatching).
5. **Quality Gate**: Clean TypeScript compilation and 50/50 backend E2E test pass rate (`python tests/e2e/run_all_tests.py`).

---

## 7. Verification Method

1. **Verify Backend E2E Test Suite**:
   Execute the automated E2E test runner to ensure 100% pass rate:
   ```powershell
   python tests/e2e/run_all_tests.py
   ```
   *Expected outcome*: 50/50 tests pass across Tiers 1–4 in $< 5$ seconds with exit code 0.

2. **Verify Baseline Data Invariants**:
   Run the following verification script to confirm schema trap invariants:
   ```powershell
   python -c "
   import json
   with open('data/baseline/districts.json') as f:
       d = json.load(f)
       assert len(d) == 41
       # Centroid is [lat, lon], label is [lon, lat]
       assert d[0]['centroid'][0] > d[0]['centroid'][1]  # Lat ~33.6 > Lon ~72.5
       assert d[0]['label'][0] > d[0]['label'][1]        # Lon ~72.4 > Lat ~33.5
   with open('data/baseline/stations.json') as f:
       s = json.load(f)
       assert len(s) == 79
       fixed = sum(1 for x in s if not x.get('mobile'))
       mobile = sum(1 for x in s if x.get('mobile'))
       assert fixed == 74 and mobile == 5
       wz = next(x for x in s if x['name'] == 'Wazirabad')
       assert wz['qa_summary']['wind_valid'] == 0
   with open('data/baseline/airports.json') as f:
       a = json.load(f)
       assert len(a) == 6
       assert any(None in x['u'] for x in a)  # Outages exist
   print('ALL BASELINE DATA INVARIANTS VERIFIED SUCCESSFULLY!')
   "
   ```

3. **Invalidation Conditions**:
   - Any backend test failure in `tests/e2e/run_all_tests.py`.
   - Modifying centroid coordinates without inverting `[lat, lon]` to `[lon, lat]`.
   - Allowing Station 172 Wazirabad to render wind vectors.
   - Calculating advection mass transport flux on dimensionless `AQI`.
   - Permitting 3D pitch/tilt on the central map canvas.
   - Introducing unapproved dependencies (`tailwindcss`, `lucide-react`, `heroicons`, emojis).
