## Task Assignment: Milestone M1-M2 (Foundation Fix & Domain Physics / Normalizer Engine)

### Working Directory
`c:\Users\Asif\Downloads\Punjab Air Quality`

### State Folder
`c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\worker_m1m2_1`

### Authoritative Files to Read
- `c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\ORIGINAL_REQUEST.md`
- `c:\Users\Asif\Downloads\Punjab Air Quality\PROJECT.md`
- `c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\orchestrator_2\SCOPE.md`
- `c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\spec_miner_r1_2\handoff.md`
- `c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\explorer_r1_1\handoff.md`
- `docs/TRANSFORMATION_LOGIC_SPEC.md`
- `src/domain/types/index.ts`
- `src/domain/math/` (reference Python implementations of T1-T11)

### Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

### Concrete Tasks & Deliverables
1. **Purge Banned Dependencies from `package.json`**:
   Remove `tailwindcss`, `lucide-react`, `tailwind-merge`, `tailwindcss-animate`, `@radix-ui/*`, `autoprefixer`, `postcss`. Ensure `package.json` contains only authorized dependencies (React 18, Deck.gl v8, MapLibre GL v3, Vite, TypeScript, etc.).
2. **Create Root `index.html`**:
   Place `index.html` at repository root. Enforce exclusive IBM Plex typography (IBM Plex Sans, IBM Plex Sans Condensed, IBM Plex Mono) loaded via clean fonts, mounting `<div id="root"></div>`, referencing `<script type="module" src="/src/main.tsx"></script>`. Absolutely zero emojis anywhere in title, meta, or markup.
3. **Fix Test Flaw in `tests/unit/test_m1_adversarial.py`**:
   Update `test_no_legacy_remnants_in_root_or_subdirs` to exclude `node_modules`, `.agents`, and `.git`, and allow the legitimate Vite root `index.html`.
4. **Implement `src/domain/normalizer/dataNormalizer.ts`**:
   Implement full TypeScript normalizer covering all 5 schema traps:
   - Trap 1: Invert district centroid `[lat, lon]` to `[lon, lat]` while preserving `label` and `boundary` coordinates.
   - Trap 2: Differentiate aerodrome wind `null` (`state: 'dropout'`) from aerodynamic calm `0.0 <= ws < 0.50` m/s (`state: 'calm'`) and active vectors (`state: 'active'`).
   - Trap 3: Hard-block wind vector rendering for Station 172 (Wazirabad) due to 140° vane offset blacklist (`blacklisted: true, state: 'blacklisted', blacklistReason: 'ANEMOMETER BLACKLISTED (VANE OFFSET)'`).
   - Trap 4: Dynamically compute fixed (74) vs mobile (5) station counts.
   - Trap 5: Unify estimation flags (`est`, `is_monitored`) into `is_estimated: boolean` and provide diagonal cross-hatching flags.
5. **Implement Client Math Transformations in TypeScript (`src/domain/math/`)**:
   Implement:
   - `idw.ts`: Discrete geodesic IDW (T1) with Haversine ($R=6371$ km) and singularity clamp $d_0 = 5.0$ km; 2D anisotropic continuous IDW (T2) with wind steering ($\epsilon = 4.0$ px) and alpha taper 45-140 km.
   - `wind.ts`: Polar to Cartesian ($u = -w_s\sin\theta, v = -w_s\cos\theta$), speed clamp $\le 30$ m/s, Wazirabad blacklist.
   - `cpf.ts`: 16-sector polar wind rose, calm exclusion ($<0.50$ m/s), pooled station $P_{75}$ threshold, small-sample suppression ($N_k < 6$).
   - `flux.ts`: Advection flux ($C_a w_a \cos(\Delta\theta) \exp(-d_{ab}/100)$), $d \le 180$ km, cone $\le 35^\circ$, physical dimension guard locking to PM2.5 when AQI is selected, top 60 links ranking, net district balance.
   - `transboundary.ts`: 39 border normal vector dot products $\Phi_j = \mathbf{w}_j \cdot \mathbf{n}_j$ triggering crimson chevrons when $\Phi_j > +0.25$ m/s.
   - `pepc_aqi.ts`: Continuous half-open piecewise linear calculation, 500 ceiling clamp when PM2.5 $> 350\ \mu\text{g/m}^3$, composite AQI governed by particulates, 7 statutory hex colors.
   - `qc.ts`: Zero-purge, 7h median spike filter ($v_i > 4M_i \land v_i > 3\text{ref}_p$), 3h logger hold filter with $i \ge 2$ guard and AQI exemption, 75% completeness rule, sub-hourly continuous lerp.
   - `projection.ts`: Plate Carrée equirectangular projection with standard parallel $31^\circ\text{N}$ ($K_X = \cos 31^\circ$), greedy AABB collision search across 12 candidate offsets, leader lines when offset $> 20$ px.
