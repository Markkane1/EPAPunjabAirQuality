# DISPATCH: Worker 4 (Final Remediation & Full Verification Worker)
Date: 2026-11-15T18:58:00Z
Target: Finalize WCAG AAA contrast in `src/workstation/state.ts`, execute all verification suites (pytest, e2e runner, typecheck, check:workstation, build), and deliver handoff report.


## 2026-11-15T18:58:19Z
Sender: 18f114c0-d178-4f99-85d5-04eaae8c00bb
Content:
You are Worker 4: Final Remediation & Full Verification Worker.
Your mission is to finalize all remaining pre-production fixes, run the complete verification suites, and deliver the final handoff report.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

MANDATORY FIRST STEP: Read the original user request at:
c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\ORIGINAL_REQUEST.md

Action Plan and References:
- Remediation Plan R2: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\orchestrator_1\REMEDIATION_PLAN_R2.md
- Auditor Evidence: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\auditor_1\handoff.md
- Reviewer 2 Evidence: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\reviewer_2\handoff.md

Tasks to execute:
1. In `src/workstation/state.ts` (lines 155-165):
   Update `pepcColorForAqi`:
   Change:
   `const text = aqi >= 101 && aqi <= 200 ? '#111827' : '#FFFFFF';`
   To:
   `const text = aqi <= 300 ? '#000000' : '#FFFFFF';`
   This guarantees that:
   - Tiers 0-300 (Good, Satisfactory, Moderate, Poor) have black ink `#000000`, achieving 9.5:1 to 19.5:1 contrast against their backgrounds (satisfies WCAG AAA >= 7.0:1).
   - Tiers 301+ (Very Poor, Hazardous) have white ink `#FFFFFF`, achieving >= 7.0:1 contrast against dark red/maroon backgrounds (satisfies WCAG AAA >= 7.0:1).
2. Confirm that:
   - `src/pipelines/cams.py` lines 118-120 and 163-165 set `self.is_healthy = False` on failure.
   - `tests/integration/test_m4_concurrency_stress.py` lines 166-170 wrap the surface cache write/read in `with repo._lock:`.
   - `package.json` contains `"@radix-ui/react-avatar": "^1.1.1"`.
   - `src/frontend/static/` has zero prohibited emojis.
3. Run the complete verification suites:
   - `python -m pytest` (must pass 100% with 0 failures across all 757 tests).
   - `python tests/e2e/run_all_tests.py` (must pass 100% with 144/144 passed across Tiers 1-5B).
   - `npm run check:workstation` (must pass with `render-ok`).
   - `npm run typecheck` (must pass with 0 errors).
   - `npm run build` (must pass with clean Vite production build).
4. Write your comprehensive completion report to:
   `c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\worker_4\handoff.md`
   Document all verified tests, commands, and outputs.
5. Send a brief message back to orchestrator upon completion.
