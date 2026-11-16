import { STATUTORY_POLLUTANTS, type LayerId, type PollutantKey } from '../domain/types';
import type { AirportRaw, BaselineFile, DistrictRaw, PollutantBlock, StationRaw } from './loadBaseline';
import {
  bearingFromUv,
  blacklistBannerText,
  buildWorkstationModel,
  fluxForPollutant,
  qcMarks,
  speedFromUv,
  validHourCount,
  type LayerVisibility,
  type PlaybackRate,
  type SelectionInput,
  type WorkstationModel,
} from './state';
import { chevronFeatures, districtFeatures, fluxFeatures, labelAnchors, stationFeatures, windFeatures, type GeoCollection } from './mapData';

export interface UiState {
  pollutant: PollutantKey;
  layers: LayerVisibility;
  search: string;
  selected: SelectionInput | null;
  hourIndex: number;
  lerpAlpha: number;
  playbackSpeed: PlaybackRate;
  isPlaying: boolean;
  stream: 'live' | 'fallback';
}

export interface MapBundle {
  districts: ReturnType<typeof districtFeatures>;
  stations: ReturnType<typeof stationFeatures>;
  winds: GeoCollection;
  flux: GeoCollection;
  chevrons: GeoCollection;
  labels: ReturnType<typeof labelAnchors>;
}

function frameValue(block: PollutantBlock | undefined, hour: number, name: string): number | null {
  const cell = block?.frames?.[hour]?.c?.[name];
  return typeof cell === 'number' && Number.isFinite(cell) ? cell : null;
}

function districtList(file: BaselineFile): DistrictRaw[] {
  return Object.values(file.districts);
}

function defaultSelection(file: BaselineFile): SelectionInput {
  const lahore = file.districts.Lahore;
  return {
    kind: 'district',
    id: 'Lahore',
    name: 'Lahore',
    latitude: lahore?.latitude ?? 31.549,
    longitude: lahore?.longitude ?? 74.364,
  };
}

function seriesFor(file: BaselineFile, pollutant: PollutantKey, selected: SelectionInput, hourCount: number): Array<number | null> {
  const block = file.pol[pollutant];
  if (selected.kind === 'station' && block?.stations?.[selected.name]) {
    return block.stations[selected.name].slice(0, hourCount);
  }
  if (selected.kind === 'district') {
    return Array.from({ length: hourCount }, (_, hour) => frameValue(block, hour, selected.name));
  }
  return [];
}

function massShares(block: PollutantBlock | undefined): { domesticShare: number; inflowShare: number } {
  let india = 0;
  let other = 0;
  for (const row of Object.values(block?.tb ?? {})) {
    if (!row?.valid) continue;
    india += row.c_india ?? 0;
    other += row.c_other ?? 0;
  }
  const total = india + other;
  if (total <= 0) return { domesticShare: 0, inflowShare: 0 };
  return { domesticShare: other / total, inflowShare: india / total };
}

