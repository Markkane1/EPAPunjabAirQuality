/**
 * EMPIRICAL CHALLENGER TEST SUITE (Milestones M1-M2)
 *
 * Direct adversarial stress testing of dataNormalizer.ts and src/domain/math/:
 * 1. Centroid inversion edge cases (raw vs GeoJSON, string types, missing data, boundary preservation)
 * 2. Aerodrome wind dropouts (null vs calm < 0.50 m/s vs active kinematics, speed & angle clamps)
 * 3. Station 172 Wazirabad blacklist suppression (case insensitivity, types, name variants, math engine blocks)
 * 4. Physical dimension guard in flux.ts (AQI strictly null, PM2.5/PM10 working, distance & cone cutoffs)
 * 5. PEPC 500 ceiling clamp for PM2.5 > 350 ug/m3, continuous half-open intervals, 7h median spike filter,
 *    3h logger hold with i >= 2 guard and AQI exemption.
 */

import * as fs from 'fs';
import * as path from 'path';

// Target modules under test
import {
  centroidLngLat,
  isDistrictEstimated,
  isStationBlacklisted,
  normalizeAirport,
  normalizeCentroid,
  normalizeDistrict,
  normalizeStation,
  normalizeWind,
  aerodromeWindCopy,
  blacklistBannerText,
  countStationNetworks,
} from '../../src/domain/normalizer/dataNormalizer.ts';

import {
  calculateAdvectionFlux,
  calculateReceptorCoupling,
  calculateNetTransportBalance,
} from '../../src/domain/math/flux.ts';

import {
  pepcCalculateAqi,
  pepcCompositeAqi,
  pepcGetCategory,
  pepcGetColor,
  PEPC_BREAKPOINTS,
  AQI_TIERS,
} from '../../src/domain/math/pepc_aqi.ts';

import {
  temporalQcClean,
  checkCompleteness,
  subhourlyLerp,
} from '../../src/domain/math/qc.ts';

import {
  polarToCartesianWind,
  cartesianToPolarWind,
  isAnemometerValid,
  isCalmWind,
  windDirectionToBearing,
} from '../../src/domain/math/wind.ts';

import {
  haversineDistance,
  forwardBearing,
  angularDivergence,
} from '../../src/domain/math/geodesy.ts';

const PROJECT_ROOT = path.resolve('.');
const BASELINE_DIR = path.join(PROJECT_ROOT, 'data', 'baseline');

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

function assertCloseTo(
  actual: number | null | undefined,
  expected: number,
  delta: number = 1e-3,
  testName: string
): void {
  if (actual == null || isNaN(actual)) {
    assert(false, testName, `Actual is null or NaN, expected close to ${expected}`);
    return;
  }
  const diff = Math.abs(actual - expected);
  assert(
    diff <= delta,
    testName,
    `Expected: ${expected} ± ${delta}, Actual: ${actual} (diff: ${diff})`
  );
}

// =========================================================================
// TEST GROUP 1: Centroid Inversion Edge Cases
// =========================================================================
console.log('--- Testing Group 1: Centroid Inversion Edge Cases ---');

// 1.1 Basic numeric inversion [lat, lon] -> [lon, lat]
const c1 = normalizeCentroid([31.5204, 74.3587]);
assertEquals(c1, [74.3587, 31.5204], '1.1 normalizeCentroid inverts [lat, lon] to [lon, lat]');
assertEquals(centroidLngLat([31.5204, 74.3587]), [74.3587, 31.5204], '1.1 centroidLngLat alias matches');

// 1.2 String coordinates within array
const c2 = normalizeCentroid(['31.5204', '74.3587'] as any);
assertEquals(c2, [74.3587, 31.5204], '1.2 normalizeCentroid handles string-encoded numeric coords');

// 1.3 Null, undefined, empty array, single element edge cases
assertEquals(normalizeCentroid(null as any), [0, 0], '1.3 normalizeCentroid handles null');
assertEquals(normalizeCentroid(undefined as any), [0, 0], '1.3 normalizeCentroid handles undefined');
assertEquals(normalizeCentroid([] as any), [0, 0], '1.3 normalizeCentroid handles empty array');
assertEquals(normalizeCentroid([31.5] as any), [0, 0], '1.3 normalizeCentroid handles 1-element array');

// 1.4 Baseline Districts Dataset Verification (41 districts)
const districtsRaw = JSON.parse(
  fs.readFileSync(path.join(BASELINE_DIR, 'districts.json'), 'utf-8')
);
assert(districtsRaw.length === 41, '1.4 Baseline has exactly 41 districts');

for (const rawD of districtsRaw) {
  const normD = normalizeDistrict(rawD);
  const [lon, lat] = normD.centroid;

  // In Punjab: Lon is ~69 to 76.5, Lat is ~27.0 to 35.5
  assert(
    lon >= 69.0 && lon <= 76.5,
    `1.4 District ${normD.name} centroid longitude ${lon} within Punjab bounds [69, 76.5]`
  );
  assert(
    lat >= 27.0 && lat <= 35.5,
    `1.4 District ${normD.name} centroid latitude ${lat} within Punjab bounds [27, 35.5]`
  );

  // Raw centroid was [lat, lon]
  assert(
    rawD.centroid[0] === lat && rawD.centroid[1] === lon,
    `1.4 District ${normD.name} raw centroid [lat, lon] properly inverted`
  );

  // Label coordinates must NOT be inverted if present
  if (rawD.label && rawD.label.length >= 2) {
    const [lLon, lLat] = normD.labelCoordinates;
    assert(
      lLon === rawD.label[0] && lLat === rawD.label[1],
      `1.4 District ${normD.name} label coordinates preserved without inversion`
    );
    assert(
      lLon >= 69.0 && lLon <= 76.5,
      `1.4 District ${normD.name} label longitude within bounds`
    );
    assert(
      lLat >= 27.0 && lLat <= 35.5,
      `1.4 District ${normD.name} label latitude within bounds`
    );
  }

  // Boundary coordinates must be preserved
  assertEquals(normD.boundary, rawD.boundary ?? rawD.polys ?? [], `1.4 District ${normD.name} boundary preserved`);
}

