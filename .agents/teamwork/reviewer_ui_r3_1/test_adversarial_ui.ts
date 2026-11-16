import { scrubberReadout, buildWorkstationModel } from '../../../src/workstation/state';
import { ApiClient } from '../../../src/frontend/static/js/api';

console.log('=== STARTING ADVERSARIAL STRESS TEST: FRONTEND UI ===');
let assertionCount = 0;
let failureCount = 0;

function assert(condition: boolean, msg: string) {
  assertionCount++;
  if (!condition) {
    console.error(`[FAIL] ${msg}`);
    failureCount++;
  }
}

// --------------------------------------------------------------------------
// 1. Dynamic Timeline Advancement Stress Tests
// --------------------------------------------------------------------------
console.log('--- 1. Testing Scrubber Readout Boundary Conditions ---');

// Test standard 216h
const r216 = scrubberReadout(0, 0.0, '2026-11-01 00:00', 216);
assert(r216.detailLine === 'Hour 1/216 · Lerp α=0.00', 'Hour 0 of 216 readout match');

// Test extended 384h
const r384_last = scrubberReadout(383, 0.0, '2026-11-16 23:00', 384);
assert(r384_last.detailLine === 'Hour 384/384 · Lerp α=0.00', 'Hour 383 of 384 readout match');

// Test beyond bounds (hourIndex > totalHours)
const r_overflow = scrubberReadout(400, 0.5, '2026-11-16 23:00', 384);
assert(r_overflow.detailLine === 'Hour 384/384 · Lerp α=0.50', 'Clamped to 384 when hourIndex exceeds 384');

// Test negative bounds (hourIndex < 0)
const r_underflow = scrubberReadout(-5, 0.25, '2026-11-01 00:00', 384);
assert(r_underflow.detailLine === 'Hour 1/384 · Lerp α=0.25', 'Clamped to 1 when hourIndex is negative');

// Test massive 720h timeline (30-day extended)
const r720 = scrubberReadout(719, 0.99, '2026-11-30 23:00', 720);
assert(r720.detailLine === 'Hour 720/720 · Lerp α=0.99', 'Hour 719 of 720 readout match');

// Test single-hour or degenerate timeline totalHours <= 0
const r_zero = scrubberReadout(0, 0.0, '2026-11-01 00:00', 0);
assert(r_zero.detailLine === 'Hour 1/1 · Lerp α=0.00', 'Degenerate totalHours 0 safely handled as 1');

// Test buildWorkstationModel with 384 horizon values
const horizon384 = Array.from({ length: 384 }, (_, i) => 100 + (i % 50));
const model384 = buildWorkstationModel({
  pollutant: 'PM2.5',
  hourIndex: 380,
  lerpAlpha: 0.45,
  timestamp: '2026-11-16 20:00',
  playbackSpeed: '1x',
  isPlaying: false,
  layers: { surface: true, choropleth: true, wind: true, flux: true, stations: true },
  search: '',
  selected: null,
  stations: [],
  districtRows: [],
  maxPm25: 150,
  validHours: 380,
  totalHours: 384,
  horizon: horizon384,
  windSpeed: 2.5,
  windDirection: 180,
  readings: [],
  sectors: [],
  p75Threshold: 80,
  calmHours: 10,
  pooled: false,
  pooledStationCount: 1,
  exportMass: 100,
  importMass: 80,
  domesticShare: 0.6,
  inflowShare: 0.4,
  activeChevrons: 5,
  fluxLinks: [],
});

assert(model384.scrubber.detailLine === 'Hour 381/384 · Lerp α=0.45', 'Model with 384-hour horizon scales scrubber readout to 384');

// --------------------------------------------------------------------------
// 2. Cross-Border Fallback Coordinates Accuracy
// --------------------------------------------------------------------------
console.log('--- 2. Testing Cross-Border Anchor Cities Coordinates ---');
const client = new ApiClient('http://127.0.0.1:9000');

// Anchor cities coordinates ground truth
const EXPECTED_CITIES: Record<string, { lat: number; lon: number; aqi: number }> = {
  Amritsar: { lat: 31.634, lon: 74.872, aqi: 382 },
  Firozpur: { lat: 30.924, lon: 74.613, aqi: 345 },
  Jalandhar: { lat: 31.326, lon: 75.576, aqi: 360 },
  Ludhiana: { lat: 30.901, lon: 75.857, aqi: 395 },
  Bathinda: { lat: 30.211, lon: 74.945, aqi: 330 },
  'Delhi NCR': { lat: 28.613, lon: 77.209, aqi: 440 },
};

client.getCrossBorderCities().then((cities) => {
  assert(cities.length === 6, 'Exactly 6 anchor cities returned from fallback');
  for (const c of cities) {
    const exp = EXPECTED_CITIES[c.city_name || c.city];
    assert(exp !== undefined, `City ${c.city_name} found in expected map`);
    if (exp) {
      assert(Math.abs(c.latitude - exp.lat) < 0.01, `${c.city_name} latitude matches`);
      assert(Math.abs(c.longitude - exp.lon) < 0.01, `${c.city_name} longitude matches`);
      assert(c.aqi === exp.aqi, `${c.city_name} aqi distinct (${c.aqi})`);
      assert(c.pm25 !== undefined && c.pm25 > 0, `${c.city_name} PM2.5 present`);
      assert(c.pm10 !== undefined && c.pm10 > 0, `${c.city_name} PM10 present`);
    }
  }

  console.log(`=================================================================`);
  console.log(`ADVERSARIAL UI TEST SUMMARY:`);
  console.log(`Total Assertions Evaluated: ${assertionCount}`);
  console.log(`Passed:                    ${assertionCount - failureCount}`);
  console.log(`Failed:                    ${failureCount}`);
  console.log(`=================================================================`);
  if (failureCount > 0) process.exit(1);
});
