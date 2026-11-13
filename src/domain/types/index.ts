/**
 * EPA Punjab Air Quality Monitoring, Processing, and Visualization System
 * Canonical Shared TypeScript Domain Contracts
 *
 * Implements strict contracts covering:
 * - 9 Statutory Pollutants & Measurements
 * - 7 Official PEPC Health Tiers & Breakpoints
 * - Stations (Fixed, Mobile, Aerodrome METAR, WMO SYNOP; 13 Lahore stations)
 * - Districts (41 districts, Centroid [lon, lat], unified is_estimated flag)
 * - Wind Vector Kinematics (Active, Calm, Dropout, Station 172 Blacklist)
 * - Transboundary Border Nodes (39 nodes, normal flux dot product, crimson/teal chevrons)
 * - Advection Mass Transport Flux (Physical dimension guard: locked to PM2.5 for AQI)
 * - 16-Sector CPF Polar Wind Rose (Small-sample suppression Nk < 6, calm exclusion)
 * - Quality Control & Time Series (7h median spike, 3h logger hold, 75% rule)
 * - Workstation 5-Zone UI & Reactive State Contracts
 */

// ============================================================================
// 1. Coordinates, Spatial & Geodetic Primitives
// ============================================================================

/**
 * Standard WGS-84 coordinate tuple in GeoJSON / deck.gl order: [longitude, latitude].
 * Note: Longitude precedes Latitude in all cartographic operations.
 */
export type LngLat = [longitude: number, latitude: number];

/**
 * Legacy or tabular coordinate tuple: [latitude, longitude].
 */
export type LatLng = [latitude: number, longitude: number];

/**
 * Geographic bounding box.
 */
export interface BoundingBox {
  west: number;
  south: number;
  east: number;
  north: number;
}

// ============================================================================
// 2. Statutory Pollutants & Regulatory Limits
// ============================================================================

/**
 * The 9 statutory air pollutants recognized by the Punjab Environmental Protection Council.
 */
export type PollutantKey =
  | 'AQI'
  | 'PM2.5'
  | 'PM10'
  | 'NO2'
  | 'SO2'
  | 'CO'
  | 'O3'
  | 'NO'
  | 'NOX';

/**
 * Physical chemical pollutants (excluding the dimensionless AQI index).
 * Used to enforce the Physical Dimension Guard in advection flux calculations.
 */
export type PhysicalPollutantKey = Exclude<PollutantKey, 'AQI'>;

export type PollutantUnit = 'ug/m3' | 'mg/m3' | 'index';

export interface PollutantMetadata {
  key: PollutantKey;
  label: string;
  chemicalFormula: string;
  unit: PollutantUnit;
  peqs24hLimit?: number;
  peqs1hLimit?: number;
  peqs8hLimit?: number;
  isDimensionless: boolean;
  stepSize: number;
}

