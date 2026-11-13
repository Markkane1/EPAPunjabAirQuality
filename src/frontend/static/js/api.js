/**
 * Client-Side API & Offline Fallback Engine.
 * Connects to FastAPI /api/v1/ endpoints, handles SSE live streaming with keepalive,
 * provides CSV file ingestion with quarantine inspector, and falls back to baseline JSON files.
 */

export class ApiClient {
  constructor(baseUrl = '') {
    this.baseUrl = baseUrl;
    this.mode = 'live'; // 'live', 'fallback', or 'user_csv'
    this.eventSource = null;
    this.watchdogTimer = null;
    this.watchdogTimeoutMs = 45000;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.cachedBaselineData = null;
    this.cachedGeoData = null;
  }

  // =========================================================================
  // METADATA & REPOSITORY ENDPOINTS
  // =========================================================================

  async getDistrictsMeta() {
    try {
      const resp = await fetch(`${this.baseUrl}/api/v1/meta/districts`);
      if (resp.ok) return await resp.json();
    } catch (err) {
      console.warn('API getDistrictsMeta offline, loading fallback:', err);
    }
    return this.loadFallbackDistricts();
  }

  async getStationsMeta() {
    try {
      const resp = await fetch(`${this.baseUrl}/api/v1/meta/stations`);
      if (resp.ok) return await resp.json();
    } catch (err) {
      console.warn('API getStationsMeta offline, loading fallback:', err);
    }
    return this.loadFallbackStations();
  }

  async getGeoBoundaries() {
    if (this.cachedGeoData) return this.cachedGeoData;
    try {
      const resp = await fetch(`${this.baseUrl}/static/data/geo_boundaries.json`);
      if (resp.ok) {
        this.cachedGeoData = await resp.json();
        return this.cachedGeoData;
      }
    } catch (err) {
      console.error('Failed to load geo_boundaries.json:', err);
    }
    return { GEO: {}, IND: {} };
  }

  // =========================================================================
  // OBSERVATION ENDPOINTS
  // =========================================================================

  async getCurrentObservations(pollutant = 'AQI', district = null) {
    try {
      const params = new URLSearchParams({ pollutant });
      if (district) params.append('district', district);
      const resp = await fetch(`${this.baseUrl}/api/v1/observations/current?${params}`);
      if (resp.ok) return await resp.json();
    } catch (err) {
      console.warn('API getCurrentObservations offline, using fallback:', err);
    }
    return this.getFallbackCurrent(pollutant, district);
  }

  async getHourlyObservations(pollutant = 'AQI', district = null) {
    try {
      const params = new URLSearchParams({ pollutant });
      if (district) params.append('district', district);
      const resp = await fetch(`${this.baseUrl}/api/v1/observations/hourly?${params}`);
      if (resp.ok) return await resp.json();
    } catch (err) {
      console.warn('API getHourlyObservations offline, using fallback:', err);
    }
    return this.getFallbackHourly(pollutant, district);
  }

  // =========================================================================
  // ANALYTICS & SPATIAL ENDPOINTS
  // =========================================================================

  async getCPFRose(district = 'Lahore', pollutant = 'PM2.5') {
    try {
      const params = new URLSearchParams({
        district: district,
        district_name: district,
        pollutant: pollutant,
      });
      const resp = await fetch(`${this.baseUrl}/api/v1/analytics/cpf?${params}`);
      if (resp.ok) return await resp.json();
    } catch (err) {
      console.warn('API getCPFRose offline, using fallback:', err);
    }
    return this.getFallbackCPF(district, pollutant);
  }

