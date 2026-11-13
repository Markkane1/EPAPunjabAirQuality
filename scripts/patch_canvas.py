with open('src/frontend/static/js/canvas.js', 'r', encoding='utf-8') as f:
    orig = f.read()

# Let's verify what we want to replace in canvas.js:
# 1. Definitions at top:
new_header = '''/**
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
'''

# Find where CanvasMapEngine class begins
class_start = orig.find('export class CanvasMapEngine {')
assert class_start != -1

# Inside constructor, add this.fcKey = '';
rest_of_file = orig[class_start:]
rest_of_file = rest_of_file.replace(
    "this.fcCtx = this.fcCanvas.getContext('2d');",
    "this.fcCtx = this.fcCanvas.getContext('2d');\n    this.fcKey = '';"
)

# In drawLayer1:
l1_old = """    // Continuous Surface Mode via Downsampled IDW Grid
    const activeStations = [];
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

    // Draw bilinear upsampled raster clipped to Punjab
    ctx.save();
    ctx.clip(this.paths.pjPath);
    ctx.imageSmoothingEnabled = true;
    ctx.drawImage(this.fcCanvas, 0, 0, gw * 5, gh * 5);
    ctx.restore();"""

l1_new = """    // Continuous Surface Mode via Downsampled IDW Grid
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
    ctx.restore();"""

rest_of_file = rest_of_file.replace(
    "drawLayer1(ctx, stationReadings, districtReadings, activeWinds) {",
    "drawLayer1(ctx, stationReadings, districtReadings, activeWinds, activeStationPoints = null) {"
)
assert l1_old in rest_of_file
rest_of_file = rest_of_file.replace(l1_old, l1_new)

# In drawLayer4:
l4_old_head = """  drawLayer4(ctx, stationReadings, districtReadings, activeWinds) {
    ctx.save();

    // 1. Fixed AQMS Stations (3.6px square)
    ctx.fillStyle = this.tokens.inkPrimary;
    ctx.globalAlpha = 0.8;
    for (const st of this.stations) {
      if (!st || !st.xy) continue;
      ctx.fillRect(st.xy[0] - 1.8, st.xy[1] - 1.8, 3.6, 3.6);
    }"""

l4_new_head = """  drawLayer4(ctx, stationReadings, districtReadings, activeWinds, activeStationPoints = null) {
    ctx.save();

    // 1. Fixed AQMS Stations (Circles in surface mode, Squares in district mode)
    if (this.displayMode === 'surface') {
      if (activeStationPoints && activeStationPoints.length > 0) {
        for (const p of activeStationPoints) {
          ctx.beginPath();
          ctx.arc(p.x, p.y, 3.6, 0, Math.PI * 2);
          ctx.fillStyle = getColorCss(p.v, this.pollutant, 1.0);
          ctx.fill();
          ctx.strokeStyle = this.tokens.inkPrimary || '#17221f';
          ctx.lineWidth = 1.0;
          ctx.stroke();
        }
      } else {
        for (const st of this.stations) {
          if (!st || !st.xy) continue;
          const v = stationReadings[st.name];
          if (v !== undefined && v !== null && !isNaN(v)) {
            ctx.beginPath();
            ctx.arc(st.xy[0], st.xy[1], 3.6, 0, Math.PI * 2);
            ctx.fillStyle = getColorCss(v, this.pollutant, 1.0);
            ctx.fill();
            ctx.strokeStyle = this.tokens.inkPrimary || '#17221f';
            ctx.lineWidth = 1.0;
            ctx.stroke();
          } else {
            ctx.fillStyle = this.tokens.inkPrimary || '#17221f';
            ctx.globalAlpha = 0.8;
            ctx.fillRect(st.xy[0] - 1.8, st.xy[1] - 1.8, 3.6, 3.6);
            ctx.globalAlpha = 1.0;
          }
        }
      }
    } else {
      ctx.fillStyle = this.tokens.inkPrimary || '#17221f';
      ctx.globalAlpha = 0.8;
      for (const st of this.stations) {
        if (!st || !st.xy) continue;
        ctx.fillRect(st.xy[0] - 1.8, st.xy[1] - 1.8, 3.6, 3.6);
      }
      ctx.globalAlpha = 1.0;
    }"""

assert l4_old_head in rest_of_file
rest_of_file = rest_of_file.replace(l4_old_head, l4_new_head)

# In drawLayer4, format value for CO:
val_old = """      const val = districtReadings[dist.name];
      const valStr = val !== null && val !== undefined ? `${Math.round(val)}` : '~';
      const labelText = `${dist.name} ${valStr}`;"""

val_new = """      const isEst = !!(dist.est || dist.is_estimated);
      const val = districtReadings[dist.name];
      const fmtVal = val !== null && val !== undefined ? (this.pollutant === 'CO' ? (+val).toFixed(2) : Math.round(val)) : '–';
      const valStr = (isEst && val !== null ? '~' : '') + fmtVal;
      const labelText = `${dist.name} ${valStr}`;"""

assert val_old in rest_of_file
rest_of_file = rest_of_file.replace(val_old, val_new)

# In render: pass activeStationPoints
render_old = """  render(state) {
    if (!this.ctx) return;

    this.ctx.save();
    this.ctx.scale(this.dpr, this.dpr);

    // Layer 0: Static Basemap
    this.drawLayer0(this.ctx);

    // Layer 1: Continuous IDW or Choropleth
    this.drawLayer1(this.ctx, state.stationReadings, state.districtReadings, state.activeWinds);

    // Layer 2: 1300-Particle Advection
    this.drawLayer2(this.ctx, state.activeWinds);

    // Layer 3: Transport Vectors & Border Chevrons
    this.drawLayer3(this.ctx, state.transportLinks, state.activeWinds);

    // Layer 4: Station Glyphs & Collision-Free District Labels
    this.drawLayer4(this.ctx, state.stationReadings, state.districtReadings, state.activeWinds);

    this.ctx.restore();
  }"""

render_new = """  render(state) {
    if (!this.ctx) return;

    this.ctx.save();
    this.ctx.scale(this.dpr, this.dpr);

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
  }"""

assert render_old in rest_of_file
rest_of_file = rest_of_file.replace(render_old, render_new)

final_canvas = new_header + "\n" + rest_of_file

with open('src/frontend/static/js/canvas.js', 'w', encoding='utf-8') as f:
    f.write(final_canvas)

print("canvas.js updated successfully! New length:", len(final_canvas))
