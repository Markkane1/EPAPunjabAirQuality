import assert from 'node:assert';
import fs from 'node:fs';
import path from 'node:path';

import {
  haversineDistance,
  forwardBearing,
  backBearing,
  angularDivergence,
  discreteGeodesicIdw,
  polarToCartesianWind,
  cartesianToPolarWind,
  calculateAdvectionFlux,
  pepcCalculateAqi,
  pepcCompositeAqi,
  temporalQcClean,
  checkCompleteness,
  subhourlyLerp,
  equirectangularProject,
} from '../../../src/domain/math';

const pyResults = JSON.parse(
  fs.readFileSync(
    path.resolve('.agents/teamwork/reviewer_m1m2_1/python_results.json'),
    'utf-8'
  )
);

console.log('=== PYTHON VS TYPESCRIPT NUMERICAL PARITY VERIFICATION ===');

const lat1 = 31.5204;
const lon1 = 74.3587;
const lat2 = 33.5651;
const lon2 = 73.0169;

// 1. Haversine
const tsHaversine = haversineDistance(lat1, lon1, lat2, lon2);
const dHav = Math.abs(tsHaversine - pyResults.haversine);
console.log(`Haversine diff: ${dHav} (TS: ${tsHaversine}, Py: ${pyResults.haversine})`);
assert(dHav < 1e-9, `Haversine difference too large: ${dHav}`);

// 2. Forward Bearing
const tsBearing = forwardBearing(lat1, lon1, lat2, lon2);
const dBrg = Math.abs(tsBearing - pyResults.bearing);
console.log(`Forward Bearing diff: ${dBrg} (TS: ${tsBearing}, Py: ${pyResults.bearing})`);
assert(dBrg < 1e-9, `Bearing difference too large: ${dBrg}`);

// 3. Back Bearing
const tsBackBrg = backBearing(lat1, lon1, lat2, lon2);
const dBackBrg = Math.abs(tsBackBrg - pyResults.back_bearing);
console.log(`Back Bearing diff: ${dBackBrg} (TS: ${tsBackBrg}, Py: ${pyResults.back_bearing})`);
assert(dBackBrg < 1e-9, `Back bearing difference too large: ${dBackBrg}`);

// 4. Angular Divergence
const tsDiv = angularDivergence(45.0, 315.0);
assert.strictEqual(tsDiv, pyResults.divergence);

// 5. IDW
const tsIdw = discreteGeodesicIdw(
  [31.5, 74.0],
  [
    { coords: [31.0, 73.5], value: 120.0 },
    { coords: [32.0, 74.5], value: 240.0 },
  ],
  2.0,
  5.0
);
const dIdw = Math.abs((tsIdw ?? 0) - pyResults.idw);
console.log(`IDW diff: ${dIdw} (TS: ${tsIdw}, Py: ${pyResults.idw})`);
assert(dIdw < 1e-9, `IDW difference too large: ${dIdw}`);

// 6. Wind Polar to Cartesian
const tsUV = polarToCartesianWind(12.5, 225.0);
assert(tsUV !== null);
const dU = Math.abs(tsUV[0] - pyResults.wind_polar_to_cart[0]);
const dV = Math.abs(tsUV[1] - pyResults.wind_polar_to_cart[1]);
console.log(`Wind (u,v) diff: dU=${dU}, dV=${dV}`);
assert(dU < 1e-9 && dV < 1e-9);

// 7. Advection Flux (PM2.5)
const tsFlux = calculateAdvectionFlux(
  [31.0, 74.0],
  [31.5, 74.0],
  'PM2.5',
  85.0,
  0.0,
  6.0
);
assert(tsFlux !== null);
const dFlux = Math.abs(tsFlux.flux - pyResults.flux_pm25.flux);
console.log(`Advection Flux diff: ${dFlux}`);
assert(dFlux < 1e-4);

// 8. Flux Physical Dimension Guard
const tsFluxAQI = calculateAdvectionFlux(
  [31.0, 74.0],
  [31.5, 74.0],
  'AQI',
  180.0,
  0.0,
  6.0
);
assert.strictEqual(tsFluxAQI, null);
assert.strictEqual(pyResults.flux_aqi_guard, null);

// 9. PEPC AQI Calculations
assert.strictEqual(pepcCalculateAqi('PM2.5', 120.0), pyResults.aqi_pm25_120);
assert.strictEqual(pepcCalculateAqi('PM2.5', 450.0), pyResults.aqi_pm25_450_clamp);
assert.strictEqual(pepcCompositeAqi(155, 95), pyResults.composite_aqi);

// 10. Temporal QC Clean
const [tsCleaned, tsSpikes] = temporalQcClean(
  [10.0, 15.0, 12.0, 14.0, 15.0, 250.0, 16.0, 14.0, 15.0],
  35.0,
  'PM2.5'
);
assert.strictEqual(tsSpikes, pyResults.qc_clean[1]);
assert.deepStrictEqual(tsCleaned, pyResults.qc_clean[0]);

// 11. Completeness & Lerp
assert.strictEqual(checkCompleteness([10.0, 20.0, null, 40.0], 0.75), pyResults.completeness);
assert.strictEqual(subhourlyLerp([10.0, 20.0, 30.0], 1.25), pyResults.subhourly);

// 12. Equirectangular Projection
const [tsX, tsY] = equirectangularProject(31.5204, 74.3587, 1200.0, 900.0);
const dX = Math.abs(tsX - pyResults.projection[0]);
const dY = Math.abs(tsY - pyResults.projection[1]);
console.log(`Projection diff: dX=${dX}, dY=${dY}`);
assert(dX < 1e-9 && dY < 1e-9);

console.log('>>> ALL PYTHON VS TYPESCRIPT PARITY CHECKS PASSED PERFECTLY! <<<');
