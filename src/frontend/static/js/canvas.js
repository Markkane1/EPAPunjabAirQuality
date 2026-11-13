/**
 * 5-Layer Canvas Rendering Engine for Punjab Air Quality Platform.
 * Layers 0-4: Static Basemap, Wind-Steered IDW Field, 1300-Particle Advection,
 * Transport Vectors & Chevrons, and Greedy Collision-Free Labels.
 */

import { project, unproject, KX, B } from './geo.js';

// Statutory PEPC 7-Stop Palette Breakpoints & Colors
export const PEPC_TIERS = [
  { min: 0, max: 50, label: 'Good', color: [0, 176, 80] },                   // #00B050
  { min: 51, max: 100, label: 'Satisfactory', color: [146, 208, 80] },      // #92D050
  { min: 101, max: 150, label: 'Moderate', color: [255, 255, 0] },          // #FFFF00
  { min: 151, max: 200, label: 'Unhealthy for Sensitive', color: [237, 125, 49] }, // #ED7D31
  { min: 201, max: 300, label: 'Unhealthy', color: [255, 0, 0] },           // #FF0000
  { min: 301, max: 400, label: 'Very Unhealthy', color: [112, 48, 160] },   // #7030A0
  { min: 401, max: 9999, label: 'Hazardous', color: [192, 0, 0] },          // #C00000
];

export const BP = {
  PM10: [75, 150, 250, 350, 450, 550],
  'PM2.5': [15, 35, 70, 140, 250, 350],
  SO2: [60, 120, 220, 320, 800, 1600],
  NO2: [40, 80, 130, 180, 380, 580],
  O3: [65, 130, 195, 260, 450, 550],
  CO: [2.5, 5, 7.5, 10, 25, 40],
  NO: [40, 80, 130, 180, 280, 400],
};

export const AQI_B = [
  [0, 50, 'Good', [0, 176, 80]],
  [51, 100, 'Satisfactory', [146, 208, 80]],
  [101, 150, 'Moderate', [255, 255, 0]],
  [151, 200, 'Unhealthy for Sensitive Groups', [237, 125, 49]],
  [201, 300, 'Unhealthy', [255, 0, 0]],
  [301, 400, 'Very Unhealthy', [112, 48, 160]],
  [401, 1e9, 'Hazardous', [192, 0, 0]],
];

export const MULT = [0, 0.5, 1.0, 1.5, 2.5, 4.0, 6.0];
export const RGB = [
  [58, 165, 93],
  [156, 204, 58],
  [242, 194, 48],
  [240, 122, 38],
  [214, 52, 44],
  [142, 59, 143],
  [90, 21, 48],
];

export const POLNAME = {
  AQI: 'AQI',
  PM10: 'PM10',
  'PM2.5': 'PM2.5',
  NO2: 'NO₂',
  SO2: 'SO₂',
  CO: 'CO',
  O3: 'O₃',
  NO: 'NO',
  NOX: 'NOx',
  NOx: 'NOx',
};

export const STATUTORY_LIMITS = {
  AQI: { name: 'AQI', unit: '', ref: 200, refavg: '24-h', scale: 'aqi' },
  'PM2.5': { name: 'PM2.5', unit: 'µg/m³', ref: 35, refavg: '24-h', scale: 'conc' },
  PM10: { name: 'PM10', unit: 'µg/m³', ref: 150, refavg: '24-h', scale: 'conc' },
  NO2: { name: 'NO₂', unit: 'µg/m³', ref: 80, refavg: '24-h', scale: 'conc' },
  SO2: { name: 'SO₂', unit: 'µg/m³', ref: 120, refavg: '24-h', scale: 'conc' },
  CO: { name: 'CO', unit: 'mg/m³', ref: 5, refavg: '8-h', scale: 'conc' },
  O3: { name: 'O₃', unit: 'µg/m³', ref: 130, refavg: '1-h', scale: 'conc' },
  NO: { name: 'NO', unit: 'µg/m³', ref: 40, refavg: '24-h', scale: 'conc' },
  NOX: { name: 'NOx', unit: 'µg/m³', ref: 100, refavg: 'scale ref', scale: 'conc' },
  NOx: { name: 'NOx', unit: 'µg/m³', ref: 100, refavg: 'scale ref', scale: 'conc' },
};

export const aqiCat = v => AQI_B.find(b => Math.round(v) <= b[1]) || AQI_B[6];
export const isAQI = Q => (typeof Q === 'string' ? Q === 'AQI' : (Q && Q.scale === 'aqi'));
export const refFor = Q => {
  const k = typeof Q === 'string' ? Q : (Q && (Q.key || Q.name));
  if (k === 'AQI') return 'aqi';
  if (BP[k]) return 'bp:' + k;
  return (typeof Q === 'object' && Q && Q.ref) ? Q.ref : (STATUTORY_LIMITS[k]?.ref || 100);
};
export const bpIdx = (v, k) => {
  const b = BP[k];
  if (!b) return 6;
  for (let i = 0; i < b.length; i++) if (v <= b[i]) return i;
  return 6;
};
export const bpTicks = k => ['0', ...BP[k].map(x => String(x))].map((s, i) => `<span style="left:${Math.max(3, (i / 7) * 100 + 1)}%">${i === 6 ? s + '+' : s}</span>`).join('');
export const aqiBar = () => 'linear-gradient(90deg,' + AQI_B.map((b, i) => `rgb(${b[3].join(',')}) ${(i / 7) * 100}%, rgb(${b[3].join(',')}) ${((i + 1) / 7) * 100}%`).join(',') + ')';
export const aqiTicks = () => ['0', '51', '101', '151', '201', '301', '401+'].map((s, i) => `<span style="left:${Math.max(4, (i / 7) * 100 + 2)}%">${s}</span>`).join('');
export const barFor = Q => (isAQI(Q) || (typeof Q === 'string' ? BP[Q] : BP[Q.key || Q.name])) ? aqiBar() : 'linear-gradient(90deg,' + MULT.map((m, i) => `rgb(${RGB[i].join(',')}) ${(m / 6) * 100}%`).join(',') + ')';
export const limLabel = Q => {
  const isA = isAQI(Q);
  if (isA) return 'EPA Punjab AQI · Unhealthy above 200';
  const ref = typeof Q === 'object' && Q ? Q.ref : (STATUTORY_LIMITS[Q]?.ref);
  const refavg = typeof Q === 'object' && Q ? Q.refavg : (STATUTORY_LIMITS[Q]?.refavg || '');
  return ref ? `PEQS ${refavg} ${ref}` : 'no PEQS (scale ref. 100)';
};

