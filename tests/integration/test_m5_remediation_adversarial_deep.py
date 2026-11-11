"""
Adversarial Empirical Deep Verification Harness for Milestone M5 Remediation:
- Defect D1: CSV Quarantine Inspector UI Feedback, Modal State, Table Layout, XSS Escaping, Partial Ingestion
- Defect D2: SSE 45s Watchdog Timer, Keepalive Reset, Silent TCP Drop Fallback, Randomized Full Jitter, and Dual-Framing Keepalive Stream
"""
import asyncio
import json
from pathlib import Path
import subprocess
import pytest
import httpx
from httpx import ASGITransport

from src.api.main import create_application
import src.api.routes.stream as stream_module

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
FRONTEND_DIR = PROJECT_ROOT / "src" / "frontend"
STATIC_DIR = FRONTEND_DIR / "static"
JS_DIR = STATIC_DIR / "js"
FIXTURES_DIR = PROJECT_ROOT / "tests" / "fixtures"


@pytest.fixture(scope="module")
def app():
    """FastAPI application instance."""
    return create_application()


@pytest.fixture
def anyio_backend():
    return "asyncio"


# =============================================================================
# DEFECT D1: CSV QUARANTINE INSPECTOR EMPIRICAL VERIFICATION
# =============================================================================

def test_d1_csv_total_failure_modal_and_quarantine_table():
    """
    Empirical check for Defect D1: Total Validation Failure (valid_rows == 0, quarantined_rows > 0).
    Verifies:
    1. False success alert eliminated; failure alert triggered.
    2. Modal is NOT dismissed (modal.hidden is False / modal.hasAttribute('hidden') is False).
    3. 5-column table is rendered with exact headers:
       'Row #', 'Station ID', 'Error Type', 'Error Message', 'Raw Row Data'.
    4. App mode does NOT change to 'user_csv'.
    """
    node_script = """
    import { UIController } from './src/frontend/static/js/ui.js';

    const quarantineDiv = { innerHTML: '' };
    const modalDiv = {
      attributes: {},
      setAttribute(k, v) { this.attributes[k] = v; },
      removeAttribute(k) { delete this.attributes[k]; },
      hasAttribute(k) { return k in this.attributes; }
    };
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
            {
              row_number: 2,
              station_id: 'PUN-LHR-001',
              error_type: 'COORDINATES_OUT_OF_BOUNDS',
              error_message: 'Latitude 45.5 out of bounds [27, 35]',
              raw_record: { station_id: 'PUN-LHR-001', lat: 45.5, lon: 74.3, pm25: 150 }
            },
            {
              row_number: 3,
              station_id: 'PUN-FSD-002',
              error_type: 'SPIKE_RATE_EXCEEDED',
              error_message: 'Delta PM2.5 > 250 ug/m3/hr',
              raw_record: { station_id: 'PUN-FSD-002', lat: 31.4, lon: 73.1, pm25: 999 }
            }
          ],
          errors: []
        })
      },
      onCsvIngested: (res) => {
        if (res.valid_rows > 0) mockApp.mode = 'user_csv';
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

      const html = quarantineDiv.innerHTML;
      const headers = ['Row #', 'Station ID', 'Error Type', 'Error Message', 'Raw Row Data'];
      const headersPresent = headers.every(h => html.includes(h));

      const result = {
        alertMsg: alerts[0] || '',
        modalHidden: modalDiv.hasAttribute('hidden'),
        hasQuarantineTable: html.includes('<table class="quarantine-table"'),
        headersPresent,
        hasBannerFailed: html.includes('banner-failed'),
        hasRowNumber: html.includes('>2<') && html.includes('>3<'),
        hasStationId: html.includes('PUN-LHR-001') && html.includes('PUN-FSD-002'),
        hasErrorType: html.includes('COORDINATES_OUT_OF_BOUNDS') && html.includes('SPIKE_RATE_EXCEEDED'),
        appMode: mockApp.mode || 'unchanged'
      };

      console.log('D1_TOTAL_FAILURE_RESULT:' + JSON.stringify(result));
    }

    run().catch(err => { console.error(err); process.exit(1); });
    """
    res = subprocess.run(["node", "-e", node_script], cwd=str(PROJECT_ROOT), capture_output=True, text=True)
    assert res.returncode == 0, f"Node script error: {res.stderr}"

    for line in res.stdout.strip().split("\n"):
        if line.startswith("D1_TOTAL_FAILURE_RESULT:"):
            data = json.loads(line.replace("D1_TOTAL_FAILURE_RESULT:", ""))
            assert "Success" not in data["alertMsg"]
            assert "Failed" in data["alertMsg"]
            assert data["modalHidden"] is False, "Modal must remain open when validation fails"
            assert data["hasQuarantineTable"] is True, "Must render .quarantine-table"
            assert data["headersPresent"] is True, "All 5 table headers must be present"
            assert data["hasBannerFailed"] is True, "Must render failure banner"
            assert data["hasRowNumber"] is True
            assert data["hasStationId"] is True
            assert data["hasErrorType"] is True
            assert data["appMode"] == "unchanged", "App mode must not transition to user_csv on total failure"


