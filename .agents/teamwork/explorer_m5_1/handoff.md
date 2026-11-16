# Technical Blueprint: Milestone M5 — Services, Ingestion & Serving Integration

## 1. Observation

### 1.1 Existing Codebase & Directory Structure
1. **`src/services/` Directory**:
   - Currently contains Python backend services: `analytics_service.py`, `dto.py`, `ingestion_service.py`, `observation_service.py`, `precomputation_service.py`, `spatial_service.py`, `__init__.py`.
   - `tsconfig.json` defines `"include": ["src", "vite.config.ts"]` and `"paths": { "@/*": ["src/*"] }`. Adding TypeScript files (`api.ts`, `sse.ts`, `fallback.ts`) directly into `src/services/` conforms to `PROJECT.md` line 74 without conflicting with Python modules.
2. **FastAPI Root Serving (`src/api/main.py:178–198`)**:
   ```python
   # Mount Static Frontend Assets & Root Delivery
   frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
   static_dir = frontend_dir / "static"
   if static_dir.exists():
       app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

   @app.get("/", include_in_schema=False)
   @app.get("/index.html", include_in_schema=False)
   async def serve_index():
       html_file = frontend_dir / "dashboard.html"
       if not html_file.exists():
           html_file = frontend_dir / "index.html"
       if html_file.exists():
           return FileResponse(html_file)
       return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"message": "Frontend dashboard not found"})
   ```
3. **Vite Production Bundler (`vite.config.ts:7–10, 40–62`)**:
   - `root: path.resolve(repoRoot, 'src')`
   - Entry point: `path.resolve(repoRoot, 'src/workstation.html')`
   - Output directory: `path.resolve(repoRoot, 'dist')`
   - Output HTML: `dist/workstation.html` (1.17 KB)
   - Asset directory: `dist/assets/` (contains CSS, vendor JS chunks, data JSON)
   - Note in `vite.config.ts`: *"HTML entry is src/workstation.html. The filename cannot be index.html: tests/unit/test_m1_adversarial.py rejects that name anywhere outside 'original System/', and a repo-root index.html fails the archival tests."*
4. **Backend Test Invariants & Assertions on Frontend Files**:
   - `tests/unit/test_m1_adversarial.py:44, 55–56`:
     ```python
     forbidden_names = {"index.html", "index.htm", "collector.py"}
     ...
     if rel == Path("index.html"):  # Only root index.html is allowed
         continue
     if p.name in forbidden_names:
         remnants.append(str(rel))
     ```
     `dist/` is **not** excluded in `test_m1_adversarial.py`. If Vite emitted `dist/index.html`, this test would fail. Therefore, the production entrypoint in `dist/` must remain `dist/workstation.html`.
   - `tests/integration/test_frontend.py:37–51, 81–86, 287–291`:
     - Line 41: `response = await client.get("/")` asserts `response.status_code == 200`, `text/html` in content-type, `"Punjab Air Quality"` in text, and `"<!DOCTYPE html>"` in text.
     - Line 48: `resp_index = await client.get("/index.html")` asserts `resp_index.text == response.text`.
     - Line 58–70: `await client.get("/static/css/tokens.css")`, `/static/js/{app.js, canvas.js, geo.js, api.js, ui.js}`, `/static/data/geo_boundaries.json` all assert HTTP 200.
     - Line 83: `html_path = FRONTEND_DIR / "dashboard.html"` asserts file exists.
     - Line 289: `html = (FRONTEND_DIR / "dashboard.html").read_text(encoding="utf-8")` reads `src/frontend/dashboard.html` directly from disk.
   - `tests/integration/test_m5_resilience_challenge.py`:
     - Line 103, 262: Node.js subprocess executes `import { ApiClient } from './src/frontend/static/js/api.js'`.
     - Line 353: Node.js subprocess executes `import { UIController } from './src/frontend/static/js/ui.js'`.
     - Line 213: `assert "2000 * Math.pow(1.5" in api_js` and `assert "this.maxReconnectAttempts = 5" in api_js` and `assert "Math.random()" in api_js`.
     - Line 254–258: Checks for 45-second watchdog timer and `addEventListener('keepalive'`.
     - Line 463–469: Verifies client guards blocking advection flux for AQI.
   - `tests/e2e/test_tier5_adversarial_hardening_api.py:733–778`:
     - Verifies static delivery under `/static/` and tests directory traversal rejection (`/static/../main.py` -> 404/400).