// 1.5 Missing label fallback to normalized centroid [lon, lat]
const dNoLabel = normalizeDistrict({
  id: 'test_d',
  name: 'Test District',
  centroid: [31.5, 74.3],
} as any);
assertEquals(dNoLabel.centroid, [74.3, 31.5], '1.5 Missing label: centroid is [lon, lat]');
assertEquals(dNoLabel.labelCoordinates, [74.3, 31.5], '1.5 Missing label: labelCoordinates falls back to [lon, lat]');

// =========================================================================
// TEST GROUP 2: Aerodrome Wind Dropouts (null vs calm < 0.50 m/s vs active)
// =========================================================================
console.log('--- Testing Group 2: Aerodrome Wind Dropouts & Kinematics ---');

// 2.1 Telemetry Dropouts in normalizeWind (null, undefined, NaN, Inf, out of range)
const dropouts = [
  { s: null, d: 180, desc: 'null speed' },
  { s: 5.0, d: null, desc: 'null direction' },
  { s: null, d: null, desc: 'both null' },
  { s: undefined, d: 180, desc: 'undefined speed' },
  { s: 5.0, d: undefined, desc: 'undefined direction' },
  { s: NaN, d: 180, desc: 'NaN speed' },
  { s: 5.0, d: NaN, desc: 'NaN direction' },
  { s: Infinity, d: 180, desc: 'Infinity speed' },
  { s: -0.1, d: 180, desc: 'negative speed' },
  { s: -50.0, d: 180, desc: 'extreme negative speed' },
  { s: 30.1, d: 180, desc: 'speed exceeding 30.0 m/s physical limit' },
  { s: 99.9, d: 180, desc: 'sensor error code 99.9' },
  { s: 5.0, d: -1.0, desc: 'negative direction' },
  { s: 5.0, d: 360.5, desc: 'direction > 360' },
];

for (const tc of dropouts) {
  const res = normalizeWind(tc.s, tc.d);
  assert(res.state === 'dropout', `2.1 Dropout check: ${tc.desc} yields state 'dropout'`);
  assert(res.speed === null && res.direction === null && res.u === null && res.v === null,
    `2.1 Dropout check: ${tc.desc} nulls all vector fields`);
  assert(!res.blacklisted, `2.1 Dropout check: ${tc.desc} not blacklisted`);
}

// 2.1b UI Copy generator aerodromeWindCopy checks
// Standard null / undefined / NaN dropouts:
assertEquals(aerodromeWindCopy(null, 180), 'TELEMETRY DROPOUT (NULL)', '2.1b aerodromeWindCopy handles null speed');
assertEquals(aerodromeWindCopy(5.0, null), 'TELEMETRY DROPOUT (NULL)', '2.1b aerodromeWindCopy handles null direction');
assertEquals(aerodromeWindCopy(undefined, undefined), 'TELEMETRY DROPOUT (NULL)', '2.1b aerodromeWindCopy handles undefined');
assertEquals(aerodromeWindCopy(NaN, 180), 'TELEMETRY DROPOUT (NULL)', '2.1b aerodromeWindCopy handles NaN');

// Adversarial finding check: aerodromeWindCopy lacking bounds check on negative/unphysical speeds
const copyNegSpeed = aerodromeWindCopy(-0.10, 180);
const copyInfSpeed = aerodromeWindCopy(Infinity, 180);
const copyCode99 = aerodromeWindCopy(99.9, 180);
console.log(`    [Adversarial Probe] aerodromeWindCopy(-0.10, 180) -> "${copyNegSpeed}"`);
console.log(`    [Adversarial Probe] aerodromeWindCopy(Infinity, 180) -> "${copyInfSpeed}"`);
console.log(`    [Adversarial Probe] aerodromeWindCopy(99.9, 180) -> "${copyCode99}"`);
// Document: aerodromeWindCopy properly purges to 'dropout' with bounds check
assertEquals(copyNegSpeed, 'TELEMETRY DROPOUT (NULL)', '2.1b aerodromeWindCopy purges negative speed to dropout');
assertEquals(copyInfSpeed, 'TELEMETRY DROPOUT (NULL)', '2.1b aerodromeWindCopy purges Infinity to dropout');
assertEquals(copyCode99, 'TELEMETRY DROPOUT (NULL)', '2.1b aerodromeWindCopy purges out-of-range speed (99.9) to dropout');

// 2.2 Aerodynamic Calm (0.0 <= speed < 0.50 m/s)
const calmCases = [
  { s: 0.0, d: 0.0, desc: 'zero speed' },
  { s: 0.25, d: 90.0, desc: '0.25 m/s' },
  { s: 0.49, d: 180.0, desc: '0.49 m/s' },
  { s: 0.4999, d: 270.0, desc: '0.4999 m/s' },
];

