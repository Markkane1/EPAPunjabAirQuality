/**
 * EPA Punjab Air Quality Monitoring, Processing, and Visualization System
 * Canonical Domain Normalizer Engine addressing all 5 Schema Traps:
 *
 * 1. Centroid Inversion: Inverts [latitude, longitude] to [longitude, latitude] for map engines
 *    while preserving already-projected label coordinates and GeoJSON boundary rings.
 * 2. Aerodrome Wind Discrimination: Differentiates null telemetry dropout from calm (0.0 <= ws < 0.50 m/s)
 *    and active advection vectors.
 * 3. Station 172 Blacklist: Hard-blocks wind rendering for Wazirabad (140 deg vane offset).
 * 4. Dynamic Network Station Counts: Evaluates fixed (74) vs mobile (5) station inventory.
 * 5. Unified Estimation Flag: Standardizes est / is_monitored into is_estimated and flags diagonal cross-hatching.
 */

import type {
  AirportStation,
  LatLng,
  LngLat,
  NormalizedDistrict,
  NormalizedStation,
  RawDistrict,
  RawStation,
  StationNetworkType,
  WindVector,
} from '../types';

/**
 * Known identifiers for Station 172 (Wazirabad AQMS) with persistent 140 degree hardware vane offset.
 */
export const WAZIRABAD_BLACKLIST_IDS = new Set([
  '172',
  172,
  'wazirabad',
  'wazirabad aqms',
  'pk_waz_001',
  'wazirabad station',
]);

/**
 * Checks if a station is blacklisted for wind measurements (Schema Trap 3).
 */
export function isStationBlacklisted(stationIdOrName?: string | number | null): boolean {
  if (stationIdOrName == null) return false;
  if (stationIdOrName === 172 || stationIdOrName === '172') return true;
  const normalized = String(stationIdOrName).trim().toLowerCase();
  if (WAZIRABAD_BLACKLIST_IDS.has(normalized)) return true;
  return normalized.includes('wazirabad');
}

/**
 * Returns warning banner text if station anemometer is blacklisted.
 */
export function blacklistBannerText(
  station: { id?: string | number; name?: string } | null | undefined
): string | null {
  if (!station) return null;
  if (isStationBlacklisted(station.id) || isStationBlacklisted(station.name)) {
    return 'ANEMOMETER BLACKLISTED (VANE OFFSET)';
  }
  return null;
}

/**
 * Trap 1: Inverts raw district centroid [latitude, longitude] to canonical [longitude, latitude].
 * Notice: Input is [lat, lon], output is GeoJSON / deck.gl order [lon, lat].
 */
export function normalizeCentroid(centroid: LatLng | [number, number]): LngLat {
  if (!centroid || centroid.length < 2) {
    return [0, 0];
  }
  const first = Number(centroid[0]);
  const second = Number(centroid[1]);
  if (isNaN(first) || isNaN(second)) {
    return [0, 0];
  }
  // Idempotent coordinate check: In South Asia (lat ~27-35, lon ~68-76),
  // if first <= 45 and second > 45, input is [lat, lon] -> invert to [lon, lat].
  if (Math.abs(first) <= 45 && Math.abs(second) > 45) {
    return [second, first];
  }
  // If first > 45 and second <= 45, input is already [lon, lat] -> return as is.
  return [first, second];
}

/**
 * Alias for normalizeCentroid.
 */
export function centroidLngLat(centroid: LatLng | [number, number]): LngLat {
  return normalizeCentroid(centroid);
}

/**
 * Trap 2 & Trap 3: Canonical wind vector normalizer.
 * - Null / NaN / Inf / out-of-range (> 30 m/s) -> 'dropout'
 * - Station 172 (Wazirabad) -> 'blacklisted'
 * - 0.0 <= speed < 0.50 m/s -> 'calm'
 * - speed >= 0.50 m/s -> 'active'
 */
export function normalizeWind(
  speed: number | null | undefined,
  direction: number | null | undefined,
  stationIdOrName?: string | number | null
): WindVector {
  // Check Trap 3: Station 172 Wazirabad Blacklist
  if (isStationBlacklisted(stationIdOrName)) {
    return {
      state: 'blacklisted',
      speed: null,
      direction: null,
      u: null,
      v: null,
      blacklisted: true,
      blacklistReason: 'ANEMOMETER BLACKLISTED (VANE OFFSET)',
    };
  }

  // Check Trap 2: Telemetry Dropout (null, undefined, NaN, or non-physical speed)
  if (
    speed == null ||
    direction == null ||
    isNaN(speed) ||
    isNaN(direction) ||
    !isFinite(speed) ||
    !isFinite(direction) ||
    speed < 0 ||
    speed > 30.0 ||
    direction < 0 ||
    direction > 360.0
  ) {
    return {
      state: 'dropout',
      speed: null,
      direction: null,
      u: null,
      v: null,
      blacklisted: false,
    };
  }

  // Check Trap 2: Aerodynamic Calm (< 0.50 m/s)
  if (speed < 0.50) {
    return {
      state: 'calm',
      speed: Number(speed.toFixed(2)),
      direction: Number(direction.toFixed(1)),
      u: 0.0,
      v: 0.0,
      blacklisted: false,
    };
  }

  // Active Advection Vector:
  // Meteorological convention: direction is azimuth the wind blows FROM (0=N, 90=E, 180=S, 270=W).
  // Vector (u, v) points in direction air mass travels TO:
  // u = -speed * sin(direction * pi / 180)
  // v = -speed * cos(direction * pi / 180)
  const rad = (direction * Math.PI) / 180.0;
  const u = -speed * Math.sin(rad);
  const v = -speed * Math.cos(rad);

  return {
    state: 'active',
    speed: Number(speed.toFixed(2)),
    direction: Number(direction.toFixed(1)),
    u: Math.abs(u) < 1e-12 ? 0.0 : Number(u.toFixed(4)),
    v: Math.abs(v) < 1e-12 ? 0.0 : Number(v.toFixed(4)),
    blacklisted: false,
  };
}

