import { discreteGeodesicIdw } from '../../../src/domain/math/idw';
import { KX_MERIDIONAL, equirectangularProject, equirectangularUnproject } from '../../../src/domain/math/projection';
import { calculateCpfRose } from '../../../src/domain/math/cpf';
import { checkCompleteness } from '../../../src/domain/math/qc';
import { haversineDistance } from '../../../src/domain/math/geodesy';

function testIdwSingularityClamp() {
  console.log('=== TS 1. DISCRETE GEODESIC IDW SINGULARITY CLAMP TEST ===');
  const target: [number, number] = [31.5204, 74.3587];
  const stA = { coords: [31.5204, 74.3587] as [number, number], value: 100.0 };
  const stB = { coords: [31.5204 + 0.09, 74.3587] as [number, number], value: 50.0 };

  const distB = haversineDistance(target[0], target[1], stB.coords[0], stB.coords[1]);
  console.log(`Distance stA: 0.0 km, Distance stB: ${distB.toFixed(4)} km`);

  const expectedWA = 1.0 / (5.0 ** 2);
  const expectedWB = 1.0 / (distB ** 2);
  const expectedVal = (expectedWA * 100.0 + expectedWB * 50.0) / (expectedWA + expectedWB);

  const valClamped = discreteGeodesicIdw(target, [stA, stB], 2.0, 5.0);
  console.log(`IDW result with d0=5.0: ${valClamped}, Expected: ${expectedVal}`);
  if (valClamped == null || Math.abs(valClamped - expectedVal) > 1e-5) {
    throw new Error(`IDW clamp mismatch: ${valClamped} vs ${expectedVal}`);
  }

  const valSingle = discreteGeodesicIdw(target, [stA], 2.0, 5.0);
  console.log(`Single station at d=0: ${valSingle}`);
  if (valSingle !== 100.0) {
    throw new Error(`Single station expected 100, got ${valSingle}`);
  }

  // Multi-station with both d < d0 (e.g. d = 2.0 km)
  const stC = { coords: [31.5204 + 0.018, 74.3587] as [number, number], value: 80.0 };
  const distC = haversineDistance(target[0], target[1], stC.coords[0], stC.coords[1]);
  console.log(`Distance stC: ${distC.toFixed(4)} km (< d0=5.0 km)`);
  const valSubD0 = discreteGeodesicIdw(target, [stA, stC], 2.0, 5.0);
  console.log(`IDW result with both d < d0: ${valSubD0}, Expected: 90.0`);
  if (valSubD0 == null || Math.abs(valSubD0 - 90.0) > 1e-5) {
    throw new Error(`Sub d0 mismatch: ${valSubD0} vs 90.0`);
  }
  console.log('TS IDW Singularity Clamp: PASSED\n');
}

function testPlateCarree() {
  console.log('=== TS 2. PLATE CARREE ASPECT RATIO K_X = cos 31° TEST ===');
  const cos31 = Math.cos((31.0 * Math.PI) / 180.0);
  console.log(`Theoretical cos(31 deg): ${cos31}`);
  console.log(`KX_MERIDIONAL in code:   ${KX_MERIDIONAL}`);
  if (Math.abs(KX_MERIDIONAL - cos31) > 1e-12) {
    throw new Error('KX_MERIDIONAL mismatch');
  }

  const pt: [number, number] = [31.5, 74.3];
  const px = equirectangularProject(pt[0], pt[1], 1200.0, 900.0);
  const unproj = equirectangularUnproject(px[0], px[1], 1200.0, 900.0);
  console.log(`Forward: ${pt} -> ${px}`);
  console.log(`Inverse: ${px} -> ${unproj}`);
  if (Math.abs(pt[0] - unproj[0]) > 1e-5 || Math.abs(pt[1] - unproj[1]) > 1e-5) {
    throw new Error('Roundtrip projection failed');
  }

  const p0 = equirectangularProject(31.0, 74.0, 1200.0, 900.0);
  const pLon = equirectangularProject(31.0, 75.0, 1200.0, 900.0);
  const pLat = equirectangularProject(32.0, 74.0, 1200.0, 900.0);
  const dx = Math.abs(pLon[0] - p0[0]);
  const dy = Math.abs(pLat[1] - p0[1]);
  const aspect = dx / dy;
  console.log(`dx: ${dx}, dy: ${dy}, aspect: ${aspect}`);
  if (Math.abs(aspect - cos31) > 1e-5) {
    throw new Error('Aspect ratio mismatch');
  }
  console.log('TS Plate Carrée aspect ratio: PASSED\n');
}