for (const tc of calmCases) {
  const res = normalizeWind(tc.s, tc.d);
  assert(res.state === 'calm', `2.2 Calm check: ${tc.desc} yields state 'calm'`);
  assertEquals(res.u, 0.0, `2.2 Calm check: ${tc.desc} zero u-component`);
  assertEquals(res.v, 0.0, `2.2 Calm check: ${tc.desc} zero v-component`);
  assert(isCalmWind(tc.s), `2.2 isCalmWind(${tc.s}) returns true`);
  const copy = aerodromeWindCopy(tc.s, tc.d);
  assert(copy.includes('AERODYNAMIC CALM (< 0.50 m/s)'), `2.2 UI copy includes calm tag for ${tc.desc}`);
}

// 2.3 Active Advection Vectors (speed >= 0.50 m/s)
// Exactly 0.50 m/s must be active, not calm!
const atBoundary = normalizeWind(0.50, 0.0);
assert(atBoundary.state === 'active', '2.3 Exactly 0.50 m/s is active, not calm');
assert(!isCalmWind(0.50), '2.3 isCalmWind(0.50) is false');

// Meteorological Kinematics:
// Direction is FROM (0=North, 90=East, 180=South, 270=West).
// Kinematic vector points TO:
// 0 deg (wind from North) -> blows South -> u = 0, v = -ws
const wNorth = normalizeWind(10.0, 0.0);
assertEquals(wNorth.state, 'active', '2.3 North wind is active');
assertEquals(wNorth.u, 0.0, '2.3 North wind u = 0');
assertCloseTo(wNorth.v, -10.0, 1e-4, '2.3 North wind v = -10.0');

// 90 deg (wind from East) -> blows West -> u = -ws, v = 0
const wEast = normalizeWind(10.0, 90.0);
assertCloseTo(wEast.u, -10.0, 1e-4, '2.3 East wind u = -10.0');
assertEquals(wEast.v, 0.0, '2.3 East wind v = 0');

// 180 deg (wind from South) -> blows North -> u = 0, v = +ws
const wSouth = normalizeWind(10.0, 180.0);
assertEquals(wSouth.u, 0.0, '2.3 South wind u = 0');
assertCloseTo(wSouth.v, 10.0, 1e-4, '2.3 South wind v = +10.0');

// 270 deg (wind from West) -> blows East -> u = +ws, v = 0
const wWest = normalizeWind(10.0, 270.0);
assertCloseTo(wWest.u, 10.0, 1e-4, '2.3 West wind u = +10.0');
assertEquals(wWest.v, 0.0, '2.3 West wind v = 0');

// Upper boundary 30.0 m/s is active
const wMax = normalizeWind(30.0, 45.0);
assertEquals(wMax.state, 'active', '2.3 Upper bound 30.0 m/s is active');

// 2.4 Baseline Airports Dataset Stress Test (6 airports, 216 hours each)
const airportsRaw = JSON.parse(
  fs.readFileSync(path.join(BASELINE_DIR, 'airports.json'), 'utf-8')
);
assert(airportsRaw.length === 6, '2.4 Exactly 6 baseline aerodromes');

let totalAirportHours = 0;
let apDropouts = 0;
let apCalms = 0;
let apActives = 0;

for (const ap of airportsRaw) {
  const normAp = normalizeAirport(ap);
  assert(normAp.coordinates[0] >= 69.0 && normAp.coordinates[0] <= 76.5, `2.4 Airport ${normAp.icao} lon in bounds`);
  assert(normAp.coordinates[1] >= 27.0 && normAp.coordinates[1] <= 35.5, `2.4 Airport ${normAp.icao} lat in bounds`);

  const uArr = ap.u ?? [];
  const vArr = ap.v ?? [];
  assertEquals(uArr.length, 216, `2.4 Airport ${normAp.icao} has 216 u-values`);
  assertEquals(vArr.length, 216, `2.4 Airport ${normAp.icao} has 216 v-values`);

  for (let h = 0; h < 216; h++) {
    totalAirportHours++;
    const u = uArr[h];
    const v = vArr[h];

    if (u == null || v == null) {
      const res = normalizeWind(null, null);
      assertEquals(res.state, 'dropout', `2.4 Airport ${normAp.icao} hour ${h} null is dropout`);
      apDropouts++;
    } else {
      const [spd, dir] = cartesianToPolarWind(u, v);
      const res = normalizeWind(spd, dir);
      if (spd < 0.50) {
        assertEquals(res.state, 'calm', `2.4 Airport ${normAp.icao} hour ${h} speed ${spd} is calm`);
        apCalms++;
      } else {
        assertEquals(res.state, 'active', `2.4 Airport ${normAp.icao} hour ${h} speed ${spd} is active`);
        apActives++;
      }
    }
  }
}
assertEquals(totalAirportHours, 6 * 216, '2.4 All 1,296 airport hours evaluated');
console.log(`    Airport Hours Summary: ${apDropouts} dropouts, ${apCalms} calms, ${apActives} actives`);

// =========================================================================
// TEST GROUP 3: Station 172 Wazirabad Blacklist Suppression
// =========================================================================
console.log('--- Testing Group 3: Station 172 Wazirabad Blacklist Suppression ---');

// 3.1 Identifier Matching
const blacklistVariants = [
  172,
  '172',
  ' 172 ',
  'wazirabad',
  'Wazirabad',
  'WAZIRABAD',
  'Wazirabad AQMS',
  'wazirabad aqms',
  'pk_waz_001',
  'PK_WAZ_001',
  'Wazirabad Station',
  'Station 172 - Wazirabad',
];

for (const id of blacklistVariants) {
  assert(
    isStationBlacklisted(id),
    `3.1 isStationBlacklisted recognizes: ${JSON.stringify(id)}`
  );
}

