/**
 * Empirical Adversarial Physics and Mathematical Invariant Stress-Test Suite (TypeScript).
 * Challenger 2 Verification Gate.
 * Covers:
 * 1. Station 172 Blacklist Stress-Test (TypeScript)
 * 2. T1 Singularity Clamp (d = 0)
 * 3. T6 Physical Dimension Guard (pollutant = 'AQI')
 * 4. T9 Scale Boundaries (PM2.5 @ 350.0, 350.1, 500.0, 5000.0)
 * 5. T10 Temporal QC (3h hold at indices 0, 1, 2 and AQI exemption)
 */

import {
  isStationBlacklisted as isWindBlacklisted,
  isAnemometerValid,
  polarToCartesianWind,
  blendWinds,
} from '../../src/domain/math/wind.ts';
import {
  isStationBlacklisted as isNormalizerBlacklisted,
  blacklistBannerText,
  normalizeWind,
} from '../../src/domain/normalizer/dataNormalizer.ts';
import { haversineDistance } from '../../src/domain/math/geodesy.ts';
import {
  discreteGeodesicIdw,
  discreteGeodesicIdwVector,
} from '../../src/domain/math/idw.ts';
import { calculateAdvectionFlux } from '../../src/domain/math/flux.ts';
import {
  pepcCalculateAqi,
  pepcCompositeAqi,
  pepcGetCategory,
} from '../../src/domain/math/pepc_aqi.ts';
import { temporalQcClean } from '../../src/domain/math/qc.ts';

let passed = 0;
let failed = 0;

function assert(condition: boolean, msg: string) {
  if (!condition) {
    console.error(`[FAIL] ${msg}`);
    failed++;
    throw new Error(`Assertion failed: ${msg}`);
  } else {
    passed++;
  }
}

console.log('=================================================================');
console.log('CHALLENGER 2: ADVERSARIAL PHYSICS & INVARIANT STRESS TEST (TS)');
console.log('=================================================================\n');

// -------------------------------------------------------------
// Objective 1: Station 172 Blacklist Stress Test
// -------------------------------------------------------------
console.log('>>> [OBJECTIVE 1] Station 172 Blacklist Stress Test (TypeScript)');
const testVariations = [
  172,
  '172',
  ' 172 ',
  'wazirabad',
  'WAZIRABAD',
  'Wazirabad',
  'Wazirabad AQMS',
  'WAZIRABAD AQMS',
  'pk_waz_001',
  'PK_WAZ_001',
  'Pk_Waz_001',
  'wazirabad station',
  'WAZIRABAD STATION',
];

for (const id of testVariations) {
  assert(isWindBlacklisted(id) === true, `isWindBlacklisted failed for ${id}`);
  assert(isNormalizerBlacklisted(id) === true, `isNormalizerBlacklisted failed for ${id}`);
  assert(isAnemometerValid(5.0, 180.0, id) === false, `isAnemometerValid must be false for ${id}`);
  assert(polarToCartesianWind(5.0, 180.0, id) === null, `polarToCartesianWind must return null for ${id}`);

  const norm = normalizeWind(5.0, 180.0, id);
  assert(norm.state === 'blacklisted', `normalizeWind state must be blacklisted for ${id}`);
  assert(norm.blacklisted === true, `normalizeWind blacklisted flag must be true for ${id}`);
  assert(norm.speed === null && norm.direction === null && norm.u === null && norm.v === null, `all vectors must be null for ${id}`);
  assert(norm.blacklistReason?.includes('BLACKLISTED') === true, `blacklistReason missing for ${id}`);

  const banner = blacklistBannerText({ id });
  assert(banner === 'ANEMOMETER BLACKLISTED (VANE OFFSET)', `blacklistBannerText failed for ${id}`);
}

// Wind blending exclusion test
{
  const target: [number, number] = [32.0, 74.0];
  const sources = [
    { station_name: '172', speed: 25.0, direction: 90.0, coords: [32.0, 74.0] as [number, number] },
    { station_name: 'clean_station', speed: 5.0, direction: 180.0, coords: [32.0, 74.0] as [number, number] },
  ];
  const blended = blendWinds(target, sources);
  assert(blended !== null, 'blendWinds must return valid vector for clean station');
  const [u, v] = blended!;
  // Clean station: speed 5.0, dir 180 -> u = -5*sin(180)=0, v = -5*cos(180)=5.0
  assert(Math.abs(u) < 1e-4, `Blended u=${u} must exclude Station 172`);
  assert(Math.abs(v - 5.0) < 1e-4, `Blended v=${v} should be 5.0`);
}
console.log('    [PASS] Station 172 successfully blacklisted across all variants and excluded from blending.');

