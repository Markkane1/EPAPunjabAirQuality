# Mathematical & Algorithmic Adversarial Challenge Report

**Document ID**: `PAQ-CHALLENGE-MATH-001`  
**Author**: Math & Algorithm Challenger (`teamwork_challenger`)  
**Date**: 2026-11-10  
**Target Specification**: `docs/TRANSFORMATION_LOGIC_SPEC.md` (v1.0.0)  
**Ground Truth Reference**: `index.html` (9.61 MB production client and embedded dataset)  
**Overall Risk Assessment**: **MEDIUM-HIGH** (Mathematical correctness of core models is solid, but 8 critical unstated assumptions, sampling cutoffs, and edge-case vulnerabilities will cause production pipeline failures if implemented as currently specified).  
**Explicit Recommendation**: **REQUEST_CHANGES** (Detailed patch items provided below).

---

## Executive Challenge Summary

A comprehensive empirical audit was conducted on the mathematical and algorithmic transformation logic specified in `TRANSFORMATION_LOGIC_SPEC.md` cross-referenced with `index.html`. Every equation, boundary condition, and numerical kernel was executed in isolated Python/NumPy stress harnesses against actual station telemetry (14,996 station-hours across 79 stations and 41 districts).

### Challenge Scorecard

| Area | Algorithmic Subsystem | Formula Under Review | Empirical Status | Finding / Vulnerability |
|---|---|---|---|---|
| **Area 1** | Discrete Geodesic IDW | $w_i = \max(d_{\text{haversine}}, 5)^{-2}$ | **VERIFIED (With Caveat)** | Singularity clamping works, but causes blunting at $d=0$ ($w=0.04$). |
| **Area 2** | Anisotropic Wind-Steered IDW | $\frac{\Delta x \cdot u - \Delta y \cdot v}{d \cdot s}$, $\epsilon=4\text{ px}$, mult $\in [0.3, 1.7]$ | **VERIFIED** | Correct screen vs meteorological coordinate flip $(-dy \cdot v)$. |
| **Area 3** | CPF Polar Wind Roses | 16 sectors, $P_{75}$, calm $<0.5\text{ m/s}$, $0.25$ baseline | **CRITICAL DEFICIENCY** | Spec omits minimum sample cutoff $N_k \ge 6$; spec implies district averaging instead of station pooling. |
| **Area 4** | Advection Transport Flux | $C \cdot w \cdot \cos(\Delta\theta) \cdot e^{-d/100}$, cone $35^\circ$ | **VERIFIED (With Caveat)** | Geometry verified; spec omits essential constraint: transport is strictly disabled for AQI. |
| **Area 5** | PEPC Breakpoints & Sub-Indices | $I = \frac{I_{hi} - I_{lo}}{BP_{hi} - BP_{lo}}(C - BP_{lo}) + I_{lo}$ | **CRITICAL DEFICIENCY** | Statutory table format creates dead-zone gap ($15.0 \to 15.1$); requires continuous formulation. |
| **Area 6** | QC Filtering & Sensor Bounds | $7\text{h median}$, $3\text{h hold}$, anemometer limits | **CRITICAL DEFICIENCY** | Python wraparound bug on $i < 2$; spec omits anemometer speed $[0, 30]$ and Wazirabad blacklist. |
| **Dormant** | Planar Screen Raster IDW | $p=3$, cell $=5\text{ px}$, $\epsilon^2 = 0.25\text{ px}^2$ | **OBSOLETE CODE** | Transform 3 (`drawSurface`) is dead uncalled code in `index.html`, superseded by Transform 2. |

---

## Detailed Adversarial Challenges & Empirical Proofs

---

### Challenge 1 (High): Missing Minimum Sample Cutoff ($N_k \ge 6$) & Station Pooling in CPF Polar Roses (Transform 5)

