# Scope: Milestone 2 — Domain Physics, Normalizer & Schema Trap Engine

## Architecture
- **Layer**: Core Domain Business Logic & Mathematical Transformation Subsystem.
- **Languages**: TypeScript (Strict mode, ESM).
- **Location**: `src/domain/normalizer/` and `src/domain/math/`.
- **Testing**: Vitest / TypeScript unit test suite in `tests/unit/`.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| F01 | T1: Discrete Geodesic IDW | Haversine distance ($R=6371$ km, $p=2$) with singularity clamp $d_0 = 5.0$ km for unmonitored district imputation. | M2 | `TRANSFORMATION_LOGIC_SPEC §2.1` |
| F02 | T2: Anisotropic Continuous IDW | 2D continuous concentration bitmap honoring Plate Carrée aspect ratio ($K_X = \cos 31^\circ$), wind steering ($\epsilon = 4.0$ px, $\cos\alpha$, speed boost), and 45–140 km alpha taper. | M2 | `TRANSFORMATION_LOGIC_SPEC §2.2` |
| F03 | T4: Vector Wind Blending & Cartesian Conversion | Polar to Cartesian wind flow vector conversion ($u = -w_s\sin\theta, v = -w_s\cos\theta$), physical speed clamp $\le 30$ m/s, and Station 172 Wazirabad blacklist. | M2 | `TRANSFORMATION_LOGIC_SPEC §2.4` |
| F04 | T5: Conditional Probability Function (CPF) Wind Rose | 16-sector polar rose, calm exclusion ($<0.50$ m/s), pooled station-hours $P_{75}$ threshold, and small-sample suppression ($N_k < 6$). | M2 | `TRANSFORMATION_LOGIC_SPEC §2.5` |
| F05 | T6: Inter-District Advection Mass Flux | Pairwise flux ($C_a w_a \cos(\Delta\theta) \exp(-d_{ab}/100)$), $d \le 180$ km, cone $\le 35^\circ$, with physical dimension guard locking to PM2.5 when AQI is selected. | M2 | `TRANSFORMATION_LOGIC_SPEC §2.6` |
| F06 | T7: Receptor CPF Pathway Coupling & Transport Balance | Flux weighted by receptor CPF probability $\Omega$ (fallback 0.25), truncated to top 60 links, and net transport balance (export - import). | M2 | `TRANSFORMATION_LOGIC_SPEC §2.7` |
| F07 | T8: Transboundary Border Belt & Normal Chevrons | 120 km border belt index and 39 border normal vector dot products $\Phi_j = \mathbf{w}_j \cdot \mathbf{n}_j$ triggering crimson chevrons when $\Phi_j > +0.25$ m/s, teal when $\Phi_j < -0.25$ m/s. | M2 | `TRANSFORMATION_LOGIC_SPEC §2.8` |
| F08 | T9: PEPC Continuous Half-Open AQI Scale & Colors | Continuous half-open intervals $(BP_{i-1}, BP_i]$, piecewise linear calculation, 500 ceiling clamp when PM2.5 $> 350\ \mu\text{g/m}^3$, particulate-governed composite AQI, 7 statutory hex colors. | M2 | `TRANSFORMATION_LOGIC_SPEC §2.9` |
| F09 | T10: Temporal Aggregation, QC Filters & Lerp | Zero-purge, 7h median spike filter ($v_i > 4M_i \land v_i > 3\text{ref}_p$), 3h logger hold filter with $i \ge 2$ guard and AQI exemption, 75% completeness rule, sub-hourly continuous lerp. | M2 | `TRANSFORMATION_LOGIC_SPEC §2.10` |
| F10 | T11: Geographic Projection & Greedy AABB Labeling | Plate Carrée projection with standard parallel $31^\circ\text{N}$ ($K_X = \cos 31^\circ$), greedy AABB collision search across 12 candidate offsets, and leader lines when offset $> 20$ px. | M2 | `TRANSFORMATION_LOGIC_SPEC §2.11` |
| F11 | Schema Trap 1: Centroid Inversion | Invert district centroid `[lat, lon]` to `[lon, lat]` while preserving `label` and `boundary` coordinates. | M2 | `ORIGINAL_REQUEST §R5`, survey |
| F12 | Schema Trap 2: Aerodrome Null vs Calm | Differentiate airport wind telemetry dropouts (`null`) from aerodynamic calm ($0.0 \le w_s < 0.50$ m/s). | M2 | `ORIGINAL_REQUEST §R5`, survey |
| F13 | Schema Trap 3: Station 172 Wazirabad Blacklist | Hard-block wind vector rendering for Station 172 (Wazirabad) due to $140^\circ$ vane offset and flag as `ANEMOMETER BLACKLISTED (VANE OFFSET)`. | M2 | `ORIGINAL_REQUEST §R5`, survey |
| F14 | Schema Trap 4: Dynamic Station Counts | Dynamically compute fixed (74) vs mobile (5) station counts from active station records. | M2 | `ORIGINAL_REQUEST §R5`, survey |
| F15 | Schema Trap 5: Estimation Flag Unification & Hatching | Unify divergent estimation flags (`est`, `is_monitored`) into `is_estimated: boolean` and trigger diagonal polygon cross-hatching. | M2 | `ORIGINAL_REQUEST §R5`, survey |

