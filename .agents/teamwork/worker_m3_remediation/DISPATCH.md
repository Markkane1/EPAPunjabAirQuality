## 2026-11-11T04:16:36Z
You are worker_m3_remediation (Archetype: teamwork_worker).
Working directory: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\worker_m3_remediation\
Project root: c:\Users\Asif\Downloads\Punjab Air Quality
Original request path: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\ORIGINAL_REQUEST.md
Scope document: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\orchestrator\PROJECT.md
Defect report path: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\challenger_m3_1_gen2\handoff.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Your task is to remediate the defect discovered by challenger_m3_1_gen2 in Milestone M3:
Target file to fix: src/pipelines/csv_adapter.py

Defect details:
In `src/pipelines/csv_adapter.py` at line 220:
`val = raw_row.get(col_orig, "").strip()`
When a user-supplied CSV has a partial or ragged line with fewer columns than the header, Python's `csv.DictReader` assigns `None` to the missing keys in `raw_row`. Because `col_orig` is in `raw_row` with value `None`, `raw_row.get(col_orig, "")` returns `None`. Calling `.strip()` on `None` raises an unhandled `AttributeError: 'NoneType' object has no attribute 'strip'`, crashing the adapter and preventing the Dead-Letter Quarantine (DLQ) from isolating the row non-haltingly.

Remediation steps:
1. In `src/pipelines/csv_adapter.py` (around line 220), safely handle `None` values:
   ```python
   raw_val = raw_row.get(col_orig)
   val = raw_val.strip() if raw_val is not None else ""
   ```
   (or `val = (raw_row.get(col_orig) or "").strip()`).
2. In addition, around line 161 where byte streams are handled:
   Auto-detect UTF-16 BOM prefixes so UTF-16 byte streams are decoded cleanly:
   ```python
   elif isinstance(source, bytes):
       if source.startswith((b"\xff\xfe", b"\xfe\xff")):
           text_data = source.decode("utf-16", errors="replace")
       else:
           text_data = source.decode("utf-8-sig", errors="replace")
   ```
3. Run the specific adversarial test:
   `python -m pytest tests/integration/test_m3_adversarial.py -k test_csv_partial_lines_and_ragged_rows -v`
4. Run the full adversarial test suite:
   `python -m pytest tests/integration/test_m3_adversarial.py -v` (must be 33 passed)
5. Run the full workspace test suite:
   `python -m pytest tests/ -v` (must be 376 passed with 0 failures)

Deliver your handoff report in:
c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\worker_m3_remediation\handoff.md
When done, send a message to orchestrator with your results and test outcomes.
