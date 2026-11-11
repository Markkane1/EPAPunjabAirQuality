# Adversarial Stress Testing & Empirical Challenge Report: Milestone M3

**Target Milestone**: M3: Data Pipelines & CSV Ingestion Engine  
**Agent**: `challenger_m3_1_gen2` (Archetype: `teamwork_challenger`)  
**Verdict**: **REQUEST_CHANGES**  
**Test Suite Created**: `tests/integration/test_m3_adversarial.py` (33 test cases)

---

## 1. Observation

### 1.1 Empirical Defect: Unhandled `AttributeError` on Ragged / Partial CSV Lines
- **Target File**: `src/pipelines/csv_adapter.py`
- **Line Number**: 220
- **Verbatim Code**:
  ```python
  215:         for row_idx, raw_row in enumerate(reader, start=2):  # 1-indexed, line 2 is first data row
  216:             total_rows += 1
  217:             # Normalize dictionary keys
  218:             clean_row: Dict[str, Any] = {}
  219:             for col_clean, col_orig in header_map.items():
  220:                 val = raw_row.get(col_orig, "").strip()
  ```
- **Trigger Input**:
  A user-supplied CSV file containing any row with fewer columns than defined in the header, e.g.:
  ```csv
  timestamp,station_id,station_name,district,latitude,longitude,pollutant,value
  2026-11-10T12:00:00Z,PK_01,Town Hall,Lahore,31.56,74.31,pm25,120.0
  2026-11-10T12:00:00Z,PK_02,Truncated Row
  2026-11-10T12:00:00Z,PK_03,Faisalabad Node,Faisalabad,31.42,73.08,pm25,150.0
  ```
- **Execution Command**:
  ```powershell
  python -m pytest tests/integration/test_m3_adversarial.py -k test_csv_partial_lines_and_ragged_rows -v
  ```
- **Verbatim Error Output**:
  ```
  FAILED tests/integration/test_m3_adversarial.py::TestUserCSVAdapterEncodingsAndDelimiters::test_csv_partial_lines_and_ragged_rows - AttributeError: 'NoneType' object has no attribute 'strip'

      for row_idx, raw_row in enumerate(reader, start=2):
          total_rows += 1
          clean_row: Dict[str, Any] = {}
          for col_clean, col_orig in header_map.items():
  >           val = raw_row.get(col_orig, "").strip()
  E           AttributeError: 'NoneType' object has no attribute 'strip'

  src\pipelines\csv_adapter.py:220: AttributeError
  ```

### 1.2 Full Test Suite Results
- Executing `python -m pytest tests/integration/test_m3_adversarial.py -v`:
  - Total Tests: 33
  - **Passed**: 32
  - **Failed**: 1 (`test_csv_partial_lines_and_ragged_rows`)
- Executing the entire workspace test suite `python -m pytest tests/ -v`:
  - Total Tests: 376
  - **Passed**: 375
  - **Failed**: 1 (`test_csv_partial_lines_and_ragged_rows`)

### 1.3 Secondary Observation: UTF-16 Byte Streams
- **Target File**: `src/pipelines/csv_adapter.py`, lines 151, 157, 162, 166.
- In `UserCSVIngestionAdapter.ingest_csv()`, input byte streams and file readers strictly decode using `"utf-8-sig"` with `errors="replace"`:
  ```python
  text_data = source.decode("utf-8-sig", errors="replace")
  ```
- When a user uploads a genuine UTF-16 LE/BE CSV byte stream (e.g. exported from Microsoft Excel on Windows "Unicode Text (.txt / .csv)" prefixed with `\xff\xfe` or `\xfe\xff`), decoding as `utf-8-sig` inserts null bytes (`\x00`), causing column detection to fail and returning:
  ```python
  file_errors=["Missing mandatory CSV columns: ['district', 'latitude', 'longitude', 'pollutant', 'station_id', 'station_name', 'timestamp', 'value']"]
  ```
- While this fails safely without raising an unhandled exception, auto-sniffing UTF-16 BOM markers (`source.startswith((b'\xff\xfe', b'\xfe\xff'))`) would allow UTF-16 files to be ingested seamlessly.

---

## 2. Logic Chain

1. **Requirement & Contract**:
   According to `DATA_PIPELINES_ARCHITECTURE.md` §2 & §4, `ORIGINAL_REQUEST.md` §R2, and the dispatch focus areas:
   - The user CSV engine must provide a **Non-halting quarantine Dead-Letter Queue (DLQ)**.
   - Individual malformed or incomplete rows must be trapped into `QuarantineRecord` objects with descriptive error diagnostics.
   - Valid rows in the same batch must continue processing and be admitted to `valid_observations` without halting or crashing the batch.