export function colArr(v, r = 'aqi') {
  if (v === null || v === undefined || isNaN(v)) return [128, 128, 128];
  if (r === 'aqi' || !r) return aqiCat(v)[3];
  if (typeof r === 'string' && r.startsWith('bp:')) return AQI_B[bpIdx(v, r.slice(3))][3];
  const numR = typeof r === 'number' ? r : 100;
  for (let i = 1; i < MULT.length; i++) {
    const x1 = MULT[i] * numR;
    if (v <= x1 || i === MULT.length - 1) {
      const x0 = MULT[i - 1] * numR;
      const t = Math.max(0, Math.min(1, (v - x0) / ((x1 - x0) || 1)));
      return RGB[i - 1].map((c, k) => Math.round(c + (RGB[i][k] - c) * t));
    }
  }
  return RGB[RGB.length - 1];
}

export function col(v, a = 1, r = 'aqi') {
  if (v === null || v === undefined || isNaN(v)) return `rgba(128, 128, 128, ${a})`;
  const c = colArr(v, r);
  return `rgba(${c[0] | 0}, ${c[1] | 0}, ${c[2] | 0}, ${a})`;
}

/**
 * Returns [r, g, b] color for value according to active pollutant scale.
 */
export function getColorRgb(val, pollutantKey) {
  const r = refFor(pollutantKey);
  return colArr(val, r);
}

export function getColorCss(val, pollutantKey, alpha = 1) {
  const r = refFor(pollutantKey);
  return col(val, alpha, r);
}

export class CanvasMapEngine {
  constructor(canvasElement, options = {}) {
    this.canvas = canvasElement;
    this.ctx = canvasElement.getContext('2d');
    this.hitCanvas = document.createElement('canvas');
    this.hitCtx = this.hitCanvas.getContext('2d');

    // Downsampled offscreen canvas for IDW raster field
    this.fcCanvas = document.createElement('canvas');
    this.fcCtx = this.fcCanvas.getContext('2d');
    this.fcKey = '';

    // State & Dimensions
    this.width = 800;
    this.height = 600;
    this.S = 1.0;
    this.dpr = window.devicePixelRatio || 1;

    // Zoom & Pan Interactive State (1.0x to 10.0x)
    this.zoom = 1.0;
    this.minZoom = 1.0;
    this.maxZoom = 10.0;
    this.pan = [0, 0];

    // Map Paths
    this.paths = null;
    this.districts = [];
    this.stations = [];
    this.airports = [];
    this.samples = []; // 39 border normal nodes

    // Active Rendering Config
    this.currentHour = 0;
    this.fractionalHour = 0.0;
    this.pollutant = 'AQI';
    this.displayMode = 'surface'; // 'surface' or 'district'
    this.showTransportLinks = true;
    this.showRegionalWinds = true;
    this.selectedDistrict = 'Lahore';

    // Theme Colors
    this.theme = 'dark';
    this.tokens = {};

    // 1300 Particle Simulation Buffers (Zero-GC pre-allocated typed arrays)
    this.PARTICLE_COUNT = 1300;
    this.LOCAL_COUNT = 700;
    this.REGIONAL_COUNT = 600;
    this.TRAIL_LENGTH = 8;

    // Buffer: 1300 particles * 8 points * 2 coords (x,y)
    this.particleTrails = new Float32Array(this.PARTICLE_COUNT * this.TRAIL_LENGTH * 2);
    // Buffer: [x, y, age, maxAge, speed, isLocal]
    this.particleState = new Float32Array(this.PARTICLE_COUNT * 6);
    this.particleHead = new Uint8Array(this.PARTICLE_COUNT);

    // Animation Ticker State
    this.dashOffset = 0.0;
    this.chevronPhase = 0.0;
    this.lastFrameTime = performance.now();

    this.initParticles();
    this.readThemeTokens();
  }

  readThemeTokens() {
    const s = getComputedStyle(document.documentElement);
    this.tokens = {
      bgCanvas: s.getPropertyValue('--bg-canvas').trim() || '#0f1716',
      bgPanel: s.getPropertyValue('--bg-panel').trim() || '#152120',
      geoSea: s.getPropertyValue('--geo-sea').trim() || '#0b1211',
      geoLand: s.getPropertyValue('--geo-land').trim() || '#162120',
      geoPunjab: s.getPropertyValue('--geo-punjab').trim() || '#1d2d2c',
      geoBorder: s.getPropertyValue('--geo-district-border').trim() || '#4f625e',
      geoInternational: s.getPropertyValue('--geo-international').trim() || '#ff7a6b',
      geoIndia: s.getPropertyValue('--geo-india-fill').trim() || '#26231a',
      flowInflow: s.getPropertyValue('--flow-inflow').trim() || '#ff6b5e',
      flowOutflow: s.getPropertyValue('--flow-outflow').trim() || '#5fc4c4',
      flowParticle: s.getPropertyValue('--flow-particle').trim() || 'rgba(225, 245, 242, 0.35)',
      inkPrimary: s.getPropertyValue('--ink-primary').trim() || '#e3ece9',
      inkSecondary: s.getPropertyValue('--ink-secondary').trim() || '#93a39e',
      accent: s.getPropertyValue('--accent').trim() || '#5fc4c4',
      vectorTransport: s.getPropertyValue('--accent').trim() || '#5fc4c4',
      fontMono: s.getPropertyValue('--font-mono').trim() || 'JetBrains Mono, monospace',
    };
  }

