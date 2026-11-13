# Handoff Report: Domain Physics, Mathematical Transformations (T1–T11) & Physical Guards Blueprint

**Author**: Explorer 2 (Milestone 2: Domain Physics, Normalizer & Schema Trap Engine)  
**Date**: 2026-11-11  
**Target Subsystem**: `src/domain/math/` (`idw.ts`, `wind.ts`, `cpf.ts`, `flux.ts`, `transboundary.ts`, `pepc.ts`, `qc.ts`, `projection.ts`, `geodesy.ts`, `index.ts`)  
**Parent Orchestrator**: `67ce931e-e2b3-4aba-ae9e-6d61493eb56a`

---

## 1. Observation

Direct examination of authoritative specifications, test suites, and prototype source code reveals the exact mathematical, physical, and architectural requirements for the TypeScript domain math engine:

### 1.1 Specification Citations (`docs/TRANSFORMATION_LOGIC_SPEC.md`)
- **T1 Geodesic IDW (§2.1.2)**: Haversine distance with earth radius $R_{\text{Earth}} = 6371.0\text{ km}$, inverse distance power $p = 2.0$, and singularity clamping distance $d_0 = 5.0\text{ km}$:
  $$d_{\text{eff}} = \max(d_i, 5.0), \quad w_i = \frac{1}{d_{\text{eff}}^2}, \quad V = \frac{\sum w_i v_i}{\sum w_i}$$
  Coincident station ($d = 0\text{ km}$) yields finite weight $w = 1 / 25 = 0.04$.
- **T2 Anisotropic Continuous IDW (§2.2.2)**: Softened isotropic kernel $\epsilon^2 = 16.0\text{ px}^2$ ($\epsilon = 4.0\text{ px}$), screen-space coordinate alignment $\cos(\alpha_i) = \frac{\Delta x_i u_i - \Delta y_i v_i}{d_i s_i}$ (where screen $y$ points south while meteorological $v > 0$ carries pollution north toward $-y$), velocity saturation at $1.5\text{ m/s}$, downwind boost up to $+70\%$ ($\psi = 1.0 + 0.70 \cos\alpha \min(1, s/1.5)$), upwind suppression floor of $0.30$, and 45–140 km alpha taper ($235 \to 95$).
- **T4 Wind Kinematics & Bounds (§2.4.0, §2.4.2)**: Speed clamp $0.0 \le w_s \le 30.0\text{ m/s}$, direction clamp $0.0^\circ \le \theta \le 360.0^\circ$, aerodynamic calm threshold $w_s < 0.50\text{ m/s}$, Station 172 (Wazirabad) hardware vane offset ($140^\circ$) blacklist, and polar-to-Cartesian advective flow vectors ($u = -w_s\sin\theta, v = -w_s\cos\theta$).
- **T5 CPF Wind Rose (§2.5.2)**: 16 sectors ($22.5^\circ$ bins, Sector 0 centered on North $[-11.25^\circ, +11.25^\circ)$), calm exclusion ($w_s < 0.50\text{ m/s}$), pooled station-hours $P_{75}(C)$ thresholding, small-sample suppression ($N_k < 6 \to \text{null}$), and rendering contract as a 10px circular stub for suppressed sectors.
- **T6 Inter-District Advection Mass Flux (§2.6.2)**:
  $$\text{Flux}_{a \to b} = C_a \cdot w_a \cdot \cos(\Delta\theta) \cdot \exp(-d_{ab} / 100.0)$$
  Constraints: $d_{ab} \le 180.0\text{ km}$, $\Delta\theta \le 35.0^\circ$, $w_a \ge 0.50\text{ m/s}$.
  **Physical Dimension Guard**: Strictly disabled for dimensionless ordinal `'AQI'` (violates dimensional analysis and mass conservation). When AQI is active in the UI, advection calculations lock to PM2.5 ($\mu\text{g/m}^3$).
- **T7 Receptor Coupling & Net Balance (§2.7.2)**: $\text{Score} = \overline{\text{Flux}}_{a \to b} \times \Omega$ where $\Omega = \text{CPF}_b(k_{\text{rec}})$ or $0.25$ (isotropic fallback when unmonitored or $N_k < 6$), strict truncation to top 60 links sorted descending, and conservative net transport balance $\sum_{\text{export}} - \sum_{\text{import}}$.
- **T8 Transboundary Index (§2.8.2)**: 120 km border corridor limit, sector matching with Indian inflow/outflow sectors, and 39 border normal vector dot products $\Phi_j = \mathbf{w}_j \cdot \mathbf{n}_j$ triggering crimson chevrons when $\Phi_j > +0.25\text{ m/s}$ and teal when $\Phi_j < -0.25\text{ m/s}$.
- **T9 PEPC AQI Scale & Colors (§2.9.2–§2.9.4)**: Continuous half-open intervals $(BP_{i-1}, BP_i]$, piecewise linear calculation, operational ceiling cap at 500 when $\text{PM}_{2.5} > 350.0\ \mu\text{g/m}^3$, composite $\text{AQI} = \max(I_{\text{PM2.5}}, I_{\text{PM10}})$, 7 statutory category hex colors, and continuous 7-stop PEQS RGB gradient ramp.
- **T10 Temporal QC & Lerp (§2.10.1)**: Step 0 non-positive/NaN purge, 7h rolling median spike filter ($v_i > 4.0 M_i \land v_i > 3.0 \text{ref}_p$), 3h logger hold filter with index guard $i \ge 2$ and AQI exemption, 75% completeness rule ($\max(1, \text{round}(0.75 H))$), and sub-hourly continuous animation lerp.
- **T11 Plate Carrée Projection & Greedy Labeling (§2.11.1–§2.11.2)**: Standard parallel $31^\circ\text{N}$, meridional factor $K_X = \cos(31^\circ) \approx 0.8571673007$, and greedy 12-candidate AABB collision search with leader lines when displacement $> 20.0\text{ px}$.

### 1.2 Existing Python Source Code (`src/domain/math/*.py`)
The existing Python modules implement these transforms cleanly and pass 100% of test suites:
- `src/domain/math/geodesy.py`: Haversine distance, forward/back bearing, angular divergence, 16-sector conversion.
- `src/domain/math/idw.py`: `discrete_geodesic_idw`, `discrete_geodesic_idw_vector`, `anisotropic_idw`, `calculate_distance_opacity`.
- `src/domain/math/wind.py`: `polar_to_cartesian_wind`, `cartesian_to_polar_wind`, `is_anemometer_valid`, `is_calm_wind`, `is_station_blacklisted`, `blend_winds`.
- `src/domain/math/cpf.py`: `calculate_cpf_rose`, `calculate_pooled_p75`, `calculate_rose_geometry`.
- `src/domain/math/flux.py`: `calculate_advection_flux`, `calculate_receptor_coupling`, `calculate_net_transport_balance`.
- `src/domain/math/transboundary.py`: `calculate_district_transboundary_flux`, `calculate_border_normal_flux`, `calculate_transboundary_index`.
- `src/domain/math/pepc_aqi.py`: `pepc_calculate_aqi`, `pepc_composite_aqi`, `pepc_get_category`, `pepc_get_color`, `pepc_interpolate_color`.
- `src/domain/math/qc.py`: `temporal_qc_clean`, `check_completeness`, `subhourly_lerp`.
- `src/domain/math/projection.py`: `equirectangular_project`, `equirectangular_unproject`, `check_aabb_collision`, `greedy_label_placement`.

### 1.3 TypeScript Shared Domain Contracts (`src/domain/types/index.ts`)
Types already define canonical interfaces:
- `LngLat` (`[lon, lat]`), `LatLng` (`[lat, lon]`)
- `PollutantKey`, `PhysicalPollutantKey`, `STATUTORY_POLLUTANTS`
- `PEPCGrade`, `PEPCTierIndex`, `AQICalculationResult`
- `WindState`, `WindVector`
- `BorderNode`, `BorderFlowState`, `TransboundaryMassBalance`
- `PathwayLink`, `TransportBalanceSummary`
- `CPFSector`, `CPFRoseData`
- `QCPoint`, `StationQCSeries`

---

## 2. Logic Chain

From the observed specifications, python implementations, and test assertions, we trace the logic chain for the TypeScript translation:

### 2.1 Critical JavaScript/TypeScript Mathematical Traps & Safeguards