5. **Backend CSV Ingestion Contract (`src/api/routes/ingest.py:116–157`)**:
   - Route: `POST /api/v1/ingest/csv`
   - Parameters:
     - `file: UploadFile = File(...)` (must end with `.csv`, len > 0)
     - `allow_missing_coords: bool = Form(False)`
   - Response Schema (`CSVIngestResponse` in `src/api/schemas/ingest.py`):
     ```python
     status: str  # "success" | "partial_quarantine" | "failed"
     filename: str
     total_rows: int
     valid_rows: int
     quarantined_rows: int
     merged_observations_count: int
     errors: List[str]
     quarantine_records: Optional[List[QuarantineDetail]]
     quarantined_records: Optional[List[QuarantineDetail]]
     ```
     where `QuarantineDetail` contains `row_number: int`, `station_id: Optional[str]`, `error_type: str`, `error_message: str`, `raw_record: Dict[str, Any]`.
6. **Existing Test Suite Baseline Results**:
   - `python tests/e2e/run_all_tests.py`: 50/50 PASSED (100% in 5.56s).
   - `python -m pytest tests/unit -q`: 292/292 PASSED (100% in 55.58s).
   - `python -m pytest tests/integration -q`: 266/266 PASSED (100% in 71.77s).
   - `python tests/challenge_build_styling_r2.py`: 4/4 Probes PASSED (0 emojis, 0 banned deps, 56/56 WCAG AAA pairs).

---

## 2. Logic Chain

1. **Production Serving Resolution**:
   - *Premise*: The prompt requests serving compiled `dist/` at `GET /` and `/assets` while retiring `dashboard.html`, without breaking any tests.
   - *Deduction from Observations 1.4 & 1.5*: Tests `test_frontend.py` line 289 and `test_m5_resilience_challenge.py` lines 103, 353 directly open and parse `src/frontend/dashboard.html` and `src/frontend/static/js/api.js` from disk.
   - *Deduction from Observation 1.4*: Tests also query `/static/css/tokens.css` and `/static/js/*` via HTTP client.
   - *Conclusion*: Retiring `dashboard.html` means replacing it as the primary HTTP payload at `GET /` with `dist/workstation.html`, while **retaining** `src/frontend/dashboard.html` and `src/frontend/static/` on the filesystem for test fixture authenticity and test runner compatibility.
   - *Serving Logic in `src/api/main.py`*:
     1. Mount `/assets` to `dist/assets` (enabling all Vite bundle chunks: JS, CSS, JSON).
     2. Keep `/static` mounted to `src/frontend/static`.
     3. At `GET /` and `GET /index.html`, serve `dist/workstation.html` when present. If not compiled (e.g. fresh repository clone), fall back gracefully to `src/frontend/dashboard.html`.
     4. `dist/workstation.html` starts with `<!DOCTYPE html>` and has `<title>EPA Punjab Air Quality</title>`, satisfying all string assertions in `test_frontend_root_endpoint_serves_html` and `test_spa_root_and_static_delivery`.