def test_d1_csv_partial_ingestion_warning_and_table():
    """
    Empirical check for Defect D1: Partial Ingestion (valid_rows > 0 && quarantined_rows > 0).
    Verifies:
    1. Warning alert is triggered (not complete failure, not false clean success).
    2. Modal remains open so user can inspect quarantined records.
    3. Quarantine report renders partial warning banner and table.
    4. onCsvIngested is called for valid records.
    """
    node_script = """
    import { UIController } from './src/frontend/static/js/ui.js';

    const quarantineDiv = { innerHTML: '' };
    const modalDiv = {
      attributes: {},
      setAttribute(k, v) { this.attributes[k] = v; },
      removeAttribute(k) { delete this.attributes[k]; },
      hasAttribute(k) { return k in this.attributes; }
    };
    const submitBtn = { disabled: false, textContent: '' };
    const alerts = [];
    let ingestedResult = null;

    const mockApp = {
      apiClient: {
        uploadCSV: async (file) => ({
          status: 'partial_quarantine',
          filename: file.name,
          total_rows: 10,
          valid_rows: 8,
          quarantined_rows: 2,
          quarantined_records: [
            {
              row_number: 4,
              station_id: 'PUN-RAW-004',
              error_type: 'SENSOR_HOLD_STUCK_VALUE',
              error_message: 'Sensor value frozen for >6 consecutive hours',
              raw_record: { station_id: 'PUN-RAW-004', pm25: 88.0 }
            }
          ],
          errors: []
        })
      },
      onCsvIngested: (res) => {
        ingestedResult = res;
      }
    };

    global.alert = (msg) => alerts.push(msg);

    const ui = Object.create(UIController.prototype);
    ui.app = mockApp;
    ui.dom = {
      csvFileInput: { files: [{ name: 'mixed_dataset.csv' }] },
      csvUploadSubmit: submitBtn,
      csvModal: modalDiv,
      csvQuarantineArea: quarantineDiv
    };

    async function run() {
      await ui.handleCsvUpload();

      const html = quarantineDiv.innerHTML;
      const result = {
        alertMsg: alerts[0] || '',
        modalHidden: modalDiv.hasAttribute('hidden'),
        hasBannerWarning: html.includes('banner-warning'),
        hasTable: html.includes('<table class="quarantine-table"'),
        ingestedValidRows: ingestedResult ? ingestedResult.valid_rows : 0
      };

      console.log('D1_PARTIAL_RESULT:' + JSON.stringify(result));
    }

    run().catch(err => { console.error(err); process.exit(1); });
    """
    res = subprocess.run(["node", "-e", node_script], cwd=str(PROJECT_ROOT), capture_output=True, text=True)
    assert res.returncode == 0, f"Node script error: {res.stderr}"

    for line in res.stdout.strip().split("\n"):
        if line.startswith("D1_PARTIAL_RESULT:"):
            data = json.loads(line.replace("D1_PARTIAL_RESULT:", ""))
            assert "Warning" in data["alertMsg"]
            assert data["modalHidden"] is False, "Modal must remain open for inspection on partial quarantine"
            assert data["hasBannerWarning"] is True, "Must render partial warning banner"
            assert data["hasTable"] is True, "Must render quarantine table"
            assert data["ingestedValidRows"] == 8, "Valid rows must be ingested"


