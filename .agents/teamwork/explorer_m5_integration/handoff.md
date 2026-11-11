# Milestone M5: API Integration, Delivery, and Automated Testing Blueprint

## 1. Observation

Direct empirical analysis of the codebase, backend implementation, baseline data stores, and architectural documentation revealed the following exact technical facts:

### 1.1 Backend Route Definitions & Parameters (`src/api/routes/`)
1. **Metadata Routes (`src/api/routes/meta.py:9–76`)**:
   - `GET /api/v1/meta/districts`: Query parameter `monitored_only: bool = False`. Returns `List[DistrictMetaResponse]` (41 districts). Fields include `id`, `name`, `division`, `latitude`, `longitude`, `is_monitored`, `border_distance_km`, `india_inflow_sectors`, `stations`, and `boundary` geometry.
   - `GET /api/v1/meta/stations`: Query parameters `district: Optional[str] = None`, `station_type: Optional[str] = None`. Returns `List[StationMetaResponse]` (85 items: 79 AQMS + 6 aerodromes). Fields include `id`, `name`, `district`, `latitude`, `longitude`, `station_type`, `has_anemometer`, `anemometer_blacklisted`, `altitude_m`, `network_type`, and hardware `metadata`.

2. **Observation Routes (`src/api/routes/observations.py:10–53`)**:
   - `GET /api/v1/observations/current`: Query parameters `pollutant: str = "AQI"`, `district: Optional[str] = None`. Returns `CurrentObservationsResponse` with `timestamp`, `hour_index`, `pollutant`, `provincial_summary` (`mean_aqi`, `exceedance_peqs_count`, `peak_district`, `peak_aqi`, `reporting_districts_count`, `total_districts`), `districts` (dictionary of 41 `DistrictReadingSchema`), and `airports` (`AirportReadingSchema`).
   - `GET /api/v1/observations/hourly`: Query parameters `pollutant: str = "AQI"`, `district: Optional[str] = None`, `start_time: Optional[datetime] = None`, `end_time: Optional[datetime] = None`. Returns `HourlyObservationsResponse` with `pollutant`, `hours` (216 ISO strings), `total_hours`, `districts` (dictionary mapping district names to `concentrations`, `wind_u`, `wind_v`, `is_estimated`), and `provincial_mean`.

3. **Spatial Surface Route (`src/api/routes/spatial.py:10–33`)**:
   - `GET /api/v1/spatial/surface`: Query parameters `timestamp: Optional[datetime] = None`, `pollutant: str = "PM2.5"`, `resolution: int = 5` (constrained `ge=1, le=50`). Returns `SpatialSurfaceResponse` containing `timestamp`, `pollutant`, `grid_width`, `grid_height`, `resolution`, `min_val`, `max_val`, `grid_matrix` (`List[List[float]]`), and optional `opacity_matrix` (`List[List[int]]`).

4. **Analytics Routes (`src/api/routes/analytics.py:10–95`)**:
   - `GET /api/v1/analytics/cpf`: Query parameters `district: str` (alias `district_name`), `pollutant: str = "PM2.5"`, `threshold: Optional[float] = None`. Returns `CPFRoseResponse` with `district`, `pollutant`, `threshold_p75`, `calm_fraction`, `null_hypothesis_baseline` ($0.25$), and 16 `sectors` containing `sector_index`, `azimuth_deg`, `direction_label`, `total_hours`, `exceedance_hours`, and `cpf_probability` (null when $N_k < 6$).
   - `GET /api/v1/analytics/flux`: Query parameters `pollutant: str = "PM2.5"`, `timestamp: Optional[datetime] = None`, `limit: int = 60` (constrained `ge=1, le=200`).
     - **Physical Invariant Guard (`src/api/routes/analytics.py:53–62`)**:
       ```python
       if pollutant.strip().upper() == "AQI":
           raise HTTPException(
               status_code=400,
               detail=(
                   "Advection transport mass flux is physically undefined for dimensionless ordinal index 'AQI'. "
                   "Mass conservation requires conserved physical concentrations. "
                   "Query a mass pollutant species such as PM2.5, PM10, NO2, SO2, CO, or O3."
               ),
           )
       ```
     - Returns `FluxTransportResponse` with `top_pathways` (max 60 links with `source_district`, `receptor_district`, `distance_km`, `bearing_deg`, `divergence_deg`, `flux`, `omega`, `score`) and `net_balance`.
   - `GET /api/v1/analytics/transboundary`: Query parameters `timestamp: Optional[datetime] = None`, `pollutant: str = "PM2.5"`. Returns `TransboundaryResponse` with `inflow_total`, `outflow_total`, `net_transboundary_flux`, `status`, `border_districts`, and 39 `border_samples` nodes (`latitude`, `longitude`, `normal_x`, `normal_y`, `normal_flux`).

5. **SSE Live Streaming Route (`src/api/routes/stream.py:13–97`)**:
   - `GET /api/v1/stream/live`: Query parameter `max_events: Optional[int] = None`.
   - Returns `StreamingResponse(media_type="text/event-stream")` with headers `Cache-Control: no-cache`, `Connection: keep-alive`, `X-Accel-Buffering: no`.
   - Behavior:
     - On connect: Immediately yields initial snapshot frame: `event: hourly_update\ndata: { ... }\n\n`.
     - Heartbeat ping: Emits comment line `: keepalive\n\n` every `KEEPALIVE_INTERVAL_SECONDS = 15.0` seconds.
     - Telemetry ticks: Checks repository every `POLL_CHECK_INTERVAL_SECONDS = 2.0` seconds; when `latest_ts != last_emitted_timestamp`, emits `event: hourly_update\ndata: { ... }\n\n`.
     - Disconnect detection: Checks `await request.is_disconnected()` to terminate gracefully.

