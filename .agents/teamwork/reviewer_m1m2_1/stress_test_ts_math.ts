import assert from 'node:assert';
import fs from 'node:fs';
import path from 'node:path';

// Normalizer imports
import {
  normalizeCentroid,
  centroidLngLat,
  normalizeWind,
  isStationBlacklisted,
  blacklistBannerText,
  countStationNetworks,
  isDistrictEstimated,
  shouldApplyDiagonalHatching,
  normalizeStation,
  normalizeDistrict,
} from '../../../src/domain/normalizer/dataNormalizer';

// Math imports
import {
  haversineDistance,
  forwardBearing,
  backBearing,
  angularDivergence,
  degreesToSector16,
  sector16ToDegrees,
  discreteGeodesicIdw,
  anisotropicIdw,
  calculateDistanceOpacity,
  polarToCartesianWind,
  cartesianToPolarWind,
  isAnemometerValid,
  isCalmWind,
  calculatePooledP75,
  calculateCpfRose,
  calculateRoseGeometry,
  calculateAdvectionFlux,
  calculateReceptorCoupling,
  calculateNetTransportBalance,
  calculateDistrictTransboundaryFlux,
  calculateBorderNormalFlux,
  calculateTransboundaryIndex,
  pepcCalculateAqi,
  pepcCompositeAqi,
  pepcGetCategory,
  pepcGetColor,
  pepcInterpolateColor,
  pepcInterpolateColorHex,
  temporalQcClean,
  checkCompleteness,
  subhourlyLerp,
  equirectangularProject,
  equirectangularUnproject,
  greedyLabelPlacement,
  checkAabbCollision,
} from '../../../src/domain/math';

console.log('=== STARTING ADVERSARIAL STRESS TEST SUITE ===');

let passCount = 0;
let testCount = 0;

function test(name: string, fn: () => void) {
  testCount++;
  try {
    fn();
    passCount++;
    console.log(`[PASS] ${name}`);
  } catch (err: any) {
    console.error(`[FAIL] ${name}: ${err.message}`);
    throw err;
  }
}

// -----------------------------------------------------------------------------
// TRAP 1: Centroid Inversion
// -----------------------------------------------------------------------------
test('Trap 1: Centroid inversion [lat, lon] -> [lon, lat]', () => {
  const rawCentroid: [number, number] = [31.5204, 74.3587]; // Lahore
  const normalized = normalizeCentroid(rawCentroid);
  assert.strictEqual(normalized[0], 74.3587, 'Longitude should be index 0');
  assert.strictEqual(normalized[1], 31.5204, 'Latitude should be index 1');
  assert.deepStrictEqual(centroidLngLat(rawCentroid), [74.3587, 31.5204]);
});

test('Trap 1: Edge cases (empty, null)', () => {
  assert.deepStrictEqual(normalizeCentroid([] as any), [0, 0]);
  assert.deepStrictEqual(normalizeCentroid(null as any), [0, 0]);
});

test('Trap 1: District normalization does not double-invert labels or boundary', () => {
  const mockDistrict: any = {
    id: 'test_district',
    name: 'Test District',
    centroid: [31.5, 74.3], // lat, lon
    label: [74.32, 31.52], // already lon, lat
    boundary: [[[ [74.0, 31.0], [74.5, 31.0], [74.5, 31.5], [74.0, 31.0] ]]],
    est: false,
    is_monitored: true,
  };
  const norm = normalizeDistrict(mockDistrict);
  assert.deepStrictEqual(norm.centroid, [74.3, 31.5]);
  assert.deepStrictEqual(norm.labelCoordinates, [74.32, 31.52]); // preserved!
  assert.strictEqual(norm.isEstimated, false);
});

// -----------------------------------------------------------------------------
// TRAP 2: Aerodrome Wind Null vs Calm vs Active
// -----------------------------------------------------------------------------
test('Trap 2: Aerodrome null wind (telemetry dropout)', () => {
  const w1 = normalizeWind(null, null);
  assert.strictEqual(w1.state, 'dropout');
  assert.strictEqual(w1.speed, null);
  assert.strictEqual(w1.u, null);

  const w2 = normalizeWind(NaN, 180);
  assert.strictEqual(w2.state, 'dropout');

  const w3 = normalizeWind(35.0, 180); // > 30 m/s out of range
  assert.strictEqual(w3.state, 'dropout');

  const w4 = normalizeWind(10.0, -10); // negative dir
  assert.strictEqual(w4.state, 'dropout');
});