// 3.2 Non-blacklisted stations must never trigger blacklist
const cleanStations = [
  171,
  '171',
  173,
  '173',
  'Lahore',
  'Multan',
  'Rawalpindi',
  'Faisalabad',
  'Bahawalpur',
  null,
  undefined,
];

for (const id of cleanStations) {
  assert(
    !isStationBlacklisted(id),
    `3.2 isStationBlacklisted rejects non-blacklisted: ${JSON.stringify(id)}`
  );
}

// 3.3 normalizeWind blacklist suppression
for (const id of [172, '172', 'Wazirabad', 'wazirabad aqms']) {
  const res = normalizeWind(12.5, 90.0, id);
  assertEquals(res.state, 'blacklisted', `3.3 normalizeWind state is 'blacklisted' for ${id}`);
  assert(res.blacklisted === true, `3.3 normalizeWind blacklisted flag true for ${id}`);
  assertEquals(res.blacklistReason, 'ANEMOMETER BLACKLISTED (VANE OFFSET)', `3.3 blacklistReason string for ${id}`);
  assert(res.speed === null && res.direction === null && res.u === null && res.v === null,
    `3.3 normalizeWind zeroes all vector coordinates for ${id}`);
}

// 3.4 Math module wind.ts blacklist suppression
assert(!isAnemometerValid(12.5, 90.0, 172), '3.4 isAnemometerValid rejects station 172');
assert(!isAnemometerValid(12.5, 90.0, 'Wazirabad'), '3.4 isAnemometerValid rejects Wazirabad');
assertEquals(polarToCartesianWind(12.5, 90.0, 172), null, '3.4 polarToCartesianWind returns null for station 172');
assertEquals(polarToCartesianWind(12.5, 90.0, 'wazirabad'), null, '3.4 polarToCartesianWind returns null for wazirabad');

// Non-blacklisted station 171 produces valid vector
const validUv = polarToCartesianWind(10.0, 180.0, 171);
assert(validUv !== null, '3.4 polarToCartesianWind succeeds for non-blacklisted station 171');

// 3.5 Warning banner text
assertEquals(
  blacklistBannerText({ id: 172, name: 'Wazirabad' }),
  'ANEMOMETER BLACKLISTED (VANE OFFSET)',
  '3.5 blacklistBannerText returns official warning banner'
);
assertEquals(
  blacklistBannerText({ id: 101, name: 'Lahore Mobile' }),
  null,
  '3.5 blacklistBannerText returns null for non-blacklisted station'
);

// 3.5b Adversarial Probe: normalizeStation input schema variations
const stWithId = normalizeStation({ id: 172, name: 'Station 172' } as any);
assert(stWithId.anemometerBlacklisted === true, '3.5b normalizeStation({ id: 172 }) sets anemometerBlacklisted = true');
assertEquals(stWithId.hasAnemometer, false, '3.5b normalizeStation({ id: 172 }) sets hasAnemometer = false');

// What if input uses { station_id: 172 } instead of { id: 172 }?
const stWithStationId = normalizeStation({ station_id: 172, name: 'Unknown Vane' } as any);
console.log(`    [Adversarial Probe] normalizeStation({ station_id: 172 }) -> id="${stWithStationId.id}", blacklisted=${stWithStationId.anemometerBlacklisted}`);
assertEquals(stWithStationId.anemometerBlacklisted, true, '3.5c normalizeStation blacklists station_id: 172');
assertEquals(stWithStationId.hasAnemometer, false, '3.5c normalizeStation disables anemometer for station_id: 172');

// 3.6 Baseline Stations Dataset Verification (79 stations)
const stationsRaw = JSON.parse(
  fs.readFileSync(path.join(BASELINE_DIR, 'stations.json'), 'utf-8')
);
assert(stationsRaw.length === 79, '3.6 Baseline has exactly 79 stations');

let blacklistedFound = 0;
for (const rawSt of stationsRaw) {
  const normSt = normalizeStation(rawSt);
  if (isStationBlacklisted(rawSt.id) || isStationBlacklisted(rawSt.name)) {
    blacklistedFound++;
    assert(normSt.anemometerBlacklisted === true, `3.6 Station ${rawSt.id} flagged anemometerBlacklisted`);
    assert(normSt.hasAnemometer === false, `3.6 Station ${rawSt.id} hasAnemometer set to false`);
  } else {
    assert(normSt.anemometerBlacklisted === false, `3.6 Clean station ${rawSt.id} not blacklisted`);
    assert(normSt.hasAnemometer === true, `3.6 Clean station ${rawSt.id} hasAnemometer true`);
  }
}
assert(blacklistedFound >= 1, `3.6 Wazirabad station identified in baseline inventory (count: ${blacklistedFound})`);

// 3.7 Dynamic Station Network Inventory (74 fixed, 5 mobile)
const counts = countStationNetworks(stationsRaw);
assertEquals(counts.fixed, 74, '3.7 Dynamic count: exactly 74 fixed stations');
assertEquals(counts.mobile, 5, '3.7 Dynamic count: exactly 5 mobile stations');
assertEquals(counts.total, 79, '3.7 Dynamic count: total is 79 stations');

// =========================================================================
// TEST GROUP 4: Physical Dimension Guard in flux.ts
// =========================================================================
console.log('--- Testing Group 4: Physical Dimension Guard in flux.ts ---');

// Source: Lahore [31.5204, 74.3587]
// Receptor: Gujranwala [32.1877, 74.1945] (~75 km north)
const lahore: [number, number] = [31.5204, 74.3587];
const gujranwala: [number, number] = [32.1877, 74.1945];

