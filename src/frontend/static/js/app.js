/**
 * Master Application Coordinator for Punjab Air Quality Operational Console.
 * Coordinates 60 FPS Canvas Map Engine, API Gateway client, and UI Controller.
 */

import { ApiClient } from './api.js';
import { compilePaths, project } from './geo.js';
import {
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
} from './canvas.js';
import { UIController } from './ui.js';

export class App {
  constructor() {
    this.apiClient = new ApiClient();
    this.canvasEngine = null;
    this.ui = null;

    // Global Interactive State
    this.state = {
      pollutant: 'AQI',
      selectedDistrict: 'Lahore',
      currentHour: 0.0,
      totalHours: 216,
      isPlaying: true,
      playbackSpeed: 0.8,
      displayMode: 'surface',
      showTransportLinks: true,
      showRegionalWinds: true,
      activeView: 'console',
      theme: 'dark',
      isLiveNowcast: true,
    };

    // Cached Domain Datasets
    this.districts = [];
    this.stations = [];
    this.airports = [];
    this.hourlyObservations = null;
    this.hourlyWinds = [];
    this.transportLinks = [];
    this.borderSamples = [];
    this.timestamps = [];

    // Animation & Throttling Ticker
    this.lastFrameTime = performance.now();
    this.lastUiUpdateTime = 0;

    // Mini comparison maps state & Lahore inset
    this.minis = [];
    this.PB = null;
    this.state.gridZoomDistrict = null;
    this.gridCurrentPB = null;
    this.gridTargetPB = null;
    this.districtBounds = new Map();
    this.lahoreCanvas = null;
    this.lctx = null;
    this.LW = 400;
    this.LH = 300;
    this.LB = { lo0: 74.08, lo1: 74.64, la0: 31.34, la1: 31.70 };
  }

  async init() {
    console.log('Initializing Punjab Air Quality Dashboard Console...');

    // 1. Initialize UI Controller
    this.ui = new UIController(this);
    this.ui.renderPollutantButtons(this.state.pollutant);
    this.ui.updateLegend(this.state.pollutant);

    // 2. Initialize Canvas Map Engine
    const mainCanvas = document.getElementById('mainMapCanvas');
    if (mainCanvas) {
      this.canvasEngine = new CanvasMapEngine(mainCanvas);
      this.canvasEngine.resize();
      this.setupMapInteraction(mainCanvas);
    }

    // 3. Load Geodata & Topology
    await this.loadCartographyAndMetadata();

    // 4. Load Baseline Telemetry & Hourly Series
    await this.loadInitialTelemetry();

    // 5. Connect SSE Live Stream
    this.apiClient.connectLiveStream(
      (update) => this.onLiveHourlyUpdate(update),
      (err) => console.warn('SSE stream error:', err),
      (mode) => this.ui.updateLiveStatus(mode)
    );

    // 5b. Initialize 9-Pollutant Mini Maps & Lahore Viewport
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
  }

  async loadCartographyAndMetadata() {
    const [geoBoundaries, districts, stations] = await Promise.all([
      this.apiClient.getGeoBoundaries(),
      this.apiClient.getDistrictsMeta(),
      this.apiClient.getStationsMeta(),
    ]);

    this.geoBoundaries = geoBoundaries;
    this.districts = districts || [];
    this.stations = stations || [];

    // Populate District Selector Dropdown in UI
    const selDropdown = document.getElementById('districtSelectDropdown');
    if (selDropdown && this.districts.length > 0) {
      selDropdown.innerHTML = '';
      this.districts.forEach(d => {
        const opt = document.createElement('option');
        opt.value = d.name || d.district;
        opt.textContent = `${d.name || d.district} ${d.est ? '(Est)' : ''}`;
        if (opt.value === this.state.selectedDistrict) opt.selected = true;
        selDropdown.appendChild(opt);
      });
    }

    this.recompilePaths();
  }

  recompilePaths() {
    if (!this.canvasEngine || !this.geoBoundaries) return;

    const S = this.canvasEngine.S;
    const paths = compilePaths(
      this.geoBoundaries.GEO,
      this.geoBoundaries.IND,
      this.tbgeo || { border: [] },
      this.districts,
      S
    );

    // Project district centroids & station coordinates into screen space
    this.districts.forEach(d => {
      const lon = d.lon !== undefined ? d.lon : (d.longitude || (d.centroid && d.centroid[0]));
      const lat = d.lat !== undefined ? d.lat : (d.latitude || (d.centroid && d.centroid[1]));
      d.xy = project(lon, lat, S);
    });

    this.stations.forEach(s => {
      const lon = s.longitude !== undefined ? s.longitude : s.lon;
      const lat = s.latitude !== undefined ? s.latitude : s.lat;
      if (lon !== undefined && lat !== undefined) {
        s.xy = project(lon, lat, S);
      }
    });

    this.airports.forEach(a => {
      const lon = a.longitude !== undefined ? a.longitude : a.lon;
      const lat = a.latitude !== undefined ? a.latitude : a.lat;
      if (lon !== undefined && lat !== undefined) {
        a.xy = project(lon, lat, S);
      }
    });

    this.canvasEngine.setTopology(
      paths,
      this.districts,
      this.stations,
      this.airports,
      this.borderSamples
    );
  }

  async loadInitialTelemetry() {
    const [hourly, current, baseline, crossBorder, tbData] = await Promise.all([
      this.apiClient.getHourlyObservations(this.state.pollutant),
      this.apiClient.getCurrentObservations(this.state.pollutant),
      this.apiClient.loadBaselineData(),
      this.apiClient.getCrossBorderCities(),
      this.apiClient.getTransboundary(this.state.pollutant),
    ]);

    this.hourlyObservations = hourly;
    if (hourly && hourly.hours) {
      this.timestamps = hourly.hours;
      this.state.totalHours = hourly.hours.length;
      const scrubRange = document.getElementById('scrubRange');
      if (scrubRange) {
        scrubRange.max = String(Math.max(0, this.state.totalHours - 1));
      }
    }

    if (baseline) {
      this.baselineData = baseline;
      this.tbgeo = baseline.tbgeo;
      this.airports = baseline.airports || [];
      this.borderSamples = (baseline.tbgeo && baseline.tbgeo.samples) || [];
      this.recompilePaths();
    }

    // Refresh UI with initial hour
    this.refreshHourData(this.state.currentHour);
    this.ui.renderLahoreStationsTable(this.stations, this.state.currentHour);
    if (crossBorder) this.ui.renderCrossBorderTable(crossBorder);
    if (tbData) this.ui.renderTransboundaryKpis(tbData);

    // Load initial CPF polar rose for selected district
    this.updateCPF();

    // Render Heatmap Matrix
    if (this.hourlyObservations) {
      this.ui.renderHeatmapMatrix(this.hourlyObservations, this.state.currentHour);
    }
  }

  async updateCPF() {
    const cpfData = await this.apiClient.getCPFRose(this.state.selectedDistrict, this.state.pollutant);
    const roseCanvas = document.getElementById('roseCanvas');
    if (roseCanvas && cpfData) {
      this.ui.drawCPFPolarRose(roseCanvas, cpfData);
    }
  }

  // =========================================================================
  // ANIMATION LOOP & TEMPORAL INTERPOLATION (60 FPS)
  // =========================================================================

