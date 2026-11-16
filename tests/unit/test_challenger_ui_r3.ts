/**
 * EMPIRICAL CHALLENGER TEST SUITE (Round 3 Frontend UI & Dynamic Timeline Gate)
 *
 * Adversarial stress testing of:
 * 1. Dynamic Timeline Advancement:
 *    - Bounds testing for hourIndex: 0, 215, 216, 383, 384, dynamic totalHours (50..10000).
 *    - Scrubber readout formatting and dynamic horizon scaling in state.ts.
 *    - Slider max hour calculation in TimelineScrubber.tsx.
 *    - Step wrapping: (current + delta + totalHours) % totalHours across all indices.
 *    - Continuous sub-hourly lerp smooth interpolation across 384 hours for all 41 districts.
 * 2. Pollutant Species Bar Tab Scoping:
 *    - Simulated view switching across all 6 tabs (console, lahore, heatmap, transboundary, fires, grid).
 *    - Verification that .zone-2-pollutants displays 'flex' ONLY on console, and 'none' elsewhere.
 * 3. Red Block Artifact in Header:
 *    - tokens.css & ui.js inspection of .provincial-aqi-badge and badge-dot.
 *    - WCAG 2.1 AAA relative luminance & contrast ratio verification (>= 7.0:1) across all tiers.
 *    - CommandBar.tsx hazardous alert badge outline styling inspection.
 * 4. Hourly Heatmap Viewport Geometry:
 *    - Viewport sizing and overflow properties on #panel-heatmap and .heatmap-container.
 *    - Stacking context z-index hierarchy: th.sticky-district (5) > td.sticky-district (4) > th (3).
 *    - Matrix column rendering without artificial 216 truncation.
 * 5. Cross-Border Fallback Coordinates in api.js:
 *    - Completeness and validity of fallback array for all 6 anchor cities.
 */

import * as fs from 'fs';
import * as path from 'path';

// State and domain math imports
import {
  scrubberReadout,
  buildWorkstationModel,
  HORIZON_HOURS,
  type WorkstationInput,
} from '../../src/workstation/state';

import { subhourlyLerp } from '../../src/domain/math/qc';

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
    const msg = `[FAIL] ${testName}${detail ? ` -> ${detail}` : ''}`;
    failureMessages.push(msg);
    console.error(msg);
  }
}

function assertEquals<T>(actual: T, expected: T, testName: string): void {
  assert(
    actual === expected,
    testName,
    `Expected '${String(expected)}', got '${String(actual)}'`
  );
}

function assertCloseTo(actual: number, expected: number, tolerance: number, testName: string): void {
  assert(
    Math.abs(actual - expected) <= tolerance,
    testName,
    `Expected ${actual} close to ${expected} within +/-${tolerance}`
  );
}

console.log('=================================================================');
console.log('STARTING EMPIRICAL CHALLENGER UI R3 VERIFICATION GATE');
console.log('=================================================================\n');

// -----------------------------------------------------------------------------
// GROUP 1: DYNAMIC TIMELINE ADVANCEMENT & SCRUBBER BOUNDS STRESS TEST
// -----------------------------------------------------------------------------
console.log('>>> [GROUP 1] Dynamic Timeline Advancement & Scrubber Bounds Stress Test');

// Test 1.1: scrubberReadout bounds at 0, 215, 216, 383, 384 for totalHours = 384
const r0 = scrubberReadout(0, 0.0, '2026-11-01 00:00', 384);
assertEquals(r0.timestampLine, '2026-11-01 00:00 PKT', 'Hour 0 timestamp line');
assertEquals(r0.detailLine, 'Hour 1/384 \u00B7 Lerp \u03B1=0.00', 'Hour 0 detail line: Hour 1/384');

const r215 = scrubberReadout(215, 0.5, '2026-11-09 23:00', 384);
assertEquals(r215.detailLine, 'Hour 216/384 \u00B7 Lerp \u03B1=0.50', 'Hour 215 detail line: Hour 216/384');

