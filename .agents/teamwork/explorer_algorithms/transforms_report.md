# Algorithmic & Mathematical Transformation Specification Report (Requirement R2)
**Punjab Air Quality Monitoring & Analytics System**
**Author:** Algorithms & Transforms Explorer (`teamwork_explorer`)
**Status:** Completed Investigation
**Target File:** `c:\Users\Asif\Downloads\Punjab Air Quality\index.html`

---

## 1. Executive Summary & Algorithmic Architecture Overview

The single-page Punjab Air Quality application (`index.html`) embeds a sophisticated suite of geostatistical, meteorological, and physical transport algorithms. The client application acts not merely as a rendering engine, but as a real-time data processing and analytics pipeline that continuously extends historical air quality datasets (`window.DATA`) with live hourly snapshots fetched from the EPA Punjab public portal (`aqi.punjab.gov.pk`), METAR airport reports, WMO synoptic stations, and ECMWF IFS atmospheric model grids.

### End-to-End Data Transformation Workflow

```
[ Raw Station Feeds ] ---> [ Quality Control & Validation ]
                                 |  - Zero / Negative Purge
                                 |  - 3-Hour Logger Hold Filter
                                 |  - 7-Sample Moving Median Spike Filter
                                 v
[ Meteorological Blending ] ---> [ District Spatial Aggregation ]
  (AQMS -> METAR -> ECMWF)       |  - Station Arithmetic Mean
                                 |  - Station Vector Wind Mean
                                 v
                            [ Spatial Interpolation (IDW) ]
                                 |  - Geodesic District IDW (Haversine, p=2)
                                 |  - Anisotropic Wind-Steered Field (p=2)
                                 |  - Raster Canvas IDW (p=3, cell=5px)
                                 v
       +-------------------------+-------------------------+
       |                                                   |
       v                                                   v
[ Physical Flux & Transport ]                    [ Statistical Analysis ]
  - Pairwise Advection Flux (180 km, 35° cone)     - Conditional Probability Function (CPF)
  - Exponential Distance Decay (LS = 100 km)       - 16-Sector Polar Roses (P75 threshold)
  - Transboundary Cross-Border Index (120 km)      - Source-Receptor Pathway Ranking
  - Boundary Layer Integration (10m vs 925 hPa)    - PEPC / PEQS Breakpoint Mapping
       |                                                   |
       +-------------------------+-------------------------+
                                 |
                                 v
                   [ Temporal & Visual Rendering ]
                     - Continuous Lerp (Sub-hourly scrub)
                     - Projected Coordinate Transform (cos 31°)
                     - Collision-Free Greedy Labeling
                     - Animated Particle Advection & Chevrons
```

---

## 2. Inverse Distance Weighting (IDW) Spatial Interpolation

Investigation of `index.html` reveals **four distinct implementations** of Inverse Distance Weighting, each tailored for a specific functional requirement:
1. **Discrete District-to-District IDW** (`extendData`, line 286): For imputing missing pollutant concentrations and wind vectors in unmonitored districts.
2. **Anisotropic Wind-Steered Continuous Surface IDW** (`fieldAt` and `renderField`, lines 527–536): For generating the primary continuous pollution surface with physical downwind advection bias.
3. **Planar Screen Raster IDW** (`drawSurface`, lines 441–448): For fast raster canvas interpolation.
4. **Vector Wind Field Interpolation** (`windAt`, line 455): For continuous particle tracing across irregular monitoring networks.

---

### 2.1 Discrete District-to-District Geodesic IDW

Implemented in `window.extendData` (lines 282–286):
```javascript
const geo = (a, b) => {
  const la1 = a[0] * rad, lo1 = a[1] * rad, la2 = b[0] * rad, lo2 = b[1] * rad, dl = lo2 - lo1;
  const d = 2 * R_ * Math.asin(Math.sqrt(Math.sin((la2 - la1) / 2) ** 2 + Math.cos(la1) * Math.cos(la2) * Math.sin(dl / 2) ** 2));
  const y = Math.sin(dl) * Math.cos(la2), x = Math.cos(la1) * Math.sin(la2) - Math.sin(la1) * Math.cos(la2) * Math.cos(dl);
  return [d, ((Math.atan2(y, x) / rad) + 360) % 360];
};
const idw = (t, vals) => {
  let ws = 0, vs = 0;
  for (const [d, v] of Object.entries(vals)) {
    if (v == null) continue;
    const w = 1 / Math.max(geo(C(t), C(d))[0], 5) ** 2;
    ws += w; vs += w * v;
  }
  return ws ? vs / ws : null;
};
```

#### Mathematical Specification:
Given a target district $t$ at coordinates $(\phi_t, \lambda_t)$ and a set of monitored districts $\mathcal{M}$ with known values $v_i$ at $(\phi_i, \lambda_i)$:

1. **Distance Metric (Great-Circle Haversine Formula)**:
   $$\Delta \phi = \phi_i - \phi_t, \quad \Delta \lambda = \lambda_i - \lambda_t$$
   $$a = \sin^2\left(\frac{\Delta \phi}{2}\right) + \cos(\phi_t)\cos(\phi_i)\sin^2\left(\frac{\Delta \lambda}{2}\right)$$
   $$d(t, i) = 2 R_{\text{Earth}} \arcsin\left(\sqrt{a}\right)$$
   where mean Earth radius $R_{\text{Earth}} = 6371.0\text{ km}$.