  initParticles() {
    for (let i = 0; i < this.PARTICLE_COUNT; i++) {
      const isLocal = i < this.LOCAL_COUNT ? 1 : 0;
      this.resetParticle(i, isLocal, Math.random() * 90);
    }
  }

  resetParticle(i, isLocal, initialAge = 0) {
    const sIdx = i * 6;
    let x, y;

    if (isLocal) {
      // Pick random coordinates within Punjab bounding box
      const minX = 0;
      const maxX = this.width;
      const minY = 0;
      const maxY = this.height;
      x = minX + Math.random() * (maxX - minX);
      y = minY + Math.random() * (maxY - minY);
    } else {
      // Regional borderland
      x = Math.random() * this.width;
      y = Math.random() * this.height;
    }

    this.particleState[sIdx] = x;
    this.particleState[sIdx + 1] = y;
    this.particleState[sIdx + 2] = initialAge; // age
    this.particleState[sIdx + 3] = 100 + Math.random() * 40; // maxAge
    this.particleState[sIdx + 4] = 0.8 + Math.random() * 0.6; // speed
    this.particleState[sIdx + 5] = isLocal;

    this.particleHead[i] = 0;
    const tBase = i * this.TRAIL_LENGTH * 2;
    for (let k = 0; k < this.TRAIL_LENGTH; k++) {
      this.particleTrails[tBase + k * 2] = x;
      this.particleTrails[tBase + k * 2 + 1] = y;
    }
  }

  setTopology(paths, districts, stations, airports, samples) {
    this.paths = paths;
    this.districts = districts || [];
    this.stations = stations || [];
    this.airports = airports || [];
    this.samples = samples || [];
  }

  project(lon, lat) {
    return project(lon, lat, this.S || 1.0);
  }

  unproject(x, y) {
    return unproject(x, y, this.S || 1.0);
  }

  resize() {
    const rect = this.canvas.parentElement.getBoundingClientRect();
    this.dpr = Math.min(2, window.devicePixelRatio || 1);
    this.width = Math.floor(rect.width || 800);

    // Compute standard parallel scale factor
    this.S = this.width / ((B.lo1 - B.lo0) * KX);
    this.height = Math.floor((B.la1 - B.la0) * this.S);

    this.canvas.width = Math.round(this.width * this.dpr);
    this.canvas.height = Math.round(this.height * this.dpr);
    this.canvas.style.width = '100%';
    this.canvas.style.height = `${this.height}px`;

    this.hitCanvas.width = this.width;
    this.hitCanvas.height = this.height;

    // Scale FC downsampled raster buffer (cell size 5px)
    this.fcCanvas.width = Math.max(1, Math.ceil(this.width / 5));
    this.fcCanvas.height = Math.max(1, Math.ceil(this.height / 5));
    this.fcKey = ''; // Invalidate IDW cache on resize

    if (this.zoom <= 1.001) {
      this.zoom = 1.0;
      this.pan = [0, 0];
    } else {
      const minPanX = this.width * (1.0 - this.zoom) - 60;
      const maxPanX = 60;
      const minPanY = this.height * (1.0 - this.zoom) - 60;
      const maxPanY = 60;
      this.pan[0] = Math.min(maxPanX, Math.max(minPanX, this.pan[0]));
      this.pan[1] = Math.min(maxPanY, Math.max(minPanY, this.pan[1]));
    }
  }

  setZoom(targetZoom, screenCenterX, screenCenterY) {
    const prevZoom = this.zoom;
    const clampedZoom = Math.max(this.minZoom, Math.min(this.maxZoom, targetZoom));
    if (Math.abs(clampedZoom - prevZoom) < 0.001) return;

    if (clampedZoom <= 1.001) {
      this.zoom = 1.0;
      this.pan = [0, 0];
      return;
    }

    const cx = screenCenterX !== undefined ? screenCenterX : this.width / 2;
    const cy = screenCenterY !== undefined ? screenCenterY : this.height / 2;

    const wx = (cx - this.pan[0]) / prevZoom;
    const wy = (cy - this.pan[1]) / prevZoom;

    const newPanX = cx - wx * clampedZoom;
    const newPanY = cy - wy * clampedZoom;

    const minPanX = this.width * (1.0 - clampedZoom) - 60;
    const maxPanX = 60;
    const minPanY = this.height * (1.0 - clampedZoom) - 60;
    const maxPanY = 60;

    this.zoom = clampedZoom;
    this.pan = [
      Math.min(maxPanX, Math.max(minPanX, newPanX)),
      Math.min(maxPanY, Math.max(minPanY, newPanY))
    ];
  }

  panBy(dx, dy) {
    if (this.zoom <= 1.001) {
      this.pan = [0, 0];
      return;
    }

    const minPanX = this.width * (1.0 - this.zoom) - 60;
    const maxPanX = 60;
    const minPanY = this.height * (1.0 - this.zoom) - 60;
    const maxPanY = 60;

    const newPanX = this.pan[0] + dx;
    const newPanY = this.pan[1] + dy;

    this.pan = [
      Math.min(maxPanX, Math.max(minPanX, newPanX)),
      Math.min(maxPanY, Math.max(minPanY, newPanY))
    ];
  }