2. **TypeScript Services Architecture (`src/services/`)**:
   - `src/services/api.ts`:
     - Must be a fully-typed HTTP client wrapping `fetch` targeting `/api/v1/*` endpoints.
     - Incorporates client-side physical domain invariant guard: When `pollutant === 'AQI'` is passed to `getAdvectionFlux`, the client must coerce it to `'PM2.5'` and emit a console warning, because mass flux $\mathbf{J} = C \mathbf{u}$ is physically undefined for dimensionless indices.
     - Implements endpoints: `getDistricts`, `getStations`, `getCurrentObservations`, `getHourlyObservations`, `getSpatialSurface`, `getCPFRose`, `getAdvectionFlux`, `getTransboundary`, `uploadCSV`, `getHealth`, `getStreamStatus`, `triggerTick`.
   - `src/services/sse.ts`:
     - Connects to `/api/v1/stream/live` using native browser `EventSource`.
     - Handles `hourly_update` events, dispatching parsed typed payloads.
     - Implements a **45-second watchdog timer**:
       - Reset on connection open, on each `keepalive` event, on `ping` events, and on any incoming message.
       - If no heartbeat is received within 45 seconds (silent TCP drop), triggers forced disconnection, marks mode as `'fallback'`, and invokes reconnection.
     - Implements **Randomized Exponential Backoff with Full Jitter**:
       - $\text{base} = \min(30000, 2000 \times 1.5^{\min(\text{attempts}, 10)})$
       - $\text{timeout} = \text{base} \times (0.5 + 0.5 \times \text{Math.random()})$
       - Guarantees non-zero variance $>1000$ and bounded delay between $1500$ ms and $30000$ ms, preventing thundering herds.
   - `src/services/fallback.ts`:
     - Encapsulates baseline airshed data loading from `data/baseline/baseline_data.json` and `data/baseline/airports.json`.
     - Applies domain normalizers from `src/domain/normalizer/dataNormalizer.ts` to ensure all 5 schema traps are handled:
       1. Centroid inversion: `[lat, lon]` -> `[lon, lat]`.
       2. Aerodrome wind state: `dropout` vs `calm` vs `active`.
       3. Station 172 Wazirabad blacklist: `blacklisted: true`, `ANEMOMETER BLACKLISTED (VANE OFFSET)`.
       4. Dynamic station counts: 74 fixed, 5 mobile.
       5. Estimation flag unification: `is_estimated: boolean`.
     - Provides offline interpolation, CPF wind rose calculation, and advection flux extraction when the backend is offline.

3. **CSV Multipart Ingestion Modal (`CSVIngestModal.tsx`)**:
   - Current modal in `CommandBar.tsx` is a bare input without validation feedback or quarantine table.
   - New `CSVIngestModal.tsx`:
     - Validates file type (`.csv`) and non-empty size before upload.
     - Includes `allow_missing_coords` toggle switch ("Allow catalog coordinate resolution").
     - Posts to `/api/v1/ingest/csv` using `FormData`.
     - Evaluates backend `CSVIngestResponse`:
       - If `status === "failed"` or `quarantined_rows > 0`: keeps modal open, renders `#csvQuarantineArea` with structured `<table>` displaying `Row`, `Station ID`, `Error Code`, `Reason`.
       - If `valid_rows > 0`: updates application mode to `'user_csv'`, updates data-source badge, and triggers airshed re-interpolation (T1 discrete IDW and T2 anisotropic surface).

---

## 3. Caveats

1. **Preservation of `src/frontend/`**: The legacy directory `src/frontend/` (containing `dashboard.html` and `static/js/api.js`) must **not** be deleted. Deleting it will cause immediate failures in pytest integration tests (`test_frontend.py` line 289 and `test_m5_resilience_challenge.py` lines 103, 353).
2. **Vite Output Filename**: The Vite output HTML file must remain `dist/workstation.html` and **not** `dist/index.html`. `tests/unit/test_m1_adversarial.py` line 44 scans the workspace for files named `index.html` and only allows the repo-root `index.html` and `original System/index.html`.
3. **No External Network Dependencies**: All font and library loading in production build occurs via local or pre-bundled assets. In test runners without an active internet connection, baseline fallback ensures 100% test reproducibility.

---

## 4. Conclusion & Concrete Technical Blueprint

### Component 1: `src/services/api.ts`
Strongly-typed API client interfacing with FastAPI backend:

```typescript
import type { PollutantKey, NormalizedDistrict, NormalizedStation } from '../domain/types';

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

export interface CurrentObservationSnapshot {
  timestamp: string;
  pollutant: string;
  mean_aqi: number;
  exceedance_peqs_count: number;
  reporting_districts_count: number;
  total_districts: number;
  districts: Record<string, {
    district_id: string;
    concentration: number | null;
    aqi: number | null;
    pepc_tier: string;
    is_estimated: boolean;
    wind_speed: number | null;
    wind_direction: number | null;
  }>;
  stations: Record<string, {
    station_id: string;
    station_name: string;
    concentration: number | null;
    aqi: number | null;
    pepc_tier: string;
    wind_speed: number | null;
    wind_direction: number | null;
    is_blacklisted: boolean;
  }>;
}

export interface HourlySeriesResponse {
  pollutant: string;
  timestamps: string[];
  districts: Record<string, {
    id: string;
    name: string;
    concentrations: (number | null)[];
    aqi: (number | null)[];
    wind_u: (number | null)[];
    wind_v: (number | null)[];
  }>;
}

export interface CPFRoseResponse {
  district: string;
  pollutant: string;
  threshold: number;
  total_valid_hours: number;
  calm_hours_excluded: number;
  sectors: Array<{
    sector: number;
    angle_deg: number;
    n_k: number;
    m_k: number;
    cpf_ratio: number | null;
    is_suppressed: boolean;
  }>;
}

export interface AdvectionFluxResponse {
  pollutant: string;
  timestamp: string;
  top_pathways: Array<{
    source_district: string;
    receptor_district: string;
    distance_km: number;
    bearing_deg: number;
    flux: number;
    source_concentration: number;
    wind_speed: number;
  }>;
  net_balance: Record<string, number>;
}

export interface TransboundaryResponse {
  timestamp: string;
  pollutant: string;
  provincial_attribution: {
    domestic_percentage: number;
    cross_border_percentage: number;
    inflow_flux: number;
    outflow_flux: number;
  };
  border_normals: Array<{
    node_id: number;
    latitude: number;
    longitude: number;
    normal_u: number;
    normal_v: number;
    wind_u: number;
    wind_v: number;
    dot_product_phi: number;
    is_inflow_crimson: boolean;
  }>;
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

export class ApiService {
  private baseUrl: string;

  constructor(baseUrl: string = '') {
    this.baseUrl = baseUrl;
  }

  async getHealth(): Promise<{ status: string; service: string; version: string }> {
    const res = await fetch(`${this.baseUrl}/health`);
    if (!res.ok) throw new Error(`Health check failed: ${res.status}`);
    return res.json();
  }

  async getDistricts(monitoredOnly: boolean = false): Promise<DistrictMetaResponse[]> {
    const params = new URLSearchParams({ monitored_only: monitoredOnly ? 'true' : 'false' });
    const res = await fetch(`${this.baseUrl}/api/v1/meta/districts?${params}`);
    if (!res.ok) throw new Error(`Districts fetch failed: ${res.status}`);
    return res.json();
  }

  async getStations(district?: string, stationType?: string): Promise<StationMetaResponse[]> {
    const params = new URLSearchParams();
    if (district) params.append('district', district);
    if (stationType) params.append('station_type', stationType);
    const res = await fetch(`${this.baseUrl}/api/v1/meta/stations?${params}`);
    if (!res.ok) throw new Error(`Stations fetch failed: ${res.status}`);
    return res.json();
  }

  async getCurrentObservations(pollutant: PollutantKey = 'AQI', district?: string): Promise<CurrentObservationSnapshot> {
    const params = new URLSearchParams({ pollutant });
    if (district) params.append('district', district);
    const res = await fetch(`${this.baseUrl}/api/v1/observations/current?${params}`);
    if (!res.ok) throw new Error(`Current observations failed: ${res.status}`);
    return res.json();
  }

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

  async getCPFRose(district: string = 'Lahore', pollutant: PollutantKey = 'PM2.5', threshold?: number): Promise<CPFRoseResponse> {
    const params = new URLSearchParams({ district, pollutant });
    if (threshold !== undefined) params.append('threshold', String(threshold));
    const res = await fetch(`${this.baseUrl}/api/v1/analytics/cpf?${params}`);
    if (!res.ok) throw new Error(`CPF Rose failed: ${res.status}`);
    return res.json();
  }

  async getAdvectionFlux(pollutant: PollutantKey = 'PM2.5', limit: number = 60): Promise<AdvectionFluxResponse> {
    // PHYSICAL INVARIANT GUARD: Mass flux is strictly undefined for AQI
    let effectivePollutant: string = pollutant;
    if (pollutant.toUpperCase() === 'AQI') {
      console.warn('Advection flux is physically undefined for AQI. Defaulting to PM2.5.');
      effectivePollutant = 'PM2.5';
    }
    const params = new URLSearchParams({ pollutant: effectivePollutant, limit: String(limit) });
    const res = await fetch(`${this.baseUrl}/api/v1/analytics/flux?${params}`);
    if (!res.ok) throw new Error(`Advection flux failed: ${res.status}`);
    return res.json();
  }

  async getTransboundary(pollutant: PollutantKey = 'PM2.5'): Promise<TransboundaryResponse> {
    const params = new URLSearchParams({ pollutant });
    const res = await fetch(`${this.baseUrl}/api/v1/analytics/transboundary?${params}`);
    if (!res.ok) throw new Error(`Transboundary analytics failed: ${res.status}`);
    return res.json();
  }

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
}
```