1. **The Modulo Operator Trap (`%` vs true mathematical modulo)**:
   - In Python, `(-10) % 360 == 350`.
   - In JavaScript, `(-10) % 360 === -10`. The JavaScript `%` is remainder, NOT modulo.
   - Any angle normalization or sector mapping (e.g. angular divergence `((a1 - a2 + 180) % 360) - 180`, or bearing `(deg + 360) % 360`) will produce **negative azimuths or negative sector indices** in JavaScript if inputs yield negative values.
   - **Resolution**: Every TypeScript math file MUST use a canonical helper:
     ```typescript
     export function mod(n: number, m: number): number {
       return ((n % m) + m) % m;
     }
     ```
2. **Floating-Point Rounding & Boundary Precision**:
   - Boundary tests in `test_tier5_adversarial_hardening_domain.py` assert exact integer AQI and specific float comparisons.
   - Coordinate conversions and distance calculations must clamp intermediate asin/acos arguments to `[-1.0, 1.0]` to prevent `NaN` due to IEEE-754 epsilon overshoot:
     ```typescript
     const c = 2.0 * Math.asin(Math.sqrt(Math.max(0.0, Math.min(1.0, a))));
     ```
3. **Array Snapshot Hold Filter Behavior**:
   - In `qc.py`, lines 97–105:
     ```python
     pre_hold = list(cleaned)
     for i in range(2, n):
         if pre_hold[i] == pre_hold[i-1] == pre_hold[i-2] and pre_hold[i] is not None:
             cleaned[i] = None
     ```
   - Testing confirms that extended holds of 4h, 5h, or 12h must purge **all readings from index 2 onward**.
   - If `cleaned[i-1]` were checked instead of `pre_hold[i-1]`, then after setting `cleaned[2] = null`, index 3 would compare against `null` and falsely survive.
   - The TypeScript implementation must clone the pre-hold state: `const preHold = [...cleaned];`.
4. **Physical Dimension Guard Architecture**:
   - In `flux.ts`, `calculateAdvectionFlux` checks `pollutant.trim().toUpperCase() === 'AQI'`. If true, it returns `null`.
   - In the higher-level pathway generator, if the active UI pollutant is `'AQI'`, the query is automatically redirected to use `PM2.5` mass concentrations, flagging the result with `isPM25Locked: true`.
5. **Station 172 Anemometer Blacklist Architecture**:
   - In `wind.ts`, `isStationBlacklisted(stationIdOrName)` checks for `"172"`, `"pk_waz_001"`, and case-insensitive `"wazirabad"`.
   - When blacklisted: `isAnemometerValid` returns `false`, `polarToCartesianWind` returns `null`, and `normalizeWind` emits `state: 'blacklisted'` with `blacklistReason: 'ANEMOMETER BLACKLISTED (VANE OFFSET)'`.

---

## 3. Caveats

1. **Performance of Anisotropic IDW on CPU vs GPU**:
   - Transform T2 can be evaluated on CPU for pointwise queries (e.g. `fieldAt(x, y)`), but evaluating it over a dense $1200 \times 900$ grid cell-by-cell in pure JS on the main thread would take 200–400ms per frame.
   - The planimetric Deck.gl stack (Milestone 3) uses a custom deck.gl layer or a coarse sub-sampled canvas/WebGL offscreen bitmap for the 60 FPS surface, while invoking `anisotropicIdw` for inspector readouts and verification.
2. **District Centroid vs Station Coordinates in Flux**:
   - Inter-district advection flux operates between district centroids $(\phi_a, \lambda_a) \to (\phi_b, \lambda_b)$ or station coordinates when aggregating district-level winds.
   - Ensure `source_station` accepts either `LngLat` `[lon, lat]` or `LatLng` `[lat, lon]` or object `{ lat, lon }` without ambiguity.
3. **No External Math Libraries**:
   - To comply with project guidelines, all TypeScript modules must use exclusively standard TypeScript / JavaScript `Math` built-ins (zero dependencies on `mathjs`, `simple-statistics`, or external packages).

---

## 4. Conclusion: Complete TypeScript Implementation Blueprint

Below is the complete, production-grade architectural blueprint for all modules under `src/domain/math/`.

### 4.1 Module 1: `src/domain/math/geodesy.ts`
Implements geodetic primitives, Haversine distance, forward/back bearings, angular divergence, and 16-sector compass rose mapping.

```typescript
/**
 * Geodesy and Spatial Coordinate Mathematics.
 * Implements great-circle Haversine distance, forward and back bearings,
 * angular divergence, and 16-sector compass rose mapping.
 * Pure TypeScript with zero external framework dependencies.
 */

export const R_EARTH_KM = 6371.0; // WGS-84 mean volumetric spherical radius in km

export const SECTOR_NAMES_16 = [
  'N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE',
  'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW',
] as const;

export type Sector16Name = typeof SECTOR_NAMES_16[number];

/**
 * True mathematical modulo operation handling negative numbers correctly.
 */
export function mod(n: number, m: number): number {
  return ((n % m) + m) % m;
}

export function toRadians(degrees: number): number {
  return degrees * (Math.PI / 180.0);
}

export function toDegrees(radians: number): number {
  return radians * (180.0 / Math.PI);
}

/**
 * Computes great-circle distance between two geographic coordinates in kilometers
 * using the Haversine formula (TRANSFORMATION_LOGIC_SPEC.md §2.1.2).
 */
export function haversineDistance(
  lat1: number,
  lon1: number,
  lat2: number,
  lon2: number,
  rEarth: number = R_EARTH_KM
): number {
  if (lat1 === lat2 && lon1 === lon2) {
    return 0.0;
  }

  const phi1 = toRadians(lat1);
  const lam1 = toRadians(lon1);
  const phi2 = toRadians(lat2);
  const lam2 = toRadians(lon2);

  const dphi = phi2 - phi1;
  const dlam = lam2 - lam1;

  const sinHalfDphi = Math.sin(dphi / 2.0);
  const sinHalfDlam = Math.sin(dlam / 2.0);

  const a = sinHalfDphi * sinHalfDphi + Math.cos(phi1) * Math.cos(phi2) * sinHalfDlam * sinHalfDlam;
  // Numerical stability clamp to [0.0, 1.0]
  const c = 2.0 * Math.asin(Math.sqrt(Math.max(0.0, Math.min(1.0, a))));
  return rEarth * c;
}

/**
 * Computes initial forward great-circle bearing from point 1 to point 2 in degrees.
 * Azimuth clockwise from North in range [0.0, 360.0) (TRANSFORMATION_LOGIC_SPEC.md §2.6.2).
 */
export function forwardBearing(
  lat1: number,
  lon1: number,
  lat2: number,
  lon2: number
): number {
  if (lat1 === lat2 && lon1 === lon2) {
    return 0.0;
  }

  const phi1 = toRadians(lat1);
  const lam1 = toRadians(lon1);
  const phi2 = toRadians(lat2);
  const lam2 = toRadians(lon2);

  const dlam = lam2 - lam1;
  const y = Math.sin(dlam) * Math.cos(phi2);
  const x = Math.cos(phi1) * Math.sin(phi2) - Math.sin(phi1) * Math.cos(phi2) * Math.cos(dlam);

  const bearing = (toDegrees(Math.atan2(y, x)) + 360.0) % 360.0;
  return bearing;
}

/**
 * Computes back-bearing (arrival angle) from destination point 2 back to point 1.
 */
export function backBearing(
  lat1: number,
  lon1: number,
  lat2: number,
  lon2: number
): number {
  return forwardBearing(lat2, lon2, lat1, lon1);
}

/**
 * Calculates shortest angular difference between two azimuth angles in degrees.
 * Range [0.0, 180.0] (TRANSFORMATION_LOGIC_SPEC.md §2.6.2).
 */
export function angularDivergence(angle1: number, angle2: number): number {
  return Math.abs(mod(angle1 - angle2 + 180.0, 360.0) - 180.0);
}

/**
 * Maps continuous azimuth degrees [0, 360) to 16 compass rose sectors (width 22.5 deg).
 * Sector 0 is centered on North (-11.25 deg to +11.25 deg). Range: [0, 15].
 */
export function degreesToSector16(deg: number): number {
  const normDeg = mod(deg, 360.0);
  return Math.floor((normDeg + 11.25) / 22.5) % 16;
}

/**
 * Returns center azimuth in degrees for a given 16-sector index.
 */
export function sector16ToDegrees(sector: number): number {
  return mod(sector, 16) * 22.5;
}
```

---

### 4.2 Module 2: `src/domain/math/idw.ts`
Implements T1 Discrete Geodesic IDW (Haversine $R=6371$ km, $p=2$, $d_0=5.0$ km) and T2 Anisotropic Wind-Steered Continuous IDW ($\epsilon = 4.0$ px, $\cos\alpha$ downwind boost $+70\%$, floor $0.30$, velocity saturation $1.5$ m/s, distance alpha taper 45–140 km from 235 to 95).

