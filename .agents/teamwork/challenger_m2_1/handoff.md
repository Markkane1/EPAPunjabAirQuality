# Empirical Adversarial Challenge Report: Milestone M2 (Pure Mathematical Engine)

**Document ID**: `PAQ-HANDOFF-M2-CHALLENGER-1`  
**Agent**: `challenger_m2_1` (Archetype: `teamwork_challenger`, Roles: `critic`, `specialist`)  
**Working Directory**: `c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\challenger_m2_1\`  
**Date**: 2026-11-10T13:45:00Z  
**Type**: Hard Handoff (Challenge Complete)  
**VERDICT**: **REJECT** (Critical empirical defect identified in `src/domain/math/qc.py`)

---

## 1. Observation

### 1.1 Direct Code Inspection
1. **Defective Hold Filter Implementation in `src/domain/math/qc.py` (lines 96–105)**:
   ```python
   # Step 2: 3-Hour Logger Hold (Sensor Freeze) Filter with Index Guard (i >= 2)
   # Physical pollutants only; dimensionless integer 'AQI' is exempt
   if pollutant.strip().upper() != "AQI":
       for i in range(2, n):
           v0 = cleaned[i]
           v1 = cleaned[i - 1]
           v2 = cleaned[i - 2]
           if v0 is not None and v1 is not None and v2 is not None:
               if v0 == v1 == v2:
                   cleaned[i] = None
   ```
   The array `cleaned` is mutated in-place (`cleaned[i] = None`). When `i = 2` triggers a hold, setting `cleaned[2] = None`, the subsequent iteration `i = 3` evaluates `v1 = cleaned[2]`, which is now `None`. The condition `v1 is not None` evaluates to `False`, aborting hold detection for `i = 3` and `i = 4`.

2. **Authoritative Specification (`docs/TRANSFORMATION_LOGIC_SPEC.md` §2.10.1 line 457)**:
   $$\text{For } i \ge 2 \text{ and } p \ne \text{'AQI'}: \quad \text{If } v_i = v_{i-1} = v_{i-2} \land v_i \ne \text{null} \implies v_i = \text{null}$$

3. **Ground Truth Baseline (`original System/index.html` lines 323–327)**:
   ```javascript
   const full = base.concat(rawv), out = rawv.slice();
   for(let k = 0; k < rawv.length; k++){ 
     const i = N0 + k, v = full[i]; 
     if(v == null) continue;
     const win = full.slice(Math.max(0, i - 3), i + 4).filter(x => x != null); 
     const med = win.length >= 3 ? median(win) : null;
     const spk = med != null && v > 4 * med && v > lim;
     const hold = p !== 'AQI' && full[i - 1] === v && full[i - 2] === v;
     if(spk || hold){ out[k] = null; spikes[p] = (spikes[p] || 0) + 1; } 
   }
   ```
   In the reference system, `hold` is evaluated against `full` (the unmutated input series), writing the scrubbed `null` to `out`. Thus, all sustained frozen hours after the first two are purged.

### 1.2 Test Execution Command and Verbatim Failure
- Command: `python -m pytest tests/unit/test_m2_adversarial.py -v`
- Result: `83 passed, 1 failed, 1 warning in 0.20s`
- Verbatim Pytest Failure Output:
  ```
  FAILED tests/unit/test_m2_adversarial.py::TestTemporalQCHoldFilterAndIndexGuard::test_sustained_logger_hold_purging_adversarial
  E       AssertionError: Sustained logger hold leaked frozen data: got [150.0, 150.0, None, 150.0, 150.0]
  E       assert [150.0, 150.0, None, 150.0, 150.0] == [150.0, 150.0, None, None, None]
  E         At index 3 diff: 150.0 != None
  ```

---

## 2. Logic Chain

1. **Step 1 (Sustained Logger Freeze Scenario)**:
   When an optical or electrochemical sensor at an AQMS hardware site freezes (a persistent failure mode documented in Punjab EPA audits), it outputs identical values across multiple consecutive hours (e.g. 5 hours of `150.0 µg/m³`).
2. **Step 2 (Tracing `src/domain/math/qc.py`)**:
   - At iteration $i = 2$: `v0 = cleaned[2] = 150.0`, `v1 = cleaned[1] = 150.0`, `v2 = cleaned[0] = 150.0`. Since `v0 == v1 == v2`, `cleaned[2]` is overwritten with `None`.
   - At iteration $i = 3$: `v0 = cleaned[3] = 150.0`, `v1 = cleaned[2] = None`, `v2 = cleaned[1] = 150.0`. Because `v1 is None`, the block `if v0 is not None and v1 is not None and v2 is not None` evaluates to `False`. `cleaned[3]` remains `150.0`.
   - At iteration $i = 4$: `v0 = cleaned[4] = 150.0`, `v1 = cleaned[3] = 150.0`, `v2 = cleaned[2] = None`. Because `v2 is None`, the block evaluates to `False`. `cleaned[4]` remains `150.0`.
3. **Step 3 (Blast Radius Assessment)**:
   Instead of properly cleaning the 5-hour freeze into `[150.0, 150.0, None, None, None]`, the output array contains `[150.0, 150.0, None, 150.0, 150.0]`. 66% of the frozen, unphysical sensor data is leaked downstream. Downstream spatial IDW interpolation (T1/T2), 24h rolling aggregations (T10), and transport flux calculations (T6) ingest these corrupted numbers as active ground truth.
4. **Step 4 (Remediation Specification)**:
   In `src/domain/math/qc.py`, the hold filter must evaluate against a non-mutating copy of the post-spike series (e.g., `ref_hold = list(cleaned)`), checking `ref_hold[i] == ref_hold[i - 1] == ref_hold[i - 2]` before assigning `cleaned[i] = None`.

---

## 3. Comprehensive Evaluation of Milestone M2 Challenge Areas

| Area | Challenge Point | Empirical Test Result | Status |
|---|---|---|---|
| **Area 1** | Extreme wind speeds ($w_s = 0.0, 0.49, 0.50, 30.0, 31.0\text{ m/s}$, negative, NaN/Inf) | $w_s=0.0 \to$ valid/calm, $0.49 \to$ valid/calm, $0.50 \to$ valid/active, $30.0 \to$ valid, $31.0 \to$ invalid (`None`), $-0.01 \to$ invalid (`None`). Wazirabad blacklist strictly enforced. | **CONFIRMED ROBUST** |
| **Area 2** | Zero distance discrete IDW ($d = 0.0\text{ km}$) | Distance clamped to $d_0 = 5.0\text{ km}$, finite weight $w = 0.04$. Single station recovers exact value ($178.5$). Multi-station analytical weights pass with zero floating-point division errors. | **CONFIRMED ROBUST** |
| **Area 3** | Anisotropic IDW kernel evaluations ($\cos\alpha = -1.0, 0.0, 1.0$) | Downwind $\cos\alpha = +1.0 \implies 1.70$ (+70% boost); Upwind $\cos\alpha = -1.0 \implies 0.30$ (-70% floor); Crosswind $\cos\alpha = 0.0 \implies 1.00$. Screen Y inversion correctly projects northward velocity to $-y$. Opacity taper across $[0, 45, 92.5, 140, 500]\text{ km}$ verified. | **CONFIRMED ROBUST** |
| **Area 4** | CPF small-sample suppression ($N_k < 6 \implies \text{None}, N_k \ge 6 \implies \text{valid}$) | $N_k \in \{0, 1, 2, 3, 4, 5\}$ strictly evaluates to `None`. $N_k = 6$ evaluates to valid probability ($m_k / 6$). Calm winds ($<0.5\text{ m/s}$) strictly excluded from sector bins and tracked in `calm_ratio`. Muted stubs ($10\text{ px}$) generated for suppressed wedges. | **CONFIRMED ROBUST** |
| **Area 5** | Physical advection flux guards ($\text{pollutant} = \text{'AQI'}$, $d > 180\text{ km}$, $\Delta\theta > 35^\circ$) | `pollutant == 'AQI'` strictly disabled (`None`). $d = 180.0\text{ km} \to$ valid, $d = 180.01\text{ km} \to$ `None`. $\Delta\theta = 35.0^\circ \to$ valid, $\Delta\theta = 35.5^\circ \to$ `None`. Top 60 pathway ranking truncation strictly enforced. | **CONFIRMED ROBUST** |
| **Area 6** | Continuous half-open intervals in PEPC AQI, operational 500 cap | Continuous half-open intervals $(BP_{i-1}, BP_i]$ verified across all 6 pollutants. Concentrations $> BP_6$ clamped to operational ceiling of 500. Zero/negative sanitization ($C \le 0 \to \text{None}$, $0.0 \to 0$). Composite AQI strictly $\max(I_{\text{PM2.5}}, I_{\text{PM10}})$. | **CONFIRMED ROBUST** |
| **Area 7** | 3h hold filter with index guard ($i \ge 2$) | Index guard $i \ge 2$ prevents negative array indexing wraparound. AQI is correctly exempt from hold filtering. **DEFECT**: In-place mutation during loop breaks detection for sustained holds $\ge 4$ hours. | **REJECTED (DEFECT FOUND)** |

---

## 4. Caveats

1. **Other Math Modules**: Transforms T1, T2, T4, T5, T6, T7, T8, T9, and T11 exhibit rigorous mathematical fidelity, correct floating-point guards, and zero framework dependencies.
2. **Review-Only Constraint**: In strict adherence to the Challenger archetype constraints, this agent did not modify `src/domain/math/qc.py`. The remediation must be applied by a worker agent.

---

## 5. Conclusion

**Verdict: REJECT Milestone M2.**  
While 8 of the 9 mathematical transformation modules are mathematically sound and survive extreme adversarial fuzzing, `src/domain/math/qc.py` contains an empirical defect that allows sustained hardware logger freezes to leak uncleaned data into the system. Milestone M2 cannot be confirmed until `worker_m2_math` remediates lines 96–105 of `src/domain/math/qc.py` and green-lights the entire adversarial test harness.

---

## 6. Verification Method

To independently reproduce the failure and verify the defect:

1. **Run the Adversarial Test Suite**:
   ```bash
   python -m pytest tests/unit/test_m2_adversarial.py -v
   ```
   *Observed result: 83 passed, 1 failed (`test_sustained_logger_hold_purging_adversarial`).*

2. **Inspect the Defective Code**:
   - File: `src/domain/math/qc.py` lines 96–105.
   - Contrast with reference: `original System/index.html` lines 323–327.

3. **Invalidation Condition**:
   - The REJECT verdict is invalidated once `src/domain/math/qc.py` is updated so that `temporal_qc_clean([150.0, 150.0, 150.0, 150.0, 150.0], 35.0, "PM2.5")` returns `[150.0, 150.0, None, None, None]`, and `python -m pytest tests/unit/test_m2_adversarial.py -v` reports 100% pass (84/84 passed).