export function assemble(file: BaselineFile, ui: UiState): { model: WorkstationModel; map: MapBundle } {
  const hour = Math.min(file.hours.length - 1, Math.max(0, ui.hourIndex));
  const districts = districtList(file);
  const selected = ui.selected ?? defaultSelection(file);
  const aqiBlock = file.pol.AQI;
  const activeBlock = file.pol[ui.pollutant];
  const pmBlock = file.pol['PM2.5'];
  const aqiByName: Record<string, number | null> = {};
  const valueByName: Record<string, number | null> = {};
  let maxPm25: number | null = null;
  for (const district of districts) {
    aqiByName[district.name] = frameValue(aqiBlock, hour, district.name);
    valueByName[district.name] = frameValue(activeBlock, hour, district.name);
    const pm = frameValue(pmBlock, hour, district.name);
    if (pm !== null && (maxPm25 === null || pm > maxPm25)) maxPm25 = pm;
  }
  const rows = districts.map((district) => ({
    id: district.name,
    name: district.name,
    value: valueByName[district.name],
    aqi: aqiByName[district.name],
    isEstimated: district.est === true || district.is_estimated === true || district.is_monitored === false,
    latitude: district.latitude ?? 0,
    longitude: district.longitude ?? 0,
  }));
  const windHour = file.wind[hour] ?? {};
  const airport = selected.kind === 'airport' ? file.airports.find((item) => (item.icao ?? item.id) === selected.id) : undefined;
  let windSpeed: number | null = null;
  let windDirection: number | null = null;
  if (selected.kind === 'station' && blacklistBannerText({ id: selected.id, name: selected.name })) {
    windSpeed = null;
    windDirection = null;
  } else if (airport) {
    const u = airport.u?.[hour];
    const v = airport.v?.[hour];
    if (typeof u === 'number' && typeof v === 'number') {
      windSpeed = speedFromUv(u, v);
      windDirection = bearingFromUv(u, v);
    }
  } else {
    const vector = windHour[selected.kind === 'station' ? selected.name : selected.name] ?? windHour[file.stations.find((station) => station.id === selected.id)?.district ?? ''];
    if (vector && vector.length >= 2) {
      windSpeed = speedFromUv(vector[0], vector[1]);
      windDirection = bearingFromUv(vector[0], vector[1]);
    }
  }
  const physicalKey: PollutantKey = ui.pollutant === 'AQI' ? 'PM2.5' : ui.pollutant;
  const physical = file.pol[physicalKey];
  const rawLinks = (physical?.frames?.[hour]?.l ?? []) as unknown[];
  const links = fluxForPollutant(ui.pollutant, rawLinks);
  const cpf = (activeBlock?.cpf ?? physical?.cpf)?.[selected.kind === 'station' ? (file.stations.find((station) => station.id === selected.id)?.district ?? selected.name) : selected.name];
  const sectors = (cpf?.sectors ?? []).map((sector, index) => ({
    sectorIndex: index,
    totalHours: sector.n ?? 0,
    cpfProbability: sector.n !== undefined && sector.n < 6 ? null : sector.cpf ?? null,
    azimuthDeg: index * 22.5,
  }));
  const sectorHours = sectors.reduce((sum, sector) => sum + sector.totalHours, 0);
  const calmRatio = cpf?.calm ?? 0;
  const calmHours = calmRatio > 0 && calmRatio < 1 ? Math.round((sectorHours * calmRatio) / (1 - calmRatio)) : Math.round(calmRatio);
  const lahoreStations = file.stations.filter((station) => station.district === 'Lahore').length;
  const pooled = selected.kind === 'district' && selected.name === 'Lahore';
  const series = seriesFor(file, ui.pollutant, selected, file.hours.length);
  const counts = validHourCount(series);
  const reference = STATUTORY_POLLUTANTS[ui.pollutant].peqs24hLimit ?? STATUTORY_POLLUTANTS[ui.pollutant].peqs1hLimit ?? activeBlock?.ref ?? 1;
  const marks = qcMarks(series, ui.pollutant, reference);
  const readings = (Object.keys(STATUTORY_POLLUTANTS) as PollutantKey[]).map((key) => {
    if (selected.kind === 'station') {
      const stationSeries = file.pol[key]?.stations?.[selected.name];
      const value = stationSeries?.[hour];
      return { key, concentration: typeof value === 'number' ? value : null };
    }
    if (selected.kind === 'district') {
      return { key, concentration: frameValue(file.pol[key], hour, selected.name) };
    }
    return { key, concentration: null };
  });
  const net = physical?.net?.[selected.kind === 'station' ? (file.stations.find((s) => s.id === selected.id)?.district ?? selected.name) : selected.name] ?? 0;
  const shares = massShares(pmBlock);
  const chevrons = chevronFeatures(file.tbgeo?.samples ?? [], districtsAsSources(districts), windHour);
  const horizon = file.hours.map((_, index) => {
    let peak = 0;
    for (const district of districts) {
      const value = frameValue(aqiBlock, index, district.name);
      if (value !== null && value > peak) peak = value;
    }
    return peak;
  });
  const spikeCount = marks.filter((mark) => mark.spike).length;
  const holdCount = marks.filter((mark) => mark.hold).length;
  const qaLines = [
    `Stream ${ui.stream === 'live' ? 'LIVE SSE' : 'BASELINE FALLBACK'}`,
    `Horizon ${file.meta.start} to ${file.meta.end} (${file.hours.length} h)`,
    `Completeness ${counts.valid}/${counts.total} valid hours`,
    `7h median spikes ${spikeCount}`,
    `3h logger holds ${holdCount}`,
    ui.pollutant === 'AQI' ? 'Dimension guard: flux locked to PM2.5 mass' : 'Flux uses the selected physical pollutant',
    blacklistBannerText(selected.kind === 'station' ? selected : null) ?? 'Anemometer blacklist clear',
    `Inflow nodes ${chevrons.count}/39`,
  ];
  const model = buildWorkstationModel({
    stations: file.stations,
    pollutant: ui.pollutant,
    stream: ui.stream,
    hourIndex: hour,
    lerpAlpha: ui.lerpAlpha,
    timestamp: file.hours[hour] ?? file.meta.start,
    search: ui.search,
    layers: ui.layers,
    selected,
    districtRows: rows,
    maxPm25,
    windSpeed,
    windDirection,
    validHours: counts.valid,
    totalHours: counts.total || file.hours.length,
    fluxLinks: links,
    playbackSpeed: ui.playbackSpeed,
    isPlaying: ui.isPlaying,
    domesticShare: shares.domesticShare,
    inflowShare: shares.inflowShare,
    activeChevrons: chevrons.count,
    exportMass: net > 0 ? net : 0,
    importMass: net < 0 ? -net : 0,
    p75Threshold: cpf?.thr ?? 0,
    calmHours,
    pooledStationCount: lahoreStations,
    pooled,
    sectors,
    readings,
    qcSeries: marks,
    horizon,
    qaLines,
  });
  const airportWind = file.airports.map((item) => ({
    ...item,
    u: item.u?.[hour] ?? null,
    v: item.v?.[hour] ?? null,
  }));
  return {
    model,
    map: {
      districts: districtFeatures(districtsAsSources(districts), aqiByName),
      stations: stationFeatures(file.stations, file.airports),
      winds: ui.layers.wind ? windFeatures(districtsAsSources(districts), windHour, airportWind) : { type: 'FeatureCollection', features: [] },
      flux: ui.layers.flux ? fluxFeatures(links, districtsAsSources(districts)) : { type: 'FeatureCollection', features: [] },
      chevrons: ui.layers.flux ? chevrons.collection : { type: 'FeatureCollection', features: [] },
      labels: labelAnchors(districtsAsSources(districts)),
    },
  };
}

function districtsAsSources(districts: DistrictRaw[]) {
  return districts.map((district) => ({
    id: String(district.id),
    name: district.name,
    centroid: district.centroid,
    latitude: district.latitude,
    longitude: district.longitude,
    boundary: district.boundary,
    est: !!(district.est || district.is_estimated),
    is_estimated: !!(district.is_estimated || district.est),
    is_monitored: district.is_monitored,
  }));
}

export function selectionFromStation(station: StationRaw): SelectionInput {
  return {
    kind: 'station',
    id: String(station.id ?? station.name ?? ''),
    name: station.name ?? '',
    stationType: station.mobile ? 'mobile' : 'fixed',
    latitude: station.latitude ?? 0,
    longitude: station.longitude ?? 0,
  };
}

export function selectionFromAirport(airport: AirportRaw): SelectionInput {
  return {
    kind: 'airport',
    id: airport.icao ?? airport.id ?? '',
    name: airport.name ?? airport.icao ?? 'Aerodrome',
    latitude: airport.latitude ?? 0,
    longitude: airport.longitude ?? 0,
  };
}

export const LAYER_IDS: LayerId[] = ['surface', 'choropleth', 'wind', 'flux', 'stations'];