```typescript
/**
 * Inverse Distance Weighting (IDW) Geostatistical Interpolation.
 * Implements:
 * 1. T1: Discrete Geodesic District-to-District IDW with Haversine distance and d0=5km clamping.
 * 2. T2: Anisotropic Wind-Steered 2D Continuous Surface IDW with plume dispersion physics.
 * Pure TypeScript with zero external framework dependencies.
 */

import { haversineDistance } from './geodesy';

export const DEFAULT_IDW_POWER = 2.0;
export const DEFAULT_D0_CLAMP_KM = 5.0;
export const DEFAULT_EPSILON_SQ_PX = 16.0; // 4.0 px softening radius squared
export const DEFAULT_VELOCITY_SATURATION_MS = 1.5;
export const MIN_ANISOTROPIC_MULTIPLIER = 0.30;
export const MAX_ANISOTROPIC_MULTIPLIER = 1.70;

export interface DiscreteIdwNode {
  lat: number;
  lon: number;
  value: number | null;
  u?: number | null;
  v?: number | null;
}

export interface AnisotropicStationNode {
  x: number;
  y: number;
  value: number | null;
  u?: number | null;
  v?: number | null;
}

export interface AnisotropicFieldResult {
  interpolatedValue: number;
  nearestStationKm: number;
  alphaChannel: number; // [95, 235]
}

/**
 * T1: Imputes missing pollutant concentration for target coordinates using discrete
 * great-circle Haversine IDW with singularity clamping d0 = 5.0 km (SPEC §2.1).
 */
export function discreteGeodesicIdw(
  targetLat: number,
  targetLon: number,
  stations: DiscreteIdwNode[],
  power: number = DEFAULT_IDW_POWER,
  d0: number = DEFAULT_D0_CLAMP_KM
): number | null {
  if (!stations || stations.length === 0) {
    return null;
  }

  let wSum = 0.0;
  let vSum = 0.0;

  for (const st of stations) {
    if (st.value === null || st.value === undefined || isNaN(st.value)) {
      continue;
    }

    const dist = haversineDistance(targetLat, targetLon, st.lat, st.lon);
    const dEff = Math.max(dist, d0);
    const weight = 1.0 / Math.pow(dEff, power);

    wSum += weight;
    vSum += weight * st.value;
  }

  if (wSum <= 0.0) {
    return null;
  }

  return vSum / wSum;
}

/**
 * T1 Vector: Interpolates orthogonal horizontal wind components (u, v) independently.
 */
export function discreteGeodesicIdwVector(
  targetLat: number,
  targetLon: number,
  stations: DiscreteIdwNode[],
  power: number = DEFAULT_IDW_POWER,
  d0: number = DEFAULT_D0_CLAMP_KM
): [u: number, v: number] | null {
  if (!stations || stations.length === 0) {
    return null;
  }

  let wSum = 0.0;
  let uSum = 0.0;
  let vSum = 0.0;

  for (const st of stations) {
    if (st.u === null || st.u === undefined || isNaN(st.u) ||
        st.v === null || st.v === undefined || isNaN(st.v)) {
      continue;
    }

    const dist = haversineDistance(targetLat, targetLon, st.lat, st.lon);
    const dEff = Math.max(dist, d0);
    const weight = 1.0 / Math.pow(dEff, power);

    wSum += weight;
    uSum += weight * st.u;
    vSum += weight * st.v;
  }

  if (wSum <= 0.0) {
    return null;
  }

  return [uSum / wSum, vSum / wSum];
}

/**
 * Computes geostatistical confidence opacity taper based on distance to nearest monitor (SPEC §2.2.2).
 */
export function calculateDistanceOpacity(kmMin: number): number {
  if (kmMin < 45.0) {
    return 235;
  }
  if (kmMin > 140.0) {
    return 95;
  }
  const alpha = 235.0 - 140.0 * ((kmMin - 45.0) / (140.0 - 45.0));
  return Math.round(alpha);
}

/**
 * T2: Anisotropic Wind-Steered Continuous 2D IDW (SPEC §2.2).
 * Modulates interpolation kernel weights based on advection direction and velocity saturation.
 */
export function anisotropicIdw(
  targetX: number,
  targetY: number,
  stations: AnisotropicStationNode[],
  fallbackWind: [u: number, v: number] = [0.0, 0.0],
  scale: number = 1.0,
  epsilonSq: number = DEFAULT_EPSILON_SQ_PX
): AnisotropicFieldResult {
  if (!stations || stations.length === 0) {
    return { interpolatedValue: 0.0, nearestStationKm: 999.0, alphaChannel: 95 };
  }

  let wSum = 0.0;
  let vSum = 0.0;
  let minDPx = Infinity;

  for (const st of stations) {
    if (st.value === null || st.value === undefined || isNaN(st.value)) {
      continue;
    }

    const dx = targetX - st.x;
    const dy = targetY - st.y;
    const dSq = dx * dx + dy * dy;
    const dPx = Math.sqrt(dSq);

    if (dPx < minDPx) {
      minDPx = dPx;
    }

    // Base isotropic softened weight
    const w0 = 1.0 / (dSq + epsilonSq);

    // Wind components
    const u = st.u !== null && st.u !== undefined && !isNaN(st.u) ? st.u : fallbackWind[0];
    const v = st.v !== null && st.v !== undefined && !isNaN(st.v) ? st.v : fallbackWind[1];
    const s = Math.sqrt(u * u + v * v);

    let weight = w0;

    // Anisotropic modulation
    if (s > 0.5 && dPx > 2.0) {
      // Screen y points south; northward wind v > 0 travels towards -y
      let cosAlpha = (dx * u - dy * v) / (dPx * s);
      cosAlpha = Math.max(-1.0, Math.min(1.0, cosAlpha));
      const sat = Math.min(1.0, s / DEFAULT_VELOCITY_SATURATION_MS);
      const psi = 1.0 + 0.70 * cosAlpha * sat;
      const mult = Math.min(MAX_ANISOTROPIC_MULTIPLIER, Math.max(MIN_ANISOTROPIC_MULTIPLIER, psi));
      weight = w0 * mult;
    }

    wSum += weight;
    vSum += weight * st.value;
  }

  if (wSum <= 0.0) {
    return { interpolatedValue: 0.0, nearestStationKm: 999.0, alphaChannel: 95 };
  }

  const interpVal = vSum / wSum;
  const kmMin = scale > 0 ? minDPx * (111.0 / scale) : minDPx;
  const alpha = calculateDistanceOpacity(kmMin);

  return {
    interpolatedValue: interpVal,
    nearestStationKm: kmMin,
    alphaChannel: alpha,
  };
}
```

---

### 4.3 Module 3: `src/domain/math/wind.ts`
Implements T4 Vector Wind Blending & Cartesian Conversion, speed clamp $\le 30.0$ m/s, aerodynamic calm cutoff $< 0.50$ m/s, and Station 172 Wazirabad blacklist enforcement.

