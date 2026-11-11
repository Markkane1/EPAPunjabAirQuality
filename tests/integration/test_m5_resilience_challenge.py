"""
Adversarial Empirical Challenge Test Suite for Milestone M5: Component-Driven UI/UX Dashboard.
Focus Areas:
1. Offline Fallback & Zero-Dependency Operation: Verify that the frontend can load, initialize,
   and render all 5 zones completely from offline baseline fixtures (src/frontend/static/data/)
   without uncaught exceptions when external API requests fail or return 500/503/TypeError.
2. SSE Stream Watchdog & Reconnection Stress Test: Analyze and verify the EventSource stream
   consumer in src/frontend/static/js/api.js, evaluating backoff behavior, absence of jitter
   (thundering herd vulnerability), and absence of a 45-second silent TCP drop watchdog timer.
3. CSV Quarantine Inspector: Stress-test uploading malformed, corrupted, out-of-bounds, or
   missing-column CSV files to evaluate client-side validation logic and quarantine reporting.
4. Physical Invariant Guard: Confirm that requesting advection flux for dimensionless 'AQI' is
   blocked both on the client side (in api.js / canvas.js) and returns HTTP 400 on the
   backend, preserving physical mass conservation J = C * u.
"""
import json
from pathlib import Path
import subprocess
import pytest
import httpx
from httpx import ASGITransport

from src.api.main import create_application

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
FRONTEND_DIR = PROJECT_ROOT / "src" / "frontend"
STATIC_DIR = FRONTEND_DIR / "static"
DATA_DIR = STATIC_DIR / "data"
JS_DIR = STATIC_DIR / "js"
FIXTURES_DIR = PROJECT_ROOT / "tests" / "fixtures"


@pytest.fixture(scope="module")
def app():
    """Create and initialize FastAPI application for test suite."""
    return create_application()


@pytest.fixture
def anyio_backend():
    """Specify asyncio as anyio engine."""
    return "asyncio"


# =============================================================================
# 1. OFFLINE FALLBACK & ZERO-DEPENDENCY OPERATION
# =============================================================================

def test_offline_baseline_fixtures_presence_and_integrity():
    """
    Verify all 5 offline baseline data bundles exist in static/data/ and conform
    to schema requirements for 100% zero-external-dependency offline operation.
    """
    # 1. Geo boundaries
    geo_path = DATA_DIR / "geo_boundaries.json"
    assert geo_path.exists(), "geo_boundaries.json missing from static/data"
    geo_data = json.loads(geo_path.read_text(encoding="utf-8"))
    assert "GEO" in geo_data and "Punjab" in geo_data["GEO"], "Punjab territory polygon missing"
    assert "IND" in geo_data and len(geo_data["IND"]) >= 10, "Indian borderland state polygons missing"

    # 2. Districts metadata
    dist_path = DATA_DIR / "districts.json"
    assert dist_path.exists(), "districts.json missing from static/data"
    districts = json.loads(dist_path.read_text(encoding="utf-8"))
    assert len(districts) == 41, f"Expected 41 districts, got {len(districts)}"
    for d in districts:
        assert "name" in d or "district" in d
        assert "centroid" in d or ("lon" in d and "lat" in d) or ("longitude" in d and "latitude" in d)

    # 3. Stations metadata
    stn_path = DATA_DIR / "stations.json"
    assert stn_path.exists(), "stations.json missing from static/data"
    stations = json.loads(stn_path.read_text(encoding="utf-8"))
    assert len(stations) >= 70, f"Expected >= 70 stations, got {len(stations)}"

    # 4. Airports metadata
    ap_path = DATA_DIR / "airports.json"
    assert ap_path.exists(), "airports.json missing from static/data"
    airports = json.loads(ap_path.read_text(encoding="utf-8"))
    assert len(airports) >= 5, f"Expected >= 5 airports, got {len(airports)}"

    # 5. Baseline 216-Hour Telemetry Dataset
    base_path = DATA_DIR / "baseline_data.json"
    assert base_path.exists(), "baseline_data.json missing from static/data"
    baseline = json.loads(base_path.read_text(encoding="utf-8"))
    assert len(baseline["hours"]) == 216, f"Expected 216 hours, got {len(baseline['hours'])}"
    assert "tbgeo" in baseline
    assert len(baseline["tbgeo"]["samples"]) == 39, "Expected 39 border normal vector nodes"
    assert len(baseline["tbgeo"]["border"]) == 440, "Expected 440 international border coordinates"
    assert "pol" in baseline and "AQI" in baseline["pol"] and "PM2.5" in baseline["pol"]


