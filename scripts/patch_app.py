with open('src/frontend/static/js/app.js', 'r', encoding='utf-8') as f:
    orig = f.read()

# 1. Update imports
old_import = "import { CanvasMapEngine, STATUTORY_LIMITS } from './canvas.js';"
new_import = """import {
  CanvasMapEngine,
  STATUTORY_LIMITS,
  PEPC_TIERS,
  BP,
  AQI_B,
  POLNAME,
  aqiBar,
  aqiTicks,
  bpTicks,
  barFor,
  limLabel,
  col,
  colArr,
  getColorRgb,
  getColorCss,
  aqiCat,
  isAQI,
  refFor
} from './canvas.js';"""

assert old_import in orig
content = orig.replace(old_import, new_import)

# 2. Add state fields to constructor
old_ctor = """    // Animation & Throttling Ticker
    this.lastFrameTime = performance.now();
    this.lastUiUpdateTime = 0;
  }"""

new_ctor = """    // Animation & Throttling Ticker
    this.lastFrameTime = performance.now();
    this.lastUiUpdateTime = 0;

    // Mini comparison maps state & Lahore inset
    this.minis = [];
    this.PB = null;
    this.lahoreCanvas = null;
    this.lctx = null;
    this.LW = 400;
    this.LH = 300;
    this.LB = { lo0: 74.08, lo1: 74.64, la0: 31.34, la1: 31.70 };
  }"""

assert old_ctor in content
content = content.replace(old_ctor, new_ctor)

# 3. In init(): call initMinis & sizeLahore, and add resize handlers
old_init_tail = """    // 6. Handle Window Resize
    window.addEventListener('resize', () => {
      if (this.canvasEngine) {
        this.canvasEngine.resize();
        this.recompilePaths();
      }
    });

    // 7. Start 60 FPS Animation Frame Loop
    requestAnimationFrame((t) => this.animationLoop(t));
  }"""

new_init_tail = """    // 5b. Initialize 9-Pollutant Mini Maps & Lahore Viewport
    this.initMinis();
    this.sizeLahore();

    // 6. Handle Window Resize
    window.addEventListener('resize', () => {
      if (this.canvasEngine) {
        this.canvasEngine.resize();
        this.recompilePaths();
      }
      this.sizeMinis();
      this.sizeLahore();
    });

    // 7. Start 60 FPS Animation Frame Loop
    requestAnimationFrame((t) => this.animationLoop(t));
  }"""

assert old_init_tail in content
content = content.replace(old_init_tail, new_init_tail)

# 4. In animationLoop: call drawMinis & drawLahore
old_anim = """    // Render Canvas Layers 0-4
    if (this.canvasEngine) {
      this.canvasEngine.currentHour = Math.floor(this.state.currentHour);
      this.canvasEngine.fractionalHour = this.state.currentHour;
      this.canvasEngine.pollutant = this.state.pollutant;
      this.canvasEngine.displayMode = this.state.displayMode;
      this.canvasEngine.showTransportLinks = this.state.showTransportLinks;
      this.canvasEngine.showRegionalWinds = this.state.showRegionalWinds;
      this.canvasEngine.selectedDistrict = this.state.selectedDistrict;

      this.canvasEngine.render(interpolated);
    }

    // Throttle UI DOM updates to 10 Hz (every 100ms) to eliminate DOM thrashing"""

new_anim = """    // Render Canvas Layers 0-4
    if (this.canvasEngine) {
      this.canvasEngine.currentHour = Math.floor(this.state.currentHour);
      this.canvasEngine.fractionalHour = this.state.currentHour;
      this.canvasEngine.pollutant = this.state.pollutant;
      this.canvasEngine.displayMode = this.state.displayMode;
      this.canvasEngine.showTransportLinks = this.state.showTransportLinks;
      this.canvasEngine.showRegionalWinds = this.state.showRegionalWinds;
      this.canvasEngine.selectedDistrict = this.state.selectedDistrict;

      this.canvasEngine.render(interpolated);
    }

    // Render 9-Pollutant Comparison Maps
    this.drawMinis();

    // Render Lahore Network Focus Inset Map
    this.drawLahore();

    // Throttle UI DOM updates to 10 Hz (every 100ms) to eliminate DOM thrashing"""

assert old_anim in content
content = content.replace(old_anim, new_anim)

