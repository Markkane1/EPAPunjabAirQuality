# Task Assignment: Explorer 2 (Math Transforms T1-T11 & Physical Guards)

## Working Directory
c:\Users\Asif\Downloads\Punjab Air Quality

## State Folder
c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\explorer_m2_2

## Objective
Analyze `docs/TRANSFORMATION_LOGIC_SPEC.md`, existing python math implementations in `src/domain/math/`, and types in `src/domain/types/index.ts` to design the full TypeScript implementation blueprint for `src/domain/math/` covering transforms T1-T11:
1. `idw.ts`: T1 Discrete Geodesic IDW (Haversine $R=6371$ km, $p=2$, singularity clamp $d_0 = 5.0$ km). T2 Anisotropic Wind-Steered Continuous IDW (Plate Carrée $K_X = \cos 31^\circ$, $\epsilon = 4.0$ px, $\cos\alpha$ downwind boost up to $+70\%$, floor $0.30$, saturation at $1.5$ m/s, distance alpha taper 45 km to 140 km from 235 to 95).
2. `wind.ts`: T4 Vector Wind Blending & Cartesian Conversion ($u = -w_s\sin\theta, v = -w_s\cos\theta$), physical sanity clamp $0 \le w_s \le 30$ m/s, station 172 blacklist enforcement.
3. `cpf.ts`: T5 16-sector CPF Polar Wind Rose ($22.5^\circ$ bins), calm cutoff $w_s < 0.50$ m/s excluded, pooled station-hour $P_{75}(C)$ evaluation for multi-station districts (Lahore $N \approx 2,700$), small-sample suppression ($N_k < 6 \to \text{null}$ rendering as 10px circular stub).
4. `flux.ts`: T6 Inter-District Advection Mass Flux ($C_a w_a \cos(\Delta\theta)\exp(-d/100)$ with $d \le 180$ km, cone $\le 35^\circ$, $w_a \ge 0.50$ m/s). **Physical Dimension Guard**: strictly disabled for `AQI` (locks to PM2.5). T7 Receptor CPF Pathway Coupling ($\text{Score} = \overline{\text{Flux}} \times \Omega$ with $0.25$ fallback, top 60 links truncation, net transport balance).
5. `transboundary.ts`: T8 Transboundary 120 km border belt index, and 39 border normal vector dot products $\Phi_j = \mathbf{w}_j \cdot \mathbf{n}_j$ triggering crimson chevrons when $\Phi_j > +0.25$ m/s, teal when $\Phi_j < -0.25$ m/s.
6. `pepc.ts`: T9 Continuous half-open piecewise linear AQI scale and 7 statutory hex colors, 500 ceiling clamp when PM2.5 $> 350\ \mu\text{g/m}^3$, composite AQI $= \max(I_{\text{PM2.5}}, I_{\text{PM10}})$.
7. `qc.ts`: T10 Temporal zero/negative purge, 7h rolling median spike filter ($v_i > 4M_i \land v_i > 3\text{ref}_p$), 3h logger hold filter with $i \ge 2$ index guard and AQI exemption, 75% completeness rule, sub-hourly continuous animation lerp.
8. `projection.ts`: T11 Equirectangular Plate Carrée projection with standard parallel $31^\circ\text{N}$ ($K_X = \cos 31^\circ$), greedy AABB collision search across 12 candidate offsets with leader lines when offset $> 20$ px.

## Files to Inspect
- `c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\ORIGINAL_REQUEST.md` (MUST read first)
- `c:\Users\Asif\Downloads\Punjab Air Quality\PROJECT.md`
- `c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\sub_orch_m2\SCOPE.md`
- `c:\Users\Asif\Downloads\Punjab Air Quality\docs\TRANSFORMATION_LOGIC_SPEC.md`
- `c:\Users\Asif\Downloads\Punjab Air Quality\src\domain\math\*.py`
- `c:\Users\Asif\Downloads\Punjab Air Quality\src\domain\types\index.ts`

## Output Requirements
Produce a comprehensive handoff report at `c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\explorer_m2_2\handoff.md` detailing:
- Exact mathematical equations, constants, and edge case guards for each module.
- Comparison with existing Python implementations to ensure 100% parity and bug-free translation.
- Complete TypeScript module signatures, exports, and data structures.
- Safeguards for physical dimension guard (AQI flux lock) and Station 172 suppression.


## 2026-11-11T14:00:08Z
[Message] timestamp=2026-11-11T14:00:08Z sender=67ce931e-e2b3-4aba-ae9e-6d61493eb56a priority=MESSAGE_PRIORITY_HIGH
Task assignment received: Investigate and design the full TypeScript implementation blueprint for `src/domain/math/` covering transforms T1-T11.