function testCpfSuppression() {
  console.log('=== TS 3. CPF N_k < 6 SMALL SAMPLE SUPPRESSION & CALM EXCLUSION TEST ===');
  const obs: any[] = [];
  for (let i = 0; i < 5; i++) {
    obs.push({ concentration: 100.0, wind_speed: 2.0, wind_direction: 0.0 });
  }
  for (let i = 0; i < 3; i++) {
    obs.push({ concentration: 200.0, wind_speed: 2.0, wind_direction: 90.0 });
  }
  for (let i = 0; i < 3; i++) {
    obs.push({ concentration: 50.0, wind_speed: 2.0, wind_direction: 90.0 });
  }
  for (let i = 0; i < 10; i++) {
    obs.push({ concentration: 300.0, wind_speed: 0.2, wind_direction: 0.0 });
  }

  const res = calculateCpfRose(obs, 100.0);
  const sec0 = res.sectors[0];
  const sec4 = res.sectors[4];
  console.log(`Sector 0 (N_k=5) result: ${sec0} (Expected: null)`);
  console.log(`Sector 4 (N_k=6) result: ${sec4} (Expected: 0.5)`);
  if (sec0 !== null) {
    throw new Error(`Sector 0 expected null, got ${sec0}`);
  }
  if (sec4 !== 0.5) {
    throw new Error(`Sector 4 expected 0.5, got ${sec4}`);
  }

  const expectedCalm = Number((10 / 21).toFixed(4));
  console.log(`Calm ratio: ${res.calm_ratio}, Expected: ${expectedCalm}`);
  if (Math.abs(res.calm_ratio - expectedCalm) > 1e-4) {
    throw new Error(`Calm ratio mismatch: ${res.calm_ratio} vs ${expectedCalm}`);
  }
  console.log('TS CPF Small-Sample Suppression & Calm Exclusion: PASSED\n');
}

function testCompleteness() {
  console.log('=== TS 4. 75% TEMPORAL COMPLETENESS RULE TEST ===');
  // 24h
  const p24 = new Array(18).fill(10.0).concat(new Array(6).fill(null));
  const f24 = new Array(17).fill(10.0).concat(new Array(7).fill(null));
  const r24P = checkCompleteness(p24);
  const r24F = checkCompleteness(f24);
  console.log(`24h pass: ${r24P}, fail: ${r24F}`);
  if (r24P !== 10.0 || r24F !== null) throw new Error('24h completeness failed');

  // 7h
  const p7 = new Array(5).fill(20.0).concat(new Array(2).fill(null));
  const f7 = new Array(4).fill(20.0).concat(new Array(3).fill(null));
  const r7P = checkCompleteness(p7);
  const r7F = checkCompleteness(f7);
  console.log(`7h pass: ${r7P}, fail: ${r7F}`);
  if (r7P !== 20.0 || r7F !== null) throw new Error('7h completeness failed');

  // 1h
  const r1P = checkCompleteness([15.0]);
  const r1F = checkCompleteness([null]);
  console.log(`1h pass: ${r1P}, fail: ${r1F}`);
  if (r1P !== 15.0 || r1F !== null) throw new Error('1h completeness failed');

  // 216h
  const p216 = new Array(162).fill(50.0).concat(new Array(54).fill(null));
  const f216 = new Array(161).fill(50.0).concat(new Array(55).fill(null));
  const r216P = checkCompleteness(p216);
  const r216F = checkCompleteness(f216);
  console.log(`216h pass: ${r216P}, fail: ${r216F}`);
  if (r216P !== 50.0 || r216F !== null) throw new Error('216h completeness failed');

  console.log('TS 75% Completeness Rule: PASSED\n');
}

testIdwSingularityClamp();
testPlateCarree();
testCpfSuppression();
testCompleteness();
console.log('ALL TYPESCRIPT MATHEMATICAL SPECIFICATION TESTS PASSED SUCCESSFULLY!');
