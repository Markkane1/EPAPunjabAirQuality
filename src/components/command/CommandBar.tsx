import React from 'react';
import { Activity, AlertTriangle, LayoutGrid, SlidersHorizontal } from '../common/icons';
import { ThemeSwitch } from '../theme-switch';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle, SheetTrigger } from '../ui/sheet';
import { Tabs, TabsList, TabsTrigger } from '../ui/tabs';
import { cn } from '../../lib/utils';
import type { PollutantKey } from '../../domain/types';
import type { HazardousAlert } from '../../workstation/state';
import type { CSVIngestResponse } from '../../services/api';
import { apiService } from '../../services/api';
import { CSVIngestModal } from './CSVIngestModal';

export interface CommandBarProps {
  className?: string;
  title: string;
  subtitle: string;
  stream: 'live' | 'fallback';
  streamLabel: string;
  stationCounter: string;
  pollutant: PollutantKey;
  pollutants: PollutantKey[];
  hazardous: HazardousAlert | null;
  qaLines: string[];
  csvFeedback?: string | null;
  timestamp?: string;
  isGridOpen?: boolean;
  onToggleGrid?: () => void;
  onPollutant?: (key: PollutantKey) => void;
  onIngestFile?: (file: File) => void;
  onUploadCSV?: (file: File, allowMissingCoords: boolean) => Promise<CSVIngestResponse>;
  onIngestSuccess?: (result: CSVIngestResponse) => void;
}

