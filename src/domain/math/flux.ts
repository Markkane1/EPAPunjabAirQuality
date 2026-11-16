/**
 * Atmospheric Advection Transport Flux and Source-Receptor Pathway Coupling in TypeScript.
 * Implements:
 * 1. T6: Physical Inter-District Advection Transport Flux (strictly disabled for 'AQI').
 * 2. T7: Receptor CPF Pathway Coupling, Top-60 Truncation, and Net Transport Balance.
 * Zero external framework dependencies.
 */

import {
  angularDivergence,
  degreesToSector16,
  forwardBearing,
  haversineDistance,
} from './geodesy';
import { CALM_WIND_THRESHOLD_MS, windDirectionToBearing } from './wind';

export const MAX_TRANSPORT_DISTANCE_KM = 180.0; // Maximum inter-district advective distance
export const MAX_TRANSPORT_CONE_DEG = 35.0; // Advection plume divergence angle limit
export const RESIDENCE_SCALE_KM = 100.0; // Atmospheric dispersion e-folding length L_S
export const ISOTROPIC_OMEGA_FALLBACK = 0.25; // Null-hypothesis isotropic receptor feedback
export const MAX_PATHWAY_LINKS = 60; // Bounded top pathway link count

export interface AdvectionFluxResult {
  flux: number;
  distance_km: number;
  bearing_deg: number;
  divergence_deg: number;
}

export interface PathwayLinkItem {
  source_district: string;
  receptor_district: string;
  distance_km: number;
  bearing_deg: number;
  flux: number;
  omega: number;
  score: number;
}

/**
 * Estimates hourly physical mass transfer between source and receptor districts
 * using vector kinematics and exponential dispersion decay (TRANSFORMATION_LOGIC_SPEC.md §2.6).
 *
 * CRITICAL DOMAIN GUARD:
 * Physical advection transport is strictly disabled for the dimensionless ordinal index 'AQI'.
 * Returns null when pollutant == 'AQI'.
 */
export function calculateAdvectionFlux(
  sourceStation:
    | [latitude: number, longitude: number]
    | {
        coords?: [latitude: number, longitude: number];
        latitude?: number;
        lat?: number;
        longitude?: number;
        lon?: number;
        value?: number | null;
        concentration?: number | null;
        u?: number | null;
        v?: number | null;
      },
  receptorCoords: [latitude: number, longitude: number],
  pollutant: string,
  concentration?: number | null,
  uWind?: number | null,
  vWind?: number | null,
  maxDistKm: number = MAX_TRANSPORT_DISTANCE_KM,
  maxConeDeg: number = MAX_TRANSPORT_CONE_DEG,
  residenceKm: number = RESIDENCE_SCALE_KM
): AdvectionFluxResult | null {
  // CRITICAL PHYSICAL DIMENSION GUARD: strictly disabled for AQI
  if (!pollutant || pollutant.trim().toUpperCase() === 'AQI') {
    return null;
  }

  let sLat: number | undefined;
  let sLon: number | undefined;

  if (Array.isArray(sourceStation)) {
    sLat = sourceStation[0];
    sLon = sourceStation[1];
  } else if (sourceStation && typeof sourceStation === 'object') {
    if (sourceStation.coords && sourceStation.coords.length >= 2) {
      sLat = sourceStation.coords[0];
      sLon = sourceStation.coords[1];
    } else {
      sLat = sourceStation.latitude ?? sourceStation.lat;
      sLon = sourceStation.longitude ?? sourceStation.lon;
    }

    if (concentration == null) {
      concentration = sourceStation.value ?? sourceStation.concentration;
    }
    if (uWind == null) {
      uWind = sourceStation.u;
    }
    if (vWind == null) {
      vWind = sourceStation.v;
    }
  }

  if (sLat == null || sLon == null || isNaN(sLat) || isNaN(sLon)) {
    return null;
  }

  const [rLat, rLon] = receptorCoords;
  const dKm = haversineDistance(sLat, sLon, rLat, rLon);
  if (dKm <= 0.0 || dKm > maxDistKm) {
    return null;
  }

  if (concentration == null) {
    return null;
  }
  const cVal = Number(concentration);
  if (isNaN(cVal) || cVal <= 0.0 || !isFinite(cVal)) {
    return null;
  }

  if (uWind == null || vWind == null) {
    return null;
  }
  const uVal = Number(uWind);
  const vVal = Number(vWind);
  if (isNaN(uVal) || isNaN(vVal) || !isFinite(uVal) || !isFinite(vVal)) {
    return null;
  }

  const wSpeed = Math.sqrt(uVal * uVal + vVal * vVal);
  if (wSpeed < CALM_WIND_THRESHOLD_MS) {
    return null; // Aerodynamic calm cutoff
  }

  // Trajectory forward bearing (source -> receptor)
  const thetaBrg = forwardBearing(sLat, sLon, rLat, rLon);

  // Wind advection vector bearing (TO)
  const thetaTo = windDirectionToBearing(uVal, vVal);

  // Angular divergence between trajectory bearing and wind vector
  const deltaTheta = angularDivergence(thetaTo, thetaBrg);
  if (deltaTheta > maxConeDeg) {
    return null; // Outside transport cone
  }

  // Physical flux calculation
  const decay = Math.exp(-dKm / residenceKm);
  const cosProj = Math.cos((deltaTheta * Math.PI) / 180.0);
  const fluxVal = cVal * wSpeed * cosProj * decay;

  return {
    flux: Number(fluxVal.toFixed(4)),
    distance_km: Number(dKm.toFixed(2)),
    bearing_deg: Number(thetaBrg.toFixed(2)),
    divergence_deg: Number(deltaTheta.toFixed(2)),
  };
}