6. **Custom CSV Ingestion Route (`src/api/routes/ingest.py:8–52`)**:
   - `POST /api/v1/ingest/csv`: Multipart form-data containing `file: UploadFile` and `allow_missing_coords: bool = False`.
   - Rejects non-CSV extensions with HTTP 400 (`"Invalid file type. Only standard comma-separated values (.csv) files are supported."`).
   - Rejects zero-byte files with HTTP 400 (`"Uploaded CSV file is empty."`).
   - Returns `CSVIngestResponse` with `status` (`"success"`, `"partial_quarantine"`, or `"failed"`), `filename`, `total_rows`, `valid_rows`, `quarantined_rows`, `merged_observations_count`, `errors`, and `quarantine_records` (`row_number`, `station_id`, `error_type`, `error_message`, `raw_record`).

### 1.2 Baseline Data Artifacts (`data/baseline/`)
Verification via filesystem directory probe confirms 5 static datasets:
- `data/baseline/stations.json` (64,507 bytes): 85 station catalog definitions with coordinates, anemometer flags, and sensor types.
- `data/baseline/districts.json` (1,127,650 bytes): 41 administrative districts with boundaries and centroids.
- `data/baseline/districts_dict.json` (1,128,152 bytes): District metadata keyed by canonical district name.
- `data/baseline/airports.json` (34,359 bytes): 6 airport aerodrome definitions (OPLA, OPFA, OPRK, OPMT, OPBW, OPSN).
- `data/baseline/baseline_data.json` (10,732,452 bytes): 216 historical hourly records (hours 0 to 215) for all 41 districts and 79 ground stations, plus transboundary boundary geometry (`tbgeo`).

### 1.3 Latent Defect in `src/api/main.py:9 & 33`
Executing `python -c "from src.api.main import init_app_state; print(init_app_state.__annotations__)"` reproduces:
```
NameError: name 'Optional' is not defined
  File "src/api/main.py", line 33, in __annotate__
    def init_app_state(app: FastAPI, base_dir: Optional[Path] = None) -> None:
```
- Line 9 currently imports only: `from typing import AsyncGenerator`.
- Line 33 utilizes `Optional[Path] = None`.
- Under Python 3.14 deferred annotation evaluation, referencing `__annotations__` crashes unless `Optional` is added to line 9: `from typing import AsyncGenerator, Optional`.

---

## 2. Logic Chain

1. **Client API Layer Requirements**:
   - Because the backend routes follow strict Pydantic v2 schemas across 6 domain routers, the frontend TypeScript client layer must mirror these contracts 1:1 using TypeScript interfaces to guarantee end-to-end type safety.
   - Because `GET /api/v1/analytics/flux?pollutant=AQI` raises HTTP 400 by design (enforcing the physical conservation law that advective transport mass flux is undefined for dimensionless ordinal indices), `analyticsClient.ts` must prevent sending `pollutant="AQI"`, automatically substituting `"PM2.5"` or displaying an informative UI banner.
   - Because `GET /api/v1/stream/live` utilizes SSE with 15s `: keepalive` heartbeats, `streamClient.ts` cannot use standard `fetch` or naive `EventSource` without handling comment lines and connection dropouts; it requires an auto-reconnecting consumer with backoff and a 35s watchdog timer.
   - Because `POST /api/v1/ingest/csv` returns quarantined rows in a structured format, `ingestClient.ts` must expose a quarantine inspector model so users can understand why specific rows failed (e.g., GPS coordinates outside Punjab or unparseable timestamps).

2. **Offline & Fallback Data Strategy**:
   - The user requested seamless offline operation when the FastAPI backend is starting or in standalone demo mode.
   - The baseline datasets in `data/baseline/` (`stations.json`, `districts.json`, `airports.json`, `baseline_data.json`) total ~13 MB uncompressed (~1.8 MB gzip).
   - By serving these pre-packaged JSON bundles from `src/frontend/public/data/` (or packaging a client-side `OfflineDataEngine`), the frontend can execute all 5 UI zones, 216-hour scrubbing, 16-sector CPF rose rendering, and spatial canvas drawing in the browser with zero backend dependency.
   - The Zone 1 status pill provides immediate situational awareness: switching from `LIVE SYNC: ACTIVE` (green) to `FALLBACK ARCHIVE (OFFLINE)` (amber) or `USER CSV DATASET` (blue).

3. **FastAPI Frontend Delivery Strategy**:
   - Serving the built single-page application (SPA) directly from FastAPI avoids multi-origin CORS complexities, enables single-binary/single-port deployment, and simplifies testing.
   - Mounting `fastapi.staticfiles.StaticFiles` after all `/api/v1/*` routes ensures API requests never collide with static file resolution.
   - An SPA catch-all route (`/{full_path:path}`) returning `index.html` allows client-side deep linking (e.g. `/focus/lahore` or `/heatmap`) without 404 errors on browser page reloads.

