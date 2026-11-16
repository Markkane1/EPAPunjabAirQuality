/**
 * Inverse Distance Weighting (IDW) Geostatistical Interpolation in TypeScript.
 * Implements:
 * 1. T1: Discrete Geodesic District-to-District IDW with Haversine distance and d0=5km clamping.
 * 2. T2: Anisotropic Wind-Steered 2D Continuous Surface IDW with plume dispersion physics.
 * Zero external framework dependencies.
 */

import { haversineDistance } from './geodesy';

export const DEFAULT_IDW_POWER = 2.0;
export const DEFAULT_D0_CLAMP_KM = 5.0;
export const DEFAULT_EPSILON_SQ_PX = 16.0; // 4.0 px softening radius squared
export const DEFAULT_VELOCITY_SATURATION_MS = 1.5;
export const MIN_ANISOTROPIC_MULTIPLIER = 0.30;
export const MAX_ANISOTROPIC_MULTIPLIER = 1.70;

export interface DiscreteIdwNode {
  coords?: [latitude: number, longitude: number];
  lat?: number;
  latitude?: number;
  lon?: number;
  longitude?: number;
  value?: number | null;
  [key: string]: any;
}

export interface VectorIdwNode extends DiscreteIdwNode {
  u?: number | null;
  v?: number | null;
}

export interface AnisotropicStation {
  coords_px?: [x: number, y: number];
  x?: number;
  y?: number;
  value?: number | null;
  u?: number | null;
  v?: number | null;
  [key: string]: any;
}

/**
 * T1: Imputes missing pollutant concentration or scalar reading for a target coordinate
 * using discrete great-circle Haversine inverse distance weighting with singularity clamping
 * (TRANSFORMATION_LOGIC_SPEC.md §2.1).
 */
export function discreteGeodesicIdw(
  target: [latitude: number, longitude: number],
  stations: DiscreteIdwNode[],
  power: number = DEFAULT_IDW_POWER,
  d0: number = DEFAULT_D0_CLAMP_KM
): number | null {
  if (!stations || stations.length === 0) {
    return null;
  }

  const [tLat, tLon] = target;
  let wSum = 0.0;
  let vSum = 0.0;

  for (const st of stations) {
    const val = st.value;
    if (val == null) continue;
    const fVal = Number(val);
    if (isNaN(fVal) || !isFinite(fVal)) continue;

    let sLat: number | undefined;
    let sLon: number | undefined;

    if (st.coords && st.coords.length >= 2) {
      sLat = st.coords[0];
      sLon = st.coords[1];
    } else {
      sLat = st.latitude ?? st.lat;
      sLon = st.longitude ?? st.lon;
    }

    if (sLat == null || sLon == null || isNaN(sLat) || isNaN(sLon)) {
      continue;
    }

    const dist = haversineDistance(tLat, tLon, sLat, sLon);
    const dEff = Math.max(dist, d0);
    const weight = 1.0 / dEff ** power;

    wSum += weight;
    vSum += weight * fVal;
  }

  if (wSum <= 0.0) {
    return null;
  }

  return vSum / wSum;
}

/**
 * Interpolates orthogonal horizontal wind components (u, v) independently
 * using discrete geodesic IDW.
 */
export function discreteGeodesicIdwVector(
  target: [latitude: number, longitude: number],
  stations: VectorIdwNode[],
  power: number = DEFAULT_IDW_POWER,
  d0: number = DEFAULT_D0_CLAMP_KM
): [u: number, v: number] | null {
  if (!stations || stations.length === 0) {
    return null;
  }

  const [tLat, tLon] = target;
  let wSum = 0.0;
  let uSum = 0.0;
  let vSum = 0.0;

  for (const st of stations) {
    const u = st.u;
    const v = st.v;
    if (u == null || v == null) continue;
    const fu = Number(u);
    const fv = Number(v);
    if (isNaN(fu) || isNaN(fv) || !isFinite(fu) || !isFinite(fv)) continue;

    let sLat: number | undefined;
    let sLon: number | undefined;

    if (st.coords && st.coords.length >= 2) {
      sLat = st.coords[0];
      sLon = st.coords[1];
    } else {
      sLat = st.latitude ?? st.lat;
      sLon = st.longitude ?? st.lon;
    }

    if (sLat == null || sLon == null || isNaN(sLat) || isNaN(sLon)) {
      continue;
    }

    const dist = haversineDistance(tLat, tLon, sLat, sLon);
    const dEff = Math.max(dist, d0);
    const weight = 1.0 / dEff ** power;

    wSum += weight;
    uSum += weight * fu;
    vSum += weight * fv;
  }

  if (wSum <= 0.0) {
    return null;
  }

  return [uSum / wSum, vSum / wSum];
}

