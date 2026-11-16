/**
 * EPA Punjab Air Quality Monitoring, Processing, and Visualization System
 * Strongly-Typed REST API Client for /api/v1/*
 *
 * Implements full typed client wrapping fetch for:
 * - Meta: /api/v1/meta/districts, /api/v1/meta/stations
 * - Observations: /api/v1/observations/current, /api/v1/observations/hourly, /api/v1/observations/cross-border
 * - Analytics: /api/v1/analytics/cpf, /api/v1/analytics/flux, /api/v1/analytics/transboundary
 * - Ingestion: /api/v1/ingest/csv
 * - Health: /health
 *
 * Physical Invariant Guard:
 * Advection transport mass flux is physically undefined for dimensionless ordinal index 'AQI'.
 * In getAdvectionFlux, when pollutant === 'AQI', client coerces to 'PM2.5' and emits a console warning.
 */

import type { PollutantKey } from '../domain/types';

export interface DistrictMetaResponse {
  id: string;
  name: string;
  division: string;
  latitude: number;
  longitude: number;
  is_monitored: boolean;
  border_distance_km: number;
  india_inflow_sectors: number[];
  stations: string[];
  boundary: any;
}

export interface StationMetaResponse {
  id: string;
  name: string;
  district: string;
  latitude: number;
  longitude: number;
  station_type: string;
  has_anemometer: boolean;
  anemometer_blacklisted: boolean;
  altitude_m?: number;
  network_type: string;
  metadata: Record<string, any>;
}

export interface CurrentDistrictObservation {
  district_id: string;
  concentration: number | null;
  aqi: number | null;
  pepc_tier: string;
  is_estimated: boolean;
  wind_speed: number | null;
  wind_direction: number | null;
}

export interface CurrentStationObservation {
  station_id: string;
  station_name: string;
  concentration: number | null;
  aqi: number | null;
  pepc_tier: string;
  wind_speed: number | null;
  wind_direction: number | null;
  is_blacklisted: boolean;
}

export interface CurrentObservationSnapshot {
  timestamp: string;
  pollutant: string;
  mean_aqi: number;
  exceedance_peqs_count: number;
  reporting_districts_count: number;
  total_districts: number;
  districts: Record<string, CurrentDistrictObservation>;
  stations: Record<string, CurrentStationObservation>;
}

export interface HourlyDistrictSeries {
  id: string;
  name: string;
  concentrations: (number | null)[];
  aqi: (number | null)[];
  wind_u: (number | null)[];
  wind_v: (number | null)[];
}

export interface HourlySeriesResponse {
  pollutant: string;
  timestamps: string[];
  districts: Record<string, HourlyDistrictSeries>;
}

export interface CPFSectorData {
  sector: number;
  angle_deg: number;
  n_k: number;
  m_k: number;
  cpf_ratio: number | null;
  is_suppressed: boolean;
}

export interface CPFRoseResponse {
  district: string;
  pollutant: string;
  threshold: number;
  total_valid_hours: number;
  calm_hours_excluded: number;
  sectors: CPFSectorData[];
}

export interface AdvectionPathway {
  source_district: string;
  receptor_district: string;
  distance_km: number;
  bearing_deg: number;
  flux: number;
  source_concentration: number;
  wind_speed: number;
}

export interface AdvectionFluxResponse {
  pollutant: string;
  timestamp: string;
  top_pathways: AdvectionPathway[];
  net_balance: Record<string, number>;
}

export interface BorderNormalVector {
  node_id: number;
  latitude: number;
  longitude: number;
  normal_u: number;
  normal_v: number;
  wind_u: number;
  wind_v: number;
  dot_product_phi: number;
  is_inflow_crimson: boolean;
}

export interface TransboundaryAttribution {
  domestic_percentage: number;
  cross_border_percentage: number;
  inflow_flux: number;
  outflow_flux: number;
}

export interface TransboundaryResponse {
  timestamp: string;
  pollutant: string;
  provincial_attribution: TransboundaryAttribution;
  border_normals: BorderNormalVector[];
}

export interface QuarantineDetail {
  row_number: number;
  station_id: string | null;
  error_type: string;
  error_message: string;
  raw_record: Record<string, any>;
}