# 5. In evaluateInterpolatedSlice: populate stationReadings and activeStationPoints
old_eval = """  evaluateInterpolatedSlice(fp) {
    const i = Math.floor(fp);
    const f = fp - i;
    const j = Math.min(this.state.totalHours - 1, i + 1);

    const districtReadings = {};
    const stationReadings = {};
    const activeWinds = {};

    // Districts
    if (this.hourlyObservations && this.hourlyObservations.districts) {
      for (const [name, series] of Object.entries(this.hourlyObservations.districts)) {
        const c0 = series.concentrations[i];
        const c1 = series.concentrations[j];
        let val = null;
        if (c0 !== null && c1 !== null) {
          val = (1.0 - f) * c0 + f * c1;
        } else if (c0 !== null) {
          val = c0;
        } else if (c1 !== null) {
          val = c1;
        }
        districtReadings[name] = val;

        // Winds
        const u0 = series.wind_u ? series.wind_u[i] : 0;
        const u1 = series.wind_u ? series.wind_u[j] : 0;
        const v0 = series.wind_v ? series.wind_v[i] : 0;
        const v1 = series.wind_v ? series.wind_v[j] : 0;
        activeWinds[name] = [
          (1.0 - f) * (u0 || 0) + f * (u1 || 0),
          (1.0 - f) * (v0 || 0) + f * (v1 || 0),
        ];
      }
    }

    // Transport links for hour i
    let links = [];
    if (this.baselineData && this.baselineData.pol && this.baselineData.pol[this.state.pollutant]) {
      const polData = this.baselineData.pol[this.state.pollutant];
      const frame = polData.frames && polData.frames[i];
      if (frame && frame.l) {
        links = frame.l.map(x => ({ src: x[0], rcv: x[1], flux: x[2] }));
      } else if (polData.links) {
        links = polData.links;
      }
    }

    return {
      districtReadings,
      stationReadings,
      activeWinds,
      transportLinks: links,
    };
  }"""

new_eval = """  evaluateInterpolatedSlice(fp) {
    const N = this.state.totalHours || 216;
    const i = Math.min(N - 1, Math.floor(fp));
    const f = fp - i;
    const j = Math.min(N - 1, i + 1);
    const wi = Math.min(N - 1, Math.round(fp));

    const districtReadings = {};
    const stationReadings = {};
    const activeStationPoints = [];
    const activeWinds = {};

    const polKey = this.state.pollutant;
    const polData = this.baselineData?.pol?.[polKey];

    // 1. Winds from baselineData or hourlyObservations
    const windHour = this.baselineData?.wind?.[wi];
    if (windHour) {
      for (const [dName, uv] of Object.entries(windHour)) {
        activeWinds[dName] = uv;
      }
    } else if (this.hourlyObservations && this.hourlyObservations.districts) {
      for (const [name, series] of Object.entries(this.hourlyObservations.districts)) {
        const u0 = series.wind_u ? series.wind_u[i] : 0;
        const u1 = series.wind_u ? series.wind_u[j] : 0;
        const v0 = series.wind_v ? series.wind_v[i] : 0;
        const v1 = series.wind_v ? series.wind_v[j] : 0;
        activeWinds[name] = [
          (1.0 - f) * (u0 || 0) + f * (u1 || 0),
          (1.0 - f) * (v0 || 0) + f * (v1 || 0),
        ];
      }
    }

    // 2. District Concentrations
    if (this.districts && this.districts.length > 0 && polData?.frames) {
      const fi = polData.frames[i];
      const fj = polData.frames[j];
      for (const d of this.districts) {
        const dName = d.name || d.district;
        const c0 = fi?.c?.[dName];
        const c1 = fj?.c?.[dName];
        let val = null;
        if (c0 !== null && c0 !== undefined && c1 !== null && c1 !== undefined) {
          val = (1.0 - f) * c0 + f * c1;
        } else if (c0 !== null && c0 !== undefined) {
          val = c0;
        } else if (c1 !== null && c1 !== undefined) {
          val = c1;
        }
        districtReadings[dName] = val;
      }
    } else if (this.hourlyObservations && this.hourlyObservations.districts) {
      for (const [name, series] of Object.entries(this.hourlyObservations.districts)) {
        const c0 = series.concentrations[i];
        const c1 = series.concentrations[j];
        let val = null;
        if (c0 !== null && c1 !== null) {
          val = (1.0 - f) * c0 + f * c1;
        } else if (c0 !== null) {
          val = c0;
        } else if (c1 !== null) {
          val = c1;
        }
        districtReadings[name] = val;
      }
    }

    // 3. Station Concentrations & Active Station Points for IDW & Glyphs
    if (this.stations && polData?.stations) {
      for (const s of this.stations) {
        const arr = polData.stations[s.name];
        if (!arr) continue;
        const x = arr[i];
        const y = arr[j];
        let v = null;
        if (x !== null && x !== undefined && y !== null && y !== undefined) {
          v = (1.0 - f) * x + f * y;
        } else if (x !== null && x !== undefined) {
          v = x;
        } else if (y !== null && y !== undefined) {
          v = y;
        }
        if (v !== null && v !== undefined && !isNaN(v)) {
          stationReadings[s.name] = v;
          const w = windHour?.[s.district || s.d] || activeWinds[s.district || s.d] || [0.5, 0.0];
          const px = s.xy ? s.xy[0] : (this.canvasEngine ? this.canvasEngine.project(s.lon, s.lat)[0] : 0);
          const py = s.xy ? s.xy[1] : (this.canvasEngine ? this.canvasEngine.project(s.lon, s.lat)[1] : 0);
          activeStationPoints.push({
            name: s.name,
            district: s.district || s.d,
            x: px,
            y: py,
            v: v,
            u: w[0] || 0.0,
            vWind: w[1] || 0.0,
            s: Math.hypot(w[0] || 0, w[1] || 0),
            mobile: s.mobile,
          });
        }
      }
    }

    // 4. Transport links for active pollutant hour i
    let links = [];
    if (polData?.frames?.[i]?.l) {
      links = polData.frames[i].l.map(x => ({ src: x[0], rcv: x[1], flux: x[2] }));
    } else if (polData?.links) {
      links = polData.links;
    }

    return {
      districtReadings,
      stationReadings,
      activeStationPoints,
      activeWinds,
      transportLinks: links,
    };
  }"""