/**
 * Computes geostatistical confidence opacity taper based on distance to nearest monitor
 * (TRANSFORMATION_LOGIC_SPEC.md §2.2.2).
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
 * T2: Anisotropic Wind-Steered Continuous 2D IDW (TRANSFORMATION_LOGIC_SPEC.md §2.2).
 * Modulates interpolation kernel weights dynamically based on advection direction
 * and velocity saturation.
 */
export function anisotropicIdw(
  targetPx: [x: number, y: number],
  stations: AnisotropicStation[],
  windVector?: [u: number, v: number] | null,
  scale: number = 1.0,
  epsilonSq: number = DEFAULT_EPSILON_SQ_PX
): [interpolatedValue: number, nearestStationKm: number, alphaChannel: number] {
  if (!stations || stations.length === 0) {
    return [0.0, 999.0, 95];
  }

  const [tx, ty] = targetPx;
  let wSum = 0.0;
  let vSum = 0.0;
  let minDPx = Infinity;

  for (const st of stations) {
    const val = st.value;
    if (val == null) continue;
    const fVal = Number(val);
    if (isNaN(fVal) || !isFinite(fVal)) continue;

    let sx: number | undefined;
    let sy: number | undefined;

    if (st.coords_px && st.coords_px.length >= 2) {
      sx = st.coords_px[0];
      sy = st.coords_px[1];
    } else {
      sx = st.x;
      sy = st.y;
    }

    if (sx == null || sy == null || isNaN(sx) || isNaN(sy)) continue;

    const dx = tx - sx;
    const dy = ty - sy;
    const dSq = dx * dx + dy * dy;
    const dPx = Math.sqrt(dSq);

    if (dPx < minDPx) {
      minDPx = dPx;
    }

    // Base isotropic softened weight
    const w0 = 1.0 / (dSq + epsilonSq);

    // Retrieve wind components (u, v)
    let u = st.u;
    let v = st.v;
    if ((u == null || v == null) && windVector != null) {
      u = windVector[0];
      v = windVector[1];
    }

    const fu = u != null ? Number(u) : 0.0;
    const fv = v != null ? Number(v) : 0.0;
    const s = Math.sqrt(fu * fu + fv * fv);

    let weight = w0;
    // Anisotropic kernel modulation
    if (s > 0.5 && dPx > 2.0) {
      // Screen y points southwards; meteorological northward v > 0 travels towards -y
      let cosAlpha = (dx * fu - dy * fv) / (dPx * s);
      cosAlpha = Math.max(-1.0, Math.min(1.0, cosAlpha));
      const sat = Math.min(1.0, s / DEFAULT_VELOCITY_SATURATION_MS);
      const psi = 1.0 + 0.70 * cosAlpha * sat;
      const mult = Math.min(
        MAX_ANISOTROPIC_MULTIPLIER,
        Math.max(MIN_ANISOTROPIC_MULTIPLIER, psi)
      );
      weight = w0 * mult;
    }

    wSum += weight;
    vSum += weight * fVal;
  }

  if (wSum <= 0.0) {
    return [0.0, 999.0, 95];
  }

  const interpVal = vSum / wSum;
  const kmMin = scale > 0 ? minDPx * (111.0 / scale) : minDPx;
  const alpha = calculateDistanceOpacity(kmMin);

  return [interpVal, kmMin, alpha];
}