// -------------------------------------------------------------
// Objective 2: T1 Singularity Clamp (d = 0)
// -------------------------------------------------------------
console.log('\n>>> [OBJECTIVE 2] T1 Singularity Clamp (Haversine d = 0)');
{
  const dZero = haversineDistance(31.5204, 74.3587, 31.5204, 74.3587);
  assert(dZero === 0.0, 'haversineDistance between identical coords must be 0.0');

  const target: [number, number] = [31.5204, 74.3587];
  const nodes = [{ coords: [31.5204, 74.3587] as [number, number], value: 142.5 }];
  const val = discreteGeodesicIdw(target, nodes, 2.0, 5.0);
  assert(val !== null, 'discreteGeodesicIdw must not return null');
  assert(!isNaN(val!) && isFinite(val!), 'discreteGeodesicIdw must be finite and not NaN');
  assert(Math.abs(val! - 142.5) < 1e-6, `discreteGeodesicIdw expected 142.5, got ${val}`);

  // Test vector interpolation with d=0
  const vecNodes = [{ coords: [31.5204, 74.3587] as [number, number], u: 3.2, v: -4.5 }];
  const vec = discreteGeodesicIdwVector(target, vecNodes, 2.0, 5.0);
  assert(vec !== null, 'discreteGeodesicIdwVector must not return null');
  assert(Math.abs(vec![0] - 3.2) < 1e-6 && Math.abs(vec![1] - (-4.5)) < 1e-6, 'vector values match');
}
console.log('    [PASS] T1 Singularity Clamp prevents division-by-zero, distance clamped to d0=5.0km.');

// -------------------------------------------------------------
// Objective 3: T6 Physical Dimension Guard
// -------------------------------------------------------------
console.log('\n>>> [OBJECTIVE 3] T6 Physical Dimension Guard (pollutant = AQI)');
{
  const source: [number, number] = [31.5204, 74.3587];
  const receptor: [number, number] = [31.9000, 74.3587]; // North

  const aqiVariations = ['AQI', 'aqi', ' AQI ', 'Aqi', 'aQi'];
  for (const pol of aqiVariations) {
    const res = calculateAdvectionFlux(
      source,
      receptor,
      pol,
      150.0,
      0.0,
      5.0
    );
    assert(res === null, `Advection flux must return null for pollutant ${pol}`);
  }

  // Physical species must calculate valid mass flux
  for (const pol of ['PM2.5', 'PM10', 'NO2', 'SO2', 'CO', 'O3']) {
    const res = calculateAdvectionFlux(
      source,
      receptor,
      pol,
      100.0,
      0.0,
      5.0
    );
    assert(res !== null, `Physical pollutant ${pol} must return valid flux`);
    assert(res!.flux > 0.0, `Physical flux must be positive for ${pol}`);
  }
}
console.log('    [PASS] Physical Dimension Guard strictly blocks dimensionless AQI and allows mass species.');