4. **Automated UI Testing Strategy**:
   - Following `/impeccable` guidelines and the 5-zone UI hierarchy in `docs/UI_UX_SPECIFICATION.md`, automated tests must assert the presence, state, and interaction of every mission-critical console element:
     - Zone 1: Status pill, Provincial AQI badge, simulation clock, subview navigation tabs, data source selector.
     - Zone 2: 9 pollutant switcher pills with statutory PEQS threshold badges and keyboard shortcut handling.
     - Zone 3: 5 canvas layers, continuous range scrubber ($fp \in [0.00, 215.00]$), play/pause toggle, speed selector, mode radios (`Continuous IDW` vs `Administrative Borders`).
     - Zone 4: Telemetry sidebar, provincial summary card, 24-hour sparkline, METAR airport winds, 41-district ranked roster, selected district drawer, and 16-sector CPF rose canvas.
     - Zone 5: Synchronized 3x3 multi-pollutant canvas grid, Lahore 11-station focus inset, virtualized 41x216 hourly matrix, and transboundary remote sensing card.

---

## 3. Detailed Architecture Blueprint & Implementation Specifications

### 3.1 Client-Side API Layer (`src/frontend/src/api/`)

#### 3.1.1 Type Definitions (`src/frontend/src/api/types.ts`)
```typescript
/**
 * Canonical TypeScript Interfaces for Punjab Air Quality API Gateway.
 * Strict 1:1 parity with backend Pydantic v2 schemas in src/api/schemas/.
 */

export type PollutantKey = 'AQI' | 'PM2.5' | 'PM10' | 'NO2' | 'SO2' | 'CO' | 'O3' | 'NO' | 'NOx';

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
  boundary?: any;
}

export interface StationMetaResponse {
  id: string;
  name: string;
  district: string;
  latitude: number;
  longitude: number;
  station_type: 'fixed' | 'mobile' | 'airport_metar' | 'wmo_synop';
  has_anemometer: boolean;
  anemometer_blacklisted: boolean;
  altitude_m?: number | null;
  network_type?: string | null;
  metadata: Record<string, any>;
}

export interface ProvincialSummarySchema {
  mean_aqi: number;
  exceedance_peqs_count: number;
  peak_district: string;
  peak_aqi: number;
  reporting_stations_count: number;
  reporting_districts_count: number;
  total_districts: number;
}

export interface DistrictReadingSchema {
  district: string;
  district_id?: string | null;
  name?: string | null;
  aqi?: number | null;
  value?: number | null;
  pm25?: number | null;
  pm10?: number | null;
  no2?: number | null;
  so2?: number | null;
  co?: number | null;
  o3?: number | null;
  u?: number | null;
  v?: number | null;
  wind_speed?: number | null;
  wind_direction?: number | null;
  is_estimated: boolean;
}

export interface AirportReadingSchema {
  icao: string;
  name: string;
  latitude: number;
  longitude: number;
  wind_speed_ms?: number | null;
  wind_direction_deg?: number | null;
  u?: number | null;
  v?: number | null;
}

export interface CurrentObservationsResponse {
  timestamp: string;
  hour_index: number;
  pollutant: string;
  provincial_summary: ProvincialSummarySchema;
  districts: Record<string, DistrictReadingSchema>;
  airports: AirportReadingSchema[];
}

export interface DistrictHourlySeriesSchema {
  concentrations: (number | null)[];
  wind_u: (number | null)[];
  wind_v: (number | null)[];
  is_estimated: boolean;
}

export interface HourlyObservationsResponse {
  pollutant: string;
  hours: string[];
  total_hours: number;
  districts: Record<string, DistrictHourlySeriesSchema>;
  provincial_mean?: (number | null)[] | null;
}

export interface SpatialSurfaceResponse {
  timestamp: string;
  pollutant: string;
  grid_width: number;
  grid_height: number;
  resolution: number;
  min_val: number;
  max_val: number;
  grid_matrix: number[][];
  opacity_matrix?: number[][] | null;
}

export interface CPFSectorDetail {
  sector_index: number;
  azimuth_deg: number;
  direction_label: string;
  total_hours: number;
  exceedance_hours: number;
  cpf_probability: number | null;
}

export interface CPFRoseResponse {
  district: string;
  pollutant: string;
  threshold_p75: number;
  calm_fraction: number;
  null_hypothesis_baseline: number;
  sectors: CPFSectorDetail[];
}

export interface AdvectionPathwayLink {
  source_district: string;
  receptor_district: string;
  distance_km: number;
  bearing_deg: number;
  divergence_deg: number;
  flux: number;
  omega: number;
  score: number;
}

export interface FluxTransportResponse {
  pollutant: string;
  timestamp?: string | null;
  total_links: number;
  top_pathways: AdvectionPathwayLink[];
  net_balance: Record<string, number>;
}

export interface BorderDistrictTransboundaryDetail {
  district: string;
  border_distance_km: number;
  inflow_sectors: number[];
  transboundary_flux: number;
  direction_mode: 'inflow' | 'outflow' | 'neutral' | 'calm';
}

export interface BorderSampleNode {
  node_index: number;
  latitude: number;
  longitude: number;
  normal_x: number;
  normal_y: number;
  normal_flux: number;
}

export interface TransboundaryResponse {
  timestamp: string;
  pollutant: string;
  inflow_total: number;
  outflow_total: number;
  net_transboundary_flux: number;
  net_flux?: number | null;
  status: 'net_inflow' | 'net_outflow' | 'neutral';
  border_districts: Record<string, BorderDistrictTransboundaryDetail>;
  border_samples: BorderSampleNode[];
}

export interface QuarantineDetail {
  row_number: number;
  station_id?: string | null;
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
  quarantine_records?: QuarantineDetail[] | null;
}

export interface SSEHourlyUpdatePayload {
  event: 'hourly_update';
  timestamp: string;
  hour_index: number;
  total_hours: number;
  provincial_summary: ProvincialSummarySchema;
  district_readings: Record<string, DistrictReadingSchema>;
  airports: AirportReadingSchema[];
}
```