assert old_eval in content
content = content.replace(old_eval, new_eval)

# 6. In updateThrottledUI: call updateLahoreTable
old_throttled = """    // Update Selected District Telemetry Drawer
    const selReadings = {
      current: slice.districtReadings[this.state.selectedDistrict],
      AQI: slice.districtReadings[this.state.selectedDistrict],
    };
    this.ui.renderSelectedDistrictTelemetry(this.state.selectedDistrict, selReadings, this.state.pollutant);
  }"""

new_throttled = """    // Update Selected District Telemetry Drawer
    const selReadings = {
      current: slice.districtReadings[this.state.selectedDistrict],
      AQI: slice.districtReadings[this.state.selectedDistrict],
    };
    this.ui.renderSelectedDistrictTelemetry(this.state.selectedDistrict, selReadings, this.state.pollutant);

    // Update Lahore Network Focus Live Table
    this.updateLahoreTable(Math.min(this.state.totalHours - 1, Math.round(this.state.currentHour)));
  }"""

assert old_throttled in content
content = content.replace(old_throttled, new_throttled)

# 7. In selectPollutant: clear fcKey and refresh hour
old_select = """  async selectPollutant(pollutantKey) {
    if (this.state.pollutant === pollutantKey) return;
    this.state.pollutant = pollutantKey;

    this.ui.renderPollutantButtons(pollutantKey);
    this.ui.updateLegend(pollutantKey);

    // Fetch new hourly series for selected pollutant
    const hourly = await this.apiClient.getHourlyObservations(pollutantKey);
    if (hourly) {
      this.hourlyObservations = hourly;
    }

    this.updateCPF();
  }"""

new_select = """  async selectPollutant(pollutantKey) {
    if (this.state.pollutant === pollutantKey) return;
    this.state.pollutant = pollutantKey;

    if (this.canvasEngine) {
      this.canvasEngine.pollutant = pollutantKey;
      this.canvasEngine.fcKey = '';
    }

    this.ui.renderPollutantButtons(pollutantKey);
    this.ui.updateLegend(pollutantKey);

    // Fetch new hourly series for selected pollutant if available
    try {
      const hourly = await this.apiClient.getHourlyObservations(pollutantKey);
      if (hourly) {
        this.hourlyObservations = hourly;
      }
    } catch (e) {
      console.warn('Hourly observations fetch fallback:', e);
    }

    this.updateCPF();
    this.refreshHourData(this.state.currentHour);
  }"""

assert old_select in content
content = content.replace(old_select, new_select)

