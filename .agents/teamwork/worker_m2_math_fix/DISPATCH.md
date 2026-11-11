## 2026-11-10T13:47:57Z
You are worker_m2_math_fix (Archetype: teamwork_worker). Your working directory is c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\worker_m2_math_fix\

MANDATORY FIRST STEP: Read the following authoritative documents before modifying any code:
1. c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\ORIGINAL_REQUEST.md
2. c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\orchestrator\PROJECT.md
3. c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\reviewer_m2_2\handoff.md
4. c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\challenger_m2_1\handoff.md
5. c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\challenger_m2_2\handoff.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

REMEDIATION OBJECTIVE:
Apply the 3 exact fixes identified in Milestone M2 Verification Gate:
1. In `src/domain/math/qc.py` lines 96–104:
   In Step 2 of `temporal_qc_clean` (the 3-hour logger hold filter), snapshot `pre_hold = list(cleaned)` before entering the loop. Inside the loop (`for i in range(2, n)`), read `v0 = pre_hold[i]`, `v1 = pre_hold[i - 1]`, `v2 = pre_hold[i - 2]`. If `v0 is not None and v1 is not None and v2 is not None and v0 == v1 == v2`: set `cleaned[i] = None`. This ensures that sustained sensor freeze events of 4, 5, 12, or more hours have all frozen readings from index 2 onward purged to `None`.
2. In `src/domain/math/pepc_aqi.py` line 11:
   Add `Any` to `from typing import Any, Dict, List, Optional, Tuple, Union`.
3. In `src/domain/math/idw.py` line 247:
   Apply the upper bound clamp: `mult = min(MAX_ANISOTROPIC_MULTIPLIER, max(MIN_ANISOTROPIC_MULTIPLIER, psi))`.
4. In `tests/unit/test_qc_filters.py`:
   Add test cases for sustained holds of 4, 5, and 12 consecutive hours asserting that all values from index 2 onward are purged to `None`.

TESTING REQUIREMENTS:
1. Run `python -m pytest tests/unit/test_qc_filters.py -v`
2. Run `python -m pytest tests/unit/test_m2_adversarial.py -v` (verify all 84 pass)
3. Run `python -m pytest tests/unit/test_m2_adversarial_challenge.py -v` (verify all 22 pass)
4. Run `python -m pytest tests/ -v` (verify all 198+ tests pass with zero failures and zero regressions)
5. Keep progress.md updated in your working directory.
6. When complete, write handoff.md following the Handoff Protocol and message back.