  async getFluxTransport(pollutant = 'PM2.5', limit = 60) {
    // Physical Invariant Guard: Mass flux is strictly undefined for AQI
    if (pollutant === 'AQI') {
      console.warn('Advection flux is physically undefined for AQI. Defaulting to PM2.5.');
      pollutant = 'PM2.5';
    }

    try {
      const params = new URLSearchParams({ pollutant, limit: String(limit) });
      const resp = await fetch(`${this.baseUrl}/api/v1/analytics/flux?${params}`);
      if (resp.ok) return await resp.json();
    } catch (err) {
      console.warn('API getFluxTransport offline, using fallback:', err);
    }
    return this.getFallbackFlux(pollutant);
  }

  async getTransboundary(pollutant = 'PM2.5') {
    try {
      const params = new URLSearchParams({ pollutant });
      const resp = await fetch(`${this.baseUrl}/api/v1/analytics/transboundary?${params}`);
      if (resp.ok) return await resp.json();
    } catch (err) {
      console.warn('API getTransboundary offline, using fallback:', err);
    }
    return this.getFallbackTransboundary(pollutant);
  }

  async getCrossBorderCities() {
    try {
      const resp = await fetch(`${this.baseUrl}/api/v1/observations/cross-border`);
      if (resp.ok) {
        const j = await resp.json();
        return j.cities || [];
      }
    } catch (err) {
      console.warn('API getCrossBorderCities offline:', err);
    }
    return [
      { city: 'Amritsar', distance_km: 28, us_aqi: 185, pepc_aqi: 185, status: 'Unhealthy' },
      { city: 'Firozpur', distance_km: 12, us_aqi: 178, pepc_aqi: 178, status: 'Unhealthy' },
      { city: 'Jalandhar', distance_km: 82, us_aqi: 240, pepc_aqi: 240, status: 'Very Unhealthy' },
      { city: 'Ludhiana', distance_km: 125, us_aqi: 265, pepc_aqi: 265, status: 'Very Unhealthy' },
      { city: 'Delhi NCR', distance_km: 360, us_aqi: 385, pepc_aqi: 385, status: 'Hazardous' },
    ];
  }

  async getRollingMean(entityType = 'district', entityId = 'Lahore', pollutant = 'PM2.5') {
    try {
      const params = new URLSearchParams({ entity_type: entityType, entity_id: entityId, pollutant });
      const resp = await fetch(`${this.baseUrl}/api/v1/observations/rolling-mean?${params}`);
      if (resp.ok) {
        const j = await resp.json();
        return j.rolling_24h_mean;
      }
    } catch (err) {
      console.warn('API getRollingMean offline:', err);
    }
    return null;
  }

  async getActiveFires() {
    try {
      const resp = await fetch(`${this.baseUrl}/api/v1/observations/fires`);
      if (resp.ok) {
        const data = await resp.json();
        return data.fires || [];
      }
    } catch (err) {
      console.warn('API getActiveFires offline:', err);
    }
    return [];
  }

  async triggerTick(mode = null) {
    try {
      const url = mode ? `${this.baseUrl}/api/v1/stream/tick?mode=${encodeURIComponent(mode)}` : `${this.baseUrl}/api/v1/stream/tick`;
      const resp = await fetch(url, { method: 'POST' });
      if (resp.ok) return await resp.json();
    } catch (err) {
      console.error('Failed to trigger tick:', err);
    }
    return null;
  }

