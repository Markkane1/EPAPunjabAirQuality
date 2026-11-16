/**
 * EMPIRICAL ADVERSARIAL STRESS TEST HARNESS
 * Challenger: challenger_m1m2_r2_1
 * Purpose: Exhaustively stress-test station 172 blacklist & aerodromeWindCopy edge cases.
 */

import {
  normalizeStation,
  isStationBlacklisted,
  normalizeWind,
  aerodromeWindCopy,
  blacklistBannerText,
} from '../../src/domain/normalizer/dataNormalizer';

let passed = 0;
let failed = 0;

function assert(condition: boolean, msg: string) {
  if (!condition) {
    console.error(`❌ FAIL: ${msg}`);
    failed++;
  } else {
    passed++;
  }
}

function assertEquals<T>(actual: T, expected: T, msg: string) {
  if (actual !== expected) {
    console.error(`❌ FAIL: ${msg} | Expected: ${JSON.stringify(expected)}, Actual: ${JSON.stringify(actual)}`);
    failed++;
  } else {
    passed++;
  }
}

console.log('=== RUNNING EMPIRICAL ADVERSARIAL CHALLENGER PROBES ===\n');

// -------------------------------------------------------------
// PROBE 1: Station 172 Blacklist Schema Variations
// -------------------------------------------------------------
console.log('>>> [PROBE 1] Station 172 Blacklist Schema Variations');

const blacklistedInputs = [
  { desc: '{ station_id: 172 }', input: { station_id: 172 } },
  { desc: '{ station_id: "172" }', input: { station_id: '172' } },
  { desc: '{ station_id: " 172 " }', input: { station_id: ' 172 ' } },
  { desc: '{ id: 172 }', input: { id: 172 } },
  { desc: '{ id: "172" }', input: { id: '172' } },
  { desc: '{ id: " 172 " }', input: { id: ' 172 ' } },
  { desc: '{ station_id: 172, name: "Arbitrary Name" }', input: { station_id: 172, name: 'Arbitrary Name' } },
  { desc: '{ id: 172, name: "Arbitrary Name" }', input: { id: 172, name: 'Arbitrary Name' } },
  { desc: '{ name: "wazirabad" }', input: { name: 'wazirabad' } },
  { desc: '{ name: "WAZIRABAD" }', input: { name: 'WAZIRABAD' } },
  { desc: '{ name: "Wazirabad AQMS" }', input: { name: 'Wazirabad AQMS' } },
  { desc: '{ name: "wazirabad station" }', input: { name: 'wazirabad station' } },
  { desc: '{ name: "pk_waz_001" }', input: { name: 'pk_waz_001' } },
  { desc: '{ name: "Sub-station in Wazirabad East" }', input: { name: 'Sub-station in Wazirabad East' } },
  { desc: '{ station_id: 172, id: 172 }', input: { station_id: 172, id: 172 } },
  { desc: '{ station_id: "172", id: "172", name: "Wazirabad" }', input: { station_id: '172', id: '172', name: 'Wazirabad' } },
];

for (const t of blacklistedInputs) {
  const norm = normalizeStation(t.input as any);
  assertEquals(norm.anemometerBlacklisted, true, `${t.desc} -> anemometerBlacklisted MUST be true`);
  assertEquals(norm.hasAnemometer, false, `${t.desc} -> hasAnemometer MUST be false`);
  
  const windNorm = normalizeWind(10.0, 180, (t.input as any).id ?? (t.input as any).station_id ?? (t.input as any).name);
  assertEquals(windNorm.state, 'blacklisted', `${t.desc} -> normalizeWind state MUST be 'blacklisted'`);
  assertEquals(windNorm.blacklisted, true, `${t.desc} -> normalizeWind blacklisted flag MUST be true`);
}

// Clean stations must NOT be blacklisted
const cleanInputs = [
  { desc: '{ id: 101, name: "Lahore Town Hall" }', input: { id: 101, name: 'Lahore Town Hall' } },
  { desc: '{ station_id: 171, name: "Gujranwala North" }', input: { station_id: 171, name: 'Gujranwala North' } },
  { desc: '{ id: 173, name: "Sialkot Cantt" }', input: { id: 173, name: 'Sialkot Cantt' } },
  { desc: '{ station_id: "wazi_clean", name: "Clean Station" }', input: { station_id: 'wazi_clean', name: 'Clean Station' } },
];

for (const t of cleanInputs) {
  const norm = normalizeStation(t.input as any);
  assertEquals(norm.anemometerBlacklisted, false, `${t.desc} -> anemometerBlacklisted MUST be false`);
  assertEquals(norm.hasAnemometer, true, `${t.desc} -> hasAnemometer MUST be true`);
}

// -------------------------------------------------------------
// PROBE 2: aerodromeWindCopy & normalizeWind Exhaustive Edge Cases
// -------------------------------------------------------------
console.log('\n>>> [PROBE 2] aerodromeWindCopy & normalizeWind Negative / Unphysical / Error Codes');