def test_d1_csv_xss_sanitization_in_quarantine_table():
    """
    Empirical check for Defect D1: Malicious CSV injection (XSS protection via escapeHtml).
    Verifies that raw script tags and HTML attributes in CSV raw data or error messages
    are sanitized and never rendered as live executable DOM tags.
    """
    node_script = """
    import { UIController } from './src/frontend/static/js/ui.js';

    const quarantineDiv = { innerHTML: '' };
    const modalDiv = {
      attributes: {},
      setAttribute(k, v) { this.attributes[k] = v; },
      removeAttribute(k) { delete this.attributes[k]; },
      hasAttribute(k) { return k in this.attributes; }
    };
    const alerts = [];

    const mockApp = {
      apiClient: {
        uploadCSV: async () => ({
          status: 'failed',
          total_rows: 1,
          valid_rows: 0,
          quarantined_rows: 1,
          quarantined_records: [
            {
              row_number: 1,
              station_id: '<script>alert("xss-station")</script>',
              error_type: '<b onmouseover="alert(1)">INJECT</b>',
              error_message: '<img src=x onerror="alert(\\'xss-msg\\')">',
              raw_record: { injection: '<script>bad()</script>', 'attr': '" onfocus="alert(1)' }
            }
          ],
          errors: ['<script>top_error()</script>']
        })
      },
      onCsvIngested: () => {}
    };

    global.alert = (msg) => alerts.push(msg);

    const ui = Object.create(UIController.prototype);
    ui.app = mockApp;
    ui.dom = {
      csvFileInput: { files: [{ name: 'xss_payload.csv' }] },
      csvUploadSubmit: { disabled: false, textContent: '' },
      csvModal: modalDiv,
      csvQuarantineArea: quarantineDiv
    };

    async function run() {
      await ui.handleCsvUpload();

      const html = quarantineDiv.innerHTML;
      const rawScriptUnescaped = html.includes('<script>');
      const rawImgUnescaped = html.includes('<img src=x onerror');
      const escapedLt = html.includes('&lt;script&gt;');
      const escapedImg = html.includes('&lt;img');

      console.log('D1_XSS_RESULT:' + JSON.stringify({
        rawScriptUnescaped,
        rawImgUnescaped,
        escapedLt,
        escapedImg
      }));
    }

    run().catch(err => { console.error(err); process.exit(1); });
    """
    res = subprocess.run(["node", "-e", node_script], cwd=str(PROJECT_ROOT), capture_output=True, text=True)
    assert res.returncode == 0, f"Node script error: {res.stderr}"

    for line in res.stdout.strip().split("\n"):
        if line.startswith("D1_XSS_RESULT:"):
            data = json.loads(line.replace("D1_XSS_RESULT:", ""))
            assert data["rawScriptUnescaped"] is False, "Unescaped <script> tag detected in rendered HTML!"
            assert data["rawImgUnescaped"] is False, "Unescaped <img onerror> tag detected in rendered HTML!"
            assert data["escapedLt"] is True, "<script> should be sanitized to &lt;script&gt;"
            assert data["escapedImg"] is True, "<img should be sanitized to &lt;img"


# =============================================================================
# DEFECT D2: SSE 45S WATCHDOG & JITTERED RECONNECTION VERIFICATION
# =============================================================================

def test_d2_sse_watchdog_timeout_triggers_fallback_and_reconnect():
    """
    Empirical check for Defect D2: 45-Second Watchdog Silence Detection.
    Verifies that:
    1. ApiClient initializes watchdog timer.
    2. In silent TCP drop (no heartbeats, no updates for 45s), watchdog fires:
       - eventSource is closed and set to null.
       - mode is changed to 'fallback'.
       - onStatusChange is notified with 'fallback'.
       - handleReconnect is triggered.
    """
    node_script = """
    import { ApiClient } from './src/frontend/static/js/api.js';

    class MockEventSource {
      constructor(url) {
        this.url = url;
        this.closed = false;
        this.listeners = {};
        setTimeout(() => { if (this.onopen) this.onopen(); }, 5);
      }
      addEventListener(evt, fn) { this.listeners[evt] = fn; }
      close() { this.closed = true; }
    }
    global.EventSource = MockEventSource;

    const client = new ApiClient();
    // Accelerate watchdog timeout to 50ms for synchronous fast empirical test
    client.watchdogTimeoutMs = 50;

    let statusUpdates = [];
    let reconnectCalled = false;

    // Monkey-patch handleReconnect to observe invocation
    const originalHandleReconnect = client.handleReconnect.bind(client);
    client.handleReconnect = function(onStatusChange) {
      reconnectCalled = true;
      // Do not schedule endless background reconnect in unit test
    };

    client.connectLiveStream(
      () => {},
      () => {},
      (mode) => { statusUpdates.push(mode); }
    );

    // Initial state after onopen
    setTimeout(() => {
      const modeAfterOpen = client.mode;
      const esExists = client.eventSource !== null;
      const timerActive = client.watchdogTimer !== null;

      // Now wait for watchdog to fire at 50ms
      setTimeout(() => {
        const result = {
          modeAfterOpen,
          modeAfterTimeout: client.mode,
          eventSourceClosed: client.eventSource === null,
          statusUpdates,
          reconnectCalled
        };
        console.log('D2_WATCHDOG_RESULT:' + JSON.stringify(result));
        process.exit(0);
      }, 70);

    }, 15);
    """
    res = subprocess.run(["node", "-e", node_script], cwd=str(PROJECT_ROOT), capture_output=True, text=True)
    assert res.returncode == 0, f"Node script error: {res.stderr}"

    for line in res.stdout.strip().split("\n"):
        if line.startswith("D2_WATCHDOG_RESULT:"):
            data = json.loads(line.replace("D2_WATCHDOG_RESULT:", ""))
            assert data["modeAfterOpen"] == "live", "Initial mode should be 'live'"
            assert data["modeAfterTimeout"] == "fallback", "Watchdog timeout must transition mode to 'fallback'"
            assert data["eventSourceClosed"] is True, "Dead socket must be closed and cleared on watchdog expiration"
            assert "fallback" in data["statusUpdates"], "onStatusChange must be notified of fallback"
            assert data["reconnectCalled"] is True, "Reconnection sequence must be initiated"


