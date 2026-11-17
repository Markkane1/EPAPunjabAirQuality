import { STATUTORY_POLLUTANTS, type LayerId, type PollutantKey } from '../domain/types';

export const WORKSTATION_TITLE = 'EPA Punjab Air Quality';
export const HORIZON_START = '2026-11-01 00:00';
export const HORIZON_END = '2026-11-09 23:00';
export const HORIZON_HOURS = 216;
export const BLACKLIST_TEXT = 'ANEMOMETER BLACKLISTED (VANE OFFSET)';
export const DIMENSION_GUARD = 'Dimension Guard: Flux locked to PM2.5 mass';

export const POLLUTANT_KEYS = Object.keys(STATUTORY_POLLUTANTS) as PollutantKey[];

export const WORKSTATION_ZONES = [
  { id: 'command-bar', dataZone: 'command-bar' },
  { id: 'spatial-dock', dataZone: 'spatial-dock' },
  { id: 'map-canvas', dataZone: 'map-canvas' },
  { id: 'receptor-inspector', dataZone: 'receptor-inspector' },
  { id: 'temporal-scrubber', dataZone: 'temporal-scrubber' },
] as const;

export const MAP_LOCK = {
  pitch: 0 as const,
  maxPitch: 0,
  bearing: 0,
  dragRotate: false,
  touchPitch: false,
};

export type PlaybackRate = '1x' | '2x' | '4x' | '8x';

export type LayerVisibility = Record<LayerId, boolean>;

export interface StationRecord {
  id?: string;
  name?: string;
  mobile?: boolean;
  network_type?: string;
  district?: string;
  latitude?: number;
  longitude?: number;
}

export interface DistrictRowInput {
  id: string;
  name: string;
  value: number | null;
  aqi: number | null;
  isEstimated: boolean;
  latitude: number;
  longitude: number;
}

export interface SectorInput {
  sectorIndex: number;
  totalHours: number;
  cpfProbability: number | null;
  azimuthDeg: number;
}

export interface SelectionInput {
  kind: 'district' | 'station' | 'airport';
  id: string;
  name: string;
  stationType?: 'fixed' | 'mobile';
  latitude: number;
  longitude: number;
}

export interface ReadingInput {
  key: PollutantKey;
  concentration: number | null;
}

export interface QcMark {
  value: number | null;
  spike: boolean;
  hold: boolean;
}

export interface WorkstationInput {
  stations: StationRecord[];
  pollutant: PollutantKey;
  stream: 'live' | 'fallback';
  hourIndex: number;
  lerpAlpha: number;
  timestamp: string;
  search: string;
  layers: LayerVisibility;
  selected: SelectionInput | null;
  districtRows: DistrictRowInput[];
  maxPm25: number | null;
  windSpeed: number | null;
  windDirection: number | null;
  validHours: number;
  totalHours: number;
  fluxLinks: unknown[];
  playbackSpeed: PlaybackRate;
  isPlaying: boolean;
  domesticShare: number;
  inflowShare: number;
  activeChevrons: number;
  exportMass: number;
  importMass: number;
  p75Threshold: number;
  calmHours: number;
  pooledStationCount: number;
  pooled: boolean;
  sectors: SectorInput[];
  readings?: ReadingInput[];
  qcSeries?: QcMark[];
  horizon?: number[];
  qaLines?: string[];
}

export interface LegendTier {
  label: string;
  hex: string;
  min: number;
  max: number;
}

export interface HazardousAlert {
  role: 'alert';
  ariaLive: 'assertive';
  background: '#C00000';
  color: '#FFFFFF';
  text: string;
}

const LEGEND: LegendTier[] = [
  { label: 'Good 0\u201350', hex: '#00B050', min: 0, max: 50 },
  { label: 'Satisfactory 51\u2013100', hex: '#92D050', min: 51, max: 100 },
  { label: 'Moderate 101\u2013150', hex: '#FFFF00', min: 101, max: 150 },
  { label: 'Unhealthy (Sensitive) 151\u2013200', hex: '#ED7D31', min: 151, max: 200 },
  { label: 'Unhealthy 201\u2013300', hex: '#FF0000', min: 201, max: 300 },
  { label: 'Very Unhealthy 301\u2013400', hex: '#7030A0', min: 301, max: 400 },
  { label: 'Hazardous 401+', hex: '#C00000', min: 401, max: 9999 },
];

