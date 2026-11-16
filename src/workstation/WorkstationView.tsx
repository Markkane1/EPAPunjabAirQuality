import { useState, type ReactNode } from 'react';
import { LayoutGrid, Maximize2, ZoomIn, ZoomOut } from '../components/common/icons';
import { ThemeProvider } from '../context/theme-provider';
import { Button } from '../components/ui/button';
import { Card } from '../components/ui/card';
import { CommandBar } from '../components/command/CommandBar';
import { SpatialDock } from '../components/dock/SpatialDock';
import { ReceptorInspector } from '../components/inspector/ReceptorInspector';
import { TimelineScrubber } from '../components/scrubber/TimelineScrubber';
import { MultiPollutantGrid } from '../components/grid/MultiPollutantGrid';
import { cn } from '../lib/utils';
import gridStyles from '../styles/grid.module.css';
import type { LayerId, PollutantKey } from '../domain/types';
import type { PlaybackRate, WorkstationModel } from './state';

export interface WorkstationHandlers {
  onPollutant?: (key: PollutantKey) => void;
  onLayer?: (id: LayerId, checked: boolean) => void;
  onSearch?: (value: string) => void;
  onSelectDistrict?: (id: string) => void;
  onStep?: (delta: -1 | 1) => void;
  onTogglePlay?: () => void;
  onSpeed?: (speed: PlaybackRate) => void;
  onScrub?: (position: number) => void;
  onZoom?: (action: 'in' | 'out' | 'reset') => void;
  onIngestFile?: (file: File) => void;
  csvFeedback?: string | null;
  mapSlot?: ReactNode;
}

export function WorkstationView({
  model,
  onPollutant,
  onLayer,
  onSearch,
  onSelectDistrict,
  onStep,
  onTogglePlay,
  onSpeed,
  onScrub,
  onZoom,
  onIngestFile,
  csvFeedback,
  mapSlot,
}: WorkstationHandlers & { model: WorkstationModel }) {
  const [showGrid, setShowGrid] = useState<boolean>(false);

  return (
    <div className={cn(gridStyles.workstation, "antialiased")}>
      {/* Zone 1: Command Header */}
      <CommandBar
        className={gridStyles.commandBar}
        title={model.title}
        subtitle={model.subtitle}
        stream={model.stream}
        streamLabel={model.streamLabel}
        stationCounter={model.stationCounter}
        timestamp={model.scrubber.timestampLine}
        pollutant={model.pollutant}
        pollutants={model.pollutants}
        hazardous={model.hazardous}
        qaLines={model.qaLines}
        csvFeedback={csvFeedback}
        isGridOpen={showGrid}
        onToggleGrid={() => setShowGrid((v) => !v)}
        onPollutant={onPollutant}
        onIngestFile={onIngestFile}
      />

      {/* Zone 2: Spatial Control Dock */}
      <SpatialDock
        className={gridStyles.spatialDock}
        layers={model.layers}
        activeLayerCount={model.activeLayerCount}
        dimensionGuard={model.dimensionGuard}
        domesticShare={model.domesticShare}
        inflowShare={model.inflowShare}
        activeChevrons={model.activeChevrons}
        search={model.search}
        districts={model.districts}
        selectedDistrictId={model.selected?.kind === 'district' ? model.selected.id : null}
        onLayer={onLayer}
        onSearch={onSearch}
        onSelectDistrict={onSelectDistrict}
      />

      {/* Zone 3: Central Planimetric Map Canvas */}
      <main
        id="map-canvas"
        data-zone="map-canvas"
        className={cn(gridStyles.mapCanvas, "relative h-full min-w-0 overflow-hidden")}
      >
        <div
          className="absolute inset-0"
          data-pitch={model.mapLock.pitch}
          data-map-lock={JSON.stringify(model.mapLock)}
        >
          {mapSlot}
        </div>

        {/* Floating Zoom & Extent HUD */}
        <div className="absolute right-3 top-3 z-10 flex flex-col gap-1 rounded-none border border-border bg-card/90 p-1">
          <Button
            variant="ghost"
            size="icon"
            className={cn("h-7 w-7 rounded-none", showGrid && "bg-primary text-primary-foreground")}
            aria-label="Toggle 3x3 Multi-Pollutant Grid"
            title="Toggle 3x3 Multi-Pollutant Grid"
            onClick={() => setShowGrid((v) => !v)}
          >
            <LayoutGrid size={14} strokeWidth={1.25} />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7 rounded-none"
            aria-label="Zoom in"
            onClick={() => onZoom?.('in')}
          >
            <ZoomIn size={14} strokeWidth={1.25} />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7 rounded-none"
            aria-label="Zoom out"
            onClick={() => onZoom?.('out')}
          >
            <ZoomOut size={14} strokeWidth={1.25} />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7 rounded-none"
            aria-label="Reset to Punjab bounds"
            onClick={() => onZoom?.('reset')}
          >
            <Maximize2 size={14} strokeWidth={1.25} />
          </Button>
        </div>

        {/* 3x3 Multi-Pollutant Comparison Grid Overlay (GAP-UI-01) */}
        {showGrid && (
          <div className="absolute left-3 top-3 z-20 w-[420px] max-w-[calc(100%-6rem)] shadow-lg animate-in fade-in zoom-in-95 duration-100">
            <MultiPollutantGrid
              activePollutant={model.pollutant}
              onSelectPollutant={(p) => {
                onPollutant?.(p);
              }}
            />
          </div>
        )}

        {/* Floating PEPC Statutory Legend */}
        <Card className="absolute bottom-3 left-3 z-10 rounded-none border-border bg-card/95 p-2.5 text-[11px] shadow-none">
          <div className="mb-1 font-mono text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
            PEPC Statutory AQI Scale
          </div>
          {model.legend.map((tier) => (
            <div key={tier.label} className="flex items-center gap-2 font-mono tabular-nums">
              <span className="h-2.5 w-4 rounded-none" style={{ backgroundColor: tier.hex }} />
              <span>{tier.label}</span>
            </div>
          ))}
        </Card>
      </main>

      {/* Zone 4: Receptor Inspector */}
      <ReceptorInspector
        className={gridStyles.receptorInspector}
        entityType={model.entityType}
        entityName={model.entityName}
        latitude={model.latitude}
        longitude={model.longitude}
        compositeAqi={model.compositeAqi}
        compositePaint={model.compositePaint}
        estimated={model.estimated}
        blacklist={model.blacklist}
        windCopy={model.windCopy}
        completeness={model.completeness}
        readings={model.readings}
        sectors={model.sectors}
        p75Threshold={model.p75Threshold}
        calmHours={model.calmHours}
        pooled={model.pooled}
        pooledStationCount={model.pooledStationCount}
        qcSeries={model.qcSeries}
        exportMass={model.exportMass}
        importMass={model.importMass}
      />

      {/* Zone 5: Temporal Playback Scrubber */}
      <TimelineScrubber
        className={gridStyles.temporalScrubber}
        hourIndex={model.hourIndex}
        lerpAlpha={model.lerpAlpha}
        isPlaying={model.isPlaying}
        playbackSpeed={model.playbackSpeed}
        scrubber={model.scrubber}
        horizon={model.horizon}
        onStep={onStep}
        onTogglePlay={onTogglePlay}
        onSpeed={onSpeed}
        onScrub={onScrub}
      />
    </div>
  );
}

export function renderWorkstation(model: WorkstationModel) {
  return (
    <ThemeProvider>
      <WorkstationView model={model} />
    </ThemeProvider>
  );
}