2. **Inverse Distance Weighting Equation**:
   $$w_i = \frac{1}{\left(\max(d(t, i), d_0)\right)^p}$$
   $$V(t) = \frac{\sum_{i \in \mathcal{M}} w_i \cdot v_i}{\sum_{i \in \mathcal{M}} w_i}$$

#### Algorithmic Parameters:
- **Power Parameter ($p$)**: $p = 2$ (Standard Inverse Square Law).
- **Zero-Distance Clamping Threshold ($d_0$)**: $d_0 = 5.0\text{ km}$. If $d(t, i) < 5\text{ km}$, distance is clamped to $5\text{ km}$ ($w_{\max} = 1 / 25 = 0.04$), preventing division by zero and singularity spikes when evaluating near coincident stations.
- **Neighborhood Selection**: Global over all active monitored districts with non-null readings ($\mathcal{M} = \{d \in \text{MON} \mid v_d \ne \text{null}\}$).
- **Execution Domain**:
  - Imputing pollutant concentration $s_d$ for unmonitored districts (`D[n].est === true`).
  - Imputing orthogonal wind vector components $(u_d, v_d)$ independently: $u_d = \text{idw}(d, \{u_m\})$, $v_d = \text{idw}(d, \{v_m\})$.

---

### 2.2 Anisotropic Wind-Steered Continuous Surface IDW

Implemented in `fieldAt` and `renderField` (lines 524–536):
```javascript
function fieldAt(x, y, pts) {
  let ws = 0, vs = 0, dmin = 1e9;
  for (const p of pts) {
    const dx = x - p.x, dy = y - p.y, d2 = dx * dx + dy * dy, d = Math.sqrt(d2);
    if (d < dmin) dmin = d;
    let w = 1 / (d2 + 16);
    if (p.u != null && d > 2) {
      const sp = Math.hypot(p.u, p.w);
      if (sp > 0.5) {
        const c = (dx * p.u - dy * p.w) / (d * sp);
        w *= Math.max(0.3, 1 + 0.7 * c * Math.min(1, sp / 1.5));
      }
    }
    ws += w; vs += w * p.v;
  }
  return [vs / ws, dmin];
}
```

#### Mathematical Specification:
Unlike standard isotropic IDW, this algorithm integrates real-time advective wind transport directly into the spatial kernel, biasing the interpolated surface in the direction of the wind plume.

1. **Euclidean Metric & Base Weight**:
   $$d_i = \sqrt{(x - x_i)^2 + (y - y_i)^2}, \quad w_{0,i} = \frac{1}{d_i^2 + \epsilon^2}$$
   with softening radius $\epsilon^2 = 16\text{ px}^2$ (effective $\epsilon = 4\text{ px}$).

2. **Wind-Steered Directional Alignment Factor**:
   Let station wind vector be $\mathbf{w}_i = (u_i, v_i)$ with wind speed $s_i = \|\mathbf{w}_i\| = \sqrt{u_i^2 + v_i^2}$.
   In screen coordinates (where $y$ increases downward, so meteorological northward wind $v > 0$ translates to $-dy$):
   $$\cos(\alpha_i) = \frac{\Delta x \cdot u_i - \Delta y \cdot v_i}{d_i \cdot s_i}$$
   where $\cos(\alpha_i) = +1$ directly downwind from the station, and $-1$ directly upwind.

3. **Anisotropic Kernel Modulation**:
   If $s_i > 0.5\text{ m/s}$ and $d_i > 2\text{ px}$:
   $$w_i = w_{0,i} \cdot \max\left(0.3, \, 1 + 0.7 \cdot \cos(\alpha_i) \cdot \min\left(1, \frac{s_i}{1.5}\right)\right)$$
   - **Downwind Amplification**: When $\cos(\alpha_i) > 0$, weight increases by up to $+70\%$.
   - **Upwind Attenuation**: When $\cos(\alpha_i) < 0$, weight is reduced to a minimum floor of $0.3$ (70% reduction).
   - **Velocity Saturation**: Reaches maximum directional bias at $s_i = 1.5\text{ m/s}$.

4. **Distance-Dependent Opacity Taper**:
   To communicate uncertainty in data-sparse regions, alpha transparency fades as a function of distance $d_{\min} = \min_i(d_i)$ to the nearest reporting station:
   $$km = d_{\min} \cdot \left(\frac{111\text{ km/deg}}{S}\right)$$
   $$\alpha(km) = \begin{cases}
     235 & \text{if } km < 45\text{ km} \\
     95  & \text{if } km > 140\text{ km} \\
     235 - 140 \cdot \left(\frac{km - 45}{140 - 45}\right) & \text{if } 45 \le km \le 140\text{ km}
   \end{cases}$$

---

### 2.3 Planar Screen Raster IDW

Implemented in `drawSurface` (lines 441–448):
```javascript
function drawSurface(st) {
  const cell = 5, gw = Math.ceil(W / cell), gh = Math.ceil(H / cell);
  // ...
  for (let y = 0; y < gh; y++)
    for (let x = 0; x < gw; x++) {
      let ws = 0, vs = 0;
      for (const p of pts) {
        const dx = x - p[0], dy = y - p[1], q = dx * dx + dy * dy + 0.25, w = 1 / (q * Math.sqrt(q));
        ws += w; vs += w * p[2];
      }
      const c = colArr(vs / ws), o = (y * gw + x) * 4;
      // write RGBA into ImageData...
    }
}
```