6. **Verification Requirements**:
   Run and document:
   - `npm run typecheck`
   - `python tests/challenge_contrast.py`
   - `python -m pytest tests/unit/test_m1_adversarial.py`
   - `python tests/e2e/run_all_tests.py`
   Write full report and verification commands/results to `handoff.md` in your state folder.


## 2026-11-14T07:58:41Z
[Message] timestamp=2026-11-14T07:58:41Z sender=b1071a7a-0888-4f29-96a9-461c600209df priority=MESSAGE_PRIORITY_HIGH content=You are worker_m1m2_1.
Working directory: c:\Users\Asif\Downloads\Punjab Air Quality
State folder: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\worker_m1m2_1
Read DISPATCH.md in your state folder.
MANDATORY: Read ORIGINAL_REQUEST.md at c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\ORIGINAL_REQUEST.md before starting work.


## 2026-11-14T08:28:43Z
[User Message] content=pause


## 2026-11-14T08:40:52Z
[Message] sender=b1071a7a-0888-4f29-96a9-461c600209df priority=MESSAGE_PRIORITY_HIGH content=**Context**: Milestone M1-M2 Execution Resume
**Content**: The user has commanded to resume execution. Please resume immediately from your checkpoint:
- Task 2: Create root `index.html` loading exclusively IBM Plex fonts (Sans, Sans Condensed, Mono), strict zero emoji rule, mounting `<div id="root"></div>`, referencing `<script type="module" src="/src/main.tsx"></script>`.
- Task 3: Fix `tests/unit/test_m1_adversarial.py` remnants check to exclude `node_modules` and `.agents` and permit the Vite root `index.html`.
- Task 4: Implement `src/domain/normalizer/dataNormalizer.ts` addressing all 5 schema traps:
  1. Centroid inversion: `[lat, lon]` -> `[lon, lat]`.
  2. Aerodrome wind `null` (`state: 'dropout'`) vs calm `0.0 <= ws < 0.50` m/s (`state: 'calm'`) vs active.
  3. Station 172 Wazirabad blacklist (`blacklisted: true`, reason: `ANEMOMETER BLACKLISTED (VANE OFFSET)`).
  4. Dynamic station counts (74 fixed, 5 mobile).
  5. Unified estimation flag (`is_estimated: boolean`) and diagonal cross-hatching.
- Task 5: Implement client math engine in TypeScript (`src/domain/math/`): IDW (T1/T2), Wind (T4), CPF (T5), Flux (T6 with PM2.5 lock for AQI), Transboundary 39 border normals (T8), PEPC AQI with 500 ceiling clamp (T9), Temporal QC with 7h spike and 3h hold index guard and AQI exemption (T10), Projection & Greedy AABB (T11).
- Task 6: Run verification suite:
  - `npm run typecheck`
  - `python tests/challenge_contrast.py`
  - `python -m pytest tests/unit/test_m1_adversarial.py`
  - `python tests/e2e/run_all_tests.py`
**Action**: Execute tasks, document verification in `handoff.md`, and report completion.