  async setStreamMode(mode) {
    try {
      const resp = await fetch(`${this.baseUrl}/api/v1/stream/mode`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode })
      });
      if (resp.ok) return await resp.json();
    } catch (err) {
      console.error('Failed to set stream mode:', err);
    }
    return null;
  }

  async getStreamStatus() {
    try {
      const resp = await fetch(`${this.baseUrl}/api/v1/stream/status`);
      if (resp.ok) return await resp.json();
    } catch (err) {
      console.warn('Failed to get stream status:', err);
    }
    return null;
  }

  // =========================================================================
  // EPA PUNJAB LIVE AQMS METHODS
  // =========================================================================

  async getEPALatest(forceRefresh = false) {
    try {
      const params = new URLSearchParams();
      if (forceRefresh) params.append('force_refresh', 'true');
      const resp = await fetch(`${this.baseUrl}/api/v1/epa/latest?${params}`);
      if (resp.ok) return await resp.json();
    } catch (err) {
      console.warn('Failed to fetch EPA latest telemetry:', err);
    }
    return null;
  }

  async getEPADaily(stationId = null) {
    try {
      const params = new URLSearchParams();
      if (stationId) params.append('station_id', stationId);
      const resp = await fetch(`${this.baseUrl}/api/v1/epa/daily?${params}`);
      if (resp.ok) return await resp.json();
    } catch (err) {
      console.warn('Failed to fetch EPA daily series:', err);
    }
    return null;
  }

  async getEPAPeriodic(stationId, startDatetime, endDatetime, interval = '60') {
    try {
      const params = new URLSearchParams({
        station_id: stationId,
        start_datetime: startDatetime,
        end_datetime: endDatetime,
        interval: String(interval),
      });
      const resp = await fetch(`${this.baseUrl}/api/v1/epa/periodic?${params}`);
      if (resp.ok) return await resp.json();
    } catch (err) {
      console.warn('Failed to fetch EPA periodic data:', err);
    }
    return null;
  }

  async getEPAAlerts(limit = 100, code = null) {
    try {
      const params = new URLSearchParams({ limit: String(limit) });
      if (code) params.append('code', code);
      const resp = await fetch(`${this.baseUrl}/api/v1/epa/alerts?${params}`);
      if (resp.ok) return await resp.json();
    } catch (err) {
      console.warn('Failed to fetch EPA operational alerts:', err);
    }
    return null;
  }

  async getEPAStations() {
    try {
      const resp = await fetch(`${this.baseUrl}/api/v1/epa/stations`);
      if (resp.ok) return await resp.json();
    } catch (err) {
      console.warn('Failed to fetch EPA stations list:', err);
    }
    return null;
  }

  async getEPAStatus() {
    try {
      const resp = await fetch(`${this.baseUrl}/api/v1/epa/status`);
      if (resp.ok) return await resp.json();
    } catch (err) {
      console.warn('Failed to check EPA API health:', err);
    }
    return null;
  }

  // =========================================================================
  // SSE LIVE STREAMING WITH 45S WATCHDOG & JITTERED RECONNECTION
  // =========================================================================

  resetWatchdog(onStatusChange) {
    this.clearWatchdog();
    const timeoutMs = this.watchdogTimeoutMs || 45000;
    this.watchdogTimer = setTimeout(() => {
      console.warn('SSE Watchdog: 45s connection silence detected. Triggering reconnection...');
      if (this.eventSource) {
        this.eventSource.close();
        this.eventSource = null;
      }
      this.mode = 'fallback';
      if (onStatusChange) onStatusChange('fallback');
      this.handleReconnect(onStatusChange);
    }, timeoutMs);
  }

  clearWatchdog() {
    if (this.watchdogTimer) {
      clearTimeout(this.watchdogTimer);
      this.watchdogTimer = null;
    }
  }

  handleReconnect(onStatusChange) {
    this.reconnectAttempts++;
    // Randomized exponential backoff with full jitter to eliminate thundering herd storms
    const attemptExp = Math.min(this.reconnectAttempts, 10);
    const base = Math.min(30000, 2000 * Math.pow(1.5, attemptExp));
    const timeout = base * (0.5 + Math.random() * 0.5);
    setTimeout(() => this.connectLiveStream(this._onHourlyUpdate, this._onError, onStatusChange), timeout);
  }

  disconnectLiveStream() {
    this.clearWatchdog();
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
    this.mode = 'fallback';
  }

  connectLiveStream(onHourlyUpdate, onError, onStatusChange) {
    this.clearWatchdog();
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
    this._onHourlyUpdate = onHourlyUpdate;
    this._onError = onError;

    const url = `${this.baseUrl}/api/v1/stream/live`;
    try {
      this.eventSource = new EventSource(url);

      this.eventSource.onopen = () => {
        this.reconnectAttempts = 0;
        this.mode = 'live';
        if (onStatusChange) onStatusChange('live');
        this.resetWatchdog(onStatusChange);
      };

      this.eventSource.addEventListener('hourly_update', (event) => {
        this.resetWatchdog(onStatusChange);
        try {
          const payload = JSON.parse(event.data);
          if (onHourlyUpdate) onHourlyUpdate(payload);
        } catch (err) {
          console.error('Failed to parse SSE payload:', err);
        }
      });

      this.eventSource.addEventListener('keepalive', () => {
        this.resetWatchdog(onStatusChange);
      });

      this.eventSource.addEventListener('ping', () => {
        this.resetWatchdog(onStatusChange);
      });

      this.eventSource.onmessage = () => {
        this.resetWatchdog(onStatusChange);
      };

      this.eventSource.onerror = (err) => {
        console.warn('SSE connection dropped, backing off...', err);
        this.clearWatchdog();
        if (this.eventSource) {
          this.eventSource.close();
          this.eventSource = null;
        }
        this.mode = 'fallback';
        if (onStatusChange) onStatusChange('fallback');
        if (onError) onError(err);

        this.handleReconnect(onStatusChange);
      };
    } catch (err) {
      console.warn('SSE EventSource initialization failed:', err);
      this.clearWatchdog();
      this.mode = 'fallback';
      if (onStatusChange) onStatusChange('fallback');
      this.handleReconnect(onStatusChange);
    }
  }

  // =========================================================================
  // CUSTOM CSV DATASET INGESTION
  // =========================================================================

  async uploadCSV(file, allowMissingCoords = false) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('allow_missing_coords', allowMissingCoords ? 'true' : 'false');

    const resp = await fetch(`${this.baseUrl}/api/v1/ingest/csv`, {
      method: 'POST',
      body: formData,
    });

    const result = await resp.json();
    if (!resp.ok) {
      throw new Error(result.detail || result.message || 'CSV Ingestion Failed');
    }
    if (result.valid_rows > 0 && result.status !== 'failed') {
      this.mode = 'user_csv';
    }
    return result;
  }

  // =========================================================================
  // OFFLINE FALLBACK ENGINE
  // =========================================================================

  async loadBaselineData() {
    if (this.cachedBaselineData) return this.cachedBaselineData;
    try {
      const resp = await fetch(`${this.baseUrl}/static/data/baseline_data.json`);
      if (resp.ok) {
        this.cachedBaselineData = await resp.json();
        return this.cachedBaselineData;
      }
    } catch (err) {
      console.error('Failed to load baseline_data.json:', err);
    }
    return null;
  }

  async loadFallbackDistricts() {
    try {
      const resp = await fetch(`${this.baseUrl}/static/data/districts.json`);
      if (resp.ok) return await resp.json();
    } catch (err) {
      console.warn('Fallback districts fetch failed:', err);
    }
    return [];
  }

  async loadFallbackStations() {
    try {
      const resp = await fetch(`${this.baseUrl}/static/data/stations.json`);
      if (resp.ok) return await resp.json();
    } catch (err) {
      console.warn('Fallback stations fetch failed:', err);
    }
    return [];
  }

  async getFallbackCurrent(pollutant = 'AQI', district = null) {
    const baseline = await this.loadBaselineData();
    if (!baseline) return null;

    const hourIdx = 23; // default anchor hour
    const polData = baseline.pol[pollutant] || baseline.pol['PM2.5'];
    const frame = polData.frames[hourIdx] || polData.frames[0];
    const winds = baseline.wind[hourIdx] || {};

    const districts = {};
    for (const [name, val] of Object.entries(frame.c)) {
      const w = winds[name] || [0, 0];
      districts[name] = {
        district: name,
        value: val,
        u: w[0],
        v: w[1],
        wind_speed: Math.hypot(w[0] || 0, w[1] || 0),
        is_estimated: !baseline.districts[name] || !!baseline.districts[name].est,
      };
    }

    return {
      timestamp: baseline.hours[hourIdx],
      hour_index: hourIdx,
      pollutant,
      provincial_summary: {
        mean_aqi: 284.5,
        exceedance_peqs_count: 38,
        peak_district: 'Lahore',
        peak_aqi: 492.0,
        total_districts: 41,
      },
      districts,
      airports: baseline.airports || [],
    };
  }

  async getFallbackHourly(pollutant = 'AQI', district = null) {
    const baseline = await this.loadBaselineData();
    if (!baseline) return null;

    const polData = baseline.pol[pollutant] || baseline.pol['PM2.5'];
    const totalHours = baseline.hours.length;
    const districts = {};

    for (const dName of Object.keys(baseline.districts)) {
      const concs = polData.frames.map(f => f.c[dName] !== undefined ? f.c[dName] : null);
      const windU = baseline.wind.map(w => w[dName] ? w[dName][0] : null);
      const windV = baseline.wind.map(w => w[dName] ? w[dName][1] : null);
      districts[dName] = {
        concentrations: concs,
        wind_u: windU,
        wind_v: windV,
        is_estimated: !!baseline.districts[dName].est,
      };
    }

    return {
      pollutant,
      hours: baseline.hours,
      total_hours: totalHours,
      districts,
    };
  }

  async getFallbackCPF(district = 'Lahore', pollutant = 'PM2.5') {
    const baseline = await this.loadBaselineData();
    if (!baseline) return null;

    const polData = baseline.pol[pollutant] || baseline.pol['PM2.5'];
    const cpfEntry = (polData.cpf && polData.cpf[district]) || {
      tau: 120,
      calm: 0.12,
      sectors: Array.from({ length: 16 }, (_, i) => ({
        sector: i,
        azimuth: i * 22.5,
        label: ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW'][i],
        cpf: 0.15 + (i >= 2 && i <= 6 ? 0.35 : 0.05),
        count: 24,
      })),
    };

    return {
      district,
      pollutant,
      threshold_p75: cpfEntry.tau || 120,
      calm_fraction: cpfEntry.calm || 0.12,
      null_hypothesis_baseline: 0.25,
      sectors: (cpfEntry.sectors || []).map(s => ({
        sector_index: s.sector,
        azimuth_deg: s.azimuth || s.sector * 22.5,
        direction_label: s.label || '',
        total_hours: s.count || 24,
        exceedance_hours: Math.round((s.count || 24) * (s.cpf || 0.25)),
        cpf_probability: s.cpf !== undefined ? s.cpf : 0.25,
      })),
    };
  }

  async getFallbackFlux(pollutant = 'PM2.5') {
    const baseline = await this.loadBaselineData();
    if (!baseline) return { top_pathways: [], total_links: 0 };

    const polData = baseline.pol[pollutant] || baseline.pol['PM2.5'];
    const links = (polData.links || []).map(l => ({
      source_district: l.src,
      receptor_district: l.rcv,
      distance_km: l.km,
      bearing_deg: 0,
      flux: l.flux,
      score: l.score,
    }));

    return {
      pollutant,
      top_pathways: links,
      total_links: links.length,
    };
  }

  async getFallbackTransboundary(pollutant = 'PM2.5') {
    const baseline = await this.loadBaselineData();
    if (!baseline || !baseline.tbgeo) return null;

    return {
      inflow_total: 482.3,
      outflow_total: 124.6,
      net_transboundary_flux: 357.7,
      status: 'NET_INFLOW_ALERT',
      border_samples: (baseline.tbgeo.samples || []).map(s => ({
        longitude: s[0],
        latitude: s[1],
        normal_x: s[2],
        normal_y: s[3],
        normal_flux: 15.4,
      })),
    };
  }
}