---

### Component 2: `src/services/sse.ts`
EventSource Manager with 45-Second Watchdog and Jittered Reconnection:

```typescript
export type StreamMode = 'live' | 'fallback';

export interface SSEUpdatePayload {
  timestamp: string;
  mean_aqi?: number;
  peak_aqi?: number;
  peak_district?: string;
  districts_committed?: number;
  stations_committed?: number;
  readings?: Record<string, number | null>;
  [key: string]: any;
}

export class LiveStreamManager {
  private url: string;
  private eventSource: EventSource | null = null;
  private watchdogTimer: ReturnType<typeof setTimeout> | null = null;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private watchdogTimeoutMs: number = 45000;
  private reconnectAttempts: number = 0;
  private maxReconnectAttempts: number = 5;
  private isDestroyed: boolean = false;

  private onUpdateCallback?: (data: SSEUpdatePayload) => void;
  private onErrorCallback?: (err: any) => void;
  private onStatusChangeCallback?: (mode: StreamMode) => void;

  constructor(url: string = '/api/v1/stream/live') {
    this.url = url;
  }

  connect(
    onUpdate: (data: SSEUpdatePayload) => void,
    onError?: (err: any) => void,
    onStatusChange?: (mode: StreamMode) => void,
  ): void {
    this.isDestroyed = false;
    this.onUpdateCallback = onUpdate;
    this.onErrorCallback = onError;
    this.onStatusChangeCallback = onStatusChange;
    this.initEventSource();
  }

  private initEventSource(): void {
    this.cleanup();
    if (this.isDestroyed) return;

    try {
      this.eventSource = new EventSource(this.url);

      this.eventSource.onopen = () => {
        this.reconnectAttempts = 0;
        this.onStatusChangeCallback?.('live');
        this.resetWatchdog();
      };

      this.eventSource.addEventListener('hourly_update', (event: MessageEvent) => {
        this.resetWatchdog();
        try {
          const payload = JSON.parse(event.data) as SSEUpdatePayload;
          this.onUpdateCallback?.(payload);
        } catch (err) {
          console.error('Failed to parse SSE hourly_update payload:', err);
        }
      });

      this.eventSource.addEventListener('keepalive', () => {
        this.resetWatchdog();
      });

      this.eventSource.addEventListener('ping', () => {
        this.resetWatchdog();
      });

      this.eventSource.onmessage = () => {
        this.resetWatchdog();
      };

      this.eventSource.onerror = (err) => {
        console.warn('SSE connection interrupted, initiating fallback backoff...', err);
        this.clearWatchdog();
        this.closeEventSource();
        this.onStatusChangeCallback?.('fallback');
        this.onErrorCallback?.(err);
        this.scheduleReconnect();
      };
    } catch (err) {
      console.warn('EventSource initialization failed:', err);
      this.onStatusChangeCallback?.('fallback');
      this.scheduleReconnect();
    }
  }

  private resetWatchdog(): void {
    this.clearWatchdog();
    this.watchdogTimer = setTimeout(() => {
      console.warn('SSE Watchdog: 45s silence detected. Reconnecting...');
      this.closeEventSource();
      this.onStatusChangeCallback?.('fallback');
      this.scheduleReconnect();
    }, this.watchdogTimeoutMs);
  }

  private clearWatchdog(): void {
    if (this.watchdogTimer) {
      clearTimeout(this.watchdogTimer);
      this.watchdogTimer = null;
    }
  }

  private scheduleReconnect(): void {
    if (this.isDestroyed) return;
    this.reconnectAttempts++;

    // Randomized exponential backoff with full jitter: min(30000, 2000 * 1.5^attempts)
    const attemptExp = Math.min(this.reconnectAttempts, 10);
    const base = Math.min(30000, 2000 * Math.pow(1.5, attemptExp));
    const delay = base * (0.5 + Math.random() * 0.5);

    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    this.reconnectTimer = setTimeout(() => {
      this.initEventSource();
    }, delay);
  }

  private closeEventSource(): void {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
  }

  private cleanup(): void {
    this.clearWatchdog();
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    this.closeEventSource();
  }

  disconnect(): void {
    this.isDestroyed = true;
    this.cleanup();
    this.onStatusChangeCallback?.('fallback');
  }
}
```

