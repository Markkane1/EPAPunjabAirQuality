## 2026-11-11T13:33:49Z
You are the Worker implementing Milestone 1: Foundation, Tooling & Design Tokens for the EPA Punjab Air Quality Institutional Frontend Workstation.
Working directory: c:\Users\Asif\Downloads\Punjab Air Quality
State folder: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\worker_m1

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

MANDATORY READING:
- c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\ORIGINAL_REQUEST.md
- c:\Users\Asif\Downloads\Punjab Air Quality\PROJECT.md
- c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\sub_orch_m1\SCOPE.md
- c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\sub_orch_m1\SYNTHESIS.md
- Explorer reports:
  - c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\explorer_m1_1\handoff.md (Tooling & dependencies)
  - c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\explorer_m1_2\handoff.md (WCAG AAA tokens & typography)
  - c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\explorer_m1_3\handoff.md (Layout shell & domain types)

FILE WRITE OWNERSHIP:
You own exclusively:
- `package.json`
- `tsconfig.json`
- `vite.config.ts`
- `index.html`
- `src/types/deckgl.d.ts`
- `src/styles/tokens.css`
- `src/styles/typography.css`
- `src/styles/grid.module.css`
- `src/App.tsx`
- `src/main.tsx`
- `src/domain/types/index.ts`
CAVEAT: Do NOT delete or modify `src/frontend/static/` (it is mounted by FastAPI for legacy compatibility).

TASKS:
1. Implement `package.json`, `tsconfig.json`, `vite.config.ts`, and `src/types/deckgl.d.ts` following Explorer 1's exact specifications.
   - Strictly ensure no banned packages (tailwindcss, lucide-react, heroicons, feather-icons).
2. Implement `src/styles/tokens.css` and `src/styles/typography.css` following Explorer 2's exact specifications.
   - All text/surface pairs must have WCAG 2.1 AAA luminance contrast >= 7.0:1.
   - Fix `--ink-secondary` (dark & light), `--ink-tertiary` (dark & light), and light mode `--accent`.
   - Statutory PEPC colors, 1px solid hairlines, 0px border-radius, zero drop-shadows, zero blur.
   - Exclusively IBM Plex typography with `font-variant-numeric: tabular-nums` and zero emojis.
3. Implement `index.html`, `src/styles/grid.module.css`, `src/App.tsx`, and `src/main.tsx` following Explorer 3's exact specifications.
   - Rigid 100vw x 100vh CSS Grid with 5 named zones (`command-bar`, `spatial-dock`, `map-canvas`, `receptor-inspector`, `temporal-scrubber`).
   - Semantic landmarks and ARIA live regions.
4. Implement `src/domain/types/index.ts` declaring canonical domain models:
   - Station, District (with inverted centroid [lon, lat] and is_estimated), Observation, WindVector (4 states), BorderNode (39 normal vectors), Airshed, PEPCGrade, PollutantKey, LayerId.
5. Verification Commands:
   - Run `npm install`
   - Run `npm run typecheck` (`tsc --noEmit`) -> must exit code 0
   - Run `npm run build` (`tsc && vite build`) -> must exit code 0, generate `dist/`
   - Run `python tests/e2e/run_all_tests.py` -> must pass 50/50 (100%)
6. Write a comprehensive handoff report documenting all implemented files, verification commands, and outputs to:
   c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\worker_m1\handoff.md
7. Notify the orchestrator with send_message when complete.