const dropoutCases = [
  // Negative speeds
  { speed: -0.0001, dir: 180, desc: 'speed = -0.0001' },
  { speed: -0.1, dir: 180, desc: 'speed = -0.1' },
  { speed: -5.0, dir: 180, desc: 'speed = -5.0' },
  { speed: -99.9, dir: 180, desc: 'speed = -99.9' },
  { speed: -Infinity, dir: 180, desc: 'speed = -Infinity' },

  // Out of range speeds (> 30.0 m/s physical limit or sensor error codes)
  { speed: 30.001, dir: 180, desc: 'speed = 30.001' },
  { speed: 30.1, dir: 180, desc: 'speed = 30.1' },
  { speed: 50.0, dir: 180, desc: 'speed = 50.0' },
  { speed: 99.9, dir: 180, desc: 'speed = 99.9 (error code)' },
  { speed: 999.0, dir: 180, desc: 'speed = 999.0' },
  { speed: Infinity, dir: 180, desc: 'speed = Infinity' },

  // Non-numeric / Missing speed
  { speed: NaN, dir: 180, desc: 'speed = NaN' },
  { speed: null, dir: 180, desc: 'speed = null' },
  { speed: undefined, dir: 180, desc: 'speed = undefined' },

  // Invalid directions
  { speed: 10.0, dir: -0.1, desc: 'dir = -0.1' },
  { speed: 10.0, dir: -180, desc: 'dir = -180' },
  { speed: 10.0, dir: 360.1, desc: 'dir = 360.1' },
  { speed: 10.0, dir: 720, desc: 'dir = 720' },
  { speed: 10.0, dir: NaN, desc: 'dir = NaN' },
  { speed: 10.0, dir: Infinity, desc: 'dir = Infinity' },
  { speed: 10.0, dir: -Infinity, desc: 'dir = -Infinity' },
  { speed: 10.0, dir: null, desc: 'dir = null' },
  { speed: 10.0, dir: undefined, desc: 'dir = undefined' },
];

for (const tc of dropoutCases) {
  const copy = aerodromeWindCopy(tc.speed, tc.dir);
  assertEquals(copy, 'TELEMETRY DROPOUT (NULL)', `aerodromeWindCopy(${tc.desc}) -> MUST return 'TELEMETRY DROPOUT (NULL)'`);

  const norm = normalizeWind(tc.speed, tc.dir);
  assertEquals(norm.state, 'dropout', `normalizeWind(${tc.desc}) -> state MUST be 'dropout'`);
  assertEquals(norm.speed, null, `normalizeWind(${tc.desc}) -> speed MUST be null`);
  assertEquals(norm.direction, null, `normalizeWind(${tc.desc}) -> direction MUST be null`);
  assertEquals(norm.u, null, `normalizeWind(${tc.desc}) -> u MUST be null`);
  assertEquals(norm.v, null, `normalizeWind(${tc.desc}) -> v MUST be null`);
}

// Calm Cases: 0.0 <= speed < 0.50 m/s
console.log('\n>>> [PROBE 3] Calm Wind Boundaries (0.0 <= speed < 0.50)');
const calmCases = [
  { speed: 0.0, dir: 0.0, desc: '0.0 m/s' },
  { speed: 0.0001, dir: 90.0, desc: '0.0001 m/s' },
  { speed: 0.25, dir: 180.0, desc: '0.25 m/s' },
  { speed: 0.49, dir: 270.0, desc: '0.49 m/s' },
  { speed: 0.4999, dir: 360.0, desc: '0.4999 m/s' },
];

for (const tc of calmCases) {
  const copy = aerodromeWindCopy(tc.speed, tc.dir);
  assert(copy.startsWith('AERODYNAMIC CALM (< 0.50 m/s)'), `aerodromeWindCopy(${tc.desc}) -> starts with AERODYNAMIC CALM`);
  
  const norm = normalizeWind(tc.speed, tc.dir);
  assertEquals(norm.state, 'calm', `normalizeWind(${tc.desc}) -> state MUST be 'calm'`);
  assertEquals(norm.u, 0.0, `normalizeWind(${tc.desc}) -> u MUST be 0.0`);
  assertEquals(norm.v, 0.0, `normalizeWind(${tc.desc}) -> v MUST be 0.0`);
}

// Active Cases: 0.50 <= speed <= 30.00 m/s
console.log('\n>>> [PROBE 4] Active Wind Boundaries (0.50 <= speed <= 30.00)');
const activeCases = [
  { speed: 0.50, dir: 0.0, desc: '0.50 m/s (exact lower active boundary)' },
  { speed: 0.501, dir: 45.0, desc: '0.501 m/s' },
  { speed: 5.5, dir: 180.0, desc: '5.5 m/s' },
  { speed: 29.99, dir: 225.0, desc: '29.99 m/s' },
  { speed: 30.0, dir: 360.0, desc: '30.0 m/s (exact upper active boundary)' },
];

for (const tc of activeCases) {
  const copy = aerodromeWindCopy(tc.speed, tc.dir);
  assert(copy.includes('m/s at'), `aerodromeWindCopy(${tc.desc}) -> formatted active vector string ("${copy}")`);
  
  const norm = normalizeWind(tc.speed, tc.dir);
  assertEquals(norm.state, 'active', `normalizeWind(${tc.desc}) -> state MUST be 'active'`);
  assert(typeof norm.u === 'number', `normalizeWind(${tc.desc}) -> u is number`);
  assert(typeof norm.v === 'number', `normalizeWind(${tc.desc}) -> v is number`);
}

console.log('\n======================================================');
console.log(`ADVERSARIAL SUITE FINISHED: Passed: ${passed}, Failed: ${failed}`);
console.log('======================================================\n');

if (failed > 0) {
  process.exit(1);
} else {
  process.exit(0);
}
