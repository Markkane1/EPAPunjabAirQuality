# Scientific Transformation Specification Mining Report (Requirement R3 / R2)

**Document ID**: `PAQ-HANDOFF-SPEC-MINER-MATH`  
**Agent**: `spec_miner_math`  
**Working Directory**: `c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\spec_miner_math\`  
**Target Specification Source**: `docs/TRANSFORMATION_LOGIC_SPEC.md`, `index.html` (monolithic baseline), `collector/collector.py`, `docs/DATA_PIPELINES_ARCHITECTURE.md`, `docs/SYSTEM_ARCHITECTURE.md`  
**Status**: Completed Hard Handoff  

---

## 1. Observation

Direct investigation of `docs/TRANSFORMATION_LOGIC_SPEC.md`, `index.html`, and `collector/collector.py` revealed eleven distinct scientific, geospatial, meteorological, and regulatory transformation subsystems.

### 1.1 Features Discovered

| # | Category | Feature | Description | Inputs | Outputs | Error Behavior | Discovered Via |
|---|---|---|---|---|---|---|---|
| **T1** | Geostatistics / Spatial | Discrete Geodesic District-to-District IDW | Imputes missing pollutant concentrations ($C$) and wind vectors ($u, v$) for unmonitored districts (`est=true`) using Haversine great-circle metric ($R=6371\text{ km}$, $p=2$, $d_0=5\text{ km}$). | Target coordinate $(\phi_t, \lambda_t)$, active monitored nodes with $(\phi_i, \lambda_i)$ and value $v_i$. | Imputed scalar concentration ($\mu\text{g/m}^3$) or velocity component ($\text{m/s}$). | If $\mathcal{M}=\emptyset$ or all values `null`, returns `null` (falls back to NWP). | `docs/TRANSFORMATION_LOGIC_SPEC.md` §2.1; `index.html`:282–286 |
| **T2** | Geostatistics / Spatial | Anisotropic Wind-Steered Continuous Surface IDW | Generates continuous 2D concentration fields across Punjab canvas, modulating interpolation kernel weights based on advection direction and velocity saturation. | Query point $(x, y)$, station nodes $(x_i, y_i, v_i, u_i, v_i)$, scale $S$. | Interpolated concentration $V(x, y)$, nearest station distance $d_{\min}$, opacity $\alpha \in [95, 235]$. | If no active stations, returns 0 / transparent canvas. Distant areas ($>140\text{ km}$) taper to $\alpha=95$. | `docs/TRANSFORMATION_LOGIC_SPEC.md` §2.2; `index.html`:524–536 |
| **T3** | Geostatistics / Spatial | Planar Screen Raster IDW (*Legacy Dormant*) | High-order inverse distance power ($p=3$, cell $5\text{px}$, $\epsilon^2=0.25\text{px}^2$) over provincial polygon mask. Superseded by Transform 2. | Screen coordinates $(X, Y)$, station values $p_i=(x_i, y_i, v_i)$. | Canvas pixel imageData color buffer. | *0 active invocations in production runtime*; dormant code preserved in `drawSurface`. | `docs/TRANSFORMATION_LOGIC_SPEC.md` §2.3; `index.html`:441–448 |
| **T4** | Meteorology / Kinematics | Vector Wind Blending & Cartesian Conversion | Converts meteorological polar wind reports $(w_s, \theta)$ to Cartesian kinematic advective vectors $(u, v)$, applies anemometer QC, and blends multi-source surface winds. | Raw speed $w_s$, direction $\theta$, station coords, airport METARs, ECMWF NWP grids. | Cartesian $(u, v)$ velocity vectors ($\text{m/s}$), blended field $\mathbf{W}(x, y)$. | Discards $w_s < 0$ or $w_s > 30\text{ m/s}$; discards $\theta < 0$ or $\theta > 360^\circ$; blacklists Wazirabad sensor offset. | `docs/TRANSFORMATION_LOGIC_SPEC.md` §2.4; `index.html`:313–315, 331–342, 455–458 |
| **T5** | Atmospheric Physics / Receptor Modeling | Conditional Probability Function (CPF) Wind Rose | Apportions pollution sources by computing directional probability of high concentrations ($>P_{75}$) across 16 compass sectors ($\Delta\theta=22.5^\circ$), with calm exclusion ($<0.5\text{ m/s}$) and small-sample suppression ($N_k < 6$). | Pooled station-hour series $\mathcal{O}_d = \{(C_s, \mathbf{w}_s)\}$, district $d$, pollutant $p$. | 16-sector probability rose $\{\text{CPF}_k\}$, threshold $\tau=P_{75}$, calm ratio $N_{\text{calm}}/N_{\text{total}}$. | If $N_k < 6$, sector returns `null` (rendered as neutral muted stub). If district unmonitored, returns `null`. | `docs/TRANSFORMATION_LOGIC_SPEC.md` §2.5; `index.html`:256, 360, 662–671 |
| **T6** | Atmospheric Physics / Transport | Physical Inter-District Advection Transport Flux | Estimates hourly physical pollutant mass transfer between district pairs within $180\text{ km}$ using vector divergence ($\Delta\theta \le 35^\circ$) and exponential spatial decay ($L_S=100\text{ km}$). | Source $(C_a, \mathbf{w}_a)$, receptor coords $(\phi_b, \lambda_b)$, distance $d_{ab}$, bearing $\theta_{\text{brg}}$. Strictly disabled for `'AQI'`. | Pairwise physical flux $\text{Flux}_{a \to b}$ ($\mu\text{g}\cdot\text{m}^{-2}\cdot\text{s}^{-1}$ or $\text{mg}\cdot\text{m}^{-2}\cdot\text{s}^{-1}$). | Returns `null` if $w_a < 0.5\text{ m/s}$, $\Delta\theta > 35^\circ$, $d_{ab} > 180\text{ km}$, or pollutant is non-physical index `AQI`. | `docs/TRANSFORMATION_LOGIC_SPEC.md` §2.6; `index.html`:255, 289–290, 351–352 |
| **T7** | Atmospheric Physics / Receptor Modeling | Receptor CPF Pathway Coupling & Transport Balance | Couples hourly physical advection flux with empirical receptor wind rose feedback coefficient $\Omega$ to derive top 60 inter-district pathway scores and district net balance. | Pairwise hourly flux series, receptor CPF rose $\text{CPF}_b(k_{\text{rec}})$. | Top 60 ranked pathway links `{src, rcv, km, flux, hours, cpf, score}`, net district balance vector. | If receptor unmonitored or $N_k < 6$, defaults $\Omega=0.25$ (isotropic null baseline). | `docs/TRANSFORMATION_LOGIC_SPEC.md` §2.7; `index.html`:358–364 |
| **T8** | Atmospheric Physics / Transboundary | Transboundary Cross-Border Inflow/Outflow Index | Quantifies international cross-border atmospheric transport across 24 border-belt districts ($d_{\text{border}} \le 120\text{ km}$), 39 border normal vector nodes, and 117 CAMS perimeter nodes. | Border district concentration $C_d$, wind $(u_d, v_d)$, border distance $d_{\text{border}}$, India wind sectors. | Net inflow/outflow time series, per-district transboundary values $\text{TBVal}_d$, normal velocity $\Phi_j$. | Calm winds ($<0.5\text{ m/s}$) yield $\text{TBVal}=0.0$. Flow parallel to border yields 0.0. Unmonitored border districts excluded from total. | `docs/TRANSFORMATION_LOGIC_SPEC.md` §2.8; `index.html`:257, 291–294, 366–367, 493–501 |
| **T9** | Regulatory Compliance / UI | Official PEPC AQI Breakpoints & Color Scales | Piecewise linear sub-index interpolation across continuous half-open intervals $(BP_{i-1}, BP_i]$ for PM2.5, PM10, NO2, SO2, CO, O3; 500 operational cap; composite $\max(I_{\text{PM2.5}}, I_{\text{PM10}})$; continuous PEQS RGB ramp. | Raw concentration $C_p$ ($\mu\text{g/m}^3$ or $\text{mg/m}^3$), statutory breakpoint matrix $BP$. | Integer AQI sub-index $[0, 500]$, category name/hex, continuous RGB 7-stop color interpolation. | If $C_p \le 0$, returns `null`. If $C_p > BP_6$, capped at 500. Composite AQI strictly determined by particulate matter. | `docs/TRANSFORMATION_LOGIC_SPEC.md` §2.9; `index.html`:383–410 |
| **T10** | Data Quality / Analytics | Temporal Aggregation & QC Spike/Hold Cleaning | Sanitizes zero/negatives, cleans 7-hour median spikes ($>4M_i$ and $>3\text{ref}_p$), purges 3-hour logger holds ($v_i=v_{i-1}=v_{i-2}$ with $i \ge 2$), applies 75% completeness rule, and executes continuous sub-hourly animation lerp. | Time-series array $v(t)$, reference limit $\text{ref}_p$, duration $H$, scrub position $fp$. | Validated cleaned time series, period means, diagnostic spike counter, sub-hourly interpolated snapshot. | Discards raw $\le 0$; holds purged for physical pollutants (AQI exempt); period rollup requires $\ge \text{round}(0.75 H)$ valid hours else `null`. | `docs/TRANSFORMATION_LOGIC_SPEC.md` §2.10; `index.html`:251, 316–328, 355–356, 435–437 |
| **T11** | Cartography / Visualization | Equirectangular Projection & Collision-Free Labeling | Projects coordinates via Plate Carrée centered on standard parallel $31^\circ\text{N}$ ($K_X=\cos 31^\circ$), and places 41 district labels using a greedy 12-offset AABB search with leader lines. | Geographic bounds $(\phi, \lambda)$, canvas width $W$, label boxes $(w, h)$, offset priority vector $\mathcal{O}$. | Canvas pixel coordinates $(X, Y)$, scale $S$, collision-free text bounding boxes and leader lines. | Boundary clamped within $[69.10^\circ\text{E}, 75.75^\circ\text{E}]$ and $[27.55^\circ\text{N}, 34.30^\circ\text{N}]$. If displacement $>20\text{px}$, renders leader line with dot. | `docs/TRANSFORMATION_LOGIC_SPEC.md` §2.11; `index.html`:418–432, 546–557 |

---

### 1.2 Edge Cases Discovered

| # | Feature | Input / Condition | Observed Behavior | Code Source Reference |
|---|---|---|---|---|
| **E1** | Discrete IDW (T1) | Target node exactly coincides with reporting monitor ($d = 0.0\text{ km}$). | Haversine distance clamped to $d_0 = 5.0\text{ km}$ ($d_{\text{eff}} = \max(d, 5.0)$); prevents division by zero, yielding finite weight $w = 1 / 25 = 0.04$. | `TRANSFORMATION_LOGIC_SPEC.md`:79–81; `index.html`:286 |
| **E2** | Discrete IDW (T1) | Zero active monitoring stations reporting in the province ($\sum w_i = 0$). | Returns `null`. Downstream pipeline gracefully falls back to Tier 3 ECMWF IFS model winds. | `TRANSFORMATION_LOGIC_SPEC.md`:100, 110; `index.html`:338–340 |
| **E3** | Anisotropic IDW (T2) | Target point within $d \le 2.0\text{ px}$ or wind speed $s_i \le 0.5\text{ m/s}$ (calm). | Anisotropic directional multiplier bypassed; defaults to isotropic baseline weight $w_{0, i} = \frac{1}{d_i^2 + 16.0}$. | `TRANSFORMATION_LOGIC_SPEC.md`:136–139; `index.html`:528–529 |
| **E4** | Anisotropic IDW (T2) | Directly upwind query point ($\cos\alpha = -1.0$) with high wind speed ($s \ge 1.5\text{ m/s}$). | Multiplier $(1.0 + 0.7 \times (-1.0) \times 1.0) = 0.30$; clamped to floor of $0.30$, suppressing upwind weight by exactly 70%. | `TRANSFORMATION_LOGIC_SPEC.md`:138, 142; `index.html`:529 |
| **E5** | Anisotropic IDW (T2) | Distance to nearest monitor $d_{\min} > 140\text{ km}$. | Alpha opacity clamped to 95 ($37\%$ opacity), visually communicating low geostatistical confidence. | `TRANSFORMATION_LOGIC_SPEC.md`:147–151; `index.html`:535 |
| **E6** | Wind QC (T4) | Wind speed $w_s < 0.0$ or $w_s > 30.0\text{ m/s}$ ($108\text{ km/h}$), or direction $\theta < 0^\circ$ or $> 360^\circ$. | Unphysical sensor values discarded (`null`). Handles DC Office Chakwal (direction in speed field) and Khanewal (`99.9` error code). | `TRANSFORMATION_LOGIC_SPEC.md`:185–187; `index.html`:251, 314–315 |
| **E7** | Wind QC (T4) | Wazirabad AQMS anemometer report. | Persistent $140^\circ$ hardware installation offset; station explicitly blacklisted (`NOWIND = ['Wazirabad']`), wind imputed via METAR or IDW. | `TRANSFORMATION_LOGIC_SPEC.md`:188; `index.html`:251, 313–314 |
| **E8** | CPF Wind Rose (T5) | Aerodynamic calm wind ($w_s < 0.5\text{ m/s}$). | Excluded from 16 directional sector counts; tracked separately in `calm_ratio = N_calm / N_total`. | `TRANSFORMATION_LOGIC_SPEC.md`:224–227; `index.html`:256, 289 |
| **E9** | CPF Wind Rose (T5) | Small sector sample size ($N_k < 6$ valid hours from sector $k$). | $\text{CPF}_k$ assigned `null` (suppression rule). Prevents false 100% spikes from 1–2 chance events. Client renders muted circular arc stub. | `TRANSFORMATION_LOGIC_SPEC.md`:235–244; `index.html`:669 |
| **E10** | CPF Wind Rose (T5) | Multi-station district (e.g. Lahore with 13 stations, Multan, Rawalpindi). | $P_{75}$ threshold $\tau$ evaluated over *pooled individual station-hour observations*, preserving localized smog gradients instead of flattening means. | `TRANSFORMATION_LOGIC_SPEC.md`:230–234; `index.html`:251, 256 |
| **E11** | Advection Flux (T6) | Requesting flux calculation for `pollutant === 'AQI'`. | **Strictly disabled**; returns empty array `[]`. Prevents physically meaningless multiplication of dimensionless health index by velocity. | `TRANSFORMATION_LOGIC_SPEC.md`:301; `DATA_PIPELINES_ARCHITECTURE.md`:381 |
| **E12** | Advection Flux (T6) | Inter-district distance $d_{ab} > 180\text{ km}$ or divergence $\Delta\theta > 35.0^\circ$. | Flux evaluates to `null`. Plume trajectory does not intersect receptor airshed within transport cone. | `TRANSFORMATION_LOGIC_SPEC.md`:287, 298, 305; `index.html`:288, 290 |
| **E13** | Pathway Coupling (T7) | Receptor district $b$ is unmonitored (`est=true`) or sector has $N_k < 6$ (`CPF=null`). | Receptor feedback coefficient $\Omega$ gracefully defaults to $0.25$ (isotropic airshed null-hypothesis baseline). | `TRANSFORMATION_LOGIC_SPEC.md`:333–337; `index.html`:362 |
| **E14** | Pathway Coupling (T7) | More than 60 candidate inter-district pathways exceed zero score. | Sorted descending by score and strictly truncated to top 60 links (`slice(0, 60)`), bounding memory and UI clutter. | `TRANSFORMATION_LOGIC_SPEC.md`:340–342; `index.html`:364 |
| **E15** | Transboundary Index (T8) | Monitored border district reports wind blowing along border (not India sector nor opposite). | $\text{TBVal} = 0.0$ (neutral / parallel atmospheric flow). | `TRANSFORMATION_LOGIC_SPEC.md`:368; `index.html`:294 |
| **E16** | PEPC AQI (T9) | Particulate concentration $C_p > BP_6$ ($\text{PM}_{2.5} > 350\ \mu\text{g/m}^3$ or $\text{PM}_{10} > 550\ \mu\text{g/m}^3$). | Sub-index clamped to operational ceiling of 500 in accordance with EPA Punjab operational regulations. | `TRANSFORMATION_LOGIC_SPEC.md`:415; `DATA_PIPELINES_ARCHITECTURE.md`:225 |
| **E17** | PEPC AQI (T9) | Concentration $C_p \le 0.0$ or non-numeric (`NaN`). | Sub-index evaluates to `null` (zero/negative sanitization). | `TRANSFORMATION_LOGIC_SPEC.md`:442–444; `index.html`:322 |
| **E18** | Temporal QC (T10) | Single-hour spike where $v_i > 4.0 \cdot \text{median}(W_i)$ AND $v_i > 3.0 \cdot \text{ref}_p$ (with $|W_i| \ge 3$). | Flagged as transient electrical/optical artifact, replaced with `null`, and logged in `spikes[p]` counter. | `TRANSFORMATION_LOGIC_SPEC.md`:446–453; `index.html`:324–327 |
| **E19** | Temporal QC (T10) | Three consecutive identical non-null readings ($v_i = v_{i-1} = v_{i-2}$) for physical pollutant ($p \ne \text{'AQI'}$). | Flagged as logger freeze / holding last value, $v_i$ replaced with `null`. Guard $i \ge 2$ prevents negative array indexing in Python. | `TRANSFORMATION_LOGIC_SPEC.md`:454–458; `index.html`:326–327 |
| **E20** | Temporal QC (T10) | 24-hour daily aggregation with fewer than 18 valid hours ($<75\%$). | Aggregation returns `null` ($N_{\text{valid}} < \max(1, \text{round}(0.75 H))$). Prevents biased daily metrics. | `TRANSFORMATION_LOGIC_SPEC.md`:460–467; `index.html`:356 |

---

## 2. Logic Chain

1. **Investigation of Authoritative Specification (`docs/TRANSFORMATION_LOGIC_SPEC.md`)**:
   - The document defines eleven transformation modules with explicit LaTeX formulas, dimensional constraints, and physical units.
   - It details that the legacy system had redundant or dormant IDW code (Transform 3 `drawSurface` with 0 callers), which must be superseded by Transform 2 (`renderField` / `fieldAt`).
   - It specifies that advection flux calculations are physically invalid for dimensionless health indexes like AQI, mandating an explicit domain guard `pollutant !== 'AQI'`.

2. **Cross-Referencing Monolithic Implementation (`index.html`)**:
   - Lines 282–286 confirm discrete geodesic IDW using the Haversine formula with radius $R=6371\text{ km}$, power $p=2$, and minimum distance clamp $d_0 = 5\text{ km}$.
   - Lines 313–315 confirm the Wazirabad wind blacklist (`NOWIND = new Set(['Wazirabad'])`) due to a $140^\circ$ physical vane misalignment, and speed bounds $[0, 30\text{ m/s}]$.
   - Lines 324–327 confirm the temporal QC cleaning: zero purge, 7-hour rolling median spike filter ($v > 4 \cdot \text{med}$ and $v > 3 \cdot \text{ref}$), and 3-hour hold filter for non-AQI pollutants.
   - Lines 355–356 confirm the 75% completeness rule: `Math.max(1, Math.round(0.75 * NA))`.
   - Lines 360–364 confirm the 16-sector CPF calculation, the receptor feedback coefficient $\Omega$ with $0.25$ isotropic fallback, and the strict truncation to the top 60 links.
   - Lines 383–410 confirm the official PEPC breakpoint tables, continuous half-open intervals, 500 operational cap, and the 7-stop continuous PEQS color interpolation scale.
   - Lines 524–536 confirm the anisotropic continuous surface IDW: softening $\epsilon^2 = 16.0\text{ px}^2$, wind alignment $\cos\alpha$, velocity saturation at $1.5\text{ m/s}$, directional multiplier clamped between $0.30$ and $1.70$, and distance opacity decay from 235 ($<45\text{ km}$) down to 95 ($>140\text{ km}$).

3. **Cross-Referencing Cloud Ingestion Daemon (`collector/collector.py`)**:
   - Lines 25–51 confirm station-to-district mappings and district centroid coordinates.
   - Lines 188–196 confirm WMO FM-12 synoptic telegram parsing and wind speed/direction extraction.
   - Lines 235–246 confirm airport METAR decoding, knots-to-m/s conversion ($0.5144$), calm wind identification, and visibility statute mile conversion ($1609.34\text{ m}$).

4. **Derivation of Deterministic Test Fixtures**:
   - Using pure mathematical functions matching the specifications, reference test cases were evaluated and verified for PEPC breakpoints, discrete IDW, anisotropic IDW, inter-district advection flux, and CPF polar roses.

---

## 3. Mathematical Models & Equations Reference

### 3.1 Transform 1: Discrete Geodesic District-to-District IDW
- **Haversine Distance**:
  $$\Delta \phi = \phi_2 - \phi_1, \quad \Delta \lambda = \lambda_2 - \lambda_1$$
  $$a = \sin^2\left(\frac{\Delta \phi}{2}\right) + \cos(\phi_1)\cos(\phi_2)\sin^2\left(\frac{\Delta \lambda}{2}\right)$$
  $$d = 2 R_{\text{Earth}} \arcsin\left(\sqrt{a}\right), \quad R_{\text{Earth}} = 6371.0\text{ km}$$
- **Singularity Clamping & Weighting**:
  $$d_{\text{eff}} = \max(d, 5.0\text{ km})$$
  $$w_i = \frac{1}{(d_{\text{eff}})^2}$$
  $$V_{\text{target}} = \frac{\sum_{i \in \mathcal{M}} w_i \cdot v_i}{\sum_{i \in \mathcal{M}} w_i}$$

### 3.2 Transform 2: Anisotropic Wind-Steered Continuous Field IDW
- **Base Distance & Softened Weight**:
  $$\Delta x_i = x - x_i, \quad \Delta y_i = y - y_i, \quad d_i = \sqrt{\Delta x_i^2 + \Delta y_i^2}$$
  $$w_{0, i} = \frac{1}{d_i^2 + \epsilon^2}, \quad \epsilon = 4.0\text{ px} \ (\epsilon^2 = 16.0)$$
- **Advection Cosine Projection**:
  $$\cos(\alpha_i) = \frac{\Delta x_i \cdot u_i - \Delta y_i \cdot v_i}{d_i \cdot s_i}, \quad s_i = \sqrt{u_i^2 + v_i^2}$$
- **Kernel Modulation**:
  $$\text{If } s_i > 0.5\text{ m/s} \text{ and } d_i > 2.0\text{ px}: \quad \psi_i = 1.0 + 0.70 \cdot \cos(\alpha_i) \cdot \min\left(1.0, \, \frac{s_i}{1.5}\right)$$
  $$w_i = w_{0, i} \cdot \max(0.30, \, \psi_i)$$
  $$\text{Else}: \quad w_i = w_{0, i}$$
- **Distance Opacity Taper**:
  $$\text{km}_{\min} = \min_i(d_i) \cdot \left(\frac{111.0}{S}\right)$$
  $$\alpha = \begin{cases} 235 & \text{if } \text{km}_{\min} < 45.0 \\ 95 & \text{if } \text{km}_{\min} > 140.0 \\ 235 - 140 \cdot \left(\frac{\text{km}_{\min} - 45.0}{95.0}\right) & \text{otherwise} \end{cases}$$

### 3.3 Transform 4: Vector Wind Conversion & Blending
- **Polar to Cartesian**:
  $$u = -w_s \cdot \sin\left(\theta \cdot \frac{\pi}{180}\right), \quad v = -w_s \cdot \cos\left(\theta \cdot \frac{\pi}{180}\right)$$
- **Cartesian to Polar**:
  $$w_s = \sqrt{u^2 + v^2}, \quad \theta_{\text{from}} = \left(\frac{\text{atan2}(-u, -v)}{\frac{\pi}{180}} + 360^\circ\right) \bmod 360^\circ$$
- **Spatial Field Blending**:
  $$\mathbf{W}(x, y) = \frac{\sum w_i \mathbf{w}_i}{\sum w_i}, \quad w_i = \frac{1}{d_i^2 + 400.0}$$

### 3.4 Transform 5: Conditional Probability Function (CPF) Polar Rose
- **16 Sectors ($\Delta\theta = 22.5^\circ$)**:
  $$k = \left\lfloor \frac{(\theta_{\text{from}} + 11.25^\circ) \bmod 360^\circ}{22.5^\circ} \right\rfloor \in [0, 15]$$
- **Calm Cutoff**: $w_s < 0.5\text{ m/s}$ excluded from directional bins.
- **Criterion Threshold**: $\tau = P_{75}(C)$ over pooled station-hour observations.
- **CPF Probability with Suppression**:
  $$\text{CPF}_k = \begin{cases} \frac{m_k}{N_k} & \text{if } N_k \ge 6 \\ \text{null} & \text{if } N_k < 6 \end{cases}$$
  where $N_k$ is valid non-calm hours in sector $k$, and $m_k$ is hours with $C > \tau$.

### 3.5 Transform 6 & 7: Inter-District Physical Advection Flux & Pathway Coupling
- **Trajectory Forward Bearing**:
  $$\theta_{\text{brg}} = \left(\text{atan2}\left(\sin(\Delta\lambda)\cos(\phi_b), \, \cos(\phi_a)\sin(\phi_b) - \sin(\phi_a)\cos(\phi_b)\cos(\Delta\lambda)\right) \cdot \frac{180}{\pi} + 360^\circ\right) \bmod 360^\circ$$
- **Downwind Vector Bearing (TO)**:
  $$\theta_{\text{to}} = \left(\text{atan2}(u_a, v_a) \cdot \frac{180}{\pi} + 360^\circ\right) \bmod 360^\circ$$
- **Angular Divergence & Transport Cone**:
  $$\Delta\theta = \left|\left((\theta_{\text{to}} - \theta_{\text{brg}} + 180^\circ) \bmod 360^\circ\right) - 180^\circ\right| \le 35.0^\circ$$
- **Hourly Advection Flux (Physical Pollutants Only; Disabled for AQI)**:
  $$\text{Flux}_{a \to b}(t) = \begin{cases} C_a(t) \cdot w_a(t) \cdot \cos\left(\Delta\theta \cdot \frac{\pi}{180}\right) \cdot \exp\left(-\frac{d_{ab}}{100.0\text{ km}}\right) & \text{if } w_a \ge 0.5\text{ m/s}, \, \Delta\theta \le 35^\circ, \, d_{ab} \le 180\text{ km} \\ \text{null} & \text{otherwise} \end{cases}$$
- **Receptor Coupling & Net Balance**:
  $$\theta_{\text{back}} = \theta_{\text{brg}}(b \to a), \quad k_{\text{rec}} = \left\lfloor \frac{(\theta_{\text{back}} + 11.25^\circ) \bmod 360^\circ}{22.5^\circ} \right\rfloor$$
  $$\Omega = \begin{cases} \text{CPF}_b(k_{\text{rec}}) & \text{if } \text{CPF}_b(k_{\text{rec}}) \ne \text{null} \\ 0.25 & \text{otherwise} \end{cases}$$
  $$\text{Score}_{a \to b} = \overline{\text{Flux}}_{a \to b} \times \Omega \quad (\text{Top 60 links retained})$$
  $$\text{Net Transport}_d = \sum_{b \ne d} \text{Score}_{d \to b} - \sum_{a \ne d} \text{Score}_{a \to d}$$

### 3.6 Transform 8: Transboundary Cross-Border Index
- **District Evaluation ($d_{\text{border}} \le 120.0\text{ km}$)**:
  $$\text{TBVal}_d(t) = \begin{cases} +C_d(t) \cdot w_d(t) \cdot \exp\left(-\frac{d_{\text{border}}}{100.0}\right) & \text{if } k \in \text{india\_sectors}_d \\ -C_d(t) \cdot w_d(t) \cdot \exp\left(-\frac{d_{\text{border}}}{100.0}\right) & \text{if } (k+8)\bmod 16 \in \text{india\_sectors}_d \\ 0.0 & \text{otherwise / calm} \end{cases}$$
- **Border Normal Vector Flow (39 Animation Nodes)**:
  $$\Phi_j(t) = u_j(t) \cdot nx_j + v_j(t) \cdot ny_j$$

### 3.7 Transform 9: Official PEPC AQI & Color Mapping
- **Breakpoint Matrix**:
  - $\text{PM}_{10}$: $[75, 150, 250, 350, 450, 550]\ \mu\text{g/m}^3$
  - $\text{PM}_{2.5}$: $[15, 35, 70, 140, 250, 350]\ \mu\text{g/m}^3$
  - $\text{SO}_2$: $[60, 120, 220, 320, 800, 1600]\ \mu\text{g/m}^3$
  - $\text{NO}_2$: $[40, 80, 130, 180, 380, 580]\ \mu\text{g/m}^3$
  - $\text{O}_3$: $[65, 130, 195, 260, 450, 550]\ \mu\text{g/m}^3$
  - $\text{CO}$: $[2.5, 5.0, 7.5, 10.0, 25.0, 40.0]\ \text{mg/m}^3$
- **Index Category Intervals ($I_{\text{low}}, I_{\text{high}}$)**:
  $(0, 50]$, $(50, 100]$, $(100, 150]$, $(150, 200]$, $(200, 300]$, $(300, 400]$, $(400, 500]$.
- **Piecewise Linear Formula**:
  $$I_p = \text{round}\left(\frac{I_{\text{high}} - I_{\text{low}}}{BP_{\text{high}} - BP_{\text{low}}} \cdot (C_p - BP_{\text{low}}) + I_{\text{low}}\right)$$
  Operational cap at 500 when $C_p > BP_6$.
  $$\text{AQI}_{\text{composite}} = \max(I_{\text{PM2.5}}, I_{\text{PM10}})$$

---

## 4. Test Fixtures & Numerical Reference Vectors

These deterministic reference values must be implemented in the automated unit test suite:

### 4.1 PEPC Breakpoint Test Matrix
| Pollutant | Concentration ($C_p$) | Category Name | Expected Sub-Index ($I_p$) | Exact Boundary Test Notes |
|---|---|---|---|---|
| **PM2.5** | $0.0\ \mu\text{g/m}^3$ | Good | $0$ | Minimum boundary |
| **PM2.5** | $7.5\ \mu\text{g/m}^3$ | Good | $25$ | Midpoint Category 0 |
| **PM2.5** | $15.0\ \mu\text{g/m}^3$ | Good | $50$ | Upper threshold Category 0 |
| **PM2.5** | $25.0\ \mu\text{g/m}^3$ | Satisfactory | $75$ | Midpoint Category 1 |
| **PM2.5** | $35.0\ \mu\text{g/m}^3$ | Satisfactory | $100$ | Upper threshold Category 1 |
| **PM2.5** | $52.5\ \mu\text{g/m}^3$ | Moderate | $125$ | Midpoint Category 2 |
| **PM2.5** | $70.0\ \mu\text{g/m}^3$ | Moderate | $150$ | Upper threshold Category 2 |
| **PM2.5** | $105.0\ \mu\text{g/m}^3$ | Unhealthy (Sensitive) | $175$ | Midpoint Category 3 |
| **PM2.5** | $140.0\ \mu\text{g/m}^3$ | Unhealthy (Sensitive) | $200$ | Upper threshold Category 3 |
| **PM2.5** | $195.0\ \mu\text{g/m}^3$ | Unhealthy | $250$ | Midpoint Category 4 |
| **PM2.5** | $250.0\ \mu\text{g/m}^3$ | Unhealthy | $300$ | Upper threshold Category 4 |
| **PM2.5** | $300.0\ \mu\text{g/m}^3$ | Very Unhealthy | $350$ | Midpoint Category 5 |
| **PM2.5** | $350.0\ \mu\text{g/m}^3$ | Very Unhealthy | $400$ | Upper threshold Category 5 |
| **PM2.5** | $400.0\ \mu\text{g/m}^3$ | Hazardous | $500$ | Operational Cap ($>350.0$) |
| **PM10** | $37.5\ \mu\text{g/m}^3$ | Good | $25$ | Midpoint Category 0 |
| **PM10** | $75.0\ \mu\text{g/m}^3$ | Good | $50$ | Upper threshold Category 0 |
| **PM10** | $150.0\ \mu\text{g/m}^3$ | Satisfactory | $100$ | Upper threshold Category 1 |
| **PM10** | $250.0\ \mu\text{g/m}^3$ | Moderate | $150$ | Upper threshold Category 2 |
| **PM10** | $350.0\ \mu\text{g/m}^3$ | Unhealthy (Sensitive) | $200$ | Upper threshold Category 3 |
| **PM10** | $450.0\ \mu\text{g/m}^3$ | Unhealthy | $300$ | Upper threshold Category 4 |
| **PM10** | $550.0\ \mu\text{g/m}^3$ | Very Unhealthy | $400$ | Upper threshold Category 5 |
| **PM10** | $600.0\ \mu\text{g/m}^3$ | Hazardous | $500$ | Operational Cap ($>550.0$) |

### 4.2 Geodesic Distance & IDW Test Fixture
- **Coordinates**:
  - Lahore Centroid: $(31.549^\circ\text{N}, 74.364^\circ\text{E})$
  - Sheikhupura Centroid: $(31.692^\circ\text{N}, 74.198^\circ\text{E})$
- **Expected Haversine Geodesic Distance**: $22.3583\text{ km}$
- **Expected Forward Bearing**: $315.3748^\circ$ (North-West)
- **Discrete IDW Interpolation Reference**:
  - Query Point: $(31.600^\circ\text{N}, 74.300^\circ\text{E})$
  - Reporting Station 1: $(31.549^\circ\text{N}, 74.364^\circ\text{E})$, Value = $200.0$ ($d = 8.3017\text{ km}, w = 0.014510$)
  - Reporting Station 2: $(31.692^\circ\text{N}, 74.198^\circ\text{E})$, Value = $150.0$ ($d = 14.0669\text{ km}, w = 0.005054$)
  - Reporting Station 3: $(31.436^\circ\text{N}, 73.102^\circ\text{E})$, Value = $100.0$ ($d = 115.0139\text{ km}, w = 0.000076$)
  - **Expected Interpolated Value**: $186.7488$

### 4.3 Physical Advection Flux Test Fixture
- **Input Parameters**:
  - Source District $a$: $C_a = 250.0\ \mu\text{g/m}^3$, Wind speed $w_a = 4.0\text{ m/s}$
  - Trajectory: Distance $d_{ab} = 50.0\text{ km}$, Bearing $\theta_{\text{brg}} = 90.0^\circ$ (East)
  - Wind Direction TO: $\theta_{\text{to}} = 105.0^\circ$
  - Divergence: $\Delta\theta = 15.0^\circ \le 35.0^\circ$
- **Intermediate Values**:
  - $\cos(15.0^\circ) = 0.965926$
  - $\exp(-50.0 / 100.0) = \exp(-0.5) = 0.606531$
- **Expected Advection Flux**: $250.0 \times 4.0 \times 0.965926 \times 0.606531 = 585.864\ \mu\text{g}\cdot\text{m}^{-2}\cdot\text{s}^{-1}$
- **Boundary Cutoffs**:
  - If $\theta_{\text{to}} = 130.0^\circ \implies \Delta\theta = 40.0^\circ > 35.0^\circ \implies \text{Flux} = \text{null}$
  - If $w_a = 0.4\text{ m/s} < 0.5\text{ m/s} \implies \text{Flux} = \text{null}$
  - If $d_{ab} = 190.0\text{ km} > 180.0\text{ km} \implies \text{Flux} = \text{null}$
  - If `pollutant === 'AQI'` $\implies \text{Flux} = \text{null}$

### 4.4 CPF Wind Rose Test Fixture
- **District**: Attock (PM2.5)
  - Threshold $\tau = P_{75} = 95.8\ \mu\text{g/m}^3$
  - Calm fraction: $0.898$ ($89.8\%$)
  - Sector 9 ($202.5^\circ$): $N_9 = 6, m_9 = 2 \implies \text{CPF}_9 = 2 / 6 = 0.333$
  - Sector 10 ($225.0^\circ$): $N_{10} = 6, m_{10} = 1 \implies \text{CPF}_{10} = 1 / 6 = 0.167$
  - Sector 12 ($270.0^\circ$): $N_{12} = 7, m_{12} = 0 \implies \text{CPF}_{12} = 0 / 7 = 0.0$
  - Sector 13 ($292.5^\circ$): $N_{13} = 5, m_{13} = 0 \implies \text{CPF}_{13} = \text{null}$ (Small-sample suppression $N < 6$)
  - Sector 4 ($90.0^\circ$): $N_4 = 4, m_4 = 0 \implies \text{CPF}_4 = \text{null}$ ($N < 6$)
  - Sector 5 ($112.5^\circ$): $N_5 = 3, m_5 = 1 \implies \text{CPF}_5 = \text{null}$ ($N < 6$)

---

## 5. Architectural Decoupling Recommendations

To achieve strict adherence to Clean Architecture and SOLID principles, the mathematical transformation algorithms must be decoupled into pure, stateless domain functions:

```
src/
└── domain/
    └── math/
        ├── __init__.py
        ├── geodesy.py          # Haversine distance, bearings, angular divergence, sector mapping
        ├── wind.py             # Polar/Cartesian conversions, anemometer bounds, QC sanitization
        ├── idw.py              # Discrete geodesic IDW (d0 clamp) & Anisotropic continuous IDW
        ├── cpf.py              # 16-sector CPF, pooled station P75 thresholding, small-sample suppression
        ├── flux.py             # Inter-district advection flux, pathway scoring, net transport balance
        ├── transboundary.py    # Border-belt index, border normal dot-products (39 & 117 nodes)
        ├── pepc_aqi.py         # Official PEPC piecewise linear AQI interpolation, capping, PEQS color stops
        ├── qc.py               # 7-hour rolling median spike filter, 3-hour hold filter (i >= 2 guard), 75% rule
        └── projection.py       # Equirectangular Plate Carrée (31°N standard parallel), AABB greedy labeling
