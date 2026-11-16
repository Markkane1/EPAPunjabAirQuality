/**
 * Meteorological Wind Kinematics and QC Validation in TypeScript.
 * Implements polar-to-Cartesian (u, v) and Cartesian-to-polar conversions,
 * anemometer physical boundary validation, and Wazirabad hardware offset blacklisting.
 * Zero external framework dependencies.
 */

// Physical Anemometer Quality Control Limits (TRANSFORMATION_LOGIC_SPEC.md §2.4.0)
export const MIN_WIND_SPEED_MS = 0.0;
export const MAX_WIND_SPEED_MS = 30.0; // 108 km/h upper physical bound for surface stations
export const MIN_WIND_DIR_DEG = 0.0;
export const MAX_WIND_DIR_DEG = 360.0;
export const CALM_WIND_THRESHOLD_MS = 0.5; // Aerodynamic calm cutoff

export const WIND_BLACKLIST_STATIONS = new Set([
  '172',
  'wazirabad',
  'wazirabad aqms',
  'pk_waz_001',
  'wazirabad station',
]);

/**
 * Checks if a station is blacklisted for wind measurements (e.g. Wazirabad).
 */
export function isStationBlacklisted(stationName?: string | number | null): boolean {
  if (stationName == null) return false;
  if (stationName === 172 || stationName === '172') return true;
  const normalized = String(stationName).trim().toLowerCase();
  if (WIND_BLACKLIST_STATIONS.has(normalized)) return true;
  return normalized.includes('wazirabad');
}

/**
 * Validates anemometer measurement against physical bounds and station blacklists.
 * (TRANSFORMATION_LOGIC_SPEC.md §2.4.0).
 */
export function isAnemometerValid(
  speedMs: number | null | undefined,
  dirDeg: number | null | undefined,
  stationName?: string | number | null
): boolean {
  if (speedMs == null || dirDeg == null) return false;
  if (isNaN(speedMs) || isNaN(dirDeg)) return false;
  if (!isFinite(speedMs) || !isFinite(dirDeg)) return false;

  if (speedMs < MIN_WIND_SPEED_MS || speedMs > MAX_WIND_SPEED_MS) return false;
  if (dirDeg < MIN_WIND_DIR_DEG || dirDeg > MAX_WIND_DIR_DEG) return false;

  if (isStationBlacklisted(stationName)) return false;

  return true;
}

/**
 * Determines whether wind speed is classified as aerodynamic calm (<0.5 m/s).
 */
export function isCalmWind(
  speedMs: number | null | undefined,
  calmThreshold: number = CALM_WIND_THRESHOLD_MS
): boolean {
  if (speedMs == null || isNaN(speedMs)) return true;
  return speedMs < calmThreshold;
}

/**
 * Converts polar meteorological wind report (speed, direction FROM) into
 * Cartesian kinematic advection flow vectors (u, v) in m/s (TRANSFORMATION_LOGIC_SPEC.md §2.4.2).
 */
export function polarToCartesianWind(
  speedMs: number | null | undefined,
  dirDeg: number | null | undefined,
  stationName?: string | number | null
): [u: number, v: number] | null {
  if (!isAnemometerValid(speedMs, dirDeg, stationName)) {
    return null;
  }

  const s = speedMs!;
  const d = dirDeg!;

  if (s === 0.0) {
    return [0.0, 0.0];
  }

  const thetaRad = (d * Math.PI) / 180.0;
  let u = -s * Math.sin(thetaRad);
  let v = -s * Math.cos(thetaRad);

  if (Math.abs(u) < 1e-12) u = 0.0;
  if (Math.abs(v) < 1e-12) v = 0.0;

  return [u, v];
}

/**
 * Reconstructs scalar wind speed (m/s) and meteorological direction FROM (deg)
 * from Cartesian flow velocity components (u, v) (TRANSFORMATION_LOGIC_SPEC.md §2.4.2).
 */
export function cartesianToPolarWind(u: number, v: number): [speed: number, direction: number] {
  const speed = Math.sqrt(u * u + v * v);
  if (speed === 0.0) {
    return [0.0, 0.0];
  }

  const direction = ((Math.atan2(-u, -v) * 180.0) / Math.PI + 360.0) % 360.0;
  return [speed, direction];
}

/**
 * Computes azimuth angle the advection vector is blowing TO (degrees clockwise from North).
 */
export function windDirectionToBearing(u: number, v: number): number {
  if (u === 0.0 && v === 0.0) {
    return 0.0;
  }
  return ((Math.atan2(u, v) * 180.0) / Math.PI + 360.0) % 360.0;
}

/**
 * Spatial vector wind field blending (TRANSFORMATION_LOGIC_SPEC.md §2.4.2 windAt).
 */
export function blendWinds(
  targetCoords: [x: number, y: number],
  windSources: Array<{
    coords?: [number, number];
    x?: number;
    y?: number;
    latitude?: number;
    longitude?: number;
    u?: number | null;
    v?: number | null;
    speed?: number | null;
    wind_speed?: number | null;
    direction?: number | null;
    wind_direction?: number | null;
    station_name?: string | null;
    name?: string | null;
  }>,
  softeningSq: number = 400.0
): [u: number, v: number] | null {
  if (!windSources || windSources.length === 0) {
    return null;
  }

  const [tx, ty] = targetCoords;
  let wSum = 0.0;
  let uSum = 0.0;
  let vSum = 0.0;

  for (const src of windSources) {
    let u = src.u;
    let v = src.v;

    if (u == null || v == null) {
      const spd = src.wind_speed ?? src.speed;
      const dr = src.wind_direction ?? src.direction;
      const stName = src.station_name ?? src.name;
      const uv = polarToCartesianWind(spd, dr, stName);
      if (!uv) continue;
      u = uv[0];
      v = uv[1];
    }

    let sx: number | undefined;
    let sy: number | undefined;

    if (src.coords && src.coords.length >= 2) {
      sx = src.coords[0];
      sy = src.coords[1];
    } else {
      sx = src.x ?? src.latitude;
      sy = src.y ?? src.longitude;
    }

    if (sx == null || sy == null || isNaN(sx) || isNaN(sy)) continue;

    const dx = tx - sx;
    const dy = ty - sy;
    const dSq = dx * dx + dy * dy;
    const weight = 1.0 / (dSq + softeningSq);

    wSum += weight;
    uSum += weight * u;
    vSum += weight * v;
  }

  if (wSum <= 0.0) {
    return null;
  }

  return [uSum / wSum, vSum / wSum];
}
