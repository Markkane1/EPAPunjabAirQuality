/**
 * Drives the shipped workstation module (pure state + rendered shell).
 * Lives outside tests/** because that tree is frozen.
 */
import fs from 'node:fs'
import path from 'node:path'
import { createRequire } from 'node:module'
import { pathToFileURL, fileURLToPath } from 'node:url'
import * as esbuild from 'esbuild'

const require = createRequire(import.meta.url)

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const stationsPath = path.join(repoRoot, 'data', 'baseline', 'stations.json')

const FROZEN_POLLUTANTS = ['AQI', 'PM2.5', 'PM10', 'NO2', 'SO2', 'CO', 'O3', 'NO', 'NOX']
const ZONE_IDS = ['command-bar', 'spatial-dock', 'map-canvas', 'receptor-inspector', 'temporal-scrubber']
const LEGEND = [
  ['Good 0–50', '#009966'],
  ['Satisfactory 51–100', '#58B947'],
  ['Moderate 101–200', '#FFDE33'],
  ['Poor 201–300', '#FF9933'],
  ['Very Poor 301–400', '#CC0033'],
  ['Severe 401–499', '#901530'],
  ['Hazardous 500+', '#C00000'],
]

function assert(cond, message) {
  if (!cond) {
    throw new Error(message)
  }
}

async function loadModule() {
  const outdir = path.join(repoRoot, 'node_modules', '.cache', 'workstation-check')
  await esbuild.build({
    entryPoints: { state: path.join(repoRoot, 'src', 'workstation', 'state.ts') },
    bundle: true,
    platform: 'node',
    format: 'esm',
    outfile: path.join(outdir, 'state.js'),
    logLevel: 'silent',
  })
  await esbuild.build({
    entryPoints: [path.join(repoRoot, 'src', 'workstation', 'ssrEntry.tsx')],
    bundle: true,
    platform: 'node',
    format: 'cjs',
    outfile: path.join(outdir, 'render.cjs'),
    jsx: 'automatic',
    alias: { '@': path.join(repoRoot, 'src') },
    external: ['react', 'react-dom'],
    logLevel: 'silent',
  })
  const state = await import(pathToFileURL(path.join(outdir, 'state.js')).href)
  let render = null
  try {
    render = require(path.join(outdir, 'render.cjs'))
  } catch (error) {
    console.error(`render-bundle-failed: ${renderFailure(error)}`)
  }
  return { state, render }
}

function renderFailure(error) {
  return error instanceof Error ? error.stack || error.message : String(error)
}