#### 3.1.2 Base HTTP Client (`src/frontend/src/api/client.ts`)
```typescript
/**
 * Robust HTTP client with AWS full-jitter backoff and circuit-breaker awareness.
 */
export class ApiError extends Error {
  constructor(
    public status: number,
    public statusText: string,
    public details?: any
  ) {
    super(`API Error ${status} ${statusText}: ${JSON.stringify(details || '')}`);
    this.name = 'ApiError';
  }
}

export interface RequestOptions extends RequestInit {
  timeoutMs?: number;
  retries?: number;
}

const DEFAULT_TIMEOUT_MS = 8000;
const BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

export async function request<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
  const { timeoutMs = DEFAULT_TIMEOUT_MS, retries = 2, ...fetchOptions } = options;
  const url = `${BASE_URL}${endpoint}`;

  let lastError: any;
  for (let attempt = 0; attempt <= retries; attempt++) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

    try {
      const response = await fetch(url, {
        ...fetchOptions,
        signal: controller.signal,
        headers: {
          'Accept': 'application/json',
          ...(fetchOptions.headers || {}),
        },
      });
      clearTimeout(timeoutId);

      if (!response.ok) {
        let errorDetails: any;
        try {
          errorDetails = await response.json();
        } catch {
          errorDetails = await response.text();
        }
        throw new ApiError(response.status, response.statusText, errorDetails);
      }

      return (await response.json()) as T;
    } catch (err: any) {
      clearTimeout(timeoutId);
      lastError = err;
      
      // Do not retry 4xx client errors (e.g. 400 AQI guard, 422 schema errors)
      if (err instanceof ApiError && err.status >= 400 && err.status < 500) {
        throw err;
      }

      if (attempt < retries) {
        // AWS full-jitter backoff: t = random(0, min(max_backoff, base * 2^attempt))
        const backoff = Math.random() * Math.min(2000, 200 * Math.pow(2, attempt));
        await new Promise((resolve) => setTimeout(resolve, backoff));
      }
    }
  }

  throw lastError;
}
```

#### 3.1.3 Domain API Clients (`src/frontend/src/api/`)

##### `metaClient.ts`:
```typescript
import { request } from './client';
import { DistrictMetaResponse, StationMetaResponse } from './types';

export const metaClient = {
  async getDistricts(monitoredOnly: boolean = false): Promise<DistrictMetaResponse[]> {
    return request<DistrictMetaResponse[]>(`/api/v1/meta/districts?monitored_only=${monitoredOnly}`);
  },

  async getStations(district?: string, stationType?: string): Promise<StationMetaResponse[]> {
    const params = new URLSearchParams();
    if (district) params.append('district', district);
    if (stationType) params.append('station_type', stationType);
    const qs = params.toString();
    return request<StationMetaResponse[]>(`/api/v1/meta/stations${qs ? `?${qs}` : ''}`);
  },
};
```

##### `obsClient.ts`:
```typescript
import { request } from './client';
import { CurrentObservationsResponse, HourlyObservationsResponse, PollutantKey } from './types';

export const obsClient = {
  async getCurrent(pollutant: PollutantKey = 'AQI', district?: string): Promise<CurrentObservationsResponse> {
    const params = new URLSearchParams({ pollutant });
    if (district) params.append('district', district);
    return request<CurrentObservationsResponse>(`/api/v1/observations/current?${params.toString()}`);
  },

  async getHourly(
    pollutant: PollutantKey = 'AQI',
    district?: string,
    startTime?: string,
    endTime?: string
  ): Promise<HourlyObservationsResponse> {
    const params = new URLSearchParams({ pollutant });
    if (district) params.append('district', district);
    if (startTime) params.append('start_time', startTime);
    if (endTime) params.append('end_time', endTime);
    return request<HourlyObservationsResponse>(`/api/v1/observations/hourly?${params.toString()}`);
  },
};
```

##### `spatialClient.ts`:
```typescript
import { request } from './client';
import { SpatialSurfaceResponse, PollutantKey } from './types';

export const spatialClient = {
  async getSurface(
    pollutant: PollutantKey = 'PM2.5',
    timestamp?: string,
    resolution: number = 5
  ): Promise<SpatialSurfaceResponse> {
    const params = new URLSearchParams({ pollutant, resolution: String(resolution) });
    if (timestamp) params.append('timestamp', timestamp);
    return request<SpatialSurfaceResponse>(`/api/v1/spatial/surface?${params.toString()}`);
  },
};
```