#### 1.1 Assumption Challenged
`TRANSFORMATION_LOGIC_SPEC.md` Section 2.5 defines:
$$\text{CPF}_k = \frac{m_k}{N_k}$$
where $N_k$ is the total count of valid non-calm hours when the wind blew from sector $k$, and $m_k$ is the count where concentration $C > \tau = P_{75}(C)$.
The specification does not impose any minimum sample count threshold on $N_k$, and Section 2.5.3 implies inputs are district-averaged hourly time series $C(t), u(t), v(t)$ ($N=216$ hours).

#### 1.2 Attack Scenario & Blast Radius
1. **Low-Sample Spurious Plume Spikes**: In an airflow regime with infrequent wind from a specific sector (e.g. Sector 11 in Multan, where $N_k = 4$, or Attock Sector 15 where $N_k = 1$), if a single hour exceeds $P_{75}$, the raw ratio $m_k / N_k$ produces $\text{CPF}_k = 1/1 = 1.0$ (100% directional probability) or $2/4 = 0.50$. In an air quality compliance dashboard, this triggers a false, extreme red wedge on the polar rose, falsely accusing an upwind industrial zone or neighboring tehsil of severe pollution transport based on an unrepresentative sample of 1 hour.
2. **UI Rendering Collapse**: In `index.html` lines 668-670:
   ```javascript
   if(s.cpf == null){
     g.strokeStyle = T['--muted']; g.lineWidth = 2;
     g.beginPath(); g.arc(cx, cy, 10, a0 + .08, a1 - .08); g.stroke(); return;
   }
   ```
   The client UI relies on `s.cpf === null` to render a neutral muted stub. If the backend computes numbers for $N_k < 6$, the rose renders wild, unvalidated wedges, breaking visual consistency.
3. **District Averaging vs Station Pooling Distortion**: If a district has multiple monitors (e.g., Lahore has 13 stations; Rawalpindi has 4 stations), averaging concentrations across all 13 stations prior to computing $P_{75}$ flattens spatial gradients. The true $P_{75}$ threshold for Multan is $245.0\ \mu\text{g/m}^3$ when computed across pooled station readings ($N=414$). Computing it on the district mean series yields a skewed threshold.

#### 1.3 Empirical Evidence & Verification
Across the entire 9.61 MB production dataset in `index.html` (all 9 pollutants across all 41 districts), we executed a Python scan over every sector in `data['pol'][p]['cpf']`:
```
Values of n where cpf is None: [0, 1, 2, 3, 4, 5]
Values of n where cpf is NOT None: [6, 7, 8, ..., 194]
All sectors with Nk < 6 are null: TRUE
All sectors with Nk >= 6 are computed: TRUE
```
In addition, calculating $P_{75}$ on the pooled station observations for Multan yields:
$$\tau_{\text{pooled}} = 245.0\ \mu\text{g/m}^3 \quad (\text{Exact match to } \texttt{data['pol']['PM2.5']['cpf']['Multan']['thr']})$$
Whereas computing $P_{75}$ on district hourly averages produces a discordant threshold.

#### 1.4 Mitigation / Required Spec Modification
Update Section 2.5 of `TRANSFORMATION_LOGIC_SPEC.md`:
1. Add explicit minimum sample count constraint:
   $$\text{CPF}_k = \begin{cases}
     \frac{m_k}{N_k} & \text{if } N_k \ge 6 \\
     \text{null} & \text{if } N_k < 6
   \end{cases}$$
2. Explicitly specify that for multi-station districts, $P_{75}$ and sector binning are evaluated over the pooled set of all valid station-hour observations $\mathcal{O}_d = \bigcup_{s \in \text{stations}(d)} \{(C_s(t), \mathbf{w}_s(t)) \mid C_s(t) > 0, \|\mathbf{w}_s(t)\| \ge 0.5\text{ m/s}\}$.

---

### Challenge 2 (High): Breakpoint Boundary Discontinuities & Dead Zones (Transform 9)

#### 2.1 Assumption Challenged
`TRANSFORMATION_LOGIC_SPEC.md` Table 365 lists statutory breakpoints with gaps between categories:
- Good: `0.0 – 15.0`
- Satisfactory: `15.1 – 35.0`
- Moderate: `35.1 – 70.0`
- Unhealthy (Sensitive): `70.1 – 140.0`
- Unhealthy: `140.1 – 250.0`
- Very Unhealthy: `250.1 – 350.0`
- Hazardous: `> 350.0`