test('Trap 2: Aerodynamic calm (0.0 <= ws < 0.50 m/s)', () => {
  const w0 = normalizeWind(0.0, 90.0);
  assert.strictEqual(w0.state, 'calm');
  assert.strictEqual(w0.speed, 0.0);
  assert.strictEqual(w0.u, 0.0);
  assert.strictEqual(w0.v, 0.0);

  const wCalm = normalizeWind(0.45, 180.0);
  assert.strictEqual(wCalm.state, 'calm');
  assert.strictEqual(wCalm.speed, 0.45);
  assert.strictEqual(wCalm.u, 0.0);
  assert.strictEqual(wCalm.v, 0.0);
});

test('Trap 2: Active wind vector (ws >= 0.50 m/s)', () => {
  // Wind from North (dir=0): blows TO South -> u=0, v=-ws
  const wNorth = normalizeWind(10.0, 0.0);
  assert.strictEqual(wNorth.state, 'active');
  assert.strictEqual(wNorth.speed, 10.0);
  assert.strictEqual(wNorth.u, 0.0);
  assert.strictEqual(wNorth.v, -10.0);

  // Wind from East (dir=90): blows TO West -> u=-ws, v=0
  const wEast = normalizeWind(5.0, 90.0);
  assert.strictEqual(wEast.state, 'active');
  assert.strictEqual(wEast.u, -5.0);
  assert.strictEqual(wEast.v, 0.0);
});

// -----------------------------------------------------------------------------
// TRAP 3: Station 172 Wazirabad Blacklist
// -----------------------------------------------------------------------------
test('Trap 3: Station 172 blacklist detection', () => {
  assert.strictEqual(isStationBlacklisted(172), true);
  assert.strictEqual(isStationBlacklisted('172'), true);
  assert.strictEqual(isStationBlacklisted('Wazirabad'), true);
  assert.strictEqual(isStationBlacklisted('Wazirabad AQMS'), true);
  assert.strictEqual(isStationBlacklisted('wazirabad station'), true);
  assert.strictEqual(isStationBlacklisted('Lahore Station'), false);
  assert.strictEqual(isStationBlacklisted(null), false);

  const banner = blacklistBannerText({ id: '172', name: 'Wazirabad AQMS' });
  assert.strictEqual(banner, 'ANEMOMETER BLACKLISTED (VANE OFFSET)');

  const wBlack = normalizeWind(5.0, 180.0, 172);
  assert.strictEqual(wBlack.state, 'blacklisted');
  assert.strictEqual(wBlack.blacklisted, true);
  assert.strictEqual(wBlack.speed, null);
  assert.strictEqual(wBlack.blacklistReason, 'ANEMOMETER BLACKLISTED (VANE OFFSET)');
});

// -----------------------------------------------------------------------------
// TRAP 4: Dynamic Station Inventory Breakdown
// -----------------------------------------------------------------------------
test('Trap 4: countStationNetworks counts dynamically', () => {
  const stationsPath = path.resolve('data/baseline/stations.json');
  const stations = JSON.parse(fs.readFileSync(stationsPath, 'utf-8'));
  const counts = countStationNetworks(stations);
  assert.strictEqual(counts.total, 79);
  assert.strictEqual(counts.fixed, 74);
  assert.strictEqual(counts.mobile, 5);

  // Dynamic test with arbitrary sub-array
  const partial = countStationNetworks([
    { name: 'Fixed A', mobile: false },
    { name: 'Fixed B', mobile: false },
    { name: 'Mobile Unit', mobile: true },
  ]);
  assert.strictEqual(partial.total, 3);
  assert.strictEqual(partial.fixed, 2);
  assert.strictEqual(partial.mobile, 1);
});