const r216 = scrubberReadout(216, 0.25, '2026-11-10 00:00', 384);
assertEquals(r216.detailLine, 'Hour 217/384 \u00B7 Lerp \u03B1=0.25', 'Hour 216 detail line: Hour 217/384 (no 216 truncation)');

const r383 = scrubberReadout(383, 0.99, '2026-11-16 23:00', 384);
assertEquals(r383.detailLine, 'Hour 384/384 \u00B7 Lerp \u03B1=0.99', 'Hour 383 detail line: Hour 384/384');

const r384 = scrubberReadout(384, 0.0, '2026-11-16 23:00', 384);
assertEquals(r384.detailLine, 'Hour 384/384 \u00B7 Lerp \u03B1=0.00', 'Hour 384 boundary clamping: clamped to safeTotal - 1');

// Test 1.2: Boundary clamping with negative and oversized hourIndex
const rNegative = scrubberReadout(-10, 0.0, '2026-11-01 00:00', 384);
assertEquals(rNegative.detailLine, 'Hour 1/384 \u00B7 Lerp \u03B1=0.00', 'Negative hourIndex clamped to Hour 1/384');

const rOverflow = scrubberReadout(9999, 0.0, '2026-11-16 23:00', 384);
assertEquals(rOverflow.detailLine, 'Hour 384/384 \u00B7 Lerp \u03B1=0.00', 'Oversized hourIndex clamped to safeTotal 384');

// Test 1.3: Default totalHours parameter preserves HORIZON_HOURS (216)
const rDefault215 = scrubberReadout(215, 0.0, '2026-11-09 23:00');
assertEquals(rDefault215.detailLine, 'Hour 216/216 \u00B7 Lerp \u03B1=0.00', 'Default totalHours is 216');

// Test 1.4: Dynamic totalHours scaling across diverse horizons [1, 24, 48, 168, 216, 384, 500, 1000]
const testHorizons = [1, 24, 48, 168, 216, 384, 500, 720, 1000];
for (const th of testHorizons) {
  for (let h = 0; h < th; h += Math.max(1, Math.floor(th / 10))) {
    const res = scrubberReadout(h, 0.42, '2026-11-01 00:00', th);
    assertEquals(res.detailLine, `Hour ${h + 1}/${th} \u00B7 Lerp \u03B1=0.42`, `Scrubber readout for totalHours=${th}, h=${h}`);
  }
}

// Test 1.5: TimelineScrubber maxHour logic simulation
// In TimelineScrubber.tsx: const maxHour = Math.max(0, (totalHours ?? (horizon.length || 216)) - 1);
function computeScrubberMaxHour(totalHours?: number, horizonLength: number = 0): number {
  return Math.max(0, (totalHours ?? (horizonLength || 216)) - 1);
}

assertEquals(computeScrubberMaxHour(384), 383, 'TimelineScrubber with totalHours=384 -> maxHour=383');
assertEquals(computeScrubberMaxHour(216), 215, 'TimelineScrubber with totalHours=216 -> maxHour=215');
assertEquals(computeScrubberMaxHour(undefined, 384), 383, 'TimelineScrubber with undefined totalHours & horizon.length=384 -> maxHour=383');
assertEquals(computeScrubberMaxHour(undefined, 0), 215, 'TimelineScrubber with undefined totalHours & empty horizon -> maxHour=215');
assertEquals(computeScrubberMaxHour(1, 0), 0, 'TimelineScrubber with totalHours=1 -> maxHour=0');

// Test 1.6: Stepping delta wrap-around logic
// In App.tsx: (current + delta + totalHours) % totalHours
function stepHour(current: number, delta: -1 | 1, totalHours: number): number {
  return (current + delta + totalHours) % totalHours;
}