```typescript
/**
 * Meteorological Wind Kinematics and QC Validation.
 * Implements polar-to-Cartesian (u, v) and Cartesian-to-polar conversions,
 * anemometer physical boundary validation, and Wazirabad hardware offset blacklisting.
 * Pure TypeScript with zero external framework dependencies.
 */

import { toRadians, toDegrees, mod } from './geodesy';

export const MIN_WIND_SPEED_MS = 0.0;
export const MAX_WIND_SPEED_MS = 30.0; // 108 km/h upper physical bound for surface stations
export const MIN_WIND_DIR_DEG = 0.0;
export const MAX_WIND_DIR_DEG = 360.0;
export const CALM_WIND_THRESHOLD_MS = 0.5; // Aerodynamic calm cutoff

export const WIND_BLACKLIST_IDENTIFIERS = new Set<string>([
  '172',
  'wazirabad',
  'wazirabad aqms',
  'pk_waz_001',
  'wazirabad station',
]);

/**
 * Checks if a station is blacklisted for wind measurements (e.g. Station 172 Wazirabad).
 */
export function isStationBlacklisted(stationIdOrName?: string | null): boolean {
  if (!stationIdOrName) {
    return false;
  }
  const normalized = stationIdOrName.trim().toLowerCase();
  if (WIND_BLACKLIST_IDENTIFIERS.has(normalized)) {
    return true;
  }
  return normalized.includes('wazirabad') || normalized === '172';
}

/**
 * Validates anemometer measurement against physical bounds and station blacklist (SPEC §2.4.0).
 */
export function isAnemometerValid(
  speedMs?: number | null,
  dirDeg?: number | null,
  stationIdOrName?: string | null
): boolean {
  if (speedMs === null || speedMs === undefined || isNaN(speedMs) || !isFinite(speedMs)) {
    return false;
  }
  if (dirDeg === null || dirDeg === undefined || isNaN(dirDeg) || !isFinite(dirDeg)) {
    return false;
  }

  if (speedMs < MIN_WIND_SPEED_MS || speedMs > MAX_WIND_SPEED_MS) {
    return false;
  }
  if (dirDeg < MIN_WIND_DIR_DEG || dirDeg > MAX_WIND_DIR_DEG) {
    return false;
  }

  if (isStationBlacklisted(stationIdOrName)) {
    return false;
  }

  return true;
}

/**
 * Determines whether wind speed is classified as aerodynamic calm (<0.50 m/s).
 */
export function isCalmWind(
  speedMs?: number | null,
  calmThreshold: number = CALM_WIND_THRESHOLD_MS
): boolean {
  if (speedMs === null || speedMs === undefined || isNaN(speedMs)) {
    return true;
  }
  return speedMs < calmThreshold;
}

/**
 * Converts polar meteorological wind report (speed, direction FROM) into
 * Cartesian kinematic advection flow vectors (u, v) in m/s (SPEC §2.4.2).
 */
export function polarToCartesianWind(
  speedMs?: number | null,
  dirDeg?: number | null,
  stationIdOrName?: string | null
): [u: number, v: number] | null {
  if (!isAnemometerValid(speedMs, dirDeg, stationIdOrName)) {
    return null;
  }

  if (speedMs === 0.0) {
    return [0.0, 0.0];
  }

  const thetaRad = toRadians(dirDeg!);
  let u = -speedMs! * Math.sin(thetaRad);
  let v = -speedMs! * Math.cos(thetaRad);

  if (Math.abs(u) < 1e-12) u = 0.0;
  if (Math.abs(v) < 1e-12) v = 0.0;

  return [u, v];
}

/**
 * Reconstructs scalar wind speed (m/s) and meteorological direction FROM (deg)
 * from Cartesian flow velocity components (u, v) (SPEC §2.4.2).
 */
export function cartesianToPolarWind(u: number, v: number): [speed: number, directionFrom: number] {
  const speed = Math.sqrt(u * u + v * v);
  if (speed === 0.0) {
    return [0.0, 0.0];
  }
  const directionFrom = mod(toDegrees(Math.atan2(-u, -v)) + 360.0, 360.0);
  return [speed, directionFrom];
}

/**
 * Computes azimuth angle the advection vector is blowing TO (degrees clockwise from North).
 */
export function windDirectionToBearing(u: number, v: number): number {
  if (u === 0.0 && v === 0.0) {
    return 0.0;
  }
  return mod(toDegrees(Math.atan2(u, v)) + 360.0, 360.0);
}

/**
 * Spatial vector wind field blending (SPEC §2.4.2 windAt).
 */
export function blendWinds(
  targetX: number,
  targetY: number,
  sources: Array<{ x: number; y: number; u: number; v: number }>,
  softeningSq: number = 400.0
): [u: number, v: number] | null {
  if (!sources || sources.length === 0) {
    return null;
  }

  let wSum = 0.0;
  let uSum = 0.0;
  let vSum = 0.0;

  for (const src of sources) {
    const dx = targetX - src.x;
    const dy = targetY - src.y;
    const dSq = dx * dx + dy * dy;
    const weight = 1.0 / (dSq + softeningSq);

    wSum += weight;
    uSum += weight * src.u;
    vSum += weight * src.v;
  }

  if (wSum <= 0.0) {
    return null;
  }

  return [uSum / wSum, vSum / wSum];
}
```

---

### 4.4 Module 4: `src/domain/math/cpf.ts`
Implements T5 16-Sector CPF Polar Wind Rose ($22.5^\circ$ bins), calm cutoff $w_s < 0.50$ m/s, pooled station-hours $P_{75}(C)$, small-sample suppression ($N_k < 6 \to \text{null}$), and polygon wedge geometry generation.

```typescript
/**
 * Conditional Probability Function (CPF) Wind Rose Modeling.
 * Performs directional source apportionment across 16 compass sectors (22.5 deg width)
 * with aerodynamic calm wind exclusion (<0.5 m/s) and small-sample suppression (Nk < 6).
 * Pure TypeScript with zero external framework dependencies.
 */

import { degreesToSector16, toRadians } from './geodesy';
import { CALM_WIND_THRESHOLD_MS } from './wind';

export const MIN_SECTOR_SAMPLES = 6;
export const DEFAULT_SECTOR_COUNT = 16;
export const DEFAULT_ISOTROPIC_BASELINE = 0.25;

export interface CPFObservation {
  value?: number | null;
  concentration?: number | null;
  windSpeed?: number | null;
  windDirection?: number | null;
}

export interface CPFRoseResult {
  sectors: Array<number | null>; // Length 16: probability or null if Nk < 6
  calmRatio: number;
  threshold: number; // tau = P75
  sectorCounts: number[]; // Nk
  sectorExceedances: number[]; // mk
}

export interface CPFRoseGeometryItem {
  sector: number;
  aStartRad: number;
  aEndRad: number;
  radiusPx: number;
  cpfValue: number | null;
  isSuppressed: boolean;
}

/**
 * Computes 75th percentile concentration threshold (tau = P75) over pooled
 * individual station-hour observations with C > 0 and wind >= calmThreshold (SPEC §2.5.2).
 */
export function calculatePooledP75(
  observations: CPFObservation[],
  calmThreshold: number = CALM_WIND_THRESHOLD_MS
): number {
  const validC: number[] = [];

  for (const obs of observations) {
    const val = obs.value ?? obs.concentration;
    if (val === null || val === undefined || isNaN(val) || val <= 0.0) {
      continue;
    }

    const ws = obs.windSpeed;
    if (ws !== null && ws !== undefined && !isNaN(ws) && ws < calmThreshold) {
      continue;
    }

    validC.push(val);
  }

  if (validC.length === 0) {
    return 0.0;
  }

  validC.sort((a, b) => a - b);
  // Linear percentile interpolation matching numpy percentile(..., 75)
  const index = 0.75 * (validC.length - 1);
  const lower = Math.floor(index);
  const upper = Math.ceil(index);
  const weight = index - lower;

  if (lower === upper) {
    return validC[lower];
  }
  return validC[lower] * (1.0 - weight) + validC[upper] * weight;
}

/**
 * Calculates 16-sector Conditional Probability Function (CPF) polar rose (SPEC §2.5.2).
 */
export function calculateCpfRose(
  observations: CPFObservation[],
  thresholdP75?: number | null,
  calmThreshold: number = CALM_WIND_THRESHOLD_MS,
  minSamples: number = MIN_SECTOR_SAMPLES
): CPFRoseResult {
  const totalObs = observations.length;
  if (totalObs === 0) {
    return {
      sectors: new Array(DEFAULT_SECTOR_COUNT).fill(null),
      calmRatio: 0.0,
      threshold: thresholdP75 ?? 0.0,
      sectorCounts: new Array(DEFAULT_SECTOR_COUNT).fill(0),
      sectorExceedances: new Array(DEFAULT_SECTOR_COUNT).fill(0),
    };
  }

  const tau = thresholdP75 ?? calculatePooledP75(observations, calmThreshold);

  let calmCount = 0;
  const sectorN = new Array(DEFAULT_SECTOR_COUNT).fill(0);
  const sectorM = new Array(DEFAULT_SECTOR_COUNT).fill(0);

  for (const obs of observations) {
    const val = obs.value ?? obs.concentration;
    if (val === null || val === undefined || isNaN(val) || val <= 0.0) {
      continue;
    }

    const ws = obs.windSpeed;
    const wd = obs.windDirection;

    if (ws === null || ws === undefined || isNaN(ws) || ws < calmThreshold) {
      calmCount++;
      continue;
    }

    if (wd === null || wd === undefined || isNaN(wd)) {
      continue;
    }

    const sectorIdx = degreesToSector16(wd);
    sectorN[sectorIdx]++;
    if (val > tau) {
      sectorM[sectorIdx]++;
    }
  }

  const calmRatio = totalObs > 0 ? calmCount / totalObs : 0.0;
  const sectors: Array<number | null> = [];

  for (let k = 0; k < DEFAULT_SECTOR_COUNT; k++) {
    if (sectorN[k] >= minSamples) {
      sectors.push(Number((sectorM[k] / sectorN[k]).toFixed(4)));
    } else {
      sectors.push(null); // Small-sample suppression
    }
  }

  return {
    sectors,
    calmRatio: Number(calmRatio.toFixed(4)),
    threshold: Number(tau.toFixed(4)),
    sectorCounts: sectorN,
    sectorExceedances: sectorM,
  };
}

/**
 * Generates sector polygon wedge coordinates for rendering polar wind roses on canvas (SPEC §2.5.2).
 */
export function calculateRoseGeometry(
  cpfSectors: Array<number | null>,
  radius: number = 100.0,
  mutedStubPx: number = 10.0
): CPFRoseGeometryItem[] {
  const geometry: CPFRoseGeometryItem[] = [];

  for (let k = 0; k < Math.min(DEFAULT_SECTOR_COUNT, cpfSectors.length); k++) {
    const val = cpfSectors[k];
    const aStart = toRadians(k * 22.5 - 11.25 - 90.0);
    const aEnd = aStart + toRadians(22.5);

    let rK: number;
    let isSuppressed: boolean;

    if (val !== null && val !== undefined) {
      rK = Math.max(2.0, radius * Math.min(1.0, val / 0.80));
      isSuppressed = false;
    } else {
      rK = mutedStubPx;
      isSuppressed = true;
    }

    geometry.push({
      sector: k,
      aStartRad: aStart,
      aEndRad: aEnd,
      radiusPx: Number(rK.toFixed(2)),
      cpfValue: val,
      isSuppressed,
    });
  }

  return geometry;
}
```

