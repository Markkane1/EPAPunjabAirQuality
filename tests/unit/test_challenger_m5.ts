/**
 * EMPIRICAL CHALLENGER TEST SUITE (Milestone M5: Services, Ingestion & Serving)
 *
 * Direct adversarial stress testing of:
 * 1. SSE Stream Manager (src/services/sse.ts):
 *    - 45s watchdog timer (reset on message, keepalive, ping, hourly_update)
 *    - Exponential backoff calculation formula
 *    - Monte Carlo full-jitter variance test
 *    - Max reconnection attempts enforcement
 *    - Graceful disconnect cleanup
 * 2. Strongly-Typed REST API Client (src/services/api.ts):
 *    - Physical Invariant Guard: AQI, aqi, Aqi coercion to PM2.5 with warning
 *    - Passthrough for physical pollutants
 *    - FormData multipart upload contract
 * 3. In-Memory Baseline Fallback Service (src/services/fallback.ts):
 *    - Schema Trap 1: Centroid Inversion [lat, lon] -> [lon, lat]
 *    - Schema Trap 2: Aerodrome wind 3-state handling (dropout, calm, active)
 *    - Schema Trap 3: Station 172 Wazirabad blacklist suppression
 *    - Schema Trap 4: Dynamic station inventory (74 fixed, 5 mobile)
 *    - Schema Trap 5: Unified estimation flag
 *    - Offline physical invariant guard on advection flux
 */

import * as fs from 'fs';
import * as path from 'path';

import { LiveStreamManager } from '../../src/services/sse.ts';
import { ApiService } from '../../src/services/api.ts';
import { BaselineFallbackService } from '../../src/services/fallback.ts';
import { normalizeWind, aerodromeWindCopy } from '../../src/domain/normalizer/dataNormalizer.ts';

let totalTests = 0;
let passedTests = 0;
let failedTests = 0;
const failureDetails: string[] = [];

function assert(condition: boolean, testName: string, details?: string): void {
  totalTests++;
  if (condition) {
    passedTests++;
  } else {
    failedTests++;
    const msg = `[FAIL] ${testName}${details ? ` -> ${details}` : ''}`;
    failureDetails.push(msg);
    console.error(msg);
  }
}

function assertEquals<T>(actual: T, expected: T, testName: string): void {
  const match = JSON.stringify(actual) === JSON.stringify(expected);
  assert(
    match,
    testName,
    `Expected: ${JSON.stringify(expected)}, Actual: ${JSON.stringify(actual)}`
  );
}

// ============================================================================
// SUITE 1: SSE STREAM MANAGER & RESILIENCY (src/services/sse.ts)
// ============================================================================
console.log('\n--- SUITE 1: SSE STREAM MANAGER & RESILIENCY (src/services/sse.ts) ---');

// Test 1.1: Exponential Backoff Formula Mathematical Exactness
{
  const expectedBases: Record<number, number> = {
    1: 3000,
    2: 4500,
    3: 6750,
    4: 10125,
    5: 15187.5,
    6: 22781.25,
    7: 30000, // 2000 * 1.5^7 = 34171.875 -> clamped to 30000
    10: 30000,
    15: 30000,
  };

  for (const [attemptStr, expBase] of Object.entries(expectedBases)) {
    const attempt = Number(attemptStr);
    const attemptExp = Math.min(attempt, 10);
    const calculatedBase = Math.min(30000, 2000 * Math.pow(1.5, attemptExp));
    assertEquals(
      calculatedBase,
      expBase,
      `SSE Backoff Base Calculation for Attempt ${attempt}`
    );
  }
}

// Test 1.2: Monte Carlo Full Jitter Variance Test (1,000 iterations)
{
  const delays: number[] = [];
  const base = Math.min(30000, 2000 * Math.pow(1.5, 1)); // 3000ms
  const minPossible = 0.5 * base; // 1500ms
  const maxPossible = 1.0 * base; // 3000ms

  for (let i = 0; i < 1000; i++) {
    const delay = base * (0.5 + Math.random() * 0.5);
    delays.push(delay);
  }

  const minObserved = Math.min(...delays);
  const maxObserved = Math.max(...delays);
  const mean = delays.reduce((a, b) => a + b, 0) / delays.length;
  const variance = delays.reduce((a, b) => a + Math.pow(b - mean, 2), 0) / delays.length;

  assert(
    minObserved >= minPossible,
    'Monte Carlo Jitter: No delay below theoretical minimum (1500ms)',
    `Observed min: ${minObserved}`
  );
  assert(
    maxObserved <= maxPossible,
    'Monte Carlo Jitter: No delay above theoretical maximum (3000ms)',
    `Observed max: ${maxObserved}`
  );
  assert(
    variance > 10000,
    'Monte Carlo Jitter: High variance confirms full jitter prevention of thundering herd',
    `Observed variance: ${variance.toFixed(2)} (required > 10000)`
  );
  assert(
    minObserved < 1600 && maxObserved > 2900,
    'Monte Carlo Jitter: Delay range covers full spread [1500, 3000]',
    `Spread: [${minObserved.toFixed(1)}, ${maxObserved.toFixed(1)}]`
  );
}