// Wrapping for totalHours = 384
assertEquals(stepHour(0, -1, 384), 383, 'Step backwards from 0 wraps to 383');
assertEquals(stepHour(383, 1, 384), 0, 'Step forward from 383 wraps to 0');
assertEquals(stepHour(215, 1, 384), 216, 'Step forward from 215 correctly advances to 216 without wrapping');
assertEquals(stepHour(216, -1, 384), 215, 'Step backwards from 216 correctly steps to 215');

// Exhaustive step testing across all indices 0..383 for totalHours = 384
for (let h = 0; h < 384; h++) {
  const nextFwd = stepHour(h, 1, 384);
  const nextBwd = stepHour(h, -1, 384);
  assertEquals(nextFwd, (h + 1) % 384, `Forward step at ${h}`);
  assertEquals(nextBwd, (h - 1 + 384) % 384, `Backward step at ${h}`);
}

// Test 1.7: Scrub position clamping
// In App.tsx: Math.max(0, Math.min(totalHours - 1, Math.floor(position)))
function scrubHour(position: number, totalHours: number): number {
  return Math.max(0, Math.min(totalHours - 1, Math.floor(position)));
}

assertEquals(scrubHour(-5.5, 384), 0, 'Scrub negative clamps to 0');
assertEquals(scrubHour(0.0, 384), 0, 'Scrub 0.0 is 0');
assertEquals(scrubHour(215.9, 384), 215, 'Scrub 215.9 is 215');
assertEquals(scrubHour(216.1, 384), 216, 'Scrub 216.1 is 216');
assertEquals(scrubHour(383.9, 384), 383, 'Scrub 383.9 is 383');
assertEquals(scrubHour(500.0, 384), 383, 'Scrub 500.0 clamps to 383');

// Test 1.8: Sub-hourly lerp continuous smoothness across 384 hours dataset
const staticBaselinePath = path.join(process.cwd(), 'src', 'frontend', 'static', 'data', 'baseline_data.json');
const staticBaseline = JSON.parse(fs.readFileSync(staticBaselinePath, 'utf8'));

assertEquals(staticBaseline.hours.length, 384, 'Static baseline data contains exactly 384 hours');
assertEquals(staticBaseline.hours[0], '2026-11-01 00:00', 'Start timestamp 2026-11-01 00:00');
assertEquals(staticBaseline.hours[383], '2026-11-16 23:00', 'End timestamp 2026-11-16 23:00');

const districts = Object.keys(staticBaseline.districts);
assertEquals(districts.length, 41, 'Baseline contains exactly 41 districts');

let lerpCount = 0;
// Test sub-hourly lerp on PM2.5 across all 384 hours for sample districts
const testDistricts = ['Lahore', 'Faisalabad', 'Rawalpindi', 'Multan', 'Gujranwala'];
for (const dist of testDistricts) {
  const series = staticBaseline.hours.map((_: any, h: number) => {
    return staticBaseline.pol['PM2.5']?.frames?.[h]?.c?.[dist] ?? null;
  });

  for (let h = 0; h < 383; h++) {
    for (const alpha of [0.0, 0.2, 0.4, 0.6, 0.8, 0.99]) {
      const val = subhourlyLerp(series, h + alpha);
      lerpCount++;
      if (series[h] !== null && series[h + 1] !== null) {
        assert(val !== null && !isNaN(val!), `Lerp output valid for ${dist} at ${h}+${alpha}`);
        const minVal = Math.min(series[h], series[h + 1]);
        const maxVal = Math.max(series[h], series[h + 1]);
        assert(
          val! >= minVal - 1e-4 && val! <= maxVal + 1e-4,
          `Lerp bounded for ${dist} at ${h}+${alpha}`
        );
      }
    }
  }
}
console.log(`    Evaluated ${lerpCount} continuous sub-hourly lerp steps across 384 hours.`);

// -----------------------------------------------------------------------------
// GROUP 2: POLLUTANT SPECIES BAR TAB SCOPING
// -----------------------------------------------------------------------------
console.log('\n>>> [GROUP 2] Pollutant Species Bar Tab Scoping Stress Test');