export const STATUTORY_POLLUTANTS: Record<PollutantKey, PollutantMetadata> = {
  AQI: {
    key: 'AQI',
    label: 'Punjab Composite AQI',
    chemicalFormula: 'AQI',
    unit: 'index',
    isDimensionless: true,
    stepSize: 1,
  },
  'PM2.5': {
    key: 'PM2.5',
    label: 'Fine Particulate Matter (<= 2.5 um)',
    chemicalFormula: 'PM2.5',
    unit: 'ug/m3',
    peqs24hLimit: 35.0,
    isDimensionless: false,
    stepSize: 0.1,
  },
  PM10: {
    key: 'PM10',
    label: 'Coarse Particulate Matter (<= 10 um)',
    chemicalFormula: 'PM10',
    unit: 'ug/m3',
    peqs24hLimit: 150.0,
    isDimensionless: false,
    stepSize: 0.1,
  },
  NO2: {
    key: 'NO2',
    label: 'Nitrogen Dioxide',
    chemicalFormula: 'NO2',
    unit: 'ug/m3',
    peqs24hLimit: 80.0,
    isDimensionless: false,
    stepSize: 0.1,
  },
  SO2: {
    key: 'SO2',
    label: 'Sulfur Dioxide',
    chemicalFormula: 'SO2',
    unit: 'ug/m3',
    peqs24hLimit: 120.0,
    isDimensionless: false,
    stepSize: 0.1,
  },
  CO: {
    key: 'CO',
    label: 'Carbon Monoxide',
    chemicalFormula: 'CO',
    unit: 'mg/m3',
    peqs8hLimit: 5.0,
    isDimensionless: false,
    stepSize: 0.01,
  },
  O3: {
    key: 'O3',
    label: 'Ground-Level Ozone',
    chemicalFormula: 'O3',
    unit: 'ug/m3',
    peqs1hLimit: 130.0,
    isDimensionless: false,
    stepSize: 0.1,
  },
  NO: {
    key: 'NO',
    label: 'Nitric Oxide',
    chemicalFormula: 'NO',
    unit: 'ug/m3',
    peqs24hLimit: 40.0,
    isDimensionless: false,
    stepSize: 0.1,
  },
  NOX: {
    key: 'NOX',
    label: 'Total Oxides of Nitrogen',
    chemicalFormula: 'NOx',
    unit: 'ug/m3',
    isDimensionless: false,
    stepSize: 0.1,
  },
};

// ============================================================================
// 3. PEPC Health Tiers & Continuous Piecewise Color Scale
// ============================================================================

export type PEPCGrade =
  | 'good'
  | 'satisfactory'
  | 'moderate'
  | 'unhealthy_sensitive'
  | 'unhealthy'
  | 'very_unhealthy'
  | 'hazardous';

export type PEPCTierIndex = 0 | 1 | 2 | 3 | 4 | 5 | 6;

export interface PEPCBreakpoint {
  tier: PEPCTierIndex;
  grade: PEPCGrade;
  descriptor: string;
  aqiMin: number;
  aqiMax: number;
  hexColor: string;
  rgbColor: [number, number, number];
  textColor: string;
  pm25Max: number;
  pm10Max: number;
}

export interface AQICalculationResult {
  aqi: number;
  tier: PEPCTierIndex;
  grade: PEPCGrade;
  hexColor: string;
  textColor: string;
  isClamped: boolean;
  governingPollutant: 'PM2.5' | 'PM10';
}

// ============================================================================
// 4. Monitoring Stations & Aerodromes
// ============================================================================

export type StationNetworkType = 'fixed' | 'mobile' | 'airport_metar' | 'wmo_synop';

export interface StationQASummary {
  district: string;
  n: number;
  wind_valid: number;
  AQI?: number;
  AQI_spk?: number;
  PM10?: number;
  PM10_spk?: number;
  'PM2.5'?: number;
  'PM2.5_spk'?: number;
  NO2?: number;
  NO2_spk?: number;
  SO2?: number;
  SO2_spk?: number;
  CO?: number;
  CO_spk?: number;
  O3?: number;
  O3_spk?: number;
  NO?: number;
  NO_spk?: number;
  NOX?: number;
  NOX_spk?: number;
  [key: string]: number | string | undefined;
}

/**
 * Raw station record from baseline or backend API.
 */
export interface RawStation {
  id: string;
  station_id?: string;
  numeric_id?: number;
  name: string;
  district: string;
  d?: string;
  latitude: number;
  longitude: number;
  lat?: number;
  lon?: number;
  mobile?: boolean;
  network_type?: string;
  coord_source?: string;
  qa_summary?: StationQASummary;
}

/**
 * Canonical normalized station entity.
 */
export interface NormalizedStation {
  id: string;
  name: string;
  district: string;
  coordinates: LngLat; // [lon, lat]
  latitude: number;
  longitude: number;
  stationType: StationNetworkType;
  mobile: boolean;
  isLahore: boolean;
  hasAnemometer: boolean;
  anemometerBlacklisted: boolean; // Station 172 (Wazirabad)
  altitudeM?: number;
  coordSource?: string;
  qaSummary?: StationQASummary;
}