2. **Standard Library `csv.DictReader` Behavior**:
   In Python's standard `csv.DictReader`, when a row contains fewer delimited columns than the header `fieldnames`, missing fields are populated in the dictionary with value `None` (mapped to the corresponding header keys).
3. **Flawed Default Handling**:
   In `src/pipelines/csv_adapter.py:220`, the code retrieves values using `raw_row.get(col_orig, "").strip()`.
   Because `col_orig` exists as a key in `raw_row` with value `None`, `dict.get(key, default)` returns `raw_row[key]` (which is `None`), completely bypassing the default fallback `""`.
4. **Unhandled Crash**:
   Calling `.strip()` on `None` raises `AttributeError: 'NoneType' object has no attribute 'strip'`.
5. **System Impact**:
   This unhandled exception bubbles up and terminates the entire `ingest_csv()` execution. Any valid observations before or after the truncated row are discarded, violating the non-halting DLQ contract.

---

## 3. Caveats

- **Scope Covered**:
  All required focus areas were empirically tested:
  1. `FallbackTemplateEngine` failure modes (missing directory, missing files, corrupt JSON, extreme hour index clamping, unknown identifiers, 79 station conformance, 41 Open-Meteo forecasts, unmapped SYNOP stations).
  2. Ingestion worker resilience (EPA Punjab connection refuse & malformed JSON, METAR timeouts, SYNOP HTTP 429 backoff, Open-Meteo HTTP 500).
  3. `BaseIngestionWorker` circuit breaker exact 5-failure threshold, 900s fail-fast cooldown, HALF-OPEN trial execution, recovery on success, and re-tripping on failure.
  4. `UserCSVIngestionAdapter` security (SQL injection, path traversal, 5000-char names, invalid data types).
  5. `UserCSVIngestionAdapter` geographic boundaries ($[27.0, 35.0]$, $[69.0, 76.0]$), OneNetwork Station 25 exclusion, 8 canonical station repairs, Step 0 negative/zero purges, and $>1000$ / $>1500$ `QC_EXCEEDANCE_EXTREME` tagging.
- **Out of Scope**:
  Streaming multi-gigabyte CSV files line-by-line using chunked generators was not tested, as the current architecture operates on in-memory batch buffers per M3 specifications.

---

## 4. Conclusion & Actionable Verdict

### Verdict: **REQUEST_CHANGES**

The M3 implementation is largely well-engineered (375 passing tests across all modules, mathematically sound circuit breaker, rigorous baseline fallback engine, robust spatial boundary enforcement, and accurate canonical coordinate repair).

However, Milestone M3 **cannot be confirmed** until the critical partial line / ragged row crash is resolved:

### Required Remediation

In `src/pipelines/csv_adapter.py` at line 220, replace:
```python
val = raw_row.get(col_orig, "").strip()
```
with:
```python
raw_val = raw_row.get(col_orig)
val = raw_val.strip() if raw_val is not None else ""
```
*(or `val = (raw_row.get(col_orig) or "").strip()`)*

### Recommended Enhancement (Optional)
In `src/pipelines/csv_adapter.py` around line 161, auto-detect UTF-16 byte streams:
```python
elif isinstance(source, bytes):
    if source.startswith((b"\xff\xfe", b"\xfe\xff")):
        text_data = source.decode("utf-16", errors="replace")
    else:
        text_data = source.decode("utf-8-sig", errors="replace")
```

---

## 5. Verification Method

To independently verify the defect and its eventual resolution:

1. **Execute the adversarial partial line test**:
   ```powershell
   python -m pytest tests/integration/test_m3_adversarial.py -k test_csv_partial_lines_and_ragged_rows -v
   ```
   - **Current Output**: Fails with `AttributeError: 'NoneType' object has no attribute 'strip'` at `src/pipelines/csv_adapter.py:220`.
   - **Expected Output after fix**: `1 passed in 0.XXs`.

2. **Execute the full M3 adversarial test harness**:
   ```powershell
   python -m pytest tests/integration/test_m3_adversarial.py -v
   ```
   - **Expected Output after fix**: `33 passed in ~8s`.

3. **Execute the full workspace test suite**:
   ```powershell
   python -m pytest tests/ -v
   ```
   - **Expected Output after fix**: `376 passed in ~35s`.
