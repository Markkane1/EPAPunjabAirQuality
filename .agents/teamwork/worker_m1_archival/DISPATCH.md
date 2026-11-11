# Task Assignment: Milestone M1 — Workspace Archival & Baseline Extraction

You are `worker_m1_archival` (Type: `teamwork_worker`).
Your working directory is: `c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\worker_m1_archival\`

## Authoritative Specifications
You MUST read:
1. `c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\ORIGINAL_REQUEST.md`
2. `c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\orchestrator\PROJECT.md`
3. `c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\explorer_survey_existing\handoff.md`

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## File Ownership
You exclusively own:
- `original System/` (directory creation and destination for archival)
- `data/baseline/` (destination for extracted baseline JSON files)
- `tests/unit/test_archival_and_baseline.py` (verification test)

Do NOT modify `docs/` or `.agents/`.

## Objectives
1. **Archive Legacy Artifacts (Requirement R1)**:
   - Create directory `original System/` at the project root (`c:\Users\Asif\Downloads\Punjab Air Quality\original System\`).
   - Move `index.html` and the `collector/` directory into `original System/`.
   - Preserve `docs/` and `.agents/` in the project root intact.
2. **Baseline Data Extraction (Requirement R2 Baseline)**:
   - From `original System/index.html` (which has `window.DATA`), extract and write clean, structured baseline JSON files to `data/baseline/`:
     - `data/baseline/stations.json`: Catalog of all 79 stations with station ID, name, district, latitude, longitude, and network type (fixed vs mobile).
     - `data/baseline/districts.json`: Catalog of all 41 districts with centroid coordinates, monitoring status (`est: false`), station mappings, and boundary coordinates.
     - `data/baseline/airports.json`: Metadata for 6 airports (OPLA, OPFA, OPMT, OPST, OPIS, VIAR) with coordinates.
     - `data/baseline/baseline_data.json`: Structured historical baseline dataset covering the 216 hours (meta, hourly station readings, district summaries, airport wind vectors, and transboundary geometry).
3. **Automated Verification**:
   - Write an automated unit test `tests/unit/test_archival_and_baseline.py` (using `pytest` or Python standard `unittest`).
   - Run the test suite using `run_command` and confirm:
     - `original System/index.html` exists and `collector/` is inside `original System/`.
     - `index.html` and `collector/` no longer exist at project root.
     - `docs/` exists at project root.
     - `data/baseline/stations.json` loads and contains 79 stations across 41 districts.
     - `data/baseline/districts.json` loads and contains 41 districts.
     - `data/baseline/baseline_data.json` loads and contains 216 hourly frames.
4. **Handoff**:
   - Document all actions, file paths, test commands, and passing output in `handoff.md` in your working directory.
   - Send a message to the orchestrator when finished.


## 2026-11-10T12:53:29Z
You are worker_m1_archival.
Working directory: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\worker_m1_archival\
Read c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\worker_m1_archival\DISPATCH.md, c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\ORIGINAL_REQUEST.md, c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\orchestrator\PROJECT.md, and c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\explorer_survey_existing\handoff.md.

MANDATORY INTEGRITY WARNING: DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Execute Milestone M1:
1. Archive index.html and collector/ into original System/ at project root, preserving docs/ and .agents/ at root.
2. Extract baseline datasets (stations.json with 79 stations, districts.json with 41 districts, airports.json, baseline_data.json) into data/baseline/.
3. Write automated verification test tests/unit/test_archival_and_baseline.py and run it.
4. Report results in handoff.md and notify the orchestrator.