/**
 * Generates descriptive UI string for aerodrome / station wind state.
 */
export function aerodromeWindCopy(
  speed: number | null | undefined,
  direction: number | null | undefined
): string {
  const norm = normalizeWind(speed, direction);
  if (norm.state === 'dropout') {
    return 'TELEMETRY DROPOUT (NULL)';
  }
  if (norm.state === 'calm') {
    return `AERODYNAMIC CALM (< 0.50 m/s) · ${norm.speed?.toFixed(2)} m/s`;
  }
  return `${norm.speed?.toFixed(2)} m/s at ${norm.direction?.toFixed(0)}°`;
}

/**
 * Trap 5: Unifies district estimation flags into canonical `isEstimated: boolean`.
 * True if `est: true` or `is_monitored: false`.
 */
export function isDistrictEstimated(
  district: RawDistrict | NormalizedDistrict | { est?: boolean; is_estimated?: boolean; is_monitored?: boolean; isEstimated?: boolean }
): boolean {
  if (!district) return true;
  if ('isEstimated' in district && typeof district.isEstimated === 'boolean') {
    return district.isEstimated;
  }
  if ('is_estimated' in district && district.is_estimated === true) {
    return true;
  }
  if ('is_monitored' in district && district.is_monitored === false) {
    return true;
  }
  if ('est' in district && district.est === true) {
    return true;
  }
  return false;
}

/**
 * Determines whether diagonal cross-hatching styling must be applied to district polygon (Trap 5).
 */
export function shouldApplyDiagonalHatching(
  district: RawDistrict | NormalizedDistrict | { est?: boolean; is_monitored?: boolean; isEstimated?: boolean }
): boolean {
  return isDistrictEstimated(district);
}

/**
 * Trap 4: Dynamically counts station inventory breakdown (fixed vs mobile).
 */
export function countStationNetworks(
  stations: (RawStation | NormalizedStation | any)[]
): { fixed: number; mobile: number; total: number } {
  let fixed = 0;
  let mobile = 0;

  for (const st of stations) {
    const isMobile =
      st.mobile === true ||
      st.stationType === 'mobile' ||
      st.network_type === 'mobile' ||
      String(st.name || '').toLowerCase().includes('mobile');
    if (isMobile) {
      mobile++;
    } else {
      fixed++;
    }
  }

  return { fixed, mobile, total: fixed + mobile };
}

/**
 * Normalizes a raw station record into canonical NormalizedStation.
 */
export function normalizeStation(raw: RawStation): NormalizedStation {
  const lat = Number(raw.latitude ?? raw.lat ?? 0);
  const lon = Number(raw.longitude ?? raw.lon ?? 0);
  const isMobile = raw.mobile === true || raw.network_type === 'mobile';
  const stationType: StationNetworkType = isMobile ? 'mobile' : 'fixed';
  const districtName = String(raw.district ?? raw.d ?? '').trim();
  const isLahore = districtName.toLowerCase() === 'lahore';
  const stationId = raw.id ?? raw.station_id;
  const blacklisted = isStationBlacklisted(stationId) || isStationBlacklisted(raw.name);

  return {
    id: String(stationId ?? ''),
    name: String(raw.name ?? ''),
    district: districtName,
    coordinates: [lon, lat],
    latitude: lat,
    longitude: lon,
    stationType,
    mobile: isMobile,
    isLahore,
    hasAnemometer: !blacklisted,
    anemometerBlacklisted: blacklisted,
    coordSource: raw.coord_source,
    qaSummary: raw.qa_summary,
  };
}

/**
 * Normalizes an airport METAR node.
 */
export function normalizeAirport(raw: any): AirportStation {
  const lat = Number(raw.latitude ?? raw.lat ?? 0);
  const lon = Number(raw.longitude ?? raw.lon ?? 0);
  return {
    id: String(raw.id ?? raw.icao ?? ''),
    icao: String(raw.icao ?? raw.id ?? ''),
    name: String(raw.name ?? ''),
    coordinates: [lon, lat],
    latitude: lat,
    longitude: lon,
  };
}

/**
 * Normalizes a raw administrative district record.
 * Addresses Trap 1 (centroid inversion), Trap 5 (unified estimation flag).
 */
export function normalizeDistrict(raw: RawDistrict): NormalizedDistrict {
  // Trap 1: Invert centroid [lat, lon] -> [lon, lat]
  const centroidLngLatCoords = normalizeCentroid(raw.centroid);

  // Label coordinates are already [lon, lat]; fallback to normalized centroid if missing
  const labelCoords: LngLat = raw.label && raw.label.length >= 2
    ? [Number(raw.label[0]), Number(raw.label[1])]
    : centroidLngLatCoords;

  // Trap 5: Unified estimation flag
  const isEstimated = isDistrictEstimated(raw);
  const isMonitored = !isEstimated;

  const boundary = raw.boundary ?? raw.polys ?? [];
  const stations = raw.stations ?? [];
  const stationCount = raw.station_count ?? stations.length;

  return {
    id: String(raw.id ?? raw.name ?? '').toLowerCase().replace(/\s+/g, '_'),
    name: String(raw.name ?? raw.district ?? ''),
    centroid: centroidLngLatCoords,
    labelCoordinates: labelCoords,
    boundary: boundary as any,
    polys: raw.polys,
    isMonitored,
    isEstimated,
    stationCount,
    stations,
    borderDistanceKm: 999.0, // Default to far; populated from spatial analysis
    indiaInflowSectors: [],
  };
}