#### Mathematical Specification:
$$q_i = \Delta x^2 + \Delta y^2 + \epsilon^2, \quad \epsilon^2 = 0.25\text{ px}^2$$
$$w_i = \frac{1}{q_i \cdot \sqrt{q_i}} = \frac{1}{q_i^{1.5}} \approx \frac{1}{r_i^3}$$
- **Power Parameter**: $p = 3$ (Higher power produces steeper localization around monitoring nodes).
- **Grid Resolution**: $5\text{ px} \times 5\text{ px}$ sampling cell.
- **Bounding Box & Boundary Clipping**: The raster image is rendered on an offscreen canvas and blitted to the main display clipped against the official Punjab boundary vector path (`pjPath`).

---

### 2.4 Vector Wind Field Interpolation

Implemented in `windAt` (line 455):
$$w_i = \frac{1}{d_i^2 + \epsilon_{\text{wind}}^2}, \quad \epsilon_{\text{wind}}^2 = 400\text{ px}^2 \quad (\epsilon = 20\text{ px})$$
$$\mathbf{W}(x, y) = \frac{\sum_{i \in \text{MON}} w_i \mathbf{w}_i + \sum_{a \in \text{AIRPORTS}} w_a \mathbf{w}_a}{\sum w_i + \sum w_a}$$
- Smoothly blends district ground-station winds with METAR airport observations.
- Softening radius of $20\text{ px}$ ensures uniform flow transition across provincial scales without localized vortex singularities.

---

## 3. Conditional Probability Function (CPF) Wind Rose Analysis

The Conditional Probability Function (CPF) is an established receptor-modeling technique used to identify local and regional source directions by analyzing the directional probability of encountering elevated pollutant concentrations.

---

### 3.1 Mathematical Definition & Formulation

Implemented in `index.html` (lines 256, 360, 662–671):
$$\text{CPF}_{\Delta \theta} = \frac{m_{\Delta \theta}}{N_{\Delta \theta}}$$

Where:
- **Directional Sectors ($\Delta \theta$)**: 16 sectors of width $22.5^\circ$ ($360^\circ / 16$):
  $$\text{Sector } i \in [0, 15] \implies \theta \in [i \cdot 22.5^\circ - 11.25^\circ, \, i \cdot 22.5^\circ + 11.25^\circ)$$
  Sector 0 is centered at North ($0^\circ / 360^\circ$), Sector 4 at East ($90^\circ$), Sector 8 at South ($180^\circ$), Sector 12 at West ($270^\circ$).
- **Wind Direction Convention**: Meteorological direction the wind is blowing **FROM**:
  $$\theta_{\text{from}} = \left(\frac{\text{atan2}(-u, -v)}{\frac{\pi}{180}} + 360\right) \bmod 360$$
  Sector assignment index:
  $$k = \left\lfloor \frac{(\theta_{\text{from}} + 11.25^\circ) \bmod 360^\circ}{22.5^\circ} \right\rfloor$$
- **Calm Wind Threshold**: $w = \sqrt{u^2 + v^2} < 0.5\text{ m/s}$ (~1 knot).
  - All calm observations are **strictly excluded** from sector sample counts $N_{\Delta \theta}$.
  - The proportion of calm conditions is tracked as a separate district scalar:
    $$\text{Calm Fraction} = \frac{N_{\text{calm}}}{N_{\text{total}}}$$
- **Concentration Threshold ($\text{thr}$)**: 75th percentile ($P_{75}$) of the district’s hourly pollutant distribution:
  $$\text{thr} = P_{75}(C_d)$$
- **Sector Counts**:
  - $N_{\Delta \theta}$ (`sector.n`): Total count of valid hours where wind blew from sector $\Delta \theta$ with $w \ge 0.5\text{ m/s}$.
  - $m_{\Delta \theta}$ (`sector.k`): Count of hours in sector $\Delta \theta$ where $C_d > \text{thr}$.

---

### 3.2 Polar Rose Rendering & Geometry

Implemented in `drawRose` (lines 662–671):
1. **Coordinate Geometry**:
   - Canvas size: $W \times W$, Center $(c_x, c_y) = (W/2, W/2)$, Maximum radius $R = W/2 - 22\text{ px}$.
   - Radial Scale: $sc = 0.8$ (Maximum display probability $\text{CPF} = 0.8$ extends to boundary radius $R$).
   - Concentric circular grid rings drawn at $\text{CPF} \in \{0.2, 0.4, 0.6, 0.8\}$ with radius $r = R \cdot \frac{v}{sc}$.
2. **Isotropic Baseline Reference Line**:
   - A dashed circle is rendered at $\text{CPF} = 0.25$:
     $$r_{\text{ref}} = R \cdot \frac{0.25}{0.8} = 0.3125 \cdot R$$
   - **Physical Interpretation**: By definition of the 75th percentile, exactly $25\%$ of all data points exceed the threshold. If sources are uniformly distributed with no directional preference, $\text{CPF}_{\Delta \theta} = 0.25$ for all sectors. Any sector where $\text{CPF} > 0.25$ indicates an **enriched upwind pollution source**.
