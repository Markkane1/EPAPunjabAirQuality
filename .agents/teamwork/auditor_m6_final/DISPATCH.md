## 2026-11-11T10:20:58Z
You are auditor_m6_final (teamwork_auditor).
Your working directory is: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\auditor_m6_final

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All verifications must be authentic. A forensic audit verdict of INTEGRITY VIOLATION acts as a binary veto.

Context and References:
- ORIGINAL_REQUEST: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\ORIGINAL_REQUEST.md
- PROJECT.md: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\orchestrator\PROJECT.md
- TEST_READY.md: c:\Users\Asif\Downloads\Punjab Air Quality\TEST_READY.md

Your Objective:
Execute the Final Forensic Integrity Audit across the entire codebase and test infrastructure:
1. R1 Archival Integrity Check:
   - Verify `original System/index.html` and `original System/collector/` exist.
   - Verify NO `index.html` exists in the workspace root or anywhere in `src/`.
2. Production AST & Import Analysis:
   - Perform AST parsing and string scan across all `.py` files in `src/`.
   - Verify 0 imports of `mock`, `MagicMock`, `unittest.mock`, `sinon`, or test doubles.
3. Facade, Stub & Placeholder Scan:
   - Scan all source files in `src/` (Python, JS, CSS, HTML) for `TODO`, `FIXME`, `dummy`, `stub`, `placeholder`, or `NotImplemented`.
   - Confirm all algorithms and services are genuine implementations.
4. Anti-Cheating & Tautology Audit:
   - Scan all test files in `tests/` for vacuous assertions (`assert True`, `assert 1 == 1`, empty test functions).
   - Verify 0 skipped or xfailed tests.
5. Empirical Execution:
   - Run `python tests/e2e/run_all_tests.py` (verify 50/50 opaque-box tests pass).
   - Run `python -m pytest tests/ -q` (verify all 641 tests pass).
6. Document your findings, execution evidence, and final verdict (**CLEAN** or **INTEGRITY VIOLATION**) in:
   `c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\auditor_m6_final\handoff.md`
7. Send a completion message back to the orchestrator.