/**
 * Airport METAR observation node.
 */
export interface AirportStation {
  id: string;
  icao: string;
  name: string;
  coordinates: LngLat;
  latitude: number;
  longitude: number;
}

// ============================================================================
// 5. Administrative Districts
// ============================================================================

/**
 * Raw district record from baseline data.
 * Notice Schema Trap 1: raw centroid is [lat, lon]!
 */
export interface RawDistrict {
  id: string;
  name: string;
  district?: string;
  latitude?: number;
  longitude?: number;
  lat?: number;
  lon?: number;
  centroid: LatLng; // [lat, lon] TRAP!
  label?: LngLat;   // [lon, lat]
  boundary?: number[][][] | number[][][][];
  polys?: number[][][];
  est?: boolean;
  is_monitored?: boolean;
  stations?: string[];
  station_count?: number;
}

/**
 * Canonical normalized district entity.
 */
export interface NormalizedDistrict {
  id: string;
  name: string;
  division?: string;
  centroid: LngLat; // Normalized to [lon, lat]!
  labelCoordinates: LngLat; // [lon, lat]
  boundary: number[][][] | number[][][][]; // GeoJSON Polygon / MultiPolygon
  polys?: number[][][];
  isMonitored: boolean;
  isEstimated: boolean; // Unified from est and !is_monitored
  stationCount: number;
  stations: string[];
  borderDistanceKm: number;
  indiaInflowSectors: number[];
}

// ============================================================================
// 6. Kinematic Wind Vectors & Anemometer States
// ============================================================================

export type WindState = 'active' | 'calm' | 'dropout' | 'blacklisted';

/**
 * Canonical wind vector representation addressing Schema Traps 2 & 3.
 */
export interface WindVector {
  state: WindState;
  speed: number | null;     // Validated speed in m/s [0.0, 30.0], or null
  direction: number | null; // Azimuth in degrees FROM [0.0, 360.0], or null
  u: number | null;         // Cartesian eastward velocity in m/s
  v: number | null;         // Cartesian northward velocity in m/s
  blacklisted: boolean;     // True for Station 172
  blacklistReason?: string; // 'ANEMOMETER BLACKLISTED (VANE OFFSET)'
}

// ============================================================================
// 7. Transboundary Border Nodes & Cross-Border Flux
// ============================================================================

export type BorderFlowState = 'inflow' | 'outflow' | 'neutral';

/**
 * One of the 39 border animation nodes along the Pakistan-India boundary.
 */
export interface BorderNode {
  index: number;
  coordinates: LngLat; // [lon, lat]
  normal: [nx: number, ny: number]; // Inward unit normal vector pointing into Punjab
  phiFlux: number | null; // Normal dot product: Phi = u * nx + v * ny
  flowState: BorderFlowState; // Inflow if Phi > +0.25 m/s, Outflow if Phi < -0.25 m/s
}

export interface TransboundaryMassBalance {
  timestamp: string;
  inflowTotal: number;
  outflowTotal: number;
  netFlux: number; // Inflow - Outflow
  easternInflowRatio: number; // 0.0 to 1.0 (Attribution Split Bar)
  domesticEmissionRatio: number; // 0.0 to 1.0
  borderNodes: BorderNode[];
}

// ============================================================================
// 8. Physical Inter-District Advection Mass Transport Flux
// ============================================================================

export interface PathwayLink {
  sourceDistrict: string;
  receptorDistrict: string;
  distanceKm: number; // <= 180.0 km
  bearingDeg: number;
  divergenceDeg: number; // <= 35.0 deg
  flux: number | null; // Null if calm < 0.50 m/s or divergence > 35 deg
  omega: number; // Receptor CPF feedback coefficient (default 0.25)
  score: number; // flux * omega
  isPM25Locked: boolean; // Physical Dimension Guard flag
}