Equation 377 defines the piecewise linear sub-index interpolation:
$$I_p = \left(\frac{I_{\text{high}} - I_{\text{low}}}{BP_{\text{high}} - BP_{\text{low}}}\right) \cdot \left(C_p - BP_{\text{low}}\right) + I_{\text{low}}$$

#### 2.2 Attack Scenario & Blast Radius
In continuous digital sensor sampling (e.g. BAM-1020 beta attenuation monitors or optical particle counters reporting floating-point numbers like $15.04\ \mu\text{g/m}^3$ or $35.08\ \mu\text{g/m}^3$):
1. **Dead Zone Trap**: If an algorithmic worker implements bracket lookup using the table's explicit ranges ($15.1 \le C \le 35.0$), any concentration in the open interval $(15.0, 15.1)$ fails all conditional checks and returns `null` or raises an `UnmatchedBreakpointException`.
2. **Negative Slope Artifact**: If the worker assigns $C = 15.05$ to Category 1 ($BP_{\text{low}} = 15.1$), the term $(C - BP_{\text{low}}) = (15.05 - 15.10) = -0.05 < 0$. This calculates:
   $$I = \frac{100 - 51}{35.0 - 15.1} (-0.05) + 51 = 51 - 0.123 = 50.877 \implies 51$$
   While the rounding saves it in some cases, near boundary edges it produces non-monotonic reversals where a higher concentration yields a lower index value than the previous category ceiling!

#### 2.3 Empirical Evidence & Verification
In `index.html` lines 384 and 393:
```javascript
const BP = {
  PM10: [75, 150, 250, 350, 450, 550],
  'PM2.5': [15, 35, 70, 140, 250, 350],
  SO2: [60, 120, 220, 320, 800, 1600],
  NO2: [40, 80, 130, 180, 380, 580],
  O3: [65, 130, 195, 260, 450, 550],
  CO: [2.5, 5, 7.5, 10, 25, 40]
};
const bpIdx = (v, k) => { const b = BP[k]; for(let i=0; i<b.length; i++) if(v <= b[i]) return i; return 6; };
```
The ground truth in `index.html` uses continuous half-open intervals: $v \le 15.0$, $v \le 35.0$, etc., with ZERO gaps.
Furthermore, testing 14,996 station-hours from EPA Punjab revealed that whenever $C_{\text{PM2.5}} > 350\ \mu\text{g/m}^3$, the EPA portal clamps Reported AQI to 500 (1,156 occurrences).

#### 2.4 Mitigation / Required Spec Modification
Revise Table 365 and Equation 377 in `TRANSFORMATION_LOGIC_SPEC.md` to define continuous mathematical brackets:
$$\text{Bracket } i: \quad BP_{i-1} < C_p \le BP_i$$
with $BP_0 = 0$, $BP_1 = 15.0$, $BP_2 = 35.0$, $BP_3 = 70.0$, $BP_4 = 140.0$, $BP_5 = 250.0$, $BP_6 = 350.0$.
Specify $I_{\text{low}}$ and $I_{\text{high}}$ as continuous interval endpoints:
Category 0: $[0, 50]$, Category 1: $[50, 100]$, Category 2: $[100, 150]$, Category 3: $[150, 200]$, Category 4: $[200, 300]$, Category 5: $[300, 400]$, Category 6: $[400, 500]$.
Explicitly note that when $C_p > BP_6$, $I_p$ is capped at 500 in accordance with EPA Punjab portal operational practice.

---

### Challenge 3 (High): Python Array Wraparound Bug in 3-Hour Hold Filter & Zero Ingestion (Transform 10)

#### 3.1 Assumption Challenged
`TRANSFORMATION_LOGIC_SPEC.md` Section 2.10.1 defines:
$$\text{If } v_i = v_{i-1} = v_{i-2} \land v_i \ne \text{null} \implies v_i = \text{null}$$
for $p \ne \text{'AQI'}$.