// Distance & Bearing from Lahore to Gujranwala
const dLhrGuj = haversineDistance(lahore[0], lahore[1], gujranwala[0], gujranwala[1]);
const brgLhrGuj = forwardBearing(lahore[0], lahore[1], gujranwala[0], gujranwala[1]);
console.log(`    Lahore -> Gujranwala: distance=${dLhrGuj.toFixed(2)} km, bearing=${brgLhrGuj.toFixed(2)}°`);

// Set wind pointing directly towards Gujranwala: theta_to = brgLhrGuj, speed = 5.0 m/s
// theta_to = atan2(u, v) -> u = speed * sin(brg), v = speed * cos(brg)
const radBrg = (brgLhrGuj * Math.PI) / 180.0;
const uFlow = 5.0 * Math.sin(radBrg);
const vFlow = 5.0 * Math.cos(radBrg);

// 4.1 MANDATORY PHYSICAL DIMENSION GUARD: strictly disabled for AQI
for (const aqiVariant of ['AQI', 'aqi', 'Aqi', ' aqi ', 'AQI ']) {
  const aqiFlux = calculateAdvectionFlux(
    lahore,
    gujranwala,
    aqiVariant,
    250.0, // Concentration/index value
    uFlow,
    vFlow
  );
  assertEquals(
    aqiFlux,
    null,
    `4.1 Dimension guard blocks pollutant '${aqiVariant}' from flux calculation`
  );
}

// 4.2 Physical mass concentrations PM2.5, PM10, NO2 MUST SUCCEED
for (const physPollutant of ['PM2.5', 'pm2.5', 'PM10', 'NO2', 'SO2', 'CO', 'O3']) {
  const physFlux = calculateAdvectionFlux(
    lahore,
    gujranwala,
    physPollutant,
    100.0, // ug/m3
    uFlow,
    vFlow
  );
  assert(physFlux !== null, `4.2 Physical pollutant '${physPollutant}' computes valid flux`);
  if (physFlux) {
    assert(physFlux.flux > 0.0, `4.2 Flux value positive for '${physPollutant}'`);
    assertCloseTo(physFlux.distance_km, dLhrGuj, 0.5, `4.2 Distance matches Haversine distance`);
    assertCloseTo(physFlux.divergence_deg, 0.0, 0.5, `4.2 Divergence is 0° when aligned`);
  }
}

// 4.3 Distance cutoff (MAX_TRANSPORT_DISTANCE_KM = 180.0 km)
// Multan is ~315 km away from Lahore
const multan: [number, number] = [30.1575, 71.5249];
const farFlux = calculateAdvectionFlux(
    lahore,
    multan,
    'PM2.5',
    100.0,
    uFlow,
    vFlow
);
assertEquals(farFlux, null, '4.3 Distance > 180 km (Lahore -> Multan ~315km) strictly returns null');

// Synthetic boundary test at 180.0 km:
// Create synthetic coords exactly 179.9 km and 180.1 km away
const kmPerDeg = (2 * Math.PI * 6371.0) / 360.0;
const lon179_9 = 179.9 / kmPerDeg;
const lon180_1 = 180.1 / kmPerDeg;
const d179_9 = haversineDistance(0, 0, 0, lon179_9);
const d180_1 = haversineDistance(0, 0, 0, lon180_1);
const flux179 = calculateAdvectionFlux([0, 0], [0, lon179_9], 'PM2.5', 100, 5, 0, 180.0);
const flux181 = calculateAdvectionFlux([0, 0], [0, lon180_1], 'PM2.5', 100, 5, 0, 180.0);
assert(flux179 !== null, `4.3 Boundary: 179.9 km (${d179_9.toFixed(2)} km) <= 180.0 km is valid`);
assertEquals(flux181, null, `4.3 Boundary: 180.1 km (${d180_1.toFixed(2)} km) > 180.0 km returns null`);

// 4.4 Calm wind cutoff (< 0.50 m/s)
const calmU = 0.2;
const calmV = 0.2; // speed = sqrt(0.08) = 0.283 m/s < 0.50
const calmFlux = calculateAdvectionFlux(lahore, gujranwala, 'PM2.5', 100.0, calmU, calmV);
assertEquals(calmFlux, null, '4.4 Calm wind (0.28 m/s < 0.50 m/s) strictly returns null');

// 4.5 Transport cone cutoff (CONE = 35.0 deg)
// When wind vector diverges by 34.9 deg (in cone) vs 35.1 deg (outside cone)
const fluxConePass = calculateAdvectionFlux(
  [0, 0],
  [1.0, 0], // bearing = 0 deg (North)
  'PM2.5',
  100.0,
  5.0 * Math.sin((34.0 * Math.PI) / 180), // 34 deg divergence
  5.0 * Math.cos((34.0 * Math.PI) / 180)
);
const fluxConeFail = calculateAdvectionFlux(
  [0, 0],
  [1.0, 0], // bearing = 0 deg (North)
  'PM2.5',
  100.0,
  5.0 * Math.sin((36.0 * Math.PI) / 180), // 36 deg divergence
  5.0 * Math.cos((36.0 * Math.PI) / 180)
);
assert(fluxConePass !== null, '4.5 34° divergence <= 35° cone passes');
assertEquals(fluxConeFail, null, '4.5 36° divergence > 35° cone returns null');