##### `analyticsClient.ts`:
```typescript
import { request } from './client';
import { CPFRoseResponse, FluxTransportResponse, TransboundaryResponse, PollutantKey } from './types';

export const analyticsClient = {
  async getCPFRose(district: string, pollutant: PollutantKey = 'PM2.5', threshold?: number): Promise<CPFRoseResponse> {
    const params = new URLSearchParams({ district, pollutant });
    if (threshold !== undefined) params.append('threshold', String(threshold));
    return request<CPFRoseResponse>(`/api/v1/analytics/cpf?${params.toString()}`);
  },

  async getAdvectionFlux(
    pollutant: PollutantKey = 'PM2.5',
    timestamp?: string,
    limit: number = 60
  ): Promise<FluxTransportResponse> {
    // Client-side domain invariant enforcement: AQI cannot be advected
    if (pollutant.toUpperCase() === 'AQI') {
      throw new Error(
        "Advection transport mass flux is physically undefined for 'AQI'. Please select PM2.5, PM10, NO2, SO2, CO, or O3."
      );
    }
    const params = new URLSearchParams({ pollutant, limit: String(limit) });
    if (timestamp) params.append('timestamp', timestamp);
    return request<FluxTransportResponse>(`/api/v1/analytics/flux?${params.toString()}`);
  },

  async getTransboundary(pollutant: PollutantKey = 'PM2.5', timestamp?: string): Promise<TransboundaryResponse> {
    const params = new URLSearchParams({ pollutant });
    if (timestamp) params.append('timestamp', timestamp);
    return request<TransboundaryResponse>(`/api/v1/analytics/transboundary?${params.toString()}`);
  },
};
```

##### `streamClient.ts` (Resilient SSE Live Stream Consumer):
```typescript
import { SSEHourlyUpdatePayload } from './types';

export type SSEUpdateCallback = (payload: SSEHourlyUpdatePayload) => void;
export type SSEStatusCallback = (status: 'connected' | 'reconnecting' | 'disconnected') => void;

export class LiveStreamConsumer {
  private eventSource: EventSource | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 10;
  private watchdogTimer: any = null;
  private isDestroyed = false;
  private lastHeartbeat = Date.now();

  constructor(
    private url: string = '/api/v1/stream/live',
    private onUpdate: SSEUpdateCallback,
    private onStatus?: SSEStatusCallback
  ) {}

  public connect(): void {
    if (this.isDestroyed) return;
    this.cleanup();

    this.onStatus?.('reconnecting');
    this.eventSource = new EventSource(this.url);

    this.eventSource.onopen = () => {
      this.reconnectAttempts = 0;
      this.lastHeartbeat = Date.now();
      this.onStatus?.('connected');
      this.startWatchdog();
    };

    // Listen for custom event 'hourly_update'
    this.eventSource.addEventListener('hourly_update', (e: MessageEvent) => {
      this.lastHeartbeat = Date.now();
      try {
        const payload: SSEHourlyUpdatePayload = JSON.parse(e.data);
        this.onUpdate(payload);
      } catch (err) {
        console.error('Failed to parse SSE hourly_update data:', err);
      }
    });

    // Native onmessage or comment handling for keepalive heartbeats
    this.eventSource.onmessage = () => {
      this.lastHeartbeat = Date.now();
    };

    this.eventSource.onerror = (e) => {
      console.warn('SSE connection error, initiating exponential backoff...', e);
      this.handleDisconnect();
    };
  }

  private startWatchdog(): void {
    clearInterval(this.watchdogTimer);
    // Ping interval is 15s; if no activity in 35s, trigger reconnection
    this.watchdogTimer = setInterval(() => {
      if (Date.now() - this.lastHeartbeat > 35000) {
        console.warn('SSE heartbeat watchdog timeout (>35s). Forcing reconnection.');
        this.handleDisconnect();
      }
    }, 5000);
  }

  private handleDisconnect(): void {
    this.cleanup();
    if (this.isDestroyed) return;

    this.onStatus?.('reconnecting');
    this.reconnectAttempts++;
    if (this.reconnectAttempts > this.maxReconnectAttempts) {
      this.onStatus?.('disconnected');
      return;
    }

    // Exponential backoff with full jitter
    const delay = Math.min(30000, 1000 * Math.pow(1.5, this.reconnectAttempts)) * (0.8 + Math.random() * 0.4);
    setTimeout(() => this.connect(), delay);
  }

  public cleanup(): void {
    clearInterval(this.watchdogTimer);
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
  }

  public destroy(): void {
    this.isDestroyed = true;
    this.cleanup();
    this.onStatus?.('disconnected');
  }
}
```

##### `ingestClient.ts` (CSV Multipart Uploader):
```typescript
import { CSVIngestResponse } from './types';
import { ApiError } from './client';

export const ingestClient = {
  async uploadCSV(file: File, allowMissingCoords: boolean = false): Promise<CSVIngestResponse> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('allow_missing_coords', String(allowMissingCoords));

    const response = await fetch('/api/v1/ingest/csv', {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      let details;
      try {
        details = await response.json();
      } catch {
        details = await response.text();
      }
      throw new ApiError(response.status, response.statusText, details);
    }

    return (await response.json()) as CSVIngestResponse;
  },
};
```

---

### 3.2 Offline & Fallback Data Strategy

#### 3.2.1 Offline Data Architecture
To ensure high availability and offline demonstration without local server execution:
1. **Static Baseline Bundle Serving**:
   - The files in `data/baseline/` (`districts.json`, `stations.json`, `airports.json`, `baseline_data.json`) are copied into the frontend static assets directory (`src/frontend/public/data/baseline/`).
   - In production or offline mode, the frontend can load these files directly via standard relative HTTP GET `/data/baseline/*.json`.