  animationLoop(timestamp) {
    const dt = Math.min(0.1, (timestamp - this.lastFrameTime) / 1000.0);
    this.lastFrameTime = timestamp;

    if (this.state.isPlaying) {
      // Advance continuous fractional position
      this.state.currentHour = (this.state.currentHour + dt * this.state.playbackSpeed) % this.state.totalHours;
    }

    // Evaluate interpolated data slice
    const interpolated = this.evaluateInterpolatedSlice(this.state.currentHour);

    // Render Canvas Layers 0-4
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

    // Throttle UI DOM updates to 10 Hz (every 100ms) to eliminate DOM thrashing
    if (timestamp - this.lastUiUpdateTime > 100) {
      this.lastUiUpdateTime = timestamp;
      this.updateThrottledUI(interpolated);
    }

    requestAnimationFrame((t) => this.animationLoop(t));
  }

  evaluateInterpolatedSlice(fp) {
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
          const S = this.canvasEngine ? this.canvasEngine.S : 1.0;
          const px = s.xy ? s.xy[0] : project(s.longitude || s.lon || 0, s.latitude || s.lat || 0, S)[0];
          const py = s.xy ? s.xy[1] : project(s.longitude || s.lon || 0, s.latitude || s.lat || 0, S)[1];
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
  }

  updateThrottledUI(slice) {
    const curHourIdx = Math.floor(this.state.currentHour);
    const tsStr = this.timestamps[curHourIdx] || '';

    // Update HUD & Clock
    this.ui.updateClockAndHUD(this.state.currentHour, tsStr, this.state.pollutant);

    // Compute Provincial Summary
    const values = Object.values(slice.districtReadings).filter(v => v !== null && !isNaN(v));
    const mean = values.length ? values.reduce((a, b) => a + b, 0) / values.length : 0;
    const spec = STATUTORY_LIMITS[this.state.pollutant] || STATUTORY_LIMITS['PM2.5'];
    const peqs = spec.ref || 100;
    const exceed = values.filter(v => v > peqs).length;

    let peakDist = '–';
    let peakVal = 0;
    for (const [d, v] of Object.entries(slice.districtReadings)) {
      if (v !== null && v > peakVal) {
        peakVal = v;
        peakDist = d;
      }
    }

    const summary = {
      mean_aqi: mean,
      exceedance_peqs_count: exceed,
      total_districts: 41,
      peak_district: peakDist,
      peak_aqi: peakVal,
    };

    this.ui.updateProvincialSummary(summary, this.state.pollutant);

    // Update Sparkline
    if (this.hourlyObservations && this.hourlyObservations.districts) {
      const selectedSeries = this.hourlyObservations.districts[this.state.selectedDistrict]?.concentrations || [];
      const sparkCanvas = document.getElementById('sparklineCanvas');
      this.ui.drawSparkline(sparkCanvas, selectedSeries, this.state.currentHour, peqs);
    }

    // Update Airport Weather
    this.ui.renderAirportWeatherTable(this.airports);

    // Update Ranked Districts
    this.ui.renderDistrictRankedList(slice.districtReadings, this.state.pollutant, this.state.selectedDistrict);

    // Update Selected District Telemetry Drawer
    const selReadings = {
      current: slice.districtReadings[this.state.selectedDistrict],
      AQI: slice.districtReadings[this.state.selectedDistrict],
    };
    this.ui.renderSelectedDistrictTelemetry(this.state.selectedDistrict, selReadings, this.state.pollutant);

    // Update Lahore Network Focus Live Table
    this.updateLahoreTable(Math.min(this.state.totalHours - 1, Math.round(this.state.currentHour)));
  }

  // =========================================================================
  // USER EVENT HANDLERS
  // =========================================================================

  togglePlay() {
    this.state.isPlaying = !this.state.isPlaying;
    const txt = this.state.isPlaying ? 'Pause' : 'Play';
    const playBtn = document.getElementById('playBtn');
    if (playBtn) playBtn.textContent = txt;
    const gridPlayBtn = document.getElementById('gridPlayBtn');
    if (gridPlayBtn) gridPlayBtn.textContent = txt;
  }

  seekHour(hour) {
    this.state.isLiveNowcast = false;
    this.ui.updateLiveModeBadge(false);
    this.state.currentHour = Math.max(0, Math.min(this.state.totalHours - 1, hour));
    this.refreshHourData(this.state.currentHour);
  }

  async toggleLiveNowcast() {
    this.state.isLiveNowcast = !this.state.isLiveNowcast;
    this.ui.updateLiveModeBadge(this.state.isLiveNowcast);
    if (this.state.isLiveNowcast) {
      await this.apiClient.setStreamMode('live');
      this.state.currentHour = Math.max(0, this.state.totalHours - 1);
      await this.apiClient.triggerTick('live');
      await this.refreshLiveTelemetry();
    } else {
      await this.apiClient.setStreamMode('simulation');
    }
  }

  async triggerPipelineTick() {
    const mode = this.state.isLiveNowcast ? 'live' : 'simulation';
    console.log(`Manually advancing pipeline tick (mode: ${mode})...`);
    const res = await this.apiClient.triggerTick(mode);
    if (res && res.status === 'success') {
      console.log('Pipeline tick advance executed:', res);
      await this.refreshLiveTelemetry();
    }
  }

  async refreshLiveTelemetry() {
    const [hourly, current, crossBorder, tbData] = await Promise.all([
      this.apiClient.getHourlyObservations(this.state.pollutant),
      this.apiClient.getCurrentObservations(this.state.pollutant),
      this.apiClient.getCrossBorderCities(),
      this.apiClient.getTransboundary(this.state.pollutant),
    ]);

    if (hourly && hourly.hours) {
      this.hourlyObservations = hourly;
      this.timestamps = hourly.hours;
      this.state.totalHours = hourly.hours.length;
      const scrubRange = document.getElementById('scrubRange');
      if (scrubRange) {
        scrubRange.max = String(Math.max(0, this.state.totalHours - 1));
      }
    }

    if (this.state.isLiveNowcast) {
      this.state.currentHour = Math.max(0, this.state.totalHours - 1);
    }

    this.refreshHourData(this.state.currentHour);
    this.ui.renderLahoreStationsTable(this.stations, this.state.currentHour);
    if (crossBorder) this.ui.renderCrossBorderTable(crossBorder);
    if (tbData) this.ui.renderTransboundaryKpis(tbData);

    if (this.state.activeView === 'heatmap' && this.hourlyObservations) {
      this.ui.renderHeatmapMatrix(this.hourlyObservations, this.state.currentHour);
    }
  }

  setSpeed(speed) {
    this.state.playbackSpeed = speed;
  }

  setDisplayMode(mode) {
    this.state.displayMode = mode;
  }

  setTransportLinksVisible(visible) {
    this.state.showTransportLinks = visible;
  }

  setRegionalWindsVisible(visible) {
    this.state.showRegionalWinds = visible;
  }

  selectDistrict(districtName) {
    if (this.state.selectedDistrict === districtName) return;
    this.state.selectedDistrict = districtName;
    const dropdown = document.getElementById('districtSelectDropdown');
    if (dropdown && dropdown.value !== districtName) dropdown.value = districtName;

    this.updateCPF();
    this.refreshHourData(this.state.currentHour);
  }