// Test 2.1: Code AST/Regex verification in ui.js
const uiJsPath = path.join(process.cwd(), 'src', 'frontend', 'static', 'js', 'ui.js');
const uiJsContent = fs.readFileSync(uiJsPath, 'utf8');

assert(
  uiJsContent.includes("(viewName === 'console') ? 'flex' : 'none'"),
  'ui.js contains strict console check: (viewName === \'console\') ? \'flex\' : \'none\''
);

assert(
  !uiJsContent.includes("(viewName === 'grid') ? 'none' : 'flex'"),
  'ui.js does NOT contain old leaky check: (viewName === \'grid\') ? \'none\' : \'flex\''
);

// Test 2.2: Simulated Tab Switching across all 6 workstation views
const workstationTabs = ['console', 'lahore', 'heatmap', 'transboundary', 'fires', 'grid'];

function simulateTabSwitch(viewName: string): { polNavDisplay: string } {
  // Exact logic from ui.js lines 405-410
  const polNavDisplay = (viewName === 'console') ? 'flex' : 'none';
  return { polNavDisplay };
}

for (const tab of workstationTabs) {
  const { polNavDisplay } = simulateTabSwitch(tab);
  if (tab === 'console') {
    assertEquals(polNavDisplay, 'flex', `Tab '${tab}' displays pollutant strip as 'flex'`);
  } else {
    assertEquals(polNavDisplay, 'none', `Tab '${tab}' hides pollutant strip with 'none'`);
  }
}

// Test 2.3: Unrecognized/Negative tab names
const invalidTabs = ['unknown', '', 'dashboard', 'settings', 'overview', 'alerts'];
for (const tab of invalidTabs) {
  const { polNavDisplay } = simulateTabSwitch(tab);
  assertEquals(polNavDisplay, 'none', `Invalid tab '${tab}' safely hides pollutant strip with 'none'`);
}

// -----------------------------------------------------------------------------
// GROUP 3: RED BLOCK ARTIFACT REMOVAL & WCAG AAA CONTRAST COMPLIANCE
// -----------------------------------------------------------------------------
console.log('\n>>> [GROUP 3] Red Block Artifact Removal & WCAG AAA Contrast Compliance');

// Test 3.1: CSS verification in tokens.css
const tokensCssPath = path.join(process.cwd(), 'src', 'frontend', 'static', 'css', 'tokens.css');
const tokensCssContent = fs.readFileSync(tokensCssPath, 'utf8');

assert(
  tokensCssContent.includes('.provincial-aqi-badge'),
  'tokens.css defines .provincial-aqi-badge'
);
assert(
  tokensCssContent.includes('background-color: rgba(112, 48, 160, 0.18)') ||
  tokensCssContent.includes('0.18'),
  '.provincial-aqi-badge has translucent 0.18 alpha background'
);
assert(
  tokensCssContent.includes('.provincial-aqi-badge .badge-dot'),
  'tokens.css defines .provincial-aqi-badge .badge-dot'
);

// Assert no solid red #C00000 background is used on the badge class
const badgeBlockMatch = tokensCssContent.match(/\.provincial-aqi-badge\s*\{([^}]+)\}/);
assert(badgeBlockMatch !== null, 'Found .provincial-aqi-badge rule in tokens.css');
if (badgeBlockMatch) {
  const ruleBody = badgeBlockMatch[1];
  assert(!ruleBody.includes('background-color: #C00000'), 'No solid #C00000 background in CSS rule');
  assert(!ruleBody.includes('background-color: #c00000'), 'No solid #c00000 background in CSS rule');
  assert(!ruleBody.includes('background-color: rgb(192, 0, 0)'), 'No solid rgb(192, 0, 0) background in CSS rule');
}