// 4.6 Mathematical formula verification
// Flux = C_a * w_s * cos(deltaTheta) * exp(-d / L_S)
// With C = 100, w_s = 5, deltaTheta = 0, d = 100 km, L_S = 100 km:
// Flux = 100 * 5 * 1.0 * exp(-1) = 500 * 0.36787944 = 183.9397
const formulaTestCoords: [number, number] = [0, 100.0 / 111.0]; // ~100 km
const fTestDist = haversineDistance(0, 0, formulaTestCoords[0], formulaTestCoords[1]);
const expectedFlux = 100.0 * 5.0 * Math.cos(0) * Math.exp(-fTestDist / 100.0);
const resFlux = calculateAdvectionFlux([0, 0], formulaTestCoords, 'PM2.5', 100.0, 5.0, 0.0);
assert(resFlux !== null, '4.6 Res flux is not null');
if (resFlux) {
  assertCloseTo(resFlux.flux, expectedFlux, 0.01, '4.6 Mathematical formulation verified against analytic solution');
}

// 4.7 Receptor Coupling Top-60 Truncation
const candidateLinks: any[] = [];
for (let i = 0; i < 100; i++) {
  candidateLinks.push({
    source_district: `src_${i}`,
    receptor_district: `rcv_${i}`,
    distance_km: 50.0,
    bearing_deg: 90.0,
    mean_flux: 100.0 - i, // 100, 99, 98, ...
  });
}
const coupled60 = calculateReceptorCoupling(candidateLinks, {}, 60);
assertEquals(coupled60.length, 60, '4.7 calculateReceptorCoupling strictly truncates to top 60 links');
// Verify descending sort order
for (let i = 0; i < coupled60.length - 1; i++) {
  assert(
    coupled60[i].score >= coupled60[i + 1].score,
    `4.7 Links sorted descending: link ${i} (${coupled60[i].score}) >= link ${i + 1} (${coupled60[i + 1].score})`
  );
}
// Verify isotropic omega fallback 0.25 when receptor CPF missing
assertEquals(coupled60[0].omega, 0.25, '4.7 Fallback omega is 0.25');

// 4.8 Net Transport Balance conservation
const sampleLinks = [
  { source_district: 'Lahore', receptor_district: 'Sheikhupura', score: 50.0 },
  { source_district: 'Sheikhupura', receptor_district: 'Gujranwala', score: 30.0 },
  { source_district: 'Gujranwala', receptor_district: 'Lahore', score: 20.0 },
];
const netBal = calculateNetTransportBalance(sampleLinks);
assertEquals(netBal['Lahore'], 50.0 - 20.0, '4.8 Lahore net balance = 30.0 (net exporter)');
assertEquals(netBal['Sheikhupura'], 30.0 - 50.0, '4.8 Sheikhupura net balance = -20.0 (net importer)');
assertEquals(netBal['Gujranwala'], 20.0 - 30.0, '4.8 Gujranwala net balance = -10.0 (net importer)');

const sumNet = Object.values(netBal).reduce((a, b) => a + b, 0);
assertCloseTo(sumNet, 0.0, 1e-6, '4.8 Closed network net balances sum exactly to zero');

// =========================================================================
// TEST GROUP 5: PEPC Calculations & Temporal QC Filters
// =========================================================================
console.log('--- Testing Group 5: PEPC Calculations & QC Filters ---');

// 5.1 PEPC 500 Ceiling Clamp for PM2.5 > 350 ug/m3
assertEquals(pepcCalculateAqi('PM2.5', 350.0), 400, '5.1 PM2.5 at exact top breakpoint 350.0 is 400 (Very Unhealthy boundary)');
assertEquals(pepcCalculateAqi('PM2.5', 350.1), 500, '5.1 PM2.5 at 350.1 clamped to 500 ceiling (Hazardous)');
assertEquals(pepcCalculateAqi('PM2.5', 500.0), 500, '5.1 PM2.5 at 500.0 clamped to 500 ceiling');
assertEquals(pepcCalculateAqi('PM2.5', 999.0), 500, '5.1 PM2.5 at 999.0 clamped to 500 ceiling');
assertEquals(pepcCalculateAqi('PM2.5', 10000.0), 500, '5.1 PM2.5 at 10000.0 clamped to 500 ceiling');

// 5.2 Continuous Half-Open Piecewise Linear Calculation across all PM2.5 intervals
// BP: [0, 15, 35, 70, 140, 250, 350]
// Tiers: [0, 50, 100, 150, 200, 300, 400, 500]
assertEquals(pepcCalculateAqi('PM2.5', 0.0), 0, '5.2 PM2.5 at 0.0 is 0');
assertEquals(pepcCalculateAqi('PM2.5', 7.5), 25, '5.2 PM2.5 at 7.5 midpoint is 25');
assertEquals(pepcCalculateAqi('PM2.5', 15.0), 50, '5.2 PM2.5 at 15.0 is exactly 50 (Good boundary)');
assertEquals(pepcCalculateAqi('PM2.5', 25.0), 75, '5.2 PM2.5 at 25.0 midpoint is 75');
assertEquals(pepcCalculateAqi('PM2.5', 35.0), 100, '5.2 PM2.5 at 35.0 is exactly 100 (Satisfactory boundary)');
assertEquals(pepcCalculateAqi('PM2.5', 52.5), 125, '5.2 PM2.5 at 52.5 midpoint is 125');
assertEquals(pepcCalculateAqi('PM2.5', 70.0), 150, '5.2 PM2.5 at 70.0 is exactly 150 (Moderate boundary)');
assertEquals(pepcCalculateAqi('PM2.5', 105.0), 175, '5.2 PM2.5 at 105.0 midpoint is 175');
assertEquals(pepcCalculateAqi('PM2.5', 140.0), 200, '5.2 PM2.5 at 140.0 is exactly 200 (Unhealthy Sensitive boundary)');
assertEquals(pepcCalculateAqi('PM2.5', 195.0), 250, '5.2 PM2.5 at 195.0 midpoint is 250');
assertEquals(pepcCalculateAqi('PM2.5', 250.0), 300, '5.2 PM2.5 at 250.0 is exactly 300 (Unhealthy boundary)');