async function runOnce(loaded) {
  const state = loaded.state
  const render = loaded.render
  const stations = JSON.parse(fs.readFileSync(stationsPath, 'utf8'))

  assert(state.WORKSTATION_TITLE === 'EPA Punjab Air Quality', 'title mismatch')
  assert(
    JSON.stringify(state.POLLUTANT_KEYS) === JSON.stringify(FROZEN_POLLUTANTS),
    `pollutant keys ${JSON.stringify(state.POLLUTANT_KEYS)}`,
  )

  const zones = state.WORKSTATION_ZONES.map((zone) => zone.id)
  assert(JSON.stringify(zones) === JSON.stringify(ZONE_IDS), `zones ${zones.join(',')}`)
  for (const zone of state.WORKSTATION_ZONES) {
    assert(zone.id === zone.dataZone, `data-zone ${zone.id}`)
  }

  const counts = state.countStationNetworks(stations)
  assert(counts.fixed === 74 && counts.mobile === 5, `station counts ${counts.fixed}/${counts.mobile}`)

  assert(state.streamBadgeCopy('live') === 'LIVE SSE', 'live badge')
  assert(state.streamBadgeCopy('fallback') === 'BASELINE FALLBACK', 'fallback badge')

  assert(state.fluxForPollutant('AQI', [{ a: 1 }]).length === 0, 'AQI flux must be empty')
  assert(state.fluxForPollutant('PM2.5', [{ a: 1 }]).length === 1, 'PM2.5 flux passthrough')
  assert(
    state.dimensionGuardCopy('AQI') === 'Dimension Guard: Flux locked to PM2.5 mass',
    'dimension guard copy',
  )
  assert(state.dimensionGuardCopy('PM2.5') === null, 'no guard on PM2.5')

  assert(state.estimatedBadge(true) === 'EST', 'EST badge')
  assert(state.estimatedBadge(false) === null, 'no EST when monitored')

  assert(
    state.blacklistBannerText({ id: '172', name: 'Wazirabad' }) === 'ANEMOMETER BLACKLISTED (VANE OFFSET)',
    'blacklist string',
  )
  assert(state.blacklistBannerText({ id: '24', name: 'Safari Park-LHR' }) === null, 'non-blacklist')

  const dropout = state.aerodromeWindCopy(null, null)
  const calm = state.aerodromeWindCopy(0.2, 40)
  const active = state.aerodromeWindCopy(3.5, 180)
  assert(dropout.includes('TELEMETRY DROPOUT (NULL)'), dropout)
  assert(calm.includes('AERODYNAMIC CALM (< 0.50 m/s)'), calm)
  assert(active.includes('3.50') && active.includes('180'), active)

  const complete = state.completenessBadge(18, 24)
  const incomplete = state.completenessBadge(17, 24)
  assert(complete.meets === true && complete.label.includes('≥75% VALID'), complete.label)
  assert(incomplete.meets === false && incomplete.label.includes('<75% INCOMPLETE'), incomplete.label)

  const legend = state.pepcLegend()
  assert(legend.length === 7, 'legend length')
  legend.forEach((tier, index) => {
    assert(tier.label === LEGEND[index][0], `legend label ${tier.label}`)
    assert(tier.hex.toUpperCase() === LEGEND[index][1], `legend hex ${tier.hex}`)
  })

  const alertOn = state.hazardousAlert(350.1)
  const alertOff = state.hazardousAlert(350)
  assert(alertOn && alertOn.role === 'alert' && alertOn.ariaLive === 'assertive', 'alert contract')
  assert(alertOn.background === '#C00000' && alertOn.color === '#FFFFFF', 'alert paint')
  assert(alertOn.text.includes('HAZARDOUS') && alertOn.text.includes('500'), alertOn.text)
  assert(alertOff === null, 'no alert at 350')

  const start = state.scrubberReadout(0, 0.2, '2026-11-01 00:00')
  const end = state.scrubberReadout(215, 0, '2026-11-09 23:00')
  assert(start.timestampLine === '2026-11-01 00:00 PKT', start.timestampLine)
  assert(start.detailLine === 'Hour 1/216 · Lerp α=0.20', start.detailLine)
  assert(end.timestampLine === '2026-11-09 23:00 PKT', end.timestampLine)
  assert(end.detailLine.includes('Hour 216/216'), end.detailLine)
  assert(state.HORIZON_START === '2026-11-01 00:00', 'horizon start')
  assert(state.HORIZON_END === '2026-11-09 23:00', 'horizon end')

  const lock = state.mapLibreConstructorOptions()
  assert(lock.pitch === 0 && lock.maxPitch === 0 && lock.bearing === 0, 'map angles')
  assert(lock.dragRotate === false && lock.touchPitch === false, 'map gestures')

  assert(JSON.stringify(state.centroidLngLat([33.669, 72.501])) === JSON.stringify([72.501, 33.669]), 'centroid trap')

  const suppressed = state.cpfSectorVisible({ totalHours: 5, cpfProbability: 0.4 })
  const visible = state.cpfSectorVisible({ totalHours: 6, cpfProbability: 0.4 })
  assert(suppressed === false && visible === true, 'Nk < 6 suppression')

  const model = state.buildWorkstationModel({
    stations,
    pollutant: 'AQI',
    stream: 'fallback',
    hourIndex: 0,
    lerpAlpha: 0.2,
    timestamp: '2026-11-01 00:00',
    search: '',
    layers: { surface: true, choropleth: true, wind: true, flux: true, stations: true },
    selected: { kind: 'station', id: '172', name: 'Wazirabad', stationType: 'fixed', latitude: 32.32, longitude: 73.956 },
    districtRows: [
      { id: 'lahore', name: 'Lahore', value: 385.8, aqi: 385.8, isEstimated: false, latitude: 31.549, longitude: 74.364 },
      { id: 'chiniot', name: 'Chiniot', value: null, aqi: null, isEstimated: true, latitude: 31.72, longitude: 72.98 },
    ],
    maxPm25: 400,
    windSpeed: null,
    windDirection: null,
    validHours: 10,
    totalHours: 24,
    fluxLinks: [{ source: 'A', target: 'B' }],
    playbackSpeed: '1x',
    isPlaying: false,
    domesticShare: 0.62,
    inflowShare: 0.38,
    activeChevrons: 4,
    exportMass: 12.5,
    importMass: 3.25,
    p75Threshold: 95.8,
    calmHours: 12,
    pooledStationCount: 13,
    pooled: true,
    sectors: [
      { sectorIndex: 0, totalHours: 5, cpfProbability: null, azimuthDeg: 0 },
      { sectorIndex: 1, totalHours: 8, cpfProbability: 0.5, azimuthDeg: 22.5 },
    ],
  })

  assert(model.title === 'EPA Punjab Air Quality', 'model title')
  assert(model.stationCounter === '74 Fixed · 5 Mobile', model.stationCounter)
  assert(model.streamLabel === 'BASELINE FALLBACK', model.streamLabel)
  assert(model.dimensionGuard === 'Dimension Guard: Flux locked to PM2.5 mass', model.dimensionGuard)
  assert(model.fluxLinks.length === 0, 'model flux empty for AQI')
  assert(model.blacklist === 'ANEMOMETER BLACKLISTED (VANE OFFSET)', model.blacklist)
  assert(model.hazardous && model.hazardous.role === 'alert', 'model alert')
  assert(model.districts.some((row) => row.isEstimated && row.badge === 'EST'), 'model EST')
  assert(model.completeness.label.includes('<75% INCOMPLETE'), model.completeness.label)
  assert(model.scrubber.detailLine.includes('Lerp α=0.20'), model.scrubber.detailLine)
  assert(model.windCopy.includes('TELEMETRY DROPOUT (NULL)'), model.windCopy)

  let renderNote = 'render-ok'
  try {
    if (!render) throw new Error('render bundle did not load')
    const html = render.renderModel(model)
    for (const id of ZONE_IDS) {
      assert(html.includes(`id="${id}"`) && html.includes(`data-zone="${id}"`), `markup zone ${id}`)
    }
    assert(html.includes('EPA Punjab Air Quality'), 'markup title')
    assert(html.includes('BASELINE FALLBACK'), 'markup fallback')
    assert(html.includes('74 Fixed · 5 Mobile'), 'markup counts')
    assert(html.includes('Dimension Guard: Flux locked to PM2.5 mass'), 'markup guard')
    assert(html.includes('ANEMOMETER BLACKLISTED (VANE OFFSET)'), 'markup blacklist')
    assert(html.includes('role="alert"') && html.includes('aria-live="assertive"'), 'markup alert')
    assert(html.includes('#C00000'), 'markup hazardous paint')
    assert(html.includes('EST'), 'markup EST')
    assert(html.includes('TELEMETRY DROPOUT (NULL)'), 'markup dropout')
    assert(html.includes('Hour 1/216 · Lerp α=0.20'), 'markup scrubber')
    assert(html.includes('data-pollutant="NOX"') && html.includes('data-pollutant="PM2.5"'), 'markup pollutants')
    for (const [label, hex] of LEGEND) {
      assert(html.includes(label) && html.includes(hex), `markup legend ${label}`)
    }
    assert(html.includes('"pitch":0') || html.includes('data-pitch="0"'), 'markup map lock')
  } catch (error) {
    renderNote = `render-failed: ${renderFailure(error)}`
    console.error(renderNote)
  }

  console.log(`workstation-check ok stations=${counts.fixed}/${counts.mobile} ${renderNote}`)
  return renderNote
}

const loaded = await loadModule()
const first = await runOnce(loaded)
const second = await runOnce(loaded)
assert(first === second, `runs diverged:\n${first}\n${second}`)
if (first.startsWith('render-failed')) {
  console.log('pure assertions passed; render did not start')
  process.exitCode = 0
}