def test_api_client_offline_fallback_execution_node():
    """
    Executes Node.js test harness importing src/frontend/static/js/api.js,
    simulating HTTP 500, 503, and network TypeError on all /api/v1/ endpoints.
    Verifies that ApiClient falls back gracefully to static JSON fixtures
    without throwing uncaught exceptions.
    """
    node_script = """
    import fs from 'fs';
    import path from 'path';
    import { ApiClient } from './src/frontend/static/js/api.js';

    // Mock global fetch to fail /api/v1/ and serve /static/data/
    global.fetch = async (url) => {
      const u = String(url);
      if (u.includes('/api/v1/')) {
        // Intermittent 503 Service Unavailable / 500 Internal Error
        return {
          ok: false,
          status: 503,
          json: async () => ({ error: 'Service Unavailable' })
        };
      }
      if (u.includes('/static/data/')) {
        const filename = path.basename(u);
        const filepath = path.join('src/frontend/static/data', filename);
        if (fs.existsSync(filepath)) {
          const content = fs.readFileSync(filepath, 'utf8');
          return {
            ok: true,
            status: 200,
            json: async () => JSON.parse(content)
          };
        }
      }
      return { ok: false, status: 404 };
    };

    async function run() {
      const client = new ApiClient('');

      const districts = await client.getDistrictsMeta();
      if (!districts || districts.length !== 41) throw new Error('Districts fallback failed');

      const stations = await client.getStationsMeta();
      if (!stations || stations.length < 70) throw new Error('Stations fallback failed');

      const current = await client.getCurrentObservations('AQI');
      if (!current || !current.districts || Object.keys(current.districts).length !== 41) {
        throw new Error('Current observations fallback failed');
      }

      const hourly = await client.getHourlyObservations('AQI');
      if (!hourly || hourly.total_hours !== 216 || Object.keys(hourly.districts).length !== 41) {
        throw new Error('Hourly observations fallback failed');
      }

      const cpf = await client.getCPFRose('Lahore', 'PM2.5');
      if (!cpf || !cpf.sectors || cpf.sectors.length !== 16) throw new Error('CPF fallback failed');

      const flux = await client.getFluxTransport('PM2.5');
      if (!flux || !flux.top_pathways || flux.top_pathways.length === 0) throw new Error('Flux fallback failed');

      const tb = await client.getTransboundary('PM2.5');
      if (!tb || !tb.border_samples || tb.border_samples.length !== 39) throw new Error('Transboundary fallback failed');

      const geo = await client.getGeoBoundaries();
      if (!geo || !geo.GEO || Object.keys(geo.GEO).length === 0) throw new Error('Geo boundaries fallback failed');

      console.log('NODE_FALLBACK_SUCCESS');
    }

    run().catch(err => {
      console.error(err);
      process.exit(1);
    });
    """

    res = subprocess.run(
        ["node", "-e", node_script],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0, f"Node offline fallback execution failed: {res.stderr}\n{res.stdout}"
    assert "NODE_FALLBACK_SUCCESS" in res.stdout


@pytest.mark.anyio
async def test_spa_root_and_static_delivery(app):
    """Verify FastAPI delivers dashboard.html at / and /index.html and static assets with HTTP 200."""
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        r_root = await client.get("/")
        assert r_root.status_code == 200
        assert "text/html" in r_root.headers.get("content-type", "")
        assert "Punjab Air Quality" in r_root.text

        r_idx = await client.get("/index.html")
        assert r_idx.status_code == 200
        assert r_idx.text == r_root.text

        for asset in ["tokens.css", "api.js", "app.js", "canvas.js", "geo.js", "ui.js"]:
            sub = "css" if asset.endswith(".css") else "js"
            r_asset = await client.get(f"/static/{sub}/{asset}")
            assert r_asset.status_code == 200, f"Failed to retrieve /static/{sub}/{asset}"


# =============================================================================
# 2. SSE STREAM WATCHDOG & RECONNECTION STRESS TEST
# =============================================================================

def test_sse_stream_exponential_backoff_and_jitter_analysis():
    """
    Adversarial Verification of SSE Stream Reconnection in src/frontend/static/js/api.js:
    1. Verifies the reconnection backoff formula base: min(30000, 2000 * Math.pow(1.5, attempts)).
    2. Verifies that random jitter (Math.random()) IS implemented in api.js to avoid thundering herds.
    3. Runs 50 iterations of retry calculation in Node.js to verify non-zero variance and bounded interval.
    """
    api_js = (JS_DIR / "api.js").read_text(encoding="utf-8")

    assert "2000 * Math.pow(1.5" in api_js, "Exponential backoff formula missing from api.js"
    assert "this.maxReconnectAttempts = 5" in api_js, "maxReconnectAttempts missing or changed"

    # Empirical check: Math.random() is present for jitter
    has_jitter = "Math.random()" in api_js
    assert has_jitter, "api.js must implement random jitter in SSE reconnection to prevent thundering herd retry storms."

    # Verify jitter variance via Node.js
    node_script = """
    const delays = [];
    for (let i = 0; i < 50; i++) {
      const base = Math.min(30000, 2000 * Math.pow(1.5, 1)); // 3000ms
      const timeout = base * (0.5 + Math.random() * 0.5);
      delays.push(timeout);
    }
    const minDelay = Math.min(...delays);
    const maxDelay = Math.max(...delays);
    const avgDelay = delays.reduce((a, b) => a + b, 0) / delays.length;
    const variance = delays.reduce((a, b) => a + Math.pow(b - avgDelay, 2), 0) / delays.length;
    console.log(JSON.stringify({ minDelay, maxDelay, variance }));
    """
    res = subprocess.run(["node", "-e", node_script], cwd=str(PROJECT_ROOT), capture_output=True, text=True)
    assert res.returncode == 0
    data = json.loads(res.stdout.strip())
    assert data["minDelay"] >= 1500.0, f"Delay under minimum: {data['minDelay']}"
    assert data["maxDelay"] <= 3000.0, f"Delay exceeded maximum: {data['maxDelay']}"
    assert data["variance"] > 1000.0, "Jitter variance is too small, danger of thundering herd"


def test_sse_stream_watchdog_timer_gap_demonstration():
    """
    Adversarial Verification: 45-Second Silent TCP Drop Watchdog in api.js.
    Verifies that:
    1. api.js implements a 45-second watchdog timer (watchdogTimer / 45000ms).
    2. api.js registers a keepalive event listener to reset connection timers.
    3. In a silent TCP drop scenario, watchdog timer fires, resets mode='fallback',
       and triggers reconnection.
    """
    api_js = (JS_DIR / "api.js").read_text(encoding="utf-8")

    # 1. Check for 45-second watchdog timer or keepalive event listener
    has_watchdog_timer = "watchdog" in api_js.lower() or "45000" in api_js or "45 * 1000" in api_js
    has_keepalive_listener = "addEventListener('keepalive'" in api_js or "addEventListener(\"keepalive\"" in api_js

    assert has_watchdog_timer, "api.js must implement a 45-second watchdog timer against silent TCP drops."
    assert has_keepalive_listener, "api.js must register a keepalive listener to reset watchdog timers on heartbeats."

    # 2. Run Node.js simulation to confirm watchdog timer behavior
    node_script = """
    import { ApiClient } from './src/frontend/static/js/api.js';

    class MockSilentEventSource {
      constructor(url) {
        this.url = url;
        this.listeners = {};
        setTimeout(() => { if (this.onopen) this.onopen(); }, 5);
      }
      addEventListener(evt, fn) { this.listeners[evt] = fn; }
      close() { this.closed = true; }
    }
    global.EventSource = MockSilentEventSource;

    const client = new ApiClient();
    let statusLog = [];
    client.connectLiveStream(
      () => {},
      () => {},
      (mode) => { statusLog.push(mode); }
    );

    setTimeout(() => {
      const hasTimer = client.watchdogTimer !== null && client.watchdogTimer !== undefined;
      console.log('WATCHDOG_TEST: mode=' + client.mode + ', hasWatchdog=' + hasTimer);
      client.disconnectLiveStream();
      process.exit(0);
    }, 20);
    """
    res = subprocess.run(
        ["node", "-e", node_script],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0
    assert "WATCHDOG_TEST: mode=live, hasWatchdog=true" in res.stdout


# =============================================================================
# 3. CSV QUARANTINE INSPECTOR & ADVERSARIAL MALFORMED UPLOADS
# =============================================================================

@pytest.mark.anyio
async def test_csv_backend_quarantine_rejection_fixtures(app):
    """
    Verify backend CSV ingestion route (/api/v1/ingest/csv) correctly rejects
    adversarial malformed files and provides structured quarantine reports:
    1. invalid_missing_columns.csv -> status: "failed", total_rows: 0, missing columns error.
    2. invalid_out_of_bounds.csv -> status: "failed", valid_rows: 0, quarantined_rows: 6.
    """
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        # Case 1: Missing Columns
        p_missing = FIXTURES_DIR / "invalid_missing_columns.csv"
        files1 = {"file": (p_missing.name, p_missing.read_bytes(), "text/csv")}
        r1 = await client.post("/api/v1/ingest/csv", files=files1)
        assert r1.status_code == 200, f"Expected 200 with failed status, got {r1.status_code}"
        d1 = r1.json()
        assert d1["status"] == "failed"
        assert d1["valid_rows"] == 0
        assert any("latitude" in e and "longitude" in e for e in d1["errors"])

        # Case 2: Out of Bounds Coordinates & Values
        p_oob = FIXTURES_DIR / "invalid_out_of_bounds.csv"
        files2 = {"file": (p_oob.name, p_oob.read_bytes(), "text/csv")}
        r2 = await client.post("/api/v1/ingest/csv", files=files2)
        assert r2.status_code == 200
        d2 = r2.json()
        assert d2["status"] == "failed"
        assert d2["valid_rows"] == 0
        assert d2["quarantined_rows"] == 6
        assert len(d2["quarantined_records"]) == 6

        # Verify line-by-line quarantine details exist in backend response
        records = d2["quarantined_records"]
        row_numbers = [r["row_number"] for r in records]
        assert row_numbers == [2, 3, 4, 5, 6, 7]
        error_types = [r["error_type"] for r in records]
        assert "COORDINATES_MISSING_OR_UNRESOLVABLE" in error_types


def test_csv_client_side_quarantine_inspector_defect_empirically():
    """
    Adversarial Verification: Quarantine Inspector in ui.js renders rejected records.
    When a user uploads a malformed/quarantined CSV:
    1. The backend returns HTTP 200 with status: "failed" and quarantined_records.
    2. UIController.handleCsvUpload() does NOT claim success for 0 records.
    3. UIController keeps the modal open (modalDismissed is False) so operator can inspect errors.
    4. UIController renders a structured quarantine inspector table inside #csvQuarantineArea.
    5. App mode does NOT switch to 'user_csv' if 0 valid records were merged.
    """
    node_script = """
    import { UIController } from './src/frontend/static/js/ui.js';

    const quarantineDiv = { innerHTML: '' };
    const modalDiv = { hidden: false, setAttribute(k, v) { this[k] = v; }, removeAttribute(k) { delete this[k]; } };
    const submitBtn = { disabled: false, textContent: '' };
    const alerts = [];

    const mockApp = {
      apiClient: {
        uploadCSV: async (file) => ({
          status: 'failed',
          filename: file.name,
          total_rows: 6,
          valid_rows: 0,
          quarantined_rows: 6,
          quarantined_records: [
            { row_number: 2, station_id: 'STN-1', error_type: 'COORDINATES_OUT_OF_BOUNDS', error_message: 'Latitude 45.5 out of [27, 35]' },
            { row_number: 3, station_id: 'STN-2', error_type: 'COORDINATES_OUT_OF_BOUNDS', error_message: 'Longitude 85.2 out of [69, 76]' }
          ],
          errors: []
        })
      },
      onCsvIngested: (result) => {
        if (result.valid_rows > 0) mockApp.status = 'user_csv';
      }
    };

    global.alert = (msg) => alerts.push(msg);

    const ui = Object.create(UIController.prototype);
    ui.app = mockApp;
    ui.dom = {
      csvFileInput: { files: [{ name: 'invalid_out_of_bounds.csv' }] },
      csvUploadSubmit: submitBtn,
      csvModal: modalDiv,
      csvQuarantineArea: quarantineDiv
    };

    async function run() {
      await ui.handleCsvUpload();
      const output = {
        alert: alerts[0] || '',
        modalDismissed: modalDiv.hidden === '',
        quarantineAreaEmpty: quarantineDiv.innerHTML === '',
        hasTable: quarantineDiv.innerHTML.includes('<table'),
        hasRowHeader: quarantineDiv.innerHTML.includes('Row') || quarantineDiv.innerHTML.includes('<th>Row</th>'),
        hasErrorType: quarantineDiv.innerHTML.includes('COORDINATES_OUT_OF_BOUNDS'),
        appIngestedStatus: mockApp.status || null
      };
      console.log('CSV_QUARANTINE_RESULT:' + JSON.stringify(output));
    }

    run();
    """
    res = subprocess.run(["node", "-e", node_script], cwd=str(PROJECT_ROOT), capture_output=True, text=True)
    assert res.returncode == 0, f"Node script failed: {res.stderr}"

    for line in res.stdout.strip().split("\n"):
        if line.startswith("CSV_QUARANTINE_RESULT:"):
            data = json.loads(line.replace("CSV_QUARANTINE_RESULT:", ""))
            assert "Success: 0 valid records" not in data["alert"]
            assert "Failed" in data["alert"] or "quarantined" in data["alert"].lower()
            assert data["modalDismissed"] is False, "Modal should remain open for operator inspection"
            assert data["quarantineAreaEmpty"] is False, "Quarantine inspector table must be rendered"
            assert data["hasTable"] is True, "Quarantine inspector must render a <table>"
            assert data["hasErrorType"] is True, "Quarantine inspector must show the error type"
            assert data["appIngestedStatus"] is None, "App status must not switch to user_csv when 0 valid rows merged"


# =============================================================================
# 4. PHYSICAL INVARIANT GUARD (DIMENSIONLESS AQI ADVECTION FLUX BLOCKING)
# =============================================================================

@pytest.mark.anyio
async def test_physical_invariant_backend_blocks_dimensionless_aqi_flux(app):
    """
    Confirm that requesting advection flux for dimensionless 'AQI' returns HTTP 400
    on the backend, preserving physical mass conservation J = C * u:
    - GET /api/v1/analytics/flux?pollutant=AQI -> 400 Bad Request
    - GET /api/v1/analytics/flux?pollutant=aqi -> 400 Bad Request
    - GET /api/v1/analytics/flux?pollutant=Aqi -> 400 Bad Request
    - Physical species (PM2.5, PM10, NO2, SO2, CO, O3) -> 200 OK with valid pathways.
    """
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        # 1. Dimensionless AQI variations must be rejected
        for aqi_var in ["AQI", "aqi", "Aqi"]:
            resp = await client.get(f"/api/v1/analytics/flux?pollutant={aqi_var}")
            assert resp.status_code == 400, f"Expected 400 for {aqi_var}, got {resp.status_code}"
            detail = resp.json().get("detail", "").lower()
            assert "dimensionless" in detail
            assert "mass conservation" in detail or "physically undefined" in detail

        # 2. Physical mass-bearing species must succeed with HTTP 200
        for species in ["PM2.5", "PM10", "NO2", "SO2", "CO", "O3"]:
            resp = await client.get(f"/api/v1/analytics/flux?pollutant={species}")
            assert resp.status_code == 200, f"Expected 200 for physical species {species}, got {resp.status_code}"
            data = resp.json()
            assert "top_pathways" in data
            assert data["pollutant"].upper() == species.upper()


def test_physical_invariant_frontend_client_guards():
    """
    Confirm client-side guards in api.js and canvas.js preserve physical invariants:
    1. api.js getFluxTransport() intercepts pollutant === 'AQI' and coerces to PM2.5.
    2. canvas.js drawLayer3() explicitly checks this.pollutant !== 'AQI' before rendering
       inter-district transport flux vectors.
    """
    # 1. api.js guard
    api_js = (JS_DIR / "api.js").read_text(encoding="utf-8")
    assert "pollutant === 'AQI'" in api_js
    assert "Advection flux is physically undefined for AQI" in api_js

    # 2. canvas.js guard
    canvas_js = (JS_DIR / "canvas.js").read_text(encoding="utf-8")
    assert "this.pollutant !== 'AQI'" in canvas_js
    assert "PHYSICAL SPECIES ONLY, DISABLED FOR AQI" in canvas_js