  resetZoom() {
    this.zoom = 1.0;
    this.pan = [0, 0];
  }

  screenToWorld(screenX, screenY) {
    return [
      (screenX - this.pan[0]) / this.zoom,
      (screenY - this.pan[1]) / this.zoom
    ];
  }

  worldToScreen(worldX, worldY) {
    return [
      worldX * this.zoom + this.pan[0],
      worldY * this.zoom + this.pan[1]
    ];
  }

  hitTestDistrict(screenX, screenY) {
    if (!this.paths || !this.paths.admPaths) return null;
    const [wx, wy] = this.screenToWorld(screenX, screenY);

    // 1. Precise boundary path hit test
    for (const adm of this.paths.admPaths) {
      if (this.hitCtx && this.hitCtx.isPointInPath(adm.path, wx, wy)) {
        return adm.name;
      }
    }

    // 2. Proximity fallback to district centroid
    const maxDist = 20 / this.zoom;
    let closestName = null;
    let closestDist = maxDist;

    for (const dist of this.districts) {
      if (!dist || !dist.xy) continue;
      const d = Math.hypot(dist.xy[0] - wx, dist.xy[1] - wy);
      if (d < closestDist) {
        closestDist = d;
        closestName = dist.name;
      }
    }

    return closestName;
  }

  /**
   * Evaluates blended vector wind [u, v] in screen coordinates at (x, y).
   */
  getWindAt(x, y, activeWinds) {
    if (!activeWinds || Object.keys(activeWinds).length === 0) {
      return [0.6, 0.2]; // default background drift
    }

    let sumU = 0;
    let sumV = 0;
    let sumW = 0;

    // Blend from districts/stations
    for (const dist of this.districts) {
      const w = activeWinds[dist.name];
      if (!w || w[0] === null || w[1] === null) continue;
      const [dx, dy] = [x - dist.xy[0], y - dist.xy[1]];
      const d2 = dx * dx + dy * dy;
      const weight = 1.0 / (d2 + 400.0); // 20px softening
      sumU += w[0] * weight;
      sumV += w[1] * weight;
      sumW += weight;
    }

    if (sumW > 0) {
      return [sumU / sumW, sumV / sumW];
    }
    return [0.5, 0.2];
  }

  /**
   * Continuous sub-hourly temporal linear interpolation helper.
   */
  lerpValue(arr, fp) {
    if (!arr || arr.length === 0) return null;
    const n = arr.length;
    const i = Math.floor(fp);
    const f = fp - i;
    const j = Math.min(n - 1, i + 1);

    const v0 = arr[Math.min(n - 1, Math.max(0, i))];
    const v1 = arr[j];

    if (v0 === null && v1 === null) return null;
    if (v0 === null) return v1;
    if (v1 === null) return v0;

    return (1.0 - f) * v0 + f * v1;
  }

  // =========================================================================
  // LAYER 0: STATIC BASEMAP CANVAS
  // =========================================================================
  drawLayer0(ctx) {
    if (!this.paths) return;

    const scaleFactor = 1.0 / Math.sqrt(this.zoom);

    // Sea/Backdrop fill - covers extended panning margin
    ctx.fillStyle = this.tokens.geoSea;
    ctx.fillRect(-this.width * 2, -this.height * 2, this.width * 5, this.height * 5);

    // Neighboring Pakistan Territories (Sind, Baluchistan, KP, etc.)
    ctx.fillStyle = this.tokens.geoLand;
    ctx.strokeStyle = this.tokens.geoBorder;
    ctx.lineWidth = 0.7 * scaleFactor;
    for (const p of this.paths.provPaths) {
      ctx.fill(p);
      ctx.stroke(p);
    }

    // Adjacent Indian Borderland States
    if (this.paths.indPath) {
      ctx.fillStyle = this.tokens.geoIndia;
      ctx.fill(this.paths.indPath);
      ctx.stroke(this.paths.indPath);
    }

    // Outer Punjab Provincial Territory
    if (this.paths.pjPath) {
      ctx.fillStyle = this.tokens.geoPunjab;
      ctx.fill(this.paths.pjPath);
    }

    // 41 Inter-district administrative boundaries
    if (this.displayMode === 'surface') {
      ctx.strokeStyle = this.tokens.geoBorder;
      ctx.lineWidth = 0.6 * scaleFactor;
      for (const adm of this.paths.admPaths) {
        ctx.stroke(adm.path);
      }
    }

    // 440-pt International Border Line (dashed stroke)
    if (this.paths.borderPath) {
      ctx.save();
      ctx.strokeStyle = this.tokens.geoInternational;
      ctx.lineWidth = 2.4 * scaleFactor;
      ctx.setLineDash([8 * scaleFactor, 4 * scaleFactor]);
      ctx.stroke(this.paths.borderPath);
      ctx.restore();
    }

    // Cartographic Watermark Typography
    ctx.save();
    ctx.font = '700 22px "Barlow Condensed", sans-serif';
    ctx.fillStyle = this.tokens.inkSecondary;
    ctx.globalAlpha = 0.25;

    const [indX, indY] = project(75.0, 30.3, this.S);
    ctx.fillText('INDIA', indX, indY);

    const [pakX, pakY] = project(69.35, 31.9, this.S);
    ctx.fillText('PAKISTAN', pakX, pakY);
    ctx.restore();
  }

