import React, { useEffect, useState, useRef, useMemo } from 'react';
import { loadBaseline, type BaselineFile } from './workstation/loadBaseline';
import {
  assemble,
  selectionFromStation,
  selectionFromAirport,
  type UiState,
} from './workstation/assemble';
import { WorkstationView } from './workstation/WorkstationView';
import { MapCanvas, type MapHandle } from './map/MapCanvas';
import {
  normalizeDistrict,
  normalizeStation,
  normalizeAirport,
} from './domain/normalizer/dataNormalizer';
import type {
  LayerId,
  PollutantKey,
  NormalizedDistrict,
  NormalizedStation,
  AirportStation,
  SelectedEntity,
} from './domain/types';
import type { PlaybackRate } from './workstation/state';
import { ThemeProvider } from './context/theme-provider';

export const App: React.FC = () => {
  const [baseline, setBaseline] = useState<BaselineFile | null>(null);
  const [loadingError, setLoadingError] = useState<string | null>(null);

  const [ui, setUi] = useState<UiState>({
    pollutant: 'AQI',
    layers: {
      surface: true,
      choropleth: true,
      wind: true,
      flux: true,
      stations: true,
    },
    search: '',
    selected: null,
    hourIndex: 0,
    lerpAlpha: 0,
    playbackSpeed: '1x',
    isPlaying: false,
    stream: 'live',
  });

  const mapRef = useRef<MapHandle>(null);

  useEffect(() => {
    loadBaseline()
      .then((data) => {
        setBaseline(data);
      })
      .catch((err) => {
        console.error('Failed to load baseline data:', err);
        setLoadingError(err.message || 'Failed to load baseline data');
      });
  }, []);

  // Pre-normalize spatial topology
  const normalizedDistricts = useMemo<NormalizedDistrict[]>(() => {
    if (!baseline) return [];
    return Object.values(baseline.districts).map((d) => normalizeDistrict(d as any));
  }, [baseline]);

  const normalizedStations = useMemo<NormalizedStation[]>(() => {
    if (!baseline) return [];
    return baseline.stations.map((s) => normalizeStation(s as any));
  }, [baseline]);

  const normalizedAirports = useMemo<AirportStation[]>(() => {
    if (!baseline) return [];
    return baseline.airports.map((a) => normalizeAirport(a));
  }, [baseline]);

  // Dynamic playback timer
  useEffect(() => {
    if (!ui.isPlaying || !baseline) return;
    const numericSpeed = parseFloat(ui.playbackSpeed) || 1;
    const intervalMs = Math.max(100, Math.round(1000 / numericSpeed));
    const timer = setInterval(() => {
      setUi((prev) => {
        const total = baseline.hours?.length || 216;
        const nextHour = (prev.hourIndex + 1) % total;
        return { ...prev, hourIndex: nextHour };
      });
    }, intervalMs);
    return () => clearInterval(timer);
  }, [ui.isPlaying, ui.playbackSpeed, baseline]);

  // Assemble workstation model
  const assembled = useMemo(() => {
    if (!baseline) return null;
    return assemble(baseline, ui);
  }, [baseline, ui]);

  // Prepare map data props for MapCanvas
  const mapProps = useMemo(() => {
    if (!baseline) return null;
    const hour = Math.min(baseline.hours.length - 1, Math.max(0, ui.hourIndex));
    const activeBlock = baseline.pol[ui.pollutant];
    const pmBlock = baseline.pol['PM2.5'];

    const districtValues: Record<string, number | null> = {};
    const pm25Values: Record<string, number | null> = {};
    for (const d of normalizedDistricts) {
      const val = activeBlock?.frames?.[hour]?.c?.[d.name];
      districtValues[d.name] = typeof val === 'number' && Number.isFinite(val) ? val : null;
      districtValues[d.id] = districtValues[d.name];

      const pm = pmBlock?.frames?.[hour]?.c?.[d.name];
      pm25Values[d.name] = typeof pm === 'number' && Number.isFinite(pm) ? pm : null;
      pm25Values[d.id] = pm25Values[d.name];
    }

    const stationValues: Record<string, number | null> = {};
    for (const s of normalizedStations) {
      const series = activeBlock?.stations?.[s.name];
      const val = series?.[hour];
      stationValues[s.name] = typeof val === 'number' && Number.isFinite(val) ? val : null;
      if (s.id) stationValues[s.id] = stationValues[s.name];
    }

    const windHour = baseline.wind[hour] ?? {};
    const districtWinds: Record<string, [number, number]> = {};
    for (const [k, v] of Object.entries(windHour)) {
      if (Array.isArray(v) && v.length >= 2) {
        districtWinds[k] = [v[0], v[1]];
      }
    }

    const airportWinds: Record<string, [number, number]> = {};
    for (const a of baseline.airports) {
      const u = a.u?.[hour];
      const v = a.v?.[hour];
      if (typeof u === 'number' && typeof v === 'number') {
        airportWinds[a.icao ?? a.id ?? ''] = [u, v];
      }
    }

    return {
      districts: normalizedDistricts,
      stations: normalizedStations,
      airports: normalizedAirports,
      borderSamples: baseline.tbgeo?.samples ?? [],
      districtValues,
      stationValues,
      pm25Values,
      districtWinds,
      airportWinds,
      pollutant: ui.pollutant,
      layers: ui.layers,
      hourIndex: ui.hourIndex,
      lerpAlpha: ui.lerpAlpha,
    };
  }, [baseline, ui.hourIndex, ui.pollutant, ui.layers, ui.lerpAlpha, normalizedDistricts, normalizedStations, normalizedAirports]);

  // Handlers
  const handlePollutant = (key: PollutantKey) => setUi((prev) => ({ ...prev, pollutant: key }));
  const handleLayer = (id: LayerId, checked: boolean) =>
    setUi((prev) => ({ ...prev, layers: { ...prev.layers, [id]: checked } }));
  const handleSearch = (s: string) => setUi((prev) => ({ ...prev, search: s }));
  const handleSelectDistrict = (id: string) => {
    if (!baseline) return;
    const dist =
      baseline.districts[id] ||
      Object.values(baseline.districts).find((d) => d.name === id || String(d.id) === id);
    if (dist) {
      setUi((prev) => ({
        ...prev,
        selected: {
          kind: 'district',
          id: dist.name,
          name: dist.name,
          latitude: dist.latitude ?? 31.549,
          longitude: dist.longitude ?? 74.364,
        },
      }));
      mapRef.current?.flyTo([dist.longitude ?? 74.364, dist.latitude ?? 31.549], 8.5);
    }
  };

  const handleStep = (delta: -1 | 1) => {
    if (!baseline) return;
    const total = baseline.hours?.length || 216;
    setUi((prev) => ({ ...prev, hourIndex: (prev.hourIndex + delta + total) % total }));
  };

  const handleTogglePlay = () => setUi((prev) => ({ ...prev, isPlaying: !prev.isPlaying }));
  const handleSpeed = (speed: PlaybackRate) => setUi((prev) => ({ ...prev, playbackSpeed: speed }));
  const handleScrub = (pos: number) => {
    if (!baseline) return;
    const total = baseline.hours?.length || 216;
    setUi((prev) => ({ ...prev, hourIndex: Math.max(0, Math.min(total - 1, Math.round(pos))) }));
  };

  const handleZoom = (action: 'in' | 'out' | 'reset') => {
    if (action === 'in') mapRef.current?.zoomIn();
    else if (action === 'out') mapRef.current?.zoomOut();
    else mapRef.current?.reset();
  };

  const handleMapSelect = (entity: { kind: 'district' | 'station' | 'airport'; id: string; name: string }) => {
    if (!baseline) return;
    if (entity.kind === 'district') {
      handleSelectDistrict(entity.name);
    } else if (entity.kind === 'station') {
      const st = baseline.stations.find((s) => s.id === entity.id || s.name === entity.name);
      if (st) {
        setUi((prev) => ({
          ...prev,
          selected: selectionFromStation(st),
        }));
      }
    } else if (entity.kind === 'airport') {
      const ap = baseline.airports.find((a) => (a.icao ?? a.id) === entity.id);
      if (ap) {
        setUi((prev) => ({
          ...prev,
          selected: selectionFromAirport(ap),
        }));
      }
    }
  };

  if (loadingError) {
    return (
      <div style={{ display: 'flex', height: '100vh', width: '100vw', alignItems: 'center', justifyContent: 'center', backgroundColor: '#0f1716', color: '#C00000', fontFamily: 'monospace' }}>
        <div>Error loading baseline telemetry: {loadingError}</div>
      </div>
    );
  }

  if (!baseline || !assembled || !mapProps) {
    return (
      <div style={{ display: 'flex', height: '100vh', width: '100vw', alignItems: 'center', justifyContent: 'center', backgroundColor: '#0f1716', color: '#00B050', fontFamily: 'monospace' }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '16px', fontWeight: 600, marginBottom: '6px' }}>EPA PUNJAB AIR QUALITY WORKSTATION</div>
          <div style={{ fontSize: '11px', color: '#c0cfcb' }}>INITIALIZING AIRSHED BASELINE TELEMETRY...</div>
        </div>
      </div>
    );
  }

  const selectedEntity: SelectedEntity = ui.selected
    ? ui.selected.kind === 'airport'
      ? { type: 'airport', id: ui.selected.id, icao: ui.selected.name }
      : { type: ui.selected.kind, id: ui.selected.id, name: ui.selected.name }
    : null;

  const mapSlot = (
    <MapCanvas
      ref={mapRef}
      districts={mapProps.districts}
      stations={mapProps.stations}
      airports={mapProps.airports}
      borderSamples={mapProps.borderSamples}
      districtValues={mapProps.districtValues}
      stationValues={mapProps.stationValues}
      pm25Values={mapProps.pm25Values}
      districtWinds={mapProps.districtWinds}
      airportWinds={mapProps.airportWinds}
      pollutant={mapProps.pollutant}
      layers={mapProps.layers}
      selectedEntity={selectedEntity}
      onSelect={handleMapSelect}
      hourIndex={mapProps.hourIndex}
      lerpAlpha={mapProps.lerpAlpha}
    />
  );

  return (
    <ThemeProvider>
      <WorkstationView
        model={assembled.model}
        onPollutant={handlePollutant}
        onLayer={handleLayer}
        onSearch={handleSearch}
        onSelectDistrict={handleSelectDistrict}
        onStep={handleStep}
        onTogglePlay={handleTogglePlay}
        onSpeed={handleSpeed}
        onScrub={handleScrub}
        onZoom={handleZoom}
        mapSlot={mapSlot}
      />
    </ThemeProvider>
  );
};