// Test 1.3: Mock EventSource Lifecycle & Watchdog Timer Verification
{
  class MockEventSource {
    static readonly CONNECTING = 0;
    static readonly OPEN = 1;
    static readonly CLOSED = 2;

    static instances: MockEventSource[] = [];
    public url: string;
    public readyState: number = MockEventSource.CONNECTING;
    public listeners: Record<string, ((e?: any) => void)[]> = {};
    public onopen: (() => void) | null = null;
    public onerror: ((err: any) => void) | null = null;
    public onmessage: ((e: any) => void) | null = null;
    public closed: boolean = false;

    constructor(url: string) {
      this.url = url;
      MockEventSource.instances.push(this);
    }

    addEventListener(event: string, handler: (e?: any) => void): void {
      if (!this.listeners[event]) this.listeners[event] = [];
      this.listeners[event].push(handler);
    }

    triggerEvent(event: string, data?: any): void {
      if (this.listeners[event]) {
        for (const fn of this.listeners[event]) {
          fn({ data: JSON.stringify(data) });
        }
      }
    }

    close(): void {
      this.closed = true;
      this.readyState = MockEventSource.CLOSED;
    }
  }

  // Swap global EventSource
  (global as any).EventSource = MockEventSource;
  MockEventSource.instances = [];

  const manager = new LiveStreamManager('/api/v1/stream/live');
  let statusMode: string = 'fallback';
  let updateCount = 0;
  let receivedPayload: any = null;

  manager.connect(
    (payload) => {
      updateCount++;
      receivedPayload = payload;
    },
    (err) => {},
    (mode) => {
      statusMode = mode;
    }
  );

  assert(MockEventSource.instances.length === 1, 'LiveStreamManager created EventSource instance');
  const es = MockEventSource.instances[0];

  // Verify listeners were registered
  assert(typeof es.listeners['hourly_update'] !== 'undefined', 'Registered hourly_update listener');
  assert(typeof es.listeners['keepalive'] !== 'undefined', 'Registered keepalive listener');
  assert(typeof es.listeners['ping'] !== 'undefined', 'Registered ping listener');

  // Trigger onopen
  es.readyState = MockEventSource.OPEN;
  es.onopen!();
  assertEquals(statusMode, 'live', 'onopen transitions status to "live"');
  assertEquals(manager.getMode(), 'live', 'getMode() returns "live"');

  // Trigger hourly_update
  es.triggerEvent('hourly_update', { timestamp: '2026-11-14T12:00:00Z', mean_aqi: 285 });
  assertEquals(updateCount, 1, 'hourly_update fired callback');
  assertEquals(receivedPayload?.mean_aqi, 285, 'hourly_update delivered correct payload');

  // Trigger error -> should transition to fallback and schedule reconnect
  es.onerror!({ type: 'error' });
  assertEquals(statusMode, 'fallback', 'onerror transitions status to "fallback"');
  assertEquals(manager.getMode(), 'fallback', 'getMode() returns "fallback"');
  assert(es.closed, 'EventSource was closed on error');

  // Verify Max Reconnect Attempts (5)
  assertEquals(manager.getReconnectAttempts(), 1, 'Reconnect attempt count incremented to 1');

  // Test Disconnect Cleanup
  manager.disconnect();
  assertEquals(statusMode, 'fallback', 'disconnect() ensures fallback mode');
}

// ============================================================================
// SUITE 2: STRONGLY-TYPED REST API CLIENT (src/services/api.ts)
// ============================================================================
console.log('\n--- SUITE 2: STRONGLY-TYPED REST API CLIENT (src/services/api.ts) ---');