---

### 4.5 Module 5: `src/domain/math/flux.ts`
Implements T6 Inter-District Advection Mass Flux with Physical Dimension Guard (locking to PM2.5 for AQI), T7 Receptor CPF Pathway Coupling, Top-60 Truncation, and Net Transport Balance.

```typescript
/**
 * Atmospheric Advection Transport Flux and Source-Receptor Pathway Coupling.
 * Implements:
 * 1. T6: Physical Inter-District Advection Transport Flux (strictly disabled for 'AQI').
 * 2. T7: Receptor CPF Pathway Coupling, Top-60 Truncation, and Net Transport Balance.
 * Pure TypeScript with zero external framework dependencies.
 */

import {
  angularDivergence,
  degreesToSector16,
  forwardBearing,
  haversineDistance,
  mod,
  toRadians,
} from './geodesy';
import { CALM_WIND_THRESHOLD_MS, windDirectionToBearing } from './wind';

export const MAX_TRANSPORT_DISTANCE_KM = 180.0; // Inter-district advective distance limit
export const MAX_TRANSPORT_CONE_DEG = 35.0; // Advection plume divergence angle limit
export const RESIDENCE_SCALE_KM = 100.0; // Atmospheric dispersion e-folding length L_S
export const ISOTROPIC_OMEGA_FALLBACK = 0.25; // Null-hypothesis isotropic receptor feedback
export const MAX_PATHWAY_LINKS = 60; // Bounded top pathway link count

export interface FluxResult {
  flux: number;
  distanceKm: number;
  bearingDeg: number;
  divergenceDeg: number;
}

export interface PathwayCandidate {
  sourceDistrict: string;
  receptorDistrict: string;
  distanceKm: number;
  bearingDeg: number;
  meanFlux: number;
}

export interface RankedPathway {
  sourceDistrict: string;
  receptorDistrict: string;
  distanceKm: number;
  bearingDeg: number;
  flux: number;
  omega: number;
  score: number;
}

/**
 * Estimates hourly physical mass transfer between source and receptor districts (SPEC §2.6).
 *
 * MANDATORY PHYSICAL DIMENSION GUARD:
 * Physical advection transport is strictly disabled for dimensionless ordinal index 'AQI'.
 * Returns null when pollutant.toUpperCase() === 'AQI'.
 */
export function calculateAdvectionFlux(
  sourceLat: number,
  sourceLon: number,
  receptorLat: number,
  receptorLon: number,
  pollutant: string,
  concentration: number | null | undefined,
  uWind: number | null | undefined,
  vWind: number | null | undefined,
  maxDistKm: number = MAX_TRANSPORT_DISTANCE_KM,
  maxConeDeg: number = MAX_TRANSPORT_CONE_DEG,
  residenceKm: number = RESIDENCE_SCALE_KM
): FluxResult | null {
  if (!pollutant || pollutant.trim().toUpperCase() === 'AQI') {
    return null; // Physical Dimension Guard
  }

  const dKm = haversineDistance(sourceLat, sourceLon, receptorLat, receptorLon);
  if (dKm <= 0.0 || dKm > maxDistKm) {
    return null;
  }

  if (concentration === null || concentration === undefined || isNaN(concentration) || concentration <= 0.0) {
    return null;
  }

  if (uWind === null || uWind === undefined || isNaN(uWind) ||
      vWind === null || vWind === undefined || isNaN(vWind)) {
    return null;
  }

  const wSpeed = Math.sqrt(uWind * uWind + vWind * vWind);
  if (wSpeed < CALM_WIND_THRESHOLD_MS) {
    return null; // Calm cutoff
  }

  const thetaBrg = forwardBearing(sourceLat, sourceLon, receptorLat, receptorLon);
  const thetaTo = windDirectionToBearing(uWind, vWind);
  const deltaTheta = angularDivergence(thetaTo, thetaBrg);

  if (deltaTheta > maxConeDeg) {
    return null; // Outside transport cone
  }

  const decay = Math.exp(-dKm / residenceKm);
  const cosProj = Math.cos(toRadians(deltaTheta));
  const fluxVal = concentration * wSpeed * cosProj * decay;

  return {
    flux: Number(fluxVal.toFixed(4)),
    distanceKm: Number(dKm.toFixed(2)),
    bearingDeg: Number(thetaBrg.toFixed(2)),
    divergenceDeg: Number(deltaTheta.toFixed(2)),
  };
}

/**
 * Couples hourly physical advection flux with empirical receptor wind rose feedback
 * coefficient Omega to rank inter-district transport pathways (SPEC §2.7).
 */
export function calculateReceptorCoupling(
  pathways: PathwayCandidate[],
  receptorCpfs: Record<string, Array<number | null>>,
  maxLinks: number = MAX_PATHWAY_LINKS
): RankedPathway[] {
  const rankedLinks: RankedPathway[] = [];

  for (const item of pathways) {
    if (!item.sourceDistrict || !item.receptorDistrict) {
      continue;
    }
    if (item.meanFlux === null || item.meanFlux === undefined || item.meanFlux <= 0.0) {
      continue;
    }

    const thetaBack = mod(item.bearingDeg + 180.0, 360.0);
    const kRec = degreesToSector16(thetaBack);

    let omega = ISOTROPIC_OMEGA_FALLBACK;
    const rcvSectors = receptorCpfs[item.receptorDistrict];
    if (rcvSectors && rcvSectors.length > kRec && rcvSectors[kRec] !== null && rcvSectors[kRec] !== undefined) {
      omega = rcvSectors[kRec]!;
    }

    const score = item.meanFlux * omega;

    rankedLinks.push({
      sourceDistrict: item.sourceDistrict,
      receptorDistrict: item.receptorDistrict,
      distanceKm: Number(item.distanceKm.toFixed(2)),
      bearingDeg: Number(item.bearingDeg.toFixed(2)),
      flux: Number(item.meanFlux.toFixed(4)),
      omega: Number(omega.toFixed(4)),
      score: Number(score.toFixed(4)),
    });
  }

  // Strictly sort descending by score and truncate to top 60 links
  rankedLinks.sort((a, b) => b.score - a.score);
  return rankedLinks.slice(0, maxLinks);
}

/**
 * Computes net district transport balance from active pathway scores (SPEC §2.7.2).
 */
export function calculateNetTransportBalance(
  rankedLinks: Array<{ sourceDistrict: string; receptorDistrict: string; score: number }>
): Record<string, number> {
  const netBalances: Record<string, number> = {};

  for (const link of rankedLinks) {
    const src = link.sourceDistrict;
    const rcv = link.receptorDistrict;
    const score = link.score ?? 0.0;

    if (src) {
      netBalances[src] = (netBalances[src] ?? 0.0) + score;
    }
    if (rcv) {
      netBalances[rcv] = (netBalances[rcv] ?? 0.0) - score;
    }
  }

  const rounded: Record<string, number> = {};
  for (const [k, v] of Object.entries(netBalances)) {
    rounded[k] = Number(v.toFixed(4));
  }
  return rounded;
}
```

---

### 4.6 Module 6: `src/domain/math/transboundary.ts`
Implements T8 120km border belt index & 39 border normal vector dot products with $\pm 0.25$ m/s threshold.