export interface CSVIngestResponse {
  status: 'success' | 'partial_quarantine' | 'failed';
  filename: string;
  total_rows: number;
  valid_rows: number;
  quarantined_rows: number;
  merged_observations_count: number;
  errors: string[];
  quarantined_records?: QuarantineDetail[];
  quarantine_records?: QuarantineDetail[];
}

export interface CrossBorderCity {
  city: string;
  city_name?: string;
  state?: string;
  country?: string;
  distance_km: number;
  latitude?: number;
  longitude?: number;
  aqi?: number;
  us_aqi?: number;
  pepc_aqi: number;
  pm25?: number;
  pm10?: number;
  status: string;
  pepc_tier?: string;
}

export interface CrossBorderHourlyCity {
  city: string;
  state: string;
  distance_km: number;
  latitude: number;
  longitude: number;
  hourly_aqi: number[];
  hourly_pm25: number[];
  hourly_pm10: number[];
  hourly_status: string[];
}

export interface CrossBorderHourlyResponse {
  status: string;
  hours: string[];
  total_hours: number;
  cities: Record<string, CrossBorderHourlyCity>;
}

export class ApiService {
  private baseUrl: string;

  constructor(baseUrl: string = '') {
    this.baseUrl = baseUrl.replace(/\/+$/, '');
  }

  /**
   * Health check endpoint: GET /health
   */
  async getHealth(): Promise<{ status: string; service: string; version: string }> {
    const res = await fetch(`${this.baseUrl}/health`);
    if (!res.ok) throw new Error(`Health check failed: ${res.status}`);
    return res.json();
  }

  /**
   * Districts metadata: GET /api/v1/meta/districts
   */
  async getDistricts(monitoredOnly: boolean = false): Promise<DistrictMetaResponse[]> {
    const params = new URLSearchParams({ monitored_only: monitoredOnly ? 'true' : 'false' });
    const res = await fetch(`${this.baseUrl}/api/v1/meta/districts?${params}`);
    if (!res.ok) throw new Error(`Districts fetch failed: ${res.status}`);
    return res.json();
  }

  async getDistrictsMeta(monitoredOnly: boolean = false): Promise<DistrictMetaResponse[]> {
    return this.getDistricts(monitoredOnly);
  }

  /**
   * Stations metadata: GET /api/v1/meta/stations
   */
  async getStations(district?: string, stationType?: string): Promise<StationMetaResponse[]> {
    const params = new URLSearchParams();
    if (district) params.append('district', district);
    if (stationType) params.append('station_type', stationType);
    const qs = params.toString();
    const res = await fetch(`${this.baseUrl}/api/v1/meta/stations${qs ? `?${qs}` : ''}`);
    if (!res.ok) throw new Error(`Stations fetch failed: ${res.status}`);
    return res.json();
  }

  async getStationsMeta(district?: string, stationType?: string): Promise<StationMetaResponse[]> {
    return this.getStations(district, stationType);
  }

  /**
   * Current observation snapshot: GET /api/v1/observations/current
   */
  async getCurrentObservations(
    pollutant: PollutantKey = 'AQI',
    district?: string
  ): Promise<CurrentObservationSnapshot> {
    const params = new URLSearchParams({ pollutant });
    if (district) params.append('district', district);
    const res = await fetch(`${this.baseUrl}/api/v1/observations/current?${params}`);
    if (!res.ok) throw new Error(`Current observations failed: ${res.status}`);
    return res.json();
  }

  /**
   * Historical hourly observation series: GET /api/v1/observations/hourly
   */
  async getHourlyObservations(
    pollutant: PollutantKey = 'AQI',
    district?: string,
    startTime?: string,
    endTime?: string
  ): Promise<HourlySeriesResponse> {
    const params = new URLSearchParams({ pollutant });
    if (district) params.append('district', district);
    if (startTime) params.append('start_time', startTime);
    if (endTime) params.append('end_time', endTime);
    const res = await fetch(`${this.baseUrl}/api/v1/observations/hourly?${params}`);
    if (!res.ok) throw new Error(`Hourly series fetch failed: ${res.status}`);
    return res.json();
  }

  /**
   * CPF Polar Rose: GET /api/v1/analytics/cpf
   */
  async getCPFRose(
    district: string = 'Lahore',
    pollutant: PollutantKey = 'PM2.5',
    threshold?: number
  ): Promise<CPFRoseResponse> {
    const params = new URLSearchParams({
      district,
      district_name: district,
      pollutant,
    });
    if (threshold !== undefined && threshold !== null) {
      params.append('threshold', String(threshold));
    }
    const res = await fetch(`${this.baseUrl}/api/v1/analytics/cpf?${params}`);
    if (!res.ok) throw new Error(`CPF Rose failed: ${res.status}`);
    return res.json();
  }