  // =========================================================================
  // LAYER 1: CONTINUOUS WIND-STEERED IDW SURFACE OR CHOROPLETH
  // =========================================================================
  drawLayer1(ctx, stationReadings, districtReadings, activeWinds, activeStationPoints = null) {
    if (!this.paths || !this.paths.pjPath) return;

    if (this.displayMode === 'district') {
      // Administrative Choropleth Mode
      for (const adm of this.paths.admPaths) {
        const val = districtReadings[adm.name];
        ctx.save();
        ctx.fillStyle = getColorCss(val, this.pollutant, 0.75);
        ctx.fill(adm.path);

        if (adm.is_estimated) {
          // Diagonal hatching for unmonitored estimated districts
          ctx.clip(adm.path);
          ctx.strokeStyle = 'rgba(0, 0, 0, 0.15)';
          ctx.lineWidth = 1.0;
          for (let y = -this.height; y < this.height * 2; y += 8) {
            ctx.beginPath();
            ctx.moveTo(0, y);
            ctx.lineTo(this.width, y + this.width);
            ctx.stroke();
          }
        }
        ctx.restore();

        ctx.strokeStyle = this.tokens.geoBorder;
        ctx.lineWidth = 0.8;
        ctx.stroke(adm.path);
      }
      return;
    }

    // Continuous Surface Mode via Downsampled IDW Grid
    let activeStations = [];
    if (activeStationPoints && activeStationPoints.length > 0) {
      activeStations = activeStationPoints;
    } else {
      for (const st of this.stations) {
        if (!st || !st.xy) continue;
        const v = stationReadings[st.name];
        if (v !== null && v !== undefined && !isNaN(v)) {
          const w = activeWinds[st.district] || [0.5, 0.0];
          activeStations.push({
            x: st.xy[0],
            y: st.xy[1],
            v: v,
            u: w[0] || 0.0,
            vWind: w[1] || 0.0,
            s: Math.hypot(w[0] || 0, w[1] || 0),
          });
        }
      }
    }

    // If no direct station readings, fallback to district centroids
    if (activeStations.length === 0) {
      for (const dist of this.districts) {
        if (!dist || !dist.xy) continue;
        const v = districtReadings[dist.name];
        if (v !== null && v !== undefined && !isNaN(v)) {
          const w = activeWinds[dist.name] || [0.5, 0.0];
          activeStations.push({
            x: dist.xy[0],
            y: dist.xy[1],
            v: v,
            u: w[0] || 0.0,
            vWind: w[1] || 0.0,
            s: Math.hypot(w[0] || 0, w[1] || 0),
          });
        }
      }
    }

    if (activeStations.length === 0) return;

    const gw = this.fcCanvas.width;
    const gh = this.fcCanvas.height;

    // Fast-path IDW cache key to prevent 60 FPS recomputation
    const key = `${this.pollutant}|${Math.round(this.fractionalHour * 12)}|${gw}|${gh}`;
    if (this.fcKey !== key) {
      this.fcKey = key;
      const imgData = this.fcCtx.createImageData(gw, gh);
      const data = imgData.data;

      for (let gy = 0; gy < gh; gy++) {
        const py = gy * 5 + 2.5;
        for (let gx = 0; gx < gw; gx++) {
          const px = gx * 5 + 2.5;

          let sumW = 0.0;
          let sumV = 0.0;
          let minD = 999999.0;

          for (let i = 0; i < activeStations.length; i++) {
            const st = activeStations[i];
            const dx = px - st.x;
            const dy = py - st.y;
            const d2 = dx * dx + dy * dy;
            const d = Math.sqrt(d2);
            if (d < minD) minD = d;

            const w0 = 1.0 / (d2 + 16.0); // 4px softening
            let w = w0;

            if (st.s > 0.5 && d > 2.0) {
              // Anisotropic wind-steering multiplier
              const cosA = (dx * st.u - dy * st.vWind) / (d * st.s);
              const psi = 1.0 + 0.70 * cosA * Math.min(1.0, st.s / 1.5);
              w = w0 * Math.max(0.30, Math.min(1.70, psi));
            }

            sumW += w;
            sumV += w * st.v;
          }

          const interpolatedVal = sumW > 0 ? sumV / sumW : 0;
          const [r, g, b] = getColorRgb(interpolatedVal, this.pollutant);

          // Distance confidence opacity taper (45km to 140km)
          const kmMin = minD * (111.0 / this.S);
          let alpha = 235;
          if (kmMin > 140.0) {
            alpha = 95;
          } else if (kmMin >= 45.0) {
            alpha = Math.round(235 - 140 * ((kmMin - 45.0) / 95.0));
          }

          const pIdx = (gy * gw + gx) * 4;
          data[pIdx] = r;
          data[pIdx + 1] = g;
          data[pIdx + 2] = b;
          data[pIdx + 3] = alpha;
        }
      }

      this.fcCtx.putImageData(imgData, 0, 0);
    }

    // Draw bilinear upsampled raster clipped to Punjab
    ctx.save();
    ctx.clip(this.paths.pjPath);
    ctx.imageSmoothingEnabled = true;
    ctx.drawImage(this.fcCanvas, 0, 0, gw * 5, gh * 5);
    ctx.restore();
  }