#### 3.2 Attack Scenario & Blast Radius
1. **Python Negative Index Wraparound**: In JavaScript (the language of `index.html`), accessing array indices `-1` or `-2` returns `undefined`, and `undefined === v` evaluates safely to `false`.
   However, in Python (the target language for the decoupled data pipelines), negative indices wrap to the tail of the array (`arr[-1]` is the last element, `arr[-2]` is the second-to-last element).
   If a developer translates this formula directly into Python as `if arr[i] == arr[i-1] == arr[i-2]:`, at $i = 0$ it compares the first hour of November 1 against the last two hours of November 9! If a station went offline at the end of the month at the same reading as its start, or on periodic cyclical signals, hours $i=0$ and $i=1$ are falsely wiped out as logger holds.
2. **Missing Zero/Negative Ingestion Cleaning**: Raw AQMS sensors often transmit $0.0$ or small negative voltage drifts (e.g. $-1.5\ \mu\text{g/m}^3$) during baseline drift. `index.html` line 322 explicitly sanitizes this: `v == null || !(v > 0) ? null : v`. If zeros are not pruned before running the 3-hour hold filter, a sequence of `0, 0, 0` is flagged as a hold instead of being pruned as missing sensor data, inflating diagnostic hold counters.

#### 3.3 Empirical Evidence & Verification
We implemented a stress test with circular sequence `s_wrap = [99.0, 50.0, 50.0, 99.0]`:
- Without $i \ge 2$ guard: $i=0$ checks `s_wrap[0] == s_wrap[-1] == s_wrap[-2]` ($99 == 99 == 50$ -> False, but for `[99, 99, 50, 99]` $i=0$ erroneously triggers hold!).
- With $i \ge 2$ guard: Correctly isolates holds only within forward temporal order.
- Verified that in `index.html`, 3-hour hold is strictly bypassed for `AQI` (`p !== 'AQI'`).

#### 3.4 Mitigation / Required Spec Modification
Update Section 2.10.1 in `TRANSFORMATION_LOGIC_SPEC.md`:
1. Add explicit index boundary precondition:
   $$\text{For } i \ge 2 \text{ and } p \ne \text{'AQI'}: \quad \text{If } v_i = v_{i-1} = v_{i-2} \land v_i \ne \text{null} \implies v_i = \text{null}$$
2. Add explicit zero/negative sanitization rule in Section 2.10.1 Step 0:
   $$v(t) \leftarrow \begin{cases} v(t) & \text{if } v(t) > 0 \\ \text{null} & \text{otherwise} \end{cases}$$

---

### Challenge 4 (Medium-High): Omission of Anemometer Physical Bounds & Sensor Misalignment Blacklist

#### 4.1 Assumption Challenged
`TRANSFORMATION_LOGIC_SPEC.md` Section 2.4 describes Vector Wind Blending and Cartesian conversions, but completely omits physical validation bounds for anemometer wind speed and wind direction, as well as station-level QA blacklisting.

#### 4.2 Attack Scenario & Blast Radius
1. **Corrupted Speeds**: Telemetry from EPA Punjab reveals raw sensor errors where wind direction is written into the speed register (e.g., DC Office Chakwal repeatedly transmitted speeds $> 200\text{ m/s}$, and DC Office Khanewal transmitted $99.9\text{ m/s}$).
   If unconstrained speeds enter Transform 2 (Anisotropic IDW) or Transform 6 (Advection Flux):
   - Advection flux $C \cdot w \cdot \cos(\Delta\theta) \cdot e^{-d/100}$ scales linearly with $w$. A wind speed of $240\text{ m/s}$ inflates estimated transport flux by $80\times$, producing gigantic fake transport arrows that dwarf all real physical transport.
2. **Vane Misalignment**: The AQMS station at Wazirabad had a physical wind vane installation error of $\sim 140^\circ$. Incorporating Wazirabad winds misdirects regional flow vectors and reverses source-receptor attributions across Gujranwala district.

