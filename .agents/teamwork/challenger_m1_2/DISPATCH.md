# Task Assignment: Milestone M1 Challenger 2

You are `challenger_m1_2` (Type: `teamwork_challenger`).
Working directory: `c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\challenger_m1_2\`

## Authoritative Specifications
Read:
- `c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\ORIGINAL_REQUEST.md`
- `c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\orchestrator\PROJECT.md`
- `c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\worker_m1_archival\handoff.md`

## Objectives
1. Empirically verify data fidelity and non-destructive archival:
   - Verify that `original System/index.html` is an authentic copy of the legacy application (file size ~9.6 MB) and contains the original `window.DATA`.
   - Verify that `original System/collector/collector.py` is present and intact.
   - Verify that `docs/` files are completely untouched and intact in root.
   - Cross-check `data/baseline/stations.json` against `window.DATA` in `original System/index.html` to confirm 0 lost stations or hallucinated records.
2. Deliver your empirical findings and verdict (CONFIRM / CHALLENGE_FAIL) in `handoff.md` and message the orchestrator.


## 2026-11-10T13:04:00Z
You are challenger_m1_2.
Working directory: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\challenger_m1_2\
Read c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\challenger_m1_2\DISPATCH.md, c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\ORIGINAL_REQUEST.md, c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\orchestrator\PROJECT.md, and c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\worker_m1_archival\handoff.md.

Adversarially challenge Milestone M1. Verify non-destructive archival, bitwise/structural authenticity of original System/index.html and collector/, preservation of docs/, and cross-check baseline datasets against window.DATA. Deliver your verdict (CONFIRM or CHALLENGE_FAIL) in handoff.md and notify the orchestrator.

## 2026-11-11T13:41:29Z
You are Challenger 2 for Milestone 1 (Foundation, Tooling & Design Tokens) of the EPA Punjab Air Quality Workstation.
Working directory: c:\Users\Asif\Downloads\Punjab Air Quality
State folder: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\challenger_m1_2

MANDATORY READING:
- c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\ORIGINAL_REQUEST.md
- c:\Users\Asif\Downloads\Punjab Air Quality\PROJECT.md
- c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\sub_orch_m1\SCOPE.md
- c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\worker_m1\handoff.md

Adversarial Challenge Objectives:
1. Empirically verify production build integrity:
   - Run npm run typecheck (tsc --noEmit) and verify zero errors, warnings, or missing declarations.
   - Run npm run build (tsc && vite build) and inspect dist/: verify bundled HTML, CSS, and JS chunks.
   - Verify that chunks are cleanly separated and no circular imports or chunk warnings occur.
2. Empirically verify layout and styling constraints:
   - Verify 100vw x 100vh CSS Grid container in src/styles/grid.module.css. Check for any overflow leakage or unhandled margins.
   - Verify 0px border-radius, 1px solid hairlines, and absolute absence of drop-shadows or backdrop-filter blurs.
   - Verify that all numbers use font-variant-numeric: tabular-nums in src/styles/typography.css.
   - Verify that zero emojis exist anywhere in source code, HTML, CSS, or titles.
3. Determine your verdict: APPROVE or REJECT.
4. Write your full challenge report to:
   c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\challenger_m1_2\handoff.md
5. Notify the orchestrator with send_message with your verdict.