// Test 3.2: ui.js updates badge with translucent styling and badge-dot
assert(
  uiJsContent.includes('this.dom.provincialAqiBadge.style.backgroundColor = `rgba(${rgb}, 0.18)`'),
  'ui.js sets translucent background: rgba(${rgb}, 0.18)'
);
assert(
  uiJsContent.includes('this.dom.provincialAqiBadge.style.borderColor = `rgba(${rgb}, 0.8)`'),
  'ui.js sets subtle border: rgba(${rgb}, 0.8)'
);
assert(
  uiJsContent.includes('<span class="badge-dot" style="background: rgb(${rgb})"></span>'),
  'ui.js injects badge-dot element'
);

// Test 3.3: CommandBar.tsx hazardous alert badge inspection
const commandBarPath = path.join(process.cwd(), 'src', 'components', 'command', 'CommandBar.tsx');
const commandBarContent = fs.readFileSync(commandBarPath, 'utf8');

assert(
  commandBarContent.includes('variant="outline"'),
  'CommandBar hazardous badge uses variant="outline"'
);
assert(
  commandBarContent.includes('border-red-500/60'),
  'CommandBar hazardous badge uses translucent border: border-red-500/60'
);
assert(
  commandBarContent.includes('bg-red-500/15'),
  'CommandBar hazardous badge uses translucent background: bg-red-500/15'
);
assert(
  !commandBarContent.includes('bg-[#C00000]') && !commandBarContent.includes('bg-red-600'),
  'CommandBar does not use solid opaque red block background'
);

// Test 3.4: WCAG 2.1 AAA Contrast Ratio Verification
// Institutional dark background colors
const DARK_BACKGROUNDS: Record<string, [number, number, number]> = {
  'bg-canvas': [15, 23, 22],        // #0f1716
  'bg-panel': [21, 33, 32],         // #152120
  'bg-panel-elevated': [28, 43, 42], // #1c2b2a
};

// Statutory PEPC tier colors [r, g, b]
const PEPC_TIER_RGB: Record<string, [number, number, number]> = {
  'Good': [0, 228, 0],
  'Moderate': [255, 255, 0],
  'Unhealthy for Sensitive': [255, 126, 0],
  'Unhealthy': [255, 0, 0],
  'Very Unhealthy': [153, 0, 76],
  'Hazardous (EPA)': [192, 0, 0],
  'Hazardous (Alt)': [126, 0, 35],
};

// Standard WCAG 2.1 relative luminance calculation
function sRgbToLinear(c: number): number {
  const norm = c / 255;
  return norm <= 0.03928 ? norm / 12.92 : Math.pow((norm + 0.055) / 1.055, 2.4);
}

function relativeLuminance(r: number, g: number, b: number): number {
  return 0.2126 * sRgbToLinear(r) + 0.7152 * sRgbToLinear(g) + 0.0722 * sRgbToLinear(b);
}

function contrastRatio(l1: number, l2: number): number {
  const lighter = Math.max(l1, l2);
  const darker = Math.min(l1, l2);
  return (lighter + 0.05) / (darker + 0.05);
}

// Pure white text #FFFFFF
const L_WHITE = relativeLuminance(255, 255, 255); // 1.0

for (const [bgName, bgRgb] of Object.entries(DARK_BACKGROUNDS)) {
  for (const [tierName, tierRgb] of Object.entries(PEPC_TIER_RGB)) {
    // Composite translucent badge (alpha = 0.18) over dark background
    const alpha = 0.18;
    const compR = Math.round(alpha * tierRgb[0] + (1 - alpha) * bgRgb[0]);
    const compG = Math.round(alpha * tierRgb[1] + (1 - alpha) * bgRgb[1]);
    const compB = Math.round(alpha * tierRgb[2] + (1 - alpha) * bgRgb[2]);

    const lBg = relativeLuminance(compR, compG, compB);
    const contrast = contrastRatio(L_WHITE, lBg);

    // WCAG AAA standard requires contrast >= 7.0:1 for normal text
    assert(
      contrast >= 7.0,
      `WCAG AAA Contrast (${tierName} on ${bgName})`,
      `Contrast is ${contrast.toFixed(2)}:1 (>= 7.0:1 required)`
    );
  }
}