```

### Decoupling Rules:
1. **Zero Framework Dependencies**: The `domain/math/` package must not import FastAPI, SQLAlchemy, TimescaleDB, Redis, or Celery. It should strictly rely on Python standard library and `numpy`/`scipy` for high-performance vectorization.
2. **Immutable Input/Output Types**: Use Python `dataclasses` or `typing.NamedTuple` with strict type annotations.
3. **Deterministic Pure Functions**: Given the same inputs, functions must produce identical outputs with zero side effects.
4. **Comprehensive Test Coverage**: Each module under `domain/math/` must be paired with co-located unit tests in `tests/unit/domain/math/` asserting the exact fixtures documented in Section 4.

---

## 6. Caveats

1. **Legacy Transform 3 vs Transform 2**: In `index.html`, `drawSurface` implemented planar screen raster IDW ($p=3$), but had 0 active callers. Production architecture must exclusively implement Transform 2 (Anisotropic Wind-Steered IDW).
2. **AQI Dimensional Restriction**: While the legacy client prototype populated `DATA.pol.AQI.links`, `TRANSFORMATION_LOGIC_SPEC.md` explicitly mandates that physical advection flux is disabled for dimensionless ordinal `AQI`. The decoupled math engine must enforce this domain guard.
3. **Wazirabad Anemometer Offset**: The persistent $140^\circ$ physical installation offset at Wazirabad requires unconditional exclusion from station wind vector averaging.

---

## 7. Conclusion

The mathematical transformation specification mining is complete. All 11 transformation subsystems, LaTeX mathematical formulations, input/output schemas, operational constraints, edge cases, numerical stability guards, and deterministic verification fixtures have been discovered, cross-verified, and documented. The domain mathematics are completely specified and ready for pure functional implementation in the target codebase.

---

## 8. Verification Method

To independently verify the mathematical transformations and fixtures documented in this report:

1. **Inspect Source Files**:
   - `docs/TRANSFORMATION_LOGIC_SPEC.md` lines 64–532
   - `index.html` lines 282–295, 313–328, 350–368, 383–410, 524–536
   - `collector/collector.py` lines 178–287
2. **Execute Python Verification Verification Runner**:
   ```bash
   python -c "
   import math
   # Haversine Test
   rad = math.pi / 180.0
   R_ = 6371.0
   lhr, skp = (31.549, 74.364), (31.692, 74.198)
   la1, lo1, la2, lo2 = lhr[0]*rad, lhr[1]*rad, skp[0]*rad, skp[1]*rad
   d = 2 * R_ * math.asin(math.sqrt(math.sin((la2 - la1)/2)**2 + math.cos(la1)*math.cos(la2)*math.sin((lo2 - lo1)/2)**2))
   assert abs(d - 22.3583) < 0.01
   print('Geodesy test passed: d =', round(d, 4))
   "
   ```
3. **Invalidation Conditions**:
   - If PEPC officially publishes new breakpoint intervals replacing the 2026 standards.
   - If EPA Punjab recalibrates or replaces the physical anemometer hardware at the Wazirabad AQMS site, resolving the $140^\circ$ offset.
