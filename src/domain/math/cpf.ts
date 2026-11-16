/**
 * Conditional Probability Function (CPF) Wind Rose Modeling in TypeScript.
 * Performs directional source apportionment across 16 compass sectors (22.5 deg width)
 * with aerodynamic calm wind exclusion (<0.5 m/s) and small-sample suppression (Nk < 6).
 * Zero external framework dependencies.
 */

import { degreesToSector16 } from './geodesy';
import { CALM_WIND_THRESHOLD_MS } from './wind';

export const MIN_SECTOR_SAMPLES = 6; // Small-sample suppression threshold
export const DEFAULT_SECTOR_COUNT = 16;
export const DEFAULT_ISOTROPIC_BASELINE = 0.25;

export interface CPFObservation {
  value?: number | null;
  concentration?: number | null;
  wind_speed?: number | null;
  speed?: number | null;
  wind_direction?: number | null;
  direction?: number | null;
  [key: string]: any;
}

export interface CPFRoseResult {
  sectors: Array<number | null>; // Exactly 16 items
  calm_ratio: number;
  threshold: number;
  sector_counts: number[];
  sector_exceedances: number[];
}

export interface CPFSectorGeometry {
  sector: number;
  a_start_rad: number;
  a_end_rad: number;
  radius_px: number;
  cpf_value: number | null;
  is_suppressed: boolean;
}

/**
 * Computes 75th percentile concentration threshold (tau = P75) over pooled
 * individual station-hour observations with C > 0 and wind >= calm_threshold
 * (TRANSFORMATION_LOGIC_SPEC.md §2.5.2).
 */
export function calculatePooledP75(
  observations: CPFObservation[],
  calmThreshold: number = CALM_WIND_THRESHOLD_MS
): number {
  const validC: number[] = [];

  for (const obs of observations) {
    const val = obs.value ?? obs.concentration;
    if (val == null) continue;
    const c = Number(val);
    if (isNaN(c) || c <= 0.0 || !isFinite(c)) continue;

    const ws = obs.wind_speed ?? obs.speed;
    if (ws != null) {
      const fWs = Number(ws);
      if (isNaN(fWs) || fWs < calmThreshold) continue;
    }

    validC.push(c);
  }

  if (validC.length === 0) {
    return 0.0;
  }

  validC.sort((a, b) => a - b);
  const p = 0.75 * (validC.length - 1);
  const base = Math.floor(p);
  const rest = p - base;

  if (base + 1 < validC.length) {
    return validC[base] + rest * (validC[base + 1] - validC[base]);
  }
  return validC[base];
}

/**
 * Calculates 16-sector Conditional Probability Function (CPF) polar rose
 * (TRANSFORMATION_LOGIC_SPEC.md §2.5.2).
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
      calm_ratio: 0.0,
      threshold: thresholdP75 ?? 0.0,
      sector_counts: new Array(DEFAULT_SECTOR_COUNT).fill(0),
      sector_exceedances: new Array(DEFAULT_SECTOR_COUNT).fill(0),
    };
  }

  const tau =
    thresholdP75 != null ? thresholdP75 : calculatePooledP75(observations, calmThreshold);

  let calmCount = 0;
  const sectorN = new Array(DEFAULT_SECTOR_COUNT).fill(0);
  const sectorM = new Array(DEFAULT_SECTOR_COUNT).fill(0);

  for (const obs of observations) {
    const val = obs.value ?? obs.concentration;
    if (val == null) continue;
    const c = Number(val);
    if (isNaN(c) || c <= 0.0 || !isFinite(c)) continue;

    const ws = obs.wind_speed ?? obs.speed;
    const wd = obs.wind_direction ?? obs.direction;

    if (ws == null || isNaN(Number(ws)) || Number(ws) < calmThreshold) {
      calmCount++;
      continue;
    }

    if (wd == null || isNaN(Number(wd))) {
      continue;
    }

    const fWd = Number(wd);
    const sectorIdx = degreesToSector16(fWd);
    sectorN[sectorIdx]++;
    if (c > tau) {
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
    calm_ratio: Number(calmRatio.toFixed(4)),
    threshold: Number(tau.toFixed(4)),
    sector_counts: sectorN,
    sector_exceedances: sectorM,
  };
}

/**
 * Generates sector polygon wedge coordinates for rendering polar wind roses on canvas
 * (TRANSFORMATION_LOGIC_SPEC.md §2.5.2 geometry).
 */
export function calculateRoseGeometry(
  cpfSectors: Array<number | null>,
  radius: number = 100.0,
  mutedStubPx: number = 10.0
): CPFSectorGeometry[] {
  const geometry: CPFSectorGeometry[] = [];
  const limit = Math.min(DEFAULT_SECTOR_COUNT, cpfSectors.length);

  for (let k = 0; k < limit; k++) {
    const val = cpfSectors[k];
    const aStart = ((k * 22.5 - 11.25 - 90.0) * Math.PI) / 180.0;
    const aEnd = aStart + (22.5 * Math.PI) / 180.0;

    let rK: number;
    let isSuppressed: boolean;

    if (val != null) {
      rK = Math.max(2.0, radius * Math.min(1.0, val / 0.80));
      isSuppressed = false;
    } else {
      rK = mutedStubPx;
      isSuppressed = true;
    }

    geometry.push({
      sector: k,
      a_start_rad: aStart,
      a_end_rad: aEnd,
      radius_px: Number(rK.toFixed(2)),
      cpf_value: val,
      is_suppressed: isSuppressed,
    });
  }

  return geometry;
}
