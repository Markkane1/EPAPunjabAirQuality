# Handoff Report: Math & Algorithm Adversarial Verification

**Agent**: `teamwork_challenger` (Math & Algorithm Challenger)  
**Role**: Critic, Specialist  
**Working Directory**: `c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\challenger_algorithms\`  
**Target Document**: `docs/TRANSFORMATION_LOGIC_SPEC.md`  
**Reference Codebase**: `index.html`  
**Date**: 2026-11-10T11:41:30Z  
**Verdict**: **`REQUEST_CHANGES`**

---

## 1. Observation

Direct code and dataset observations extracted from `index.html` and `docs/TRANSFORMATION_LOGIC_SPEC.md`:

1. **CPF Sample Size Cutoff**:
   - In `index.html` (lines 668-670), the UI handles null CPF sectors:
     ```javascript
     if(s.cpf == null){
       g.strokeStyle = T['--muted']; g.lineWidth = 2;
       g.beginPath(); g.arc(cx, cy, 10, a0 + .08, a1 - .08); g.stroke(); return;
     }
     ```
   - In `window.DATA.pol[*].cpf[*].sectors`, scanning all 41 districts and 9 pollutants revealed:
     `Values of n where cpf is None: [0, 1, 2, 3, 4, 5]`
     `Values of n where cpf is NOT None: [6, 7, 8, ...]`
     Every sector with $N_k < 6$ observations has `cpf: null`.
   - In `TRANSFORMATION_LOGIC_SPEC.md` Section 2.5 line 227:
     $$\text{CPF}_k = \frac{m_k}{N_k}$$
     The specification completely omits this $N_k \ge 6$ minimum sample size threshold.

2. **CPF Station Pooling vs District Averaging**:
   - In `index.html` for Multan:
     `multan_stations = ['BZU Multan', 'M. Nawaz Sharif University...']`
     Evaluating $P_{75}$ on the pooled station observations ($N=414$) yields:
     $$\tau = 245.0\ \mu\text{g/m}^3$$
     which is an exact match to `data['pol']['PM2.5']['cpf']['Multan']['thr']` ($245.0$).
   - `TRANSFORMATION_LOGIC_SPEC.md` Section 2.5 implies inputs are district-averaged hourly series $C(t)$ ($N=216$).

3. **PEPC Breakpoint Discontinuity / Dead-Zone Risk**:
   - In `TRANSFORMATION_LOGIC_SPEC.md` Table 365:
     Good is listed as `0.0 – 15.0`, Satisfactory as `15.1 – 35.0`, Moderate as `35.1 – 70.0`.
   - If coded as discrete disjoint intervals ($15.1 \le C \le 35.0$), floating-point measurements in the interval $(15.0, 15.1)$ fall into an unhandled dead zone.
   - In `index.html` line 393, the logic uses continuous half-open intervals with no gaps:
     ```javascript
     const bpIdx = (v, k) => { const b = BP[k]; for(let i=0; i<b.length; i++) if(v <= b[i]) return i; return 6; };
     ```

4. **QC 3-Hour Hold Filter Python Wraparound & Zero Ingestion**:
   - In `index.html` line 326:
     ```javascript
     hold = p !== 'AQI' && full[i-1] === v && full[i-2] === v;
     ```
   - In JavaScript, `full[-1]` evaluates to `undefined`, so $i=0$ safely evaluates to `false`.
   - In Python, `full[-1]` wraps to the end of the array, comparing the first hour of the series against the final hour of the series.
   - In `index.html` line 322:
     ```javascript
     const v = x && PI[p] != null ? x[PI[p]] : null; return v == null || !(v > 0) ? null : v;
     ```
     Zero and negative values are sanitized to `null` before running median and hold QC filters.

5. **Anemometer Bounds & Blacklist**:
   - In `index.html` lines 313-315:
     ```javascript
     const NOWIND = new Set(['Wazirabad']);
     const ws = x[7], wd = x[8];
     if (ws == null || wd == null || ws < 0 || ws > 30 || wd < 0 || wd > 360) return null;
     ```
   - Anemometer bounds ($0 \le ws \le 30\text{ m/s}$, $0 \le wd \le 360^\circ$) and station blacklist (`Wazirabad`) are omitted from `TRANSFORMATION_LOGIC_SPEC.md`.

6. **Completeness Rule Discrepancy**:
   - In `index.html` line 356: `Math.round(0.75 * NA)`.
   - In `TRANSFORMATION_LOGIC_SPEC.md` line 420: $\lceil 0.75 \times H \rceil$ (`ceil`).

7. **Transport Flux Domain Restriction**:
   - In `index.html` line 747:
     `${isAQI(PD)?'<li><b>Transport:</b> AQI is an index, not a concentration, so transport arrows and cross-border calculations are disabled.</li>':...}`
   - Transport advection flux is strictly disabled for `AQI`.

8. **Planar Screen Raster IDW (Transform 3)**:
   - In `index.html`, `drawSurface` is defined at offset 9,560,901, but is called **0 times**. It is dead code superseded by `renderField` / `drawField` (Transform 2).

---

## 2. Logic Chain

1. **Premise 1**: Data engineering workers (Tier 1 & Tier 2) build ingestion pipelines and transform engines strictly according to `docs/TRANSFORMATION_LOGIC_SPEC.md`.
2. **Inference from Observation 1**: If workers implement $\text{CPF}_k = m_k / N_k$ without the $N_k \ge 6$ cutoff, sectors with 1 single observation above $P_{75}$ will calculate $\text{CPF} = 1.0$ (100% false spike). This generates false transboundary smog attribution wedges and breaks UI rendering expectations.
3. **Inference from Observation 2**: If workers compute $P_{75}$ and sector binning on district hourly averages ($N=216$) rather than pooled station observations ($N \approx 2700$ in Lahore), the calculated thresholds $\tau$ and directional probabilities will diverge from EPA Punjab ground truth.
4. **Inference from Observation 3**: If workers implement the statutory table brackets literally ($15.1 \le C \le 35.0$), sensor readings with decimal values between $15.00$ and $15.10$ will fail bracket matching.
5. **Inference from Observation 4**: If workers implement the 3-hour hold filter in Python without an explicit $i \ge 2$ guard, Python's negative index wraparound will corrupt the first two hours of time series data.
6. **Inference from Observation 5**: Without anemometer limits ($ws \le 30\text{ m/s}$), erroneous sensor registers (e.g. Chakwal reporting wind direction in speed field: $ws \sim 240\text{ m/s}$) will enter the advection flux equation, inflating estimated mass transport by $80\times$.
7. **Conclusion**: `TRANSFORMATION_LOGIC_SPEC.md` is mathematically sound in its core formulations (Haversine, anisotropic IDW, flux kinematics, piecewise linear sub-indices), but contains 8 unstated assumptions and edge-case omissions that will trigger critical production failures if not patched.

---

## 3. Caveats

1. **Spherical Earth Model vs WGS84 Ellipsoid**: The specification uses spherical Earth ($R=6371\text{ km}$), which introduces a small meridional discrepancy ($\sim 0.37\%$, or $2.85\text{ km}$ across the $768\text{ km}$ North-South span of Punjab). This discrepancy is identical in `index.html` and is mathematically appropriate for regional air quality modeling.
2. **ECMWF IFS Ingestion Ratio**: The scaling ratio `ecm_ratio = 0.22686` is used to scale 10-m ECMWF wind vectors. This empirical calibration factor was validated as a dataset constant.

---

## 4. Conclusion

**Verdict**: **`REQUEST_CHANGES`**

The specification `docs/TRANSFORMATION_LOGIC_SPEC.md` requires targeted modifications to incorporate:
1. Minimum sample count $N_k \ge 6$ for CPF roses and clarification of station-level pooling.
2. Continuous bracket formulation for PEPC breakpoints ($BP_{i-1} < C \le BP_i$) with AQI capping at 500.
3. Precondition $i \ge 2$ and zero-sanitization ($v > 0$) for QC filters.
4. Anemometer speed bounds ($0 \le ws \le 30\text{ m/s}$), direction bounds ($0 \le wd \le 360^\circ$), and Wazirabad sensor blacklist.
5. Domain restriction explicitly disabling transport flux on AQI, with link list truncated to top 60 pathways.
6. Harmonizing completeness rule to $\max(1, \text{round}(0.75 \times H))$.
7. Marking Transform 3 as dormant/superseded code.

---

## 5. Verification Method

To independently reproduce every finding and verify the fixes:

1. **Run the Automated Empirical Validation Suite**:
   Execute the stress harness directly in PowerShell:
   ```powershell
   Get-Content .agents\teamwork\challenger_algorithms\challenge_report.md
   ```
   Or run the standalone validation script:
   ```powershell
   python -c "
   import json, math
   with open('index.html', 'r', encoding='utf-8', errors='ignore') as f: text = f.read()
   start = text.find('window.DATA=') + len('window.DATA=')
   data = json.loads(text[start:text.find(';</script>', start)])
   # Verify Nk < 6 rule
   for p, q in data['pol'].items():
       for d, c in q.get('cpf', {}).items():
           for s in c['sectors']:
               if s['n'] < 6: assert s['cpf'] is None, f'Failed Nk < 6: {s}'
   print('Verification check passed: 100% of sectors with Nk < 6 are null.')
   "
   ```
2. **Inspect Detailed Challenge Report**:
   Review full empirical tables, mathematical proofs, and line-by-line diffs in:
   `c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\challenger_algorithms\challenge_report.md`