  // =========================================================================
  // LAYER 2: 1300-PARTICLE WIND ADVECTION SIMULATION
  // =========================================================================
  drawLayer2(ctx, activeWinds) {
    if (!this.paths || !this.paths.pjPath) return;

    ctx.save();
    ctx.strokeStyle = this.tokens.flowParticle;
    ctx.lineWidth = 0.9 / Math.sqrt(this.zoom);

    const hit = this.hitCtx;
    const S100 = this.S / 100.0;

    for (let i = 0; i < this.PARTICLE_COUNT; i++) {
      const sIdx = i * 6;
      let x = this.particleState[sIdx];
      let y = this.particleState[sIdx + 1];
      let age = this.particleState[sIdx + 2] + 1;
      const maxAge = this.particleState[sIdx + 3];
      const isLocal = this.particleState[sIdx + 5];

      // Wind evaluation
      const [u, v] = this.getWindAt(x, y, activeWinds);
      const kFactor = (isLocal ? 1.4 : 2.2) * S100;

      const nx = x + u * kFactor;
      const ny = y - v * kFactor;

      // Check boundaries & respawn
      let outOfBounds = false;
      if (isLocal) {
        if (!hit.isPointInPath(this.paths.pjPath, nx, ny)) {
          outOfBounds = true;
        }
      } else {
        if (nx < 0 || nx > this.width || ny < 0 || ny > this.height) {
          outOfBounds = true;
        }
      }

      if (age > maxAge || outOfBounds) {
        this.resetParticle(i, isLocal, 0);
        continue;
      }

      // Update position & ring buffer
      this.particleState[sIdx] = nx;
      this.particleState[sIdx + 1] = ny;
      this.particleState[sIdx + 2] = age;

      let head = (this.particleHead[i] + 1) % this.TRAIL_LENGTH;
      this.particleHead[i] = head;

      const tBase = i * this.TRAIL_LENGTH * 2;
      this.particleTrails[tBase + head * 2] = nx;
      this.particleTrails[tBase + head * 2 + 1] = ny;

      // Draw multi-segment trail
      ctx.beginPath();
      for (let step = 0; step < this.TRAIL_LENGTH; step++) {
        const idx = (head - step + this.TRAIL_LENGTH) % this.TRAIL_LENGTH;
        const px = this.particleTrails[tBase + idx * 2];
        const py = this.particleTrails[tBase + idx * 2 + 1];
        if (step === 0) {
          ctx.moveTo(px, py);
        } else {
          ctx.lineTo(px, py);
        }
      }
      ctx.stroke();
    }

    ctx.restore();
  }

  // =========================================================================
  // LAYER 3: TRANSPORT FLUX VECTORS & BORDER CHEVRONS
  // =========================================================================
  drawLayer3(ctx, transportLinks, activeWinds) {
    // 1. Inter-District Transport Vectors (PHYSICAL SPECIES ONLY, DISABLED FOR AQI)
    if (this.showTransportLinks && this.pollutant !== 'AQI' && transportLinks && transportLinks.length > 0) {
      ctx.save();
      this.dashOffset = (this.dashOffset - 0.6) % 12;

      // Sort & filter top 12 active links
      const active12 = transportLinks.slice(0, 12);
      const maxF = active12[0] ? active12[0].flux || 1.0 : 1.0;

      for (const link of active12) {
        const srcDist = this.districts.find(d => d.name === link.src || d.name === link.source_district);
        const rcvDist = this.districts.find(d => d.name === link.rcv || d.name === link.receptor_district);
        if (!srcDist || !rcvDist) continue;

        const [sx, sy] = srcDist.xy;
        const [ex, ey] = rcvDist.xy;
        const dx = ex - sx;
        const dy = ey - sy;
        const L = Math.hypot(dx, dy);
        if (L < 10) continue;

        const ux = dx / L;
        const uy = dy / L;

        // Quadratic Bezier perpendicular bulge
        const cx = (sx + ex) / 2 - uy * L * 0.12;
        const cy = (sy + ey) / 2 + ux * L * 0.12;

        const flux = link.flux || 0.0;
        const w = 1.2 + 4.0 * Math.sqrt(Math.max(0, flux) / (maxF || 1.0));

        // Pass 1: Background halo
        ctx.strokeStyle = this.tokens.bgPanel;
        ctx.lineWidth = w + 2.5;
        ctx.beginPath();
        ctx.moveTo(sx, sy);
        ctx.quadraticCurveTo(cx, cy, ex, ey);
        ctx.stroke();

        // Pass 2: Source concentration stroke
        ctx.strokeStyle = this.tokens.accent;
        ctx.lineWidth = w;
        ctx.beginPath();
        ctx.moveTo(sx, sy);
        ctx.quadraticCurveTo(cx, cy, ex, ey);
        ctx.stroke();

        // Pass 3: Animated dashed flow core
        ctx.strokeStyle = this.tokens.geoPunjab;
        ctx.lineWidth = Math.max(1.0, w * 0.35);
        ctx.setLineDash([4, 8]);
        ctx.lineDashOffset = this.dashOffset;
        ctx.beginPath();
        ctx.moveTo(sx, sy);
        ctx.quadraticCurveTo(cx, cy, ex, ey);
        ctx.stroke();
        ctx.setLineDash([]);

        // Directional arrowhead at receptor
        const angle = Math.atan2(ey - cy, ex - cx);
        const headLen = 5 + w;
        ctx.fillStyle = this.tokens.accent;
        ctx.beginPath();
        ctx.moveTo(ex, ey);
        ctx.lineTo(ex - headLen * Math.cos(angle - 0.45), ey - headLen * Math.sin(angle - 0.45));
        ctx.lineTo(ex - headLen * Math.cos(angle + 0.45), ey - headLen * Math.sin(angle + 0.45));
        ctx.closePath();
        ctx.fill();
      }
      ctx.restore();
    }

    // 2. 39 Border Normal Chevrons
    if (this.samples && this.samples.length > 0) {
      ctx.save();
      this.chevronPhase = (this.chevronPhase + 0.012) % 1.0;
      const alpha = 0.35 + 0.65 * Math.sin(this.chevronPhase * Math.PI);
      const normalDisp = (this.chevronPhase - 0.5) * 18.0;

      for (const sample of this.samples) {
        const [x, y] = project(sample[0], sample[1], this.S);
        const nx = sample[2];
        const ny = sample[3];

        // Evaluate normal velocity component: c = u * nx + v * ny
        const [u, v] = this.getWindAt(x, y, activeWinds);
        const c = u * nx + v * ny;

        if (Math.abs(c) < 0.25) continue; // Suppressed when calm

        const isInflow = c > 0.25;
        ctx.strokeStyle = isInflow ? this.tokens.flowInflow : this.tokens.flowOutflow;
        ctx.lineWidth = 2.2;
        ctx.globalAlpha = alpha;

        // Position with normal oscillation
        const px = x + nx * normalDisp;
        const py = y + ny * normalDisp;
        const chevronSize = 5 + Math.min(3, Math.abs(c)) * 2.5;

        // Draw chevron V pointing along normal
        const perpX = -ny;
        const perpY = nx;

        ctx.beginPath();
        ctx.moveTo(px - nx * chevronSize + perpX * chevronSize * 0.7, py - ny * chevronSize + perpY * chevronSize * 0.7);
        ctx.lineTo(px, py);
        ctx.lineTo(px - nx * chevronSize - perpX * chevronSize * 0.7, py - ny * chevronSize - perpY * chevronSize * 0.7);
        ctx.stroke();
      }
      ctx.restore();
    }
  }