  setupMapInteraction(canvas) {
    if (!canvas) return;

    let isDragging = false;
    let startX = 0;
    let startY = 0;
    let lastX = 0;
    let lastY = 0;
    let totalMoved = 0;

    // 1. Wheel Zoom centered smoothly at mouse cursor
    canvas.addEventListener('wheel', (e) => {
      e.preventDefault();
      if (!this.canvasEngine) return;

      const rect = canvas.getBoundingClientRect();
      const mouseX = e.clientX - rect.left;
      const mouseY = e.clientY - rect.top;

      // Smooth zoom factor: 1.15x per notch
      const factor = e.deltaY < 0 ? 1.15 : (1.0 / 1.15);
      const targetZoom = this.canvasEngine.zoom * factor;
      this.canvasEngine.setZoom(targetZoom, mouseX, mouseY);

      canvas.style.cursor = this.canvasEngine.zoom > 1.05 ? 'grab' : 'crosshair';
    }, { passive: false });

    // 2. Mouse Drag (Pan) & Click (District Selection)
    canvas.addEventListener('mousedown', (e) => {
      if (e.button !== 0) return; // Left mouse button only
      isDragging = true;
      startX = e.clientX;
      startY = e.clientY;
      lastX = e.clientX;
      lastY = e.clientY;
      totalMoved = 0;

      if (this.canvasEngine && this.canvasEngine.zoom > 1.05) {
        canvas.style.cursor = 'grabbing';
      }
    });

    window.addEventListener('mousemove', (e) => {
      if (!isDragging || !this.canvasEngine) return;
      const dx = e.clientX - lastX;
      const dy = e.clientY - lastY;
      lastX = e.clientX;
      lastY = e.clientY;
      totalMoved += Math.hypot(dx, dy);

      if (totalMoved > 3) {
        this.canvasEngine.panBy(dx, dy);
        canvas.style.cursor = 'grabbing';
      }
    });

    window.addEventListener('mouseup', (e) => {
      if (!isDragging) return;
      isDragging = false;

      if (this.canvasEngine) {
        canvas.style.cursor = this.canvasEngine.zoom > 1.05 ? 'grab' : 'crosshair';
      }

      // If mouse barely moved (< 5px), treat as a click to select district
      if (totalMoved < 5 && this.canvasEngine) {
        const rect = canvas.getBoundingClientRect();
        const screenX = e.clientX - rect.left;
        const screenY = e.clientY - rect.top;
        const clickedDistrict = this.canvasEngine.hitTestDistrict(screenX, screenY);
        if (clickedDistrict) {
          this.selectDistrict(clickedDistrict);
        }
      }
    });

    // 3. Touch support (pinch to zoom, one-finger pan)
    let initialTouchDist = 0;
    let initialTouchZoom = 1.0;
    let lastTouchX = 0;
    let lastTouchY = 0;

    canvas.addEventListener('touchstart', (e) => {
      if (!this.canvasEngine) return;
      if (e.touches.length === 1) {
        isDragging = true;
        startX = e.touches[0].clientX;
        startY = e.touches[0].clientY;
        lastTouchX = startX;
        lastTouchY = startY;
        totalMoved = 0;
      } else if (e.touches.length === 2) {
        isDragging = false;
        initialTouchDist = Math.hypot(
          e.touches[0].clientX - e.touches[1].clientX,
          e.touches[0].clientY - e.touches[1].clientY
        );
        initialTouchZoom = this.canvasEngine.zoom;
      }
    }, { passive: true });

    canvas.addEventListener('touchmove', (e) => {
      if (!this.canvasEngine) return;
      if (e.touches.length === 1 && isDragging) {
        const cx = e.touches[0].clientX;
        const cy = e.touches[0].clientY;
        const dx = cx - lastTouchX;
        const dy = cy - lastTouchY;
        lastTouchX = cx;
        lastTouchY = cy;
        totalMoved += Math.hypot(dx, dy);
        if (totalMoved > 3) {
          this.canvasEngine.panBy(dx, dy);
        }
      } else if (e.touches.length === 2 && initialTouchDist > 0) {
        const curDist = Math.hypot(
          e.touches[0].clientX - e.touches[1].clientX,
          e.touches[0].clientY - e.touches[1].clientY
        );
        const rect = canvas.getBoundingClientRect();
        const midX = (e.touches[0].clientX + e.touches[1].clientX) / 2 - rect.left;
        const midY = (e.touches[0].clientY + e.touches[1].clientY) / 2 - rect.top;
        const factor = curDist / initialTouchDist;
        this.canvasEngine.setZoom(initialTouchZoom * factor, midX, midY);
      }
    }, { passive: true });

    canvas.addEventListener('touchend', (e) => {
      if (isDragging && totalMoved < 5 && e.changedTouches.length === 1 && this.canvasEngine) {
        const rect = canvas.getBoundingClientRect();
        const screenX = e.changedTouches[0].clientX - rect.left;
        const screenY = e.changedTouches[0].clientY - rect.top;
        const clickedDistrict = this.canvasEngine.hitTestDistrict(screenX, screenY);
        if (clickedDistrict) {
          this.selectDistrict(clickedDistrict);
        }
      }
      if (e.touches.length === 0) {
        isDragging = false;
        initialTouchDist = 0;
      }
    }, { passive: true });
  }

  async selectPollutant(pollutantKey) {
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
  }

  onThemeChanged(theme) {
    this.state.theme = theme;
    if (this.canvasEngine) {
      this.canvasEngine.theme = theme;
      this.canvasEngine.readThemeTokens();
    }
  }

  onViewSwitched(viewName) {
    this.state.activeView = viewName;
    if (viewName === 'grid') {
      this.sizeMinis();
      this.drawMinis();
    } else if (viewName === 'heatmap' && this.hourlyObservations) {
      this.ui.renderHeatmapMatrix(this.hourlyObservations, this.state.currentHour);
    } else if (viewName === 'lahore') {
      this.sizeLahore();
      this.drawLahore();
    }
  }

  onLiveHourlyUpdate(update) {
    console.log('SSE Live Telemetry Packet Received:', update);
    this.ui.updateLiveStatus('live');
    this.refreshLiveTelemetry();
  }

  onCsvIngested(result) {
    if (!result || result.valid_rows === 0 || result.status === 'failed') {
      console.warn('Ignoring CSV ingestion with 0 valid records:', result);
      return;
    }
    console.log('CSV Ingestion Complete:', result);
    this.ui.updateLiveStatus('user_csv');
  }

  // =========================================================================
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
      const S = this.canvasEngine ? this.canvasEngine.S : 1.0;
      const px = s.xy ? s.xy[0] : project(s.longitude || s.lon || 0, s.latitude || s.lat || 0, S)[0];
      const py = s.xy ? s.xy[1] : project(s.longitude || s.lon || 0, s.latitude || s.lat || 0, S)[1];
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

    // 3x3 Synchronized Grid: All 9 monitored species
    const CMP = ['AQI', 'PM2.5', 'PM10', 'NO2', 'SO2', 'CO', 'O3', 'NO', 'NOX'];

    const SPECIES_NAMES = {
      AQI: 'Air Quality Index',
      'PM2.5': 'Fine Particulate',
      PM10: 'Respirable Dust',
      NO2: 'Nitrogen Dioxide',
      SO2: 'Sulfur Dioxide',
      CO: 'Carbon Monoxide',
      O3: 'Surface Ozone',
      NO: 'Nitric Oxide',
      NOX: 'Reactive Nitrogen',
    };

    const SPECIES_LIMITS = {
      AQI: 'PEQS: 200 Index',
      'PM2.5': 'PEQS 24h: 35 µg/m³',
      PM10: 'PEQS 24h: 150 µg/m³',
      NO2: 'PEQS 24h: 80 µg/m³',
      SO2: 'PEQS 24h: 120 µg/m³',
      CO: 'PEQS 8h: 5 mg/m³',
      O3: 'PEQS 1h: 130 µg/m³',
      NO: 'PEQS 24h: 40 µg/m³',
      NOX: 'Ref: 100 µg/m³',
    };

    const SPECIES_MAX = {
      AQI: '500+',
      'PM2.5': '350+',
      PM10: '550+',
      NO2: '580+',
      SO2: '1600+',
      CO: '40+',
      O3: '550+',
      NO: '400+',
      NOX: '600+',
    };