// 5.3 Ceiling Clamp for other pollutants
assertEquals(pepcCalculateAqi('PM10', 550.1), 500, '5.3 PM10 > 550 clamped to 500');
assertEquals(pepcCalculateAqi('SO2', 1600.1), 500, '5.3 SO2 > 1600 clamped to 500');
assertEquals(pepcCalculateAqi('NO2', 580.1), 500, '5.3 NO2 > 580 clamped to 500');
assertEquals(pepcCalculateAqi('CO', 40.1), 500, '5.3 CO > 40 clamped to 500');
assertEquals(pepcCalculateAqi('O3', 550.1), 500, '5.3 O3 > 550 clamped to 500');

// Edge cases
assertEquals(pepcCalculateAqi('PM2.5', null), null, '5.3 Null concentration returns null');
assertEquals(pepcCalculateAqi('PM2.5', -5.0), null, '5.3 Negative concentration returns null');
assertEquals(pepcCalculateAqi('PM2.5', NaN), null, '5.3 NaN concentration returns null');
assertEquals(pepcCalculateAqi('UNRECOGNIZED_GAS', 50.0), null, '5.3 Unrecognized pollutant returns null');

// 5.4 Composite AQI: max(I_PM2.5, I_PM10)
assertEquals(pepcCompositeAqi(150, 80), 150, '5.4 Composite AQI max(150, 80) = 150');
assertEquals(pepcCompositeAqi(80, 220), 220, '5.4 Composite AQI max(80, 220) = 220');
assertEquals(pepcCompositeAqi(null, 150), 150, '5.4 Composite AQI with null PM2.5 takes PM10');
assertEquals(pepcCompositeAqi(200, null), 200, '5.4 Composite AQI with null PM10 takes PM2.5');
assertEquals(pepcCompositeAqi(null, null), null, '5.4 Composite AQI with both null returns null');

// 5.5 Category Names & Colors
assertEquals(pepcGetCategory(35), 'Good', '5.5 Category for 35 is Good');
assertEquals(pepcGetCategory(75), 'Satisfactory', '5.5 Category for 75 is Satisfactory');
assertEquals(pepcGetCategory(125), 'Moderate', '5.5 Category for 125 is Moderate');
assertEquals(pepcGetCategory(175), 'Unhealthy (Sensitive)', '5.5 Category for 175 is Unhealthy (Sensitive)');
assertEquals(pepcGetCategory(250), 'Unhealthy', '5.5 Category for 250 is Unhealthy');
assertEquals(pepcGetCategory(350), 'Very Unhealthy', '5.5 Category for 350 is Very Unhealthy');
assertEquals(pepcGetCategory(450), 'Hazardous', '5.5 Category for 450 is Hazardous');
assertEquals(pepcGetCategory(500), 'Hazardous', '5.5 Category for 500 is Hazardous');

assertEquals(pepcGetColor(45), '#00B050', '5.5 Color for 45 is #00B050 (Good green)');
assertEquals(pepcGetColor(500), '#C00000', '5.5 Color for 500 is #C00000 (Hazardous maroon)');

// 5.6 7-Hour Rolling Window Median Spike Filter
// Threshold: v_i > 4 * M_i AND v_i > 3 * refLimit
// Ref limit for PM2.5 = 35 ug/m3 -> 3 * refLimit = 105 ug/m3
const refPM25 = 35.0;

// Test with an obvious spike:
// Baseline at 50, isolated spike at 600 (> 4*50=200 and > 105)
const spikeSeries = [50, 50, 50, 50, 600, 50, 50, 50];
const [cleanedSpikes, nSpikes] = temporalQcClean(spikeSeries, refPM25, 'PM2.5');
assertEquals(nSpikes, 1, '5.6 Exactly 1 spike detected');
assertEquals(cleanedSpikes[4], null, '5.6 Spike value at index 4 replaced with null');
assertEquals(cleanedSpikes[0], 50, '5.6 Non-spike index 0 preserved');
assertEquals(cleanedSpikes[5], 50, '5.6 Non-spike index 5 preserved');

// Test elevated non-spike value (180 > 105, but 180 < 4*50=200):
const nonSpikeSeries = [50, 50, 50, 50, 180, 50, 50, 50];
const [cleanedNonSpikes, nNonSpikes] = temporalQcClean(nonSpikeSeries, refPM25, 'PM2.5');
assertEquals(nNonSpikes, 0, '5.6 Non-spike (180 < 4*50) not flagged');
assertEquals(cleanedNonSpikes[4], 180, '5.6 Value 180 preserved');

// Test high smog episode where median is elevated (e.g. 350 ug/m3):
// M_i = 350 -> 4 * M_i = 1400. Value 450 is NOT a spike!
const smogSeries = [350, 360, 340, 350, 450, 350, 360, 350];
const [cleanedSmog, nSmogSpikes] = temporalQcClean(smogSeries, refPM25, 'PM2.5');
assertEquals(nSmogSpikes, 0, '5.6 High episode values during smog not false-flagged as spikes');
assertEquals(cleanedSmog[4], 450, '5.6 Smog episode value 450 preserved');

