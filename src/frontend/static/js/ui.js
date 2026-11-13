/**
 * UI Components & Controller Module for Punjab Air Quality Console.
 * Manages DOM updates, Event Listeners, Modals, 16-Sector CPF Polar Rose,
 * 24h Sparkline Canvas, and Deep-Dive Panels across Zones 1-5.
 */

import {
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
  getColorCss,
  getColorRgb,
  aqiCat,
  isAQI,
  refFor
} from './canvas.js';

function escapeHtml(str) {
  if (str === null || str === undefined) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

export class UIController {
  constructor(app) {
    this.app = app;

    // Cache Key DOM Elements
    this.dom = {
      // Zone 1
      liveBadge: document.getElementById('liveSyncBadge'),
      liveBadgeText: document.getElementById('liveSyncText'),
      provincialAqiBadge: document.getElementById('provincialAqiBadge'),
      clockReadout: document.getElementById('clockReadout'),
      themeToggleBtn: document.getElementById('themeToggleBtn'),
      csvUploadBtn: document.getElementById('csvUploadBtn'),
      csvModal: document.getElementById('csvModal'),
      csvFileInput: document.getElementById('csvFileInput'),
      csvUploadSubmit: document.getElementById('csvUploadSubmit'),
      csvModalClose: document.getElementById('csvModalClose'),
      csvQuarantineArea: document.getElementById('csvQuarantineArea'),
      navTabs: document.querySelectorAll('.nav-tab-btn'),

      // Zone 2
      pollutantStrip: document.getElementById('pollutantStrip'),

      // Zone 3
      hudDate: document.getElementById('hudDate'),
      hudTime: document.getElementById('hudTime'),
      hudPollutant: document.getElementById('hudPollutant'),
      legendTitle: document.getElementById('legendTitle'),
      legendColorBar: document.getElementById('legendColorBar'),
      legendTicks: document.getElementById('legendTicks'),
      playBtn: document.getElementById('playBtn'),
      scrubRange: document.getElementById('scrubRange'),
      speedSelect: document.getElementById('speedSelect'),
      modeRadios: document.querySelectorAll('input[name="mapMode"]'),
      transportCheck: document.getElementById('toggleTransportLinks'),
      regionalWindCheck: document.getElementById('toggleRegionalWinds'),

      // Zone 4
      kpiMean: document.getElementById('kpiMeanVal'),
      kpiExceed: document.getElementById('kpiExceedVal'),
      kpiPeak: document.getElementById('kpiPeakVal'),
      sparkCanvas: document.getElementById('sparklineCanvas'),
      airportTableBody: document.getElementById('airportTableBody'),
      districtRankedList: document.getElementById('districtRankedList'),
      selectedDistrictTitle: document.getElementById('selectedDistrictTitle'),
      selectedDistrictTableBody: document.getElementById('selectedDistrictTableBody'),
      districtSelectDropdown: document.getElementById('districtSelectDropdown'),
      roseCanvas: document.getElementById('roseCanvas'),
      roseMetaText: document.getElementById('roseMetaText'),

      // Zone 5 Panels
      deepDivePanels: document.querySelectorAll('.deep-dive-panel'),
      miniGridContainer: document.getElementById('miniGridContainer'),
      lahoreTableBody: document.getElementById('lahoreTableBody'),
      lahoreCanvas: document.getElementById('lahoreMapCanvas'),
      heatmapContainer: document.getElementById('heatmapContainer'),
      heatmapTable: document.getElementById('heatmapTable'),
      heatmapTabs: document.querySelectorAll('.heatmap-metric-tab'),

      // Live & Dynamic Ingestion Controls
      liveToggleBtn: document.getElementById('liveToggleBtn'),
      tickBtn: document.getElementById('tickBtn'),
      tbInflowVal: document.getElementById('tbInflowVal'),
      tbOutflowVal: document.getElementById('tbOutflowVal'),
      tbNetVal: document.getElementById('tbNetVal'),
      tbNodesCount: document.getElementById('tbNodesCount'),
      crossBorderTableBody: document.getElementById('crossBorderTableBody'),

      // Grid Synoptic Toolbar
      gridPlayBtn: document.getElementById('gridPlayBtn'),
      gridScrubRange: document.getElementById('gridScrubRange'),
      gridTimeDisplay: document.getElementById('gridTimeDisplay'),
      gridMapModeRadios: document.querySelectorAll('input[name="gridMapMode"]'),
      gridToggleTransport: document.getElementById('gridToggleTransport'),
      gridResetZoomBtn: document.getElementById('gridResetZoomBtn'),
      gridZoomBanner: document.getElementById('gridZoomBanner'),
      gridZoomDistrictName: document.getElementById('gridZoomDistrictName'),
    };

    this.bindEvents();
  }

  bindEvents() {
    // Theme Switcher
    if (this.dom.themeToggleBtn) {
      this.dom.themeToggleBtn.addEventListener('click', () => {
        const currentTheme = document.documentElement.getAttribute('data-theme') || 'dark';
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', newTheme);
        this.app.onThemeChanged(newTheme);
      });
    }

    // Navigation Subview Tabs
    this.dom.navTabs.forEach(btn => {
      btn.addEventListener('click', () => {
        const targetView = btn.dataset.view;
        this.dom.navTabs.forEach(b => b.setAttribute('aria-selected', b === btn ? 'true' : 'false'));
        this.switchView(targetView);
      });
    });

    // CSV Modal
    if (this.dom.csvUploadBtn && this.dom.csvModal) {
      this.dom.csvUploadBtn.addEventListener('click', () => {
        this.dom.csvModal.removeAttribute('hidden');
      });
    }
    if (this.dom.csvModalClose) {
      this.dom.csvModalClose.addEventListener('click', () => {
        this.dom.csvModal.setAttribute('hidden', '');
      });
    }
    if (this.dom.csvFileInput) {
      this.dom.csvFileInput.addEventListener('change', () => {
        if (this.dom.csvQuarantineArea) {
          this.dom.csvQuarantineArea.innerHTML = '';
        }
      });
    }
    if (this.dom.csvUploadSubmit) {
      this.dom.csvUploadSubmit.addEventListener('click', () => this.handleCsvUpload());
    }

    // Scrubber & Playback Controls
    if (this.dom.liveToggleBtn) {
      this.dom.liveToggleBtn.addEventListener('click', () => {
        this.app.toggleLiveNowcast();
      });
    }
    if (this.dom.tickBtn) {
      this.dom.tickBtn.addEventListener('click', () => {
        this.app.triggerPipelineTick();
      });
    }
    if (this.dom.playBtn) {
      this.dom.playBtn.addEventListener('click', () => this.app.togglePlay());
    }
    if (this.dom.scrubRange) {
      this.dom.scrubRange.addEventListener('input', (e) => {
        this.app.seekHour(parseFloat(e.target.value));
      });
    }
    if (this.dom.speedSelect) {
      this.dom.speedSelect.addEventListener('change', (e) => {
        this.app.setSpeed(parseFloat(e.target.value));
      });
    }

    // Display Mode Radios
    this.dom.modeRadios.forEach(radio => {
      radio.addEventListener('change', (e) => {
        if (e.target.checked) {
          this.app.setDisplayMode(e.target.value);
          this.dom.gridMapModeRadios.forEach(r => { r.checked = (r.value === e.target.value); });
        }
      });
    });

    // Environmental Layer Toggles
    if (this.dom.transportCheck) {
      this.dom.transportCheck.addEventListener('change', (e) => {
        this.app.setTransportLinksVisible(e.target.checked);
        if (this.dom.gridToggleTransport) this.dom.gridToggleTransport.checked = e.target.checked;
      });
    }

    // Grid Synoptic Toolbar Bindings
    if (this.dom.gridPlayBtn) {
      this.dom.gridPlayBtn.addEventListener('click', () => this.app.togglePlay());
    }
    if (this.dom.gridScrubRange) {
      this.dom.gridScrubRange.addEventListener('input', (e) => {
        this.app.seekHour(parseFloat(e.target.value));
      });
    }
    this.dom.gridMapModeRadios.forEach(radio => {
      radio.addEventListener('change', (e) => {
        if (e.target.checked) {
          this.app.setDisplayMode(e.target.value);
          this.dom.modeRadios.forEach(r => { r.checked = (r.value === e.target.value); });
        }
      });
    });
    if (this.dom.gridToggleTransport) {
      this.dom.gridToggleTransport.addEventListener('change', (e) => {
        this.app.setTransportLinksVisible(e.target.checked);
        if (this.dom.transportCheck) this.dom.transportCheck.checked = e.target.checked;
      });
    }
    if (this.dom.gridResetZoomBtn) {
      this.dom.gridResetZoomBtn.addEventListener('click', () => {
        this.app.setGridZoomDistrict(null);
      });
    }
    if (this.dom.regionalWindCheck) {
      this.dom.regionalWindCheck.addEventListener('change', (e) => {
        this.app.setRegionalWindsVisible(e.target.checked);
      });
    }

    // District Selector Dropdown
    if (this.dom.districtSelectDropdown) {
      this.dom.districtSelectDropdown.addEventListener('change', (e) => {
        this.app.selectDistrict(e.target.value);
      });
    }

    // Map Zoom & Pan HUD Controls
    this.bindZoomControls();

    // Global Keyboard Hotkeys
    window.addEventListener('keydown', (e) => {
      // Spacebar toggles Play/Pause (unless focused in an input)
      if (e.code === 'Space' && e.target.tagName !== 'INPUT' && e.target.tagName !== 'SELECT') {
        e.preventDefault();
        this.app.togglePlay();
      }

      // Keys 1 through 9 switch statutory pollutants
      if (e.code.startsWith('Digit') && e.target.tagName !== 'INPUT') {
        const digit = parseInt(e.code.slice(5), 10);
        const pollutants = ['AQI', 'PM2.5', 'PM10', 'NO2', 'SO2', 'CO', 'O3', 'NO', 'NOx'];
        if (digit >= 1 && digit <= pollutants.length) {
          this.app.selectPollutant(pollutants[digit - 1]);
        }
      }
    });
  }

  bindZoomControls() {
    const btnIn = document.getElementById('btnZoomIn');
    const btnOut = document.getElementById('btnZoomOut');
    const btnReset = document.getElementById('btnZoomReset');

    if (btnIn) {
      btnIn.addEventListener('click', () => {
        if (!this.app.canvasEngine) return;
        const cx = this.app.canvasEngine.width / 2;
        const cy = this.app.canvasEngine.height / 2;
        this.app.canvasEngine.setZoom(this.app.canvasEngine.zoom * 1.35, cx, cy);
        const mc = document.getElementById('mainMapCanvas');
        if (mc) mc.style.cursor = this.app.canvasEngine.zoom > 1.05 ? 'grab' : 'crosshair';
      });
    }

    if (btnOut) {
      btnOut.addEventListener('click', () => {
        if (!this.app.canvasEngine) return;
        const cx = this.app.canvasEngine.width / 2;
        const cy = this.app.canvasEngine.height / 2;
        this.app.canvasEngine.setZoom(this.app.canvasEngine.zoom / 1.35, cx, cy);
        const mc = document.getElementById('mainMapCanvas');
        if (mc) mc.style.cursor = this.app.canvasEngine.zoom > 1.05 ? 'grab' : 'crosshair';
      });
    }

    if (btnReset) {
      btnReset.addEventListener('click', () => {
        if (!this.app.canvasEngine) return;
        this.app.canvasEngine.resetZoom();
        const mc = document.getElementById('mainMapCanvas');
        if (mc) mc.style.cursor = 'crosshair';
      });
    }
  }

  switchView(viewName) {
    this.dom.navTabs.forEach(b => {
      const active = b.dataset.view === viewName;
      b.classList.toggle('active', active);
      b.setAttribute('aria-selected', active ? 'true' : 'false');
    });

    // Show only the target panel; hide all others
    const panelIds = ['panel-console', 'panel-grid', 'panel-lahore', 'panel-heatmap', 'panel-transboundary'];
    const targetId = viewName === 'console' ? 'panel-console' : `panel-${viewName}`;
    panelIds.forEach(id => {
      const el = document.getElementById(id);
      if (!el) return;
      if (id === targetId) {
        el.removeAttribute('hidden');
      } else {
        el.setAttribute('hidden', '');
      }
    });

    // Toggle single-pollutant strip: hide in grid view where all 9 species are rendered simultaneously
    const polNav = document.querySelector('.zone-2-pollutants');
    if (polNav) {
      polNav.style.display = (viewName === 'grid') ? 'none' : 'flex';
    }

    if (this.dom.gridPlayBtn) {
      this.dom.gridPlayBtn.textContent = this.app.state.isPlaying ? 'Pause' : 'Play';
    }

    // Scroll to top of page on each view switch for clean UX
    window.scrollTo({ top: 0, behavior: 'smooth' });

    // Notify app if subview canvas needs resize/render
    this.app.onViewSwitched(viewName);
  }

  renderPollutantButtons(activePollutant) {
    if (!this.dom.pollutantStrip) return;
    this.dom.pollutantStrip.innerHTML = '';

    const list = ['AQI', 'PM2.5', 'PM10', 'NO2', 'SO2', 'CO', 'O3', 'NO', 'NOX'];
    list.forEach((key) => {
      const spec = STATUTORY_LIMITS[key] || { name: key, unit: 'µg/m³' };
      const btn = document.createElement('button');
      btn.className = `pol-btn${key === activePollutant ? ' active' : ''}`;
      btn.type = 'button';
      btn.setAttribute('role', 'radio');
      btn.setAttribute('aria-checked', key === activePollutant ? 'true' : 'false');
      btn.dataset.pollutant = key;

      const limitLabel = spec.scale === 'aqi' ? 'PEPC' : spec.ref ? `${spec.ref}` : 'REF 100';
      btn.innerHTML = `
        <span class="species">${POLNAME[key] || spec.name}</span>
        <span class="limit-badge">${limitLabel}</span>
      `;

      btn.addEventListener('click', () => {
        this.app.selectPollutant(key);
      });

      this.dom.pollutantStrip.appendChild(btn);
    });
  }

  updateLiveStatus(mode) {
    if (!this.dom.liveBadge) return;
    this.dom.liveBadge.className = 'live-pulse-badge';

    if (mode === 'live') {
      this.dom.liveBadge.classList.add('live');
      this.dom.liveBadgeText.textContent = 'LIVE SYNC: ACTIVE';
    } else if (mode === 'user_csv') {
      this.dom.liveBadge.classList.add('user');
      this.dom.liveBadgeText.textContent = 'USER CSV DATASET';
    } else {
      this.dom.liveBadge.classList.add('warn');
      this.dom.liveBadgeText.textContent = 'FALLBACK ARCHIVE (OFFLINE)';
    }
  }

  updateClockAndHUD(hourIndex, timestampStr, activePollutant) {
    // Format Pakistan Standard Time: PKT (UTC+5)
    let dateStr = 'Nov 2026';
    let timeStr = `Hour ${hourIndex}:00`;

    if (timestampStr) {
      try {
        const d = new Date(timestampStr.replace(' ', 'T') + (timestampStr.includes('Z') ? '' : 'Z'));
        dateStr = d.toLocaleDateString('en-GB', { timeZone: 'Asia/Karachi', weekday: 'short', day: '2-digit', month: 'short' });
        timeStr = d.toLocaleTimeString('en-GB', { timeZone: 'Asia/Karachi', hour: '2-digit', minute: '2-digit', hour12: false });
      } catch (e) {
        timeStr = `${hourIndex}:00`;
      }
    }

    if (this.dom.clockReadout) {
      this.dom.clockReadout.textContent = `PKT (UTC+5): ${dateStr} ${timeStr}`;
    }
    if (this.dom.hudDate) this.dom.hudDate.textContent = dateStr;
    if (this.dom.hudTime) this.dom.hudTime.textContent = timeStr;
    if (this.dom.hudPollutant) this.dom.hudPollutant.textContent = `${activePollutant} · ${STATUTORY_LIMITS[activePollutant]?.unit || ''}`;
    if (this.dom.scrubRange && document.activeElement !== this.dom.scrubRange) {
      this.dom.scrubRange.value = hourIndex.toFixed(2);
    }
    if (this.dom.gridScrubRange && document.activeElement !== this.dom.gridScrubRange) {
      this.dom.gridScrubRange.value = hourIndex.toFixed(2);
    }
    if (this.dom.gridTimeDisplay) {
      this.dom.gridTimeDisplay.textContent = `${dateStr} ${timeStr}`;
    }
  }

  updateLegend(pollutantKey) {
    if (!this.dom.legendColorBar || !this.dom.legendTicks) return;

    const Q = this.app?.baselineData?.pol?.[pollutantKey] || { key: pollutantKey, ref: 35, refavg: '24-hr', unit: 'µg/m³' };
    const spec = STATUTORY_LIMITS[pollutantKey] || STATUTORY_LIMITS['PM2.5'];

    if (this.dom.legendTitle) {
      const name = POLNAME[pollutantKey] || spec.name;
      const lim = limLabel(Q);
      this.dom.legendTitle.textContent = `${name} · ${lim}`;
    }

    // Set Discrete / Stepped Statutory Gradient Bar
    this.dom.legendColorBar.style.background = barFor(Q);

    // Set Statutory Ticks
    if (isAQI(Q)) {
      this.dom.legendTicks.innerHTML = aqiTicks();
    } else if (BP[pollutantKey]) {
      this.dom.legendTicks.innerHTML = bpTicks(pollutantKey);
    } else {
      const ref = Q.ref || spec.ref || 100;
      const multipliers = [0, 0.5, 1.0, 1.5, 2.5, 4.0, 6.0];
      this.dom.legendTicks.innerHTML = multipliers.map((m, i) => {
        const val = pollutantKey === 'CO' ? (m * ref).toFixed(1) : Math.round(m * ref);
        const left = Math.max(3, Math.min(97, (i / (multipliers.length - 1)) * 100));
        return `<span style="left: ${left}%">${val}${i === 6 ? '+' : ''}</span>`;
      }).join('');
    }
  }

  updateProvincialSummary(summary, activePollutant) {
    if (!summary) return;

    if (this.dom.kpiMean) {
      this.dom.kpiMean.textContent = summary.mean_aqi !== undefined ? summary.mean_aqi.toFixed(1) : '–';
    }
    if (this.dom.kpiExceed) {
      this.dom.kpiExceed.textContent = `${summary.exceedance_peqs_count || 0} / ${summary.total_districts || 41}`;
    }
    if (this.dom.kpiPeak) {
      this.dom.kpiPeak.textContent = summary.peak_district ? `${summary.peak_district} (${Math.round(summary.peak_aqi || 0)})` : '–';
    }

    // Update Provincial Header Badge
    if (this.dom.provincialAqiBadge) {
      const maxVal = summary.peak_aqi || 280;
      let tier = PEPC_TIERS[3]; // Unhealthy default
      for (const t of PEPC_TIERS) {
        if (maxVal <= t.max) {
          tier = t;
          break;
        }
      }
      this.dom.provincialAqiBadge.style.backgroundColor = `rgb(${tier.color.join(',')})`;
      this.dom.provincialAqiBadge.textContent = `${activePollutant} ${Math.round(maxVal)} · ${tier.label.toUpperCase()}`;
    }
  }

  // =========================================================================
  // ZONE 4: SIDEBAR RENDERERS
  // =========================================================================

  drawSparkline(canvas, seriesData, currentHourIndex, peqsLimit = 200) {
    if (!canvas || !seriesData || seriesData.length === 0) return;
    const ctx = canvas.getContext('2d');
    const w = canvas.width = canvas.parentElement.clientWidth || 300;
    const h = canvas.height = 70;

    ctx.clearRect(0, 0, w, h);

    const validVals = seriesData.filter(v => v !== null && !isNaN(v));
    if (validVals.length === 0) return;

    const maxVal = Math.max(...validVals, peqsLimit * 1.25, 50);
    const minVal = Math.min(0, ...validVals);

    const getX = (idx) => (idx / (seriesData.length - 1)) * w;
    const getY = (val) => h - ((val - minVal) / (maxVal - minVal)) * (h - 10) - 5;

    // PEQS Reference Dashed Line
    const peqsY = getY(peqsLimit);
    ctx.strokeStyle = '#ff4a4a';
    ctx.lineWidth = 1.0;
    ctx.setLineDash([4, 3]);
    ctx.beginPath();
    ctx.moveTo(0, peqsY);
    ctx.lineTo(w, peqsY);
    ctx.stroke();
    ctx.setLineDash([]);

    // Sparkline Trend Curve
    ctx.strokeStyle = '#5fc4c4';
    ctx.lineWidth = 1.6;
    ctx.beginPath();
    let started = false;
    for (let i = 0; i < seriesData.length; i++) {
      const v = seriesData[i];
      if (v === null || isNaN(v)) continue;
      const x = getX(i);
      const y = getY(v);
      if (!started) {
        ctx.moveTo(x, y);
        started = true;
      } else {
        ctx.lineTo(x, y);
      }
    }
    ctx.stroke();

    // Synchronized Cursor Line
    const cursorX = getX(currentHourIndex);
    ctx.strokeStyle = '#ffffff';
    ctx.lineWidth = 1.2;
    ctx.beginPath();
    ctx.moveTo(cursorX, 0);
    ctx.lineTo(cursorX, h);
    ctx.stroke();

    // Active Cursor Dot
    const curVal = seriesData[Math.floor(currentHourIndex)];
    if (curVal !== null && !isNaN(curVal)) {
      const curY = getY(curVal);
      ctx.fillStyle = '#5fc4c4';
      ctx.beginPath();
      ctx.arc(cursorX, curY, 3.5, 0, Math.PI * 2);
      ctx.fill();
    }
  }

  renderAirportWeatherTable(airports) {
    if (!this.dom.airportTableBody) return;
    this.dom.airportTableBody.innerHTML = '';

    const list = airports && airports.length > 0 ? airports : [
      { icao: 'OPLA', name: 'Lahore', wind_dir: 180, wind_kt: 4, vis: 1200, temp: 21, wx: 'Smoke' },
      { icao: 'OPFA', name: 'Faisalabad', wind_dir: 210, wind_kt: 6, vis: 2500, temp: 23, wx: 'Mist' },
      { icao: 'OPMT', name: 'Multan', wind_dir: 160, wind_kt: 3, vis: 1800, temp: 24, wx: 'Haze' },
      { icao: 'OPST', name: 'Sialkot', wind_dir: 140, wind_kt: 5, vis: 1000, temp: 20, wx: 'Smoke' },
      { icao: 'OPIS', name: 'Islamabad', wind_dir: 320, wind_kt: 4, vis: 4000, temp: 19, wx: 'Clear' },
      { icao: 'VIAR', name: 'Amritsar', wind_dir: 170, wind_kt: 5, vis: 800, temp: 20, wx: 'Fog' },
    ];

    list.slice(0, 8).forEach(ap => {
      const row = document.createElement('tr');
      const windStr = ap.wind_dir ? `${ap.wind_dir}° ${ap.wind_kt || 0}kt` : (ap.wind_kt ? `${ap.wind_kt}kt` : 'Calm');
      row.innerHTML = `
        <td><b>${ap.icao || ap.id}</b> <span style="font-size: 10px; color: var(--ink-secondary)">${ap.name || ''}</span></td>
        <td class="r num">${windStr}</td>
        <td class="r num">${ap.vis || 1500}m</td>
        <td class="r num">${ap.temp || 21}°C</td>
        <td style="font-size: 11px">${ap.wx || 'Haze'}</td>
      `;
      this.dom.airportTableBody.appendChild(row);
    });
  }

  renderDistrictRankedList(districtsReadings, activePollutant, selectedDistrict) {
    if (!this.dom.districtRankedList) return;
    this.dom.districtRankedList.innerHTML = '';

    const sorted = Object.entries(districtsReadings)
      .map(([name, val]) => ({ name, val: val !== null && val !== undefined ? val : -1 }))
      .sort((a, b) => b.val - a.val);

    const maxVal = Math.max(1, ...sorted.map(d => d.val));
    const spec = STATUTORY_LIMITS[activePollutant] || STATUTORY_LIMITS['PM2.5'];
    const peqs = spec.ref || 100;

    sorted.forEach((item, idx) => {
      const row = document.createElement('div');
      row.className = `district-row ${item.name === selectedDistrict ? 'selected' : ''}`;
      row.dataset.district = item.name;

      const pct = Math.min(100, Math.max(0, (item.val / maxVal) * 100));
      const peqsPct = Math.min(100, (peqs / maxVal) * 100);
      const color = getColorCss(item.val, activePollutant, 0.9);

      row.innerHTML = `
        <span class="name">${idx + 1}. ${item.name}</span>
        <div class="bar-track">
          <div class="bar-fill" style="width: ${pct}%; background-color: ${color}"></div>
          <div class="bar-peqs-marker" style="left: ${peqsPct}%" title="PEQS: ${peqs}"></div>
        </div>
        <span class="val-box">${item.val >= 0 ? Math.round(item.val) : '~'}</span>
      `;

      row.addEventListener('click', () => {
        this.app.selectDistrict(item.name);
      });

      this.dom.districtRankedList.appendChild(row);
    });
  }

  renderSelectedDistrictTelemetry(districtName, readings, activePollutant, rollingMeans = {}) {
    if (this.dom.selectedDistrictTitle) {
      this.dom.selectedDistrictTitle.textContent = districtName;
    }
    if (!this.dom.selectedDistrictTableBody) return;
    this.dom.selectedDistrictTableBody.innerHTML = '';

    const isEst = this.app?.districts?.find(d => (d.name || d.district) === districtName)?.est;
    const pollutants = ['AQI', 'PM2.5', 'PM10', 'NO2', 'SO2', 'CO', 'O3', 'NO', 'NOX'];
    const curHour = this.app?.state?.currentHour || 0;

    pollutants.forEach(pol => {
      const spec = STATUTORY_LIMITS[pol] || { name: pol, unit: 'µg/m³' };
      const Q = this.app?.baselineData?.pol?.[pol];
      
      let curVal = readings[pol] !== undefined ? readings[pol] : (this.app?.mval ? this.app.mval(Q, districtName, curHour) : null);
      if (curVal === null && pol === activePollutant) curVal = readings.current;

      const r = refFor(Q);
      const valFmt = curVal == null ? '–' : (pol === 'CO' ? (+curVal).toFixed(2) : Math.round(curVal));
      const valStr = curVal !== null ? `${isEst ? '~' : ''}${valFmt}` : '–';

      const dailyMean = Q?.daily?.[districtName]?.mean;
      let periodMean = rollingMeans[pol] !== undefined ? rollingMeans[pol] : (dailyMean !== undefined ? dailyMean : (curVal !== null ? (pol === 'CO' ? curVal * 0.94 : Math.round(curVal * 0.94)) : null));
      const meanFmt = periodMean == null ? '–' : (pol === 'CO' ? (+periodMean).toFixed(2) : Math.round(periodMean));
      const meanStr = periodMean !== null ? `${isEst ? '~' : ''}${meanFmt}` : '–';

      const ref = Q?.ref || spec.ref;
      let peqsStr = '–';
      if (isAQI(Q)) {
        peqsStr = curVal !== null ? aqiCat(curVal)[2] : '–';
      } else if (ref) {
        const exceedRatio = curVal ? (curVal / ref).toFixed(1) : null;
        peqsStr = `${spec.refavg || ''} ${ref}${exceedRatio ? ` (${exceedRatio}x)` : ''}`;
      }

      const swatchColor = curVal !== null ? col(curVal, 1.0, r) : 'transparent';
      const row = document.createElement('tr');
      if (pol === activePollutant) {
        row.style.fontWeight = '700';
        row.style.background = 'var(--bg-panel-elevated)';
      }

      row.innerHTML = `
        <td><b>${POLNAME[pol] || spec.name}</b> <span style="font-size: 10px; color: var(--ink-secondary)">${spec.unit || ''}</span></td>
        <td class="r num">${curVal !== null ? `<span class="swatch" style="background:${swatchColor}"></span>` : ''}${valStr}</td>
        <td class="r num">${meanStr}</td>
        <td class="r num">${peqsStr}</td>
      `;
      this.dom.selectedDistrictTableBody.appendChild(row);
    });
  }

  updateLiveModeBadge(isLive) {
    if (this.dom.liveToggleBtn) {
      if (isLive) {
        this.dom.liveToggleBtn.classList.add('active');
        this.dom.liveToggleBtn.style.background = '#a33';
        this.dom.liveToggleBtn.style.color = '#fff';
        this.dom.liveToggleBtn.textContent = '🔴 LIVE';
      } else {
        this.dom.liveToggleBtn.classList.remove('active');
        this.dom.liveToggleBtn.style.background = 'var(--bg-card)';
        this.dom.liveToggleBtn.style.color = 'var(--ink-secondary)';
        this.dom.liveToggleBtn.textContent = '⚪ HISTORICAL';
      }
    }
  }

  renderLahoreStationsTable(stations, currentHour) {
    if (!this.dom.lahoreTableBody) return;
    this.dom.lahoreTableBody.innerHTML = '';

    const cleanStationName = (name) => {
      return (name || '')
        .replace(/-LHR$/, '')
        .replace(/ LHR - Mobile \d| - Mobile \d/, '')
        .replace('Govt. Teaching Hospital ', 'GTH ')
        .replace('BHU Jandiala Kalsan', 'Jandiala Kalsan')
        .replace('Gulberg III Lahore', 'Gulberg III')
        .replace('Kahna Nau Hospital', 'Kahna Nau')
        .replace('Punjab University', 'Punjab Univ')
        .trim();
    };

    const lahoreStations = (stations || []).filter(s => {
      const d = (s.district || s.d || '').toLowerCase();
      const isLhr = d === 'lahore' || (s.name && s.name.toLowerCase().includes('lhr'));
      const isMetar = s.station_type === 'airport_metar' || s.name === 'Lahore';
      return isLhr && !isMetar;
    });

    if (lahoreStations.length === 0) {
      this.dom.lahoreTableBody.innerHTML = '<tr><td colspan="4" style="text-align: center; color: var(--ink-secondary);">No Lahore stations active</td></tr>';
      return;
    }

    lahoreStations.forEach(s => {
      const row = document.createElement('tr');
      const val = s.current !== undefined ? s.current : (s.val !== undefined ? s.val : (s.reading !== undefined ? s.reading : null));
      const polVal = val !== null ? Math.round(val) : '–';
      const mean24 = s.mean24 !== undefined ? Math.round(s.mean24) : (val !== null ? Math.round(val * 0.94) : '–');
      const cleanName = cleanStationName(s.name);
      const typeStr = s.mobile ? '<span style="color:#60a5fa; font-size:11px;">▲ Mobile</span>' : '<span style="color:#94a3b8; font-size:11px;">■ Fixed</span>';
      const readColor = val !== null ? getColorCss(val, 'PM2.5') : 'inherit';
      const swatch = val !== null ? `<span class="swatch" style="background:${readColor}; display:inline-block; width:8px; height:8px; border-radius:2px; margin-right:6px; vertical-align:middle;"></span>` : '';

      row.innerHTML = `
        <td><b>${escapeHtml(cleanName)}</b></td>
        <td>${typeStr}</td>
        <td class="r num" style="color: ${readColor}; font-weight:600;">${swatch}${polVal}</td>
        <td class="r num">${mean24}</td>
      `;
      this.dom.lahoreTableBody.appendChild(row);
    });
  }

  renderTransboundaryKpis(tbData) {
    if (!tbData) return;
    if (this.dom.tbInflowVal && tbData.inflow_total !== undefined) {
      this.dom.tbInflowVal.textContent = `${Number(tbData.inflow_total).toFixed(1)} kg/s`;
    }
    if (this.dom.tbOutflowVal && tbData.outflow_total !== undefined) {
      this.dom.tbOutflowVal.textContent = `${Number(tbData.outflow_total).toFixed(1)} kg/s`;
    }
    if (this.dom.tbNetVal && tbData.net_transboundary_flux !== undefined) {
      const val = Number(tbData.net_transboundary_flux);
      const sign = val > 0 ? '+' : '';
      this.dom.tbNetVal.textContent = `${sign}${val.toFixed(1)} kg/s`;
      this.dom.tbNetVal.style.color = val > 0 ? '#ff4a4a' : '#5fc4c4';
    }
    if (this.dom.tbNodesCount && tbData.border_samples) {
      this.dom.tbNodesCount.textContent = `${tbData.border_samples.length} Nodes`;
    }
  }

  renderCrossBorderTable(cities) {
    if (!this.dom.crossBorderTableBody) return;
    this.dom.crossBorderTableBody.innerHTML = '';
    const list = cities && cities.length > 0 ? cities : [];

    list.forEach(c => {
      const row = document.createElement('tr');
      const aqi = c.pepc_aqi || c.us_aqi || c.aqi || 150;
      const dist = c.distance_km !== undefined ? `${Math.round(c.distance_km)} km` : '–';
      const statusStr = c.status || c.pepc_tier || 'Unhealthy';
      const aqiColor = getColorCss(aqi, 'AQI');

      row.innerHTML = `
        <td><b>${escapeHtml(c.city)}</b></td>
        <td>${dist}</td>
        <td class="r num" style="color: ${aqiColor}">${aqi}</td>
        <td style="font-size: 11px">${escapeHtml(statusStr)}</td>
      `;
      this.dom.crossBorderTableBody.appendChild(row);
    });
  }

  // =========================================================================
  // 16-SECTOR CPF POLAR WIND ROSE CANVAS
  // =========================================================================

  drawCPFPolarRose(canvas, cpfData) {
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const size = canvas.width = canvas.parentElement.clientWidth || 240;
    canvas.height = size;

    ctx.clearRect(0, 0, size, size);

    const cx = size / 2;
    const cy = size / 2;
    const maxRadius = size * 0.42;

    // Draw concentric reference circles: 0.25 (null hypothesis), 0.50, 0.75
    const rings = [0.25, 0.50, 0.75];
    ctx.lineWidth = 0.8;

    rings.forEach(rVal => {
      const r = rVal * maxRadius;
      ctx.strokeStyle = rVal === 0.25 ? '#ff6b5e' : 'rgba(255, 255, 255, 0.15)';
      if (rVal === 0.25) {
        ctx.setLineDash([3, 3]);
      } else {
        ctx.setLineDash([]);
      }
      ctx.beginPath();
      ctx.arc(cx, cy, r, 0, Math.PI * 2);
      ctx.stroke();
    });
    ctx.setLineDash([]);

    // 16 radial spoke lines (22.5 deg intervals)
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.1)';
    for (let i = 0; i < 16; i++) {
      const angle = (i * 22.5 - 90) * (Math.PI / 180);
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.lineTo(cx + Math.cos(angle) * maxRadius, cy + Math.sin(angle) * maxRadius);
      ctx.stroke();
    }

    if (!cpfData || !cpfData.sectors) return;

    // Draw 16 CPF Wedges
    const sectors = cpfData.sectors;
    const tau = cpfData.threshold_p75 || 100;

    sectors.forEach(sec => {
      const prob = sec.cpf_probability || 0;
      const r = Math.min(maxRadius, prob * maxRadius);
      const startAngle = (sec.azimuth_deg - 11.25 - 90) * (Math.PI / 180);
      const endAngle = (sec.azimuth_deg + 11.25 - 90) * (Math.PI / 180);

      // Color proportionally to concentration: C = tau * (0.6 + 1.4 * CPF)
      const effectiveVal = tau * (0.6 + 1.4 * prob);
      const [cr, cg, cb] = getColorRgb(effectiveVal, 'PM2.5');

      ctx.fillStyle = `rgba(${cr}, ${cg}, ${cb}, 0.75)`;
      ctx.strokeStyle = `rgb(${cr}, ${cg}, ${cb})`;
      ctx.lineWidth = 1.0;

      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.arc(cx, cy, r, startAngle, endAngle);
      ctx.closePath();
      ctx.fill();
      ctx.stroke();
    });

    // Central calm fraction badge
    const calmRatio = cpfData.calm_fraction !== undefined ? `${Math.round(cpfData.calm_fraction * 100)}%` : '12%';
    ctx.fillStyle = 'rgba(21, 33, 32, 0.9)';
    ctx.beginPath();
    ctx.arc(cx, cy, 14, 0, Math.PI * 2);
    ctx.fill();

    ctx.strokeStyle = '#5fc4c4';
    ctx.lineWidth = 1.2;
    ctx.stroke();

    ctx.fillStyle = '#ffffff';
    ctx.font = '600 10px "JetBrains Mono", monospace';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(calmRatio, cx, cy);

    // Cardinal labels (N, E, S, W)
    ctx.fillStyle = 'var(--ink-secondary)';
    ctx.font = '700 11px "Barlow Condensed", sans-serif';
    ctx.fillText('N', cx, cy - maxRadius - 6);
    ctx.fillText('S', cx, cy + maxRadius + 10);
    ctx.fillText('E', cx + maxRadius + 10, cy);
    ctx.fillText('W', cx - maxRadius - 10, cy);
  }

  // =========================================================================
  // ZONE 5: VIRTUALIZED HEATMAP MATRIX TABLE
  // =========================================================================

  renderHeatmapMatrix(hourlyData, activeHourIndex, metricType = 'concentration') {
    if (!this.dom.heatmapTable || !hourlyData || !hourlyData.districts) return;

    const districts = Object.keys(hourlyData.districts);
    const hours = hourlyData.hours || Array.from({ length: 216 }, (_, i) => `H${i}`);
    const totalCols = Math.min(hours.length, 216);

    let html = '<thead><tr><th class="sticky-district">District</th>';
    for (let h = 0; h < totalCols; h++) {
      const isCur = h === Math.floor(activeHourIndex);
      html += `<th class="${isCur ? 'active-col' : ''}">H${h}</th>`;
    }
    html += '</tr></thead><tbody>';

    districts.forEach(dName => {
      html += `<tr><td class="sticky-district">${dName}</td>`;
      const series = hourlyData.districts[dName].concentrations || [];
      for (let h = 0; h < totalCols; h++) {
        const val = series[h];
        const isCur = h === Math.floor(activeHourIndex);
        const bg = val !== null && val !== undefined ? getColorCss(val, hourlyData.pollutant || 'PM2.5', 0.85) : 'transparent';
        const txt = val !== null && val !== undefined ? Math.round(val) : '–';
        html += `<td class="${isCur ? 'active-col' : ''}" style="background-color: ${bg}; color: #ffffff" title="${dName} Hour ${h}: ${txt}">${txt}</td>`;
      }
      html += '</tr>';
    });
    html += '</tbody>';

    this.dom.heatmapTable.innerHTML = html;
  }

  // =========================================================================
  // CSV UPLOAD HANDLER & QUARANTINE INSPECTOR
  // =========================================================================

  renderCsvQuarantineReport(result) {
    if (!this.dom.csvQuarantineArea) return;
    const records = result.quarantined_records || result.quarantine_records || [];
    const errors = result.errors || [];
    const validCount = result.valid_rows || 0;
    const quarantinedCount = result.quarantined_rows || records.length;
    const isTotalFailure = validCount === 0;

    let html = '';

    // Status / Alert banner
    if (isTotalFailure) {
      html += `
        <div class="quarantine-banner banner-failed" style="margin-top: 10px; padding: 10px 12px; background: rgba(255, 107, 94, 0.15); border: 1px solid #ff6b5e; border-radius: 4px; color: #ff7a6b; font-size: 12px;">
          <div style="font-weight: 700; margin-bottom: 4px; display: flex; align-items: center; gap: 6px;">
            <span style="font-size: 14px;">⚠️</span> CSV Validation Failed: 0 Valid Records Merged
          </div>
          <div>All ${quarantinedCount || result.total_rows || 0} row(s) were quarantined or invalid. Current telemetry dataset remains unchanged.</div>
        </div>
      `;
    } else {
      html += `
        <div class="quarantine-banner banner-warning" style="margin-top: 10px; padding: 10px 12px; background: rgba(237, 125, 49, 0.15); border: 1px solid #ED7D31; border-radius: 4px; color: #f09553; font-size: 12px;">
          <div style="font-weight: 700; margin-bottom: 4px; display: flex; align-items: center; gap: 6px;">
            <span style="font-size: 14px;">ℹ️</span> Partial Ingestion: ${validCount} Records Merged
          </div>
          <div>${quarantinedCount} row(s) were quarantined due to schema or validation errors. Review the quarantine table below.</div>
        </div>
      `;
    }

    // Top-Level Schema Errors (e.g. missing columns)
    if (errors.length > 0) {
      html += `
        <div class="quarantine-errors" style="margin-top: 8px; padding: 8px 12px; background: rgba(0, 0, 0, 0.25); border: 1px solid var(--border-subtle); border-radius: 4px; font-size: 12px; color: var(--ink-primary);">
          <div style="font-weight: 600; color: #ff7a6b; margin-bottom: 4px;">Top-Level Schema Errors:</div>
          <ul style="margin: 0; padding-left: 18px;">
            ${errors.map(err => `<li style="margin-bottom: 2px;">${escapeHtml(err)}</li>`).join('')}
          </ul>
        </div>
      `;
    }

    // High-visibility scrollable table for row-level quarantine records
    if (records.length > 0) {
      html += `
        <div class="quarantine-table-wrap" style="margin-top: 10px; max-height: 240px; overflow-y: auto; overflow-x: auto; border: 1px solid var(--border-subtle); border-radius: 4px; background: var(--bg-canvas);">
          <table class="quarantine-table" style="width: 100%; border-collapse: collapse; font-size: 11px; text-align: left;">
            <thead>
              <tr style="position: sticky; top: 0; background: var(--bg-panel-elevated); z-index: 2; border-bottom: 1px solid var(--border-strong);">
                <th style="padding: 6px 8px; font-family: var(--font-mono); font-size: 10px; text-transform: uppercase; color: var(--ink-secondary); white-space: nowrap;">Row #</th>
                <th style="padding: 6px 8px; font-family: var(--font-mono); font-size: 10px; text-transform: uppercase; color: var(--ink-secondary); white-space: nowrap;">Station ID</th>
                <th style="padding: 6px 8px; font-family: var(--font-mono); font-size: 10px; text-transform: uppercase; color: var(--ink-secondary); white-space: nowrap;">Error Type</th>
                <th style="padding: 6px 8px; font-family: var(--font-mono); font-size: 10px; text-transform: uppercase; color: var(--ink-secondary); white-space: nowrap;">Error Message</th>
                <th style="padding: 6px 8px; font-family: var(--font-mono); font-size: 10px; text-transform: uppercase; color: var(--ink-secondary); white-space: nowrap;">Raw Row Data</th>
              </tr>
            </thead>
            <tbody>
              ${records.map(rec => {
                const rowNum = rec.row_number ?? '-';
                const stationId = escapeHtml(rec.station_id || '-');
                const errType = escapeHtml(rec.error_type || 'VALIDATION_ERROR');
                const errMsg = escapeHtml(rec.error_message || 'Malformed record');
                const rawData = rec.raw_record ? escapeHtml(JSON.stringify(rec.raw_record)) : '-';
                return `
                  <tr style="border-bottom: 1px solid var(--border-subtle);">
                    <td style="padding: 6px 8px; font-family: var(--font-mono); font-weight: 600; color: var(--accent); white-space: nowrap; text-align: center;">${rowNum}</td>
                    <td style="padding: 6px 8px; font-family: var(--font-mono); color: var(--ink-primary); white-space: nowrap;">${stationId}</td>
                    <td style="padding: 6px 8px; white-space: nowrap;"><span style="display: inline-block; padding: 2px 6px; font-family: var(--font-mono); font-size: 10px; font-weight: 600; color: #ff6b5e; background: rgba(255, 107, 94, 0.15); border-radius: 3px;">${errType}</span></td>
                    <td style="padding: 6px 8px; font-family: var(--font-body); font-size: 11px; color: var(--ink-primary); line-height: 1.3; max-width: 200px; word-break: break-word;">${errMsg}</td>
                    <td style="padding: 6px 8px; max-width: 220px;"><pre style="margin: 0; padding: 3px 5px; font-family: var(--font-mono); font-size: 10px; color: var(--ink-secondary); background: rgba(0,0,0,0.3); border-radius: 2px; overflow-x: auto; white-space: pre-wrap; word-break: break-all;">${rawData}</pre></td>
                  </tr>
                `;
              }).join('')}
            </tbody>
          </table>
        </div>
      `;
    }

    this.dom.csvQuarantineArea.innerHTML = html;
  }

  async handleCsvUpload() {
    const file = this.dom.csvFileInput.files[0];
    if (!file) {
      alert('Please select a valid CSV file.');
      return;
    }

    // Reset previous quarantine error messages
    if (this.dom.csvQuarantineArea) {
      this.dom.csvQuarantineArea.innerHTML = '';
    }

    try {
      this.dom.csvUploadSubmit.disabled = true;
      this.dom.csvUploadSubmit.textContent = 'Uploading & Validating...';

      const result = await this.app.apiClient.uploadCSV(file);
      const qRecords = result.quarantined_records || result.quarantine_records || [];
      const hasQuarantine = (result.quarantined_rows > 0) || (qRecords.length > 0) || (result.status === 'partial_quarantine') || (result.status === 'failed');
      const hasErrors = result.errors && result.errors.length > 0;
      const validCount = result.valid_rows || 0;

      if (hasQuarantine || hasErrors || validCount === 0 || result.status === 'failed') {
        // Render detailed quarantine inspector table & banner
        this.renderCsvQuarantineReport(result);

        if (result.status === 'failed' || validCount === 0) {
          alert(`CSV Ingestion Failed: 0 valid records merged. ${result.quarantined_rows || qRecords.length || result.total_rows || 0} record(s) quarantined. Review quarantine details below.`);
          // Keep modal open, do NOT switch app state to user_csv
        } else {
          alert(`CSV Ingestion Warning: ${validCount} valid records merged into telemetry, but ${result.quarantined_rows} record(s) were quarantined. Review quarantine details below.`);
          // Valid rows merged -> update app telemetry
          this.app.onCsvIngested(result);
        }
      } else {
        // Complete success with zero quarantined rows
        if (this.dom.csvQuarantineArea) this.dom.csvQuarantineArea.innerHTML = '';
        if (this.dom.csvModal) this.dom.csvModal.setAttribute('hidden', '');
        alert(`CSV Upload Success: ${validCount} valid records merged into telemetry.`);
        this.app.onCsvIngested(result);
      }
    } catch (err) {
      alert(`CSV Upload Failed: ${err.message}`);
      if (this.dom.csvQuarantineArea) {
        this.dom.csvQuarantineArea.innerHTML = `<div style="color: #ff5e5e; font-size: 12px; margin-top: 8px;"><b>Error:</b> ${escapeHtml(err.message)}</div>`;
      }
    } finally {
      this.dom.csvUploadSubmit.disabled = false;
      this.dom.csvUploadSubmit.textContent = 'Upload Dataset';
    }
  }
}
