/**
 * Transboundary Atmospheric Cross-Border Inflow and Outflow Index in TypeScript.
 * Implements:
 * 1. T8: 120km border-belt district inflow/outflow evaluation against Indian wind sectors.
 * 2. 39 border normal vector node dot products for animated map chevrons.
 * Zero external framework dependencies.
 */

import { degreesToSector16 } from './geodesy';
import { CALM_WIND_THRESHOLD_MS, cartesianToPolarWind } from './wind';

export const BORDER_CORRIDOR_LIMIT_KM = 120.0; // 120 km border-belt corridor limit
export const BORDER_RESIDENCE_SCALE_KM = 100.0; // e-folding decay scale
export const FLOW_NORMAL_THRESHOLD_MS = 0.25; // Chevron animation threshold (+inflow, -outflow)

export interface BorderDistrictInput {
  district_id?: string;
  name?: string;
  district?: string;
  border_distance_km?: number;
  india_sectors?: number[];
  concentration?: number | null;
  value?: number | null;
  u?: number | null;
  v?: number | null;
  wind_speed?: number | null;
  speed?: number | null;
  wind_direction?: number | null;
  direction?: number | null;
  is_estimated?: boolean;
  est?: boolean;
  [key: string]: any;
}

export interface BorderNormalInput {
  u?: number;
  v?: number;
  nx?: number;
  ny?: number;
  [key: string]: any;
}

export interface TransboundaryIndexResult {
  inflow_total: number;
  outflow_total: number;
  net_flux: number;
  district_values: Record<string, number>;
  normal_fluxes: number[];
}

/**
 * Evaluates hourly transboundary flux value (TBVal_d) for an individual border district
 * (TRANSFORMATION_LOGIC_SPEC.md §2.8.2).
 */
export function calculateDistrictTransboundaryFlux(
  borderDistanceKm: number,
  indiaSectors: number[],
  concentration: number,
  uWind: number,
  vWind: number,
  _isEstimated: boolean = false
): number {
  if (borderDistanceKm > BORDER_CORRIDOR_LIMIT_KM) {
    return 0.0;
  }

  if (concentration <= 0.0 || isNaN(concentration) || !isFinite(concentration)) {
    return 0.0;
  }

  const wSpeed = Math.sqrt(uWind * uWind + vWind * vWind);
  if (wSpeed < CALM_WIND_THRESHOLD_MS) {
    return 0.0; // Calm winds yield zero flux
  }

  const [, dirFrom] = cartesianToPolarWind(uWind, vWind);
  const sectorK = degreesToSector16(dirFrom);

  const decay = Math.exp(-borderDistanceKm / BORDER_RESIDENCE_SCALE_KM);
  const magnitude = concentration * wSpeed * decay;

  // Inflow check (wind blows FROM India into Pakistan)
  if (indiaSectors.includes(sectorK)) {
    return magnitude;
  }

  // Outflow check (wind blows FROM Pakistan into India, 180 deg opposite)
  const outflowSector = (sectorK + 8) % 16;
  if (indiaSectors.includes(outflowSector)) {
    return -magnitude;
  }

  // Neutral or parallel flow along border
  return 0.0;
}

/**
 * Calculates normal velocity projection onto border normal node (TRANSFORMATION_LOGIC_SPEC.md §2.8.2).
 * Phi_j = u_j * nx_j + v_j * ny_j
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
 * Computes aggregated regional transboundary inflow/outflow metrics and border node fluxes
 * (TRANSFORMATION_LOGIC_SPEC.md §2.8).
 */
export function calculateTransboundaryIndex(
  borderDistricts: BorderDistrictInput[],
  borderNormals?: BorderNormalInput[] | null
): TransboundaryIndexResult {
  const districtValues: Record<string, number> = {};
  let inflowTotal = 0.0;
  let outflowTotal = 0.0;

  for (const d of borderDistricts) {
    const dId = String(d.district_id ?? d.name ?? d.district ?? '');
    const distKm = Number(d.border_distance_km ?? 999.0);
    const indiaSec = Array.isArray(d.india_sectors) ? d.india_sectors : [];
    const isEst = Boolean(d.is_estimated ?? d.est ?? false);

    const rawVal = d.concentration ?? d.value ?? 0.0;
    const c = Number(rawVal);

    let u = d.u;
    let v = d.v;

    if (u == null || v == null) {
      const spd = d.wind_speed ?? d.speed ?? 0.0;
      const dr = d.wind_direction ?? d.direction ?? 0.0;
      if (spd != null && dr != null) {
        const rad = (Number(dr) * Math.PI) / 180.0;
        u = -Number(spd) * Math.sin(rad);
        v = -Number(spd) * Math.cos(rad);
      } else {
        u = 0.0;
        v = 0.0;
      }
    }

    const tbVal = calculateDistrictTransboundaryFlux(
      distKm,
      indiaSec,
      c,
      Number(u),
      Number(v),
      isEst
    );

    districtValues[dId] = Number(tbVal.toFixed(4));

    // Only monitored stations contribute to official regional inflow/outflow totals
    if (!isEst) {
      if (tbVal > 0.0) {
        inflowTotal += tbVal;
      } else if (tbVal < 0.0) {
        outflowTotal += Math.abs(tbVal);
      }
    }
  }

  // 39 Border animation nodes normal vector flow
  const normalFluxes: number[] = [];
  if (borderNormals) {
    for (const node of borderNormals) {
      const uN = Number(node.u ?? 0.0);
      const vN = Number(node.v ?? 0.0);
      const nx = Number(node.nx ?? 0.0);
      const ny = Number(node.ny ?? 0.0);
      const phi = calculateBorderNormalFlux(uN, vN, nx, ny);
      normalFluxes.push(Number(phi.toFixed(4)));
    }
  }

  const netFlux = inflowTotal - outflowTotal;

  return {
    inflow_total: Number(inflowTotal.toFixed(4)),
    outflow_total: Number(outflowTotal.toFixed(4)),
    net_flux: Number(netFlux.toFixed(4)),
    district_values: districtValues,
    normal_fluxes: normalFluxes,
  };
}