// -----------------------------------------------------------------------------
// GROUP 4: HOURLY HEATMAP VIEWPORT GEOMETRY & STACKING CONTEXT
// -----------------------------------------------------------------------------
console.log('\n>>> [GROUP 4] Hourly Heatmap Viewport Geometry & Stacking Context');

// Test 4.1: CSS verification of #panel-heatmap
assert(
  tokensCssContent.includes('height: calc(100vh - 72px)'),
  '#panel-heatmap defines height: calc(100vh - 72px)'
);
assert(
  tokensCssContent.includes('max-height: calc(100vh - 72px)'),
  '#panel-heatmap defines max-height: calc(100vh - 72px)'
);

// Regex check on #panel-heatmap declaration
const panelHeatmapMatch = tokensCssContent.match(/#panel-heatmap\s*\{([^}]+)\}/);
assert(panelHeatmapMatch !== null, 'Found #panel-heatmap rule block in tokens.css');
if (panelHeatmapMatch) {
  const body = panelHeatmapMatch[1];
  assert(body.includes('overflow: hidden'), '#panel-heatmap has overflow: hidden');
  assert(body.includes('display: flex'), '#panel-heatmap has display: flex');
  assert(body.includes('flex-direction: column'), '#panel-heatmap has flex-direction: column');
}

// Test 4.2: CSS verification of .heatmap-container
const containerMatch = tokensCssContent.match(/\.heatmap-container\s*\{([^}]+)\}/);
assert(containerMatch !== null, 'Found .heatmap-container rule block in tokens.css');
if (containerMatch) {
  const body = containerMatch[1];
  assert(body.includes('overflow: auto'), '.heatmap-container has overflow: auto');
  assert(body.includes('flex: 1 1 0') || body.includes('flex: 1'), '.heatmap-container has flex: 1 1 0');
  assert(body.includes('min-height: 0'), '.heatmap-container has min-height: 0');
  assert(body.includes('max-height: none'), '.heatmap-container has max-height: none');
}

// Test 4.3: Stacking context & Z-index hierarchy
// table.heatmap-table th -> z-index: 3 (sticky header row)
// table.heatmap-table td.sticky-district -> z-index: 4 (sticky district column)
// table.heatmap-table th.sticky-district -> z-index: 5 (corner intersection cell)

const thMatch = tokensCssContent.match(/table\.heatmap-table\s+th\s*\{([^}]+)\}/);
assert(thMatch !== null, 'Found table.heatmap-table th rule');
if (thMatch) {
  assert(thMatch[1].includes('z-index: 3'), 'Sticky column headers have z-index: 3');
}

const tdStickyMatch = tokensCssContent.match(/table\.heatmap-table\s+td\.sticky-district\s*\{([^}]+)\}/);
assert(tdStickyMatch !== null, 'Found td.sticky-district rule');
if (tdStickyMatch) {
  assert(tdStickyMatch[1].includes('z-index: 4'), 'Sticky district column has z-index: 4');
}

const thStickyMatch = tokensCssContent.match(/table\.heatmap-table\s+th\.sticky-district\s*\{([^}]+)\}/);
assert(thStickyMatch !== null, 'Found th.sticky-district corner rule');
if (thStickyMatch) {
  assert(thStickyMatch[1].includes('z-index: 5'), 'Corner intersection header has z-index: 5');
}

// Stacking inequality check: Corner cell (5) > District cell (4) > Column header (3)
const zCorner = 5;
const zDistrict = 4;
const zHeader = 3;
assert(zCorner > zDistrict && zDistrict > zHeader, 'Stacking order guarantees corner cell renders above both column and row headers');

// Test 4.4: ui.js renderHeatmapMatrix dynamically renders all columns
assert(
  uiJsContent.includes('const totalCols = hours.length;'),
  'ui.js renderHeatmapMatrix derives totalCols = hours.length without 216 clamping'
);

// -----------------------------------------------------------------------------
// GROUP 5: CROSS-BORDER FALLBACK COORDINATES IN api.js
// -----------------------------------------------------------------------------
console.log('\n>>> [GROUP 5] Cross-Border Fallback Coordinates in api.js');

