import baselineUrl from '../../data/baseline/baseline_data.json?url';

export interface BaselineFile {
  meta: { start: string; end: string; nstations?: number; ndistricts?: number };
  hours: string[];
  districts: Record<string, DistrictRaw>;
  stations: StationRaw[];
  airports: AirportRaw[];
  pol: Record<string, PollutantBlock>;
  wind: Array<Record<string, number[]>>;
  tbgeo: { samples: number[][]; border?: number[][] };
}

export interface DistrictRaw {
  id: string | number;
  name: string;
  centroid?: [number, number];
  latitude?: number;
  longitude?: number;
  boundary?: unknown;
  est?: boolean;
  is_estimated?: boolean;
  is_monitored?: boolean;
  stations?: string[];
}

export interface StationRaw {
  id?: string;
  name?: string;
  district?: string;
  latitude?: number;
  longitude?: number;
  mobile?: boolean;
  network_type?: string;
}

export interface AirportRaw {
  id?: string;
  icao?: string;
  name?: string;
  latitude?: number;
  longitude?: number;
  u?: Array<number | null>;
  v?: Array<number | null>;
}

export interface PollutantBlock {
  ref?: number;
  frames?: Array<{ c?: Record<string, number | null>; l?: unknown[] }>;
  cpf?: Record<string, { thr?: number; calm?: number; sectors?: Array<{ n?: number; k?: number; cpf?: number | null }> }>;
  net?: Record<string, number>;
  tb?: Record<string, { valid?: boolean; c_india?: number; c_other?: number }>;
  stations?: Record<string, Array<number | null>>;
}

export async function loadBaseline(): Promise<BaselineFile> {
  const response = await fetch(baselineUrl);
  if (!response.ok) {
    throw new Error(`Baseline fetch failed (${response.status})`);
  }
  return response.json() as Promise<BaselineFile>;
}
