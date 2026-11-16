import { BitmapLayer } from '@deck.gl/layers';
import { anisotropicIdw, calculateDistanceOpacity, discreteGeodesicIdw } from '../../domain/math/idw';
import { pepcInterpolateColor } from '../../domain/math/pepc_aqi';
import { STATUTORY_POLLUTANTS, type PollutantKey, type SurfaceMode } from '../../domain/types';

export const PUNJAB_SURFACE_BOUNDS: [number, number, number, number] = [69.10, 27.55, 75.75, 34.30];
export const GRID_WIDTH = 150;
export const GRID_HEIGHT = 175;

export interface SurfaceLayerStation {
  id: string;
  name?: string;
  latitude: number;
  longitude: number;
  value?: number | null;
  u?: number | null;
  v?: number | null;
}

export interface SurfaceLayerProps {
  id?: string;
  visible: boolean;
  opacity?: number;
  mode?: SurfaceMode;
  pollutant: PollutantKey;
  stations: SurfaceLayerStation[];
  stationValues?: Record<string, number | null>;
  stationWinds?: Record<string, [u: number, v: number]>;
  regionalWind?: [u: number, v: number] | null;
  updateTrigger?: unknown;
}

/**
 * Layer 1: 2D continuous IDW spatial surface bitmap honoring Plate Carrée aspect ratio (K_X = cos 31°).
 * Computes on a downsampled 150x175 offscreen grid and returns a hardware-filtered BitmapLayer.
 */
export function createSurfaceLayer(props: SurfaceLayerProps): BitmapLayer | null {
  if (!props.visible) {
    return null;
  }

  if (typeof document === 'undefined') {
    return null;
  }

  const {
    id = 'surface-layer',
    opacity = 0.85,
    mode = 'anisotropic_wind_steered',
    pollutant,
    stations,
    stationValues = {},
    stationWinds = {},
    regionalWind = null,
  } = props;

  const [lonMin, latMin, lonMax, latMax] = PUNJAB_SURFACE_BOUNDS;
  const lonSpan = lonMax - lonMin;
  const latSpan = latMax - latMin;

  // Prepare station data
  const validStations = stations
    .map((st) => {
      const val = stationValues[st.id] ?? st.value;
      const wind = stationWinds[st.id];
      const u = wind ? wind[0] : st.u ?? null;
      const v = wind ? wind[1] : st.v ?? null;
      return {
        ...st,
        value: typeof val === 'number' && Number.isFinite(val) ? val : null,
        u,
        v,
        // Pixel coordinates in 150x175 grid
        x: ((st.longitude - lonMin) / lonSpan) * (GRID_WIDTH - 1),
        y: ((latMax - st.latitude) / latSpan) * (GRID_HEIGHT - 1),
      };
    })
    .filter((st) => st.value !== null);

  if (validStations.length === 0) {
    return null;
  }

  // Create offscreen raster canvas
  const canvas = document.createElement('canvas');
  canvas.width = GRID_WIDTH;
  canvas.height = GRID_HEIGHT;
  const ctx = canvas.getContext('2d');
  if (!ctx) return null;

  const imageData = ctx.createImageData(GRID_WIDTH, GRID_HEIGHT);
  const data = imageData.data;

  const meta = STATUTORY_POLLUTANTS[pollutant];
  const refLimit = meta?.peqs24hLimit ?? meta?.peqs1hLimit ?? 100.0;

  const isAnisotropic = mode === 'anisotropic_wind_steered';

  // Format stations for T1 vs T2
  const discreteNodes = validStations.map((st) => ({
    coords: [st.latitude, st.longitude] as [number, number],
    value: st.value,
  }));

  const anisotropicNodes = validStations.map((st) => ({
    coords_px: [st.x, st.y] as [number, number],
    value: st.value,
    u: st.u,
    v: st.v,
  }));

  // Rasterize grid
  let ptr = 0;
  for (let py = 0; py < GRID_HEIGHT; py++) {
    const lat = latMax - (py / (GRID_HEIGHT - 1)) * latSpan;
    for (let px = 0; px < GRID_WIDTH; px++) {
      const lon = lonMin + (px / (GRID_WIDTH - 1)) * lonSpan;

      let value: number;
      let alpha: number;

      if (isAnisotropic) {
        const [val, , a] = anisotropicIdw(
          [px, py],
          anisotropicNodes,
          regionalWind,
          1.0
        );
        value = val;
        alpha = a;
      } else {
        const val = discreteGeodesicIdw([lat, lon], discreteNodes);
        value = val ?? 0;
        // Nearest distance for opacity taper
        let minD = Infinity;
        for (const st of validStations) {
          const d = Math.hypot(px - st.x, py - st.y);
          if (d < minD) minD = d;
        }
        const kmMin = minD * (111.0 / 1.0);
        alpha = calculateDistanceOpacity(kmMin);
      }

      const [r, g, b] = pepcInterpolateColor(value, refLimit);

      data[ptr] = r;
      data[ptr + 1] = g;
      data[ptr + 2] = b;
      data[ptr + 3] = alpha;
      ptr += 4;
    }
  }

  ctx.putImageData(imageData, 0, 0);

  return new BitmapLayer({
    id,
    bounds: PUNJAB_SURFACE_BOUNDS,
    image: canvas,
    opacity,
    pickable: false,
    updateTriggers: {
      image: props.updateTrigger,
    },
  });
}
