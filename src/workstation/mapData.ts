import { centroidLngLat, districtUsesHatch, pepcColorForAqi, speedFromUv } from './state';

export interface GeoFeature {
  type: 'Feature';
  geometry: { type: string; coordinates: unknown };
  properties: Record<string, string | number | boolean | null>;
}

export interface GeoCollection {
  type: 'FeatureCollection';
  features: GeoFeature[];
}

export interface DistrictSource {
  id: string;
  name: string;
  centroid?: [number, number];
  latitude?: number;
  longitude?: number;
  boundary?: unknown;
  est?: boolean;
  is_estimated?: boolean;
  is_monitored?: boolean;
}

function depth(value: unknown): number {
  let level = 0;
  let cursor = value;
  while (Array.isArray(cursor)) {
    level += 1;
    cursor = cursor[0];
  }
  return level;
}

function normalizePosition(point: number[]): [number, number] {
  return centroidLngLat([point[0], point[1]]);
}

function normalizeRing(ring: number[][]): number[][] {
  return ring.map((point) => normalizePosition(point));
}

export function districtGeometry(boundary: unknown): GeoFeature['geometry'] | null {
  const level = depth(boundary);
  if (level === 3) {
    return { type: 'Polygon', coordinates: (boundary as number[][][]).map((ring) => normalizeRing(ring)) };
  }
  if (level === 4) {
    return {
      type: 'MultiPolygon',
      coordinates: (boundary as number[][][][]).map((polygon) => polygon.map((ring) => normalizeRing(ring))),
    };
  }
  return null;
}

export function districtFeatures(
  districts: DistrictSource[],
  aqiByName: Record<string, number | null>,
): GeoCollection {
  const features: GeoFeature[] = [];
  for (const district of districts) {
    const geometry = districtGeometry(district.boundary);
    if (!geometry) continue;
    const estimated = district.est === true || district.is_estimated === true || district.is_monitored === false;
    const aqi = aqiByName[district.name] ?? null;
    const paint = pepcColorForAqi(aqi);
    features.push({
      type: 'Feature',
      geometry,
      properties: {
        kind: 'district',
        id: district.id,
        name: district.name,
        estimated: districtUsesHatch(estimated),
        color: aqi === null ? '#334155' : paint.hex,
        aqi: aqi === null ? '' : Math.round(aqi),
      },
    });
  }
  return { type: 'FeatureCollection', features };
}

export function stationFeatures(
  stations: Array<{ id?: string; name?: string; latitude?: number; longitude?: number; mobile?: boolean; district?: string }>,
  airports: Array<{ id?: string; icao?: string; name?: string; latitude?: number; longitude?: number }>,
): GeoCollection {
  const features: GeoFeature[] = [];
  for (const station of stations) {
    if (typeof station.longitude !== 'number' || typeof station.latitude !== 'number') continue;
    const blacklisted = String(station.id) === '172' || (station.name ?? '').toLowerCase().includes('wazirabad');
    features.push({
      type: 'Feature',
      geometry: { type: 'Point', coordinates: [station.longitude, station.latitude] },
      properties: {
        kind: 'station',
        id: station.id ?? station.name ?? '',
        name: station.name ?? '',
        mobile: station.mobile === true,
        blacklisted,
        district: station.district ?? '',
      },
    });
  }
  for (const airport of airports) {
    if (typeof airport.longitude !== 'number' || typeof airport.latitude !== 'number') continue;
    features.push({
      type: 'Feature',
      geometry: { type: 'Point', coordinates: [airport.longitude, airport.latitude] },
      properties: {
        kind: 'airport',
        id: airport.icao ?? airport.id ?? '',
        name: airport.name ?? airport.icao ?? '',
        mobile: false,
        blacklisted: false,
        district: '',
      },
    });
  }
  return { type: 'FeatureCollection', features };
}