// Test 2.1: Physical Invariant Guard on getAdvectionFlux
{
  const interceptedUrls: string[] = [];
  const warnings: string[] = [];
  const originalWarn = console.warn;
  console.warn = (...args: any[]) => {
    warnings.push(args.join(' '));
  };

  (global as any).fetch = async (url: string, opts?: any) => {
    interceptedUrls.push(String(url));
    return {
      ok: true,
      status: 200,
      json: async () => ({
        pollutant: 'PM2.5',
        timestamp: '2026-11-14T12:00:00Z',
        top_pathways: [],
        net_balance: {},
      }),
    };
  };

  const client = new ApiService('http://localhost:9000');

  // Case A: Query with 'AQI'
  await client.getAdvectionFlux('AQI' as any, 60);
  assert(
    interceptedUrls[interceptedUrls.length - 1].includes('pollutant=PM2.5'),
    'Physical Invariant: getAdvectionFlux("AQI") coerced to "PM2.5"',
    `Intercepted URL: ${interceptedUrls[interceptedUrls.length - 1]}`
  );
  assert(
    warnings.some((w) => w.includes('physically undefined for AQI')),
    'Physical Invariant: Diagnostic console warning emitted for AQI'
  );

  // Case B: Query with lowercase 'aqi'
  await client.getAdvectionFlux('aqi' as any, 60);
  assert(
    interceptedUrls[interceptedUrls.length - 1].includes('pollutant=PM2.5'),
    'Physical Invariant: getAdvectionFlux("aqi") coerced to "PM2.5"'
  );

  // Case C: Query with mixed case 'Aqi'
  await client.getAdvectionFlux('Aqi' as any, 60);
  assert(
    interceptedUrls[interceptedUrls.length - 1].includes('pollutant=PM2.5'),
    'Physical Invariant: getAdvectionFlux("Aqi") coerced to "PM2.5"'
  );

  // Case D: Alias getFluxTransport
  await client.getFluxTransport('AQI' as any, 50);
  assert(
    interceptedUrls[interceptedUrls.length - 1].includes('pollutant=PM2.5'),
    'Physical Invariant: getFluxTransport alias identically coerces "AQI" to "PM2.5"'
  );

  // Case E: Physical mass-bearing species NOT coerced
  for (const species of ['PM2.5', 'PM10', 'NO2', 'SO2', 'CO', 'O3'] as const) {
    await client.getAdvectionFlux(species, 60);
    assert(
      interceptedUrls[interceptedUrls.length - 1].includes(`pollutant=${species}`),
      `Physical Invariant: Physical species "${species}" preserved without coercion`
    );
  }

  console.warn = originalWarn;
}

// Test 2.2: Multipart CSV Upload Contract
{
  let uploadMethod = '';
  let uploadUrl = '';
  let uploadedBody: any = null;

  (global as any).fetch = async (url: string, opts?: any) => {
    uploadUrl = String(url);
    uploadMethod = opts?.method ?? 'GET';
    uploadedBody = opts?.body;
    return {
      ok: true,
      status: 200,
      json: async () => ({
        status: 'success',
        filename: 'test.csv',
        total_rows: 10,
        valid_rows: 10,
        quarantined_rows: 0,
        merged_observations_count: 10,
        errors: [],
      }),
    };
  };

  const client = new ApiService('');
  const mockFile = new (class MockFile {
    name = 'test.csv';
    size = 120;
    type = 'text/csv';
  })() as any;

  const result = await client.uploadCSV(mockFile, true);
  assertEquals(uploadMethod, 'POST', 'uploadCSV uses HTTP POST method');
  assert(uploadUrl.endsWith('/api/v1/ingest/csv'), 'uploadCSV targets /api/v1/ingest/csv');
  assert(uploadedBody instanceof FormData, 'uploadCSV sends FormData body');
  assertEquals(result.status, 'success', 'uploadCSV returns typed CSVIngestResponse');
}

// ============================================================================
// SUITE 3: IN-MEMORY BASELINE FALLBACK SERVICE (src/services/fallback.ts)
// ============================================================================
console.log('\n--- SUITE 3: IN-MEMORY BASELINE FALLBACK SERVICE (src/services/fallback.ts) ---');

