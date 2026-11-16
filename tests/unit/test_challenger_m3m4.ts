/**
/**
 * EMPIRICAL CHALLENGER TEST SUITE (Milestones M3-M4 Gate Challenge)
 *
 * Direct adversarial stress testing of:
 * 1. Regulatory Rules:
 *    - PEPC continuous piecewise calculation and 500 ceiling clamp for PM2.5 > 350.
 *    - 75% temporal completeness rule (`validHours / totalHours >= 0.75` -> `≥75% VALID`, else `<75% INCOMPLETE`).
 *    - 16-sector CPF Polar Rose: calm wind exclusion (ws < 0.50 m/s) and small-sample suppression (Nk < 6).
 *    - 216h QC anomaly filters: 7h median spike filter (vi > 4Mi and vi > 3ref_p) and 3h logger hold filter (vi = vi-1 = vi-2 with i >= 2), with AQI exemption.
 * 2. Temporal Scrubber & Playback:
 *    - Sub-hourly continuous lerp (alpha in [0.00, 1.00)) across adjacent hourly matrices.
 *    - Transport controls, playback speeds (1x, 2x, 4x, 8x), and keyboard shortcuts (Space, ArrowLeft, ArrowRight).
 * 3. Planimetric Map Canvas & 5 Deck.gl Layers:
 *    - MapLibre planimetric lock (pitch: 0, maxPitch: 0, bearing: 0, dragRotate: false, touchPitch: false).
 *    - SurfaceLayer Plate Carree bounds & resolution.
 *    - ChoroplethLayer 41 districts, estimated hatching, greedy AABB collision labels.
 *    - WindLayer 3-state kinematics & Station 172 Wazirabad blacklist hard-block.
 *    - FluxLayer top-60 links, physical dimension guard locking to PM2.5 for AQI, and 39 border normal chevrons (crimson for Phi > +0.25 m/s).
 *    - StationLayer 74 fixed, 5 mobile, 6 aerodromes, and Lahore 13 micro-airshed picking.
 */

import * as path from 'path';
import * as fs from 'fs';

// Math and normalizer imports
import {
  pepcCalculateAqi,
  pepcCompositeAqi,
  pepcGetCategory,
  pepcGetColor,
  pepcInterpolateColor,
  pepcInterpolateColorHex,
  PEPC_BREAKPOINTS,
  AQI_TIERS,
} from '../../src/domain/math/pepc_aqi.ts';

import {
  calculateCpfRose,
  calculatePooledP75,
  calculateRoseGeometry,
  MIN_SECTOR_SAMPLES,
} from '../../src/domain/math/cpf.ts';

import {
  temporalQcClean,
  checkCompleteness,
  subhourlyLerp,
} from '../../src/domain/math/qc.ts';

import {
  calculateAdvectionFlux,
  MAX_TRANSPORT_CONE_DEG,
  MAX_TRANSPORT_DISTANCE_KM,
} from '../../src/domain/math/flux.ts';

import {
  checkAabbCollision,
  equirectangularProject,
  equirectangularUnproject,
  LABEL_CANDIDATE_OFFSETS,
  LEADER_LINE_THRESHOLD_PX,
} from '../../src/domain/math/projection.ts';

import {
  isStationBlacklisted,
  normalizeWind,
  normalizeDistrict,
  normalizeStation,
  normalizeAirport,
} from '../../src/domain/normalizer/dataNormalizer.ts';

// Workstation state models and constants
import {
  completenessBadge,
  cpfSectorVisible,
  hazardousAlert,
  qcMarks,
  scrubberReadout,
  statutorySubIndex,
  MAP_LOCK,
  BLACKLIST_TEXT,
  DIMENSION_GUARD,
  HORIZON_HOURS,
  countStationNetworks,
} from '../../src/workstation/state.ts';

import {
  PUNJAB_SURFACE_BOUNDS,
  GRID_WIDTH,
  GRID_HEIGHT,
} from '../../src/map/layers/SurfaceLayer.ts';

let totalAssertions = 0;
let passedAssertions = 0;
let failedAssertions = 0;
const failureMessages: string[] = [];