export function windFeatures(
  districts: DistrictSource[],
  windByName: Record<string, number[] | null | undefined>,
  airports: Array<{ icao?: string; name?: string; latitude?: number; longitude?: number; u?: number | null; v?: number | null }>,
): GeoCollection {
  const features: GeoFeature[] = [];
  for (const district of districts) {
    const vector = windByName[district.name];
    if (!vector || vector.length < 2) continue;
    const [u, v] = vector;
    if (speedFromUv(u, v) < 0.5) continue;
    const origin = district.centroid
      ? centroidLngLat(district.centroid)
      : ([district.longitude ?? 0, district.latitude ?? 0] as [number, number]);
    const scale = 0.015 + Math.min(speedFromUv(u, v), 30) * 0.004;
    features.push({
      type: 'Feature',
      geometry: {
        type: 'LineString',
        coordinates: [origin, [origin[0] + u * scale, origin[1] + v * scale]],
      },
      properties: { kind: 'wind', name: district.name, id: district.id },
    });
  }
  for (const airport of airports) {
    if (typeof airport.longitude !== 'number' || typeof airport.latitude !== 'number') continue;
    if (airport.u === null || airport.u === undefined || airport.v === null || airport.v === undefined) continue;
    if (speedFromUv(airport.u, airport.v) < 0.5) continue;
    const scale = 0.02;
    features.push({
      type: 'Feature',
      geometry: {
        type: 'LineString',
        coordinates: [
          [airport.longitude, airport.latitude],
          [airport.longitude + airport.u * scale, airport.latitude + airport.v * scale],
        ],
      },
      properties: { kind: 'wind', name: airport.name ?? airport.icao ?? '', id: airport.icao ?? '' },
    });
  }
  return { type: 'FeatureCollection', features };
}

export function fluxFeatures(
  links: Array<[string, string, number] | unknown>,
  districts: DistrictSource[],
): GeoCollection {
  const byName = new Map(districts.map((district) => [district.name, district]));
  const features: GeoFeature[] = [];
  const rows = links.slice(0, 60);
  for (const link of rows) {
    if (!Array.isArray(link) || link.length < 2) continue;
    const source = byName.get(String(link[0]));
    const target = byName.get(String(link[1]));
    if (!source?.centroid || !target?.centroid) continue;
    features.push({
      type: 'Feature',
      geometry: {
        type: 'LineString',
        coordinates: [centroidLngLat(source.centroid), centroidLngLat(target.centroid)],
      },
      properties: { kind: 'flux', name: `${link[0]} \u2192 ${link[1]}`, id: `${link[0]}-${link[1]}` },
    });
  }
  return { type: 'FeatureCollection', features };
}

export function chevronFeatures(
  samples: number[][],
  districts: DistrictSource[],
  windByName: Record<string, number[] | null | undefined>,
): { count: number; collection: GeoCollection } {
  const features: GeoFeature[] = [];
  let count = 0;
  for (const sample of samples) {
    if (sample.length < 4) continue;
    const [lon, lat, nx, ny] = sample;
    let best = Infinity;
    let vector: number[] | null = null;
    for (const district of districts) {
      const longitude = district.longitude ?? (district.centroid ? centroidLngLat(district.centroid)[0] : undefined);
      const latitude = district.latitude ?? (district.centroid ? centroidLngLat(district.centroid)[1] : undefined);
      if (typeof longitude !== 'number' || typeof latitude !== 'number') continue;
      const dist = (longitude - lon) ** 2 + (latitude - lat) ** 2;
      if (dist < best) {
        best = dist;
        vector = windByName[district.name] ?? null;
      }
    }
    if (!vector) continue;
    const phi = vector[0] * nx + vector[1] * ny;
    if (!(phi > 0.25)) continue;
    count += 1;
    features.push({
      type: 'Feature',
      geometry: {
        type: 'LineString',
        coordinates: [
          [lon, lat],
          [lon + nx * 0.12, lat + ny * 0.12],
        ],
      },
      properties: { kind: 'chevron', name: 'Inflow', id: `${lon.toFixed(3)},${lat.toFixed(3)}`, phi: Number(phi.toFixed(2)) },
    });
  }
  return { count, collection: { type: 'FeatureCollection', features } };
}

export function labelAnchors(districts: DistrictSource[]): Array<{ id: string; name: string; longitude: number; latitude: number }> {
  return districts.map((district) => {
    const [longitude, latitude] = district.centroid
      ? centroidLngLat(district.centroid)
      : [district.longitude ?? 0, district.latitude ?? 0];
    return { id: district.id, name: district.name, longitude, latitude };
  });
}

export const EMPTY_COLLECTION: GeoCollection = { type: 'FeatureCollection', features: [] };
