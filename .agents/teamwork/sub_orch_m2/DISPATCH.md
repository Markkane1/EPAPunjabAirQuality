# Dispatch Assignment: Milestone 2 Sub-Orchestrator

## Role: Sub-Orchestrator for Milestone 2 (Domain Physics, Normalizer & Schema Trap Engine)
## Working Directory: c:\Users\Asif\Downloads\Punjab Air Quality
## State Folder: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\sub_orch_m2
## Scope Document: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\sub_orch_m2\SCOPE.md
## Global Project Document: c:\Users\Asif\Downloads\Punjab Air Quality\PROJECT.md
## Original Request Path: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\ORIGINAL_REQUEST.md

## Scope & Objective
Own and complete **Milestone 2: Domain Physics, Normalizer & Schema Trap Engine** for the EPA Punjab Air Quality Institutional Frontend Workstation.

### Specific Deliverables
1. **Data Normalizer (`src/domain/normalizer/dataNormalizer.ts`)**:
   - Resolve all 5 schema traps:
     - Trap 1: Invert district centroid `[lat, lon]` to `[lon, lat]` while keeping `label` and `boundary` `[lon, lat]` unchanged.
     - Trap 2: Differentiate aerodrome wind telemetry dropouts (`null`) from aerodynamic calm ($0.0 \le w_s < 0.500$ m/s).
     - Trap 3: Hard-block wind vector rendering for Station 172 (Wazirabad) due to $140^\circ$ physical vane offset blacklist; set `anemometerBlacklisted: true` and flag as `ANEMOMETER BLACKLISTED (VANE OFFSET)`.
     - Trap 4: Dynamically compute fixed (74) vs mobile (5) station counts from active station records.
     - Trap 5: Unify divergent estimation flags (`est`, `is_monitored`) into canonical `is_estimated: boolean` and trigger diagonal cross-hatching on district polygons.
2. **Mathematical & Atmospheric Physics Transformations (`src/domain/math/`)**:
   - `idw.ts`: T1 Discrete Geodesic IDW (Haversine $R=6371$ km, $p=2$, singularity clamp $d_0 = 5.0$ km). T2 Anisotropic Wind-Steered Continuous IDW (Plate Carrée $K_X = \cos 31^\circ$, $\epsilon = 4.0$ px, $\cos\alpha$ downwind boost up to $+70\%$, floor $0.30$, saturation at $1.5$ m/s, distance alpha taper 45 km to 140 km from 235 to 95).
   - `wind.ts`: T4 Vector Wind Blending & Cartesian Conversion ($u = -w_s\sin\theta, v = -w_s\cos\theta$), physical sanity clamp $0 \le w_s \le 30$ m/s, station 172 blacklist enforcement.
   - `cpf.ts`: T5 16-sector CPF Polar Wind Rose ($22.5^\circ$ bins), calm cutoff $w_s < 0.50$ m/s excluded, pooled station-hour $P_{75}(C)$ evaluation for multi-station districts (Lahore $N \approx 2,700$), small-sample suppression ($N_k < 6 \to \text{null}$ rendering as 10px circular stub).
   - `flux.ts`: T6 Inter-District Advection Mass Flux ($C_a w_a \cos(\Delta\theta)\exp(-d/100)$ with $d \le 180$ km, cone $\le 35^\circ$, $w_a \ge 0.50$ m/s). **Physical Dimension Guard**: strictly disabled for `AQI` (locks to PM2.5). T7 Receptor CPF Pathway Coupling ($\text{Score} = \overline{\text{Flux}} \times \Omega$ with $0.25$ fallback, top 60 links truncation, net transport balance).
   - `transboundary.ts`: T8 Transboundary 120 km border belt index, and 39 border normal vector dot products $\Phi_j = \mathbf{w}_j \cdot \mathbf{n}_j$ triggering crimson chevrons when $\Phi_j > +0.25$ m/s, teal when $\Phi_j < -0.25$ m/s.
   - `pepc.ts`: T9 Continuous half-open piecewise linear AQI scale and 7 statutory hex colors, 500 ceiling clamp when PM2.5 $> 350\ \mu\text{g/m}^3$, composite AQI $= \max(I_{\text{PM2.5}}, I_{\text{PM10}})$.
   - `qc.ts`: T10 Temporal zero/negative purge, 7h rolling median spike filter ($v_i > 4M_i \land v_i > 3\text{ref}_p$), 3h logger hold filter with $i \ge 2$ index guard and AQI exemption, 75% completeness rule, sub-hourly continuous animation lerp.
   - `projection.ts`: T11 Equirectangular Plate Carrée projection with standard parallel $31^\circ\text{N}$ ($K_X = \cos 31^\circ$), greedy AABB collision search across 12 candidate offsets with leader lines when offset $> 20$ px.
3. **Comprehensive Unit Test Suite**:
   - Add automated TypeScript unit tests verifying all 11 transformations and 5 schema traps against mathematical tolerances ($\epsilon = 10^{-5}$) and edge cases.
4. **Verification**:
   - `npm run typecheck` and `npm run build` pass with zero errors.
   - All unit tests pass.
   - `python tests/e2e/run_all_tests.py` passes 50/50 tests (100%).

### Workflow
As Sub-Orchestrator, follow the Project Pattern iteration loop:
1. Initialize `SCOPE.md`, `BRIEFING.md`, and `progress.md`.
2. Spawn 3 Explorers in parallel to design the implementation and file layout.
3. Spawn a Worker to implement all deliverables and run build/test commands.
4. Spawn 2 Reviewers independently to verify mathematical exactness and schema trap handling.
5. Spawn 2 Challengers to empirically verify edge cases and boundary conditions.
6. Spawn a Forensic Auditor (`teamwork_auditor`) to ensure authentic physics logic with zero hardcoded shortcuts.
7. Record gate verdicts in `GATE_STATUS.md`. Pass only if all checks pass and audit is clean.
8. Deliver handoff to parent (`854942e9-be47-4067-87d5-db3fbea7749d`).