## Milestones & Work Items
| # | Work Item | Scope | Dependencies | Status |
|---|-----------|-------|-------------|--------|
| M2.1 | Data Normalizer Engine | `src/domain/normalizer/dataNormalizer.ts` addressing all 5 schema traps. | types (`src/domain/types/index.ts`) | IN_PROGRESS |
| M2.2 | Math Transforms T1–T11 | `src/domain/math/` (`idw.ts`, `wind.ts`, `cpf.ts`, `flux.ts`, `transboundary.ts`, `pepc.ts`, `qc.ts`, `projection.ts`). | types | IN_PROGRESS |
| M2.3 | Unit Test Suite | Comprehensive unit tests in `tests/unit/` covering all transforms, schema traps, boundary conditions, and mathematical exactness. | M2.1, M2.2 | PLANNED |
| M2.4 | Review & Audit Gate | Verification by 2 Reviewers, 2 Challengers, and Forensic Auditor. | M2.1, M2.2, M2.3 | PLANNED |

## Interface Contracts

### Normalizer Interface
- `normalizeDistrict(rawDistrict: RawDistrict): NormalizedDistrict`:
  - Centroid inverted: `centroid: [number, number]` where `[0]` is lon, `[1]` is lat.
  - `label` and `boundary` coordinates remain untouched.
  - `is_estimated: boolean` canonical flag derived from `rawDistrict.est === true || rawDistrict.is_monitored === false`.
- `normalizeWind(rawWind: RawWind, stationId: string): NormalizedWind`:
  - Station 172 (Wazirabad): `anemometerBlacklisted: true`, reason: `'ANEMOMETER BLACKLISTED (VANE OFFSET)'`, vector components suppressed.
  - Null wind dropouts: `status: 'dropout'` (`speed: null, direction: null, u: null, v: null`).
  - Calm wind ($0.0 \le w_s < 0.500$ m/s): `status: 'calm'` (`speed: ws, direction: wd, u: 0, v: 0`).
  - Active wind ($w_s \ge 0.500$ m/s): `status: 'active'`, Cartesian components computed.
- `countStationTypes(stations: Station[]): { fixedCount: number, mobileCount: number, aerodromeCount: number, total: number }`:
  - Dynamic derivation from station records.

### Math Interfaces
- `calculateAQI(concentration: number, pollutant: PollutantKey): AQIResult`:
  - Piecewise linear sub-index on continuous half-open intervals $(BP_{i-1}, BP_i]$.
  - Clamped to 500 ceiling when PM2.5 > 350 $\mu\text{g/m}^3$.
  - Statutory 7 PEPC color codes.
- `calculateAdvectionFlux(params: FluxParams): PathwayLink[]`:
  - Physical dimension guard: if pollutant is AQI, locks to PM2.5.
- `calculateCPF(observations: HourlyObservation[], thresholdP75: number): CPFResult`:
  - 16 sectors ($22.5^\circ$), calm exclusion ($w_s < 0.50$ m/s), small-sample suppression ($N_k < 6 \to \text{null}$).
- `calculateTransboundaryIndex(borderNodes: BorderNode[], windVectors: WindVector[]): TransboundaryResult`:
  - Dot product $\Phi_j = \mathbf{w}_j \cdot \mathbf{n}_j$. Crimson chevron when $\Phi_j > +0.25$ m/s; teal when $\Phi_j < -0.25$ m/s.
