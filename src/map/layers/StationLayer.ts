import type { Layer } from '@deck.gl/core';
import { PathLayer, PolygonLayer, ScatterplotLayer } from '@deck.gl/layers';
import { isStationBlacklisted } from '../../domain/normalizer/dataNormalizer';
import type { AirportStation, NormalizedStation, PollutantKey } from '../../domain/types';
import { pepcColorForAqi } from '../../workstation/state';

export interface StationLayerProps {
  stations: NormalizedStation[];
  airports?: AirportStation[];
  stationValues?: Record<string, number | null>;
  pollutant?: PollutantKey;
  visible: boolean;
  selectedStationId?: string | null;
  onSelect?: (entity: { kind: 'station' | 'airport'; id: string; name: string }) => void;
  onHover?: (info: unknown) => void;
  updateTrigger?: unknown;
}

function hexToRgb(hex: string): [number, number, number] {
  const clean = hex.replace('#', '');
  const r = parseInt(clean.substring(0, 2), 16) || 0;
  const g = parseInt(clean.substring(2, 4), 16) || 0;
  const b = parseInt(clean.substring(4, 6), 16) || 0;
  return [r, g, b];
}

export function createStationLayers(props: StationLayerProps): Layer[] {
  if (!props.visible) return [];

  const {
    stations = [],
    airports = [],
    stationValues = {},
    selectedStationId = null,
    updateTrigger,
  } = props;

  // 1. Separate fixed vs mobile stations
  const fixedStations: Array<{
    id: string;
    name: string;
    lon: number;
    lat: number;
    polygon: number[][];
    color: [number, number, number, number];
    isSelected: boolean;
    isBlacklisted: boolean;
    isLahore: boolean;
    rawVal: number | null;
  }> = [];

  const mobileStations: Array<{
    id: string;
    name: string;
    lon: number;
    lat: number;
    polygon: number[][];
    color: [number, number, number, number];
    isSelected: boolean;
    isLahore: boolean;
    rawVal: number | null;
  }> = [];

  const dFix = 0.015; // Square half-width
  const dMob = 0.018; // Diamond extent

  for (const st of stations) {
    const lon = st.coordinates[0];
    const lat = st.coordinates[1];
    const rawVal = stationValues[st.id] ?? stationValues[st.name] ?? null;
    const paint = pepcColorForAqi(rawVal);
    const rgb = hexToRgb(paint.hex);
    const isSelected = selectedStationId === st.id || selectedStationId === st.name;
    const isBl = isStationBlacklisted(st.id);
    const isLahore = st.district?.toLowerCase() === 'lahore' || st.isLahore === true;

    if (st.mobile || st.stationType === 'mobile') {
      // 5 Mobile diamonds: [0, -d], [d, 0], [0, d], [-d, 0]
      mobileStations.push({
        id: st.id,
        name: st.name,
        lon,
        lat,
        polygon: [
          [lon, lat - dMob],
          [lon + dMob, lat],
          [lon, lat + dMob],
          [lon - dMob, lat],
        ],
        color: [...rgb, 230],
        isSelected,
        isLahore,
        rawVal,
      });
    } else {
      // 74 Fixed squares: [-d, -d], [d, -d], [d, d], [-d, d]
      fixedStations.push({
        id: st.id,
        name: st.name,
        lon,
        lat,
        polygon: [
          [lon - dFix, lat - dFix],
          [lon + dFix, lat - dFix],
          [lon + dFix, lat + dFix],
          [lon - dFix, lat + dFix],
        ],
        color: isBl ? [192, 0, 0, 240] : [...rgb, 230],
        isSelected,
        isBlacklisted: isBl,
        isLahore,
        rawVal,
      });
    }
  }

  // 2. 6 Aerodromes Crosshairs
  const dAir = 0.025;
  const aerodromePaths: Array<{
    id: string;
    name: string;
    path: number[][];
    lon: number;
    lat: number;
  }> = [];

  for (const ap of airports) {
    const lon = ap.coordinates[0];
    const lat = ap.coordinates[1];
    // Crosshair: 2 intersecting lines
    aerodromePaths.push(
      {
        id: ap.icao || ap.id,
        name: ap.name,
        path: [
          [lon - dAir, lat],
          [lon + dAir, lat],
        ],
        lon,
        lat,
      },
      {
        id: ap.icao || ap.id,
        name: ap.name,
        path: [
          [lon, lat - dAir],
          [lon, lat + dAir],
        ],
        lon,
        lat,
      }
    );
  }

  // Unified pickable points for seamless hover/click across all 79 stations and airports
  const pickableEntities = [
    ...fixedStations.map((st) => ({
      kind: 'station' as const,
      id: st.id,
      name: st.name,
      position: [st.lon, st.lat] as [number, number],
      isLahore: st.isLahore,
    })),
    ...mobileStations.map((st) => ({
      kind: 'station' as const,
      id: st.id,
      name: st.name,
      position: [st.lon, st.lat] as [number, number],
      isLahore: st.isLahore,
    })),
    ...airports.map((ap) => ({
      kind: 'airport' as const,
      id: ap.icao || ap.id,
      name: ap.name,
      position: [ap.coordinates[0], ap.coordinates[1]] as [number, number],
      isLahore: false,
    })),
  ];

  const layers: Layer[] = [];

  // 1. Fixed Stations (74 squares)
  if (fixedStations.length > 0) {
    layers.push(
      new PolygonLayer({
        id: 'station-fixed-squares',
        data: fixedStations,
        getPolygon: (d: any) => d.polygon,
        getFillColor: (d: any): [number, number, number, number] => d.color,
        getLineColor: (d: any): [number, number, number, number] =>
          d.isSelected ? [255, 255, 255, 255] : [15, 23, 42, 220],
        getLineWidth: (d: any) => (d.isSelected ? 2 : 1),
        lineWidthUnits: 'pixels',
        filled: true,
        stroked: true,
        pickable: false,
        updateTriggers: {
          getFillColor: [updateTrigger, stationValues],
          getLineColor: selectedStationId,
        },
      })
    );
  }

  // 2. Mobile Stations (5 diamonds)
  if (mobileStations.length > 0) {
    layers.push(
      new PolygonLayer({
        id: 'station-mobile-diamonds',
        data: mobileStations,
        getPolygon: (d: any) => d.polygon,
        getFillColor: (d: any): [number, number, number, number] => d.color,
        getLineColor: (d: any): [number, number, number, number] =>
          d.isSelected ? [255, 255, 255, 255] : [15, 23, 42, 220],
        getLineWidth: (d: any) => (d.isSelected ? 2 : 1),
        lineWidthUnits: 'pixels',
        filled: true,
        stroked: true,
        pickable: false,
        updateTriggers: {
          getFillColor: [updateTrigger, stationValues],
          getLineColor: selectedStationId,
        },
      })
    );
  }

  // 3. Aerodromes (6 crosshairs)
  if (aerodromePaths.length > 0) {
    layers.push(
      new PathLayer({
        id: 'station-aerodrome-crosshairs',
        data: aerodromePaths,
        getPath: (d: any) => d.path,
        getColor: [56, 189, 248, 240], // Sky blue #38bdf8
        getWidth: 1.8,
        widthUnits: 'pixels',
        pickable: false,
      })
    );
  }

  // 4. Interactive Picking Layer (Picking radius 8px, distinct picking for all 13 Lahore stations)
  layers.push(
    new ScatterplotLayer({
      id: 'station-picking-hitboxes',
      data: pickableEntities,
      getPosition: (d: any) => d.position,
      getRadius: 8,
      radiusUnits: 'pixels',
      filled: true,
      getFillColor: [0, 0, 0, 0], // Invisible hitbox
      pickable: true,
      autoHighlight: true,
      highlightColor: [255, 255, 255, 60],
      onClick: (info: any) => {
        if (info.object) {
          props.onSelect?.({
            kind: info.object.kind,
            id: info.object.id,
            name: info.object.name,
          });
        }
      },
      onHover: props.onHover,
    })
  );

  return layers;
}