/**
 * Couples hourly physical advection flux with empirical receptor wind rose feedback
 * coefficient Omega to rank inter-district transport pathways (TRANSFORMATION_LOGIC_SPEC.md §2.7).
 */
export function calculateReceptorCoupling(
  fluxSeries: Array<{
    source_district?: string;
    src?: string;
    receptor_district?: string;
    rcv?: string;
    distance_km?: number;
    km?: number;
    bearing_deg?: number;
    bearing?: number;
    mean_flux?: number;
    flux?: number;
    [key: string]: any;
  }>,
  receptorCpfs: Record<string, any>,
  maxLinks: number = MAX_PATHWAY_LINKS
): PathwayLinkItem[] {
  const rankedLinks: PathwayLinkItem[] = [];

  for (const item of fluxSeries) {
    const src = item.source_district ?? item.src;
    const rcv = item.receptor_district ?? item.rcv;
    if (!src || !rcv) continue;

    const rawFlux = item.mean_flux ?? item.flux ?? 0.0;
    const meanFlux = Number(rawFlux);
    if (isNaN(meanFlux) || meanFlux <= 0.0) continue;

    const distKm = Number(item.distance_km ?? item.km ?? 0.0);
    const bearingFwd = item.bearing_deg ?? item.bearing;

    // Calculate arrival back-bearing at receptor: (bearing + 180) mod 360
    const thetaBack =
      bearingFwd != null ? (Number(bearingFwd) + 180.0) % 360.0 : 0.0;
    const kRec = degreesToSector16(thetaBack);

    // Retrieve receptor CPF feedback Omega
    let omega = ISOTROPIC_OMEGA_FALLBACK;
    if (rcv in receptorCpfs) {
      const rcvRose = receptorCpfs[rcv];
      let sectors: Array<number | null> | undefined;

      if (rcvRose && typeof rcvRose === 'object') {
        if ('sectors' in rcvRose && Array.isArray(rcvRose.sectors)) {
          sectors = rcvRose.sectors;
        } else if (Array.isArray(rcvRose)) {
          sectors = rcvRose;
        }
      }

      if (sectors && sectors.length > kRec && sectors[kRec] != null) {
        omega = Number(sectors[kRec]);
      }
    }

    const score = meanFlux * omega;

    rankedLinks.push({
      source_district: src,
      receptor_district: rcv,
      distance_km: Number(distKm.toFixed(2)),
      bearing_deg: Number((bearingFwd != null ? Number(bearingFwd) : 0.0).toFixed(2)),
      flux: Number(meanFlux.toFixed(4)),
      omega: Number(omega.toFixed(4)),
      score: Number(score.toFixed(4)),
    });
  }

  // Sort descending by score and truncate to top 60 links
  rankedLinks.sort((a, b) => b.score - a.score);
  return rankedLinks.slice(0, maxLinks);
}

/**
 * Computes net district transport balance from active pathway scores
 * (TRANSFORMATION_LOGIC_SPEC.md §2.7.2).
 */
export function calculateNetTransportBalance(
  pathwayLinks: Array<{
    source_district?: string;
    receptor_district?: string;
    score?: number;
    [key: string]: any;
  }>
): Record<string, number> {
  const netBalances: Record<string, number> = {};

  for (const link of pathwayLinks) {
    const src = link.source_district;
    const rcv = link.receptor_district;
    const score = Number(link.score ?? 0.0);

    if (src) {
      netBalances[src] = (netBalances[src] ?? 0.0) + score;
    }
    if (rcv) {
      netBalances[rcv] = (netBalances[rcv] ?? 0.0) - score;
    }
  }

  const result: Record<string, number> = {};
  for (const [d, bal] of Object.entries(netBalances)) {
    result[d] = Number(bal.toFixed(4));
  }
  return result;
}