export interface TransportBalanceSummary {
  districtName: string;
  totalExport: number;
  totalImport: number;
  netTransport: number; // Export - Import (>0 smog source, <0 receptor)
}

// ============================================================================
// 9. Conditional Probability Function (CPF) Polar Wind Rose
// ============================================================================

export interface CPFSector {
  sectorIndex: number; // 0 to 15
  azimuthDeg: number;  // 0.0 to 337.5
  cardinalLabel: string; // 'N', 'NNE', 'NE', etc.
  totalHours: number;  // Nk
  exceedanceHours: number; // mk (hours > P75)
  cpfProbability: number | null; // Null if Nk < 6 (small-sample suppression rule)
  isSuppressed: boolean; // True if Nk < 6
}

export interface CPFRoseData {
  districtName: string;
  pollutant: PollutantKey;
  p75Threshold: number; // P75 concentration threshold
  calmHours: number;    // Count of hours with ws < 0.50 m/s
  totalHours: number;   // Total valid hours
  calmRatio: number;    // calmHours / totalHours
  sectors: CPFSector[]; // Exactly 16 sectors
}

// ============================================================================
// 10. Quality Control & Time Series Inspection
// ============================================================================

export type QCFlag =
  | 'QC_EXCEEDANCE_EXTREME' // PM2.5 > 1000 or PM10 > 1500
  | 'QC_SPIKE_7H_MEDIAN'   // vi > 4 * Mi && vi > 3 * ref_p
  | 'QC_LOGGER_HOLD_3H'    // 3 identical consecutive values for i >= 2 (AQI exempt)
  | 'QC_ZERO_PURGED'       // Raw <= 0 converted to null
  | 'QC_INCOMPLETE_75'     // < 75% temporal completeness
  | 'ANEMOMETER_BLACKLISTED'
  | 'WIND_DROPOUT'
  | 'WIND_CALM';

export interface QCPoint {
  hourIndex: number;
  timestamp: string;
  rawValue: number | null;
  qcValue: number | null;
  isSpike7h: boolean;
  isHold3h: boolean;
  peqsLimit?: number;
}

export interface StationQCSeries {
  stationId: string;
  pollutant: PollutantKey;
  completenessPct: number;
  meets75Rule: boolean;
  points: QCPoint[];
}

// ============================================================================
// 11. Workstation State, Layers & Viewport
// ============================================================================

export type LayerId = 'surface' | 'choropleth' | 'wind' | 'flux' | 'stations';

export type LayerVisibilityState = Record<LayerId, boolean>;

export type SurfaceMode = 'discrete_geodesic' | 'anisotropic_wind_steered';

export type DataSourceMode = 'live_stream' | 'fallback_baseline';

export type PlaybackSpeed = 0.35 | 0.8 | 1.6;

export interface MapViewport {
  longitude: number;
  latitude: number;
  zoom: number;
  pitch: 0; // Strictly locked to 0
  bearing: 0; // Strictly locked to 0
  maxPitch: 0;
}

export type SelectedEntity =
  | { type: 'district'; id: string; name: string }
  | { type: 'station'; id: string; name: string }
  | { type: 'airport'; id: string; icao: string }
  | null;

export interface WorkstationAlert {
  id: string;
  level: 'info' | 'warning' | 'hazardous' | 'clamp_500';
  message: string;
  timestamp: string;
  assertive: boolean;
}

/**
 * Continuous Sub-Hourly Interpolated State snapshot for 60 FPS rendering.
 */
export interface InterpolatedWorkstationState {
  fpos: number;
  hourA: number;
  hourB: number;
  fraction: number;
  timestamp: string;
  districtConcentrations: Record<string, number | null>;
  districtWinds: Record<string, [u: number, v: number]>;
  stationConcentrations: Record<string, number | null>;
  stationWinds: Record<string, [u: number, v: number]>;
  provincialMeanAQI: number;
  provincialPeakAQI: number;
  peakDistrictName: string;
  districtsExceedingPEQS: number;
}