  // =========================================================================
  // LAYER 4: STATION GLYPHS & COLLISION-FREE DISTRICT LABELS
  // =========================================================================
  drawLayer4(ctx, stationReadings, districtReadings, activeWinds, activeStationPoints = null) {
    ctx.save();
    const scaleFactor = 1.0 / Math.sqrt(this.zoom);

    // 1. Fixed AQMS Stations (Circles in surface mode, Squares in district mode)
    if (this.displayMode === 'surface') {
      if (activeStationPoints && activeStationPoints.length > 0) {
        for (const p of activeStationPoints) {
          ctx.beginPath();
          ctx.arc(p.x, p.y, 3.6 * scaleFactor, 0, Math.PI * 2);
          ctx.fillStyle = getColorCss(p.v, this.pollutant, 1.0);
          ctx.fill();
          ctx.strokeStyle = this.tokens.inkPrimary || '#17221f';
          ctx.lineWidth = 1.0 * scaleFactor;
          ctx.stroke();
        }
      } else {
        for (const st of this.stations) {
          if (!st || !st.xy) continue;
          const v = stationReadings[st.name];
          if (v !== undefined && v !== null && !isNaN(v)) {
            ctx.beginPath();
            ctx.arc(st.xy[0], st.xy[1], 3.6 * scaleFactor, 0, Math.PI * 2);
            ctx.fillStyle = getColorCss(v, this.pollutant, 1.0);
            ctx.fill();
            ctx.strokeStyle = this.tokens.inkPrimary || '#17221f';
            ctx.lineWidth = 1.0 * scaleFactor;
            ctx.stroke();
          } else {
            ctx.fillStyle = this.tokens.inkPrimary || '#17221f';
            ctx.globalAlpha = 0.8;
            ctx.fillRect(st.xy[0] - 1.8 * scaleFactor, st.xy[1] - 1.8 * scaleFactor, 3.6 * scaleFactor, 3.6 * scaleFactor);
            ctx.globalAlpha = 1.0;
          }
        }
      }
    } else {
      ctx.fillStyle = this.tokens.inkPrimary || '#17221f';
      ctx.globalAlpha = 0.8;
      for (const st of this.stations) {
        if (!st || !st.xy) continue;
        ctx.fillRect(st.xy[0] - 1.8 * scaleFactor, st.xy[1] - 1.8 * scaleFactor, 3.6 * scaleFactor, 3.6 * scaleFactor);
      }
      ctx.globalAlpha = 1.0;
    }

    // 2. Airport METAR Sites (Triangle + Wind Arrow)
    for (const ap of this.airports) {
      if (!ap || !ap.xy) continue;
      const [ax, ay] = ap.xy;
      ctx.fillStyle = this.tokens.accent;
      ctx.beginPath();
      ctx.moveTo(ax, ay - 6 * scaleFactor);
      ctx.lineTo(ax + 5 * scaleFactor, ay + 4 * scaleFactor);
      ctx.lineTo(ax - 5 * scaleFactor, ay + 4 * scaleFactor);
      ctx.closePath();
      ctx.fill();

      // Velocity arrow
      const w = activeWinds[ap.district || ap.id] || [1.0, 0.0];
      const speed = Math.hypot(w[0], w[1]);
      if (speed > 0.3) {
        const uNorm = w[0] / speed;
        const vNorm = -w[1] / speed;
        const arrowLen = (8 + speed * 7) * scaleFactor;
        ctx.strokeStyle = this.tokens.accent;
        ctx.lineWidth = 1.4 * scaleFactor;
        ctx.beginPath();
        ctx.moveTo(ax, ay);
        ctx.lineTo(ax + uNorm * arrowLen, ay + vNorm * arrowLen);
        ctx.stroke();
      }
    }

    // 3. Collision-Free Greedy District Labels (12-Offset Search + Leader Lines)
    const CANDIDATE_OFFSETS = [
      [0, 0], [0, 14], [0, -14], [16, 0], [-16, 0], [0, 26],
      [0, -26], [30, 8], [-30, 8], [24, -20], [-24, -20], [0, 38],
    ];

    const placedBoxes = [];
    const fontPx = Math.max(7, Math.round(11 * scaleFactor));
    ctx.font = `600 ${fontPx}px "JetBrains Mono", monospace`;

    // Sort order: Selected district first, then monitored, then unmonitored
    const sortedDistricts = [...this.districts].sort((a, b) => {
      if (a.name === this.selectedDistrict) return -1;
      if (b.name === this.selectedDistrict) return 1;
      return (a.est ? 1 : 0) - (b.est ? 1 : 0);
    });

    for (const dist of sortedDistricts) {
      if (!dist || !dist.xy) continue;
      const [ax, ay] = dist.xy;
      const isEst = !!(dist.est || dist.is_estimated);
      const val = districtReadings[dist.name];
      const fmtVal = val !== null && val !== undefined ? (this.pollutant === 'CO' ? (+val).toFixed(2) : Math.round(val)) : '–';
      const valStr = (isEst && val !== null ? '~' : '') + fmtVal;
      const labelText = `${dist.name} ${valStr}`;

      const textWidth = ctx.measureText(labelText).width;
      const boxW = textWidth + 8 * scaleFactor;
      const boxH = 16 * scaleFactor;

      let chosenOffset = null;

      // Greedy AABB collision search
      for (const [ox, oy] of CANDIDATE_OFFSETS) {
        const candidateBox = {
          x: ax + ox * scaleFactor - boxW / 2,
          y: ay + oy * scaleFactor - boxH / 2,
          w: boxW,
          h: boxH,
        };

        let collision = false;
        for (const placed of placedBoxes) {
          if (
            candidateBox.x < placed.x + placed.w &&
            candidateBox.x + candidateBox.w > placed.x &&
            candidateBox.y < placed.y + placed.h &&
            candidateBox.y + candidateBox.h > placed.y
          ) {
            collision = true;
            break;
          }
        }

        if (!collision) {
          chosenOffset = [ox, oy];
          placedBoxes.push(candidateBox);
          break;
        }
      }

      if (!chosenOffset) {
        chosenOffset = CANDIDATE_OFFSETS[0];
      }

      const lx = ax + chosenOffset[0] * scaleFactor;
      const ly = ay + chosenOffset[1] * scaleFactor;

      // Automated leader line for displacement > 20px
      const disp = Math.hypot(chosenOffset[0], chosenOffset[1]) * scaleFactor;
      if (disp > 20.0 * scaleFactor) {
        ctx.strokeStyle = this.tokens.inkSecondary;
        ctx.lineWidth = 0.8 * scaleFactor;
        ctx.beginPath();
        ctx.moveTo(ax, ay);
        ctx.lineTo(lx, ly);
        ctx.stroke();

        ctx.fillStyle = this.tokens.inkSecondary;
        ctx.beginPath();
        ctx.arc(ax, ay, 2 * scaleFactor, 0, Math.PI * 2);
        ctx.fill();
      }

      // District centroid node glyph
      const isSelected = dist.name === this.selectedDistrict;
      const r = (isSelected ? 8 : 5) * scaleFactor;
      ctx.fillStyle = getColorCss(val, this.pollutant, 0.9);
      ctx.beginPath();
      ctx.arc(ax, ay, r, 0, Math.PI * 2);
      ctx.fill();

      if (dist.est) {
        ctx.strokeStyle = this.tokens.inkPrimary;
        ctx.lineWidth = 1.2 * scaleFactor;
        ctx.setLineDash([2 * scaleFactor, 2 * scaleFactor]);
        ctx.stroke();
        ctx.setLineDash([]);
      } else {
        ctx.strokeStyle = isSelected ? this.tokens.accent : '#ffffff';
        ctx.lineWidth = (isSelected ? 2.0 : 1.2) * scaleFactor;
        ctx.stroke();
      }

      // Dual-pass text rendering: contrast halo + ink text
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';

      // Pass 1: Halo
      ctx.strokeStyle = this.theme === 'dark' ? 'rgba(15, 23, 22, 0.9)' : 'rgba(255, 255, 255, 0.9)';
      ctx.lineWidth = 3.0 * scaleFactor;
      ctx.strokeText(labelText, lx, ly);

      // Pass 2: Main Text
      ctx.fillStyle = this.tokens.inkPrimary;
      ctx.fillText(labelText, lx, ly);
    }

    ctx.restore();
  }

