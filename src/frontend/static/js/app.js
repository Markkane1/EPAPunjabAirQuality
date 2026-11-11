/**
 * Master Application Coordinator for Punjab Air Quality Operational Console.
 * Coordinates 60 FPS Canvas Map Engine, API Gateway client, and UI Controller.
 */

import { ApiClient } from './api.js';
import { compilePaths, project } from './geo.js';
import { CanvasMapEngine, STATUTORY_LIMITS } from './canvas.js';
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

    // 6. Handle Window Resize
    window.addEventListener('resize', () => {
      if (this.canvasEngine) {
        this.canvasEngine.resize();
        this.recompilePaths();
      }
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
    const [hourly, current, baseline] = await Promise.all([
      this.apiClient.getHourlyObservations(this.state.pollutant),
      this.apiClient.getCurrentObservations(this.state.pollutant),
      this.apiClient.loadBaselineData(),
    ]);

    this.hourlyObservations = hourly;
    if (hourly && hourly.hours) {
      this.timestamps = hourly.hours;
      this.state.totalHours = hourly.hours.length;
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

    // Throttle UI DOM updates to 10 Hz (every 100ms) to eliminate DOM thrashing
    if (timestamp - this.lastUiUpdateTime > 100) {
      this.lastUiUpdateTime = timestamp;
      this.updateThrottledUI(interpolated);
    }

    requestAnimationFrame((t) => this.animationLoop(t));
  }

  evaluateInterpolatedSlice(fp) {
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
  }

  // =========================================================================
  // USER EVENT HANDLERS
  // =========================================================================

  togglePlay() {
    this.state.isPlaying = !this.state.isPlaying;
    const playBtn = document.getElementById('playBtn');
    if (playBtn) {
      playBtn.textContent = this.state.isPlaying ? 'Pause' : 'Play';
    }
  }

  seekHour(hour) {
    this.state.currentHour = Math.max(0, Math.min(this.state.totalHours - 1, hour));
    this.refreshHourData(this.state.currentHour);
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
    this.state.selectedDistrict = districtName;
    const dropdown = document.getElementById('districtSelectDropdown');
    if (dropdown) dropdown.value = districtName;

    this.updateCPF();
  }

  async selectPollutant(pollutantKey) {
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
    if (viewName === 'heatmap' && this.hourlyObservations) {
      this.ui.renderHeatmapMatrix(this.hourlyObservations, this.state.currentHour);
    }
  }

  onLiveHourlyUpdate(update) {
    console.log('SSE Live Telemetry Packet Received:', update);
    // Merge new telemetry frame if timestamp is newer
    this.ui.updateLiveStatus('live');
  }

  onCsvIngested(result) {
    if (!result || result.valid_rows === 0 || result.status === 'failed') {
      console.warn('Ignoring CSV ingestion with 0 valid records:', result);
      return;
    }
    console.log('CSV Ingestion Complete:', result);
    this.ui.updateLiveStatus('user_csv');
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
