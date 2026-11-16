## 2026-11-14T09:12:13Z

## Task Assignment: Milestone M1-M2 Remediation Worker (Iteration 2)

### Working Directory
`c:\Users\Asif\Downloads\Punjab Air Quality`

### State Folder
`c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\worker_m1m2_r2_1`

### Authoritative Files to Read
- `c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\ORIGINAL_REQUEST.md`
- `c:\Users\Asif\Downloads\Punjab Air Quality\PROJECT.md`
- `c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\orchestrator_2\SCOPE.md`
- `c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\orchestrator_2\GATE_STATUS.md`
- `c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\auditor_m1m2_1\handoff.md`
- `c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\explorer_m1m2_r2_1\handoff.md` (COMPLETE STEP-BY-STEP REMEDIATION PLAN)

### Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

### Your Exclusive Write Boundaries
- `postcss.config.js` (delete)
- `tailwind.config.js` (delete)
- `src/main.tsx` (remove shadcn.css import)
- `src/styles/shadcn.css` (delete)
- `src/workstation.html` (replace banned fonts with IBM Plex, remove tailwind classes)
- `tests/unit/test_archival_and_baseline.py` (permit Vite root index.html via size guard < 100KB)
- `tests/unit/test_m1_adversarial_challenge.py` (permit Vite root index.html via size guard < 100KB)
- `src/domain/normalizer/dataNormalizer.ts` (fix `stationId = raw.id ?? raw.station_id` blacklist check; fix `aerodromeWindCopy` bounds check)
- `tests/unit/test_challenger_m1m2.ts` (synchronize test assertions with updated normalizer)
- `src/components/common/icons.tsx` (create bespoke 1.25px stroke, miter-joined inline SVGs for 23 glyphs)
- `src/lib/utils.ts` (refactor `cn` to use `clsx` directly)
- `src/components/theme-switch.tsx`, `src/components/ui/dialog.tsx`, `src/components/ui/select.tsx`, `src/components/ui/sheet.tsx`, `src/workstation/WorkstationView.tsx` (update imports to `@/components/common/icons`)
- `src/domain/math/ambient.d.ts` (delete evasion file)
- `src/frontend/dashboard.html` (purge Unicode emojis)

### Execution Steps
Follow the exact 4-phase technical plan in `explorer_m1m2_r2_1/handoff.md`:
1. Phase 1: Build Blocker & Banned Styling Purge.
2. Phase 2: Synchronize Legacy Archival Unit Tests.
3. Phase 3: Defensive Normalizer Edge Cases.
4. Phase 4: Clean Up Ambient Evasion & Implement Bespoke Inline SVGs.

### Verification Execution Requirements
Run all commands and document verbatim outputs in `handoff.md`:
1. `npm run build` (`tsc && vite build`) — MUST succeed cleanly with exit code 0.
2. `python -m pytest tests/unit/` — all 292 tests MUST pass with 0 failures.
3. `npx tsx tests/unit/test_challenger_m1m2.ts` — all empirical challenges MUST pass.
4. `python tests/challenge_contrast.py` — 56/56 AAA pairs pass, 0 banned items.
5. `python tests/e2e/run_all_tests.py` — 50/50 backend E2E tests pass.
6. Verify `src/domain/math/ambient.d.ts` is deleted and 0 imports of `lucide-react` or `tailwind-merge` remain in `src/`.

Write report to `handoff.md` and send message upon completion.