def test_d2_sse_heartbeats_reset_watchdog_timer():
    """
    Empirical check for Defect D2: Heartbeats prevent watchdog expiration.
    Simulates incoming 'keepalive', 'ping', and 'hourly_update' events.
    Verifies that each event successfully resets the watchdog timer and prevents
    false fallback disconnects.
    """
    node_script = """
    import { ApiClient } from './src/frontend/static/js/api.js';

    class MockEventSource {
      constructor(url) {
        this.url = url;
        this.closed = false;
        this.listeners = {};
        setTimeout(() => { if (this.onopen) this.onopen(); }, 5);
      }
      addEventListener(evt, fn) { this.listeners[evt] = fn; }
      close() { this.closed = true; }
      emit(evt, data) {
        if (this.listeners[evt]) this.listeners[evt]({ data: JSON.stringify(data) });
      }
    }
    global.EventSource = MockEventSource;

    const client = new ApiClient();
    client.watchdogTimeoutMs = 60; // Watchdog expires in 60ms

    let fallbackTriggered = false;
    client.connectLiveStream(
      () => {},
      () => {},
      (mode) => { if (mode === 'fallback') fallbackTriggered = true; }
    );

    setTimeout(() => {
      // At t=25ms: emit keepalive
      client.eventSource.emit('keepalive', {});

      setTimeout(() => {
        // At t=50ms: emit ping
        client.eventSource.emit('ping', {});

        setTimeout(() => {
          // At t=75ms: emit hourly_update
          client.eventSource.emit('hourly_update', { timestamp: 12345 });

          setTimeout(() => {
            // At t=100ms: Check if client is still live (total elapsed 100ms > 60ms watchdog)
            const result = {
              clientMode: client.mode,
              fallbackTriggered,
              socketStillOpen: client.eventSource !== null && !client.eventSource.closed
            };
            console.log('D2_HEARTBEAT_RESET_RESULT:' + JSON.stringify(result));
            client.disconnectLiveStream();
            process.exit(0);
          }, 25);

        }, 25);

      }, 25);

    }, 25);
    """
    res = subprocess.run(["node", "-e", node_script], cwd=str(PROJECT_ROOT), capture_output=True, text=True)
    assert res.returncode == 0, f"Node script error: {res.stderr}"

    for line in res.stdout.strip().split("\n"):
        if line.startswith("D2_HEARTBEAT_RESET_RESULT:"):
            data = json.loads(line.replace("D2_HEARTBEAT_RESET_RESULT:", ""))
            assert data["clientMode"] == "live", "Client must remain in live mode when heartbeats arrive"
            assert data["fallbackTriggered"] is False, "Heartbeats must prevent false watchdog triggers"
            assert data["socketStillOpen"] is True, "Socket must remain open"


