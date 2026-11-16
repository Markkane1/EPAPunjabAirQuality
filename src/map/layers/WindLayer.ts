import type { Layer } from '@deck.gl/core';
import { PathLayer, ScatterplotLayer } from '@deck.gl/layers';
import { isStationBlacklisted, normalizeWind } from '../../domain/normalizer/dataNormalizer';
import type { AirportStation, NormalizedDistrict, NormalizedStation } from '../../domain/types';

export interface WindLayerProps {
  districts?: NormalizedDistrict[];
  stations?: NormalizedStation[];
  airports?: AirportStation[];
  districtWinds?: Record<string, [u: number, v: number]>;
  stationWinds?: Record<string, [u: number, v: number]>;
  airportWinds?: Record<string, [u: number, v: number]>;
  visible: boolean;
  onHover?: (info: unknown) => void;
  updateTrigger?: unknown;
}

interface WindVectorItem {
  id: string;
  name: string;
  kind: 'district' | 'station' | 'airport';
  lon: number;
  lat: number;
  state: 'active' | 'calm' | 'dropout' | 'blacklisted';
  speed: number | null;
  direction: number | null;
  u: number;
  v: number;
  blacklistReason?: string;
}

/**
 * Creates arrow path geometry [origin, tip, fin1, tip, fin2] for an active wind vector.
 */
function createArrowPath(
  lon: number,
  lat: number,
  u: number,
  v: number,
  speed: number
): number[][] {
  const scale = 0.012 + Math.min(speed, 30.0) * 0.0035;
  const tipLon = lon + u * scale;
  const tipLat = lat + v * scale;

  // Arrowhead fins
  const arrowLen = 0.025;
  const angle = Math.atan2(v, u);
  const fin1Angle = angle + (150 * Math.PI) / 180;
  const fin2Angle = angle - (150 * Math.PI) / 180;

  const fin1Lon = tipLon + Math.cos(fin1Angle) * arrowLen;
  const fin1Lat = tipLat + Math.sin(fin1Angle) * arrowLen;
  const fin2Lon = tipLon + Math.cos(fin2Angle) * arrowLen;
  const fin2Lat = tipLat + Math.sin(fin2Angle) * arrowLen;

  return [
    [lon, lat],
    [tipLon, tipLat],
    [fin1Lon, fin1Lat],
    [tipLon, tipLat],
    [fin2Lon, fin2Lat],
  ];
}