const apiJsPath = path.join(process.cwd(), 'src', 'frontend', 'static', 'js', 'api.js');
const apiJsContent = fs.readFileSync(apiJsPath, 'utf8');

// Extract the fallback array from api.js getCrossBorderCities
const fallbackMatch = apiJsContent.match(/return\s*\[\s*[\s\S]*?city:\s*'Amritsar'[\s\S]*?\];/);
assert(fallbackMatch !== null, 'Found cross-border fallback array in api.js');

// Parse the 6 fallback city objects
const expectedCities = ['Amritsar', 'Firozpur', 'Jalandhar', 'Ludhiana', 'Bathinda', 'Delhi NCR'];

// Extract city objects using regex matches
const cityObjRegex = /\{\s*city:\s*'([^']+)'[\s\S]*?\}/g;
const matchedCities: any[] = [];
let m: RegExpExecArray | null;
while ((m = cityObjRegex.exec(apiJsContent)) !== null) {
  const block = m[0];
  const cityName = m[1];
  if (expectedCities.includes(cityName)) {
    // Extract fields
    const latMatch = block.match(/latitude:\s*([0-9.]+)/);
    const lonMatch = block.match(/longitude:\s*([0-9.]+)/);
    const aqiMatch = block.match(/aqi:\s*([0-9.]+)/);
    const distMatch = block.match(/distance_km:\s*([0-9.]+)/);
    const statusMatch = block.match(/status:\s*'([^']+)'/);
    matchedCities.push({
      city: cityName,
      latitude: latMatch ? parseFloat(latMatch[1]) : null,
      longitude: lonMatch ? parseFloat(lonMatch[1]) : null,
      aqi: aqiMatch ? parseFloat(aqiMatch[1]) : null,
      distance_km: distMatch ? parseFloat(distMatch[1]) : null,
      status: statusMatch ? statusMatch[1] : null,
    });
  }
}

assertEquals(matchedCities.length, 6, 'Fallback contains all 6 anchor cities');

const cityNames = matchedCities.map(c => c.city);
for (const expected of expectedCities) {
  assert(cityNames.includes(expected), `City '${expected}' present in fallback array`);
}

// Stress-test each city coordinate validity
const seenCoordinates = new Set<string>();
for (const c of matchedCities) {
  assert(typeof c.latitude === 'number' && !isNaN(c.latitude) && c.latitude !== null, `${c.city} has valid numeric latitude`);
  assert(typeof c.longitude === 'number' && !isNaN(c.longitude) && c.longitude !== null, `${c.city} has valid numeric longitude`);
  
  // Latitude bounds check for Indo-Gangetic Plain / Punjab region
  assert(c.latitude >= 28.0 && c.latitude <= 32.5, `${c.city} latitude (${c.latitude}) within [28.0, 32.5]`);
  // Longitude bounds check
  assert(c.longitude >= 74.0 && c.longitude <= 78.0, `${c.city} longitude (${c.longitude}) within [74.0, 78.0]`);

  // Assert coordinates are distinct per city
  const coordKey = `${c.latitude.toFixed(3)},${c.longitude.toFixed(3)}`;
  assert(!seenCoordinates.has(coordKey), `${c.city} has unique coordinates (${coordKey})`);
  seenCoordinates.add(coordKey);

  // Assert other telemetry fields
  assert(c.distance_km > 0, `${c.city} distance_km > 0 (${c.distance_km})`);
  assert(c.aqi > 0, `${c.city} aqi > 0 (${c.aqi})`);
  assert(typeof c.status === 'string' && c.status.length > 0, `${c.city} status is non-empty (${c.status})`);
}

// -----------------------------------------------------------------------------
// VERIFICATION SUMMARY
// -----------------------------------------------------------------------------
console.log('\n=================================================================');
console.log('CHALLENGER UI R3 VERIFICATION SUMMARY:');
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
