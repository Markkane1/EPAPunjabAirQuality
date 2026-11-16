import React from 'react';
import { AlertOctagon } from '../common/icons';
import { Badge } from '../ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { ScrollArea } from '../ui/scroll-area';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import { cn } from '../../lib/utils';
import { cpfSectorVisible, type WorkstationModel } from '../../workstation/state';

export interface ReceptorInspectorProps {
  className?: string;
  entityType: string;
  entityName: string;
  latitude: number;
  longitude: number;
  compositeAqi: number | null;
  compositePaint: { hex: string; text: string; label: string };
  estimated: boolean;
  blacklist: string | null;
  windCopy: string;
  completeness: { meets: boolean; label: string; pct: number };
  readings: WorkstationModel['readings'];
  sectors: WorkstationModel['sectors'];
  p75Threshold: number;
  calmHours: number;
  pooled: boolean;
  pooledStationCount: number;
  qcSeries: WorkstationModel['qcSeries'];
  exportMass: number;
  importMass: number;
}

function CpfRose({ sectors }: { sectors: WorkstationModel['sectors'] }) {
  const cx = 92;
  const cy = 92;
  const radius = 72;
  return (
    <svg viewBox="0 0 184 184" className="h-44 w-44" role="img" aria-label="16-sector CPF polar rose">
      {/* Concentric rings: 0.25 null hypothesis circle, 0.5, 0.75, 1.0 */}
      {[0.25, 0.5, 0.75, 1].map((scale) => (
        <circle
          key={scale}
          cx={cx}
          cy={cy}
          r={radius * scale}
          className="fill-none stroke-border"
          strokeDasharray={scale === 0.25 ? '2 2' : undefined}
          strokeWidth={scale === 0.25 ? 1.25 : 1}
        />
      ))}
      {/* 16 Directional Sectors (22.5 deg intervals) */}
      {sectors.map((sector) => {
        const visible = cpfSectorVisible(sector);
        const magnitude = visible ? sector.cpfProbability ?? 0 : 0.12;
        const start = ((sector.azimuthDeg - 11.25 - 90) * Math.PI) / 180;
        const end = ((sector.azimuthDeg + 11.25 - 90) * Math.PI) / 180;
        const outer = radius * Math.max(0.08, magnitude);
        const x1 = cx + Math.cos(start) * outer;
        const y1 = cy + Math.sin(start) * outer;
        const x2 = cx + Math.cos(end) * outer;
        const y2 = cy + Math.sin(end) * outer;
        const d = `M ${cx} ${cy} L ${x1} ${y1} A ${outer} ${outer} 0 0 1 ${x2} ${y2} Z`;
        return (
          <path
            key={sector.sectorIndex}
            d={d}
            className={visible ? 'fill-primary/25 stroke-primary' : 'fill-transparent stroke-muted-foreground'}
            strokeDasharray={visible ? undefined : '3 3'}
            strokeWidth={1}
          />
        );
      })}
    </svg>
  );
}

function QcSparkline({ marks }: { marks: WorkstationModel['qcSeries'] }) {
  const values = marks.map((m) => m.value);
  const finite = values.filter((v): v is number => v !== null);
  if (finite.length < 2) {
    return <div className="font-mono text-[10px] text-muted-foreground">No telemetry in this window.</div>;
  }
  const max = Math.max(...finite);
  const min = Math.min(...finite);
  const span = max - min || 1;
  const width = 320;
  const height = 64;
  const step = width / Math.max(1, marks.length - 1);
  const y = (val: number) => height - ((val - min) / span) * (height - 8) - 4;
  const line = marks
    .map((mark, index) => (mark.value === null ? null : `${index === 0 ? 'M' : 'L'} ${index * step} ${y(mark.value)}`))
    .filter(Boolean)
    .join(' ');
  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="h-16 w-full" aria-label="216-Hour QC Time-Series Sparkline">
      <path d={line} className="fill-none stroke-foreground/80" strokeWidth="1.4" />
      {marks.map((mark, index) => {
        if (mark.value === null) return null;
        const color = mark.spike ? '#C00000' : mark.hold ? '#FF9933' : '#009966';
        return (
          <circle
            key={index}
            cx={index * step}
            cy={y(mark.value)}
            r={mark.spike || mark.hold ? 2.4 : 1.1}
            fill={color}
          />
        );
      })}
    </svg>
  );
}