3. **Wedge Arc Geometry**:
   For sector $i \in [0, 15]$:
   $$\text{Start Angle } a_0 = \left(i \cdot 22.5^\circ - 11.25^\circ - 90^\circ\right) \cdot \frac{\pi}{180}$$
   $$\text{End Angle } a_1 = a_0 + 22.5^\circ \cdot \frac{\pi}{180}$$
   $$\text{Radius } r_i = \max\left(2, \, R \cdot \min\left(1, \frac{\text{CPF}_i}{0.8}\right)\right)$$
4. **Dynamic Wedge Color Modulation**:
   The wedge color is calculated by multiplying the $P_{75}$ threshold by a CPF amplification factor:
   $$C_{\text{render}} = \text{thr} \cdot (0.6 + 1.4 \cdot \text{CPF}_i)$$
   $$\text{Wedge Color} = \text{col}(C_{\text{render}}, \, \alpha = 0.9)$$
   This ensures wedges pointing toward severe source regions are colored in deeper warning hues (e.g. Red/Purple/Maroon) while cleaner sectors remain green/yellow.

---

## 4. Atmospheric Transport & Advection Flux Modeling

The system estimates inter-district pollution advection and international cross-border transport using hourly vector kinematics combined with empirical dispersion decay.

---

### 4.1 Inter-District Pairwise Advection Flux

Implemented in `flux` (lines 287–290) and `extendData` (lines 351, 358–364):
```javascript
const CALM = DATA.meta.calm || 0.5, MAXD = 180, CONE = 35, LS = 100;
const flux = (c, u, v, km, brg) => {
  if (c == null || u == null) return null;
  const w = Math.hypot(u, v);
  if (w < CALM) return null;
  const to = ((Math.atan2(u, v) / rad) + 360) % 360;
  const dl = Math.abs(((to - brg + 180) % 360 + 360) % 360 - 180);
  return dl <= CONE ? c * w * Math.cos(dl * rad) * Math.exp(-km / LS) : null;
};
```

#### Mathematical Formulation:
For each source district $a$ and receptor district $b$:
1. **Geodesic Trajectory**:
   Distance $d_{ab}$ and initial forward bearing $\theta_{\text{brg}}(a \to b)$ calculated via Haversine and spherical trigonometry:
   $$\text{Bearing } \theta_{\text{brg}} = \text{atan2}\left(\sin(\Delta \lambda)\cos(\phi_b), \, \cos(\phi_a)\sin(\phi_b) - \sin(\phi_a)\cos(\phi_b)\cos(\Delta \lambda)\right)$$
   Cutoff constraint: $d_{ab} \le \text{MAXD} = 180.0\text{ km}$.

2. **Downwind Advection Direction**:
   $$\mathbf{w}_a = (u_a, v_a), \quad w_a = \sqrt{u_a^2 + v_a^2}$$
   $$\text{Direction TO: } \theta_{\text{to}} = \left(\frac{\text{atan2}(u_a, v_a)}{\frac{\pi}{180}} + 360\right) \bmod 360$$

3. **Angular Divergence**:
   $$\Delta \theta = |(\theta_{\text{to}} - \theta_{\text{brg}} + 180^\circ) \bmod 360^\circ - 180^\circ|$$
   Constraint: $\Delta \theta \le \text{CONE} = 35.0^\circ$.

4. **Advection Flux Equation**:
   $$\text{Flux}_{a \to b}(t) = \begin{cases}
     C_a(t) \cdot w_a(t) \cdot \cos(\Delta \theta) \cdot \exp\left(-\frac{d_{ab}}{L_S}\right) & \text{if } w_a \ge 0.5\text{ m/s} \text{ and } \Delta \theta \le 35^\circ \\
     \text{null} & \text{otherwise}
   \end{cases}$$
   where:
   - $C_a(t)$: Pollutant concentration at source district $a$ ($\mu\text{g/m}^3$ or $\text{mg/m}^3$).
   - $w_a(t)$: Surface wind speed at source ($m/s$).
   - $\cos(\Delta \theta)$: Geometric projection of the wind vector onto the source-receptor axis.
   - $L_S = 100.0\text{ km}$: Characteristic atmospheric residence and dispersion length scale ($e$-folding distance).

---

### 4.2 Pathway Coupling & Receptor-Weighted Scoring

Implemented in lines 358–364:
1. **Period Average Flux**:
   $$\overline{\text{Flux}}_{a \to b} = \frac{\sum_{t=1}^{N} \text{Flux}_{a \to b}(t)}{N_{\text{active}}}$$
   where $N_{\text{active}}$ is the total number of hours with valid monitoring data.

2. **Receptor CPF Feedback Coupling**:
   To confirm that transported air actually elevated pollution at the receptor, the pathway flux is multiplied by the receptor’s historical CPF for winds arriving from the direction of the source:
   $$\text{Back Bearing } \theta_{\text{back}} = \theta_{\text{brg}}(b \to a)$$
   $$\text{Receptor Sector } k = \left\lfloor \frac{(\theta_{\text{back}} + 11.25^\circ) \bmod 360^\circ}{22.5^\circ} \right\rfloor$$
   $$c_{\text{cpf}} = \text{CPF}_b(\text{Sector } k)$$
   $$\text{Coupling Coefficient } \Omega = \begin{cases} c_{\text{cpf}} & \text{if available} \\ 0.25 & \text{if unmonitored / null} \end{cases}$$