// -------------------------------------------------------------
// Objective 4: T9 Scale Boundaries & 500 Ceiling Clamp
// -------------------------------------------------------------
console.log('\n>>> [OBJECTIVE 4] T9 Scale Boundaries (PM2.5 @ 350.0, 350.1, 500.0, 5000.0)');
{
  // 350.0 is upper breakpoint of Category 5 (Very Unhealthy) -> AQI 400
  assert(pepcCalculateAqi('PM2.5', 350.0) === 400, 'PM2.5 at 350.0 must be 400 (top of Cat 5)');
  assert(pepcGetCategory(400) === 'Very Unhealthy', 'AQI 400 category must be Very Unhealthy');

  // 350.1 exceeds statutory top breakpoint (350.0) -> strictly clamped to 500
  assert(pepcCalculateAqi('PM2.5', 350.1) === 500, 'PM2.5 at 350.1 must be 500 (Hazardous ceiling)');
  assert(pepcGetCategory(500) === 'Hazardous', 'AQI 500 category must be Hazardous');

  // 500.0 -> strictly clamped to 500
  assert(pepcCalculateAqi('PM2.5', 500.0) === 500, 'PM2.5 at 500.0 must be 500');

  // 5000.0 -> strictly clamped to 500
  assert(pepcCalculateAqi('PM2.5', 5000.0) === 500, 'PM2.5 at 5000.0 must be 500');

  // Continuous half-open intervals
  assert(pepcCalculateAqi('PM2.5', 0.0) === 0, 'PM2.5 @ 0.0 -> 0');
  assert(pepcCalculateAqi('PM2.5', 15.0) === 50, 'PM2.5 @ 15.0 -> 50');
  assert(pepcCalculateAqi('PM2.5', 15.0001) === 50, 'PM2.5 @ 15.0001 -> 50');
  assert(pepcCalculateAqi('PM2.5', 25.0) === 75, 'PM2.5 @ 25.0 -> 75');
  assert(pepcCalculateAqi('PM2.5', 35.0) === 100, 'PM2.5 @ 35.0 -> 100');
  assert(pepcCalculateAqi('PM2.5', 35.0001) === 100, 'PM2.5 @ 35.0001 -> 100');
  assert(pepcCalculateAqi('PM2.5', 70.0) === 150, 'PM2.5 @ 70.0 -> 150');
  assert(pepcCalculateAqi('PM2.5', 140.0) === 200, 'PM2.5 @ 140.0 -> 200');
  assert(pepcCalculateAqi('PM2.5', 250.0) === 300, 'PM2.5 @ 250.0 -> 300');
  assert(pepcCalculateAqi('PM2.5', 300.0) === 350, 'PM2.5 @ 300.0 -> 350');

  // PM10 ceiling
  assert(pepcCalculateAqi('PM10', 550.0) === 400, 'PM10 @ 550.0 -> 400');
  assert(pepcCalculateAqi('PM10', 550.1) === 500, 'PM10 @ 550.1 -> 500');
  assert(pepcCalculateAqi('PM10', 1000.0) === 500, 'PM10 @ 1000.0 -> 500');

  // Composite AQI
  assert(pepcCompositeAqi(300, 200) === 300, 'composite max(300, 200) = 300');
  assert(pepcCompositeAqi(null, 250) === 250, 'composite max(null, 250) = 250');
  assert(pepcCompositeAqi(450, null) === 450, 'composite max(450, null) = 450');
  assert(pepcCompositeAqi(null, null) === null, 'composite max(null, null) = null');
}
console.log('    [PASS] T9 Continuous half-open intervals and strict 500 ceiling clamp verified.');

// -------------------------------------------------------------
// Objective 5: T10 Temporal QC (3h hold & AQI exemption)
// -------------------------------------------------------------
console.log('\n>>> [OBJECTIVE 5] T10 Temporal QC (3h hold at indices 0, 1, 2 & AQI exemption)');
{
  // For physical pollutant: duplicate values at indices 0, 1, 2, 3
  const rawPM25 = [80.0, 80.0, 80.0, 80.0, 95.0];
  const [cleanedPM25] = temporalQcClean(rawPM25, 35.0, 'PM2.5');
  assert(cleanedPM25[0] === 80.0, 'index 0 kept');
  assert(cleanedPM25[1] === 80.0, 'index 1 kept');
  assert(cleanedPM25[2] === null, 'index 2 suppressed by 3h hold');
  assert(cleanedPM25[3] === null, 'index 3 suppressed by 3h hold');
  assert(cleanedPM25[4] === 95.0, 'index 4 kept');

  // For AQI: completely exempt from 3h hold filter
  const rawAQI = [150.0, 150.0, 150.0, 150.0, 150.0];
  const [cleanedAQI] = temporalQcClean(rawAQI, 35.0, 'AQI');
  assert(
    cleanedAQI[0] === 150.0 &&
    cleanedAQI[1] === 150.0 &&
    cleanedAQI[2] === 150.0 &&
    cleanedAQI[3] === 150.0 &&
    cleanedAQI[4] === 150.0,
    'AQI series must not be suppressed by hold filter'
  );

  // Short series without negative index wraparound
  const [cleanedShort] = temporalQcClean([50.0, 50.0], 35.0, 'PM2.5');
  assert(cleanedShort.length === 2 && cleanedShort[0] === 50.0 && cleanedShort[1] === 50.0, 'short series kept');
}
console.log('    [PASS] T10 Temporal QC index guard and AQI exemption verified.');

console.log('\n=================================================================');
console.log(`TOTAL ASSERTIONS EVALUATED: ${passed}`);
console.log(`PASSED: ${passed}`);
console.log(`FAILED: ${failed}`);
console.log('=================================================================');