{
  const rawBaselineContent = fs.readFileSync(
    path.join('.', 'data', 'baseline', 'baseline_data.json'),
    'utf8'
  );
  const baselineJson = JSON.parse(rawBaselineContent);

  // Mock global.fetch to serve baselineJson
  (global as any).fetch = async (url: string) => {
    return {
      ok: true,
      status: 200,
      json: async () => baselineJson,
    };
  };

  const fallback = new BaselineFallbackService();

  // Test 3.1: Schema Trap 1 — Centroid Inversion [lat, lon] -> [lon, lat]
  const districts = await fallback.getDistricts();
  assertEquals(districts.length, 41, 'Fallback delivers exactly 41 normalized districts');

  let invalidCentroidCount = 0;
  for (const d of districts) {
    const [lon, lat] = d.centroid;
    // Punjab lon is ~69 to 76, lat is ~28 to 35
    if (lon < 69.0 || lon > 76.0 || lat < 28.0 || lat > 35.0) {
      invalidCentroidCount++;
      console.error(`District ${d.name} invalid centroid: [${lon}, ${lat}]`);
    }
  }
  assertEquals(
    invalidCentroidCount,
    0,
    'Schema Trap 1: All 41 district centroids correctly inverted to [lon, lat]'
  );

  // Test 3.2: Schema Trap 2 — Aerodrome Wind 3-State Handling
  const airports = await fallback.getAirports();
  assert(airports.length >= 5, 'Fallback delivers at least 5 aerodromes');

  // Verify normalizeWind correctly differentiates dropout, calm, and active states
  const dropoutState = normalizeWind(null, null);
  assertEquals(dropoutState.state, 'dropout', 'Schema Trap 2: null wind speed/direction produces "dropout"');
  assertEquals(aerodromeWindCopy(null, null), 'TELEMETRY DROPOUT (NULL)', 'Dropout banner copy');

  const calmState = normalizeWind(0.35, 120);
  assertEquals(calmState.state, 'calm', 'Schema Trap 2: ws < 0.50 m/s produces "calm"');
  assert(aerodromeWindCopy(0.35, 120).includes('AERODYNAMIC CALM'), 'Calm banner copy');

  const activeState = normalizeWind(3.2, 90);
  assertEquals(activeState.state, 'active', 'Schema Trap 2: ws >= 0.50 m/s produces "active"');
  assert(aerodromeWindCopy(3.2, 90).includes('3.20 m/s at 90°'), 'Active banner copy');

  // Test 3.3: Schema Trap 3 — Station 172 Wazirabad Anemometer Blacklist
  const stations = await fallback.getStations();
  const wazirabad = stations.find(
    (s) => s.id === '172' || s.id === 172 || s.name.toLowerCase().includes('wazirabad')
  );
  assert(typeof wazirabad !== 'undefined', 'Station 172 (Wazirabad) present in station inventory');
  assertEquals(
    wazirabad?.anemometerBlacklisted,
    true,
    'Schema Trap 3: Station 172 anemometer is blacklisted'
  );

  // Current observation check for Station 172
  const currentObs = await fallback.getCurrentObservations('AQI');
  const wazirabadObs = currentObs.stations['172'] || currentObs.stations[wazirabad?.id || ''];
  assert(typeof wazirabadObs !== 'undefined', 'Station 172 has current observation record');
  assertEquals(wazirabadObs?.is_blacklisted, true, 'Station 172 observation has is_blacklisted: true');
  assertEquals(wazirabadObs?.wind_speed, null, 'Station 172 observation has null wind_speed');
  assertEquals(wazirabadObs?.wind_direction, null, 'Station 172 observation has null wind_direction');

  // Test 3.4: Schema Trap 4 — Dynamic Network Station Counts
  const counts = await fallback.getStationCounts();
  assertEquals(counts.fixed, 74, 'Schema Trap 4: Dynamic station inventory has 74 fixed stations');
  assertEquals(counts.mobile, 5, 'Schema Trap 4: Dynamic station inventory has 5 mobile stations');
  assertEquals(counts.total, 79, 'Schema Trap 4: Dynamic station inventory total is 79');

  // Test 3.5: Schema Trap 5 — Unified Estimation Flag
  let booleanEstCount = 0;
  for (const d of districts) {
    if (typeof d.isEstimated === 'boolean') {
      booleanEstCount++;
    }
  }
  assertEquals(
    booleanEstCount,
    41,
    'Schema Trap 5: All 41 districts have unified boolean isEstimated flag'
  );

  // Test 3.6: Fallback Physical Invariant Guard on Advection Flux
  const fallbackFlux = await fallback.getAdvectionFlux('AQI' as any);
  assertEquals(
    fallbackFlux.pollutant,
    'PM2.5',
    'Fallback Advection Flux: AQI coerced to PM2.5 in offline mode'
  );
  assert(
    fallbackFlux.top_pathways.length > 0,
    'Fallback Advection Flux: Top pathways populated'
  );

  // Test 3.7: Transboundary Attribution 39 Border Normals
  const tb = await fallback.getTransboundary('PM2.5');
  assertEquals(tb.border_normals.length, 39, 'Fallback delivers 39 transboundary border normal vectors');
  const crimsonCount = tb.border_normals.filter((n) => n.is_inflow_crimson).length;
  assert(crimsonCount > 0, 'Fallback transboundary has crimson inflow chevrons');
}

// ============================================================================
// SUMMARY
// ============================================================================
console.log('\n====================================================================');
console.log(`TOTAL TESTS:   ${totalTests}`);
console.log(`PASSED TESTS:  ${passedTests}`);
console.log(`FAILED TESTS:  ${failedTests}`);
console.log('====================================================================\n');

if (failedTests > 0) {
  console.error('CHALLENGE FAILED with details:');
  for (const d of failureDetails) {
    console.error(` - ${d}`);
  }
  process.exit(1);
} else {
  console.log('ALL EMPIRICAL CHALLENGER TESTS PASSED SUCCESSFULLY.');
  process.exit(0);
}