3. **Composite Pathway Score**:
   $$\text{Score}_{a \to b} = \overline{\text{Flux}}_{a \to b} \times \Omega$$

4. **District Net Export / Import Balance**:
   For each district $d$:
   $$\text{Net Transport}_d = \sum_{b \ne d} \text{Score}_{d \to b} - \sum_{a \ne d} \text{Score}_{a \to d}$$
   - Positive value ($\text{Net} > 0$): Net pollution **exporter** (source).
   - Negative value ($\text{Net} < 0$): Net pollution **importer** (receptor).

---

### 4.3 Transboundary Cross-Border Flux Modeling

Implemented in `tbVal` (lines 292–294) and lines 366–367:
```javascript
const tbVal = (d, c, u, v) => {
  const g = TBG[d];
  if (c == null || u == null) return null;
  const w = Math.hypot(u, v);
  if (w < CALM) return 0;
  const frm = ((Math.atan2(-u, -v) / rad) + 360) % 360;
  const k = Math.floor(((frm + 11.25) % 360) / 22.5);
  const val = c * w * Math.exp(-g.border_km / 100);
  return g.india_sectors.includes(k) ? val : g.india_sectors.includes((k + 8) % 16) ? -val : 0;
};
```

#### Mathematical Specification:
1. **Target Border Belt**: Districts within $120\text{ km}$ of the international border ($\mathcal{B} = \{d \in \text{Districts} \mid d_{\text{border}} \le 120\text{ km}\}$).
2. **Direction Classification**:
   - Meteorological direction FROM: $\theta_{\text{from}} = \text{atan2}(-u, -v)$.
   - Sector index: $k = \lfloor (\theta_{\text{from}} + 11.25) / 22.5 \rfloor \bmod 16$.
   - **Inflow (India $\to$ Pakistan)**: If $k \in \text{india\_sectors}_d$, value $= +C_d \cdot w_d \cdot e^{-d_{\text{border}} / 100}$.
   - **Outflow (Pakistan $\to$ India)**: If $(k + 8) \bmod 16 \in \text{india\_sectors}_d$, value $= -C_d \cdot w_d \cdot e^{-d_{\text{border}} / 100}$.
   - **Neutral / Parallel**: Otherwise, value $= 0$.
3. **Hourly Regional Inflow and Outflow Totals**:
   $$\text{Total Inflow}(t) = \sum_{d \in \mathcal{B}, \neg \text{est}} \max\left(\text{TBVal}_d(t), \, 0\right)$$
   $$\text{Total Outflow}(t) = \sum_{d \in \mathcal{B}, \neg \text{est}} \max\left(-\text{TBVal}_d(t), \, 0\right)$$

---

### 4.4 Boundary Layer & Reanalysis Integration (10m vs 925 hPa)

The codebase accounts for vertical atmospheric structure through ECMWF IFS reanalysis data:
- **10-meter wind**: Governs surface contact, local dispersion, and human exposure.
- **925 hPa wind (~750m AGL)**: Governs long-range regional transport of agricultural residue burning plumes above the nocturnal temperature inversion.
- **Calibration Scaling Ratio**: $K_R = 0.22686$ (embedded in metadata as `ecm_ratio`). Reanalysis 10m grid winds over smooth terrain overestimate localized urban surface friction measured by ground stations. When substituting missing station winds with METAR or ECMWF data, wind vectors are calibrated by $K_R$:
  $$\mathbf{w}_{\text{calibrated}} = K_R \cdot \mathbf{w}_{\text{ECMWF}}$$
- **Border Normal Flux Across 117 Discretized Coordinates**:
  Sample points $(\lambda_j, \phi_j)$ along the border line with inward unit normal vectors $\mathbf{n}_j = (nx_j, ny_j)$:
  $$c_j = \mathbf{w}(\lambda_j, \phi_j) \cdot \mathbf{n}_j = u_j \cdot nx_j + v_j \cdot ny_j$$
  - $c_j > +0.25\text{ m/s}$: Net inward transboundary advection.
  - $c_j < -0.25\text{ m/s}$: Net outward transboundary advection.

---

## 5. PEPC Breakpoints, Sub-Indices & Visual Mapping

Air quality classification in `index.html` implements the official standards approved by the **Punjab Environmental Protection Council (PEPC)** and the **Punjab Environmental Quality Standards (PEQS)**.

---

### 5.1 PEPC Pollutant Breakpoint Matrix

Implemented in `BP` (line 384):
```javascript
const BP = {
  PM10:   [75,  150, 250, 350, 450, 550],
  'PM2.5': [15,  35,  70,  140, 250, 350],
  SO2:    [60,  120, 220, 320, 800, 1600],
  NO2:    [40,  80,  130, 180, 380, 580],
  O3:     [65,  130, 195, 260, 450, 550],
  CO:     [2.5, 5,   7.5, 10,  25,  40]
};
```