// -----------------------------------------------------------------------------
// TRAP 5: Unified Estimation Flag & Diagonal Cross-Hatching
// -----------------------------------------------------------------------------
test('Trap 5: Unified estimation flag handles est and is_monitored', () => {
  assert.strictEqual(isDistrictEstimated({ est: true } as any), true);
  assert.strictEqual(isDistrictEstimated({ is_monitored: false } as any), true);
  assert.strictEqual(isDistrictEstimated({ est: false, is_monitored: true } as any), false);
  assert.strictEqual(isDistrictEstimated({ isEstimated: true } as any), true);

  assert.strictEqual(shouldApplyDiagonalHatching({ est: true } as any), true);
  assert.strictEqual(shouldApplyDiagonalHatching({ is_monitored: false } as any), true);
  assert.strictEqual(shouldApplyDiagonalHatching({ est: false, is_monitored: true } as any), false);
});

// -----------------------------------------------------------------------------
// MATH ENGINE: Geodesy & Bearing
// -----------------------------------------------------------------------------
test('Math Geodesy: Haversine distance and bearings', () => {
  // Lahore (31.5204, 74.3587) to Gujranwala (32.1617, 74.1883)
  const dist = haversineDistance(31.5204, 74.3587, 32.1617, 74.1883);
  assert(dist > 70 && dist < 80, `Expected ~73km, got ${dist}`);

  const brg = forwardBearing(31.5204, 74.3587, 32.1617, 74.1883);
  assert(brg > 340 && brg < 350, `Expected ~346 deg NNW, got ${brg}`);

  const backBrg = backBearing(31.5204, 74.3587, 32.1617, 74.1883);
  const diff = Math.abs(angularDivergence(brg, (backBrg + 180) % 360));
  assert(diff < 1.0, `Back bearing divergence should be < 1 deg, got ${diff}`);

  assert.strictEqual(degreesToSector16(0), 0); // North
  assert.strictEqual(degreesToSector16(22.5), 1); // NNE
  assert.strictEqual(degreesToSector16(90), 4); // East
  assert.strictEqual(degreesToSector16(355), 0); // North (-5 deg)
});

// -----------------------------------------------------------------------------
// MATH ENGINE: IDW Geostatistics
// -----------------------------------------------------------------------------
test('Math IDW: Discrete Geodesic IDW with d0 clamping', () => {
  const nodes = [
    { coords: [31.5, 74.0] as [number, number], value: 100 },
    { coords: [31.5, 75.0] as [number, number], value: 200 },
  ];
  // Target midway
  const mid = discreteGeodesicIdw([31.5, 74.5], nodes);
  assert(mid !== null && Math.abs(mid - 150) < 0.1, `Midway IDW expected ~150, got ${mid}`);

  // Singularity clamp: target exactly at node 0
  const atNode = discreteGeodesicIdw([31.5, 74.0], nodes);
  assert(atNode !== null && atNode < 120, `Singularity clamp should prevent division by 0`);
});

// -----------------------------------------------------------------------------
// MATH ENGINE: Physical Dimension Guard & Advection Flux
// -----------------------------------------------------------------------------
test('Math Flux: Physical Dimension Guard strictly blocks AQI', () => {
  const source = { coords: [31.5, 74.0] as [number, number], value: 150, u: 5.0, v: 0.0 };
  const receptor: [number, number] = [31.5, 74.5]; // East of source

  // Physical pollutant PM2.5 works
  const fluxPM25 = calculateAdvectionFlux(source, receptor, 'PM2.5');
  assert(fluxPM25 !== null, 'PM2.5 flux must not be null');
  assert(fluxPM25.flux > 0, 'Flux must be positive');

  // DIMENSION GUARD: AQI must return null!
  const fluxAQI1 = calculateAdvectionFlux(source, receptor, 'AQI');
  assert.strictEqual(fluxAQI1, null, 'AQI must return null');

  const fluxAQI2 = calculateAdvectionFlux(source, receptor, 'aqi');
  assert.strictEqual(fluxAQI2, null, 'lowercase aqi must return null');

  const fluxAQI3 = calculateAdvectionFlux(source, receptor, ' AQI ');
  assert.strictEqual(fluxAQI3, null, 'whitespace AQI must return null');

  // Distance > 180 km returns null
  const farReceptor: [number, number] = [28.0, 71.0];
  assert.strictEqual(calculateAdvectionFlux(source, farReceptor, 'PM2.5'), null);
});