const SUBINDEX_BREAKS: Record<string, number[]> = {
  PM10: [0, 75, 150, 250, 350, 450, 550],
  'PM2.5': [0, 15, 35, 70, 140, 250, 350],
  SO2: [0, 60, 120, 220, 320, 800, 1600],
  NO2: [0, 40, 80, 130, 180, 380, 580],
  O3: [0, 65, 130, 195, 260, 450, 550],
  CO: [0, 2.5, 5, 7.5, 10, 25, 40],
};
const SUBINDEX_TIERS = [0, 50, 100, 150, 200, 300, 400, 500];

export function pepcLegend(): LegendTier[] {
  return LEGEND.map((tier) => ({ ...tier }));
}

export function pepcColorForAqi(aqi: number | null): { hex: string; text: string; label: string } {
  if (aqi === null || Number.isNaN(aqi)) {
    return { hex: '#64748b', text: '#FFFFFF', label: 'No data' };
  }
  const tier = LEGEND.find((item) => aqi <= item.max) ?? LEGEND[LEGEND.length - 1];
  const text = aqi <= 300 ? '#000000' : '#FFFFFF';
  return { hex: tier.hex, text, label: tier.label.replace(/\s+\d.*$/, '') };
}

export function countStationNetworks(stations: StationRecord[]): { fixed: number; mobile: number } {
  let mobile = 0;
  for (const station of stations) {
    if (station.mobile === true || station.network_type === 'mobile') mobile += 1;
  }
  return { fixed: stations.length - mobile, mobile };
}

export function streamBadgeCopy(mode: 'live' | 'fallback'): string {
  return mode === 'live' ? 'LIVE SSE' : 'BASELINE FALLBACK';
}

export function fluxForPollutant<T>(pollutant: PollutantKey, links: T[]): T[] {
  return pollutant === 'AQI' ? [] : links;
}

export function dimensionGuardCopy(pollutant: PollutantKey): string | null {
  return pollutant === 'AQI' ? DIMENSION_GUARD : null;
}

export function estimatedBadge(isEstimated: boolean): 'EST' | null {
  return isEstimated ? 'EST' : null;
}

export function districtUsesHatch(isEstimated: boolean): boolean {
  return isEstimated;
}

export function blacklistBannerText(station: { id?: string; name?: string } | null): string | null {
  if (!station) return null;
  const id = String(station.id ?? '');
  const name = (station.name ?? '').toLowerCase();
  if (id === '172' || name.includes('wazirabad')) return BLACKLIST_TEXT;
  return null;
}

export function aerodromeWindCopy(speed: number | null, direction: number | null): string {
  if (speed === null || Number.isNaN(speed)) return 'TELEMETRY DROPOUT (NULL)';
  if (speed >= 0 && speed < 0.5) return 'AERODYNAMIC CALM (< 0.50 m/s)';
  const bearing = direction === null || Number.isNaN(direction) ? '\u2014' : `${Math.round(direction)}\u00B0`;
  return `${speed.toFixed(2)} m/s @ ${bearing}`;
}

export function completenessBadge(validHours: number, totalHours: number): { meets: boolean; label: string; pct: number } {
  const required = Math.max(1, Math.round(0.75 * totalHours));
  const meets = validHours >= required;
  const pct = totalHours === 0 ? 0 : Math.round((validHours / totalHours) * 100);
  const status = meets ? '\u226575% VALID' : '<75% INCOMPLETE';
  return { meets, pct, label: `${validHours}/${totalHours}h (${pct}%) \u00B7 ${status}` };
}

export function hazardousAlert(pm25: number | null): HazardousAlert | null {
  if (pm25 === null || !(pm25 > 350)) return null;
  return {
    role: 'alert',
    ariaLive: 'assertive',
    background: '#C00000',
    color: '#FFFFFF',
    text: 'HAZARDOUS \u00B7 500 CEILING CLAMP',
  };
}

export function scrubberReadout(
  hourIndex: number,
  lerpAlpha: number,
  timestamp: string,
  totalHours: number = HORIZON_HOURS
): { timestampLine: string; detailLine: string } {
  const safeTotal = Math.max(1, totalHours);
  const clamped = Math.min(safeTotal - 1, Math.max(0, hourIndex));
  return {
    timestampLine: `${timestamp} PKT`,
    detailLine: `Hour ${clamped + 1}/${safeTotal} \u00B7 Lerp \u03B1=${lerpAlpha.toFixed(2)}`,
  };
}

export function mapLibreConstructorOptions() {
  return {
    pitch: MAP_LOCK.pitch,
    maxPitch: MAP_LOCK.maxPitch,
    bearing: MAP_LOCK.bearing,
    dragRotate: MAP_LOCK.dragRotate,
    touchPitch: MAP_LOCK.touchPitch,
  };
}

