/**
 * Empirical Stress Test and Verification Suite for Milestone M3-M4.
 * Covers:
 * 1. Map Canvas Planimetric Lock (pitch=0, bearing=0, gestures disabled, DOM data attributes).
 * 2. SurfaceLayer (Plate Carree K_X = cos 31 deg, 150x175 grid evaluation speed, distance alpha taper).
 * 3. ChoroplethLayer (41 districts, statutory PEPC hex colors, diagonal hatching for estimated, greedy AABB placement with leader line offset > 20px).
 * 4. WindLayer (3-state display: dropout, calm, active; Station 172 Wazirabad blacklist hard-blocking).
 * 5. FluxLayer (Physical Dimension Guard locking to PM2.5 when AQI selected; 39 border normal chevrons triggering crimson strictly for Phi_j > +0.25 m/s).
 * 6. StationLayer (79 stations: 74 fixed squares, 5 mobile diamonds, 6 aerodrome crosshairs; 13 Lahore micro-airshed stations individually pickable).
 */

import * as fs from 'node:fs';
import * as path from 'node:path';
import { fileURLToPath } from 'node:url';
import { performance } from 'node:perf_hooks';
import * as esbuild from 'esbuild';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Math & Normalizer Imports
import { haversineDistance } from '../../src/domain/math/geodesy';
import {
  anisotropicIdw,
  calculateDistanceOpacity,
  discreteGeodesicIdw,
  DEFAULT_VELOCITY_SATURATION_MS,
  MAX_ANISOTROPIC_MULTIPLIER,
  MIN_ANISOTROPIC_MULTIPLIER,
} from '../../src/domain/math/idw';
import {
  calculateAdvectionFlux,
  MAX_TRANSPORT_CONE_DEG,
  MAX_TRANSPORT_DISTANCE_KM,
} from '../../src/domain/math/flux';
import {
  pepcInterpolateColor,
} from '../../src/domain/math/pepc_aqi';
import {
  pepcColorForAqi,
} from '../../src/workstation/state';
import {
  checkAabbCollision,
  equirectangularProject,
  equirectangularUnproject,
  greedyLabelPlacement,
  KX_MERIDIONAL,
  LABEL_CANDIDATE_OFFSETS,
  LEADER_LINE_THRESHOLD_PX,
  STANDARD_PARALLEL_DEG,
} from '../../src/domain/math/projection';
import {
  centroidLngLat,
  isStationBlacklisted,
  normalizeDistrict,
  normalizeStation,
  normalizeWind,
} from '../../src/domain/normalizer/dataNormalizer';

// Map & Layer Imports (Layers imported directly, MapCanvas bundled via esbuild to handle css)
import {
  createSurfaceLayer,
  GRID_HEIGHT,
  GRID_WIDTH,
  PUNJAB_SURFACE_BOUNDS,
} from '../../src/map/layers/SurfaceLayer';
import { createChoroplethLayers } from '../../src/map/layers/ChoroplethLayer';
import { createWindLayers } from '../../src/map/layers/WindLayer';
import { createFluxLayers } from '../../src/map/layers/FluxLayer';
import { createStationLayers } from '../../src/map/layers/StationLayer';

let totalAssertions = 0;
let passedAssertions = 0;
let failedAssertions = 0;

function assert(condition: boolean, message: string): void {
  totalAssertions++;
  if (!condition) {
    failedAssertions++;
    console.error(`  [FAIL] Assertion failed: ${message}`);
    throw new Error(`Assertion failed: ${message}`);
  } else {
    passedAssertions++;
  }
}

function assertClose(actual: number, expected: number, tolerance: number, message: string): void {
  totalAssertions++;
  const diff = Math.abs(actual - expected);
  if (diff > tolerance) {
    failedAssertions++;
    console.error(`  [FAIL] ${message}: actual ${actual} != expected ${expected} (diff ${diff} > tol ${tolerance})`);
    throw new Error(`${message}: actual ${actual} != expected ${expected}`);
  } else {
    passedAssertions++;
  }
}

// Minimal DOM canvas mock for testing SurfaceLayer in Node.js
function setupCanvasMock(): void {
  if (typeof (globalThis as any).document === 'undefined') {
    (globalThis as any).document = {
      createElement: (tag: string) => {
        if (tag === 'canvas') {
          return {
            width: 0,
            height: 0,
            getContext: () => ({
              createImageData: (w: number, h: number) => ({
                width: w,
                height: h,
                data: new Uint8ClampedArray(w * h * 4),
              }),
              putImageData: () => {},
            }),
          };
        }
        return {};
      },
    };
  }
}