// -----------------------------------------------------------------------------
// MATH ENGINE: CPF Polar Wind Rose
// -----------------------------------------------------------------------------
test('Math CPF: 16-sector wind rose with small-sample suppression and calm exclusion', () => {
  const obs = [
    // 5 observations from North (sector 0) with high concentration
    { concentration: 200, speed: 2.0, direction: 0 },
    { concentration: 210, speed: 2.5, direction: 2 },
    { concentration: 220, speed: 1.8, direction: 358 },
    { concentration: 230, speed: 3.0, direction: 1 },
    { concentration: 240, speed: 2.2, direction: 0 },
    // 3 calm observations
    { concentration: 300, speed: 0.2, direction: 90 },
    { concentration: 310, speed: 0.3, direction: 90 },
    { concentration: 320, speed: 0.1, direction: 90 },
  ];

  const rose = calculateCpfRose(obs, 100);
  assert.strictEqual(rose.sectors.length, 16);
  // Sector 0 has only 5 samples (< 6), so it MUST be suppressed (null)!
  assert.strictEqual(rose.sectors[0], null, 'Sector 0 with 5 samples must be suppressed to null');
  assert(rose.calm_ratio > 0.3, 'Calm ratio should be computed');

  // Add 1 more sample to reach 6 samples for sector 0
  obs.push({ concentration: 250, speed: 2.0, direction: 0 });
  const rose2 = calculateCpfRose(obs, 100);
  assert(rose2.sectors[0] !== null, 'Sector 0 with 6 samples must NOT be suppressed');
  assert.strictEqual(rose2.sectors[0], 1.0, 'All 6 samples exceed threshold 100');
});

// -----------------------------------------------------------------------------
// MATH ENGINE: PEPC AQI Calculation & 500 Ceiling Clamp
// -----------------------------------------------------------------------------
test('Math PEPC: Piecewise linear calculation and 500 ceiling clamp', () => {
  // PM2.5 = 0 -> 0
  assert.strictEqual(pepcCalculateAqi('PM2.5', 0), 0);

  // PM2.5 = 15.0 -> exactly tier 50 (Good boundary)
  assert.strictEqual(pepcCalculateAqi('PM2.5', 15.0), 50);

  // PM2.5 = 35.0 -> tier 100 (Satisfactory boundary)
  assert.strictEqual(pepcCalculateAqi('PM2.5', 35.0), 100);

  // PM2.5 = 70.0 -> tier 150 (Moderate boundary)
  assert.strictEqual(pepcCalculateAqi('PM2.5', 70.0), 150);

  // PM2.5 = 350.0 -> tier 400 (Very Unhealthy boundary)
  assert.strictEqual(pepcCalculateAqi('PM2.5', 350.0), 400);

  // OPERATIONAL CEILING CLAMP: PM2.5 > 350 -> strictly 500!
  assert.strictEqual(pepcCalculateAqi('PM2.5', 351.0), 500);
  assert.strictEqual(pepcCalculateAqi('PM2.5', 500.0), 500);
  assert.strictEqual(pepcCalculateAqi('PM2.5', 1200.0), 500);

  // Composite AQI = max(PM2.5, PM10)
  assert.strictEqual(pepcCompositeAqi(120, 80), 120);
  assert.strictEqual(pepcCompositeAqi(90, 160), 160);

  // Color mappings
  assert.strictEqual(pepcGetCategory(45), 'Good');
  assert.strictEqual(pepcGetColor(45), '#00B050');
  assert.strictEqual(pepcGetCategory(500), 'Hazardous');
  assert.strictEqual(pepcGetColor(500), '#C00000');
});