export const ReceptorInspector: React.FC<ReceptorInspectorProps> = ({
  className,
  entityType,
  entityName,
  latitude,
  longitude,
  compositeAqi,
  compositePaint,
  estimated,
  blacklist,
  windCopy,
  completeness,
  readings,
  sectors,
  p75Threshold,
  calmHours,
  pooled,
  pooledStationCount,
  qcSeries,
  exportMass,
  importMass,
}) => {
  return (
    <aside
      id="receptor-inspector"
      data-zone="receptor-inspector"
      className={cn("z-20 flex h-full w-[380px] shrink-0 flex-col overflow-hidden border-l border-border bg-card", className)}
    >
      <ScrollArea className="flex-1">
        <div className="space-y-3.5 p-3.5">
          {/* Card 1: Receptor Identity */}
          <Card className="rounded-none border-border shadow-none">
            <CardHeader className="p-3.5 pb-2">
              <div className="flex flex-wrap items-center gap-1.5">
                <Badge variant="secondary" className="rounded-none font-mono text-[10px] uppercase">
                  {entityType}
                </Badge>
                {estimated ? (
                  <Badge variant="outline" className="h-4 rounded-none border-dashed px-1 font-mono text-[9px]">
                    EST
                  </Badge>
                ) : null}
              </div>
              <CardTitle className="text-base font-bold tracking-tight">{entityName}</CardTitle>
              <CardDescription className="font-mono text-[11px] tabular-nums">
                {latitude.toFixed(3)}°N, {longitude.toFixed(3)}°E
              </CardDescription>
            </CardHeader>
            <CardContent className="p-3.5 pt-2">
              <div className="flex items-end justify-between gap-2">
                <div className="font-mono text-3xl font-extrabold tabular-nums">
                  {compositeAqi === null ? '—' : Math.round(compositeAqi)}
                </div>
                <Badge
                  className="rounded-none border-0 text-white"
                  style={{ backgroundColor: compositePaint.hex, color: compositePaint.text }}
                >
                  {compositePaint.label}
                </Badge>
              </div>

              {blacklist ? (
                <div
                  data-testid="wazirabad-blacklist-banner"
                  className="mt-2.5 flex items-center gap-2 rounded-none border border-destructive/50 bg-destructive/10 px-2.5 py-2 font-mono text-xs font-semibold text-destructive"
                >
                  <AlertOctagon size={16} strokeWidth={1.25} className="shrink-0" />
                  <span>{blacklist}</span>
                </div>
              ) : null}

              <div className="mt-2 font-mono text-xs tabular-nums text-muted-foreground" data-testid="aerodrome-wind">
                {windCopy}
              </div>
            </CardContent>
          </Card>

          {/* Card 2: 9-Parameter Statutory Sub-Indices */}
          <Card className="rounded-none border-border shadow-none">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 p-3 pb-2">
              <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Statutory Sub-Indices (9)
              </CardTitle>
              <Badge
                variant={completeness.meets ? 'outline' : 'destructive'}
                className="rounded-none font-mono text-[10px] tabular-nums"
              >
                {completeness.label}
              </Badge>
            </CardHeader>
            <CardContent className="p-0">
              <Table className="text-xs">
                <TableHeader>
                  <TableRow>
                    <TableHead>Parameter</TableHead>
                    <TableHead className="text-right">Conc.</TableHead>
                    <TableHead className="text-right">Sub-index</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {readings.map((r) => (
                    <TableRow key={r.key}>
                      <TableCell className="py-1.5 font-medium">
                        {r.key}
                        {r.governing ? (
                          <Badge variant="secondary" className="ml-1 h-4 rounded-none px-1 font-mono text-[9px]">
                            governing
                          </Badge>
                        ) : null}
                      </TableCell>
                      <TableCell className="py-1.5 text-right font-mono tabular-nums">
                        {r.formatted} {r.unit === 'index' ? '' : r.unit}
                      </TableCell>
                      <TableCell className="py-1.5 text-right font-mono tabular-nums">
                        {r.subIndex === null ? '—' : r.subIndex}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>

          {/* Card 3: 16-Sector CPF Polar Rose */}
          <Card className="rounded-none border-border shadow-none">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 p-3 pb-1">
              <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                16-Sector CPF Polar Rose
              </CardTitle>
              <span className="font-mono text-[10px] text-muted-foreground">
                P75 τ = {p75Threshold.toFixed(1)}
              </span>
            </CardHeader>
            <CardContent className="flex flex-col items-center p-3">
              <CpfRose sectors={sectors} />
              <p className="mt-1 text-center font-mono text-[10px] text-muted-foreground">
                {pooled ? `${pooledStationCount}-station pooled hours` : 'single-station hours'} · calm excluded {calmHours} h (ws &lt; 0.50 m/s)
              </p>
            </CardContent>
          </Card>

          {/* Card 4: 216h Telemetry & QC Flags */}
          <Card className="rounded-none border-border shadow-none">
            <CardHeader className="p-3 pb-1">
              <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                216h Telemetry & QC Flags
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 p-3">
              <QcSparkline marks={qcSeries} />
              <div className="flex justify-between font-mono text-xs tabular-nums">
                <span>Export {exportMass.toFixed(1)}</span>
                <span>Import {importMass.toFixed(1)}</span>
              </div>
            </CardContent>
          </Card>
        </div>
      </ScrollArea>
    </aside>
  );
};