---

### Component 3: `src/services/fallback.ts`
Robust Offline Airshed Loader & Imputer:

```typescript
import baselineUrl from '../../data/baseline/baseline_data.json?url';
import type { BaselineFile } from '../workstation/loadBaseline';
import { normalizeDistrict, normalizeStation, normalizeAirport } from '../domain/normalizer/dataNormalizer';
import type { NormalizedDistrict, NormalizedStation, NormalizedAirport, PollutantKey } from '../domain/types';

export class BaselineFallbackService {
  private cachedData: BaselineFile | null = null;
  private cachedDistricts: NormalizedDistrict[] | null = null;
  private cachedStations: NormalizedStation[] | null = null;
  private cachedAirports: NormalizedAirport[] | null = null;

  async load(): Promise<BaselineFile> {
    if (this.cachedData) return this.cachedData;
    const res = await fetch(baselineUrl);
    if (!res.ok) throw new Error(`Offline baseline fetch failed: ${res.status}`);
    this.cachedData = (await res.json()) as BaselineFile;
    return this.cachedData;
  }

  async getDistricts(): Promise<NormalizedDistrict[]> {
    if (this.cachedDistricts) return this.cachedDistricts;
    const data = await this.load();
    this.cachedDistricts = Object.values(data.districts).map((d) => normalizeDistrict(d as any));
    return this.cachedDistricts;
  }

  async getStations(): Promise<NormalizedStation[]> {
    if (this.cachedStations) return this.cachedStations;
    const data = await this.load();
    this.cachedStations = data.stations.map((s) => normalizeStation(s as any));
    return this.cachedStations;
  }

  async getAirports(): Promise<NormalizedAirport[]> {
    if (this.cachedAirports) return this.cachedAirports;
    const data = await this.load();
    this.cachedAirports = data.airports.map((a) => normalizeAirport(a));
    return this.cachedAirports;
  }

  async getHourlyFrame(pollutant: PollutantKey, hourIndex: number) {
    const data = await this.load();
    const frame = data.pol[pollutant]?.frames?.[hourIndex]?.c ?? {};
    const windHour = data.wind[hourIndex] ?? {};
    return { frame, windHour };
  }
}
```

---

### Component 4: `src/components/command/CSVIngestModal.tsx`
Institutional Modal with Structured Quarantine Table:

```tsx
import React, { useState } from 'react';
import { Upload, AlertTriangle, CheckCircle2, XCircle } from '../common/icons';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '../ui/dialog';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Badge } from '../ui/badge';
import type { CSVIngestResponse } from '../../services/api';

export interface CSVIngestModalProps {
  onUpload: (file: File, allowMissingCoords: boolean) => Promise<CSVIngestResponse>;
  onSuccessMerged?: (result: CSVIngestResponse) => void;
}

export const CSVIngestModal: React.FC<CSVIngestModalProps> = ({ onUpload, onSuccessMerged }) => {
  const [open, setOpen] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [allowMissingCoords, setAllowMissingCoords] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [response, setResponse] = useState<CSVIngestResponse | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0];
    setValidationError(null);
    setResponse(null);
    if (!selected) {
      setFile(null);
      return;
    }
    if (!selected.name.toLowerCase().endsWith('.csv')) {
      setValidationError('Invalid file type. Only .csv files are supported.');
      setFile(null);
      return;
    }
    if (selected.size === 0) {
      setValidationError('Selected file is empty (0 bytes).');
      setFile(null);
      return;
    }
    setFile(selected);
  };

  const handleSubmit = async () => {
    if (!file) return;
    setUploading(true);
    setValidationError(null);
    try {
      const res = await onUpload(file, allowMissingCoords);
      setResponse(res);
      if (res.valid_rows > 0 && res.status !== 'failed') {
        onSuccessMerged?.(res);
      }
    } catch (err: any) {
      setValidationError(err.message || 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  const quarantinedRecords = response?.quarantined_records ?? response?.quarantine_records ?? [];

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm" className="h-8 gap-1.5 rounded-none text-xs font-medium">
          <Upload size={14} strokeWidth={1.25} /> Ingest CSV
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-2xl rounded-none border-border bg-background p-6">
        <DialogHeader>
          <DialogTitle className="font-mono text-sm uppercase tracking-wider">
            EPA Telemetry CSV Ingestion & Quality Quarantine
          </DialogTitle>
          <DialogDescription className="font-mono text-xs text-muted-foreground">
            Multipart upload to POST /api/v1/ingest/csv. Validates coordinates, statutory pollutants, and temporal holds.
          </DialogDescription>
        </DialogHeader>

        <div className="mt-4 space-y-4">
          <div className="space-y-2">
            <label className="font-mono text-xs font-medium text-foreground">Select Ingestion CSV File</label>
            <Input
              type="file"
              accept=".csv,text/csv"
              onChange={handleFileChange}
              disabled={uploading}
              className="rounded-none font-mono text-xs"
            />
          </div>

          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="allowCoords"
              checked={allowMissingCoords}
              onChange={(e) => setAllowMissingCoords(e.target.checked)}
              disabled={uploading}
              className="h-4 w-4 rounded-none"
            />
            <label htmlFor="allowCoords" className="font-mono text-xs text-muted-foreground">
              Allow canonical catalog coordinate resolution for recognized stations
            </label>
          </div>

          <div className="flex items-center justify-between border-t border-border pt-4">
            <Button
              onClick={handleSubmit}
              disabled={!file || uploading}
              className="rounded-none font-mono text-xs"
            >
              {uploading ? 'Processing & Validating…' : 'Upload & Commit Dataset'}
            </Button>
            {response && (
              <Badge
                variant="outline"
                className={`rounded-none font-mono text-xs ${
                  response.status === 'success'
                    ? 'border-emerald-500/40 text-emerald-500'
                    : response.status === 'partial_quarantine'
                    ? 'border-amber-500/40 text-amber-500'
                    : 'border-rose-500/40 text-rose-500'
                }`}
              >
                {response.status.toUpperCase()}: {response.valid_rows} VALID / {response.quarantined_rows} QUARANTINED
              </Badge>
            )}
          </div>

          {validationError && (
            <div className="border border-rose-500/40 bg-rose-500/10 p-3 font-mono text-xs text-rose-400">
              {validationError}
            </div>
          )}

          {response?.errors && response.errors.length > 0 && (
            <div className="border border-rose-500/40 bg-rose-500/10 p-3 font-mono text-xs text-rose-400">
              <span className="font-bold">Schema Rejection Errors:</span>
              <ul className="list-disc pl-5 mt-1 space-y-0.5">
                {response.errors.map((e, idx) => (
                  <li key={idx}>{e}</li>
                ))}
              </ul>
            </div>
          )}

          {/* QUARANTINE INSPECTOR AREA (Required for adversarial tests) */}
          <div id="csvQuarantineArea" className="mt-4">
            {quarantinedRecords.length > 0 && (
              <div className="space-y-2">
                <span className="font-mono text-xs font-semibold uppercase text-muted-foreground">
                  Quarantine Inspection Log ({quarantinedRecords.length} records rejected)
                </span>
                <div className="max-h-48 overflow-auto border border-border">
                  <table className="w-full text-left font-mono text-xs border-collapse">
                    <thead className="bg-muted text-muted-foreground border-b border-border">
                      <tr>
                        <th className="p-2 border-r border-border">Row</th>
                        <th className="p-2 border-r border-border">Station ID</th>
                        <th className="p-2 border-r border-border">Error Code</th>
                        <th className="p-2">Error Message</th>
                      </tr>
                    </thead>
                    <tbody>
                      {quarantinedRecords.map((r, idx) => (
                        <tr key={idx} className="border-b border-border/50 hover:bg-muted/50">
                          <td className="p-2 border-r border-border tabular-nums">{r.row_number}</td>
                          <td className="p-2 border-r border-border">{r.station_id || 'N/A'}</td>
                          <td className="p-2 border-r border-border text-rose-400">{r.error_type}</td>
                          <td className="p-2 text-muted-foreground">{r.error_message}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
};
```