```typescript
/**
 * Transboundary Atmospheric Cross-Border Inflow and Outflow Index.
 * Implements:
 * 1. T8: 120km border-belt district inflow/outflow evaluation against Indian wind sectors.
 * 2. 39 border normal vector node dot products for animated map chevrons.
 * Pure TypeScript with zero external framework dependencies.
 */

import { degreesToSector16 } from './geodesy';
import { CALM_WIND_THRESHOLD_MS, cartesianToPolarWind } from './wind';

export const BORDER_CORRIDOR_LIMIT_KM = 120.0;
export const BORDER_RESIDENCE_SCALE_KM = 100.0;
export const FLOW_NORMAL_THRESHOLD_MS = 0.25;

export interface BorderDistrictInput {
  districtId: string;
  borderDistanceKm: number;
  indiaSectors: number[];
  concentration: number;
  u: number;
  v: number;
  isEstimated?: boolean;
}

export interface BorderNormalInput {
  u: number;
  v: number;
  nx: number;
  ny: number;
}

export interface TransboundaryIndexResult {
  inflowTotal: number;
  outflowTotal: number;
  netFlux: number;
  districtValues: Record<string, number>;
  normalFluxes: number[];
}

/**
 * Evaluates hourly transboundary flux value (TBVal_d) for an individual border district (SPEC §2.8.2).
 */
export function calculateDistrictTransboundaryFlux(
  borderDistanceKm: number,
  indiaSectors: number[],
  concentration: number,
  uWind: number,
  vWind: number,
  isEstimated: boolean = false
): number {
  if (borderDistanceKm > BORDER_CORRIDOR_LIMIT_KM) {
    return 0.0;
  }

  if (concentration <= 0.0 || isNaN(concentration)) {
    return 0.0;
  }

  const wSpeed = Math.sqrt(uWind * uWind + vWind * vWind);
  if (wSpeed < CALM_WIND_THRESHOLD_MS) {
    return 0.0;
  }

  const [, dirFrom] = cartesianToPolarWind(uWind, vWind);
  const sectorK = degreesToSector16(dirFrom);

  const decay = Math.exp(-borderDistanceKm / BORDER_RESIDENCE_SCALE_KM);
  const magnitude = concentration * wSpeed * decay;

  // Inflow check (wind blows FROM India into Pakistan)
  if (indiaSectors.includes(sectorK)) {
    return magnitude;
  }

  // Outflow check (wind blows FROM Pakistan into India)
  const outflowSector = (sectorK + 8) % 16;
  if (indiaSectors.includes(outflowSector)) {
    return -magnitude;
  }

  return 0.0;
}

/**
 * Calculates normal velocity projection onto border normal node: Phi_j = u * nx + v * ny (SPEC §2.8.2).
 */
export function calculateBorderNormalFlux(
  uWind: number,
  vWind: number,
  nx: number,
  ny: number
): number {
  return uWind * nx + vWind * ny;
}

/**
 * Computes aggregated regional transboundary inflow/outflow metrics and border node fluxes (SPEC §2.8).
 */
export function calculateTransboundaryIndex(
  borderDistricts: BorderDistrictInput[],
  borderNormals?: BorderNormalInput[]
): TransboundaryIndexResult {
  const districtValues: Record<string, number> = {};
  let inflowTotal = 0.0;
  let outflowTotal = 0.0;

  for (const d of borderDistricts) {
    const tbVal = calculateDistrictTransboundaryFlux(
      d.borderDistanceKm,
      d.indiaSectors,
      d.concentration,
      d.u,
      d.v,
      d.isEstimated ?? false
    );

    districtValues[d.districtId] = Number(tbVal.toFixed(4));

    if (!d.isEstimated) {
      if (tbVal > 0.0) {
        inflowTotal += tbVal;
      } else if (tbVal < 0.0) {
        outflowTotal += Math.abs(tbVal);
      }
    }
  }

  const normalFluxes: number[] = [];
  if (borderNormals) {
    for (const node of borderNormals) {
      const phi = calculateBorderNormalFlux(node.u, node.v, node.nx, node.ny);
      normalFluxes.push(Number(phi.toFixed(4)));
    }
  }

  return {
    inflowTotal: Number(inflowTotal.toFixed(4)),
    outflowTotal: Number(outflowTotal.toFixed(4)),
    netFlux: Number((inflowTotal - outflowTotal).toFixed(4)),
    districtValues,
    normalFluxes,
  };
}
```

---

### 4.7 Module 7: `src/domain/math/pepc.ts`
Implements T9 Continuous half-open piecewise linear AQI scale, 500 ceiling clamp when PM2.5 > 350 ug/m3, composite AQI = max(PM2.5, PM10), 7 statutory hex colors, and continuous 7-stop PEQS RGB gradient ramp.

```typescript
/**
 * Official Punjab Environmental Protection Council (PEPC) AQI Calculations and Color Scales.
 * Implements:
 * 1. T9: Statutory piecewise linear sub-index interpolation across continuous half-open intervals.
 * 2. 500 operational ceiling cap.
 * 3. Particulate-matter composite AQI: max(I_PM2.5, I_PM10).
 * 4. Official 7-category color palette and continuous 7-stop PEQS RGB gradient ramp.
 * Pure TypeScript with zero external framework dependencies.
 */

export const PEPC_BREAKPOINTS: Record<string, number[]> = {
  PM10: [0.0, 75.0, 150.0, 250.0, 350.0, 450.0, 550.0],
  'PM2.5': [0.0, 15.0, 35.0, 70.0, 140.0, 250.0, 350.0],
  SO2: [0.0, 60.0, 120.0, 220.0, 320.0, 800.0, 1600.0],
  NO2: [0.0, 40.0, 80.0, 130.0, 180.0, 380.0, 580.0],
  O3: [0.0, 65.0, 130.0, 195.0, 260.0, 450.0, 550.0],
  CO: [0.0, 2.5, 5.0, 7.5, 10.0, 25.0, 40.0],
};

export const AQI_TIERS = [0, 50, 100, 150, 200, 300, 400, 500];

export const PEPC_CATEGORIES = [
  { indexMax: 50, name: 'Good', hex: '#00B050' },
  { indexMax: 100, name: 'Satisfactory', hex: '#92D050' },
  { indexMax: 150, name: 'Moderate', hex: '#FFFF00' },
  { indexMax: 200, name: 'Unhealthy (Sensitive)', hex: '#ED7D31' },
  { indexMax: 300, name: 'Unhealthy', hex: '#FF0000' },
  { indexMax: 400, name: 'Very Unhealthy', hex: '#7030A0' },
  { indexMax: 500, name: 'Hazardous', hex: '#C00000' },
] as const;

export const PEQS_MULTIPLIERS = [0.0, 0.5, 1.0, 1.5, 2.5, 4.0, 6.0] as const;
export const PEQS_RGB_STOPS: Array<[number, number, number]> = [
  [58, 165, 93],   // Clean Green
  [156, 204, 58],  // Light Green
  [242, 194, 48],  // Yellow (At Standard)
  [240, 122, 38],  // Orange (1.5x Limit)
  [214, 52, 44],   // Red (2.5x Limit)
  [142, 59, 143],  // Purple (4.0x Limit)
  [90, 21, 48],    // Deep Maroon (6.0x Limit)
];

export function normalizePollutantKey(pollutant: string): string {
  const clean = pollutant.trim().toUpperCase().replace(/[._]/g, '');
  if (clean === 'PM25' || clean === 'PM2') return 'PM2.5';
  if (clean === 'PM10' || clean === 'PM1') return 'PM10';
  return clean;
}

/**
 * Computes statutory Punjab AQI sub-index for a pollutant concentration (SPEC §2.9.2).
 */
export function pepcCalculateAqi(pollutant: string, concentration?: number | null): number | null {
  if (concentration === null || concentration === undefined || isNaN(concentration) || concentration < 0.0) {
    return null;
  }
  if (concentration === 0.0) {
    return 0;
  }

  const key = normalizePollutantKey(pollutant);
  const bps = PEPC_BREAKPOINTS[key];
  if (!bps) {
    return null;
  }

  // Operational Ceiling Cap
  if (concentration > bps[bps.length - 1]) {
    return 500;
  }

  // Continuous half-open intervals: (BP_low, BP_high]
  for (let i = 1; i < bps.length; i++) {
    const bpLow = bps[i - 1];
    const bpHigh = bps[i];
    if (concentration > bpLow && concentration <= bpHigh) {
      const iLow = AQI_TIERS[i - 1];
      const iHigh = AQI_TIERS[i];
      const val = ((iHigh - iLow) / (bpHigh - bpLow)) * (concentration - bpLow) + iLow;
      return Math.round(val);
    }
  }

  return 500;
}

/**
 * Computes Composite Punjab Air Quality Index = max(I_PM2.5, I_PM10) (SPEC §2.9.3).
 */
export function pepcCompositeAqi(
  pm25Aqi?: number | null,
  pm10Aqi?: number | null
): number | null {
  const valid = [pm25Aqi, pm10Aqi].filter((v): v is number => v !== null && v !== undefined && !isNaN(v));
  if (valid.length === 0) {
    return null;
  }
  return Math.max(...valid);
}

/**
 * Returns official PEPC category name descriptor for given AQI value.
 */
export function pepcGetCategory(aqi?: number | null): string {
  if (aqi === null || aqi === undefined || isNaN(aqi)) {
    return 'Unknown';
  }
  for (const cat of PEPC_CATEGORIES) {
    if (aqi <= cat.indexMax) {
      return cat.name;
    }
  }
  return 'Hazardous';
}

/**
 * Returns official PEPC hex color string for given AQI value.
 */
export function pepcGetColor(aqi?: number | null): string {
  if (aqi === null || aqi === undefined || isNaN(aqi)) {
    return '#808080';
  }
  for (const cat of PEPC_CATEGORIES) {
    if (aqi <= cat.indexMax) {
      return cat.hex;
    }
  }
  return '#C00000';
}

/**
 * Computes continuous 7-stop PEQS RGB color vector relative to statutory standard limit (SPEC §2.9.4).
 */
export function pepcInterpolateColor(
  value: number,
  refLimit: number
): [r: number, g: number, b: number] {
  if (refLimit <= 0.0 || value <= 0.0 || isNaN(value)) {
    return PEQS_RGB_STOPS[0];
  }

  const multVal = value / refLimit;
  const numStops = PEQS_MULTIPLIERS.length;

  if (multVal <= PEQS_MULTIPLIERS[0]) {
    return PEQS_RGB_STOPS[0];
  }
  if (multVal >= PEQS_MULTIPLIERS[numStops - 1]) {
    return PEQS_RGB_STOPS[numStops - 1];
  }

  for (let k = 1; k < numStops; k++) {
    const m0 = PEQS_MULTIPLIERS[k - 1];
    const m1 = PEQS_MULTIPLIERS[k];
    if (multVal >= m0 && multVal <= m1) {
      const t = (multVal - m0) / (m1 - m0);
      const c0 = PEQS_RGB_STOPS[k - 1];
      const c1 = PEQS_RGB_STOPS[k];
      const r = Math.round((1.0 - t) * c0[0] + t * c1[0]);
      const g = Math.round((1.0 - t) * c0[1] + t * c1[1]);
      const b = Math.round((1.0 - t) * c0[2] + t * c1[2]);
      return [r, g, b];
    }
  }

  return PEQS_RGB_STOPS[numStops - 1];
}

export function pepcInterpolateColorHex(value: number, refLimit: number): string {
  const [r, g, b] = pepcInterpolateColor(value, refLimit);
  return `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`.toUpperCase();
}
```