# 8. Add all helper methods before refreshHourData
methods_to_add = """  // =========================================================================
  // MULTI-POLLUTANT 3x3 GRID & LAHORE NETWORK HELPERS
  // =========================================================================

  maxL(Q) {
    let m = 1e-9;
    if (Q && Q.frames) {
      for (const f of Q.frames) {
        if (f.l) {
          for (const l of f.l) {
            if (l[2] > m) m = l[2];
          }
        }
      }
    }
    return m;
  }

  mval(Q, dName, fp) {
    if (!Q || !Q.frames) return null;
    const N = this.state.totalHours || 216;
    const i = Math.min(N - 1, Math.floor(fp));
    const j = Math.min(N - 1, i + 1);
    const f = fp - i;
    const fi = Q.frames[i];
    const fj = Q.frames[j];
    const a = fi?.c?.[dName];
    const b = fj?.c?.[dName];
    if (a == null && b == null) return null;
    if (a == null) return b;
    if (b == null) return a;
    return a + (b - a) * f;
  }

  getStationPointsForPollutant(Q, fp) {
    if (!Q || !Q.stations || !this.stations) return [];
    const N = this.state.totalHours || 216;
    const i = Math.min(N - 1, Math.floor(fp));
    const j = Math.min(N - 1, i + 1);
    const f = fp - i;
    const wi = Math.min(N - 1, Math.round(fp));
    const windHour = this.baselineData?.wind?.[wi];

    const out = [];
    for (const s of this.stations) {
      const arr = Q.stations[s.name];
      if (!arr) continue;
      const x = arr[i];
      const y = arr[j];
      let v = null;
      if (x !== null && x !== undefined && y !== null && y !== undefined) {
        v = (1.0 - f) * x + f * y;
      } else if (x !== null && x !== undefined) {
        v = x;
      } else if (y !== null && y !== undefined) {
        v = y;
      }
      if (v == null || isNaN(v)) continue;

      const w = windHour?.[s.district || s.d];
      const px = s.xy ? s.xy[0] : (this.canvasEngine ? this.canvasEngine.project(s.lon, s.lat)[0] : 0);
      const py = s.xy ? s.xy[1] : (this.canvasEngine ? this.canvasEngine.project(s.lon, s.lat)[1] : 0);
      out.push({
        x: px,
        y: py,
        v,
        u: w ? w[0] : null,
        vWind: w ? w[1] : null,
      });
    }
    return out;
  }

  renderMiniField(cvs, x0, y0, w0, h0, scale, cell, Q, r, fp) {
    const pts = this.getStationPointsForPollutant(Q, fp);
    if (!pts || pts.length === 0) return 0;

    const gw = Math.ceil(w0 / cell);
    const gh = Math.ceil(h0 / cell);
    if (cvs.width !== gw || cvs.height !== gh) {
      cvs.width = gw;
      cvs.height = gh;
    }
    const g = cvs.getContext('2d');
    const img = g.createImageData(gw, gh);
    const data = img.data;
    const kmU = 111.0 / (this.canvasEngine ? this.canvasEngine.S : 1.0);

    for (let yy = 0; yy < gh; yy++) {
      for (let xx = 0; xx < gw; xx++) {
        const mx = x0 + (xx + 0.5) * cell / scale;
        const my = y0 + (yy + 0.5) * cell / scale;

        let ws = 0.0, vs = 0.0, dmin = 1e9;
        for (let i = 0; i < pts.length; i++) {
          const p = pts[i];
          const dx = mx - p.x;
          const dy = my - p.y;
          const d2 = dx * dx + dy * dy;
          const d = Math.sqrt(d2);
          if (d < dmin) dmin = d;

          let w = 1.0 / (d2 + 16.0);
          if (p.u != null && d > 2.0) {
            const sp = Math.hypot(p.u, p.vWind);
            if (sp > 0.5) {
              const c = (dx * p.u - dy * p.vWind) / (d * sp);
              w *= Math.max(0.3, 1.0 + 0.7 * c * Math.min(1.0, sp / 1.5));
            }
          }
          ws += w;
          vs += w * p.v;
        }

        const val = ws > 0 ? vs / ws : 0;
        const c = colArr(val, r);
        const km = dmin * kmU;
        const alpha = km < 45.0 ? 235 : km > 140.0 ? 95 : Math.round(235 - 140 * (km - 45.0) / 95.0);

        const o = (yy * gw + xx) * 4;
        data[o] = c[0];
        data[o + 1] = c[1];
        data[o + 2] = c[2];
        data[o + 3] = alpha;
      }
    }

    g.putImageData(img, 0, 0);
    return 1;
  }

  initMinis() {
    const container = document.getElementById('miniGridContainer') || document.getElementById('minis');
    if (!container || !this.baselineData || !this.baselineData.pol) return;

    const CMP = ['AQI', 'PM2.5', 'PM10', 'NO2', 'SO2', 'CO', 'O3', 'NO', 'NOX'];
    container.innerHTML = CMP.map(p => {
      const Q = this.baselineData.pol[p];
      if (!Q) return '';
      const pClean = p.replace('.', '');
      const unitLabel = isAQI(Q) ? '' : `${Q.unit || 'µg/m³'} · `;
      const limit = limLabel(Q);
      const barBg = barFor(Q);
      const ticksHtml = isAQI(Q) ? aqiTicks() : (BP[p] ? bpTicks(p) : '');
      const fallbackTicks = (isAQI(Q) || BP[p]) ? '' : [0, 1, 2.5, 4, 6].map(m => {
        const pct = Math.min(94, Math.max(5, (m / 6) * 100));
        const num = p === 'CO' ? (m * (Q.ref || 100)).toFixed(1) : Math.round(m * (Q.ref || 100));
        return `<span style="left:${pct}%">${num}${m === 6 ? '+' : ''}</span>`;
      }).join('');

      return `
        <figure class="mini" id="mini_card_${pClean}">
          <figcaption>
            <b>${POLNAME[p] || p}</b>
            <span>${unitLabel}${limit}<br><span id="mm_${pClean}"></span></span>
          </figcaption>
          <canvas id="mc_${pClean}" class="mini-canvas" aria-label="${POLNAME[p] || p} map"></canvas>
          <div class="mleg">
            <div class="mbar" style="background:${barBg};"></div>
            <div class="mticks">${ticksHtml}${fallbackTicks}</div>
          </div>
        </figure>
      `;
    }).join('');

    this.minis = CMP.map(p => {
      const pClean = p.replace('.', '');
      const cv = document.getElementById('mc_' + pClean);
      const Q = this.baselineData.pol[p];
      return {
        p,
        cv,
        g: cv ? cv.getContext('2d') : null,
        Q,
        r: refFor(Q),
        maxf: this.maxL(Q),
        means: Q && Q.frames ? Q.frames.map(f => {
          const v = this.districts ? this.districts.filter(d => !d.est).map(d => f.c[d.name || d.district]).filter(x => x != null) : [];
          return v.length ? v.reduce((a, b) => a + b, 0) / v.length : null;
        }) : [],
      };
    });

    this.sizeMinis();
  }

  sizeMinis() {
    if (!this.canvasEngine || !this.minis || this.minis.length === 0) return;
    const [x0, y0] = this.canvasEngine.project(69.25, 34.1);
    const [x1, y1] = this.canvasEngine.project(75.45, 27.62);
    this.PB = { x0, y0, w: x1 - x0, h: y1 - y0 };

    const dp = Math.min(2, window.devicePixelRatio || 1);
    for (const m of this.minis) {
      if (!m.cv || !m.g) continue;
      const r = m.cv.getBoundingClientRect();
      m.W = r.width || 300;
      m.k = m.W / this.PB.w;
      m.H = this.PB.h * m.k;
      m.dp = dp;
      m.cv.width = Math.round(m.W * dp);
      m.cv.height = Math.round(m.H * dp);
      m.cv.style.height = m.H + 'px';

      // Click district on mini map selects it
      m.cv.onclick = (e) => {
        const b = m.cv.getBoundingClientRect();
        const x = (e.clientX - b.left) / m.k + this.PB.x0;
        const y = (e.clientY - b.top) / m.k + this.PB.y0;
        if (this.canvasEngine && this.canvasEngine.paths) {
          for (const adm of this.canvasEngine.paths.admPaths) {
            if (this.canvasEngine.hitCtx && this.canvasEngine.hitCtx.isPointInPath(adm.path, x, y)) {
              this.selectDistrict(adm.name);
              break;
            }
          }
        }
      };
    }
  }

  drawMinis() {
    if (!this.PB || !this.minis || this.minis.length === 0) return;
    const fp = this.state.currentHour;
    const fr = Math.min(this.state.totalHours - 1, Math.round(fp));
    const paths = this.canvasEngine?.paths;
    if (!paths) return;

    for (const m of this.minis) {
      if (!m.cv || !m.g) continue;
      const g = m.g;
      const k = m.k;
      const Q = m.Q;
      if (!Q) continue;
      const fm = (v) => v == null ? '–' : (m.p === 'CO' ? (+v).toFixed(1) : Math.round(v));

      g.save();
      g.setTransform(m.dp * k, 0, 0, m.dp * k, -this.PB.x0 * m.dp * k, -this.PB.y0 * m.dp * k);

      // Background sea & land
      g.fillStyle = this.canvasEngine.tokens.geoSea;
      g.fillRect(this.PB.x0, this.PB.y0, this.PB.w, this.PB.h);

      g.fillStyle = this.canvasEngine.tokens.geoLand;
      if (paths.provPaths) {
        for (const p of paths.provPaths) g.fill(p);
      }
      if (paths.indPath) {
        g.fillStyle = this.canvasEngine.tokens.geoIndia;
        g.fill(paths.indPath);
      }

      if (this.state.displayMode === 'surface') {
        g.fillStyle = this.canvasEngine.tokens.geoPunjab;
        g.fill(paths.pjPath);
        m.fc = m.fc || document.createElement('canvas');
        const key = Math.round(fp * 4) + '|' + m.W;
        if (m.fk !== key) {
          m.fk = key;
          this.renderMiniField(m.fc, this.PB.x0, this.PB.y0, m.W, m.H, k, 4, Q, m.r, fp);
        }
        g.save();
        g.clip(paths.pjPath);
        g.imageSmoothingEnabled = true;
        g.drawImage(m.fc, this.PB.x0, this.PB.y0, (m.fc.width * 4) / k, (m.fc.height * 4) / k);
        g.restore();
      } else {
        // Administrative choropleth mode
        for (const adm of paths.admPaths) {
          const v = this.mval(Q, adm.name, fp);
          g.fillStyle = v == null ? this.canvasEngine.tokens.geoPunjab : col(v, 0.9, m.r);
          g.fill(adm.path);
          if (adm.is_estimated && v != null) {
            if (!m.pat && this.canvasEngine.hatchPattern) m.pat = this.canvasEngine.hatchPattern;
            if (m.pat) {
              g.fillStyle = m.pat;
              g.fill(adm.path);
            }
          }
        }
      }

      // Boundaries
      g.strokeStyle = this.canvasEngine.tokens.inkPrimary;
      g.globalAlpha = 0.4;
      g.lineWidth = 0.6 / k;
      for (const adm of paths.admPaths) {
        g.stroke(adm.path);
      }
      g.globalAlpha = 1.0;

      // Selected district outline
      const selAdm = paths.admPaths.find(a => a.name === this.state.selectedDistrict);
      if (selAdm) {
        g.lineWidth = 2.0 / k;
        g.strokeStyle = this.canvasEngine.tokens.inkPrimary;
        g.stroke(selAdm.path);
      }

      // Outer provincial boundary
      g.lineWidth = 1.1 / k;
      g.strokeStyle = this.canvasEngine.tokens.geoBorder;
      g.stroke(paths.pjPath);

      // Border dash
      if (paths.borderPath) {
        g.save();
        g.strokeStyle = this.canvasEngine.tokens.geoBorder;
        g.lineWidth = 1.8 / k;
        g.setLineDash([6 / k, 3 / k]);
        g.stroke(paths.borderPath);
        g.restore();
      }

      // Switch to pixel coordinates for text & arrows
      g.setTransform(m.dp, 0, 0, m.dp, 0, 0);
      const Px = (x, y) => [(x - this.PB.x0) * k, (y - this.PB.y0) * k];

      // Transport links (if enabled and not AQI)
      if (this.state.showTransportLinks && !isAQI(Q) && Q.frames && Q.frames[fr] && Q.frames[fr].l) {
        const ls = Q.frames[fr].l.slice()
          .sort((a, b) => b[2] - a[2])
          .filter(l => l[2] >= (m.maxf || 1) * 0.08)
          .slice(0, 8);

        for (const [a, b, fl] of ls) {
          const distA = this.districts.find(d => (d.name || d.district) === a);
          const distB = this.districts.find(d => (d.name || d.district) === b);
          if (!distA || !distB || !distA.xy || !distB.xy) continue;

          const [x0, y0] = Px(...distA.xy);
          const [x1, y1] = Px(...distB.xy);
          const dx = x1 - x0, dy = y1 - y0;
          const L = Math.hypot(dx, dy);
          if (L < 1) continue;
          const ux = dx / L, uy = dy / L;
          const sx = x0 + ux * 5, sy = y0 + uy * 5;
          const ex = x1 - ux * 6, ey = y1 - uy * 6;
          const w = 1 + 2.6 * Math.sqrt(fl / (m.maxf || 1));

          g.strokeStyle = this.canvasEngine.tokens.vectorTransport;
          g.globalAlpha = 0.85;
          g.lineWidth = w;
          g.lineCap = 'round';
          g.beginPath();
          g.moveTo(sx, sy);
          g.lineTo(ex, ey);
          g.stroke();

          const hs = 4 + w;
          g.fillStyle = this.canvasEngine.tokens.vectorTransport;
          g.beginPath();
          g.moveTo(ex, ey);
          g.lineTo(ex - ux * hs - uy * hs * 0.55, ey - uy * hs + ux * hs * 0.55);
          g.lineTo(ex - ux * hs + uy * hs * 0.55, ey - uy * hs - ux * hs * 0.55);
          g.closePath();
          g.fill();
          g.globalAlpha = 1.0;
        }
      }

      // Station points or collision-free district numbers
      if (this.state.displayMode === 'surface') {
        const pts = this.getStationPointsForPollutant(Q, fp);
        for (const p of pts) {
          const [x, y] = Px(p.x, p.y);
          g.beginPath();
          g.arc(x, y, 2.4, 0, Math.PI * 2);
          g.fillStyle = col(p.v, 1.0, m.r);
          g.fill();
          g.strokeStyle = this.canvasEngine.tokens.inkPrimary;
          g.lineWidth = 0.8;
          g.stroke();
        }
      } else {
        const placed = [];
        g.font = `700 ${m.W > 420 ? 11 : 9.5}px ${this.canvasEngine.tokens.fontMono}`;
        g.textAlign = 'center';
        g.lineJoin = 'round';

        const items = this.districts.map(dist => {
          const dName = dist.name || dist.district;
          const xy = dist.xy || [0, 0];
          return {
            n: dName,
            xy: Px(xy[0], xy[1]),
            v: this.mval(Q, dName, fp),
            est: dist.est,
          };
        }).sort((a, b) => (b.n === this.state.selectedDistrict) - (a.n === this.state.selectedDistrict) || (a.est - b.est));

        for (const it of items) {
          if (it.v == null) continue;
          const s = (it.est ? '~' : '') + fm(it.v);
          const tw = g.measureText(s).width;
          const [x, y] = it.xy;
          let best = null;
          for (const [dx, dy] of [[0, 0], [0, 10], [0, -10], [12, 0], [-12, 0]]) {
            const r = [x + dx - tw / 2 - 1, y + dy - 8, tw + 2, 11];
            if (!placed.some(q => r[0] < q[0] + q[2] && r[0] + r[2] > q[0] && r[1] < q[1] + q[3] && r[1] + r[3] > q[1])) {
              best = [x + dx, y + dy, r];
              break;
            }
          }
          if (!best) continue;
          placed.push(best[2]);
          g.lineWidth = 2.6;
          g.strokeStyle = 'rgba(255,255,255,.85)';
          g.fillStyle = '#17221f';
          g.strokeText(s, best[0], best[1] + 2);
          g.fillText(s, best[0], best[1] + 2);
        }
        g.textAlign = 'left';
      }

      g.restore();

      // Update subtitle: province mean and exceedances
      const mm = m.means[fr];
      const el = document.getElementById('mm_' + m.p.replace('.', ''));
      if (el) {
        const overCount = this.districts
          ? this.districts
              .filter(d => !d.est)
              .map(d => Q.frames?.[fr]?.c?.[d.name || d.district])
              .filter(v => v != null && v > (Q.ref || 0)).length
          : 0;
        el.textContent = `province mean ${fm(mm)}` + (Q.ref ? ` · ${overCount} district${overCount === 1 ? '' : 's'} above limit` : '');
      }
    }
  }

  sizeLahore() {
    this.lahoreCanvas = document.getElementById('lahoreMapCanvas');
    if (!this.lahoreCanvas) return;
    this.lctx = this.lahoreCanvas.getContext('2d');
    const r = this.lahoreCanvas.getBoundingClientRect();
    const dp = Math.min(2, window.devicePixelRatio || 1);
    this.LW = r.width || 400;
    this.LH = r.height || 300;
    this.lahoreCanvas.width = Math.round(this.LW * dp);
    this.lahoreCanvas.height = Math.round(this.LH * dp);
    this.lctx.scale(dp, dp);
  }

  drawLahore() {
    if (!this.lahoreCanvas || !this.lctx || !this.canvasEngine) return;
    const g = this.lctx;
    const LW = this.LW;
    const LH = this.LH;
    const LB = this.LB;
    const fp = this.state.currentHour;
    const fi = Math.min(this.state.totalHours - 1, Math.floor(fp));
    const fj = Math.min(this.state.totalHours - 1, fi + 1);
    const f = fp - fi;

    const Qproj = (lo, la) => [
      ((lo - LB.lo0) / (LB.lo1 - LB.lo0)) * LW,
      ((LB.la1 - la) / (LB.la1 - LB.la0)) * LH,
    ];

    g.save();
    g.fillStyle = this.canvasEngine.tokens.geoSea;
    g.fillRect(0, 0, LW, LH);

    // India region
    if (this.geoBoundaries && this.geoBoundaries.IND) {
      g.fillStyle = this.canvasEngine.tokens.geoIndia;
      for (const poly of Object.values(this.geoBoundaries.IND)) {
        for (const ring of poly) {
          g.beginPath();
          ring.forEach((pt, idx) => {
            const [x, y] = Qproj(pt[0], pt[1]);
            if (idx === 0) g.moveTo(x, y);
            else g.lineTo(x, y);
          });
          g.closePath();
          g.fill();
        }
      }
    }

    // Lahore and border districts
    const polData = this.baselineData?.pol?.[this.state.pollutant];
    const lahoreVal = polData?.frames?.[fi]?.c?.Lahore;
    g.fillStyle = lahoreVal != null ? col(lahoreVal, 0.35, refFor(polData)) : this.canvasEngine.tokens.geoPunjab;
    g.fillRect(0, 0, LW * 0.75, LH);

    // Border line dash
    if (this.tbgeo && this.tbgeo.border) {
      g.save();
      g.strokeStyle = this.canvasEngine.tokens.geoBorder;
      g.lineWidth = 2.4;
      g.setLineDash([8, 4]);
      g.beginPath();
      this.tbgeo.border.forEach((pt, idx) => {
        const [x, y] = Qproj(pt[0], pt[1]);
        if (idx === 0) g.moveTo(x, y);
        else g.lineTo(x, y);
      });
      g.stroke();
      g.restore();
    }

    // INDIA label
    g.fillStyle = this.canvasEngine.tokens.inkSecondary;
    g.font = `700 16px ${this.canvasEngine.tokens.fontDisplay}`;
    g.fillText('INDIA', LW - 60, LH * 0.55);

    // Wind arrow indicator for Lahore
    const wi = Math.min(this.state.totalHours - 1, Math.round(fp));
    const lahoreWind = this.baselineData?.wind?.[wi]?.Lahore;
    if (lahoreWind) {
      const [u, v] = lahoreWind;
      const ws = Math.hypot(u, v);
      const cx = 38, cy = LH - 38;
      g.strokeStyle = this.canvasEngine.tokens.inkPrimary;
      g.fillStyle = this.canvasEngine.tokens.inkPrimary;
      g.beginPath();
      g.arc(cx, cy, 22, 0, Math.PI * 2);
      g.globalAlpha = 0.25;
      g.stroke();
      g.globalAlpha = 1.0;

      if (ws > 0.1) {
        const ux = u / ws, uy = -v / ws, k = 18;
        g.lineWidth = 2.4;
        g.beginPath();
        g.moveTo(cx - ux * k, cy - uy * k);
        g.lineTo(cx + ux * k, cy + uy * k);
        g.stroke();

        g.beginPath();
        g.moveTo(cx + ux * k, cy + uy * k);
        g.lineTo(cx + ux * k - ux * 7 - uy * 5, cy + uy * k - uy * 7 + ux * 5);
        g.lineTo(cx + ux * k - ux * 7 + uy * 5, cy + uy * k - uy * 7 - ux * 5);
        g.closePath();
        g.fill();
      }
      g.font = `11px ${this.canvasEngine.tokens.fontMono}`;
      g.fillText(`wind ${ws.toFixed(1)} m/s`, cx - 26, cy - 28);
    }

    // Lahore Stations
    const lahoreStations = this.stations.filter(s => (s.district || s.d) === 'Lahore');
    const pts = lahoreStations.map(s => {
      const a = polData?.stations?.[s.name]?.[fi];
      const b = polData?.stations?.[s.name]?.[fj];
      let v = null;
      if (a !== null && a !== undefined && b !== null && b !== undefined) v = (1 - f) * a + f * b;
      else if (a !== null && a !== undefined) v = a;
      else if (b !== null && b !== undefined) v = b;
      return {
        s,
        xy: Qproj(s.longitude || s.lon, s.latitude || s.lat),
        v,
      };
    }).sort((a, b) => a.xy[1] - b.xy[1]);

    // Draw station glyphs
    for (const o of pts) {
      const [x, y] = o.xy;
      g.beginPath();
      if (o.s.mobile) {
        g.moveTo(x, y - 8);
        g.lineTo(x + 7, y + 5);
        g.lineTo(x - 7, y + 5);
        g.closePath();
      } else {
        g.rect(x - 6, y - 6, 12, 12);
      }
      g.fillStyle = o.v == null ? this.canvasEngine.tokens.bgPanel : col(o.v, 1.0, refFor(polData));
      g.fill();
      g.strokeStyle = this.canvasEngine.tokens.inkPrimary;
      g.lineWidth = 1.4;
      g.stroke();
    }

    // Draw collision-free labels
    g.font = `600 11.5px ${this.canvasEngine.tokens.fontMono}`;
    g.lineJoin = 'round';
    for (const o of pts) {
      const [x, y] = o.xy;
      const shortName = o.s.name.replace(/-LHR$/, '').replace(/ LHR - Mobile \d| - Mobile \d/, '').replace('Govt. Teaching Hospital ', 'GTH ').trim();
      const valFmt = o.v == null ? '–' : (this.state.pollutant === 'CO' ? (+o.v).toFixed(1) : Math.round(o.v));
      const lb = `${shortName} ${valFmt}`;
      const tw = g.measureText(lb).width;
      const lx = x > LW * 0.6 ? x - tw - 10 : x + 10;
      const ly = y + 4;

      g.lineWidth = 3;
      g.strokeStyle = 'rgba(255,255,255,.85)';
      g.strokeText(lb, lx, ly);
      g.fillStyle = '#17221f';
      g.fillText(lb, lx, ly);
    }

    g.restore();
  }

  updateLahoreTable(fr) {
    const tbody = document.getElementById('lahoreTableBody');
    if (!tbody || !this.stations) return;

    const polData = this.baselineData?.pol?.[this.state.pollutant];
    if (!polData || !polData.stations) return;

    const lahoreStations = this.stations.filter(s => (s.district || s.d) === 'Lahore');
    const N = this.state.totalHours || 216;
    const fmt = v => v == null ? '–' : (this.state.pollutant === 'CO' ? (+v).toFixed(1) : Math.round(v));
    const r = refFor(polData);

    tbody.innerHTML = lahoreStations.map(s => {
      const vs = polData.stations[s.name] || [];
      const v = vs[fr];
      const valid = vs.filter(x => x != null && !isNaN(x));
      const m = valid.length >= Math.max(1, Math.round(0.75 * N)) ? valid.reduce((a, b) => a + b, 0) / valid.length : null;
      const shortName = s.name.replace(/-LHR$/, '').replace(/ LHR - Mobile \d| - Mobile \d/, '').replace('Govt. Teaching Hospital ', 'GTH ').trim();
      const typeStr = s.mobile ? '▲ Mobile' : '■ Fixed';
      const swatch = v != null ? `<span class="swatch" style="background:${col(v, 1.0, r)}"></span>` : '';

      return `<tr>
        <td>${shortName}</td>
        <td>${typeStr}</td>
        <td class="r num">${swatch}${fmt(v)}</td>
        <td class="r num">${fmt(m)}</td>
      </tr>`;
    }).join('');
  }
"""

assert "  refreshHourData(hour) {" in content
content = content.replace("  refreshHourData(hour) {", methods_to_add + "\n  refreshHourData(hour) {")

with open('src/frontend/static/js/app.js', 'w', encoding='utf-8') as f:
    f.write(content)

print("app.js patched successfully! New length:", len(content))