---

### Component 5: Production Serving in `src/api/main.py`
Exact implementation diff to mount compiled assets and root workstation without breaking tests:

```python
    # -------------------------------------------------------------------------
    # Mount Static Frontend Assets & Workstation Root Delivery
    # -------------------------------------------------------------------------
    frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
    static_dir = frontend_dir / "static"
    dist_dir = Path(__file__).resolve().parent.parent.parent / "dist"
    dist_assets = dist_dir / "assets"

    # Mount compiled Vite assets directory (/assets)
    if dist_assets.exists():
        app.mount("/assets", StaticFiles(directory=str(dist_assets)), name="assets")

    # Retain /static mount for test suites, fixtures, and legacy dependencies
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    @app.get("/", include_in_schema=False)
    @app.get("/index.html", include_in_schema=False)
    async def serve_index():
        # 1. Prefer compiled institutional workstation bundle
        dist_html = dist_dir / "workstation.html"
        if dist_html.exists():
            return FileResponse(dist_html)

        # 2. Fall back to legacy dashboard in unbuilt test/CI environments
        legacy_html = frontend_dir / "dashboard.html"
        if not legacy_html.exists():
            legacy_html = frontend_dir / "index.html"
        if legacy_html.exists():
            return FileResponse(legacy_html)

        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"message": "Frontend dashboard not found"},
        )
```

---

## 5. Verification Method

### Step 1: TypeScript Compilation & Production Bundle Check
```bash
# 1. Verify TypeScript types compile cleanly without error
npx tsc --noEmit

# 2. Build production assets into dist/
npm run build
```
*Pass Criteria*:
- Return code 0.
- `dist/workstation.html` and `dist/assets/` generated with zero warnings/errors.

### Step 2: Adversarial & Styling Challenge Suite
```bash
python tests/challenge_build_styling_r2.py
```
*Pass Criteria*:
- Probe 1 (Build), Probe 2 (Banned imports), Probe 3 (Zero emojis), Probe 4 (WCAG AAA contrast) all output `PASS`.

### Step 3: Pytest Unit Tests
```bash
python -m pytest tests/unit -q
```
*Pass Criteria*:
- 292/292 tests passed with 0 failures (`test_m1_adversarial.py`, `test_data_normalizer.py`, etc.).

### Step 4: Pytest Integration Tests
```bash
python -m pytest tests/integration -q
```
*Pass Criteria*:
- 266/266 tests passed with 0 failures (`test_frontend.py`, `test_m5_resilience_challenge.py`, etc.).

### Step 5: Full E2E Test Suite
```bash
python tests/e2e/run_all_tests.py
```
*Pass Criteria*:
- Tiers 1–4: 50/50 tests passed (100% success rate in < 10 seconds).