---

### 4.8 Module 8: `src/domain/math/qc.ts`
Implements T10 Temporal zero purge, 7h median spike filter, 3h logger hold filter with $i \ge 2$ guard and AQI exemption, 75% completeness rule, sub-hourly continuous lerp.

```typescript
/**
 * Temporal Quality Control (QC), Outlier Scrubbing, Completeness Rules, and Animation Lerp.
 * Implements:
 * 1. T10: Step 0 zero/negative purge.
 * 2. 7-hour rolling median spike filter (>4M and >3ref).
 * 3. 3-hour logger hold (sensor freeze) filter with i >= 2 index guard (AQI exempt).
 * 4. 75% temporal completeness aggregation rule.
 * 5. Continuous sub-hourly linear interpolation (lerp) for 60 FPS animation scrubbing.
 * Pure TypeScript with zero external framework dependencies.
 */

export const DEFAULT_COMPLETENESS_RATIO = 0.75;
export const MEDIAN_WINDOW_HALF_WIDTH = 3; // 7-hour window: [i - 3, i + 3]
export const MIN_MEDIAN_WINDOW_SAMPLES = 3;
export const SPIKE_MEDIAN_MULTIPLIER = 4.0;
export const SPIKE_REF_MULTIPLIER = 3.0;

export interface TemporalQcResult {
  cleaned: Array<number | null>;
  spikeCount: number;
}

/**
 * Sanitizes zero/negatives, cleans 7-hour rolling median spikes, and purges 3-hour logger holds (SPEC §2.10.1).
 */
export function temporalQcClean(
  series: Array<number | null | undefined>,
  refLimit: number,
  pollutant: string
): TemporalQcResult {
  if (!series || series.length === 0) {
    return { cleaned: [], spikeCount: 0 };
  }

  // Step 0: Zero and negative purge
  const cleaned: Array<number | null> = series.map((v) => {
    if (v === null || v === undefined || isNaN(v) || !isFinite(v) || v <= 0.0) {
      return null;
    }
    return v;
  });

  const n = cleaned.length;
  let spikeCount = 0;

  // Step 1: 7-Hour Rolling Window Median Spike Filter
  for (let i = 0; i < n; i++) {
    const curr = cleaned[i];
    if (curr === null) {
      continue;
    }

    const wStart = Math.max(0, i - MEDIAN_WINDOW_HALF_WIDTH);
    const wEnd = Math.min(n, i + MEDIAN_WINDOW_HALF_WIDTH + 1);
    const window: number[] = [];

    for (let j = wStart; j < wEnd; j++) {
      if (cleaned[j] !== null) {
        window.push(cleaned[j]!);
      }
    }

    if (window.length >= MIN_MEDIAN_WINDOW_SAMPLES) {
      window.sort((a, b) => a - b);
      const mid = Math.floor(window.length / 2);
      const medianVal = window.length % 2 !== 0 ? window[mid] : (window[mid - 1] + window[mid]) / 2.0;

      if (curr > SPIKE_MEDIAN_MULTIPLIER * medianVal && curr > SPIKE_REF_MULTIPLIER * refLimit) {
        cleaned[i] = null;
        spikeCount++;
      }
    }
  }

  // Step 2: 3-Hour Logger Hold (Sensor Freeze) Filter with Index Guard (i >= 2)
  // Physical pollutants only; dimensionless integer 'AQI' is exempt
  if (pollutant.trim().toUpperCase() !== 'AQI') {
    const preHold = [...cleaned];
    for (let i = 2; i < n; i++) {
      const v0 = preHold[i];
      const v1 = preHold[i - 1];
      const v2 = preHold[i - 2];
      if (v0 !== null && v1 !== null && v2 !== null) {
        if (v0 === v1 && v1 === v2) {
          cleaned[i] = null;
        }
      }
    }
  }

  return { cleaned, spikeCount };
}

/**
 * Evaluates regulatory 75% temporal completeness rule for time aggregation (SPEC §2.10.1).
 */
export function checkCompleteness(
  series: Array<number | null | undefined>,
  requiredRatio: number = DEFAULT_COMPLETENESS_RATIO
): number | null {
  const totalHours = series.length;
  if (totalHours === 0) {
    return null;
  }

  const validValues = series.filter((v): v is number => v !== null && v !== undefined && !isNaN(v));
  const nValid = validValues.length;

  const minRequired = Math.max(1, Math.round(requiredRatio * totalHours));
  if (nValid < minRequired) {
    return null;
  }

  const sum = validValues.reduce((acc, v) => acc + v, 0);
  return sum / nValid;
}

/**
 * Continuous sub-hourly linear interpolation for smooth 60 FPS animation scrubbing (SPEC §2.10.1).
 */
export function subhourlyLerp(
  series: Array<number | null | undefined>,
  fp: number
): number | null {
  const n = series.length;
  if (n === 0) {
    return null;
  }
  if (n === 1) {
    return series[0] ?? null;
  }

  const clampedFp = Math.max(0.0, Math.min(n - 1.0, fp));
  const i = Math.floor(clampedFp);
  const j = Math.min(n - 1, i + 1);
  const f = clampedFp - i;

  const a = series[i] ?? null;
  const b = series[j] ?? null;

  if (a === null && b === null) {
    return null;
  }
  if (a === null) {
    return b;
  }
  if (b === null) {
    return a;
  }

  return a + (b - a) * f;
}
```

---

### 4.9 Module 9: `src/domain/math/projection.ts`
Implements T11 Equirectangular Plate Carrée projection with standard parallel $31^\circ\text{N}$ ($K_X = \cos 31^\circ$), greedy AABB collision search across 12 candidate offsets with leader lines when offset $> 20$ px.

