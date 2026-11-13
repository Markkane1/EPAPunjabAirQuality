import React, { useState } from 'react';
import styles from './styles/grid.module.css';
import { PollutantKey, LayerId } from './domain/types';

export const App: React.FC = () => {
  const [activePollutant, setActivePollutant] = useState<PollutantKey>('AQI');
  const [layerVisibility, setLayerVisibility] = useState<Record<LayerId, boolean>>({
    surface: true,
    choropleth: true,
    wind: true,
    flux: true,
    stations: true,
  });

  return (
    <div className={styles.workstation} role="application" aria-label="EPA Punjab Air Quality Institutional Workstation">
      
      {/* Zone 1: Command Bar (Top) */}
      <header className={styles.commandBar} role="banner" aria-label="Workstation Command Bar">
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span
              style={{
                width: '8px',
                height: '8px',
                borderRadius: '0px',
                backgroundColor: 'var(--pulse-live, #00B050)',
                display: 'inline-block',
              }}
              aria-hidden="true"
            />
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', letterSpacing: '0.06em' }}>
              LIVE SYNC: ACTIVE (BASELINE FALLBACK READY)
            </span>
          </div>

          <div style={{ height: '18px', width: '1px', backgroundColor: 'var(--border-subtle, #2a3a38)' }} />

          <h1 style={{ fontSize: '15px', fontWeight: 600, margin: 0, letterSpacing: '0.02em' }}>
            EPA PUNJAB AIR QUALITY WORKSTATION
          </h1>
        </div>

        {/* Assertive ARIA Live Region for Hazardous Alerts / 500 Clamps */}
        <div
          role="status"
          aria-live="assertive"
          aria-atomic="true"
          style={{ fontFamily: 'var(--font-mono)', fontSize: '12px', color: 'var(--pepc-hazardous, #C00000)' }}
        >
          {/* Milestone 4 Alert Banners mount here */}
        </div>

        {/* 9 Statutory Pollutant Switcher Placeholder */}
        <div role="radiogroup" aria-label="Statutory Pollutant Switcher" style={{ display: 'flex', gap: '4px' }}>
          {(['AQI', 'PM2.5', 'PM10', 'NO2', 'SO2', 'CO', 'O3', 'NO', 'NOX'] as PollutantKey[]).map((pol) => (
            <button
              key={pol}
              type="button"
              role="radio"
              aria-checked={activePollutant === pol}
              onClick={() => setActivePollutant(pol)}
              style={{
                fontFamily: 'var(--font-condensed)',
                fontSize: '12px',
                fontWeight: activePollutant === pol ? 600 : 400,
                padding: '4px 8px',
                border: activePollutant === pol ? '1px solid var(--accent, #5fc4c4)' : '1px solid transparent',
                backgroundColor: activePollutant === pol ? 'var(--bg-panel-elevated, #1c2b2a)' : 'transparent',
                color: activePollutant === pol ? 'var(--ink-primary, #e3ece9)' : 'var(--ink-secondary, #c0cfcb)',
                cursor: 'pointer',
              }}
            >
              {pol}
            </button>
          ))}
        </div>
      </header>

      {/* Zone 2: Spatial Control Dock (Left) */}
      <aside className={styles.spatialDock} role="region" aria-label="Spatial Control Dock">
        <div className={styles.panelHeader}>
          <span>Spatial Controls &amp; 41 Districts</span>
        </div>
        <div className={styles.panelBody}>
          {/* Milestone 4 will mount Layer Stack Toggles, Mass-Balance Split Bar, District Ranking Table */}
          <div style={{ fontSize: '12px', color: 'var(--ink-secondary)' }}>
            <div style={{ marginBottom: '8px', fontWeight: 600 }}>ACTIVE DECK.GL LAYERS:</div>
            {(Object.keys(layerVisibility) as LayerId[]).map((layerId) => (
              <label key={layerId} style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                <input
                  type="checkbox"
                  checked={layerVisibility[layerId]}
                  onChange={(e) => setLayerVisibility({ ...layerVisibility, [layerId]: e.target.checked })}
                />
                <span style={{ textTransform: 'capitalize' }}>{layerId}</span>
              </label>
            ))}
          </div>
        </div>
      </aside>

      {/* Zone 3: Central Planimetric Map Canvas (Center) */}
      <main className={styles.mapCanvas} role="main" aria-label="Planimetric Atmospheric Map Viewport">
        <div
          id="mapLibreCanvas"
          style={{ width: '100%', height: '100%', position: 'absolute', top: 0, left: 0 }}
        >
          {/* Milestone 3 will mount strictly locked MapLibre GL instance (pitch: 0, dragRotate: false) */}
        </div>
        <div
          id="deckOverlay"
          style={{ width: '100%', height: '100%', position: 'absolute', top: 0, left: 0, pointerEvents: 'none' }}
        >
          {/* Milestone 3 will mount interleaved Deck.gl 5-layer MapboxOverlay */}
        </div>
      </main>

      {/* Zone 4: Receptor Inspector (Right) */}
      <aside className={styles.receptorInspector} role="complementary" aria-label="Receptor Inspector">
        <div className={styles.panelHeader}>
          <span>Receptor Telemetry &amp; Diagnostics</span>
        </div>
        <div className={styles.panelBody}>
          {/* Milestone 4 will mount 9-parameter sub-index table, 16-sector CPF rose, 216h QC sparkline */}
          <div style={{ fontSize: '12px', color: 'var(--ink-secondary)' }}>
            Select a station or district on the map or spatial dock to inspect detailed receptor telemetry and polar wind rose.
          </div>
        </div>
      </aside>

      {/* Zone 5: Temporal Playback Scrubber (Bottom) */}
      <footer className={styles.temporalScrubber} role="contentinfo" aria-label="Temporal Playback Controller">
        <div style={{ display: 'flex', alignItems: 'center', width: '100%', gap: '16px' }}>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: '12px', minWidth: '160px' }}>
            PKT: 2026-11-01 00:00
          </span>
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '4px' }}>
            {/* Scrubber slider and horizon sparkline placeholder */}
            <input
              type="range"
              min="0"
              max="215"
              defaultValue="0"
              style={{ width: '100%', accentColor: 'var(--accent, #5fc4c4)' }}
              aria-label="216-Hour Simulation Timeline Scrubber"
            />
          </div>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: '12px' }}>
            HOUR: 0 / 215
          </span>
        </div>
      </footer>

    </div>
  );
};