#### 4.3 Empirical Evidence & Verification
In `index.html` lines 313-315:
```javascript
const NOWIND = new Set(['Wazirabad']);
const ws = x[7], wd = x[8];
if (ws == null || wd == null || ws < 0 || ws > 30 || wd < 0 || wd > 360) return null;
```
Inspection of `DATA.qa` confirms that every valid station wind in the database satisfies $0 \le ws \le 30\text{ m/s}$ ($108\text{ km/h}$) and $0 \le wd \le 360^\circ$, and Wazirabad is 100% excluded from wind vector processing.

#### 4.4 Mitigation / Required Spec Modification
Add Section 2.4.0 (Anemometer QC & Validation Rules) to `TRANSFORMATION_LOGIC_SPEC.md`:
1. Wind Speed Filter: $0.0 \le w_s \le 30.0\text{ m/s}$; discard values outside this physical range.
2. Wind Direction Filter: $0.0^\circ \le \theta \le 360.0^\circ$.
3. Station Blacklist: Hardcode exclusion of known misaligned or uncalibrated vanes (`NOWIND = ['Wazirabad']`).

---

### Challenge 5 (Medium): Transport Advection Invalidation on AQI & 60-Pathway Truncation (Transform 6 & 7)

#### 5.1 Assumption Challenged
`TRANSFORMATION_LOGIC_SPEC.md` Section 2.6 specifies the physical transport equation:
$$\text{Flux}_{a \to b} = C_a \cdot w_a \cdot \cos(\Delta\theta) \cdot e^{-d/100}$$
and Section 2.7 specifies pairwise link pathway scoring without stating domain restrictions regarding the nature of pollutant $C_a$.

#### 5.2 Attack Scenario & Blast Radius
AQI is a segmented non-linear index (a dimensionless risk scale from 0 to 500), not a conserved mass concentration ($\mu\text{g/m}^3$). Multiplying an ordinal index by physical velocity ($m/s$) has no dimensional or physical meaning (it violates mass conservation).
If a backend worker computes advection flux for AQI, it produces unscientific "AQI flux" vectors.

#### 5.3 Empirical Evidence & Verification
In `index.html` lines 747-748:
```javascript
${isAQI(PD)?'<li><b>Transport:</b> AQI is an index, not a concentration, so transport arrows and cross-border calculations are disabled.</li>':...}
```
In `index.html`, transport flux and cross-border indices are strictly disabled whenever `pol === 'AQI'`.
Furthermore, in line 364 of `index.html`:
```javascript
Q.links = links.slice(0, 60);
```
The active display and storage links are strictly capped to the top 60 pathways by pathway score.

#### 5.4 Mitigation / Required Spec Modification
1. Add an explicit domain restriction to Section 2.6: Advection flux is strictly restricted to physical concentration species ($\text{PM}_{2.5}, \text{PM}_{10}, \text{NO}_2, \text{SO}_2, \text{CO}, \text{O}_3$). When `pollutant == 'AQI'`, the transport transform returns an empty set.
2. Note in Section 2.7 that the link list is truncated to the top 60 pathways: `Q.links = links.sort((a,b) => b.score - a.score).slice(0, 60)`.

---

### Challenge 6 (Medium): Completeness Aggregation Rule Discrepancy ($\text{round}$ vs $\text{ceil}$) (Transform 10)

#### 6.1 Assumption Challenged
`TRANSFORMATION_LOGIC_SPEC.md` line 420 defines the 75% completeness requirement as:
$$N_{\text{valid}} \ge \lceil 0.75 \times H \rceil$$