| Category Index ($i$) | Category Descriptor | AQI Range | PM2.5 (24h) [$\mu\text{g/m}^3$] | PM10 (24h) [$\mu\text{g/m}^3$] | NO2 (1h) [$\mu\text{g/m}^3$] | SO2 (1h) [$\mu\text{g/m}^3$] | CO (8h) [$\text{mg/m}^3$] | O3 (1h) [$\mu\text{g/m}^3$] | Category Color (RGB / Hex) |
|---|---|---|---|---|---|---|---|---|---|
| **0** | **Good** | 0 – 50 | 0 – 15 | 0 – 75 | 0 – 40 | 0 – 60 | 0 – 2.5 | 0 – 65 | `[0, 176, 80]` (`#00B050`) |
| **1** | **Satisfactory** | 51 – 100 | 16 – 35 | 76 – 150 | 41 – 80 | 61 – 120 | 2.6 – 5.0 | 66 – 130 | `[146, 208, 80]` (`#92D050`) |
| **2** | **Moderate** | 101 – 150 | 36 – 70 | 151 – 250 | 81 – 130 | 121 – 220 | 5.1 – 7.5 | 131 – 195 | `[255, 255, 0]` (`#FFFF00`) |
| **3** | **Unhealthy for Sensitive Groups** | 151 – 200 | 71 – 140 | 251 – 350 | 131 – 180 | 221 – 320 | 7.6 – 10.0 | 196 – 260 | `[237, 125, 49]` (`#ED7D31`) |
| **4** | **Unhealthy** | 201 – 300 | 141 – 250 | 351 – 450 | 181 – 380 | 321 – 800 | 10.1 – 25.0 | 261 – 450 | `[255, 0, 0]` (`#FF0000`) |
| **5** | **Very Unhealthy** | 301 – 400 | 251 – 350 | 451 – 550 | 381 – 580 | 801 – 1600 | 25.1 – 40.0 | 451 – 550 | `[112, 48, 160]` (`#7030A0`) |
| **6** | **Hazardous** | 401+ | > 350 | > 550 | > 580 | > 1600 | > 40.0 | > 550 | `[192, 0, 0]` (`#C00000`) |

---

### 5.2 AQI Sub-Index Linear Interpolation

Implemented via EPA standard piecewise linear formula:
$$I_p = \frac{I_{\text{high}} - I_{\text{low}}}{BP_{\text{high}} - BP_{\text{low}}} \left(C_p - BP_{\text{low}}\right) + I_{\text{low}}$$
Where:
- $C_p$: Measured pollutant concentration truncated/rounded to precision.
- $BP_{\text{low}}, BP_{\text{high}}$: Lower and upper concentration breakpoints for category containing $C_p$.
- $I_{\text{low}}, I_{\text{high}}$: Corresponding index range limits (e.g. $[151, 200]$).
- Composite District AQI: Maximum governing sub-index, restricted to PM2.5 and PM10:
  $$\text{AQI} = \max\left(I_{\text{PM2.5}}, \, I_{\text{PM10}}\right)$$

---

### 5.3 PEQS Limits & Continuous Color Ramp

For individual pollutants displayed against legal limits (lines 388, 401):
- **PEQS Limits**: PM2.5 = 35 $\mu\text{g/m}^3$ (24h), PM10 = 150 $\mu\text{g/m}^3$ (24h), NO2 = 80 $\mu\text{g/m}^3$ (24h), SO2 = 120 $\mu\text{g/m}^3$ (24h), CO = 5 $\text{mg/m}^3$ (8h), O3 = 130 $\mu\text{g/m}^3$ (1h).
- **Continuous Color Scaling**: Stops set as multiples of the PEQS reference limit:
  $$\text{MULT} = [0, \, 0.5, \, 1.0, \, 1.5, \, 2.5, \, 4.0, \, 6.0]$$
  $$\text{RGB Stops} = \begin{bmatrix}
    [58, 165, 93] & \text{(Green)} \\
    [156, 204, 58] & \text{(Yellow-Green)} \\
    [242, 194, 48] & \text{(Yellow)} \\
    [240, 122, 38] & \text{(Orange)} \\
    [214, 52, 44]  & \text{(Red)} \\
    [142, 59, 143] & \text{(Purple)} \\
    [90, 21, 48]   & \text{(Deep Maroon)}
  \end{bmatrix}$$
  For value $v$ between stops $x_0 = \text{MULT}[i-1] \cdot \text{ref}$ and $x_1 = \text{MULT}[i] \cdot \text{ref}$:
  $$t = \text{clamp}\left(\frac{v - x_0}{x_1 - x_0}, \, 0, \, 1\right)$$
  $$\text{RGB}(v) = \text{RGB}_{i-1} + t \cdot (\text{RGB}_i - \text{RGB}_{i-1})$$

---

## 6. Hourly Aggregation, Quality Control & Temporal Smoothing

---

### 6.1 Automated Quality Control & Validation Rules

Implemented in `window.extendData` (lines 314–328):
```javascript
for (let k = 0; k < rawv.length; k++) {
  const i = N0 + k, v = full[i];
  if (v == null) continue;
  const win = full.slice(Math.max(0, i - 3), i + 4).filter(x => x != null);
  const med = win.length >= 3 ? median(win) : null;
  const spk = med != null && v > 4 * med && v > lim;
  const hold = p !== 'AQI' && full[i - 1] === v && full[i - 2] === v;
  if (spk || hold) {
    out[k] = null;
    spikes[p] = (spikes[p] || 0) + 1;
  }
}
```