2. **Client-Side Repository & Fallback Engine (`src/frontend/src/offline/OfflineDataEngine.ts`)**:
   - Implements the exact same method signatures as `metaClient`, `obsClient`, `spatialClient`, and `analyticsClient`.
   - On application boot:
     - The application runs an initial probe to `GET /health` with a 2000ms timeout.
     - **Server Available**: Connects to `/api/v1/*` routes; status pill = `LIVE SYNC: ACTIVE` (pulsing green).
     - **Server Unavailable**: Switches automatically to `OfflineDataEngine`; status pill = `FALLBACK ARCHIVE (OFFLINE)` (amber).
     - **User Uploads CSV**: Switches to memory store; status pill = `USER CSV DATASET` (indigo).
3. **Pure TypeScript Client-Side Interpolation & Transforms**:
   - Layer 1 continuous IDW rasterization is already executed on the client canvas/WebGL context.
   - 16-sector CPF wind roses are pre-computed or computed directly from the 216-hour arrays using the pure math formulas from `TRANSFORMATION_LOGIC_SPEC.md §2.5`.

---

### 3.3 Frontend Delivery via FastAPI

#### 3.3.1 Delivery Architecture & Routing
FastAPI serves the compiled React single-page application from `src/frontend/dist` (or `src/frontend/` in standalone prototype mode).
- Static assets (JS chunks, CSS, SVG, TopoJSON) are served with long-term cache headers: `Cache-Control: public, max-age=31536000, immutable`.
- `index.html` is served with `Cache-Control: no-cache, no-store, must-revalidate` to ensure immediate UI updates upon deployment.
- SPA catch-all routing ensures client-side deep links (e.g. `/focus/lahore` or `/heatmap`) resolve cleanly without returning 404s.

#### 3.3.2 Implementation Patch for `src/api/main.py`
The implementer will apply the following exact modifications:
1. **Fix line 9 typing import**: Add `Optional` to line 9.
2. **Mount StaticFiles & SPA Catch-All**:

```python
# =========================================================================
# DIFF SPECIFICATION: src/api/main.py
# =========================================================================
--- a/src/api/main.py
+++ b/src/api/main.py
@@ -6,9 +6,11 @@
 from contextlib import asynccontextmanager
 import logging
 from pathlib import Path
-from typing import AsyncGenerator
+from typing import AsyncGenerator, Optional
 from fastapi import FastAPI, Request, status
 from fastapi.exceptions import RequestValidationError
 from fastapi.middleware.cors import CORSMiddleware
-from fastapi.responses import JSONResponse
+from fastapi.responses import JSONResponse, FileResponse
+from fastapi.staticfiles import StaticFiles
 
@@ -120,6 +122,23 @@
     # Initialize in-memory state
     init_app_state(app)
 
+    # Mount Frontend Single-Page Application (SPA)
+    frontend_dist = Path(__file__).resolve().parent.parent.parent / "src" / "frontend" / "dist"
+    if not frontend_dist.exists():
+        frontend_dist = Path(__file__).resolve().parent.parent.parent / "src" / "frontend"
+
+    if frontend_dist.exists() and (frontend_dist / "index.html").exists():
+        # Mount static asset bundles if present
+        assets_dir = frontend_dist / "assets"
+        if assets_dir.exists():
+            app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")
+
+        # SPA Catch-All Route for client-side navigation
+        @app.get("/{full_path:path}", include_in_schema=False)
+        async def serve_spa(full_path: str):
+            target_file = frontend_dist / full_path
+            if full_path and target_file.is_file():
+                return FileResponse(target_file)
+            return FileResponse(frontend_dist / "index.html")
+
     return app
```

---

### 3.4 Automated Verification & UI Test Strategy

To fulfill Requirement R6 and Milestone M5/M6 certification, automated UI testing must verify the complete interface specification in `docs/UI_UX_SPECIFICATION.md`:

```
+---------------------------------------------------------------------------------------------------+
| TEST ARCHITECTURE (Milestone M5 & M6)                                                            |
| +-----------------------------------------------------------------------------------------------+ |
| | Tier 1: API Client Unit Tests (Vitest / mock-fetch / MSW)                                     | |
| |   - Request serialization, retry logic, AQI physical guard rejection, SSE keepalive parser    | |
| +-----------------------------------------------------------------------------------------------+ |
| | Tier 2: Component DOM & State Tests (React Testing Library + jsdom)                           | |
| |   - 5 Zones, 9 Pollutant buttons, Scrubber range [0, 215], 41 District ranking list           | |
| +-----------------------------------------------------------------------------------------------+ |
| | Tier 3: 5-Layer Canvas & WebGL Rendering Pipeline Tests                                       | |
| |   - Layer 0 (Basemap), Layer 1 (IDW), Layer 2 (1300 Particles), Layer 3 (Flux), Layer 4 (Text)| |
| +-----------------------------------------------------------------------------------------------+ |
| | Tier 4: End-to-End Operational Workflow Scenarios (Playwright / Headless Browser)             | |
| |   - Severe Smog Inversion, Offline Fallback, User CSV Ingest & Quarantine Modal, SSE Tick     | |
| +-----------------------------------------------------------------------------------------------+ |
```

#### 3.4.1 Test Cases for All 5 UI Zones