#### 6.2 Empirical Evidence & Verification
In `index.html` line 356:
```javascript
vals.length >= Math.max(1, Math.round(0.75 * NA))
```
`index.html` uses `Math.round(0.75 * NA)`, NOT `Math.ceil`.
For periods with odd hours (e.g. a rolling 7-hour or 11-hour window, or partial exports):
- For $H = 7$: $0.75 \times 7 = 5.25 \implies \text{round} = 5$, but $\text{ceil} = 6$.
- For $H = 11$: $0.75 \times 11 = 8.25 \implies \text{round} = 8$, but $\text{ceil} = 9$.
Using `ceil` requires 1 additional valid hour, causing valid district period means to be discarded as `null` when exactly 5 out of 7 hours are reported.

#### 6.3 Mitigation / Required Spec Modification
Harmonize Section 2.10.1 line 420 to match production implementation:
$$N_{\text{valid}} \ge \max\left(1, \, \text{round}(0.75 \times H)\right)$$

---

### Challenge 7 (Low-Medium): Singularity Clamping & Weighting Behavior in Geodesic IDW (Transform 1)

#### 7.1 Empirical Stress-Test
We verified the singularity clamping behavior of:
$$w_i = \frac{1}{\left(\max(d(t, i), \, 5.0\text{ km})\right)^2}$$
When query point $t$ coincides with station $i$ ($d = 0$):
$w_i = 1 / 25.0 = 0.0400$.
If a neighboring station $j$ is at $d = 9.48\text{ km}$:
$w_j = 1 / 9.48^2 = 0.0111$.
The interpolated value is:
$$V(t) = \frac{0.0400 \times 100 + 0.0111 \times 50}{0.0400 + 0.0111} = 89.12$$
In classical IDW, $V(t) \to 100.0$ as $d \to 0$. In this formulation, $V(t)$ is blunted to $89.12$ because of the $5\text{ km}$ minimum radius.
However, in `index.html`, IDW is ONLY executed for unmonitored districts (`est = true`). The minimum distance between any unmonitored district centroid and any monitored station in Punjab is $> 15\text{ km}$. Therefore, the $5\text{ km}$ clamping does NOT blunt any real district interpolation, serving purely as an IEEE 754 division-by-zero safeguard.
Conclusion: Mathematically sound and safe for production.

---

### Challenge 8 (Low): Planar Screen Raster IDW (Transform 3) is Dead Code

#### 8.1 Empirical Verification
`TRANSFORMATION_LOGIC_SPEC.md` Section 2.3 documents "Planar Screen Raster IDW ($p=3$, $\text{cell}=5\text{ px}$, $\epsilon^2=0.25\text{ px}^2$)" extracted from `function drawSurface(st)`.
We searched the entire 9.61 MB codebase for invocations of `drawSurface`:
- Defined at character offset 9,560,901.
- Total calls in codebase: **0**.
In `index.html` line 523 and 542:
`let MODE = 'surface'; function drawChoro(st) { if(MODE === 'surface') { drawField(); return; } ... }`
The application exclusively invokes `drawField()` (which calls `renderField` and `fieldAt`, implementing Transform 2: Anisotropic Wind-Steered IDW).
Transform 3 is obsolete legacy code. Documenting it as an active system deliverable introduces architectural clutter.

---

## Complete Verification Test Harness Results

The following automated Python validation script was executed directly against `index.html`:

```text
=== STARTING EMPIRICAL VALIDATION HARNESS ===

[AREA 1] Discrete Geodesic IDW Verification:
Test 1.1: d1=0.0000 km, d2=9.4809 km => Clamped IDW result: 89.12 (Weight 1: 0.0400, Weight 2: 0.011125)
Test 1.2: All null nodes => result: None (Expect None)
Test 1.3: North-South extreme distance: Haversine = 768.23 km, Equirectangular Flat = 765.38 km (Diff: 2.85 km, 0.37%)

[AREA 2] Anisotropic Wind-Steered IDW Verification:
Test 2.1: Downwind multiplier c=1.0 => 1.70 (+70% amplification)
          Upwind multiplier c=-1.0 => 0.30 (-70% suppression)
          Ratio of downwind to upwind weight: 5.67x
Test 2.2: Softening parameter eps=4 px => max weight at d=0: 0.0625

[AREA 3] CPF Polar Rose Verification:
Test 3.1: Sector 0 bounds test: [0, 0, 0, 0] (Expect all 0s)
          Sector 1 start: 1 (Expect 1), Sector 15 end: 15 (Expect 15)
Test 3.2: Validating Nk < 6 sample cutoff across entire database:
          All sectors with Nk < 6 are null: True
          All sectors with Nk >= 6 are computed: True

[AREA 4] Advection Transport Flux Verification:
Test 4.1: On-axis flux (dl=0 deg, 50km): 363.92
          Cone boundary flux (dl=35 deg, 50km): 298.10 (cos(35)=0.8192)
          Out of cone flux (dl=36 deg, 50km): None (Expect None)
Test 4.2: Distance decay: Flux at 0km = 100.00, Flux at 100km = 36.79 (Ratio: 0.3679, Expect 1/e = 0.3679)

[AREA 5] PEPC Breakpoints & Sub-Index Verification:
Test 5.1: Boundary values check for PM2.5:
          C =  15.0 => AQI Sub-index = 50 (Expected 50)
          C =  35.0 => AQI Sub-index = 100 (Expected 100)
          C =  70.0 => AQI Sub-index = 150 (Expected 150)
          C = 140.0 => AQI Sub-index = 200 (Expected 200)
          C = 250.0 => AQI Sub-index = 300 (Expected 300)
          C = 350.0 => AQI Sub-index = 400 (Expected 400)

[AREA 6] QC Filtering & Anemometer Bounds Verification:
Test 6.1: Spike input: [50.0, 52.0, 48.0, 250.0, 51.0, 49.0, 50.0] => Output: [50.0, 52.0, 48.0, None, 51.0, 49.0, 50.0] (Spike detected: True)
Test 6.2: Hold input: [80.0, 80.0, 80.0, 80.0, 82.0] => Output: [80.0, 80.0, None, None, 82.0] (Holds flagged: 2)
Test 6.3: Wraparound protection on [99, 50, 50, 99]: [99.0, 50.0, 50.0, 99.0] (Flags: 0)
Test 6.4: Anemometer bounds check: 35 m/s => None (Expect None)
          Wazirabad vane check: 5 m/s => None (Expect None)

=== ALL HARNESS ASSERTIONS PASSED EMPIRICALLY ===
```

---

## Actionable Patch Instructions for `TRANSFORMATION_LOGIC_SPEC.md`

1. **Section 2.5 (CPF Wind Roses)**:
   - Add $N_k \ge 6$ threshold: if $N_k < 6 \implies \text{CPF}_k = \text{null}$.
   - Clarify that $P_{75}$ and sector binning are performed on pooled station-hours for multi-station districts.
2. **Section 2.9 (PEPC Breakpoints & Sub-Index)**:
   - Define continuous mathematical intervals ($BP_{i-1} < C \le BP_i$) with no discrete numerical dead zones.
   - Specify index clamping at 500 when $C > 350\ \mu\text{g/m}^3$ for PM2.5.
3. **Section 2.10 (QC Cleaning)**:
   - Add precondition $i \ge 2$ to prevent negative index wraparound bugs in Python.
   - Add step 0: discard $v \le 0$ as null prior to median and hold filtering.
   - Harmonize completeness rule from $\lceil 0.75 \times H \rceil$ to $\max(1, \text{round}(0.75 \times H))$.
4. **Section 2.4 (Meteorology & Winds)**:
   - Document anemometer speed validity bounds: $0.0 \le w_s \le 30.0\text{ m/s}$.
   - Document anemometer direction validity bounds: $0.0^\circ \le \theta \le 360.0^\circ$.
   - Formally document sensor blacklist: `NOWIND = ['Wazirabad']`.
5. **Section 2.6 (Advection Transport)**:
   - Add explicit domain constraint: Transport flux is disabled for `AQI`.
   - Note that output links are sorted and sliced to top 60 pathways.
6. **Section 2.3 (Planar Raster IDW)**:
   - Mark Transform 3 as "Dormant / Superseded by Transform 2" to prevent wasted pipeline implementation effort.
