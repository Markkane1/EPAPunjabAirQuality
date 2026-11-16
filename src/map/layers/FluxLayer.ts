import type { Layer } from '@deck.gl/core';
import { ArcLayer, PathLayer } from '@deck.gl/layers';
import { calculateAdvectionFlux, MAX_TRANSPORT_CONE_DEG, MAX_TRANSPORT_DISTANCE_KM } from '../../domain/math/flux';
import { centroidLngLat } from '../../domain/normalizer/dataNormalizer';
import type { NormalizedDistrict, PollutantKey } from '../../domain/types';

export interface FluxLayerProps {
  districts: NormalizedDistrict[];
  districtValues?: Record<string, number | null>;
  pm25Values?: Record<string, number | null>;
  districtWinds?: Record<string, [u: number, v: number]>;
  borderSamples?: number[][]; // 39 nodes: [lon, lat, nx, ny]
  pollutant: PollutantKey;
  visible: boolean;
  onHover?: (info: unknown) => void;
  updateTrigger?: unknown;
}

interface AdvectionLink {
  sourceDistrict: string;
  receptorDistrict: string;
  sourceCoords: [number, number];
  targetCoords: [number, number];
  flux: number;
}

interface BorderChevron {
  lon: number;
  lat: number;
  phi: number;
  color: [number, number, number, number];
  path: number[][];
}

/**
 * Creates a V-shaped chevron pointing along the direction vector [nx, ny].
 */
function createChevronPath(lon: number, lat: number, nx: number, ny: number): number[][] {
  const len = 0.06;
  const tipLon = lon + nx * len;
  const tipLat = lat + ny * len;

  const baseAngle = Math.atan2(ny, nx);
  const wing1Angle = baseAngle + (145 * Math.PI) / 180;
  const wing2Angle = baseAngle - (145 * Math.PI) / 180;
  const wingLen = 0.035;

  const w1Lon = tipLon + Math.cos(wing1Angle) * wingLen;
  const w1Lat = tipLat + Math.sin(wing1Angle) * wingLen;
  const w2Lon = tipLon + Math.cos(wing2Angle) * wingLen;
  const w2Lat = tipLat + Math.sin(wing2Angle) * wingLen;

  return [
    [w1Lon, w1Lat],
    [tipLon, tipLat],
    [w2Lon, w2Lat],
  ];
}

export function createFluxLayers(props: FluxLayerProps): Layer[] {
  if (!props.visible) return [];

  const {
    districts,
    districtValues = {},
    pm25Values = {},
    districtWinds = {},
    borderSamples = [],
    pollutant,
    updateTrigger,
  } = props;

  // Physical Dimension Guard:
  // If pollutant is AQI, calculate using PM2.5 mass values
  const effectiveValues = pollutant === 'AQI' ? pm25Values : districtValues;
  const isLocked = pollutant === 'AQI';

  // Compute top-60 advection pathway links
  const links: AdvectionLink[] = [];

  for (const src of districts) {
    const sCoords = src.centroid ? centroidLngLat(src.centroid) : src.labelCoordinates;
    const sVal = effectiveValues[src.name] ?? effectiveValues[src.id];
    if (sVal == null || sVal <= 0) continue;

    const wind = districtWinds[src.name] ?? districtWinds[src.id];
    if (!wind) continue;

    const [u, v] = wind;
    const speed = Math.hypot(u, v);
    if (speed < 0.5) continue;

    for (const rec of districts) {
      if (rec.id === src.id) continue;
      const rCoords = rec.centroid ? centroidLngLat(rec.centroid) : rec.labelCoordinates;

      const result = calculateAdvectionFlux(
        { coords: [sCoords[1], sCoords[0]], value: sVal, u, v },
        [rCoords[1], rCoords[0]],
        isLocked ? 'PM2.5' : pollutant
      );

      if (
        result &&
        result.flux > 0 &&
        result.distance_km <= MAX_TRANSPORT_DISTANCE_KM &&
        result.divergence_deg <= MAX_TRANSPORT_CONE_DEG
      ) {
        links.push({
          sourceDistrict: src.name,
          receptorDistrict: rec.name,
          sourceCoords: [sCoords[0], sCoords[1]],
          targetCoords: [rCoords[0], rCoords[1]],
          flux: result.flux,
        });
      }
    }
  }

  // Truncate to top 60 coupled pathways
  links.sort((a, b) => b.flux - a.flux);
  const top60Links = links.slice(0, 60);

  // Compute 39 border normal chevrons
  const chevrons: BorderChevron[] = [];
  for (const sample of borderSamples) {
    if (sample.length < 4) continue;
    const [lon, lat, nx, ny] = sample;

    // Find nearest district wind vector
    let nearestDist = Infinity;
    let nearestWind: [number, number] | null = null;

    for (const d of districts) {
      const c = d.centroid ? centroidLngLat(d.centroid) : d.labelCoordinates;
      const dist = (c[0] - lon) ** 2 + (c[1] - lat) ** 2;
      if (dist < nearestDist) {
        nearestDist = dist;
        nearestWind = districtWinds[d.name] ?? districtWinds[d.id] ?? null;
      }
    }

    if (!nearestWind) continue;

    const [u, v] = nearestWind;
    const phi = u * nx + v * ny;

    // Trigger crimson strictly when Phi > +0.25 m/s (inward inflow)
    // Trigger teal when Phi < -0.25 m/s (outward outflow)
    if (phi > 0.25) {
      chevrons.push({
        lon,
        lat,
        phi,
        color: [192, 0, 0, 240], // Statutory Crimson #C00000
        path: createChevronPath(lon, lat, nx, ny),
      });
    } else if (phi < -0.25) {
      chevrons.push({
        lon,
        lat,
        phi,
        color: [95, 196, 196, 220], // Outflow Teal #5fc4c4
        path: createChevronPath(lon, lat, -nx, -ny),
      });
    }
  }

  const layers: Layer[] = [];

  // 1. Inter-District Advection Mass Flux Arcs
  if (top60Links.length > 0) {
    layers.push(
      new ArcLayer({
        id: 'advection-flux-arcs',
        data: top60Links,
        getSourcePosition: (d: AdvectionLink) => d.sourceCoords,
        getTargetPosition: (d: AdvectionLink) => d.targetCoords,
        getSourceColor: [56, 189, 248, 220], // Sky blue #38bdf8
        getTargetColor: [244, 63, 94, 220],  // Rose #f43f5e
        getWidth: (d: AdvectionLink) => Math.max(1.2, Math.min(6.0, Math.sqrt(d.flux) * 0.8)),
        widthUnits: 'pixels',
        pickable: true,
        onHover: props.onHover,
        updateTriggers: {
          getSourcePosition: updateTrigger,
          getWidth: [updateTrigger, effectiveValues],
        },
      })
    );
  }

  // 2. Transboundary Border Normal Chevrons
  if (chevrons.length > 0) {
    layers.push(
      new PathLayer({
        id: 'transboundary-chevrons',
        data: chevrons,
        getPath: (d: any) => d.path,
        getColor: (d: any) => d.color,
        getWidth: 2.2,
        widthUnits: 'pixels',
        pickable: true,
        onHover: props.onHover,
        updateTriggers: {
          getColor: updateTrigger,
          getPath: updateTrigger,
        },
      })
    );
  }

  return layers;
}