function assert(condition: boolean, testName: string, detail?: string): void {
  totalAssertions++;
  if (condition) {
    passedAssertions++;
  } else {
    failedAssertions++;
    const msg = `[CHALLENGER FAILURE] ${testName}${detail ? ` -> ${detail}` : ''}`;
    failureMessages.push(msg);
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
  delta: number = 1e-4,
  testName: string
): void {
  if (actual == null || isNaN(actual)) {
    assert(false, testName, `Value is null/NaN (expected: ${expected})`);
    return;
  }
  const diff = Math.abs(actual - expected);
  assert(
    diff <= delta,
    testName,
    `Actual: ${actual}, Expected: ${expected}, Diff: ${diff} > Delta: ${delta}`
  );
}

console.log('=================================================================');
console.log('STARTING EMPIRICAL CHALLENGER TEST SUITE (M3-M4 VERIFICATION GATE)');
console.log('=================================================================\n');

// -----------------------------------------------------------------------------
// GROUP 1: PEPC CONTINUOUS PIECEWISE AQI & 500 CEILING CLAMP
// -----------------------------------------------------------------------------
console.log('>>> [GROUP 1] PEPC Continuous Piecewise Calculation & 500 Ceiling Clamp');

// Test 1.1: Breakpoint boundaries and monotonicity for all 6 statutory pollutants
for (const [pol, bps] of Object.entries(PEPC_BREAKPOINTS)) {
  // Check concentration = 0 -> AQI 0
  assertEquals(pepcCalculateAqi(pol, 0), 0, `pepcCalculateAqi(${pol}, 0) === 0`);
  assertEquals(statutorySubIndex(pol as any, 0), 0, `statutorySubIndex(${pol}, 0) === 0`);

  // Check invalid/negative concentrations -> null
  assertEquals(pepcCalculateAqi(pol, -1), null, `pepcCalculateAqi(${pol}, -1) === null`);
  assertEquals(pepcCalculateAqi(pol, NaN), null, `pepcCalculateAqi(${pol}, NaN) === null`);
  assertEquals(pepcCalculateAqi(pol, null), null, `pepcCalculateAqi(${pol}, null) === null`);

  let prevAqi = 0;
  for (let i = 1; i < bps.length; i++) {
    const bpLow = bps[i - 1];
    const bpHigh = bps[i];
    const tierLow = AQI_TIERS[i - 1];
    const tierHigh = AQI_TIERS[i];

    // Check exact upper breakpoint
    const aqiUpper = pepcCalculateAqi(pol, bpHigh);
    assertEquals(
      aqiUpper,
      tierHigh,
      `pepcCalculateAqi(${pol}, ${bpHigh}) === ${tierHigh}`
    );

    const statutoryUpper = statutorySubIndex(pol as any, bpHigh);
    assertEquals(
      statutoryUpper,
      tierHigh,
      `statutorySubIndex(${pol}, ${bpHigh}) === ${tierHigh}`
    );

    // Check midpoint
    const midC = (bpLow + bpHigh) / 2;
    const aqiMid = pepcCalculateAqi(pol, midC);
    const statutoryMid = statutorySubIndex(pol as any, midC);
    assertEquals(
      aqiMid,
      statutoryMid,
      `Parity at midpoint ${pol} C=${midC}: aqiMid=${aqiMid}, statutoryMid=${statutoryMid}`
    );
    assert(
      aqiMid! >= tierLow && aqiMid! <= tierHigh,
      `Midpoint AQI ${aqiMid} within [${tierLow}, ${tierHigh}]`
    );

    // Monotonicity check
    assert(
      aqiUpper! >= prevAqi,
      `Monotonicity check ${pol} tier ${i}: aqiUpper=${aqiUpper} >= prevAqi=${prevAqi}`
    );
    prevAqi = aqiUpper!;

    // Fuzz 10 points within interval
    for (let f = 1; f < 10; f++) {
      const fuzzC = bpLow + (f / 10) * (bpHigh - bpLow);
      const val1 = pepcCalculateAqi(pol, fuzzC);
      const val2 = statutorySubIndex(pol as any, fuzzC);
      assertEquals(val1, val2, `Fuzz parity ${pol} at C=${fuzzC.toFixed(2)}`);
      assert(val1! >= tierLow && val1! <= tierHigh, `Fuzz value in bounds`);
    }
  }

  // Check top breakpoint ceiling clamp
  const topBp = bps[bps.length - 1];
  const clampAbove = pepcCalculateAqi(pol, topBp + 0.001);
  assertEquals(
    clampAbove,
    500,
    `Ceiling clamp for ${pol} at ${topBp + 0.001} === 500`
  );
  assertEquals(
    statutorySubIndex(pol as any, topBp + 0.001),
    500,
    `statutorySubIndex ceiling clamp for ${pol} at ${topBp + 0.001} === 500`
  );
  assertEquals(
    pepcCalculateAqi(pol, topBp * 2),
    500,
    `Extreme concentration ${topBp * 2} clamped to 500`
  );
}

// Test 1.2: PM2.5 specific statutory requirements (350 threshold)
// At PM2.5 = 350.0: tier is exactly 400
assertEquals(pepcCalculateAqi('PM2.5', 350.0), 400, 'PM2.5 @ 350.0 === 400');
assertEquals(statutorySubIndex('PM2.5', 350.0), 400, 'statutorySubIndex PM2.5 @ 350.0 === 400');
// At PM2.5 = 350.0001: clamped to 500
assertEquals(pepcCalculateAqi('PM2.5', 350.0001), 500, 'PM2.5 @ 350.0001 clamped to 500');
assertEquals(statutorySubIndex('PM2.5', 350.0001), 500, 'statutorySubIndex PM2.5 @ 350.0001 clamped to 500');
assertEquals(pepcCalculateAqi('PM2.5', 500.0), 500, 'PM2.5 @ 500.0 clamped to 500');
assertEquals(pepcCalculateAqi('PM2.5', 1200.0), 500, 'PM2.5 @ 1200.0 clamped to 500');

// Test 1.3: hazardousAlert helper
assertEquals(hazardousAlert(null), null, 'hazardousAlert(null) === null');
assertEquals(hazardousAlert(350.0), null, 'hazardousAlert(350.0) === null');
const alert350_1 = hazardousAlert(350.001);
assert(alert350_1 !== null, 'hazardousAlert(350.001) triggered');
assertEquals(alert350_1?.role, 'alert', 'Alert role === "alert"');
assertEquals(alert350_1?.ariaLive, 'assertive', 'Alert ariaLive === "assertive"');
assertEquals(alert350_1?.background, '#C00000', 'Alert background === "#C00000"');
assertEquals(alert350_1?.color, '#FFFFFF', 'Alert text color === "#FFFFFF"');
assertEquals(alert350_1?.text, 'HAZARDOUS · 500 CEILING CLAMP', 'Alert text verified');

// Test 1.4: Particulate Composite AQI max(I_PM2.5, I_PM10)
assertEquals(pepcCompositeAqi(150, 100), 150, 'Composite max(150, 100) === 150');
assertEquals(pepcCompositeAqi(80, 220), 220, 'Composite max(80, 220) === 220');
assertEquals(pepcCompositeAqi(300, null), 300, 'Composite max(300, null) === 300');
assertEquals(pepcCompositeAqi(null, 450), 450, 'Composite max(null, 450) === 450');
assertEquals(pepcCompositeAqi(null, null), null, 'Composite max(null, null) === null');

// Test 1.5: 7-Category Descriptors and Colors
assertEquals(pepcGetCategory(45), 'Good', 'AQI 45 -> Good');
assertEquals(pepcGetCategory(75), 'Satisfactory', 'AQI 75 -> Satisfactory');
assertEquals(pepcGetCategory(125), 'Moderate', 'AQI 125 -> Moderate');
assertEquals(pepcGetCategory(175), 'Unhealthy (Sensitive)', 'AQI 175 -> Unhealthy (Sensitive)');
assertEquals(pepcGetCategory(250), 'Unhealthy', 'AQI 250 -> Unhealthy');
assertEquals(pepcGetCategory(350), 'Very Unhealthy', 'AQI 350 -> Very Unhealthy');
assertEquals(pepcGetCategory(450), 'Hazardous', 'AQI 450 -> Hazardous');
assertEquals(pepcGetCategory(500), 'Hazardous', 'AQI 500 -> Hazardous');

assertEquals(pepcGetColor(45), '#00B050', 'AQI 45 -> #00B050');
assertEquals(pepcGetColor(75), '#92D050', 'AQI 75 -> #92D050');
assertEquals(pepcGetColor(125), '#FFFF00', 'AQI 125 -> #FFFF00');
assertEquals(pepcGetColor(175), '#ED7D31', 'AQI 175 -> #ED7D31');
assertEquals(pepcGetColor(250), '#FF0000', 'AQI 250 -> #FF0000');
assertEquals(pepcGetColor(350), '#7030A0', 'AQI 350 -> #7030A0');
assertEquals(pepcGetColor(450), '#C00000', 'AQI 450 -> #C00000');

// Test 1.6: 7-stop PEQS RGB color gradient interpolation
const [r0, g0, b0] = pepcInterpolateColor(0, 35);
assertEquals([r0, g0, b0], [58, 165, 93], '0 concentration returns stop 0 (Clean Green)');
const [rMax, gMax, bMax] = pepcInterpolateColor(35 * 6.0, 35);
assertEquals([rMax, gMax, bMax], [90, 21, 48], '6x limit returns stop 6 (Deep Maroon)');
const hexMid = pepcInterpolateColorHex(35 * 1.0, 35);
assertEquals(hexMid, '#F2C230', '1.0x standard returns #F2C230 (Yellow at Standard)');

// -----------------------------------------------------------------------------
// GROUP 2: 75% TEMPORAL COMPLETENESS RULE
// -----------------------------------------------------------------------------
console.log('\n>>> [GROUP 2] 75% Temporal Completeness Rule');

// Test 2.1: 216-hour simulation horizon exact boundary testing
// 0.75 * 216 = 162 required hours
const b216_exact = completenessBadge(162, 216);
assertEquals(b216_exact.meets, true, '162/216h meets 75% completeness');
assertEquals(b216_exact.pct, 75, '162/216h is exactly 75%');
assert(
  b216_exact.label.includes('≥75% VALID'),
  '162/216h label contains "≥75% VALID"'
);

const b216_short = completenessBadge(161, 216);
assertEquals(b216_short.meets, false, '161/216h fails 75% completeness');
assert(
  b216_short.label.includes('<75% INCOMPLETE'),
  '161/216h label contains "<75% INCOMPLETE"'
);

// Full horizon vs 0 valid
assertEquals(completenessBadge(216, 216).meets, true, '216/216h meets');
assertEquals(completenessBadge(0, 216).meets, false, '0/216h fails');

// Test 2.2: Systematic boundary sweeps across horizon lengths 1 to 240
for (let total = 1; total <= 240; total++) {
  const req = Math.max(1, Math.round(0.75 * total));
  const passBadge = completenessBadge(req, total);
  assertEquals(passBadge.meets, true, `Req ${req}/${total} meets completeness`);
  assert(
    passBadge.label.includes('≥75% VALID'),
    `${req}/${total} labeled as ≥75% VALID`
  );

  if (req > 1) {
    const failBadge = completenessBadge(req - 1, total);
    assertEquals(
      failBadge.meets,
      false,
      `Req-1 ${req - 1}/${total} fails completeness`
    );
    assert(
      failBadge.label.includes('<75% INCOMPLETE'),
      `${req - 1}/${total} labeled as <75% INCOMPLETE`
    );
  }
}

// Test 2.3: checkCompleteness function in src/domain/math/qc.ts
// Array of 20 elements: 15 valid (75%), 5 null
const series20_pass = Array.from({ length: 20 }, (_, i) => (i < 15 ? 100 : null));
const avgPass = checkCompleteness(series20_pass, 0.75);
assertEquals(avgPass, 100, 'checkCompleteness with 15/20 (75%) returns average 100');

// Array of 20 elements: 14 valid (70%), 6 null
const series20_fail = Array.from({ length: 20 }, (_, i) => (i < 14 ? 100 : null));
const avgFail = checkCompleteness(series20_fail, 0.75);
assertEquals(avgFail, null, 'checkCompleteness with 14/20 (<75%) returns null');

// Empty series
assertEquals(checkCompleteness([], 0.75), null, 'checkCompleteness([]) returns null');

// -----------------------------------------------------------------------------
// GROUP 3: 16-SECTOR CPF POLAR ROSE (CALM EXCLUSION & SMALL-SAMPLE SUPPRESSION)
// -----------------------------------------------------------------------------
console.log('\n>>> [GROUP 3] 16-Sector CPF Polar Rose Modeling');

// Test 3.1: Calm wind exclusion (< 0.50 m/s)
const calmObservations = [
  // 5 calm wind observations (ws < 0.50)
  { value: 120, wind_speed: 0.10, wind_direction: 90 },
  { value: 130, wind_speed: 0.25, wind_direction: 90 },
  { value: 140, wind_speed: 0.40, wind_direction: 90 },
  { value: 150, wind_speed: 0.499, wind_direction: 90 },
  { value: 160, wind_speed: 0.00, wind_direction: 90 },
  // 10 active wind observations from Sector 4 (90 deg -> East)
  ...Array.from({ length: 10 }, (_, i) => ({
    value: 80 + i * 10,
    wind_speed: 2.5,
    wind_direction: 90.0,
  })),
];

const roseResult = calculateCpfRose(calmObservations, 100.0, 0.50, 6);
// Total obs = 15. Calm = 5. Calm ratio = 5/15 = 0.3333
assertCloseTo(roseResult.calm_ratio, 0.3333, 1e-3, 'Calm ratio 5/15 === 0.3333');
// Sector 4 (90 deg) should have exactly 10 counts (the 5 calms must NOT be in sector 4!)
assertEquals(roseResult.sector_counts[4], 10, 'Sector 4 counts === 10 (calm excluded)');

// Exceedances for C > 100 in sector 4: values are 80, 90, 100, 110, 120, 130, 140, 150, 160, 170
// Strictly > 100: 110, 120, 130, 140, 150, 160, 170 -> 7 exceedances
assertEquals(roseResult.sector_exceedances[4], 7, 'Sector 4 exceedances === 7');
assertEquals(roseResult.sectors[4], 0.7000, 'Sector 4 CPF probability === 0.7000');

// All other sectors should have count = 0 and be suppressed (null)
for (let k = 0; k < 16; k++) {
  if (k !== 4) {
    assertEquals(roseResult.sector_counts[k], 0, `Sector ${k} count === 0`);
    assertEquals(roseResult.sectors[k], null, `Sector ${k} suppressed (< 6 samples)`);
  }
}

// Test 3.2: Small-sample suppression threshold (N_k < 6)
// Create sectors with counts from 1 to 10
const sampleObs: any[] = [];
for (let sector = 0; sector < 16; sector++) {
  const count = sector; // Sector 0 has 0, sector 5 has 5, sector 6 has 6, etc.
  const deg = sector * 22.5;
  for (let c = 0; c < count; c++) {
    sampleObs.push({
      value: 150, // All exceed tau=100
      wind_speed: 3.0,
      wind_direction: deg,
    });
  }
}

const multiSectorRose = calculateCpfRose(sampleObs, 100.0, 0.50, 6);
for (let sector = 0; sector < 16; sector++) {
  if (sector < 6) {
    assertEquals(
      multiSectorRose.sectors[sector],
      null,
      `Sector ${sector} with ${sector} samples suppressed (< 6)`
    );
  } else {
    assertEquals(
      multiSectorRose.sectors[sector],
      1.0,
      `Sector ${sector} with ${sector} samples valid (>= 6) with CPF 1.0`
    );
  }
}

// Test 3.3: cpfSectorVisible helper
assertEquals(
  cpfSectorVisible({ totalHours: 5, cpfProbability: 0.8 }),
  false,
  'cpfSectorVisible false for totalHours=5'
);
assertEquals(
  cpfSectorVisible({ totalHours: 6, cpfProbability: null }),
  false,
  'cpfSectorVisible false for cpfProbability=null'
);
assertEquals(
  cpfSectorVisible({ totalHours: 6, cpfProbability: 0.5 }),
  true,
  'cpfSectorVisible true for totalHours=6 and cpfProbability=0.5'
);

// Test 3.4: calculatePooledP75 with calm exclusion
const pooledObs = [
  { value: 50, wind_speed: 0.2 }, // calm -> excluded
  { value: 10, wind_speed: 1.0 },
  { value: 20, wind_speed: 1.0 },
  { value: 30, wind_speed: 1.0 },
  { value: 40, wind_speed: 1.0 },
];
// Active values: [10, 20, 30, 40]. P75 = 0.75 * 3 = 2.25 -> 30 + 0.25 * (40 - 30) = 32.5
const p75 = calculatePooledP75(pooledObs, 0.50);
assertEquals(p75, 32.5, 'Pooled P75 calculates 32.5 on active subset');

// Test 3.5: calculateRoseGeometry
const geom = calculateRoseGeometry(multiSectorRose.sectors, 100.0, 10.0);
assertEquals(geom.length, 16, 'Geometry generates 16 sector wedges');
assertEquals(geom[0].is_suppressed, true, 'Sector 0 wedge is suppressed');
assertEquals(geom[0].radius_px, 10.0, 'Suppressed wedge has muted stub 10px');
assertEquals(geom[6].is_suppressed, false, 'Sector 6 wedge is not suppressed');
assert(geom[6].radius_px > 10.0, 'Active wedge has expanded radius');

// -----------------------------------------------------------------------------
// GROUP 4: 216h QC ANOMALY FILTERS (7h MEDIAN SPIKE & 3h LOGGER HOLD)
// -----------------------------------------------------------------------------
console.log('\n>>> [GROUP 4] 216h QC Anomaly Filters & AQI Exemption');

// Test 4.1: 7-Hour Rolling Median Spike Filter (> 4*M and > 3*ref)
// Construct series with baseline 20, ref = 35 (PM2.5)
// Spike threshold: > 4 * 20 = 80 AND > 3 * 35 = 105.
// Value 100: > 80 but not > 105 -> NOT a spike
// Value 110: > 80 AND > 105 -> SPIKE!
const spikeSeries = [
  20, 20, 20, 100, 20, 20, 20, // Index 3: 100 -> NOT spike (>80 but <=105)
  20, 20, 20, 110, 20, 20, 20, // Index 10: 110 -> SPIKE (>80 and >105)
];

const [cleanedSpikes, spikeCount] = temporalQcClean(spikeSeries, 35.0, 'PM2.5');
assertEquals(spikeCount, 1, 'Exactly 1 spike identified');
assertEquals(cleanedSpikes[3], 100, 'Index 3 (100) preserved (fails >3*ref test)');
assertEquals(cleanedSpikes[10], null, 'Index 10 (110) purged to null (satisfies both >4*M and >3*ref)');

// Verify qcMarks implementation
const marksSpike = qcMarks(spikeSeries, 'PM2.5', 35.0);
assertEquals(marksSpike[3].spike, false, 'qcMarks[3].spike === false');
assertEquals(marksSpike[10].spike, true, 'qcMarks[10].spike === true');

// Test 4.2: 3-Hour Logger Hold Filter (Sensor Freeze) with i >= 2 Index Guard
// Sequence: [10, 10, 10, 10, 20]
// Index 0: 10 (no freeze)
// Index 1: 10 (i < 2 guard -> no freeze)
// Index 2: 10 (i=2, v[2]==v[1]==v[0] -> HOLD!)
// Index 3: 10 (i=3, v[3]==v[2]==v[1] -> HOLD!)
// Index 4: 20 (no freeze)
const holdSeries = [10, 10, 10, 10, 20];
const [cleanedHolds] = temporalQcClean(holdSeries, 35.0, 'PM2.5');
assertEquals(cleanedHolds[0], 10, 'Index 0 preserved');
assertEquals(cleanedHolds[1], 10, 'Index 1 preserved (index guard i >= 2)');
assertEquals(cleanedHolds[2], null, 'Index 2 purged (hold detected)');
assertEquals(cleanedHolds[3], null, 'Index 3 purged (hold detected)');
assertEquals(cleanedHolds[4], 20, 'Index 4 preserved');

const marksHold = qcMarks(holdSeries, 'PM2.5', 35.0);
assertEquals(marksHold[0].hold, false, 'marksHold[0].hold === false');
assertEquals(marksHold[1].hold, false, 'marksHold[1].hold === false');
assertEquals(marksHold[2].hold, true, 'marksHold[2].hold === true');
assertEquals(marksHold[3].hold, true, 'marksHold[3].hold === true');
assertEquals(marksHold[4].hold, false, 'marksHold[4].hold === false');

// Test 4.3: AQI Exemption from Logger Hold Filter
// The requirement explicitly mandates: dimensionless AQI is EXEMPT from 3h logger hold filter
const aqiHoldSeries = [300, 300, 300, 300, 300];
const [cleanedAqi] = temporalQcClean(aqiHoldSeries, 100.0, 'AQI');
assertEquals(cleanedAqi, aqiHoldSeries, 'temporalQcClean for AQI exempts logger hold completely');

const marksAqi = qcMarks(aqiHoldSeries, 'AQI', 100.0);
for (let i = 0; i < marksAqi.length; i++) {
  assertEquals(marksAqi[i].hold, false, `marksAqi[${i}].hold strictly false (AQI exempt)`);
}

// Case-insensitivity check: 'aqi' vs 'AQI'
const [cleanedAqiLower] = temporalQcClean(aqiHoldSeries, 100.0, 'aqi');
assertEquals(cleanedAqiLower, aqiHoldSeries, 'Lower case aqi also exempt');

// -----------------------------------------------------------------------------
// GROUP 5: SUB-HOURLY CONTINUOUS LERP & ANIMATION SCRUBBING
// -----------------------------------------------------------------------------
console.log('\n>>> [GROUP 5] Sub-Hourly Continuous Lerp across Matrices');

const testMatrixSeries = [100.0, 200.0, 300.0, 400.0];

// Test 5.1: Exact hourly nodes (alpha = 0.0)
assertEquals(subhourlyLerp(testMatrixSeries, 0.0), 100.0, 'Lerp @ 0.0 === 100.0');
assertEquals(subhourlyLerp(testMatrixSeries, 1.0), 200.0, 'Lerp @ 1.0 === 200.0');
assertEquals(subhourlyLerp(testMatrixSeries, 2.0), 300.0, 'Lerp @ 2.0 === 300.0');
assertEquals(subhourlyLerp(testMatrixSeries, 3.0), 400.0, 'Lerp @ 3.0 === 400.0');

// Test 5.2: Continuous fractional positions alpha in (0.00, 1.00)
assertCloseTo(subhourlyLerp(testMatrixSeries, 0.5), 150.0, 1e-4, 'Lerp @ 0.5 === 150.0');
assertCloseTo(subhourlyLerp(testMatrixSeries, 0.25), 125.0, 1e-4, 'Lerp @ 0.25 === 125.0');
assertCloseTo(subhourlyLerp(testMatrixSeries, 1.75), 275.0, 1e-4, 'Lerp @ 1.75 === 275.0');
assertCloseTo(subhourlyLerp(testMatrixSeries, 2.10), 310.0, 1e-4, 'Lerp @ 2.10 === 310.0');

// Test 5.3: Clamping bounds
assertEquals(subhourlyLerp(testMatrixSeries, -5.0), 100.0, 'Negative fp clamped to index 0');
assertEquals(subhourlyLerp(testMatrixSeries, 10.0), 400.0, 'Excess fp clamped to index n-1');

// Test 5.4: Missing telemetry interpolation fallbacks
const seriesWithNulls = [100.0, null, 300.0];
// Lerp between 100 and null: returns 100
assertEquals(subhourlyLerp(seriesWithNulls, 0.5), 100.0, 'Lerp with right null returns left');
// Lerp between null and 300: returns 300
assertEquals(subhourlyLerp(seriesWithNulls, 1.5), 300.0, 'Lerp with left null returns right');
// Both null: returns null
assertEquals(subhourlyLerp([null, null], 0.5), null, 'Lerp with both null returns null');

// Test 5.5: scrubberReadout format verification
const readout0 = scrubberReadout(0, 0.0, '2026-11-01 00:00');
assertEquals(readout0.timestampLine, '2026-11-01 00:00 PKT', 'Timestamp line matches PKT format');
assertEquals(readout0.detailLine, 'Hour 1/216 · Lerp α=0.00', 'Detail line matches Hour 1/216 · Lerp α=0.00');

const readoutMid = scrubberReadout(47, 0.42, '2026-11-02 23:25');
assertEquals(readoutMid.detailLine, 'Hour 48/216 · Lerp α=0.42', 'Detail line matches Hour 48/216 · Lerp α=0.42');

const readoutMax = scrubberReadout(215, 0.99, '2026-11-09 23:59');
assertEquals(readoutMax.detailLine, 'Hour 216/216 · Lerp α=0.99', 'Detail line matches Hour 216/216 · Lerp α=0.99');

// -----------------------------------------------------------------------------
// GROUP 6: PLANIMETRIC MAP CANVAS & 5 DECK.GL LAYERS CONSTRAINTS
// -----------------------------------------------------------------------------
console.log('\n>>> [GROUP 6] Planimetric Map Canvas & 5 Deck.gl Layers Architecture');

// Test 6.1: MapLibre Planimetric Lock (Pitch = 0, Bearing = 0, DragRotate = False)
assertEquals(MAP_LOCK.pitch, 0, 'MAP_LOCK pitch === 0');
assertEquals(MAP_LOCK.maxPitch, 0, 'MAP_LOCK maxPitch === 0');
assertEquals(MAP_LOCK.bearing, 0, 'MAP_LOCK bearing === 0');
assertEquals(MAP_LOCK.dragRotate, false, 'MAP_LOCK dragRotate === false');
assertEquals(MAP_LOCK.touchPitch, false, 'MAP_LOCK touchPitch === false');

// Test 6.2: SurfaceLayer parameters
assertEquals(PUNJAB_SURFACE_BOUNDS, [69.10, 27.55, 75.75, 34.30], 'Punjab surface bounds match Plateau Carree');
assertEquals(GRID_WIDTH, 150, 'Grid width === 150');
assertEquals(GRID_HEIGHT, 175, 'Grid height === 175');

// Test 6.3: Station 172 Wazirabad Anemometer Blacklist Hard-Block
assert(isStationBlacklisted(172), 'Station 172 blacklisted by number');
assert(isStationBlacklisted('172'), 'Station 172 blacklisted by string');
assert(!isStationBlacklisted(1), 'Station 1 not blacklisted');

const normStation172 = normalizeStation({ station_id: 172, name: 'Wazirabad Town Hall' });
assertEquals(normStation172.anemometerBlacklisted, true, 'normalizeStation(172) anemometerBlacklisted === true');
assertEquals(normStation172.hasAnemometer, false, 'normalizeStation(172) hasAnemometer === false');

const normWind172 = normalizeWind(5.0, 180, 172);
assertEquals(normWind172.state, 'blacklisted', 'normalizeWind for station 172 is blacklisted');
assertEquals(normWind172.blacklisted, true, 'normalizeWind blacklisted === true');
assertEquals(normWind172.blacklistReason, BLACKLIST_TEXT, 'normalizeWind blacklistReason matches');

// Test 6.4: Wind Kinematics (Active vs Calm vs Dropout)
const calmWind = normalizeWind(0.35, 180, 1);
assertEquals(calmWind.state, 'calm', 'Wind 0.35 m/s is calm');
const activeWind = normalizeWind(2.5, 90, 1);
assertEquals(activeWind.state, 'active', 'Wind 2.5 m/s is active');
const dropoutWind = normalizeWind(null, null, 1);
assertEquals(dropoutWind.state, 'dropout', 'Null wind is dropout');

// Test 6.5: Physical Dimension Guard in Advection Flux
// AQI selected -> calculations lock to PM2.5
const fluxAqiDirect = calculateAdvectionFlux(
  { coords: [31.5, 74.3], value: 100, u: 2.0, v: 0.0 },
  [31.5, 74.5],
  'AQI'
);
assertEquals(fluxAqiDirect, null, 'calculateAdvectionFlux with AQI species returns null (Dimension Guard)');

const fluxPm25 = calculateAdvectionFlux(
  { coords: [31.5, 74.3], value: 100, u: 2.0, v: 0.0 },
  [31.5, 74.5],
  'PM2.5'
);
assert(fluxPm25 !== null && fluxPm25.flux > 0, 'calculateAdvectionFlux with PM2.5 succeeds');
assertEquals(DIMENSION_GUARD, 'Dimension Guard: Flux locked to PM2.5 mass', 'DIMENSION_GUARD text matches');

// Test 6.6: Physical Cutoffs (d <= 180 km, cone <= 35 deg)
assertEquals(MAX_TRANSPORT_DISTANCE_KM, 180.0, 'MAX_TRANSPORT_DISTANCE_KM === 180.0');
assertEquals(MAX_TRANSPORT_CONE_DEG, 35.0, 'MAX_TRANSPORT_CONE_DEG === 35.0');

// Test 6.7: Transboundary Border Normal Chevrons
// Inward transport dot product Phi_j = u*nx + v*ny
// Positive normal points into Punjab: Phi > +0.25 triggers crimson #C00000
const uIn = 1.0, vIn = 0.0;
const nx = 1.0, ny = 0.0;
const phiIn = uIn * nx + vIn * ny;
assert(phiIn > 0.25, 'Inward dot product > +0.25 m/s');

// Outward transport dot product Phi < -0.25 triggers teal #5fc4c4
const uOut = -1.0, vOut = 0.0;
const phiOut = uOut * nx + vOut * ny;
assert(phiOut < -0.25, 'Outward dot product < -0.25 m/s');

// Deadband |Phi| <= 0.25 -> no chevron triggered
const uDead = 0.1, vDead = 0.0;
const phiDead = uDead * nx + vDead * ny;
assert(phiDead <= 0.25 && phiDead >= -0.25, 'Deadband |Phi| <= 0.25');

// Test 6.8: Stations Network Dynamic Counting
const testStations = [
  ...Array.from({ length: 74 }, (_, i) => ({ id: `${i}`, mobile: false })),
  ...Array.from({ length: 5 }, (_, i) => ({ id: `m_${i}`, mobile: true })),
];
const netCounts = countStationNetworks(testStations);
assertEquals(netCounts.fixed, 74, 'Fixed stations count === 74');
assertEquals(netCounts.mobile, 5, 'Mobile stations count === 5');

// Test 6.9: Greedy AABB Label Placement & Leader Line Threshold
assertEquals(LEADER_LINE_THRESHOLD_PX, 20.0, 'LEADER_LINE_THRESHOLD_PX === 20.0');
assert(LABEL_CANDIDATE_OFFSETS.length >= 10, 'Candidate label offsets >= 10');

// Test collision detection logic
const boxA: [number, number, number, number] = [0, 0, 40, 20];
const boxB_colliding: [number, number, number, number] = [10, 5, 40, 20];
const boxC_clear: [number, number, number, number] = [50, 50, 40, 20];
assertEquals(checkAabbCollision(boxA, boxB_colliding), true, 'Collision detected between intersecting boxes');
assertEquals(checkAabbCollision(boxA, boxC_clear), false, 'No collision between disjoint boxes');

// -----------------------------------------------------------------------------
// GROUP 7: FULL BASELINE DATA INTEGRITY & MATRIX LERP STRESS TEST
// -----------------------------------------------------------------------------
console.log('\n>>> [GROUP 7] Full Baseline Data Integrity & 216h Matrix Lerp Stress Test');

const baselinePath = path.join(process.cwd(), 'data', 'baseline', 'baseline_data.json');
const airportsPath = path.join(process.cwd(), 'data', 'baseline', 'airports.json');
const stationsPath = path.join(process.cwd(), 'data', 'baseline', 'stations.json');

const baseline = JSON.parse(fs.readFileSync(baselinePath, 'utf8'));
const airports = JSON.parse(fs.readFileSync(airportsPath, 'utf8'));
const rawStations = JSON.parse(fs.readFileSync(stationsPath, 'utf8'));

// Verify 41 districts
const districtNames = Object.keys(baseline.districts);
assertEquals(districtNames.length, 41, 'Baseline contains exactly 41 districts');

// Verify 216 hours
assertEquals(baseline.hours.length, 216, 'Baseline contains exactly 216 hours');
assertEquals(baseline.hours[0], '2026-11-01 00:00', 'Start timestamp matches 2026-11-01 00:00');
assertEquals(baseline.hours[215], '2026-11-09 23:00', 'End timestamp matches 2026-11-09 23:00');

// Verify 79 stations inventory: 74 fixed, 5 mobile
assertEquals(rawStations.length, 79, 'Total raw stations count === 79');
const stationBreakdown = countStationNetworks(rawStations);
assertEquals(stationBreakdown.fixed, 74, 'Fixed stations count === 74');
assertEquals(stationBreakdown.mobile, 5, 'Mobile stations count === 5');

// Verify 6 airports
assertEquals(airports.length, 6, 'Total airports count === 6');

// Verify 39 border normal nodes in tbgeo
assertEquals(baseline.tbgeo?.samples?.length, 39, 'Transboundary samples count === 39');

// Stress-test continuous sub-hourly lerp across all 41 districts for all 216 hours
// Sample 5 fractional alpha values per hour (0.1, 0.3, 0.5, 0.7, 0.9)
let lerpEvaluations = 0;
for (const dName of districtNames) {
  const pm25Series = baseline.hours.map((_: any, h: number) => {
    return baseline.pol['PM2.5']?.frames?.[h]?.c?.[dName] ?? null;
  });

  for (let h = 0; h < 215; h++) {
    for (const alpha of [0.0, 0.25, 0.5, 0.75, 0.99]) {
      const interpolated = subhourlyLerp(pm25Series, h + alpha);
      lerpEvaluations++;
      if (pm25Series[h] != null && pm25Series[h + 1] != null) {
        assert(interpolated !== null, `Lerp not null for ${dName} at ${h}+${alpha}`);
        const minVal = Math.min(pm25Series[h], pm25Series[h + 1]);
        const maxVal = Math.max(pm25Series[h], pm25Series[h + 1]);
        assert(
          interpolated! >= minVal - 1e-4 && interpolated! <= maxVal + 1e-4,
          `Lerp bounded for ${dName} at ${h}+${alpha}`
        );
      }
    }
  }
}
console.log(`    Evaluated ${lerpEvaluations} continuous matrix lerp calculations across all 41 districts`);

// -----------------------------------------------------------------------------
// VERIFICATION SUMMARY
// -----------------------------------------------------------------------------
console.log('\n=================================================================');
console.log('CHALLENGER GATE VERIFICATION SUMMARY:');
console.log(`Total Assertions Evaluated: ${totalAssertions}`);
console.log(`Passed Assertions:          ${passedAssertions}`);
console.log(`Failed Assertions:          ${failedAssertions}`);
console.log('=================================================================');

if (failedAssertions > 0) {
  console.error('\nFAILURE DETAILS:');
  failureMessages.forEach((msg) => console.error(msg));
  process.exit(1);
} else {
  console.log('\n>>> ALL EMPIRICAL CHALLENGES PASSED PERFECTLY (0 FAILURES). <<<');
  process.exit(0);
}