#### Quality Control Rules:
1. **Invalid / Zero Purge**:
   Any reading where $v \le 0$ or $v == \text{null}$ or is non-finite is set to `null`.
2. **7-Hour Moving Median Spike Filter**:
   For each sample $i$, construct a 7-hour symmetric window $W_i = [i-3, \, i+3]$. If at least 3 valid samples exist, compute median $M = \text{median}(W_i)$.
   A reading is discarded as an unphysical transient spike if:
   $$v_i > 4 \cdot M \quad \text{AND} \quad v_i > 3 \cdot (\text{ref} \text{ or } 100)$$
3. **Sensor Freeze / Logger Hold Filter**:
   Environmental logger failure typically repeats identical float values. For all physical pollutants ($p \ne \text{'AQI'}$):
   $$\text{If } v_i = v_{i-1} = v_{i-2} \implies v_i \text{ is invalidated (`null`)}.$$
4. **Anemometer Sanity Validation**:
   - Discard if wind speed $w_s < 0$ or $w_s > 30\text{ m/s}$.
   - Discard if wind direction $w_d < 0^\circ$ or $w_d > 360^\circ$.
   - **Specific Instrument Blacklist**: Wazirabad station wind vane was found rotated by $\sim 140^\circ$ offset and is hardcoded to be excluded (`NOWIND = new Set(['Wazirabad'])`).

---

### 6.2 Multi-Source Meteorological Fusion Hierarchy

Implemented in lines 330–342:
For each district $d$ and hour $h$:
1. **Level 1 (AQMS On-Site Sensors)**: Vector mean of all valid station anemometers within district $d$:
   $$\bar{u}_d = \frac{1}{K}\sum_{k=1}^K -w_{s,k}\sin(w_{d,k}\cdot \frac{\pi}{180}), \quad \bar{v}_d = \frac{1}{K}\sum_{k=1}^K -w_{s,k}\cos(w_{d,k}\cdot \frac{\pi}{180})$$
2. **Level 2 (District Airport METAR)**: If no station wind is available, map district to airport METAR (`DAP` dictionary):
   $$(u_d, v_d) = (u_{\text{METAR}} \cdot K_R, \, v_{\text{METAR}} \cdot K_R)$$
3. **Level 3 (ECMWF IFS 10m Wind)**: If no METAR exists, sample ECMWF IFS grid:
   $$(u_d, v_d) = (-w_{s,\text{ecm}} \cdot K_R \sin(w_{d,\text{ecm}}), \, -w_{s,\text{ecm}} \cdot K_R \cos(w_{d,\text{ecm}}))$$
4. **Level 4 (Spatial IDW Fallback)**: For districts without monitors, calculate IDW from all Level 1/2 monitored districts; if that fails, use ECMWF.

---

### 6.3 Aggregation Completeness: The 75% Rule

Implemented in lines 355–356 and line 701:
- **District Mean Concentration**: Arithmetic mean of valid stations reporting in district $d$.
- **Period Mean Validation**:
  $$\text{Period Mean} = \begin{cases}
    \frac{1}{N_{\text{valid}}} \sum_{t=1}^{N_{\text{valid}}} C(t) & \text{if } N_{\text{valid}} \ge \text{round}(0.75 \cdot N_{\text{active}}) \\
    \text{null} & \text{otherwise}
  \end{cases}$$
  Ensures that statistical metrics (e.g. daily or period averages) cannot be distorted by isolated samples during brief episodes.

---

### 6.4 Sub-Hourly Temporal Interpolation (Animation Lerp)

Implemented in `at` (line 435–437):
For continuous time-scrubbing at fractional frame position $fp \in [0, N-1]$:
$$i = \lfloor fp \rfloor, \quad j = \min(N-1, i+1), \quad f = fp - i$$
$$\text{lerp}(a, b, f) = \begin{cases}
  b & \text{if } a \text{ is null} \\
  a & \text{if } b \text{ is null} \\
  a + (b - a) \cdot f & \text{otherwise}
\end{cases}$$
Applied synchronously across all district concentration values and orthogonal wind vectors $(u, v)$ for smooth 60 FPS canvas animation.

---

## 7. Geometric, Projection & Visual Layout Algorithms

---

### 7.1 Geographic Map Projection

Implemented in `P` and `unP` (lines 419–422, 458):
The map uses an **Equirectangular (Plate Carrée) projection with standard parallel at $31^\circ\text{ N}$**:
- **Bounding Box**: Longitude $\lambda \in [69.10^\circ, 75.75^\circ]\text{ E}$, Latitude $\phi \in [27.55^\circ, 34.30^\circ]\text{ N}$.
- **Meridional Distortion Factor**:
  $$K_X = \cos(31^\circ) = \cos\left(\frac{31 \cdot \pi}{180}\right) \approx 0.8571673$$
- **Forward Screen Transform**:
  $$S = \frac{W}{(\lambda_{\max} - \lambda_{\min}) \cdot K_X}$$
  $$X = (\lambda - \lambda_{\min}) \cdot K_X \cdot S$$
  $$Y = (\phi_{\max} - \phi) \cdot S$$
- **Inverse Geographic Transform**:
  $$\lambda = \frac{X}{K_X \cdot S} + \lambda_{\min}, \quad \phi = \phi_{\max} - \frac{Y}{S}$$

---

### 7.2 Collision-Free Greedy Label Placement Algorithm