  /**
   * Inter-District Advection Mass Transport Flux: GET /api/v1/analytics/flux
   *
   * Physical Invariant Guard:
   * Mass flux is strictly undefined for dimensionless composite AQI.
   * When pollutant === 'AQI', coerce to 'PM2.5' and warn.
   */
  async getAdvectionFlux(
    pollutant: PollutantKey = 'PM2.5',
    limit: number = 60
  ): Promise<AdvectionFluxResponse> {
    let effectivePollutant: string = pollutant;
    if (pollutant === 'AQI' || pollutant.toUpperCase() === 'AQI') {
      console.warn('Advection flux is physically undefined for AQI. Defaulting to PM2.5.');
      effectivePollutant = 'PM2.5';
    }
    const params = new URLSearchParams({ pollutant: effectivePollutant, limit: String(limit) });
    const res = await fetch(`${this.baseUrl}/api/v1/analytics/flux?${params}`);
    if (!res.ok) throw new Error(`Advection flux failed: ${res.status}`);
    return res.json();
  }

  /**
   * Alias for getAdvectionFlux
   */
  async getFluxTransport(
    pollutant: PollutantKey = 'PM2.5',
    limit: number = 60
  ): Promise<AdvectionFluxResponse> {
    return this.getAdvectionFlux(pollutant, limit);
  }

  /**
   * Transboundary analytics: GET /api/v1/analytics/transboundary
   */
  async getTransboundary(pollutant: PollutantKey = 'PM2.5'): Promise<TransboundaryResponse> {
    const params = new URLSearchParams({ pollutant });
    const res = await fetch(`${this.baseUrl}/api/v1/analytics/transboundary?${params}`);
    if (!res.ok) throw new Error(`Transboundary analytics failed: ${res.status}`);
    return res.json();
  }

  /**
   * Cross-border cities telemetry: GET /api/v1/observations/cross-border
   */
  async getCrossBorderCities(hourIndex?: number, timestamp?: string): Promise<CrossBorderCity[]> {
    const params = new URLSearchParams();
    if (hourIndex !== undefined && hourIndex !== null) params.append('hour_index', String(hourIndex));
    if (timestamp) params.append('timestamp', timestamp);
    const qs = params.toString() ? `?${params.toString()}` : '';
    const res = await fetch(`${this.baseUrl}/api/v1/observations/cross-border${qs}`);
    if (!res.ok) throw new Error(`Cross-border cities fetch failed: ${res.status}`);
    const data = await res.json();
    return data.cities || [];
  }

  /**
   * Cross-border historical hourly time-series: GET /api/v1/observations/cross-border/hourly
   */
  async getCrossBorderHourly(): Promise<CrossBorderHourlyResponse> {
    const res = await fetch(`${this.baseUrl}/api/v1/observations/cross-border/hourly`);
    if (!res.ok) throw new Error(`Cross-border hourly fetch failed: ${res.status}`);
    return res.json();
  }

  /**
   * Multipart CSV Ingestion: POST /api/v1/ingest/csv
   */
  async uploadCSV(file: File, allowMissingCoords: boolean = false): Promise<CSVIngestResponse> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('allow_missing_coords', allowMissingCoords ? 'true' : 'false');
    const res = await fetch(`${this.baseUrl}/api/v1/ingest/csv`, {
      method: 'POST',
      body: formData,
    });
    const result: CSVIngestResponse = await res.json();
    return result;
  }

  /**
   * Stream diagnostic tick trigger (test harness): POST /api/v1/stream/tick
   */
  async triggerTick(mode?: string): Promise<Record<string, any>> {
    const params = mode ? `?mode=${encodeURIComponent(mode)}` : '';
    const res = await fetch(`${this.baseUrl}/api/v1/stream/tick${params}`, {
      method: 'POST',
    });
    if (!res.ok) throw new Error(`Trigger tick failed: ${res.status}`);
    return res.json();
  }
}

// Backward-compatibility alias
export { ApiService as ApiClient };
export const apiService = new ApiService();