async function runM3M4EmpiricalChallenges() {
  console.log('=================================================================');
  console.log('STARTING EMPIRICAL CHALLENGER VERIFICATION FOR MILESTONE M3-M4');
  console.log('=================================================================\n');

  setupCanvasMock();

  // Load baseline datasets
  const repoRoot = path.resolve(__dirname, '../..');
  const baselineRaw = JSON.parse(
    fs.readFileSync(path.join(repoRoot, 'data', 'baseline', 'baseline_data.json'), 'utf8')
  );
  const airportsRaw = JSON.parse(
    fs.readFileSync(path.join(repoRoot, 'data', 'baseline', 'airports.json'), 'utf8')
  );

  const rawDistricts = Array.isArray(baselineRaw.districts)
    ? baselineRaw.districts
    : Object.values(baselineRaw.districts);
  const rawStations = Array.isArray(baselineRaw.stations)
    ? baselineRaw.stations
    : Object.values(baselineRaw.stations);
  const borderSamples = baselineRaw.tbgeo?.samples ?? baselineRaw.transboundary_geometry?.samples ?? [];

  const districts = rawDistricts.map(normalizeDistrict);
  const stations = rawStations.map(normalizeStation);
  const airports = airportsRaw.map((a: any) => ({
    icao: a.icao,
    name: a.name,
    latitude: a.latitude,
    longitude: a.longitude,
    coordinates: [a.longitude, a.latitude] as [number, number],
  }));

  // =================================================================
  // GROUP 1: MAP CANVAS PLANIMETRIC LOCK CHALLENGE
  // =================================================================
  console.log('--- GROUP 1: Map Canvas Planimetric Lock Challenge ---');

  // Bundle MapCanvas via esbuild with css: empty
  const mapCanvasBuild = await esbuild.build({
    entryPoints: [path.join(repoRoot, 'src', 'map', 'MapCanvas.tsx')],
    bundle: true,
    format: 'cjs',
    write: false,
    external: ['react', 'react-dom', 'maplibre-gl', '@deck.gl/mapbox', '@deck.gl/layers', '@deck.gl/core'],
    loader: { '.css': 'empty' },
  });
  const mapCanvasCode = mapCanvasBuild.outputFiles[0].text;
  const mapCanvasModule: any = { exports: {} };
  const runModule = new Function('module', 'exports', 'require', mapCanvasCode);
  runModule(mapCanvasModule, mapCanvasModule.exports, (mod: string) => {
    if (mod === 'react') return { forwardRef: (f: any) => f, useEffect: () => {}, useImperativeHandle: () => {}, useRef: () => ({ current: null }), useState: (v: any) => [v, () => {}] };
    if (mod === 'maplibre-gl') return {};
    if (mod === '@deck.gl/mapbox') return { MapboxOverlay: class {} };
    if (mod === '@deck.gl/layers') return {};
    if (mod === '@deck.gl/core') return {};
    return {};
  });

  const { MAP_LOCK, PUNJAB_BOUNDS, LAHORE_CENTER } = mapCanvasModule.exports;

  // Verify MAP_LOCK structure
  assert(MAP_LOCK !== undefined, 'MAP_LOCK must be exported from MapCanvas');
  assert(MAP_LOCK.pitch === 0, 'MAP_LOCK.pitch must be strictly 0');
  assert(MAP_LOCK.maxPitch === 0, 'MAP_LOCK.maxPitch must be strictly 0');
  assert(MAP_LOCK.bearing === 0, 'MAP_LOCK.bearing must be strictly 0');
  assert(MAP_LOCK.dragRotate === false, 'MAP_LOCK.dragRotate must be false');
  assert(MAP_LOCK.touchPitch === false, 'MAP_LOCK.touchPitch must be false');

  // Verify geographic constants
  assert(PUNJAB_BOUNDS[0][0] === 69.3 && PUNJAB_BOUNDS[0][1] === 27.7, 'PUNJAB_BOUNDS min [69.3, 27.7]');
  assert(PUNJAB_BOUNDS[1][0] === 75.5 && PUNJAB_BOUNDS[1][1] === 34.15, 'PUNJAB_BOUNDS max [75.5, 34.15]');
  assert(LAHORE_CENTER[0] === 74.3587 && LAHORE_CENTER[1] === 31.5204, 'LAHORE_CENTER [74.3587, 31.5204]');

  // Verify MapCanvas.tsx source code contains hard gesture disabling
  const mapCanvasSource = fs.readFileSync(path.join(repoRoot, 'src', 'map', 'MapCanvas.tsx'), 'utf8');
  assert(mapCanvasSource.includes('map.dragRotate.disable()'), 'MapCanvas must call map.dragRotate.disable()');
  assert(mapCanvasSource.includes('map.touchZoomRotate.disableRotation()'), 'MapCanvas must call map.touchZoomRotate.disableRotation()');
  assert(mapCanvasSource.includes('map.touchPitch.disable()'), 'MapCanvas must call map.touchPitch.disable()');
  assert(mapCanvasSource.includes('map.keyboard.disableRotation()'), 'MapCanvas must call map.keyboard.disableRotation()');
  assert(mapCanvasSource.includes('data-pitch={MAP_LOCK.pitch}'), 'MapCanvas must expose data-pitch={MAP_LOCK.pitch}');
  assert(mapCanvasSource.includes('data-map-lock='), 'MapCanvas must expose data-map-lock attribute');

  console.log('  [PASS] Planimetric Lock verified: pitch=0, bearing=0, rotation/pitch gestures disabled.\n');

  // =================================================================
  // GROUP 2: SURFACE LAYER CHALLENGE (Plate Carree, 150x175, Alpha Taper)
  // =================================================================
  console.log('--- GROUP 2: SurfaceLayer Plate Carree & Performance Challenge ---');

  // Verify Plate Carree factor
  const expectedKx = Math.cos((31.0 * Math.PI) / 180.0);
  assertClose(KX_MERIDIONAL, expectedKx, 1e-12, 'KX_MERIDIONAL must equal cos(31 deg)');
  assertClose(KX_MERIDIONAL, 0.857167300702, 1e-9, 'KX_MERIDIONAL approx 0.857167');
  assert(STANDARD_PARALLEL_DEG === 31.0, 'Standard parallel must be 31.0 deg');

  // Verify surface bounds and grid dimensions
  assert(GRID_WIDTH === 150, 'Grid width must be 150');
  assert(GRID_HEIGHT === 175, 'Grid height must be 175');
  assert(PUNJAB_SURFACE_BOUNDS[0] === 69.10, 'Bounds lonMin 69.10');
  assert(PUNJAB_SURFACE_BOUNDS[1] === 27.55, 'Bounds latMin 27.55');
  assert(PUNJAB_SURFACE_BOUNDS[2] === 75.75, 'Bounds lonMax 75.75');
  assert(PUNJAB_SURFACE_BOUNDS[3] === 34.30, 'Bounds latMax 34.30');

  // Distance Alpha Taper Empirical Tests
  assert(calculateDistanceOpacity(0.0) === 235, 'Opacity at 0km must be 235');
  assert(calculateDistanceOpacity(44.9) === 235, 'Opacity at 44.9km must be 235');
  assert(calculateDistanceOpacity(45.0) === 235, 'Opacity at 45.0km must be 235');
  assert(calculateDistanceOpacity(92.5) === 165, 'Opacity at 92.5km midpoint must be 165');
  assert(calculateDistanceOpacity(140.0) === 95, 'Opacity at 140km must be 95');
  assert(calculateDistanceOpacity(250.0) === 95, 'Opacity at 250km must be 95');

  // Verify monotonicity of alpha taper across [0, 200] km
  let prevAlpha = 236;
  for (let km = 0; km <= 200; km += 5) {
    const a = calculateDistanceOpacity(km);
    assert(a <= prevAlpha, `Alpha at ${km}km (${a}) must be <= alpha at ${km - 5}km (${prevAlpha})`);
    assert(a >= 95 && a <= 235, `Alpha at ${km}km (${a}) must be in [95, 235]`);
    prevAlpha = a;
  }

  // Anisotropic wind-steered physics verification
  const centerTarget: [number, number] = [100, 100];
  const stationUpwind = [{ coords_px: [90, 100] as [number, number], value: 100, u: 5.0, v: 0.0 }]; // wind blowing east towards target
  const stationDownwind = [{ coords_px: [110, 100] as [number, number], value: 100, u: 5.0, v: 0.0 }]; // wind blowing east away from target

  const [valUpwind] = anisotropicIdw(centerTarget, stationUpwind);
  const [valDownwind] = anisotropicIdw(centerTarget, stationDownwind);
  assert(valUpwind > 0 && valDownwind > 0, 'Anisotropic values must be positive');

  // Adversarial edge cases for SurfaceLayer:
  assert(createSurfaceLayer({ visible: false, pollutant: 'AQI', stations: [] }) === null, 'SurfaceLayer visible=false must return null');
  assert(createSurfaceLayer({ visible: true, pollutant: 'AQI', stations: [] }) === null, 'SurfaceLayer empty stations must return null');
  
  // Non-finite values in stations
  const nonFiniteLayer = createSurfaceLayer({
    visible: true,
    pollutant: 'AQI',
    stations: [
      { id: '1', latitude: 31.5, longitude: 74.3, value: NaN },
      { id: '2', latitude: 31.6, longitude: 74.4, value: Infinity },
    ],
  });
  assert(nonFiniteLayer === null, 'SurfaceLayer with only NaN/Infinity values must return null');

  // Benchmark 150x175 grid evaluation speed
  const stValues: Record<string, number> = {};
  const stWinds: Record<string, [number, number]> = {};
  stations.forEach((s) => {
    stValues[s.id] = 120.0;
    stWinds[s.id] = [2.5, -1.0];
  });

  const iterations = 5;
  const startEval = performance.now();
  for (let iter = 0; iter < iterations; iter++) {
    const layer = createSurfaceLayer({
      visible: true,
      mode: 'anisotropic_wind_steered',
      pollutant: 'PM2.5',
      stations: stations.map((s) => ({
        id: s.id,
        name: s.name,
        latitude: s.latitude,
        longitude: s.longitude,
      })),
      stationValues: stValues,
      stationWinds: stWinds,
    });
    assert(layer !== null, `SurfaceLayer must not be null (iter ${iter})`);
  }
  const totalEvalMs = performance.now() - startEval;
  const avgEvalMs = totalEvalMs / iterations;
  console.log(`  [Benchmark] 150x175 grid evaluated in avg ${avgEvalMs.toFixed(2)} ms/frame across ${iterations} runs`);
  assert(avgEvalMs < 120.0, `150x175 grid evaluation must be fast (< 120 ms), took ${avgEvalMs.toFixed(2)} ms`);

  // Test discrete geodesic mode
  const discreteLayer = createSurfaceLayer({
    visible: true,
    mode: 'discrete_geodesic_idw',
    pollutant: 'AQI',
    stations: stations.map((s) => ({
      id: s.id,
      name: s.name,
      latitude: s.latitude,
      longitude: s.longitude,
    })),
    stationValues: stValues,
  });
  assert(discreteLayer !== null, 'Discrete geodesic SurfaceLayer must not be null');

  console.log('  [PASS] SurfaceLayer verified: Plate Carree, 150x175 grid speed, and alpha taper.\n');

  // =================================================================
  // GROUP 3: CHOROPLETH LAYER CHALLENGE (41 Districts, Hatching, Labels)
  // =================================================================
  console.log('--- GROUP 3: ChoroplethLayer 41 Districts & Greedy AABB Labels ---');

  assert(districts.length === 41, `Must have exactly 41 districts, found ${districts.length}`);

  // Test Statutory PEPC Palette across all 7 statutory tiers
  const pepcCases: Array<[number, string]> = [
    [25, '#009966'],  // Good
    [75, '#58B947'],  // Satisfactory
    [150, '#FFDE33'], // Moderate
    [250, '#FF9933'], // Poor
    [350, '#CC0033'], // Very Poor
    [450, '#901530'], // Severe
    [550, '#C00000'], // Hazardous
  ];

  for (const [aqi, expectedHex] of pepcCases) {
    const res = pepcColorForAqi(aqi);
    assert(res.hex.toUpperCase() === expectedHex, `AQI ${aqi} must map to ${expectedHex}, got ${res.hex}`);
  }

  // Create choropleth layers with baseline districts (all monitored)
  const districtValues: Record<string, number | null> = {};
  districts.forEach((d, idx) => {
    districtValues[d.id] = (idx % 2 === 0) ? (idx * 12 + 30) : null;
  });

  const baseChLayers = createChoroplethLayers({
    districts,
    districtValues,
    pollutant: 'AQI',
    visible: true,
  });

  // With all districts monitored, baseline produces polygon and text layers
  const basePolygonLayer = baseChLayers.find((l) => l.id === 'district-choropleth-layer');
  const baseLabelLayer = baseChLayers.find((l) => l.id === 'district-labels');
  assert(basePolygonLayer !== undefined, 'district-choropleth-layer must exist in baseChLayers');
  assert(baseLabelLayer !== undefined, 'district-labels must exist in baseChLayers');

  // Now create an adversarial scenario with 5 estimated districts
  const mixedDistricts = districts.map((d, idx) => ({
    ...d,
    isEstimated: idx < 5, // first 5 districts estimated
  }));

  const hatchChLayers = createChoroplethLayers({
    districts: mixedDistricts,
    districtValues,
    pollutant: 'AQI',
    visible: true,
  });

  const hatchLayer = hatchChLayers.find((l) => l.id === 'district-hatch-layer');
  assert(hatchLayer !== undefined, 'district-hatch-layer must exist when estimated districts present');
  const hatchData = (hatchLayer as any).props.data as any[];
  assert(hatchData.length > 0, `Hatch layer must have generated paths, got ${hatchData.length}`);

  // Now create an adversarial dense cluster scenario where 7 districts share the exact same anchor
  // to force candidate offsets >= 5 ([0, 26.0] > 20px) and trigger district-label-leaders LineLayer
  const clusteredDistricts = districts.slice(0, 8).map((d) => ({
    ...d,
    centroid: [74.35, 31.52] as [number, number],
    labelCoordinates: [74.35, 31.52] as [number, number],
  }));

  const clusteredChLayers = createChoroplethLayers({
    districts: clusteredDistricts,
    districtValues,
    pollutant: 'AQI',
    visible: true,
  });

  const leadersLayer = clusteredChLayers.find((l) => l.id === 'district-label-leaders');
  assert(leadersLayer !== undefined, 'district-label-leaders LineLayer must exist when offsets > 20px occur');
  const leaderData = (leadersLayer as any).props.data as any[];
  assert(leaderData.length > 0, `Leader lines must be generated for congested labels, got ${leaderData.length}`);

  // Verify Greedy AABB label collision placement on all 41 districts
  const labelItems = districts.map((d) => {
    const anchor = d.centroid ? centroidLngLat(d.centroid) : d.labelCoordinates;
    const [x, y] = equirectangularProject(anchor[1], anchor[0]);
    return {
      district_id: d.id,
      text: d.name,
      x,
      y,
      width: Math.max(36, d.name.length * 6.8),
      height: 14,
    };
  });

  const placedResults = greedyLabelPlacement(labelItems);
  assert(placedResults.length === 41, `All 41 districts must have placed labels, got ${placedResults.length}`);

  // Adversarial check: verify ZERO overlapping bounding boxes among placed labels
  let overlapCount = 0;
  for (let i = 0; i < placedResults.length; i++) {
    for (let j = i + 1; j < placedResults.length; j++) {
      const box1 = placedResults[i].bounding_box;
      const box2 = placedResults[j].bounding_box;
      if (checkAabbCollision(box1, box2)) {
        overlapCount++;
      }
    }
  }
  assert(overlapCount === 0, `Greedy AABB labels must have 0 overlaps, found ${overlapCount}`);

  // Leader line threshold check: offset > 20px <=> has_leader_line === true
  for (const label of placedResults) {
    const offset = Math.hypot(label.offset_x, label.offset_y);
    if (offset > LEADER_LINE_THRESHOLD_PX) {
      assert(label.has_leader_line === true, `Label ${label.text} offset ${offset.toFixed(1)}px > 20 must have leader line`);
    } else {
      assert(label.has_leader_line === false, `Label ${label.text} offset ${offset.toFixed(1)}px <= 20 must not have leader line`);
    }
  }

  console.log('  [PASS] ChoroplethLayer verified: 41 districts, statutory PEPC colors, hatching, 0 AABB collisions.\n');

  // =================================================================
  // GROUP 4: WIND LAYER CHALLENGE (3 States & Station 172 Blacklist)
  // =================================================================
  console.log('--- GROUP 4: WindLayer 3-State Display & Wazirabad Blacklist Challenge ---');

  // Test 3 states via normalizeWind
  const dropoutNorm = normalizeWind(null, null, '24');
  assert(dropoutNorm.state === 'dropout', 'null wind must yield state=dropout');
  assert(dropoutNorm.speed === null, 'dropout speed must be null');

  // Exact calm vs active threshold at 0.50 m/s
  const calmBorder = normalizeWind(0.4999, 120, '24');
  assert(calmBorder.state === 'calm', 'speed 0.4999 m/s must yield state=calm');
  const activeBorder = normalizeWind(0.5000, 120, '24');
  assert(activeBorder.state === 'active', 'speed 0.5000 m/s must yield state=active');

  // Adversarial unphysical wind speeds
  assert(normalizeWind(-0.01, 120, '24').state === 'dropout', 'negative speed must yield dropout');
  assert(normalizeWind(30.01, 120, '24').state === 'dropout', '>30 m/s speed must yield dropout');
  assert(normalizeWind(NaN, 120, '24').state === 'dropout', 'NaN speed must yield dropout');
  assert(normalizeWind(5.0, -1, '24').state === 'dropout', 'negative direction must yield dropout');
  assert(normalizeWind(5.0, 360.1, '24').state === 'dropout', '>360 direction must yield dropout');

  const calmNorm = normalizeWind(0.35, 120, '24');
  assert(calmNorm.state === 'calm', 'speed 0.35 m/s must yield state=calm');
  assert(calmNorm.speed === 0.35, 'calm speed must be preserved');

  const activeNorm = normalizeWind(4.2, 270, '24');
  assert(activeNorm.state === 'active', 'speed 4.2 m/s must yield state=active');
  assert(activeNorm.speed === 4.2, 'active speed must be 4.2');

  // Station 172 Wazirabad Blacklist Hard-Blocking - Exhaustive Alias Probing
  const blacklistAliases = [
    '172',
    172,
    'wazirabad',
    'WAZIRABAD',
    'Wazirabad AQMS',
    'pk_waz_001',
    'wazirabad station',
  ];
  for (const alias of blacklistAliases) {
    assert(isStationBlacklisted(alias) === true, `Alias "${alias}" must be blacklisted`);
    const norm = normalizeWind(5.5, 90, alias);
    assert(norm.blacklisted === true, `Alias "${alias}" must have blacklisted=true`);
    assert(norm.state === 'blacklisted', `Alias "${alias}" must have state=blacklisted`);
    assert(norm.blacklistReason === 'ANEMOMETER BLACKLISTED (VANE OFFSET)', `Alias "${alias}" reason check`);
  }
  assert(isStationBlacklisted('24') === false, 'Station "24" must not be blacklisted');
  assert(isStationBlacklisted('Lahore') === false, 'Station "Lahore" must not be blacklisted');

  // Test createWindLayers output with mixed states and Station 172
  const stationWindsMap: Record<string, [number, number]> = {
    '172': [4.0, 4.0], // Wazirabad with active telemetry - MUST BE HARD BLOCKED
    '24': [0.2, 0.1],  // Safari Park - CALM (<0.50 m/s)
    '25': [3.0, 2.0],  // Active wind
    // Other stations will be null/dropout
  };

  const windLayers = createWindLayers({
    districts,
    stations,
    airports,
    stationWinds: stationWindsMap,
    visible: true,
  });

  const activeVectorLayer = windLayers.find((l) => l.id === 'wind-active-vectors');
  const calmCircleLayer = windLayers.find((l) => l.id === 'wind-calm-circles');
  const dropoutGlyphLayer = windLayers.find((l) => l.id === 'wind-dropout-glyphs');
  const blacklistBadgeLayer = windLayers.find((l) => l.id === 'wind-blacklisted-badges');

  assert(activeVectorLayer !== undefined, 'wind-active-vectors must exist');
  assert(calmCircleLayer !== undefined, 'wind-calm-circles must exist');
  assert(dropoutGlyphLayer !== undefined, 'wind-dropout-glyphs must exist');
  assert(blacklistBadgeLayer !== undefined, 'wind-blacklisted-badges must exist');

  // Verify Wazirabad is in blacklist layer and NOT in active vector layer
  const blacklistData = (blacklistBadgeLayer as any).props.data as any[];
  assert(blacklistData.some((it) => it.name.includes('Wazirabad') || it.id.includes('172')), 'Wazirabad must be in blacklisted layer');

  const activeData = (activeVectorLayer as any).props.data as any[];
  assert(!activeData.some((it) => it.item?.name?.includes('Wazirabad') || it.item?.id?.includes('172')), 'Wazirabad must NEVER appear in active vector layer');

  console.log('  [PASS] WindLayer verified: 3 states (dropout/calm/active) and Wazirabad hard-block.\n');

  // =================================================================
  // GROUP 5: FLUX LAYER CHALLENGE (Dimension Guard & Border Chevrons)
  // =================================================================
  console.log('--- GROUP 5: FluxLayer Physical Dimension Guard & Border Chevrons ---');

  // Advection flux physical cutoff tests: d <= 180 km and cone <= 35 deg
  assert(MAX_TRANSPORT_DISTANCE_KM === 180.0, 'MAX_TRANSPORT_DISTANCE_KM must be 180.0');
  assert(MAX_TRANSPORT_CONE_DEG === 35.0, 'MAX_TRANSPORT_CONE_DEG must be 35.0');

  // Physical Dimension Guard:
  // When AQI is passed, links must use pm25Values
  const testDistWinds: Record<string, [number, number]> = {};
  districts.forEach((d) => {
    testDistWinds[d.name] = [4.0, 0.0]; // eastward wind
  });

  const testDistrictAqiVals: Record<string, number> = {};
  districts.forEach((d) => {
    testDistrictAqiVals[d.name] = 350.0;
  });

  // 1. AQI selected, but pm25Values is EMPTY -> must yield ZERO flux links!
  const fluxEmptyPm25 = createFluxLayers({
    districts,
    districtValues: testDistrictAqiVals,
    pm25Values: {}, // empty!
    districtWinds: testDistWinds,
    borderSamples,
    pollutant: 'AQI',
    visible: true,
  });
  const arcLayerEmpty = fluxEmptyPm25.find((l) => l.id === 'advection-flux-arcs');
  const arcLinksEmpty = arcLayerEmpty ? (arcLayerEmpty as any).props.data.length : 0;
  assert(arcLinksEmpty === 0, 'When AQI selected and pm25Values empty, advection arcs must be 0 (Dimension Guard locked)');

  // 2. AQI selected, with pm25Values provided -> must generate flux links based on pm25Values
  const testPm25Vals: Record<string, number> = {};
  districts.forEach((d) => {
    testPm25Vals[d.name] = 120.0;
  });

  const fluxWithPm25 = createFluxLayers({
    districts,
    districtValues: testDistrictAqiVals,
    pm25Values: testPm25Vals,
    districtWinds: testDistWinds,
    borderSamples,
    pollutant: 'AQI',
    visible: true,
  });
  const arcLayerWithPm25 = fluxWithPm25.find((l) => l.id === 'advection-flux-arcs');
  assert(arcLayerWithPm25 !== undefined, 'Advection arcs must exist when pm25Values provided');
  const arcLinksCount = (arcLayerWithPm25 as any).props.data.length;
  assert(arcLinksCount > 0 && arcLinksCount <= 60, `Flux links must be in (0, 60], got ${arcLinksCount}`);

  // Transboundary Border Normal Chevrons (39 nodes) Challenge
  assert(borderSamples.length === 39, `Must have exactly 39 border normal nodes, got ${borderSamples.length}`);

  // Test chevron triggers across normal dot product Phi_j = u*nx + v*ny
  // Case A: Strong Inflow (Phi > +0.25 m/s) -> Statutory Crimson [192, 0, 0, 240]
  // Case B: Strong Outflow (Phi < -0.25 m/s) -> Outflow Teal [95, 196, 196, 220]
  // Case C: Deadband (-0.25 <= Phi <= +0.25) -> NO CHEVRON

  // Synthetic border samples: node 0 pointing inwards (nx=-1, ny=0), node 1 pointing outwards
  const syntheticSamples = [
    [74.5, 31.5, -1.0, 0.0], // Node 0: normal points WEST into Punjab
    [74.6, 31.6, 1.0, 0.0],  // Node 1: normal points EAST
  ];

  // Wind vector: u = -2.0 (blowing WEST into Punjab)
  // For Node 0: Phi = u*nx + v*ny = (-2.0)*(-1.0) = +2.0 > +0.25 -> CRIMSON
  // For Node 1: Phi = (-2.0)*(1.0) = -2.0 < -0.25 -> TEAL
  const customWinds: Record<string, [number, number]> = {};
  districts.forEach((d) => {
    customWinds[d.name] = [-2.0, 0.0];
  });

  const fluxChevrons = createFluxLayers({
    districts,
    districtValues: testDistrictAqiVals,
    pm25Values: testPm25Vals,
    districtWinds: customWinds,
    borderSamples: syntheticSamples,
    pollutant: 'AQI',
    visible: true,
  });

  const chevronLayer = fluxChevrons.find((l) => l.id === 'transboundary-chevrons');
  assert(chevronLayer !== undefined, 'transboundary-chevrons layer must exist');
  const chevronData = (chevronLayer as any).props.data as any[];

  const node0Chevron = chevronData.find((c) => Math.abs(c.lon - 74.5) < 0.01);
  assert(node0Chevron !== undefined, 'Node 0 chevron must exist');
  assert(node0Chevron.phi > 0.25, `Node 0 phi must be > 0.25, got ${node0Chevron.phi}`);
  assert(
    node0Chevron.color[0] === 192 && node0Chevron.color[1] === 0 && node0Chevron.color[2] === 0,
    `Node 0 chevron color must be crimson [192, 0, 0], got ${JSON.stringify(node0Chevron.color)}`
  );

  const node1Chevron = chevronData.find((c) => Math.abs(c.lon - 74.6) < 0.01);
  assert(node1Chevron !== undefined, 'Node 1 chevron must exist');
  assert(node1Chevron.phi < -0.25, `Node 1 phi must be < -0.25, got ${node1Chevron.phi}`);
  assert(
    node1Chevron.color[0] === 95 && node1Chevron.color[1] === 196 && node1Chevron.color[2] === 196,
    `Node 1 chevron color must be teal [95, 196, 196], got ${JSON.stringify(node1Chevron.color)}`
  );

  // Deadband check: u = 0.1, nx = 1.0 => Phi = +0.10 <= +0.25 -> NO CHEVRON
  const deadbandWinds: Record<string, [number, number]> = {};
  districts.forEach((d) => {
    deadbandWinds[d.name] = [0.10, 0.0];
  });
  const deadbandFlux = createFluxLayers({
    districts,
    districtValues: testDistrictAqiVals,
    pm25Values: testPm25Vals,
    districtWinds: deadbandWinds,
    borderSamples: syntheticSamples,
    pollutant: 'AQI',
    visible: true,
  });
  const deadbandChevronLayer = deadbandFlux.find((l) => l.id === 'transboundary-chevrons');
  const deadbandChevronsCount = deadbandChevronLayer ? (deadbandChevronLayer as any).props.data.length : 0;
  assert(deadbandChevronsCount === 0, `Deadband wind (Phi=0.10) must produce 0 chevrons, got ${deadbandChevronsCount}`);

  console.log('  [PASS] FluxLayer verified: Dimension Guard locking to PM2.5 and 39 border normal crimson triggers.\n');

  // =================================================================
  // GROUP 6: STATION LAYER CHALLENGE (79 Stations + 13 Lahore Micro-airshed)
  // =================================================================
  console.log('--- GROUP 6: StationLayer 79 Stations & Lahore Micro-Airshed Picking ---');

  // Station counts verification
  const fixedCount = stations.filter((s) => !s.mobile && s.stationType !== 'mobile').length;
  const mobileCount = stations.filter((s) => s.mobile || s.stationType === 'mobile').length;
  const aerodromeCount = airports.length;

  assert(fixedCount === 74, `Fixed stations must be 74, got ${fixedCount}`);
  assert(mobileCount === 5, `Mobile stations must be 5, got ${mobileCount}`);
  assert(aerodromeCount === 6, `Aerodromes must be 6, got ${aerodromeCount}`);
  assert(fixedCount + mobileCount === 79, `Total monitoring stations must be 79, got ${fixedCount + mobileCount}`);

  // Create station layers
  let selectedEntity: any = null;
  const stLayers = createStationLayers({
    stations,
    airports,
    stationValues: stValues,
    pollutant: 'AQI',
    visible: true,
    onSelect: (e) => {
      selectedEntity = e;
    },
  });

  const fixedLayer = stLayers.find((l) => l.id === 'station-fixed-squares');
  const mobileLayer = stLayers.find((l) => l.id === 'station-mobile-diamonds');
  const airportLayer = stLayers.find((l) => l.id === 'station-aerodrome-crosshairs');
  const pickingLayer = stLayers.find((l) => l.id === 'station-picking-hitboxes');

  assert(fixedLayer !== undefined, 'station-fixed-squares layer must exist');
  assert(mobileLayer !== undefined, 'station-mobile-diamonds layer must exist');
  assert(airportLayer !== undefined, 'station-aerodrome-crosshairs layer must exist');
  assert(pickingLayer !== undefined, 'station-picking-hitboxes layer must exist');

  assert((fixedLayer as any).props.data.length === 74, 'Fixed layer must have 74 squares');
  assert((mobileLayer as any).props.data.length === 5, 'Mobile layer must have 5 diamonds');
  assert((airportLayer as any).props.data.length === 12, 'Aerodromes layer must have 12 path segments (6 crosshairs * 2)');

  // Picking layer contains all 74 + 5 + 6 = 85 entities
  const pickingData = (pickingLayer as any).props.data as any[];
  assert(pickingData.length === 85, `Picking layer must have 85 hitboxes (74+5+6), got ${pickingData.length}`);

  // Lahore 13 Micro-airshed Stations Picking Challenge
  const lahoreStations = stations.filter(
    (s) => s.district?.toLowerCase() === 'lahore' || s.isLahore === true
  );
  assert(lahoreStations.length === 13, `Lahore micro-airshed must have exactly 13 stations, found ${lahoreStations.length}`);

  // Verify all 13 Lahore stations have distinct coordinates
  const coordsSet = new Set<string>();
  for (const st of lahoreStations) {
    const key = `${st.coordinates[0].toFixed(5)},${st.coordinates[1].toFixed(5)}`;
    assert(!coordsSet.has(key), `Lahore station ${st.name} (${st.id}) has duplicate coordinates ${key}`);
    coordsSet.add(key);
  }
  assert(coordsSet.size === 13, `All 13 Lahore stations must have unique coordinates, found ${coordsSet.size}`);

  // Simulate picking each Lahore station via pickingLayer onClick
  const onClickHandler = (pickingLayer as any).props.onClick;
  assert(typeof onClickHandler === 'function', 'pickingLayer must have onClick function');

  for (const lahoreSt of lahoreStations) {
    const matchedHitbox = pickingData.find((p) => p.id === lahoreSt.id);
    assert(matchedHitbox !== undefined, `Hitbox for Lahore station ${lahoreSt.name} (${lahoreSt.id}) must exist`);

    onClickHandler({ object: matchedHitbox });
    assert(selectedEntity !== null, `Selected entity must be updated on pick`);
    assert(selectedEntity.id === lahoreSt.id, `Selected ID ${selectedEntity.id} must match picked station ${lahoreSt.id}`);
    assert(selectedEntity.name === lahoreSt.name, `Selected name ${selectedEntity.name} must match ${lahoreSt.name}`);
  }

  console.log('  [PASS] StationLayer verified: 74 fixed, 5 mobile, 6 airports, 13 Lahore stations uniquely pickable.\n');

  // =================================================================
  // SUMMARY
  // =================================================================
  console.log('=================================================================');
  console.log(`ALL EMPIRICAL M3-M4 CHALLENGES PASSED PERFECTLY!`);
  console.log(`Total Assertions Evaluated: ${totalAssertions}`);
  console.log(`Passed:                     ${passedAssertions}`);
  console.log(`Failed:                     ${failedAssertions}`);
  console.log('=================================================================');
}

runM3M4EmpiricalChallenges().catch((err) => {
  console.error('FATAL CHALLENGE ERROR:', err);
  process.exit(1);
});