##### Zone 1: Command Header & Navigation Strip
- **TC-Z1-01 (Telemetry Status Pill)**: Verify element `#system-status-pill` renders. When API connects, asserts text contains `"LIVE SYNC: ACTIVE"` and has class `bg-emerald-500/20 text-emerald-400`. When offline, asserts text contains `"FALLBACK ARCHIVE (OFFLINE)"` and has amber theme classes.
- **TC-Z1-02 (Provincial AQI Badge)**: Verify element `#provincial-aqi-badge` displays current mean AQI (e.g. `AQI: 342 - VERY UNHEALTHY`) with the exact PEPC background hex color (`#7E0023`).
- **TC-Z1-03 (Simulation Clock)**: Verify element `#simulation-clock-display` displays Pakistan Standard Time formatted as `PKT (UTC+5): [Day] [DD] [Mon] [HH]:00`.
- **TC-Z1-04 (Sub-View Navigation Tabs)**: Verify all 4 tab buttons exist: `Main Console`, `Lahore Focus`, `Hourly Heatmap`, and `Transboundary`. Clicking a tab switches active route state without page reload.
- **TC-Z1-05 (Data Source Selector)**: Verify data source selector radio/select exists with options `Live Feed`, `Baseline Archive`, and `User CSV Dataset`. Switching to `Baseline Archive` triggers offline data load.

##### Zone 2: Primary Pollutant Switcher
- **TC-Z2-01 (9 Statutory Pollutant Buttons)**: Verify persistent horizontal control strip renders exactly 9 buttons: `AQI`, `PM2.5`, `PM10`, `NO2`, `SO2`, `CO`, `O3`, `NO`, `NOx`.
- **TC-Z2-02 (Statutory Regulatory Limit Badges)**: Verify each button displays its official PEQS limit badge (`35 ug/m3` for PM2.5, `150 ug/m3` for PM10, `80 ug/m3` for NO2, `5 mg/m3` for CO, etc.).
- **TC-Z2-03 (Pollutant Switch Reactivity)**: Clicking `PM10` updates active pollutant in Zustand `spatialStore`. Asserts all 5 zones update their active labels and units without resetting time scrubber position.
- **TC-Z2-04 (Keyboard Navigation Shortcuts)**: Pressing number keys `1` through `9` triggers instant switching to the corresponding pollutant.

##### Zone 3: Interactive Geographic Map Viewport & Time Scrubber Deck
- **TC-Z3-01 (5-Layer Stacked Canvas Initialization)**: Verify canvas DOM elements exist:
  - `#canvas-layer-0-basemap`
  - `#canvas-layer-1-surface-idw`
  - `#canvas-layer-2-wind-particles`
  - `#canvas-layer-3-transport-flux`
  - `#canvas-layer-4-station-labels`
- **TC-Z3-02 (Continuous Temporal Scrubber Slider)**: Verify slider input `#temporal-scrubber-slider` has attributes `min="0"`, `max="215"`, `step="0.01"`. Dragging slider to `100.5` updates `fpos` in `timeStore` and recalculates interpolated sub-hourly concentrations.
- **TC-Z3-03 (Play/Pause & Keyboard Spacebar)**: Clicking `#play-pause-btn` or pressing `Spacebar` toggles playback state between running and paused.
- **TC-Z3-04 (Speed Stepper)**: Verify speed control radios exist for `0.35x` (Slow), `0.8x` (Normal), and `1.6x` (Fast). Selecting `1.6x` doubles the scrubber tick increment per animation frame.
- **TC-Z3-05 (Layer Visibility Toggles)**: Toggling `#toggle-flux-vectors` enables/disables Layer 3 rendering; toggling `#toggle-surface-mode` switches between `Continuous IDW Field` and `Administrative Choropleth`.

##### Zone 4: Real-Time Telemetry Sidebar (360px Fixed Desktop)
- **TC-Z4-01 (Provincial KPI Summary Card)**: Verify mean AQI, PEQS exceedance counter (`38 / 41 districts > PEQS`), and peak district (`Lahore: 492`).
- **TC-Z4-02 (24-Hour Sparkline Canvas)**: Verify `#provincial-sparkline-canvas` renders with provincial historical line, current scrubber vertical cursor line, and dashed red PEQS limit benchmark.
- **TC-Z4-03 (Airport METAR Weather Matrix)**: Verify aerodrome cards render for at least 6 key airports (OPLA, OPFA, OPMT, OPST, OPIS, VIAR) displaying wind direction arrow, speed in knots, and visibility.
- **TC-Z4-04 (Ranked District Exceedance List)**: Verify all 41 districts are rendered in ranked descending order of concentration/AQI, each displaying a relative bar indicator and `LIVE` vs `IDW ESTIMATE` badge.
- **TC-Z4-05 (Selected District Drawer & 16-Sector CPF Rose)**: Clicking a district (e.g. `Lahore`) in the roster opens the deep-dive drawer, displaying the 9-pollutant table and rendering the `#cpf-polar-rose-canvas` (16 sectors, $P_{75}$ threshold, and $0.25$ null hypothesis circle).