Implemented in `drawNodes` (lines 512–516) and `drawValues` (lines 554–557):
To prevent visual overlap of district text and station numbers:
1. Candidate search offsets ordered by proximity:
   $$\mathcal{O} = \{[0, 0], [0, 14], [0, -14], [16, 0], [-16, 0], [0, 26], [0, -26], [30, 8], [-30, 8], [24, -20], [-24, -20], [0, 38]\}$$
2. For each offset $[\Delta x, \Delta y]$, construct the proposed AABB bounding rectangle:
   $$R = \left[x + \Delta x - \frac{w}{2} - 1, \, y + \Delta y - \frac{h}{2}, \, w + 2, \, h\right]$$
3. Evaluate collision against all previously placed bounding boxes:
   $$\text{Collision}(R, Q) \iff R.x < Q.x + Q.w \land R.x + R.w > Q.x \land R.y < Q.y + Q.h \land R.y + R.h > Q.y$$
4. Accept first non-overlapping offset. If displacement $\sqrt{\Delta x^2 + \Delta y^2} > 20\text{ px}$, automatically synthesize a leader line with terminal node dot connecting the text box to the anchor coordinate.

---

### 7.3 Numerical Particle Advection Tracing

Implemented in `stepDraw` and `rStep` (lines 464–475):
1. **Euler Forward Integration**:
   $$x_{t+\Delta t} = x_t + u(x_t, y_t) \cdot k, \quad y_{t+\Delta t} = y_t - v(x_t, y_t) \cdot k$$
   where $k = 1.4 \cdot S / 100$ (scaled to map zoom level).
2. **Path History Ring Buffer**: Each particle retains a trail of length 8.
3. **Lifecycle & Boundary Regeneration**:
   - Random age initialized up to 90 ticks; terminates when $\text{age} > 120$.
   - Point-in-polygon test (`isPointInPath(pjPath, x, y)`) respawns particles exiting provincial territory.
   - Regional particles outside Punjab use bilinear interpolation on ECMWF 0.5° wind grid (`ecmAt`).

---

## 8. Summary Specification Matrix

| Algorithm | Code Location | Input Parameters | Formula / Core Logic | Output / Destination |
|---|---|---|---|---|
| **District IDW** | `index.html:286` | $\{(\phi_i, \lambda_i, v_i)\}$, Target $(\phi_t, \lambda_t)$ | $w_i = \max(d_{\text{haversine}}, 5)^{-2}, \quad V = \frac{\sum w_i v_i}{\sum w_i}$ | Imputed district concentration & wind |
| **Wind-Steered Surface IDW** | `index.html:527` | Station $(x_i, y_i, v_i, u_i, v_i)$, Grid $(x, y)$ | $w_i = \frac{1}{d_i^2+16} \cdot \max(0.3, 1 + 0.7 c_i \min(1, \frac{s_i}{1.5}))$ | Continuous spatial field with wind advection |
| **Raster Canvas IDW** | `index.html:441` | Station coords $p_i$, Screen pixel $(x, y)$ | $q = dx^2 + dy^2 + 0.25, \quad w_i = q^{-1.5}$ ($p=3$) | Fast pixel imageData buffer (5px cells) |
| **CPF Polar Rose** | `index.html:662` | Series $(C, u, v)$, Sector $\Delta \theta = 22.5^\circ$ | $\text{CPF} = m_{\Delta \theta} / N_{\Delta \theta}$ ($C > P_{75}$, $w \ge 0.5\text{ m/s}$) | Directional wind rose with 0.25 baseline |
| **Advection Flux** | `index.html:289` | $C_a, (u_a, v_a), d_{ab}, \theta_{\text{brg}}$ | $C_a \cdot w_a \cdot \cos(\Delta \theta) \cdot e^{-d_{ab}/100}$ ($d \le 180, \Delta \theta \le 35^\circ$) | Pairwise inter-district hourly transport |
| **Cross-Border Flux** | `index.html:292` | $C_d, (u_d, v_d), d_{\text{border}}$, India sectors | $\pm C_d \cdot w_d \cdot e^{-d_{\text{border}}/100}$ (inflow/outflow) | Border-belt transboundary time series |
| **Spike Filter** | `index.html:325` | 7-sample window $W_i$, $P_{\text{ref}}$ | Discard if $v > 4 \cdot \text{median}(W_i)$ AND $v > 3 \cdot \text{ref}$ | Cleaned hourly time series |
| **Hold Filter** | `index.html:326` | 3 consecutive samples $v_i, v_{i-1}, v_{i-2}$ | Discard if $v_i = v_{i-1} = v_{i-2}$ (for $p \ne \text{'AQI'}$) | Sensor freeze invalidation |
| **PEPC Breakpoints** | `index.html:384` | Raw concentrations $C_p$ | 7 category intervals (Good $\to$ Hazardous) | Sub-index & categorical color assignment |
| **Equirectangular Projection** | `index.html:422` | Latitude $\phi$, Longitude $\lambda$ | $x = (\lambda - \lambda_0) K_X S, \quad y = (\phi_1 - \phi) S$ ($K_X = \cos 31^\circ$) | 2D Canvas coordinate mapping |

---
*Report completed and verified against authoritative source `c:\Users\Asif\Downloads\Punjab Air Quality\index.html`.*