/** Baseline centroids are stored [lat, lon]. Cartographic order is [lon, lat]. */
export function centroidLngLat(centroid: [number, number]): [number, number] {
  const [first, second] = centroid;
  if (Math.abs(first) <= 45 && Math.abs(second) > 45) return [second, first];
  return [first, second];
}

export function cpfSectorVisible(sector: { totalHours: number; cpfProbability: number | null }): boolean {
  return sector.totalHours >= 6 && sector.cpfProbability !== null;
}

export function statutorySubIndex(pollutant: PollutantKey, concentration: number | null): number | null {
  if (concentration === null || Number.isNaN(concentration) || concentration < 0) return null;
  if (concentration === 0) return 0;
  const breaks = SUBINDEX_BREAKS[pollutant];
  if (!breaks) return null;
  if (concentration > breaks[breaks.length - 1]) return 500;
  for (let i = 1; i < breaks.length; i += 1) {
    const low = breaks[i - 1];
    const high = breaks[i];
    if (low < concentration && concentration <= high) {
      const iLow = SUBINDEX_TIERS[i - 1];
      const iHigh = SUBINDEX_TIERS[i];
      return Math.round(((iHigh - iLow) / (high - low)) * (concentration - low) + iLow);
    }
  }
  return 500;
}

function median(values: number[]): number {
  if (values.length === 0) return 0;
  const sorted = values.toSorted((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 === 1 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
}

export function qcMarks(values: Array<number | null>, pollutant: PollutantKey, reference: number): QcMark[] {
  const clean = values.map((value) => (value === null || !Number.isFinite(value) || value <= 0 ? null : value));
  return clean.map((value, index) => {
    if (value === null) return { value: null, spike: false, hold: false };
    const window = clean.slice(Math.max(0, index - 3), index + 4).filter((item): item is number => item !== null);
    const mid = median(window);
    const spike = value > 4 * mid && value > 3 * reference;
    const hold =
      pollutant !== 'AQI' &&
      index >= 2 &&
      clean[index - 1] === value &&
      clean[index - 2] === value;
    return { value, spike, hold };
  });
}

export function validHourCount(values: Array<number | null>): { valid: number; total: number } {
  const total = values.length;
  const valid = values.filter((value) => value !== null && Number.isFinite(value) && value > 0).length;
  return { valid, total };
}

export function speedFromUv(u: number, v: number): number {
  return Math.hypot(u, v);
}

export function bearingFromUv(u: number, v: number): number {
  const degrees = (Math.atan2(-u, -v) * 180) / Math.PI;
  return (degrees + 360) % 360;
}

export function entityTypeLabel(selection: SelectionInput | null): string {
  if (!selection) return 'DISTRICT';
  if (selection.kind === 'airport') return 'ICAO AERODROME';
  if (selection.kind === 'station') return selection.stationType === 'mobile' ? 'MOBILE STATION' : 'FIXED STATION';
  return 'DISTRICT';
}

export function placeLabels(items: Array<{ id: string; x: number; y: number; name: string }>): Array<{ id: string; x: number; y: number; name: string; dx: number; dy: number; leader: boolean }> {
  const offsets: Array<[number, number]> = [
    [0, 0],
    [14, -12],
    [-14, -12],
    [16, 8],
    [-16, 8],
    [0, -18],
    [22, -4],
    [-22, -4],
    [10, 16],
    [-10, 16],
    [28, -14],
    [-28, 14],
  ];
  const placed: Array<{ x: number; y: number; w: number; h: number }> = [];
  return items.map((item) => {
    const w = Math.max(36, item.name.length * 6.2);
    const h = 14;
    for (const [dx, dy] of offsets) {
      const box = { x: item.x + dx - w / 2, y: item.y + dy - h / 2, w, h };
      const hit = placed.some((other) => box.x < other.x + other.w && box.x + box.w > other.x && box.y < other.y + other.h && box.y + h > other.y);
      if (!hit) {
        placed.push(box);
        return { ...item, dx, dy, leader: Math.hypot(dx, dy) > 20 };
      }
    }
    return { ...item, dx: 0, dy: 0, leader: false };
  });
}

function formatReading(pollutant: PollutantKey, value: number | null): string {
  if (value === null || Number.isNaN(value)) return '\u2014';
  if (pollutant === 'AQI') return String(Math.round(value));
  return value.toFixed(1);
}

export function buildWorkstationModel(input: WorkstationInput) {
  const counts = countStationNetworks(input.stations);
  const query = input.search.trim().toLowerCase();
  const districts = input.districtRows
    .filter((row) => query.length === 0 || row.name.toLowerCase().includes(query))
    .toSorted((a, b) => (b.value ?? -Infinity) - (a.value ?? -Infinity))
    .map((row, index) => {
      const paint = pepcColorForAqi(row.aqi);
      return {
        ...row,
        rank: index + 1,
        badge: estimatedBadge(row.isEstimated),
        hatch: districtUsesHatch(row.isEstimated),
        formatted: formatReading(input.pollutant, row.value),
        color: paint.hex,
        textColor: paint.text,
      };
    });
  const alert = hazardousAlert(input.maxPm25);
  const completeness = completenessBadge(input.validHours, input.totalHours);
  const timelineHours = input.horizon && input.horizon.length > 0 ? input.horizon.length : HORIZON_HOURS;
  const scrubber = scrubberReadout(input.hourIndex, input.lerpAlpha, input.timestamp, timelineHours);
  const windCopy = aerodromeWindCopy(input.windSpeed, input.windDirection);
  const blacklist = blacklistBannerText(
    input.selected && input.selected.kind === 'station' ? { id: input.selected.id, name: input.selected.name } : null,
  );
  const composite = input.selected
    ? input.districtRows.find((row) => row.id === input.selected?.id)?.aqi ?? input.districtRows.find((row) => row.name === input.selected?.name)?.aqi ?? null
    : null;
  const selectedAqi = input.selected?.kind === 'district'
    ? input.districtRows.find((row) => row.id === input.selected?.id)?.aqi ?? null
    : composite;
  const paint = pepcColorForAqi(selectedAqi);
  const readings = (input.readings ?? POLLUTANT_KEYS.map((key) => ({ key, concentration: null }))).map((reading) => ({
    ...reading,
    unit: STATUTORY_POLLUTANTS[reading.key].unit,
    subIndex: reading.key === 'AQI' ? (reading.concentration === null ? null : Math.round(reading.concentration)) : statutorySubIndex(reading.key, reading.concentration),
    formatted: formatReading(reading.key, reading.concentration),
  }));
  const governing = readings.reduce<{ key: PollutantKey; subIndex: number } | null>((best, reading) => {
    if (reading.key === 'AQI' || reading.subIndex === null) return best;
    if (!best || reading.subIndex > best.subIndex) return { key: reading.key, subIndex: reading.subIndex };
    return best;
  }, null);
  const activeLayerCount = (Object.keys(input.layers) as LayerId[]).filter((id) => input.layers[id]).length;
  return {
    title: WORKSTATION_TITLE,
    subtitle: 'AQMS & Atmospheric Transport Workstation',
    pollutant: input.pollutant,
    pollutants: POLLUTANT_KEYS,
    stream: input.stream,
    streamLabel: streamBadgeCopy(input.stream),
    stationCounter: `${counts.fixed} Fixed \u00B7 ${counts.mobile} Mobile`,
    counts,
    layers: input.layers,
    activeLayerCount,
    dimensionGuard: dimensionGuardCopy(input.pollutant),
    fluxLinks: fluxForPollutant(input.pollutant, input.fluxLinks),
    search: input.search,
    districts,
    hazardous: alert,
    selected: input.selected,
    entityType: entityTypeLabel(input.selected),
    entityName: input.selected?.name ?? 'Punjab province',
    latitude: input.selected?.latitude ?? 31.0,
    longitude: input.selected?.longitude ?? 72.8,
    compositeAqi: selectedAqi,
    compositePaint: paint,
    estimated: input.selected?.kind === 'district'
      ? Boolean(input.districtRows.find((row) => row.id === input.selected?.id)?.isEstimated)
      : false,
    blacklist,
    windCopy,
    completeness,
    readings: readings.map((reading) => ({ ...reading, governing: governing?.key === reading.key })),
    sectors: input.sectors,
    p75Threshold: input.p75Threshold,
    calmHours: input.calmHours,
    pooled: input.pooled,
    pooledStationCount: input.pooledStationCount,
    qcSeries: input.qcSeries ?? [],
    exportMass: input.exportMass,
    importMass: input.importMass,
    domesticShare: input.domesticShare,
    inflowShare: input.inflowShare,
    activeChevrons: input.activeChevrons,
    scrubber,
    playbackSpeed: input.playbackSpeed,
    isPlaying: input.isPlaying,
    hourIndex: input.hourIndex,
    lerpAlpha: input.lerpAlpha,
    horizon: input.horizon ?? [],
    legend: pepcLegend(),
    mapLock: mapLibreConstructorOptions(),
    qaLines: input.qaLines ?? [],
  };
}

export type WorkstationModel = ReturnType<typeof buildWorkstationModel>;