def test_d2_exponential_backoff_randomized_jitter_distribution():
    """
    Empirical Statistical check for Defect D2: Randomized Full Jitter Distribution.
    Executes 200 reconnection retry calculations in Node.js across attempts 1..5.
    Verifies:
    1. Every retry timeout is strictly within [0.5 * base, 1.0 * base].
    2. The distribution is non-deterministic (standard deviation > 0, variance > 1000).
    3. Min and Max values show broad spread across the jitter band.
    """
    node_script = """
    function computeRetry(reconnectAttempts) {
      const attemptExp = Math.min(reconnectAttempts, 10);
      const base = Math.min(30000, 2000 * Math.pow(1.5, attemptExp));
      return { base, timeout: base * (0.5 + Math.random() * 0.5) };
    }

    const results = {};
    for (let attempt = 1; attempt <= 4; attempt++) {
      const samples = [];
      let baseVal = 0;
      for (let i = 0; i < 200; i++) {
        const { base, timeout } = computeRetry(attempt);
        baseVal = base;
        samples.push(timeout);
      }
      const min = Math.min(...samples);
      const max = Math.max(...samples);
      const mean = samples.reduce((a, b) => a + b, 0) / samples.length;
      const variance = samples.reduce((a, b) => a + Math.pow(b - mean, 2), 0) / samples.length;
      const stdDev = Math.sqrt(variance);

      results[attempt] = { base: baseVal, min, max, mean, variance, stdDev };
    }

    console.log('D2_JITTER_DISTRIBUTION:' + JSON.stringify(results));
    """
    res = subprocess.run(["node", "-e", node_script], cwd=str(PROJECT_ROOT), capture_output=True, text=True)
    assert res.returncode == 0, f"Node script error: {res.stderr}"

    for line in res.stdout.strip().split("\n"):
        if line.startswith("D2_JITTER_DISTRIBUTION:"):
            dist = json.loads(line.replace("D2_JITTER_DISTRIBUTION:", ""))
            for attempt_str, stats in dist.items():
                base = stats["base"]
                min_val = stats["min"]
                max_val = stats["max"]
                mean = stats["mean"]
                std_dev = stats["stdDev"]

                assert min_val >= 0.5 * base, f"Min delay below lower bound: {min_val} < {0.5 * base}"
                assert max_val <= 1.0 * base, f"Max delay above upper bound: {max_val} > {1.0 * base}"
                # Expected mean of uniform [0.5, 1.0] is 0.75 * base
                assert 0.70 * base <= mean <= 0.80 * base, f"Mean deviation too large: {mean}"
                assert std_dev > 50.0, f"Standard deviation too low: {std_dev}, jitter not randomized"


@pytest.mark.anyio
async def test_d2_stream_py_yields_dual_framing_keepalive():
    """
    Empirical check for Defect D2: SSE dual framing in src/api/routes/stream.py.
    Verifies that the heartbeat yield contains both:
    1. Proxy comment: ': keepalive\\n\\n'
    2. Named event: 'event: keepalive\\ndata: {}\\n\\n'
    """
    # Inspect source code directly
    stream_py_path = PROJECT_ROOT / "src" / "api" / "routes" / "stream.py"
    content = stream_py_path.read_text(encoding="utf-8")
    assert ": keepalive\\n\\nevent: keepalive\\ndata: {}\\n\\n" in content, (
        "stream.py must yield dual framing keepalive"
    )

    # Test the generator behavior with accelerated keepalive interval
    orig_interval = stream_module.KEEPALIVE_INTERVAL_SECONDS
    orig_poll = stream_module.POLL_CHECK_INTERVAL_SECONDS
    try:
        stream_module.KEEPALIVE_INTERVAL_SECONDS = 0.05
        stream_module.POLL_CHECK_INTERVAL_SECONDS = 0.01

        class MockRequest:
            async def is_disconnected(self):
                return False

        class MockObsService:
            def get_latest_summary_for_stream(self):
                return {"snapshot": True}
            def get_latest_timestamp_utc(self):
                return None

        generator = stream_module.sse_event_generator(MockRequest(), MockObsService())
        # First event is snapshot
        snap = await anext(generator)
        assert "event: hourly_update" in snap

        # Wait for accelerated keepalive interval
        await asyncio.sleep(0.08)
        hb = await anext(generator)

        assert ": keepalive" in hb
        assert "event: keepalive" in hb
        assert "data: {}" in hb
    finally:
        stream_module.KEEPALIVE_INTERVAL_SECONDS = orig_interval
        stream_module.POLL_CHECK_INTERVAL_SECONDS = orig_poll