```typescript
/**
 * Geographic Equirectangular Projection and Collision-Free Greedy Labeling.
 * Implements:
 * 1. T11: Equirectangular Plate Carree projection centered on standard parallel 31 deg N.
 * 2. Forward and inverse coordinate transforms.
 * 3. Greedy 12-offset Axis-Aligned Bounding Box (AABB) collision-free label search with leader line detection.
 * Pure TypeScript with zero external framework dependencies.
 */

import { toRadians } from './geodesy';

export const LON_MIN_DEG = 69.10;
export const LON_MAX_DEG = 75.75;
export const LAT_MIN_DEG = 27.55;
export const LAT_MAX_DEG = 34.30;
export const STANDARD_PARALLEL_DEG = 31.0;

export const KX_MERIDIONAL = Math.cos(toRadians(STANDARD_PARALLEL_DEG)); // ~0.8571673007

export const LABEL_CANDIDATE_OFFSETS: Array<[dx: number, dy: number]> = [
  [0.0, 0.0],
  [0.0, 14.0],
  [0.0, -14.0],
  [16.0, 0.0],
  [-16.0, 0.0],
  [0.0, 26.0],
  [0.0, -26.0],
  [30.0, 8.0],
  [-30.0, 8.0],
  [24.0, -20.0],
  [-24.0, -20.0],
  [0.0, 38.0],
];

export const LEADER_LINE_THRESHOLD_PX = 20.0;

export interface LabelRequest {
  id: string;
  text: string;
  x: number; // Anchor canvas x
  y: number; // Anchor canvas y
  width?: number; // Text width in pixels (default: 48.0)
  height?: number; // Text height in pixels (default: 16.0)
}

export interface PlacedLabel {
  id: string;
  text: string;
  anchorX: number;
  anchorY: number;
  placedX: number;
  placedY: number;
  offsetX: number;
  offsetY: number;
  hasLeaderLine: boolean;
  boundingBox: [x: number, y: number, w: number, h: number];
}

/**
 * Projects geographic WGS-84 coordinates (lat, lon) to 2D canvas pixel coordinates (X, Y) (SPEC §2.11.1).
 */
export function equirectangularProject(
  lat: number,
  lon: number,
  widthPx: number = 1200.0,
  heightPx: number = 900.0
): [x: number, y: number] {
  const scale = widthPx / ((LON_MAX_DEG - LON_MIN_DEG) * KX_MERIDIONAL);
  const x = (lon - LON_MIN_DEG) * KX_MERIDIONAL * scale;
  const y = (LAT_MAX_DEG - lat) * scale;
  return [x, y];
}

/**
 * Inverse projection: maps canvas pixel coordinates (X, Y) back to geographic coordinates (lat, lon).
 */
export function equirectangularUnproject(
  x: number,
  y: number,
  widthPx: number = 1200.0,
  heightPx: number = 900.0
): [lat: number, lon: number] {
  const scale = widthPx / ((LON_MAX_DEG - LON_MIN_DEG) * KX_MERIDIONAL);
  const lon = x / (KX_MERIDIONAL * scale) + LON_MIN_DEG;
  const lat = LAT_MAX_DEG - y / scale;
  return [lat, lon];
}

/**
 * Evaluates whether two Axis-Aligned Bounding Boxes (AABB) overlap (SPEC §2.11.2).
 */
export function checkAabbCollision(
  box1: [x: number, y: number, w: number, h: number],
  box2: [x: number, y: number, w: number, h: number]
): boolean {
  const [x1, y1, w1, h1] = box1;
  const [x2, y2, w2, h2] = box2;

  return (
    x1 < x2 + w2 &&
    x1 + w1 > x2 &&
    y1 < y2 + h2 &&
    y1 + h1 > y2
  );
}

/**
 * Places district text labels on canvas without visual overlap using a greedy 12-offset search (SPEC §2.11.2).
 */
export function greedyLabelPlacement(
  labels: LabelRequest[],
  candidateOffsets: Array<[dx: number, dy: number]> = LABEL_CANDIDATE_OFFSETS,
  leaderLineThresh: number = LEADER_LINE_THRESHOLD_PX
): PlacedLabel[] {
  const placedBoxes: Array<[x: number, y: number, w: number, h: number]> = [];
  const results: PlacedLabel[] = [];

  for (const item of labels) {
    const ax = item.x;
    const ay = item.y;
    const w = item.width ?? 48.0;
    const h = item.height ?? 16.0;

    let chosenOffset = candidateOffsets[candidateOffsets.length - 1];
    let chosenBox: [number, number, number, number] | null = null;

    for (const [dx, dy] of candidateOffsets) {
      const boxX = ax + dx - w / 2.0 - 1.0;
      const boxY = ay + dy - h / 2.0;
      const boxW = w + 2.0;
      const boxH = h;
      const candidateBox: [number, number, number, number] = [boxX, boxY, boxW, boxH];

      let collides = false;
      for (const pBox of placedBoxes) {
        if (checkAabbCollision(candidateBox, pBox)) {
          collides = true;
          break;
        }
      }

      if (!collides) {
        chosenOffset = [dx, dy];
        chosenBox = candidateBox;
        break;
      }
    }

    if (chosenBox === null) {
      const [dx, dy] = chosenOffset;
      chosenBox = [ax + dx - w / 2.0 - 1.0, ay + dy - h / 2.0, w + 2.0, h];
    }

    placedBoxes.push(chosenBox);
    const [dx, dy] = chosenOffset;
    const disp = Math.sqrt(dx * dx + dy * dy);
    const hasLeader = disp > leaderLineThresh;

    results.push({
      id: item.id,
      text: item.text,
      anchorX: Number(ax.toFixed(2)),
      anchorY: Number(ay.toFixed(2)),
      placedX: Number((ax + dx).toFixed(2)),
      placedY: Number((ay + dy).toFixed(2)),
      offsetX: Number(dx.toFixed(2)),
      offsetY: Number(dy.toFixed(2)),
      hasLeaderLine: hasLeader,
      boundingBox: [
        Number(chosenBox[0].toFixed(2)),
        Number(chosenBox[1].toFixed(2)),
        Number(chosenBox[2].toFixed(2)),
        Number(chosenBox[3].toFixed(2)),
      ],
    });
  }

  return results;
}
```

---

### 4.10 Module 10: `src/domain/math/index.ts`
Aggregates and re-exports all math transforms T1–T11.

```typescript
/**
 * EPA Punjab Air Quality Scientific Transformation Subsystem.
 * Exports pure TypeScript implementations of transforms T1-T11.
 */

export * from './geodesy';
export * from './idw';
export * from './wind';
export * from './cpf';
export * from './flux';
export * from './transboundary';
export * from './pepc';
export * from './qc';
export * from './projection';
```

---

## 5. Verification Method

To verify the mathematical accuracy, stability, and parity of these TypeScript modules:

1. **Independent Reference Fixtures**:
   - Geodesy Haversine: Lahore `(31.549, 74.364)` to Sheikhupura `(31.692, 74.198)` must equal $22.3583\text{ km} \pm 0.001$.
   - Geodesy Bearing: Lahore to Sheikhupura must equal $315.3748^\circ \pm 0.01$.
   - Discrete IDW: Target `(31.600, 74.300)` against stations `[(31.549, 74.364, 200.0), (31.692, 74.198, 150.0), (31.436, 73.102, 100.0)]` must yield $186.7488 \pm 0.01$.
   - Singularity clamp: At $d = 0$, $d_{\text{eff}} = 5.0\text{ km}$, $w = 0.04$.
   - Advection Flux: Source `C = 250, w = 4.0 m/s`, distance $50\text{ km}$, divergence $15^\circ$ yields flux $585.864 \pm 0.5$.
   - Physical Dimension Guard: `calculateAdvectionFlux(..., pollutant='AQI')` must return `null`.
   - PEPC PM2.5 Breakpoints: $0 \to 0$, $15.0 \to 50$, $35.0 \to 100$, $70.0 \to 150$, $140.0 \to 200$, $250.0 \to 300$, $350.0 \to 400$, $>350.0 \to 500$ (capped).
   - 3-hour Logger Hold: Uniform sequence $[50, 50, 50, 50, 50]$ purges indices 2, 3, 4 to `null`. For AQI, hold filter is strictly disabled.
   - Plate Carrée Projection: Roundtrip forward and inverse projection error $< 10^{-6}$.
2. **Automated Unit Test Execution**:
   - Once implemented in `src/domain/math/*.ts`, run the Vitest suite:
     ```powershell
     npm run test:unit
     ```
   - Run backend regression suite:
     ```powershell
     python tests/e2e/run_all_tests.py
     ```
     Verifies 50/50 tests pass with zero regressions.
