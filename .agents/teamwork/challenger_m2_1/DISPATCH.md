## 2026-11-10T13:33:48Z

You are challenger_m2_1 (Archetype: teamwork_challenger). Your working directory is c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\challenger_m2_1\

MANDATORY FIRST STEP: Read the following authoritative documents before testing:
1. c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\ORIGINAL_REQUEST.md
2. c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\orchestrator\PROJECT.md
3. c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\spec_miner_math\handoff.md
4. c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\worker_m2_math\handoff.md
5. docs/TRANSFORMATION_LOGIC_SPEC.md

CHALLENGE OBJECTIVE:
Perform empirical adversarial testing and stress verification of Milestone M2 pure mathematical modules in `src/domain/math/`.
Stress-test:
- Extreme boundary conditions ($w_s = 0.0, 0.49, 0.50, 30.0, 31.0\text{ m/s}$).
- Zero distance queries ($d = 0.0\text{ km}$) for discrete IDW.
- Upwind/downwind anisotropic IDW kernel evaluations ($\cos\alpha = -1.0, 0.0, 1.0$).
- Small-sample sector suppression ($N_k = 0, 1, 5 \implies \text{None}$; $N_k = 6 \implies \text{valid}$).
- Physical advection flux with $\text{pollutant} = 'AQI'$ (must return None), distance $>180\text{ km}$, angle $>35^\circ$.
- Continuous half-open intervals in PEPC AQI, operational 500 ceiling clamp, zero/negative suppression.
- 3h hold filter with $i \ge 2$ index boundary guard.
Write an adversarial test file in `tests/unit/test_m2_adversarial.py` and run `python -m pytest tests/unit/test_m2_adversarial.py -v`.
Deliver verdict: CONFIRM or REJECT in handoff.md and send a message when done.
