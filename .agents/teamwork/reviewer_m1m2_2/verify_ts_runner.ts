import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

import {
  haversineDistance,
  forwardBearing,
  backBearing,
  angularDivergence,
  degreesToSector16,
  sector16ToDegrees,
} from '../../../src/domain/math/geodesy';

import {
  discreteGeodesicIdw,
  discreteGeodesicIdwVector,
  calculateDistanceOpacity,
  anisotropicIdw,
} from '../../../src/domain/math/idw';

import {
  isStationBlacklisted,
  isAnemometerValid,
  isCalmWind,
  polarToCartesianWind,
  cartesianToPolarWind,
  windDirectionToBearing,
} from '../../../src/domain/math/wind';

import {
  calculatePooledP75,
  calculateCpfRose,
} from '../../../src/domain/math/cpf';

import {
  calculateAdvectionFlux,
  calculateReceptorCoupling,
  calculateNetTransportBalance,
} from '../../../src/domain/math/flux';

import {
  calculateDistrictTransboundaryFlux,
  calculateBorderNormalFlux,
  calculateTransboundaryIndex,
} from '../../../src/domain/math/transboundary';

import {
  pepcCalculateAqi,
  pepcCompositeAqi,
  pepcGetCategory,
  pepcGetColor,
  pepcInterpolateColor,
} from '../../../src/domain/math/pepc_aqi';

import {
  temporalQcClean,
  checkCompleteness,
  subhourlyLerp,
} from '../../../src/domain/math/qc';

import {
  equirectangularProject,
  equirectangularUnproject,
  checkAabbCollision,
  greedyLabelPlacement,
} from '../../../src/domain/math/projection';

import {
  normalizeCentroid,
  centroidLngLat,
  normalizeWind,
  isDistrictEstimated,
  shouldApplyDiagonalHatching,
  countStationNetworks,
} from '../../../src/domain/normalizer/dataNormalizer';

// Read inputs from stdin or test_inputs.json
const dirName = path.dirname(fileURLToPath(import.meta.url));
const inputFilePath = path.join(dirName, 'test_cases.json');
const testCases = JSON.parse(fs.readFileSync(inputFilePath, 'utf-8'));

const results: Record<string, any> = {};

// 1. Geodesy
results.geodesy = testCases.geodesy.map((tc: any) => ({
  dist: haversineDistance(tc.lat1, tc.lon1, tc.lat2, tc.lon2),
  fwd_bearing: forwardBearing(tc.lat1, tc.lon1, tc.lat2, tc.lon2),
  back_bearing: backBearing(tc.lat1, tc.lon1, tc.lat2, tc.lon2),
  ang_div: angularDivergence(tc.angle1, tc.angle2),
  sector: degreesToSector16(tc.deg),
  sector_deg: sector16ToDegrees(tc.sector_idx),
}));

// 2. IDW
results.idw = testCases.idw.map((tc: any) => ({
  scalar: discreteGeodesicIdw(tc.target, tc.stations, tc.power, tc.d0),
  vector: discreteGeodesicIdwVector(tc.target, tc.vector_stations, tc.power, tc.d0),
  opacity: calculateDistanceOpacity(tc.km_min),
  anisotropic: anisotropicIdw(tc.target_px, tc.aniso_stations, tc.wind_vector, tc.scale, tc.epsilon_sq),
}));

// 3. Wind
results.wind = testCases.wind.map((tc: any) => ({
  blacklisted: isStationBlacklisted(tc.station_name),
  valid: isAnemometerValid(tc.speed, tc.direction, tc.station_name),
  calm: isCalmWind(tc.speed),
  polar_to_cart: polarToCartesianWind(tc.speed, tc.direction, tc.station_name),
  cart_to_polar: cartesianToPolarWind(tc.u, tc.v),
  bearing: windDirectionToBearing(tc.u, tc.v),
}));

// 4. CPF
results.cpf = testCases.cpf.map((tc: any) => ({
  p75: calculatePooledP75(tc.observations),
  rose: calculateCpfRose(tc.observations, tc.threshold_p75),
}));

// 5. Flux
results.flux = testCases.flux.map((tc: any) => ({
  flux: calculateAdvectionFlux(tc.source, tc.receptor, tc.pollutant, tc.concentration, tc.u, tc.v),
}));

// 6. Transboundary
results.transboundary = testCases.transboundary.map((tc: any) => ({
  district_flux: calculateDistrictTransboundaryFlux(tc.border_dist, tc.india_sectors, tc.conc, tc.u, tc.v, tc.is_est),
  normal_flux: calculateBorderNormalFlux(tc.u, tc.v, tc.nx, tc.ny),
}));

// 7. PEPC AQI
results.pepc_aqi = testCases.pepc_aqi.map((tc: any) => ({
  aqi: pepcCalculateAqi(tc.pollutant, tc.concentration),
  composite: pepcCompositeAqi(tc.pm25, tc.pm10),
  category: pepcGetCategory(tc.test_aqi),
  color: pepcGetColor(tc.test_aqi),
  peqs_rgb: pepcInterpolateColor(tc.value, tc.ref_limit),
}));

// 8. QC
results.qc = testCases.qc.map((tc: any) => ({
  clean: temporalQcClean(tc.series, tc.ref_limit, tc.pollutant),
  completeness: checkCompleteness(tc.series),
  lerp: subhourlyLerp(tc.series, tc.fp),
}));

// 9. Projection
results.projection = testCases.projection.map((tc: any) => {
  const proj = equirectangularProject(tc.lat, tc.lon);
  const unproj = equirectangularUnproject(proj[0], proj[1]);
  return {
    proj,
    unproj,
    collision: checkAabbCollision(tc.box1, tc.box2),
  };
});

// 10. Data Normalizer Traps
results.normalizer = {
  centroid: testCases.normalizer.centroids.map((c: any) => normalizeCentroid(c)),
  winds: testCases.normalizer.winds.map((w: any) => normalizeWind(w.speed, w.direction, w.station)),
  est: testCases.normalizer.districts.map((d: any) => ({
    is_est: isDistrictEstimated(d),
    hatching: shouldApplyDiagonalHatching(d),
  })),
  counts: countStationNetworks(testCases.normalizer.stations),
};

const outputFilePath = path.join(dirName, 'ts_results.json');
fs.writeFileSync(outputFilePath, JSON.stringify(results, null, 2));
console.log('TypeScript math execution complete. Output saved to ts_results.json');