export const CommandBar: React.FC<CommandBarProps> = ({
  className,
  title,
  subtitle,
  stream,
  streamLabel,
  stationCounter,
  pollutant,
  pollutants,
  hazardous,
  qaLines,
  csvFeedback,
  timestamp,
  isGridOpen,
  onToggleGrid,
  onPollutant,
  onIngestFile,
  onUploadCSV,
  onIngestSuccess,
}) => {
  return (
    <header
      id="command-bar"
      data-zone="command-bar"
      className={cn("z-30 flex h-14 shrink-0 items-center justify-between gap-3 border-b border-border bg-background px-4", className)}
    >
      {/* Group 1: System Identity & Stream Status */}
      <div className="flex min-w-0 items-center gap-3" style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-none bg-primary text-primary-foreground" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', width: '32px', height: '32px', flexShrink: 0, marginRight: '4px' }}>
          <Activity size={16} strokeWidth={1.25} />
        </div>
        <div className="min-w-0" style={{ display: 'flex', flexDirection: 'column', marginRight: '12px' }}>
          <span className="block text-sm font-bold leading-none tracking-tight" style={{ fontWeight: 700, fontSize: '13px', lineHeight: 1.2 }}>{title}</span>
          <span className="font-mono text-[11px] text-muted-foreground" style={{ fontSize: '11px', color: 'var(--ink-secondary)', marginTop: '2px' }}>{subtitle}</span>
        </div>
        <div style={{ width: '1px', height: '24px', backgroundColor: 'var(--border-subtle)', margin: '0 8px' }} />
        {stream === 'live' ? (
          <Badge
            variant="outline"
            data-testid="stream-badge"
            className="h-6 gap-1.5 rounded-none border-emerald-500/30 bg-emerald-500/10 px-2 font-mono text-[11px] text-emerald-600 dark:text-emerald-400"
            style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', padding: '0 8px', height: '24px', marginRight: '8px' }}
          >
            <span className="h-1.5 w-1.5 rounded-none bg-emerald-500 animate-pulse" style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: '#10b981', display: 'inline-block' }} />
            {streamLabel}
          </Badge>
        ) : (
          <Badge
            variant="outline"
            data-testid="stream-badge"
            className="h-6 gap-1.5 rounded-none border-amber-500/40 bg-amber-500/10 px-2 font-mono text-[11px] text-amber-600 dark:text-amber-400"
            style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', padding: '0 8px', height: '24px', marginRight: '8px' }}
          >
            <span className="h-1.5 w-1.5 rounded-none bg-amber-500" style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: '#f59e0b', display: 'inline-block' }} />
            {streamLabel}
          </Badge>
        )}
        <Badge variant="secondary" className="h-6 rounded-none font-mono text-[11px] tabular-nums" style={{ display: 'inline-flex', alignItems: 'center', padding: '0 8px', height: '24px', marginRight: '8px' }}>
          {stationCounter}
        </Badge>
        {timestamp ? (
          <Badge
            variant="outline"
            data-testid="simulation-clock"
            className="h-6 rounded-none font-mono text-[11px] tabular-nums text-foreground"
            style={{ display: 'inline-flex', alignItems: 'center', padding: '0 8px', height: '24px' }}
          >
            {timestamp}
          </Badge>
        ) : null}
      </div>

      {/* Group 2: Statutory 9-Pollutant Switcher */}
      <Tabs value={pollutant} onValueChange={(val) => onPollutant?.(val as PollutantKey)}>
        <TabsList
          className="h-9 rounded-none border border-border/50 bg-muted/70 p-1"
          role="radiogroup"
          aria-label="Statutory Pollutant Switcher"
        >
          {pollutants.map((key) => (
            <TabsTrigger
              key={key}
              value={key}
              data-testid={`pollutant-${key}`}
              data-pollutant={key}
              role="radio"
              aria-checked={pollutant === key}
              aria-label={key}
              className="rounded-none px-2.5 py-1 font-mono text-xs font-medium data-[state=active]:bg-background data-[state=active]:text-foreground"
            >
              {key}
            </TabsTrigger>
          ))}
        </TabsList>
      </Tabs>

      {/* Group 3: Assertive ARIA Alert, CSV Ingest, QA Drawer & Theme Switch */}
      <div className="flex items-center gap-2">
        {hazardous ? (
          <Badge
            role={hazardous.role}
            aria-live={hazardous.ariaLive}
            variant="outline"
            className="h-7 gap-1.5 rounded-none border border-red-500/60 bg-red-500/15 px-2.5 font-mono text-xs uppercase tracking-wider text-red-400"
          >
            <AlertTriangle size={14} strokeWidth={1.25} className="text-red-500" />
            {hazardous.text}
          </Badge>
        ) : null}

        {/* Institutional CSV Ingestion Modal with Quarantine Inspector */}
        <CSVIngestModal
          onUpload={async (file, allowMissingCoords) => {
            if (onUploadCSV) {
              return await onUploadCSV(file, allowMissingCoords);
            }
            const res = await apiService.uploadCSV(file, allowMissingCoords);
            onIngestFile?.(file);
            return res;
          }}
          onSuccessMerged={(result) => {
            onIngestSuccess?.(result);
          }}
        />

        {csvFeedback ? (
          <span className="font-mono text-[11px] text-muted-foreground hidden lg:inline">
            {csvFeedback}
          </span>
        ) : null}

        {onToggleGrid ? (
          <Button
            variant="outline"
            size="sm"
            data-testid="toggle-grid-btn"
            className={cn("h-8 gap-1.5 rounded-none text-xs font-medium", isGridOpen && "bg-primary text-primary-foreground")}
            onClick={onToggleGrid}
            aria-label="Toggle 3x3 Multi-Pollutant Grid"
            title="Toggle 3x3 Multi-Pollutant Grid"
          >
            <LayoutGrid size={14} strokeWidth={1.25} />
            <span>3x3 Grid</span>
          </Button>
        ) : null}

        <Sheet>
          <SheetTrigger asChild>
            <Button variant="outline" size="sm" className="h-8 gap-1.5 rounded-none text-xs font-medium">
              <SlidersHorizontal size={14} strokeWidth={1.25} /> QA
            </Button>
          </SheetTrigger>
          <SheetContent className="rounded-none">
            <SheetHeader>
              <SheetTitle>QA & diagnostics</SheetTitle>
              <SheetDescription>
                Temporal QC, completeness, and transport guards for the current receptor.
              </SheetDescription>
            </SheetHeader>
            <ul className="mt-4 space-y-2 font-mono text-xs">
              {qaLines.map((line) => (
                <li key={line} className="rounded-none border border-border px-2 py-1.5">
                  {line}
                </li>
              ))}
            </ul>
          </SheetContent>
        </Sheet>

        <ThemeSwitch />
      </div>
    </header>
  );
};