// 5.7 3-Hour Logger Hold (Sensor Freeze) Filter with Index Guard (i >= 2)
// Physical pollutant: 'PM2.5'
// Sequence: [10, 20, 50, 50, 50, 60] -> at index 4, three consecutive identical values: [50, 50, 50]
const holdSeries = [10, 20, 50, 50, 50, 60];
const [cleanedHold, _] = temporalQcClean(holdSeries, refPM25, 'PM2.5');
assertEquals(cleanedHold[0], 10, '5.7 Hold index 0 preserved');
assertEquals(cleanedHold[1], 20, '5.7 Hold index 1 preserved');
assertEquals(cleanedHold[2], 50, '5.7 Hold index 2 preserved');
assertEquals(cleanedHold[3], 50, '5.7 Hold index 3 preserved');
assertEquals(cleanedHold[4], null, '5.7 Hold index 4 (3rd consecutive identical) set to null');
assertEquals(cleanedHold[5], 60, '5.7 Index 5 after hold preserved');

// Verify Index Guard i >= 2:
// Sequence with 2 identical values at indices 0 and 1: [50, 50, 60, 70]
const shortHold = [50, 50, 60, 70];
const [cleanedShort, __] = temporalQcClean(shortHold, refPM25, 'PM2.5');
assertEquals(cleanedShort[0], 50, '5.7 Index guard: index 0 never flagged');
assertEquals(cleanedShort[1], 50, '5.7 Index guard: index 1 never flagged (needs 3 consecutive)');

// 5.8 CRITICAL AQI EXEMPTION from 3-Hour Logger Hold:
// For pollutant 'AQI', identical consecutive values are genuine and MUST NOT be purged!
const aqiHoldSeries = [150, 150, 150, 150, 150, 150];
const [cleanedAqiHold, ___] = temporalQcClean(aqiHoldSeries, refPM25, 'AQI');
assertEquals(cleanedAqiHold[2], 150, '5.8 AQI Exemption: index 2 preserved');
assertEquals(cleanedAqiHold[3], 150, '5.8 AQI Exemption: index 3 preserved (not null!)');
assertEquals(cleanedAqiHold[4], 150, '5.8 AQI Exemption: index 4 preserved (not null!)');
assertEquals(cleanedAqiHold[5], 150, '5.8 AQI Exemption: index 5 preserved (not null!)');

// Case-insensitive check: 'aqi'
const [cleanedAqiLower, ____] = temporalQcClean(aqiHoldSeries, refPM25, 'aqi');
assertEquals(cleanedAqiLower[4], 150, '5.8 AQI Exemption works with lowercase pollutant');

// 5.9 Step 0: Zero and negative purge
const badInputs = [-10, 0, 0.0, NaN, 50, -0.001];
const [cleanedZeros, _____] = temporalQcClean(badInputs, refPM25, 'PM2.5');
assertEquals(cleanedZeros[0], null, '5.9 Negative value -10 purged to null');
assertEquals(cleanedZeros[1], null, '5.9 Zero purged to null');
assertEquals(cleanedZeros[2], null, '5.9 0.0 purged to null');
assertEquals(cleanedZeros[3], null, '5.9 NaN purged to null');
assertEquals(cleanedZeros[4], 50, '5.9 Valid 50 preserved');
assertEquals(cleanedZeros[5], null, '5.9 -0.001 purged to null');

// 5.10 75% Completeness Rule
// Over 24 hours: round(0.75 * 24) = 18 required valid hours
const full24 = new Array(24).fill(100);
assertEquals(checkCompleteness(full24), 100, '5.10 24/24 hours valid -> complete');

// Exactly 18 valid hours (18/24 = 75%)
const valid18 = [...new Array(18).fill(100), ...new Array(6).fill(null)];
assertEquals(checkCompleteness(valid18), 100, '5.10 18/24 hours (75%) valid -> complete');

// 17 valid hours (17/24 = 70.8% < 75%)
const valid17 = [...new Array(17).fill(100), ...new Array(7).fill(null)];
assertEquals(checkCompleteness(valid17), null, '5.10 17/24 hours (<75%) valid -> null');

// 5.11 Subhourly Lerp
const lerpSeries = [10.0, 20.0, 30.0, 40.0];
assertCloseTo(subhourlyLerp(lerpSeries, 0.0), 10.0, 1e-4, '5.11 Lerp at 0.0');
assertCloseTo(subhourlyLerp(lerpSeries, 1.5), 25.0, 1e-4, '5.11 Lerp at 1.5 midpoint of 20 and 30 is 25');
assertCloseTo(subhourlyLerp(lerpSeries, 2.25), 32.5, 1e-4, '5.11 Lerp at 2.25 is 32.5');
assertCloseTo(subhourlyLerp(lerpSeries, 3.0), 40.0, 1e-4, '5.11 Lerp at 3.0');
// Boundary clamping
assertCloseTo(subhourlyLerp(lerpSeries, -1.0), 10.0, 1e-4, '5.11 Lerp clamps negative position');
assertCloseTo(subhourlyLerp(lerpSeries, 10.0), 40.0, 1e-4, '5.11 Lerp clamps past-end position');

// =========================================================================
// FINAL EMPIRICAL SUMMARY & REPORTING
// =========================================================================
console.log('\n=================================================================');
console.log(`EMPIRICAL CHALLENGER VERIFICATION SUMMARY:`);
console.log(`Total Assertions Evaluated: ${totalTests}`);
console.log(`Passed:                    ${passedTests}`);
console.log(`Failed:                    ${failedTests}`);
console.log('=================================================================');

if (failedTests > 0) {
  console.error('\nFAILURES RECORDED:');
  for (const f of failureDetails) {
    console.error(f);
  }
  process.exit(1);
} else {
  console.log('\nALL EMPIRICAL CHALLENGES PASSED PERFECTLY (0 FAILURES).');
  process.exit(0);
}