// -----------------------------------------------------------------------------
// MATH ENGINE: Temporal QC (Spike Filter, Hold Filter, AQI Exemption)
// -----------------------------------------------------------------------------
test('Math QC: Temporal QC clean with spike and hold filters, AQI exemption', () => {
  // Series with 7-hour median spike at index 5
  const rawSeries = [20, 22, 21, 23, 20, 500, 22, 21, 20, 22];
  const [cleaned, spikes] = temporalQcClean(rawSeries, 35.0, 'PM2.5');
  assert.strictEqual(spikes, 1);
  assert.strictEqual(cleaned[5], null, 'Spike at index 5 should be scrubbed');

  // Series with 3-hour logger hold (sensor freeze) at index 4
  const holdSeries = [20, 25, 30, 30, 30, 35, 40];
  const [cleanedHold, _] = temporalQcClean(holdSeries, 35.0, 'PM2.5');
  assert.strictEqual(cleanedHold[4], null, 'Hold at index 4 should be scrubbed for physical pollutant');

  // AQI EXEMPTION: 3 identical AQI values are legitimate integer index states and NOT scrubbed!
  const aqiHoldSeries = [150, 160, 200, 200, 200, 210];
  const [cleanedAqi, _2] = temporalQcClean(aqiHoldSeries, 35.0, 'AQI');
  assert.strictEqual(cleanedAqi[4], 200, 'AQI hold should be EXEMPT from hold filter');

  // 75% Completeness rule
  const eightValues = [10, 20, null, 30, 40, 50, 60, null]; // 6/8 = 75%
  assert(checkCompleteness(eightValues, 0.75) !== null);

  const lowValues = [10, null, null, null, null, 50, 60, null]; // 3/8 = 37.5%
  assert.strictEqual(checkCompleteness(lowValues, 0.75), null);

  // Sub-hourly lerp
  assert.strictEqual(subhourlyLerp([10, 20], 0.5), 15);
  assert.strictEqual(subhourlyLerp([10, 20], 0.0), 10);
  assert.strictEqual(subhourlyLerp([10, 20], 1.0), 20);
});

// -----------------------------------------------------------------------------
// MATH ENGINE: Transboundary Index & Border Normals
// -----------------------------------------------------------------------------
test('Math Transboundary: 120km limit and border normal dot product', () => {
  // Border district within 120km with inflow wind
  const fluxInflow = calculateDistrictTransboundaryFlux(
    50.0, // 50 km from border
    [4, 5], // East, ESE sectors (from India)
    100.0, // concentration
    -3.0, // u < 0 (from East)
    0.0 // v = 0
  );
  assert(fluxInflow > 0, `Inflow flux should be positive, got ${fluxInflow}`);

  // Beyond 120km limit
  const fluxFar = calculateDistrictTransboundaryFlux(
    130.0,
    [4, 5],
    100.0,
    -3.0,
    0.0
  );
  assert.strictEqual(fluxFar, 0.0, 'Beyond 120km should yield 0 flux');

  // Normal dot product: Phi = u*nx + v*ny
  // Normal pointing into Punjab (nx=1, ny=0). Wind blowing into Punjab (u=2, v=0) -> Phi = 2.0
  const phi = calculateBorderNormalFlux(2.0, 0.0, 1.0, 0.0);
  assert.strictEqual(phi, 2.0);
});

// -----------------------------------------------------------------------------
// MATH ENGINE: Equirectangular Projection & Greedy AABB Collision
// -----------------------------------------------------------------------------
test('Math Projection: Equirectangular Plate Carree and Greedy AABB Placement', () => {
  const [x, y] = equirectangularProject(31.5204, 74.3587, 1200);
  assert(x > 0 && x < 1200);
  assert(y > 0 && y < 1200);

  const [lat, lon] = equirectangularUnproject(x, y, 1200);
  assert(Math.abs(lat - 31.5204) < 1e-4, 'Lat round trip mismatch');
  assert(Math.abs(lon - 74.3587) < 1e-4, 'Lon round trip mismatch');

  // AABB Collision check
  assert.strictEqual(checkAabbCollision([0, 0, 10, 10], [5, 5, 10, 10]), true);
  assert.strictEqual(checkAabbCollision([0, 0, 10, 10], [20, 20, 10, 10]), false);

  // Greedy label placement
  const labels = [
    { district_id: 'd1', text: 'District 1', anchor_x: 100, anchor_y: 100, width: 40, height: 14 },
    { district_id: 'd2', text: 'District 2', anchor_x: 100, anchor_y: 100, width: 40, height: 14 }, // colliding
  ];
  const placed = greedyLabelPlacement(labels);
  assert.strictEqual(placed.length, 2);
  assert(
    placed[0].placed_x !== placed[1].placed_x || placed[0].placed_y !== placed[1].placed_y,
    'Colliding labels must be offset to distinct positions'
  );
});

console.log(`\n=== STRESS TEST SUMMARY: ${passCount}/${testCount} TESTS PASSED ===\n`);
