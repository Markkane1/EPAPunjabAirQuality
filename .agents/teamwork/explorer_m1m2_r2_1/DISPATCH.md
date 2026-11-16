## Task Assignment: Forensic Audit Remediation Explorer (Milestone M1-M2, Iteration 2)

### Working Directory
`c:\Users\Asif\Downloads\Punjab Air Quality`

### State Folder
`c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\explorer_m1m2_r2_1`

### Authoritative Files to Read
- `c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\ORIGINAL_REQUEST.md`
- `c:\Users\Asif\Downloads\Punjab Air Quality\PROJECT.md`
- `c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\orchestrator_2\GATE_STATUS.md`
- `c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\auditor_m1m2_1\handoff.md` (FULL FORENSIC AUDIT EVIDENCE REPORT)
- `c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\challenger_m1m2_1\handoff.md`
- `c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\challenger_m1m2_2\handoff.md`
- `c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\worker_m1m2_1\handoff.md`

### Mandatory Integrity Requirement
The Forensic Auditor reported INTEGRITY VIOLATION on Iteration 1. Your fix strategy MUST directly and comprehensively address the specific integrity violations identified by the auditor. You MUST NOT recommend strategies that circumvent or evade the audit.

### Audit Evidence to Remediate:
1. **Critical Build Blocker (`npm run build`)**:
   `postcss.config.js` and `tailwind.config.js` remain at root and trigger PostCSS error `Cannot find module 'tailwindcss'`. Furthermore, `src/styles/shadcn.css` contains `@tailwind` directives and `font-family: Inter, ...` override, and is imported in `src/main.tsx`.
   - Formulate exact plan to remove/neutralize `postcss.config.js`, `tailwind.config.js`, remove `shadcn.css` import from `src/main.tsx`, and clean any `@tailwind` / `Inter` overrides so `npm run build` (`tsc && vite build`) succeeds cleanly with 0 errors.
2. **Conflicting Legacy Unit Tests**:
   `tests/unit/test_archival_and_baseline.py:35` and `tests/unit/test_m1_adversarial_challenge.py:40` fail because they assert no `index.html` exists at root. Formulate exact patch to exclude `node_modules`, `.agents`, and allow root `index.html`.
3. **Data Normalizer Defensive Edge Cases**:
   - `normalizeStation`: check `raw.id ?? raw.station_id` so `{ station_id: 172 }` is blacklisted.
   - `aerodromeWindCopy`: validate physical speed bounds ($0 \le ws \le 30$ m/s, $ws \ge 0$).
4. **Clean Dependencies & Icons**:
   - Clean up `ambient.d.ts` evasion typings.

### Objective
Investigate these issues thoroughly across the codebase and write a precise, step-by-step remediation plan in `handoff.md` for the Worker.
Send a message when completed.
