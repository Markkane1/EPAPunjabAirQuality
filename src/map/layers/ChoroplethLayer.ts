import type { Layer } from '@deck.gl/core';
import { GeoJsonLayer, LineLayer, PathLayer, TextLayer } from '@deck.gl/layers';
import {
  checkAabbCollision,
  equirectangularProject,
  equirectangularUnproject,
  LABEL_CANDIDATE_OFFSETS,
  LEADER_LINE_THRESHOLD_PX,
} from '../../domain/math/projection';
import { centroidLngLat } from '../../domain/normalizer/dataNormalizer';
import type { NormalizedDistrict, PollutantKey } from '../../domain/types';
import { pepcColorForAqi } from '../../workstation/state';

export interface ChoroplethLayerProps {
  districts: NormalizedDistrict[];
  districtValues?: Record<string, number | null>;
  pollutant?: PollutantKey;
  visible: boolean;
  selectedDistrictId?: string | null;
  onSelect?: (district: NormalizedDistrict) => void;
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

/**
 * Generates 45-degree diagonal hatching lines across the bounding box of an estimated district.
 */
function generateHatchLines(district: NormalizedDistrict): number[][][] {
  let minLon = Infinity;
  let maxLon = -Infinity;
  let minLat = Infinity;
  let maxLat = -Infinity;

  const extractCoords = (coords: unknown): void => {
    if (!Array.isArray(coords)) return;
    if (typeof coords[0] === 'number' && typeof coords[1] === 'number') {
      const [lon, lat] = coords as [number, number];
      if (lon < minLon) minLon = lon;
      if (lon > maxLon) maxLon = lon;
      if (lat < minLat) minLat = lat;
      if (lat > maxLat) maxLat = lat;
    } else {
      coords.forEach(extractCoords);
    }
  };

  extractCoords(district.boundary);
  if (!isFinite(minLon) || !isFinite(minLat)) return [];

  const step = 0.07;
  const lines: number[][][] = [];
  const width = maxLon - minLon;
  const height = maxLat - minLat;
  const span = width + height;

  for (let d = -height; d <= width; d += step) {
    const x1 = minLon + Math.max(0, d);
    const y1 = minLat + Math.max(0, -d);
    const x2 = minLon + Math.min(width, d + span);
    const y2 = minLat + Math.min(height, -d + span);
    if (x2 > x1 && y2 > y1) {
      lines.push([
        [x1, y1],
        [x2, y2],
      ]);
    }
  }

  return lines;
}

export function createChoroplethLayers(props: ChoroplethLayerProps): Layer[] {
  if (!props.visible) return [];

  const {
    districts,
    districtValues = {},
    selectedDistrictId = null,
    updateTrigger,
  } = props;

  // Build GeoJSON features for districts
  const geojsonFeatures = districts.map((district) => {
    const rawVal = districtValues[district.name] ?? districtValues[district.id] ?? null;
    const paint = pepcColorForAqi(rawVal);
    const isSelected = selectedDistrictId === district.id || selectedDistrictId === district.name;
    const isEstimated = district.isEstimated;

    return {
      type: 'Feature' as const,
      geometry: {
        type: Array.isArray(district.boundary[0]?.[0]?.[0]) ? 'MultiPolygon' : 'Polygon',
        coordinates: district.boundary,
      },
      properties: {
        ...district,
        rawVal,
        fillColor: hexToRgb(paint.hex),
        isSelected,
        isEstimated,
      },
    };
  });

  const layers: Layer[] = [];

  // 1. District Polygons Fills & Borders
  layers.push(
    new GeoJsonLayer({
      id: 'district-choropleth-layer',
      data: {
        type: 'FeatureCollection',
        features: geojsonFeatures,
      },
      filled: true,
      stroked: true,
      getFillColor: (f: any): [number, number, number, number] => {
        const c = f.properties?.fillColor ?? [51, 65, 85];
        return [c[0], c[1], c[2], 190];
      },
      getLineColor: (f: any): [number, number, number, number] =>
        f.properties?.isSelected ? [255, 255, 255, 255] : [148, 163, 184, 200],
      getLineWidth: (f: any) => (f.properties?.isSelected ? 2 : 1),
      lineWidthUnits: 'pixels',
      pickable: true,
      autoHighlight: true,
      highlightColor: [255, 255, 255, 40],
      onClick: (info: any) => {
        if (info.object?.properties) {
          props.onSelect?.(info.object.properties as NormalizedDistrict);
        }
      },
      onHover: props.onHover,
      updateTriggers: {
        getFillColor: [updateTrigger, districtValues],
        getLineColor: selectedDistrictId,
        getLineWidth: selectedDistrictId,
      },
    })
  );

  // 2. Diagonal Cross-Hatching for Estimated / Unmonitored Districts
  const hatchPaths: Array<{ path: number[][] }> = [];
  districts
    .filter((d) => d.isEstimated)
    .forEach((d) => {
      const lines = generateHatchLines(d);
      for (const line of lines) {
        hatchPaths.push({ path: line });
      }
    });

  if (hatchPaths.length > 0) {
    layers.push(
      new PathLayer({
        id: 'district-hatch-layer',
        data: hatchPaths,
        getPath: (d: any) => d.path,
        getColor: [226, 232, 240, 130],
        getWidth: 1,
        widthUnits: 'pixels',
        pickable: false,
      })
    );
  }

  // 3. Collision-free Greedy AABB Labels & Leader Lines (Transform T11)
  const placedBoxes: Array<[number, number, number, number]> = [];
  const placedLabels: Array<{
    name: string;
    anchorLngLat: [number, number];
    placedLngLat: [number, number];
    hasLeader: boolean;
  }> = [];

  for (const d of districts) {
    const anchor = d.centroid ? centroidLngLat(d.centroid) : d.labelCoordinates;
    const [anchorLon, anchorLat] = anchor;
    const [anchorX, anchorY] = equirectangularProject(anchorLat, anchorLon);

    const w = Math.max(36, d.name.length * 6.8);
    const h = 14;

    let chosenOffset: [number, number] = [0, 0];
    let found = false;

    for (const [dx, dy] of LABEL_CANDIDATE_OFFSETS) {
      const candBox: [number, number, number, number] = [
        anchorX + dx - w / 2,
        anchorY + dy - h / 2,
        w,
        h,
      ];

      const collides = placedBoxes.some((box) => checkAabbCollision(candBox, box));
      if (!collides) {
        placedBoxes.push(candBox);
        chosenOffset = [dx, dy];
        found = true;
        break;
      }
    }

    if (!found) {
      placedBoxes.push([anchorX - w / 2, anchorY - h / 2, w, h]);
      chosenOffset = [0, 0];
    }

    const [placedLat, placedLon] = equirectangularUnproject(
      anchorX + chosenOffset[0],
      anchorY + chosenOffset[1]
    );

    const offsetDist = Math.hypot(chosenOffset[0], chosenOffset[1]);
    const hasLeader = offsetDist > LEADER_LINE_THRESHOLD_PX;

    placedLabels.push({
      name: d.name,
      anchorLngLat: [anchorLon, anchorLat],
      placedLngLat: [placedLon, placedLat],
      hasLeader,
    });
  }

  // Leader lines
  const leaderLines = placedLabels
    .filter((l) => l.hasLeader)
    .map((l) => ({
      sourcePosition: l.anchorLngLat,
      targetPosition: l.placedLngLat,
    }));

  if (leaderLines.length > 0) {
    layers.push(
      new LineLayer({
        id: 'district-label-leaders',
        data: leaderLines,
        getSourcePosition: (d: any) => d.sourcePosition,
        getTargetPosition: (d: any) => d.targetPosition,
        getColor: [226, 232, 240, 200],
        getWidth: 1,
        widthUnits: 'pixels',
        pickable: false,
      })
    );
  }

  // Label text
  layers.push(
    new TextLayer({
      id: 'district-labels',
      data: placedLabels,
      getPosition: (d: any) => d.placedLngLat,
      getText: (d: any) => d.name,
      getSize: 11,
      getColor: [255, 255, 255, 245],
      fontFamily: 'IBM Plex Sans, sans-serif',
      fontWeight: 600,
      getTextAnchor: 'middle',
      getAlignmentBaseline: 'center',
      outlineWidth: 2,
      outlineColor: [15, 23, 22, 255],
      pickable: false,
      updateTriggers: {
        data: updateTrigger,
      },
    })
  );

  return layers;
}