export function createWindLayers(props: WindLayerProps): Layer[] {
  if (!props.visible) return [];

  const {
    districts = [],
    stations = [],
    airports = [],
    districtWinds = {},
    stationWinds = {},
    airportWinds = {},
    updateTrigger,
  } = props;

  const items: WindVectorItem[] = [];

  // 1. District winds
  for (const d of districts) {
    const uv = districtWinds[d.name] ?? districtWinds[d.id];
    const lon = d.centroid[0];
    const lat = d.centroid[1];
    if (uv && typeof uv[0] === 'number' && typeof uv[1] === 'number') {
      const u = uv[0];
      const v = uv[1];
      const speed = Math.hypot(u, v);
      const state = speed < 0.5 ? 'calm' : 'active';
      items.push({
        id: `district-wind-${d.id}`,
        name: d.name,
        kind: 'district',
        lon,
        lat,
        state,
        speed,
        direction: (Math.atan2(-u, -v) * 180) / Math.PI,
        u,
        v,
      });
    }
  }

  // 2. Station winds (enforcing Station 172 Wazirabad blacklist)
  for (const st of stations) {
    const lon = st.coordinates[0];
    const lat = st.coordinates[1];
    const isBl = isStationBlacklisted(st.id);

    if (isBl) {
      items.push({
        id: `station-wind-${st.id}`,
        name: st.name,
        kind: 'station',
        lon,
        lat,
        state: 'blacklisted',
        speed: null,
        direction: null,
        u: 0,
        v: 0,
        blacklistReason: 'ANEMOMETER BLACKLISTED (VANE OFFSET)',
      });
      continue;
    }

    const uv = stationWinds[st.id] ?? stationWinds[st.name];
    if (!uv) {
      items.push({
        id: `station-wind-${st.id}`,
        name: st.name,
        kind: 'station',
        lon,
        lat,
        state: 'dropout',
        speed: null,
        direction: null,
        u: 0,
        v: 0,
      });
    } else {
      const u = uv[0];
      const v = uv[1];
      const norm = normalizeWind(Math.hypot(u, v), 0, st.id);
      items.push({
        id: `station-wind-${st.id}`,
        name: st.name,
        kind: 'station',
        lon,
        lat,
        state: norm.state === 'dropout' ? 'dropout' : norm.state === 'calm' ? 'calm' : 'active',
        speed: norm.speed,
        direction: norm.direction,
        u,
        v,
      });
    }
  }

  // 3. Airport winds
  for (const ap of airports) {
    const lon = ap.coordinates[0];
    const lat = ap.coordinates[1];
    const uv = airportWinds[ap.icao] ?? airportWinds[ap.id];

    if (!uv || uv[0] == null || uv[1] == null) {
      items.push({
        id: `airport-wind-${ap.icao}`,
        name: ap.name,
        kind: 'airport',
        lon,
        lat,
        state: 'dropout',
        speed: null,
        direction: null,
        u: 0,
        v: 0,
      });
    } else {
      const u = uv[0];
      const v = uv[1];
      const speed = Math.hypot(u, v);
      const state = speed < 0.5 ? 'calm' : 'active';
      items.push({
        id: `airport-wind-${ap.icao}`,
        name: ap.name,
        kind: 'airport',
        lon,
        lat,
        state,
        speed,
        direction: (Math.atan2(-u, -v) * 180) / Math.PI,
        u,
        v,
      });
    }
  }

  const layers: Layer[] = [];

  // Active wind arrows
  const activeArrows = items
    .filter((it) => it.state === 'active')
    .map((it) => ({
      path: createArrowPath(it.lon, it.lat, it.u, it.v, it.speed ?? 1.0),
      item: it,
    }));

  if (activeArrows.length > 0) {
    layers.push(
      new PathLayer({
        id: 'wind-active-vectors',
        data: activeArrows,
        getPath: (d) => d.path,
        getColor: [226, 232, 240, 220],
        getWidth: 1.5,
        widthUnits: 'pixels',
        pickable: true,
        onHover: props.onHover,
        updateTriggers: {
          getPath: updateTrigger,
        },
      })
    );
  }

  // Calm wind circles (<0.50 m/s)
  const calmPoints = items.filter((it) => it.state === 'calm');
  if (calmPoints.length > 0) {
    layers.push(
      new ScatterplotLayer({
        id: 'wind-calm-circles',
        data: calmPoints,
        getPosition: (d) => [d.lon, d.lat],
        getRadius: 4.5,
        radiusUnits: 'pixels',
        filled: false,
        stroked: true,
        getLineColor: [148, 163, 184, 200],
        getLineWidth: 1.25,
        lineWidthUnits: 'pixels',
        pickable: true,
        onHover: props.onHover,
      })
    );
  }

  // Telemetry dropout glyphs (null)
  const dropouts = items.filter((it) => it.state === 'dropout');
  if (dropouts.length > 0) {
    layers.push(
      new ScatterplotLayer({
        id: 'wind-dropout-glyphs',
        data: dropouts,
        getPosition: (d) => [d.lon, d.lat],
        getRadius: 3.5,
        radiusUnits: 'pixels',
        filled: true,
        getFillColor: [100, 116, 139, 120],
        stroked: true,
        getLineColor: [100, 116, 139, 200],
        getLineWidth: 1,
        lineWidthUnits: 'pixels',
        pickable: true,
        onHover: props.onHover,
      })
    );
  }

  // Station 172 Wazirabad blacklist alert badge
  const blacklisted = items.filter((it) => it.state === 'blacklisted');
  if (blacklisted.length > 0) {
    layers.push(
      new ScatterplotLayer({
        id: 'wind-blacklisted-badges',
        data: blacklisted,
        getPosition: (d) => [d.lon, d.lat],
        getRadius: 7,
        radiusUnits: 'pixels',
        filled: true,
        getFillColor: [192, 0, 0, 230], // Crimson #C00000
        stroked: true,
        getLineColor: [255, 255, 255, 255],
        getLineWidth: 1.5,
        lineWidthUnits: 'pixels',
        pickable: true,
        onHover: props.onHover,
      })
    );
  }

  return layers;
}
