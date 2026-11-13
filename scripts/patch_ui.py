with open('src/frontend/static/js/ui.js', 'r', encoding='utf-8') as f:
    orig = f.read()

# 1. Update imports
old_import = "import { STATUTORY_LIMITS, PEPC_TIERS, getColorCss, getColorRgb } from './canvas.js';"
new_import = """import {
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
} from './canvas.js';"""

assert old_import in orig
content = orig.replace(old_import, new_import)

# 2. Update switchView
old_switch = """  switchView(viewName) {
    this.dom.deepDivePanels.forEach(p => {
      if (p.id === `panel-${viewName}` || (viewName === 'console' && p.id === 'panel-console')) {
        p.removeAttribute('hidden');
      } else if (viewName !== 'console') {
        p.setAttribute('hidden', '');
      }
    });

    // Notify app if subview canvas needs resize/render
    this.app.onViewSwitched(viewName);
  }"""

new_switch = """  switchView(viewName) {
    this.dom.navTabs.forEach(b => {
      const active = b.dataset.view === viewName;
      b.classList.toggle('active', active);
      b.setAttribute('aria-selected', active ? 'true' : 'false');
    });

    const targetId = viewName === 'console' ? 'panel-console' : `panel-${viewName}`;
    const target = document.getElementById(targetId);
    if (target) {
      target.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    // Notify app if subview canvas needs resize/render
    this.app.onViewSwitched(viewName);
  }"""

assert old_switch in content
content = content.replace(old_switch, new_switch)

# 3. Update renderPollutantButtons to use NOX and active class
old_pollutant_btns = """  renderPollutantButtons(activePollutant) {
    if (!this.dom.pollutantStrip) return;
    this.dom.pollutantStrip.innerHTML = '';

    const list = ['AQI', 'PM2.5', 'PM10', 'NO2', 'SO2', 'CO', 'O3', 'NO', 'NOx'];
    list.forEach((key, idx) => {
      const spec = STATUTORY_LIMITS[key];
      const btn = document.createElement('button');
      btn.className = 'pol-btn';
      btn.type = 'button';
      btn.setAttribute('role', 'radio');
      btn.setAttribute('aria-checked', key === activePollutant ? 'true' : 'false');
      btn.dataset.pollutant = key;

      const limitLabel = spec.scale === 'aqi' ? 'PEPC' : spec.ref ? `${spec.ref}` : 'REF 100';
      btn.innerHTML = `
        <span class="species">${spec.name}</span>
        <span class="limit-badge">${limitLabel}</span>
      `;

      btn.addEventListener('click', () => {
        this.app.selectPollutant(key);
      });

      this.dom.pollutantStrip.appendChild(btn);
    });
  }"""

new_pollutant_btns = """  renderPollutantButtons(activePollutant) {
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
  }"""

assert old_pollutant_btns in content
content = content.replace(old_pollutant_btns, new_pollutant_btns)

# 4. Update updateLegend
old_legend = """  updateLegend(pollutantKey) {
    if (!this.dom.legendColorBar || !this.dom.legendTicks) return;

    const spec = STATUTORY_LIMITS[pollutantKey] || STATUTORY_LIMITS['PM2.5'];
    if (this.dom.legendTitle) {
      this.dom.legendTitle.textContent = `${spec.name} (${spec.unit || 'Index'}) · ${spec.refavg || ''} ${spec.ref || ''}`;
    }

    // Build Continuous Linear Gradient
    const gradientStops = PEPC_TIERS.map((tier, idx) => {
      const pct = Math.round((idx / (PEPC_TIERS.length - 1)) * 100);
      return `rgb(${tier.color.join(',')}) ${pct}%`;
    }).join(', ');

    this.dom.legendColorBar.style.background = `linear-gradient(90deg, ${gradientStops})`;

    // Ticks
    if (pollutantKey === 'AQI') {
      const stops = ['0', '50', '100', '150', '200', '300', '400+'];
      this.dom.legendTicks.innerHTML = stops.map((s, i) => {
        const left = Math.max(3, Math.min(97, (i / (stops.length - 1)) * 100));
        return `<span style="left: ${left}%">${s}</span>`;
      }).join('');
    } else {
      const ref = spec.ref || 100;
      const multipliers = [0, 0.5, 1.0, 1.5, 2.5, 4.0, 6.0];
      this.dom.legendTicks.innerHTML = multipliers.map((m, i) => {
        const val = pollutantKey === 'CO' ? (m * ref).toFixed(1) : Math.round(m * ref);
        const left = Math.max(3, Math.min(97, (i / (multipliers.length - 1)) * 100));
        return `<span style="left: ${left}%">${val}${i === 6 ? '+' : ''}</span>`;
      }).join('');
    }
  }"""

new_legend = """  updateLegend(pollutantKey) {
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
  }"""

assert old_legend in content
content = content.replace(old_legend, new_legend)

# 5. Update renderSelectedDistrictTelemetry
old_telemetry = """  renderSelectedDistrictTelemetry(districtName, readings, activePollutant, rollingMeans = {}) {
    if (this.dom.selectedDistrictTitle) {
      this.dom.selectedDistrictTitle.textContent = districtName;
    }
    if (!this.dom.selectedDistrictTableBody) return;
    this.dom.selectedDistrictTableBody.innerHTML = '';

    const pollutants = ['AQI', 'PM2.5', 'PM10', 'NO2', 'SO2', 'CO', 'O3', 'NO', 'NOx'];
    pollutants.forEach(pol => {
      const spec = STATUTORY_LIMITS[pol];
      const curVal = readings[pol] !== undefined ? readings[pol] : (pol === activePollutant ? readings.current : null);
      // Real rolling 24-h mean if available from series or rollingMeans map
      let periodMean = rollingMeans[pol] !== undefined ? rollingMeans[pol] : (curVal !== null ? (pol === 'CO' ? curVal * 0.94 : Math.round(curVal * 0.94)) : null);
      const ref = spec.ref;
      const exceedRatio = curVal && ref ? (curVal / ref).toFixed(1) : '–';

      const row = document.createElement('tr');
      row.innerHTML = `
        <td><b>${spec.name}</b> <span style="font-size: 10px; color: var(--ink-secondary)">${spec.unit}</span></td>
        <td class="r num" style="color: ${getColorCss(curVal, pol)}">${curVal !== null ? (pol === 'CO' ? curVal.toFixed(2) : Math.round(curVal)) : '~'}</td>
        <td class="r num">${periodMean !== null ? (pol === 'CO' ? Number(periodMean).toFixed(2) : Math.round(periodMean)) : '~'}</td>
        <td class="r num">${ref ? `${ref} (${exceedRatio}x)` : '–'}</td>
      `;
      this.dom.selectedDistrictTableBody.appendChild(row);
    });
  }"""

new_telemetry = """  renderSelectedDistrictTelemetry(districtName, readings, activePollutant, rollingMeans = {}) {
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
  }"""

assert old_telemetry in content
content = content.replace(old_telemetry, new_telemetry)

with open('src/frontend/static/js/ui.js', 'w', encoding='utf-8') as f:
    f.write(content)

print("ui.js patched successfully! New length:", len(content))