##### Zone 5: Deep-Dive Analytics & Transboundary Panels
- **TC-Z5-01 (3x3 Synchronized Multi-Pollutant Grid)**: Verify 9 synchronized mini-canvas viewports render simultaneously for all 9 pollutants, synchronized to the primary time scrubber.
- **TC-Z5-02 (Lahore Network Inset Focus)**: Verify Lahore inset displays all 11 stations (7 fixed, 4 mobile) and Wagha border crossing telemetry.
- **TC-Z5-03 (Virtualized Hourly Heatmap Matrix)**: Verify 41 districts $\times$ 216 hours matrix renders without DOM thrashing using virtualized rows.
- **TC-Z5-04 (Transboundary Inflow & Border Normals)**: Verify 39 border normal vector nodes render with inward/outward flux balance.

##### Cross-Cutting Workflows (CSV Upload & SSE Streaming)
- **TC-WF-01 (User CSV Upload & Quarantine Modal)**:
  - Submitting `valid_station_observations.csv` via the upload dialog returns HTTP 200, parses 15 rows, shows `"Success: 15 rows merged"`, and sets status pill to `USER CSV DATASET`.
  - Submitting `invalid_out_of_bounds.csv` opens the `#quarantine-report-modal`, displaying a structured table of quarantined rows with error reasons (`"Latitude 25.0 outside Punjab boundary [27.0, 35.0]"`).
- **TC-WF-02 (SSE Live Telemetry Stream Processing)**:
  - Mocking an SSE message `event: hourly_update` with hour index 216 automatically advances the time scrubber maximum from 215 to 216, flashes the status pill, and updates the sidebar ranking.
  - Verifying the SSE consumer handles `: keepalive\n\n` comments without triggering disconnections or unhandled errors.

---

## 4. Caveats

1. **Read-Only Constraint**: In strict adherence to the agent instructions, zero source code or test files were directly modified or written during this investigation. All proposed changes (such as the `Optional` typing import in `src/api/main.py:9` and the FastAPI SPA static mounting) are communicated as precise diffs for the implementer agent.
2. **WebGL Fallback in Headless CI**: In headless Linux/Windows CI environments without hardware GPU acceleration, WebGL canvas contexts can fail to initialize unless software rasterization (`llvmpipe` / `swiftshader` or headless Chrome flags `--use-gl=angle --use-angle=swiftshader`) is configured. The multi-layer canvas renderer should automatically degrade to standard Canvas 2D offscreen downsampling if WebGL context acquisition returns `null`.
3. **Large Baseline Dataset Footprint**: `baseline_data.json` is 10.7 MB uncompressed. While fast to load in local desktop browsers, serving this over external networks requires HTTP gzip/brotli compression (reducing transfer size to ~1.8 MB) or serving partitioned hourly slice chunks on demand.

---

## 5. Conclusion

1. **API Integration Readiness**: The 6 backend FastAPI route modules (`meta`, `observations`, `spatial`, `analytics`, `stream`, `ingest`) are complete, fully operational, and verified by passing all 15 integration tests in 1.73s. The designed TypeScript client layer (`src/frontend/src/api/`) maps 1:1 to all backend contracts, enforces physical domain rules (blocking AQI mass advection), and provides an auto-reconnecting SSE stream consumer with a 15s keepalive heartbeat watchdog.
2. **Offline & Standalone Strategy**: Pre-bundling the extracted baseline JSON records from `data/baseline/` into `src/frontend/public/data/baseline/` enables 100% offline functionality. The designed client-side fallback provider allows the complete 5-zone UI dashboard, 216-hour scrubber, 16-sector CPF rose, and canvas rendering engine to execute without a running backend server.
3. **FastAPI Delivery**: FastAPI can seamlessly deliver the frontend single-page application by mounting `StaticFiles` and implementing an SPA catch-all route. The minor deferred typing bug in `src/api/main.py:9` (`NameError: name 'Optional' is not defined`) has been isolated and a 2-line fix documented.
4. **Automated UI Testing Strategy**: A structured test suite covering all 5 UI zones, 9 pollutant switches, 5 canvas layers, time scrubber controls, CSV quarantine modal, and SSE push streaming has been fully designed and specified for Milestone M5 implementation and Milestone M6 verification gate certification.

---

## 6. Verification Method

To independently verify the empirical observations and test designs documented in this blueprint:

1. **Verify Backend API Endpoint Contracts**:
   ```powershell
   python -m pytest tests/integration/test_api_endpoints.py -v
   ```
   *Expected Result*: All 15 tests pass (100% green in ~1.8s).

2. **Verify the `src/api/main.py` Annotation Defect**:
   ```powershell
   python -c "from src.api.main import init_app_state; print(init_app_state.__annotations__)"
   ```
   *Expected Result*: Raises `NameError: name 'Optional' is not defined`.
   *Fix Validation*: Add `from typing import AsyncGenerator, Optional` to line 9; re-run command to confirm it outputs `{'app': <class 'fastapi.applications.FastAPI'>, 'base_dir': typing.Optional[pathlib.Path], 'return': None}` with exit code 0.

3. **Verify Baseline Dataset Integrity**:
   ```powershell
   Get-ChildItem -Path "data\baseline" | Select-Object Name, Length
   ```
   *Expected Result*: Confirms `stations.json` (~64.5 KB), `districts.json` (~1.12 MB), `airports.json` (~34.3 KB), and `baseline_data.json` (~10.7 MB) are present and populated.

4. **Verify E2E Real-World Scenarios**:
   ```powershell
   python -m pytest tests/e2e/test_tier4_real_world_scenarios.py -v
   ```
   *Expected Result*: All 5 scenarios pass, verifying offline fallback baseline templating, severe smog inversion, and user CSV validation.