  /**
   * Primary Render Dispatcher.
   */
  render(state) {
    if (!this.ctx) return;

    // Reset transform and clear entire viewport canvas
    this.ctx.save();
    this.ctx.setTransform(1, 0, 0, 1, 0, 0);
    this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
    this.ctx.restore();

    this.ctx.save();
    this.ctx.scale(this.dpr, this.dpr);

    // Fill viewport background with geoSea
    this.ctx.fillStyle = this.tokens.geoSea || '#0b1211';
    this.ctx.fillRect(0, 0, this.width, this.height);

    // Apply interactive Zoom & Pan world transform
    this.ctx.translate(this.pan[0], this.pan[1]);
    this.ctx.scale(this.zoom, this.zoom);

    const activeStationPoints = state.activeStationPoints || null;

    // Layer 0: Static Basemap
    this.drawLayer0(this.ctx);

    // Layer 1: Continuous IDW or Choropleth
    this.drawLayer1(this.ctx, state.stationReadings, state.districtReadings, state.activeWinds, activeStationPoints);

    // Layer 2: 1300-Particle Advection
    this.drawLayer2(this.ctx, state.activeWinds);

    // Layer 3: Transport Vectors & Border Chevrons
    this.drawLayer3(this.ctx, state.transportLinks, state.activeWinds);

    // Layer 4: Station Glyphs & Collision-Free District Labels
    this.drawLayer4(this.ctx, state.stationReadings, state.districtReadings, state.activeWinds, activeStationPoints);

    this.ctx.restore();
  }
}
