/**
 * Geodesy and Spatial Coordinate Mathematics in TypeScript.
 * Implements great-circle Haversine distance, forward and back bearings,
 * angular divergence, and 16-sector compass rose mapping.
 * Zero external framework dependencies.
 */

export const R_EARTH_KM = 6371.0; // WGS-84 mean volumetric spherical radius in km

export const SECTOR_NAMES_16 = [
  'N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE',
  'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW',
] as const;

export type SectorName16 = (typeof SECTOR_NAMES_16)[number];

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

  const phi1 = (lat1 * Math.PI) / 180.0;
  const lam1 = (lon1 * Math.PI) / 180.0;
  const phi2 = (lat2 * Math.PI) / 180.0;
  const lam2 = (lon2 * Math.PI) / 180.0;

  const dphi = phi2 - phi1;
  const dlam = lam2 - lam1;

  const a =
    Math.sin(dphi / 2.0) ** 2 +
    Math.cos(phi1) * Math.cos(phi2) * Math.sin(dlam / 2.0) ** 2;

  // Clamp argument to asin to [0.0, 1.0] for numerical stability
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

  const phi1 = (lat1 * Math.PI) / 180.0;
  const lam1 = (lon1 * Math.PI) / 180.0;
  const phi2 = (lat2 * Math.PI) / 180.0;
  const lam2 = (lon2 * Math.PI) / 180.0;

  const dlam = lam2 - lam1;
  const y = Math.sin(dlam) * Math.cos(phi2);
  const x =
    Math.cos(phi1) * Math.sin(phi2) -
    Math.sin(phi1) * Math.cos(phi2) * Math.cos(dlam);

  const bearing = ((Math.atan2(y, x) * 180.0) / Math.PI + 360.0) % 360.0;
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
  return Math.abs((((angle1 - angle2 + 180.0) % 360.0) + 360.0) % 360.0 - 180.0);
}

/**
 * Maps continuous azimuth degrees [0, 360) to 16 compass rose sectors (width 22.5 deg).
 * Sector 0 is centered on North (-11.25 deg to +11.25 deg).
 * Range: [0, 15] (TRANSFORMATION_LOGIC_SPEC.md §2.5.2).
 */
export function degreesToSector16(deg: number): number {
  const normDeg = ((deg % 360.0) + 360.0) % 360.0;
  const sector = Math.floor((normDeg + 11.25) / 22.5) % 16;
  return sector;
}

/**
 * Returns center azimuth in degrees for a given 16-sector index.
 */
export function sector16ToDegrees(sector: number): number {
  return ((sector % 16) + 16) % 16 * 22.5;
}