    container.innerHTML = CMP.map(p => {
      const Q = this.baselineData.pol[p];
      if (!Q) return '';
      const pClean = p.replace('.', '');
      const barBg = barFor(Q);
      const unitStr = Q.unit || (isAQI(Q) ? 'AQI' : 'µg/m³');

      return `
        <figure class="mini" id="mini_card_${pClean}">
          <div class="mini-card-header">
            <div class="mini-card-title-row">
              <div class="mini-spec-group">
                <span class="mini-species-badge">${POLNAME[p] || p}</span>
                <span class="mini-species-name">${SPECIES_NAMES[p] || ''}</span>
              </div>
              <div class="mini-mean-display">
                <span class="mini-mean-val tabular-nums" id="mval_${pClean}">–</span>
                <span class="mini-unit-tag">${unitStr}</span>
                <span class="mini-status-chip" id="mchip_${pClean}">–</span>
              </div>
            </div>
            <div class="mini-card-sub-row">
              <span class="mini-peqs-badge">${SPECIES_LIMITS[p] || ''}</span>
              <span class="mini-tally-text tabular-nums" id="mtally_${pClean}">–</span>
            </div>
          </div>
          <canvas id="mc_${pClean}" class="mini-canvas" aria-label="${POLNAME[p] || p} map"></canvas>
          <div class="mleg">
            <div class="mbar" style="background:${barBg};"></div>
            <div class="mleg-scale tabular-nums">
              <span class="mleg-min">0</span>
              <span class="mleg-ref">${SPECIES_LIMITS[p] || ''}</span>
              <span class="mleg-max">${SPECIES_MAX[p] || 'max'}</span>
            </div>
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

  computeDistrictBounds() {
    if (!this.districts || this.districts.length === 0 || !this.canvasEngine) return;
    if (this.districtBounds && this.districtBounds.size >= this.districts.length) return;
    this.districtBounds = new Map();
    const S = this.canvasEngine.S || 1.0;
    const pb_w = this.PB ? this.PB.w : 5.314;
    const pb_h = this.PB ? this.PB.h : 6.48;
    const aspect = pb_w / pb_h;

    for (const d of this.districts) {
      const name = d.name || d.district;
      const coords = [];
      const extract = (p) => {
        if (Array.isArray(p)) {
          if (p.length >= 2 && typeof p[0] === 'number' && typeof p[1] === 'number') {
            coords.push(p);
          } else {
            for (const sub of p) extract(sub);
          }
        }
      };
      extract(d.polys || d.boundary || []);
      if (coords.length === 0) continue;

      let minX = 1e9, maxX = -1e9, minY = 1e9, maxY = -1e9;
      for (const [lon, lat] of coords) {
        const [x, y] = project(lon, lat, S);
        if (x < minX) minX = x;
        if (x > maxX) maxX = x;
        if (y < minY) minY = y;
        if (y > maxY) maxY = y;
      }

      const dw = maxX - minX;
      const dh = maxY - minY;
      const cx = (minX + maxX) / 2;
      const cy = (minY + maxY) / 2;

      // Contextual padding factor: district fills comfortable center with neighboring boundaries
      const padFactor = 1.65;
      let vw = Math.max(dw * padFactor, 0.95);
      let vh = vw / aspect;
      if (dh * padFactor > vh) {
        vh = dh * padFactor;
        vw = vh * aspect;
      }

      this.districtBounds.set(name, {
        x0: cx - vw / 2,
        y0: cy - vh / 2,
        w: vw,
        h: vh,
        cx,
        cy,
        dw,
        dh,
      });
    }
  }

  getGridActiveViewport() {
    if (!this.PB) return { x0: 0, y0: 0, w: 1, h: 1 };
    if (!this.gridCurrentPB) {
      this.gridCurrentPB = { ...this.PB };
      this.gridTargetPB = { ...this.PB };
    }

    let target = this.PB;
    if (this.state.gridZoomDistrict && this.districtBounds && this.districtBounds.has(this.state.gridZoomDistrict)) {
      target = this.districtBounds.get(this.state.gridZoomDistrict);
    }
    this.gridTargetPB = target;

    // Smooth exponential decay lerp for fluid camera motion across 60 FPS
    const lerpSpeed = 0.22;
    this.gridCurrentPB.x0 += (target.x0 - this.gridCurrentPB.x0) * lerpSpeed;
    this.gridCurrentPB.y0 += (target.y0 - this.gridCurrentPB.y0) * lerpSpeed;
    this.gridCurrentPB.w += (target.w - this.gridCurrentPB.w) * lerpSpeed;
    this.gridCurrentPB.h += (target.h - this.gridCurrentPB.h) * lerpSpeed;

    if (Math.abs(target.x0 - this.gridCurrentPB.x0) < 0.0005 &&
        Math.abs(target.y0 - this.gridCurrentPB.y0) < 0.0005 &&
        Math.abs(target.w - this.gridCurrentPB.w) < 0.0005 &&
        Math.abs(target.h - this.gridCurrentPB.h) < 0.0005) {
      this.gridCurrentPB.x0 = target.x0;
      this.gridCurrentPB.y0 = target.y0;
      this.gridCurrentPB.w = target.w;
      this.gridCurrentPB.h = target.h;
    }

    return this.gridCurrentPB;
  }

  hitTestMiniDistrict(wx, wy) {
    if (!this.canvasEngine || !this.canvasEngine.paths || !this.canvasEngine.paths.admPaths) return null;
    const hitCtx = this.canvasEngine.hitCtx;
    // 1. Precise boundary path hit test
    for (const adm of this.canvasEngine.paths.admPaths) {
      if (hitCtx && hitCtx.isPointInPath(adm.path, wx, wy)) {
        return adm.name;
      }
    }
    // 2. Proximity fallback to district centroid
    let closestName = null;
    let closestDist = 0.35;
    for (const d of this.districts) {
      if (!d.xy) continue;
      const dx = wx - d.xy[0];
      const dy = wy - d.xy[1];
      const dist = Math.hypot(dx, dy);
      if (dist < closestDist) {
        closestDist = dist;
        closestName = d.name || d.district;
      }
    }
    return closestName;
  }

  setGridZoomDistrict(districtName) {
    if (this.state.gridZoomDistrict === districtName) return;
    this.state.gridZoomDistrict = districtName;
    if (districtName) {
      this.state.selectedDistrict = districtName;
      const dropdown = document.getElementById('districtSelectDropdown');
      if (dropdown && dropdown.value !== districtName) dropdown.value = districtName;
      this.updateCPF();
      this.refreshHourData(this.state.currentHour);
    }

    // Update Grid Zoom Banner in UI toolbar
    const banner = document.getElementById('gridZoomBanner');
    const nameEl = document.getElementById('gridZoomDistrictName');
    if (banner && nameEl) {
      if (districtName) {
        banner.style.display = 'inline-flex';
        nameEl.textContent = districtName;
      } else {
        banner.style.display = 'none';
      }
    }
  }

  toggleGridDistrictZoom(districtName) {
    if (this.state.gridZoomDistrict === districtName) {
      this.setGridZoomDistrict(null);
    } else {
      this.setGridZoomDistrict(districtName);
    }
  }

  sizeMinis() {
    if (!this.canvasEngine || !this.minis || this.minis.length === 0) return;
    const S = this.canvasEngine.S || 1.0;
    const p0 = project(69.25, 34.1, S);
    const p1 = project(75.45, 27.62, S);
    const x0 = p0[0], y0 = p0[1], x1 = p1[0], y1 = p1[1];
    this.PB = { x0, y0, w: x1 - x0, h: y1 - y0 };

    this.computeDistrictBounds();

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

      // District click on mini map: zoom into district and show name!
      m.cv.onclick = (e) => {
        const b = m.cv.getBoundingClientRect();
        const activePB = this.getGridActiveViewport();
        const k = m.W / activePB.w;
        const x = (e.clientX - b.left) / k + activePB.x0;
        const y = (e.clientY - b.top) / k + activePB.y0;
        const clickedDistrict = this.hitTestMiniDistrict(x, y);
        if (clickedDistrict) {
          this.toggleGridDistrictZoom(clickedDistrict);
        } else if (this.state.gridZoomDistrict) {
          this.setGridZoomDistrict(null);
        }
      };

      // Hover feedback: cursor pointer & tooltip
      m.cv.onmousemove = (e) => {
        const b = m.cv.getBoundingClientRect();
        const activePB = this.getGridActiveViewport();
        const k = m.W / activePB.w;
        const x = (e.clientX - b.left) / k + activePB.x0;
        const y = (e.clientY - b.top) / k + activePB.y0;
        const hoverDistrict = this.hitTestMiniDistrict(x, y);
        if (hoverDistrict) {
          m.cv.style.cursor = 'pointer';
          m.cv.title = this.state.gridZoomDistrict === hoverDistrict
            ? `Click to zoom out (${hoverDistrict})`
            : `Click to zoom into ${hoverDistrict}`;
        } else {
          m.cv.style.cursor = this.state.gridZoomDistrict ? 'zoom-out' : 'default';
          m.cv.title = this.state.gridZoomDistrict ? 'Click outside to reset zoom' : '';
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

    const activePB = this.getGridActiveViewport();
    const isZoomed = !!this.state.gridZoomDistrict;
    const activeDistName = this.state.gridZoomDistrict || this.state.selectedDistrict;

    for (const m of this.minis) {
      if (!m.cv || !m.g) continue;
      const g = m.g;
      const k = m.W / activePB.w;
      const Q = m.Q;
      if (!Q) continue;
      const fm = (v) => v == null ? '–' : (m.p === 'CO' ? (+v).toFixed(1) : Math.round(v));

      g.save();
      g.setTransform(m.dp * k, 0, 0, m.dp * k, -activePB.x0 * m.dp * k, -activePB.y0 * m.dp * k);

      // Background sea & land
      g.fillStyle = this.canvasEngine.tokens.geoSea;
      g.fillRect(activePB.x0, activePB.y0, activePB.w, activePB.h);

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
        const key = Math.round(fp * 4) + '|' + Math.round(this.PB.w);
        if (m.fk !== key) {
          m.fk = key;
          const baseScale = m.W / this.PB.w;
          this.renderMiniField(m.fc, this.PB.x0, this.PB.y0, m.W, m.H, baseScale, 4, Q, m.r, fp);
        }
        g.save();
        g.clip(paths.pjPath);
        g.imageSmoothingEnabled = true;
        g.drawImage(m.fc, this.PB.x0, this.PB.y0, this.PB.w, this.PB.h);
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

      // District boundaries
      g.strokeStyle = this.canvasEngine.tokens.inkPrimary;
      g.globalAlpha = 0.35;
      g.lineWidth = (isZoomed ? 1.0 : 0.6) / k;
      for (const adm of paths.admPaths) {
        g.stroke(adm.path);
      }
      g.globalAlpha = 1.0;

      // Highlight selected/zoomed district boundary with vibrant cyan glow
      const selAdm = paths.admPaths.find(a => a.name === activeDistName);
      if (selAdm) {
        g.save();
        g.lineWidth = (isZoomed ? 3.4 : 2.0) / k;
        g.strokeStyle = '#5fc4c4';
        g.shadowColor = 'rgba(95, 196, 196, 0.9)';
        g.shadowBlur = 8 / k;
        g.stroke(selAdm.path);
        g.restore();
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

      // Switch to pixel coordinates for text, arrows & callout badges
      g.setTransform(m.dp, 0, 0, m.dp, 0, 0);
      const Px = (x, y) => [(x - activePB.x0) * k, (y - activePB.y0) * k];

      // Transport links (refined vector arcs)
      if (this.state.showTransportLinks && !isAQI(Q) && Q.frames && Q.frames[fr] && Q.frames[fr].l) {
        const ls = Q.frames[fr].l.slice()
          .sort((a, b) => b[2] - a[2])
          .filter(l => l[2] >= (m.maxf || 1) * 0.12)
          .slice(0, 5);

        for (const [a, b, fl] of ls) {
          const distA = this.districts.find(d => (d.name || d.district) === a);
          const distB = this.districts.find(d => (d.name || d.district) === b);
          if (!distA || !distB || !distA.xy || !distB.xy) continue;

          const [x0, y0] = Px(...distA.xy);
          const [x1, y1] = Px(...distB.xy);
          if ((x0 < -20 && x1 < -20) || (x0 > m.W + 20 && x1 > m.W + 20)) continue;
          const dx = x1 - x0, dy = y1 - y0;
          const L = Math.hypot(dx, dy);
          if (L < 8) continue;
          const ux = dx / L, uy = dy / L;
          const sx = x0 + ux * 4, sy = y0 + uy * 4;
          const ex = x1 - ux * 5, ey = y1 - uy * 5;

          const cx = (sx + ex) / 2 - uy * L * 0.12;
          const cy = (sy + ey) / 2 + ux * L * 0.12;

          g.save();
          g.strokeStyle = 'rgba(95, 196, 196, 0.75)';
          g.lineWidth = isZoomed ? 1.8 : 1.4;
          g.lineCap = 'round';
          g.beginPath();
          g.moveTo(sx, sy);
          g.quadraticCurveTo(cx, cy, ex, ey);
          g.stroke();

          const angle = Math.atan2(ey - cy, ex - cx);
          const headLen = isZoomed ? 5.5 : 4;
          g.fillStyle = 'rgba(95, 196, 196, 0.9)';
          g.beginPath();
          g.moveTo(ex, ey);
          g.lineTo(ex - headLen * Math.cos(angle - 0.4), ey - headLen * Math.sin(angle - 0.4));
          g.lineTo(ex - headLen * Math.cos(angle + 0.4), ey - headLen * Math.sin(angle + 0.4));
          g.closePath();
          g.fill();
          g.restore();
        }
      }

      // Station points in surface mode
      if (this.state.displayMode === 'surface') {
        const pts = this.getStationPointsForPollutant(Q, fp);
        for (const p of pts) {
          const [x, y] = Px(p.x, p.y);
          if (x < -10 || x > m.W + 10 || y < -10 || y > m.H + 10) continue;
          g.beginPath();
          g.arc(x, y, isZoomed ? 3.0 : 1.8, 0, Math.PI * 2);
          g.fillStyle = col(p.v, 0.95, m.r);
          g.fill();
          g.strokeStyle = 'rgba(255, 255, 255, 0.45)';
          g.lineWidth = 0.6;
          g.stroke();
        }
      } else if (!isZoomed) {
        // Full province choropleth district numbers
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
        }).sort((a, b) => (b.n === activeDistName) - (a.n === activeDistName) || (a.est - b.est));

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
          g.lineWidth = 2.4;
          g.strokeStyle = 'rgba(15, 23, 22, 0.85)';
          g.fillStyle = '#e3ece9';
          g.strokeText(s, best[0], best[1] + 2);
          g.fillText(s, best[0], best[1] + 2);
        }
        g.textAlign = 'left';
      }

      // DISTRICT NAME & VALUE PROMINENT CALLOUT (When district is selected / zoomed)
      if (activeDistName) {
        const focusDist = this.districts.find(d => (d.name || d.district) === activeDistName);
        if (focusDist && focusDist.xy) {
          const [dx, dy] = Px(...focusDist.xy);
          const distVal = this.mval(Q, activeDistName, fp);
          const valStr = distVal == null ? '–' : (m.p === 'CO' ? (+distVal).toFixed(1) : Math.round(distVal));
          const unitStr = Q.unit || (isAQI(Q) ? 'AQI' : 'µg/m³');
          const colBadge = col(distVal, 1.0, m.r);

          g.save();
          g.font = `700 12px ${this.canvasEngine.tokens.fontMono}`;
          const nameW = g.measureText(activeDistName.toUpperCase()).width;
          g.font = `600 11px ${this.canvasEngine.tokens.fontMono}`;
          const valW = g.measureText(valStr + ' ' + unitStr).width;
          const badgeW = nameW + valW + 36;
          const badgeH = 26;

          let bx = dx - badgeW / 2;
          let by = dy - badgeH / 2;
          bx = Math.max(8, Math.min(m.W - badgeW - 8, bx));
          by = Math.max(8, Math.min(m.H - badgeH - 8, by));

          // Glass pill background
          g.fillStyle = 'rgba(10, 18, 16, 0.92)';
          g.strokeStyle = '#5fc4c4';
          g.lineWidth = 1.5;
          g.shadowColor = 'rgba(0, 0, 0, 0.6)';
          g.shadowBlur = 6;
          if (g.roundRect) {
            g.beginPath();
            g.roundRect(bx, by, badgeW, badgeH, 4);
            g.fill();
            g.stroke();
          } else {
            g.fillRect(bx, by, badgeW, badgeH);
            g.strokeRect(bx, by, badgeW, badgeH);
          }
          g.shadowBlur = 0;

          // Severity dot
          g.fillStyle = colBadge;
          g.beginPath();
          g.arc(bx + 11, by + badgeH / 2, 4, 0, Math.PI * 2);
          g.fill();
          g.strokeStyle = '#ffffff';
          g.lineWidth = 0.8;
          g.stroke();

          // District Name
          g.fillStyle = '#ffffff';
          g.font = `700 12px ${this.canvasEngine.tokens.fontMono}`;
          g.textBaseline = 'middle';
          g.fillText(activeDistName.toUpperCase(), bx + 22, by + badgeH / 2);

          // Pollutant Reading
          g.fillStyle = colBadge;
          g.font = `600 11px ${this.canvasEngine.tokens.fontMono}`;
          g.fillText(`${valStr} ${unitStr}`, bx + 22 + nameW + 8, by + badgeH / 2);
          g.restore();

          // If zoomed in: render surrounding visible neighboring district names for context
          if (isZoomed) {
            for (const nb of this.districts) {
              const nbName = nb.name || nb.district;
              if (nbName === activeDistName || !nb.xy) continue;
              const [nx, ny] = Px(...nb.xy);
              if (nx >= 25 && nx <= m.W - 25 && ny >= 18 && ny <= m.H - 18) {
                const nbVal = this.mval(Q, nbName, fp);
                if (nbVal != null) {
                  g.save();
                  g.font = `600 9.5px ${this.canvasEngine.tokens.fontMono}`;
                  g.textAlign = 'center';
                  g.textBaseline = 'middle';
                  const nbStr = `${nbName}: ${fm(nbVal)}`;
                  const nbW = g.measureText(nbStr).width;
                  g.fillStyle = 'rgba(12, 20, 18, 0.82)';
                  g.fillRect(nx - nbW / 2 - 4, ny - 7, nbW + 8, 14);
                  g.strokeStyle = 'rgba(255, 255, 255, 0.16)';
                  g.strokeRect(nx - nbW / 2 - 4, ny - 7, nbW + 8, 14);
                  g.fillStyle = '#b8c8c2';
                  g.fillText(nbStr, nx, ny);
                  g.restore();
                }
              }
            }
          }
        }
      }

      g.restore();

      // Update institutional card telemetry
      const pClean = m.p.replace('.', '');
      const valEl = document.getElementById('mval_' + pClean);
      const chipEl = document.getElementById('mchip_' + pClean);
      const tallyEl = document.getElementById('mtally_' + pClean);

      if (isZoomed && activeDistName) {
        // District focused mode: card displays the zoomed district's telemetry!
        const dVal = this.mval(Q, activeDistName, fp);
        const dStr = dVal == null ? '–' : (m.p === 'CO' ? (+dVal).toFixed(1) : Math.round(dVal));
        const unitStr = Q.unit || (isAQI(Q) ? 'AQI' : 'µg/m³');

        if (valEl) valEl.textContent = dStr;

        if (chipEl && dVal != null) {
          if (isAQI(Q)) {
            const cat = aqiCat(dVal);
            chipEl.textContent = cat[2].toUpperCase();
            chipEl.style.backgroundColor = `rgb(${cat[3].join(',')})`;
            chipEl.style.color = (cat[0] >= 201 || cat[0] === 0) ? '#ffffff' : '#000000';
          } else if (Q.ref) {
            const ratio = (dVal / Q.ref).toFixed(1);
            if (dVal > Q.ref) {
              chipEl.textContent = `${ratio}× PEQS`;
              chipEl.style.backgroundColor = ratio > 2.0 ? 'var(--pepc-hazardous)' : 'var(--pepc-unhealthy)';
              chipEl.style.color = '#ffffff';
            } else {
              chipEl.textContent = 'COMPLIANT';
              chipEl.style.backgroundColor = 'var(--pepc-good)';
              chipEl.style.color = '#000000';
            }
          }
        }

        if (tallyEl) {
          tallyEl.innerHTML = `<span style="color:var(--accent); font-weight:600;">📍 ${activeDistName}</span> · ${dStr} ${unitStr}`;
        }
      } else {
        // Provincial airshed baseline aggregates
        const mm = m.means[fr];
        const meanVal = mm != null ? (m.p === 'CO' ? mm.toFixed(1) : Math.round(mm)) : '–';
        if (valEl) valEl.textContent = meanVal;

        if (chipEl && mm != null) {
          if (isAQI(Q)) {
            const cat = aqiCat(mm);
            chipEl.textContent = cat[2].toUpperCase();
            chipEl.style.backgroundColor = `rgb(${cat[3].join(',')})`;
            chipEl.style.color = (cat[0] >= 201 || cat[0] === 0) ? '#ffffff' : '#000000';
          } else if (Q.ref) {
            const ratio = (mm / Q.ref).toFixed(1);
            if (mm > Q.ref) {
              chipEl.textContent = `${ratio}× PEQS`;
              chipEl.style.backgroundColor = ratio > 2.0 ? 'var(--pepc-hazardous)' : 'var(--pepc-unhealthy)';
              chipEl.style.color = '#ffffff';
            } else {
              chipEl.textContent = 'COMPLIANT';
              chipEl.style.backgroundColor = 'var(--pepc-good)';
              chipEl.style.color = '#000000';
            }
          } else {
            chipEl.textContent = 'MONITORED';
            chipEl.style.backgroundColor = 'var(--bg-panel-elevated)';
            chipEl.style.color = 'var(--ink-secondary)';
          }
        }

        if (tallyEl) {
          const overCount = this.districts
            ? this.districts
                .filter(d => !d.est)
                .map(d => Q.frames?.[fr]?.c?.[d.name || d.district])
                .filter(v => v != null && v > (Q.ref || 0)).length
            : 0;
          tallyEl.textContent = Q.ref 
            ? `${overCount} / 41 districts in exceedance`
            : 'Scale reference baseline';
        }
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
    this.lctx.setTransform(dp, 0, 0, dp, 0, 0);
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

    const ring = (path, r, proj) => {
      r.forEach((p, i) => {
        const [x, y] = proj(p[0], p[1]);
        if (i === 0) path.moveTo(x, y);
        else path.lineTo(x, y);
      });
      path.closePath();
    };

    g.save();

    // 1. Clear & Background
    g.fillStyle = this.canvasEngine.tokens.geoSea || '#0d1512';
    g.fillRect(0, 0, LW, LH);

    // 2. India territory
    if (this.geoBoundaries && this.geoBoundaries.IND) {
      const indPath = new Path2D();
      for (const poly of Object.values(this.geoBoundaries.IND)) {
        for (const r of poly) {
          ring(indPath, r, Qproj);
        }
      }
      g.fillStyle = this.canvasEngine.tokens.geoIndia || '#15211c';
      g.fill(indPath);
      g.strokeStyle = this.canvasEngine.tokens.borderSubtle || '#23332c';
      g.lineWidth = 1;
      g.stroke(indPath);
    }

    // 3. Punjab Districts (Lahore + bordering districts Kasur, Sheikhupura, Nankana Sahib)
    const polData = this.baselineData?.pol?.[this.state.pollutant];
    const rPol = refFor(polData);

    if (this.districts && this.districts.length > 0) {
      for (const d of this.districts) {
        const polys = d.polys || (d.boundary ? [d.boundary] : null);
        if (!polys) continue;

        const dName = d.name || d.district;
        const isLahore = dName === 'Lahore';
        const p = new Path2D();
        for (const po of polys) {
          for (const r of po) {
            ring(p, r, Qproj);
          }
        }

        if (isLahore) {
          // Fill Lahore with interpolated concentration choropleth
          const lahoreVal = polData?.frames?.[fi]?.c?.Lahore;
          g.fillStyle = lahoreVal != null ? col(lahoreVal, 0.45, rPol) : (this.canvasEngine.tokens.geoPunjab || '#1a2722');
          g.fill(p);
          // Highlight Lahore district boundary with prominent border
          g.strokeStyle = 'rgba(52, 211, 153, 0.7)';
          g.lineWidth = 1.8;
          g.stroke(p);
        } else {
          // Neighboring districts rendered in subtle background tone
          g.fillStyle = this.canvasEngine.tokens.geoPunjab || '#182420';
          g.fill(p);
          g.strokeStyle = 'rgba(255, 255, 255, 0.08)';
          g.lineWidth = 1.0;
          g.stroke(p);

          // Neighbor district name label
          const labelCoord = d.label || (d.centroid ? [d.centroid[0], d.centroid[1]] : [d.longitude, d.latitude]);
          if (labelCoord) {
            const [lx, ly] = Qproj(labelCoord[0], labelCoord[1]);
            if (lx > 20 && lx < LW - 20 && ly > 20 && ly < LH - 20) {
              g.fillStyle = 'rgba(255, 255, 255, 0.32)';
              g.font = `italic 600 11px ${this.canvasEngine.tokens.fontBody || 'sans-serif'}`;
              g.fillText(dName.toUpperCase(), lx - 20, ly);
            }
          }
        }
      }
    }

    // 4. International Border Line
    if (this.tbgeo && this.tbgeo.border) {
      g.save();
      g.strokeStyle = this.canvasEngine.tokens.geoBorder || '#e05344';
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

    // 5. India Region Label
    g.fillStyle = 'rgba(255, 255, 255, 0.38)';
    g.font = `700 15px ${this.canvasEngine.tokens.fontDisplay || 'sans-serif'}`;
    g.fillText('INDIA', LW - 65, LH * 0.55);

    // 6. Meteorological Wind Compass Widget (Bottom-Left)
    const wi = Math.min(this.state.totalHours - 1, Math.round(fp));
    const lahoreWind = this.baselineData?.wind?.[wi]?.Lahore;
    if (lahoreWind) {
      const [u, v] = lahoreWind;
      const ws = Math.hypot(u, v);
      const cx = 44, cy = LH - 44, rad = 24;

      g.save();
      // Circular dial backplate
      g.fillStyle = 'rgba(12, 20, 18, 0.88)';
      g.strokeStyle = 'rgba(255, 255, 255, 0.16)';
      g.lineWidth = 1;
      g.beginPath();
      g.arc(cx, cy, rad, 0, Math.PI * 2);
      g.fill();
      g.stroke();

      // Cardinal tick marks
      g.strokeStyle = 'rgba(255, 255, 255, 0.28)';
      g.lineWidth = 1;
      [0, Math.PI / 2, Math.PI, (3 * Math.PI) / 2].forEach(ang => {
        g.beginPath();
        g.moveTo(cx + Math.cos(ang) * (rad - 4), cy + Math.sin(ang) * (rad - 4));
        g.lineTo(cx + Math.cos(ang) * rad, cy + Math.sin(ang) * rad);
        g.stroke();
      });

      // 'N' indicator
      g.font = `600 8px ${this.canvasEngine.tokens.fontMono}`;
      g.fillStyle = 'rgba(255, 255, 255, 0.5)';
      g.textAlign = 'center';
      g.textBaseline = 'top';
      g.fillText('N', cx, cy - rad + 2);

      // Wind vector arrow
      if (ws > 0.05) {
        const ux = u / ws, uy = -v / ws, k = 15;
        g.strokeStyle = this.canvasEngine.tokens.accent || '#34d399';
        g.fillStyle = this.canvasEngine.tokens.accent || '#34d399';
        g.lineWidth = 2.2;
        g.beginPath();
        g.moveTo(cx - ux * 5, cy - uy * 5);
        g.lineTo(cx + ux * k, cy + uy * k);
        g.stroke();

        g.beginPath();
        g.moveTo(cx + ux * k, cy + uy * k);
        g.lineTo(cx + ux * k - ux * 6 - uy * 4, cy + uy * k - uy * 6 + ux * 4);
        g.lineTo(cx + ux * k - ux * 6 + uy * 4, cy + uy * k - uy * 6 - ux * 4);
        g.closePath();
        g.fill();
      }

      // Wind text readout
      g.textAlign = 'left';
      g.textBaseline = 'alphabetic';
      g.font = `600 11px ${this.canvasEngine.tokens.fontMono}`;
      g.fillStyle = '#e6ece9';
      g.fillText(`${ws.toFixed(1)} m/s`, cx + rad + 8, cy - 2);

      const deg = Math.round((Math.atan2(-u, -v) * 180 / Math.PI + 360) % 360);
      g.font = `10px ${this.canvasEngine.tokens.fontMono}`;
      g.fillStyle = 'rgba(255, 255, 255, 0.5)';
      g.fillText(`Lahore · ${deg}°`, cx + rad + 8, cy + 12);
      g.restore();
    }

    // 7. Lahore Real AQMS Stations (Exclude dummy 'Lahore' and airport METAR)
    const lahoreStations = this.stations.filter(s => {
      const d = (s.district || s.d || '').toLowerCase();
      const isLhr = d === 'lahore' || (s.name && s.name.toLowerCase().includes('lhr'));
      const isMetar = s.station_type === 'airport_metar' || s.name === 'Lahore';
      return isLhr && !isMetar;
    });

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

    // Draw station glyphs with glow
    for (const o of pts) {
      const [x, y] = o.xy;
      const fillCol = o.v == null ? this.canvasEngine.tokens.bgPanel : col(o.v, 1.0, rPol);

      g.save();
      if (o.v != null) {
        g.shadowColor = col(o.v, 0.6, rPol);
        g.shadowBlur = 6;
      }

      g.beginPath();
      if (o.s.mobile) {
        // Equilateral triangle for Mobile AQMS
        g.moveTo(x, y - 8);
        g.lineTo(x + 7, y + 5);
        g.lineTo(x - 7, y + 5);
        g.closePath();
      } else {
        // Centered square for Fixed AQMS
        g.rect(x - 6, y - 6, 12, 12);
      }
      g.fillStyle = fillCol;
      g.fill();
      g.strokeStyle = '#ffffff';
      g.lineWidth = 1.4;
      g.stroke();
      g.restore();
    }

    // 8. Collision-Free Dark Glass Badges with Smart Leader Lines
    const cleanStationName = (name) => {
      return name
        .replace(/-LHR$/, '')
        .replace(/ LHR - Mobile \d| - Mobile \d/, '')
        .replace('Govt. Teaching Hospital ', 'GTH ')
        .replace('BHU Jandiala Kalsan', 'Jandiala Kalsan')
        .replace('Gulberg III Lahore', 'Gulberg III')
        .replace('Kahna Nau Hospital', 'Kahna Nau')
        .replace('Punjab University', 'Punjab Univ')
        .trim();
    };

    const placed = [];
    g.font = `600 11px ${this.canvasEngine.tokens.fontMono}`;

    for (const o of pts) {
      const [x, y] = o.xy;
      const sName = cleanStationName(o.s.name);
      const valFmt = o.v == null ? '–' : (this.state.pollutant === 'CO' ? (+o.v).toFixed(1) : Math.round(o.v));
      const valStr = ` ${valFmt}`;
      const nameW = g.measureText(sName).width;
      const valW = g.measureText(valStr).width;
      const boxW = Math.round(nameW + valW + 20);
      const boxH = 18;

      let best = null;
      const preferLeft = x > LW * 0.58;
      const sides = preferLeft ? [true, false] : [false, true];
      const verticalOffsets = [0, -16, 16, -32, 32, -48, 48];

      for (const left of sides) {
        for (const dy of verticalOffsets) {
          const lx = left ? x - 12 - boxW : x + 12;
          const ly = y - 9 + dy;
          const rect = [lx - 2, ly - 2, boxW + 4, boxH + 4];

          if (lx < 4 || lx + boxW > LW - 4 || ly < 4 || ly + boxH > LH - 4) continue;

          const collides = placed.some(p =>
            rect[0] < p[0] + p[2] && rect[0] + rect[2] > p[0] &&
            rect[1] < p[1] + p[3] && rect[1] + rect[3] > p[1]
          );

          if (!collides) {
            best = { lx, ly, boxW, boxH, rect, dy, left };
            break;
          }
        }
        if (best) break;
      }

      if (!best) {
        best = {
          lx: preferLeft ? x - 12 - boxW : x + 12,
          ly: y - 9,
          boxW,
          boxH,
          rect: [preferLeft ? x - 12 - boxW : x + 12, y - 9, boxW, boxH],
          dy: 0,
          left: preferLeft,
        };
      }
      placed.push(best.rect);

      // Leader line if offset or displaced
      if (Math.abs(best.dy) > 4 || best.left) {
        g.save();
        g.strokeStyle = 'rgba(255, 255, 255, 0.28)';
        g.lineWidth = 1.0;
        g.beginPath();
        g.moveTo(x, y);
        const targetX = best.left ? best.lx + best.boxW : best.lx;
        const targetY = best.ly + best.boxH / 2;
        g.lineTo(targetX, targetY);
        g.stroke();
        g.restore();
      }

      // Dark glass pill badge background
      g.save();
      g.fillStyle = 'rgba(12, 20, 18, 0.90)';
      g.strokeStyle = 'rgba(255, 255, 255, 0.16)';
      g.lineWidth = 1;
      if (g.roundRect) {
        g.beginPath();
        g.roundRect(best.lx, best.ly, best.boxW, best.boxH, 4);
        g.fill();
        g.stroke();
      } else {
        g.fillRect(best.lx, best.ly, best.boxW, best.boxH);
        g.strokeRect(best.lx, best.ly, best.boxW, best.boxH);
      }

      // Severity indicator dot
      const dotColor = o.v == null ? 'var(--ink-secondary)' : col(o.v, 1.0, rPol);
      g.fillStyle = dotColor;
      g.beginPath();
      g.arc(best.lx + 8, best.ly + best.boxH / 2, 3, 0, Math.PI * 2);
      g.fill();

      // Station Name
      g.font = `600 11px ${this.canvasEngine.tokens.fontMono}`;
      g.fillStyle = '#e6ece9';
      g.textBaseline = 'middle';
      g.fillText(sName, best.lx + 15, best.ly + best.boxH / 2);

      // Station Reading Value
      g.fillStyle = dotColor;
      g.font = `700 11px ${this.canvasEngine.tokens.fontMono}`;
      g.fillText(valStr, best.lx + 15 + nameW, best.ly + best.boxH / 2);
      g.restore();
    }

    g.restore();
  }

  updateLahoreTable(fr) {
    const tbody = document.getElementById('lahoreTableBody');
    if (!tbody || !this.stations) return;

    const polData = this.baselineData?.pol?.[this.state.pollutant];
    if (!polData || !polData.stations) return;

    const lahoreStations = this.stations.filter(s => {
      const d = (s.district || s.d || '').toLowerCase();
      const isLhr = d === 'lahore' || (s.name && s.name.toLowerCase().includes('lhr'));
      const isMetar = s.station_type === 'airport_metar' || s.name === 'Lahore';
      return isLhr && !isMetar;
    });

    const N = this.state.totalHours || 216;
    const fmt = v => v == null ? '–' : (this.state.pollutant === 'CO' ? (+v).toFixed(1) : Math.round(v));
    const r = refFor(polData);

    const cleanStationName = (name) => {
      return name
        .replace(/-LHR$/, '')
        .replace(/ LHR - Mobile \d| - Mobile \d/, '')
        .replace('Govt. Teaching Hospital ', 'GTH ')
        .replace('BHU Jandiala Kalsan', 'Jandiala Kalsan')
        .replace('Gulberg III Lahore', 'Gulberg III')
        .replace('Kahna Nau Hospital', 'Kahna Nau')
        .replace('Punjab University', 'Punjab Univ')
        .trim();
    };

    tbody.innerHTML = lahoreStations.map(s => {
      const vs = polData.stations[s.name] || [];
      const v = vs[fr];
      const valid = vs.filter(x => x != null && !isNaN(x));
      const m = valid.length >= Math.max(1, Math.round(0.75 * N)) ? valid.reduce((a, b) => a + b, 0) / valid.length : null;
      const cleanName = cleanStationName(s.name);
      const typeStr = s.mobile ? '<span style="color:#60a5fa;">▲ Mobile</span>' : '<span style="color:#94a3b8;">■ Fixed</span>';
      const swatch = v != null ? `<span class="swatch" style="background:${col(v, 1.0, r)}; display:inline-block; width:8px; height:8px; border-radius:2px; margin-right:6px; vertical-align:middle;"></span>` : '';
      const readColor = v != null ? col(v, 1.0, r) : 'inherit';

      return `<tr>
        <td><b>${cleanName}</b></td>
        <td><span style="font-size:11px;">${typeStr}</span></td>
        <td class="r num" style="color:${readColor}; font-weight:600;">${swatch}${fmt(v)}</td>
        <td class="r num">${fmt(m)}</td>
      </tr>`;
    }).join('');
  }

  refreshHourData(hour) {
    const slice = this.evaluateInterpolatedSlice(hour);
    this.updateThrottledUI(slice);
  }
}

// Bootstrap on DOM Ready
document.addEventListener('DOMContentLoaded', () => {
  window.PAQ_APP = new App();
  window.PAQ_APP.init().catch(err => console.error('App init error:', err));
});
