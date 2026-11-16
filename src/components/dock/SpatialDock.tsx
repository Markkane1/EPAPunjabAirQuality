import React from 'react';
import { GitBranch, Layers, Map as MapIcon, Radio, Search, Wind } from '../common/icons';
import { Badge } from '../ui/badge';
import { Card } from '../ui/card';
import { Input } from '../ui/input';
import { ScrollArea } from '../ui/scroll-area';
import { Separator } from '../ui/separator';
import { Switch } from '../ui/switch';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import { cn } from '../../lib/utils';
import type { LayerId } from '../../domain/types';
import type { LayerVisibility, WorkstationModel } from '../../workstation/state';

export interface SpatialDockProps {
  className?: string;
  layers: LayerVisibility;
  activeLayerCount: number;
  dimensionGuard: string | null;
  domesticShare: number;
  inflowShare: number;
  activeChevrons: number;
  search: string;
  districts: WorkstationModel['districts'];
  selectedDistrictId?: string | null;
  onLayer?: (id: LayerId, checked: boolean) => void;
  onSearch?: (value: string) => void;
  onSelectDistrict?: (id: string) => void;
}

const LAYER_DEFINITIONS: Array<{ id: LayerId; label: string; hint: string; icon: typeof Layers }> = [
  { id: 'surface', label: 'Spatial IDW Surface', hint: 'Anisotropic continuous field', icon: Layers },
  { id: 'choropleth', label: 'District Choropleth & Labels', hint: '41 districts + greedy AABB labels', icon: MapIcon },
  { id: 'wind', label: 'Wind Vector Field', hint: 'ECMWF + stations + aerodromes', icon: Wind },
  { id: 'flux', label: 'Advection Flux & Border Chevrons', hint: 'Top 60 links + 39 border nodes', icon: GitBranch },
  { id: 'stations', label: 'Monitoring Stations & Aerodromes', hint: '79 stations + 6 ICAO airports', icon: Radio },
];

export const SpatialDock: React.FC<SpatialDockProps> = ({
  className,
  layers,
  activeLayerCount,
  dimensionGuard,
  domesticShare,
  inflowShare,
  activeChevrons,
  search,
  districts,
  selectedDistrictId,
  onLayer,
  onSearch,
  onSelectDistrict,
}) => {
  return (
    <aside
      id="spatial-dock"
      data-zone="spatial-dock"
      className={cn("z-20 flex h-full w-[340px] shrink-0 flex-col overflow-hidden border-r border-border bg-card", className)}
    >
      {/* Section 1: Cartographic Layers Header & 5 Switches */}
      <div className="flex items-center justify-between px-4 py-2.5">
        <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Cartographic Layers
        </span>
        <Badge variant="secondary" className="rounded-none font-mono text-[10px]">
          {activeLayerCount}/5 Active
        </Badge>
      </div>
      <div className="space-y-1 px-3 pb-3">
        {LAYER_DEFINITIONS.map((layer) => {
          const Icon = layer.icon;
          return (
            <div
              key={layer.id}
              className="flex items-center justify-between rounded-none border border-transparent px-2.5 py-1.5 transition-colors hover:bg-muted/60"
            >
              <div className="flex min-w-0 items-center gap-2">
                <Icon size={16} strokeWidth={1.25} className="shrink-0 text-muted-foreground" />
                <div className="min-w-0">
                  <div className="text-xs font-medium">{layer.label}</div>
                  <div className="truncate text-[10px] text-muted-foreground">{layer.hint}</div>
                  {layer.id === 'flux' && dimensionGuard ? (
                    <span className="block font-mono text-[10px] text-amber-500">{dimensionGuard}</span>
                  ) : null}
                </div>
              </div>
              <Switch
                checked={layers[layer.id]}
                onCheckedChange={(checked) => onLayer?.(layer.id, checked)}
                aria-label={layer.label}
              />
            </div>
          );
        })}
      </div>

      <Separator />

      {/* Section 2: Transboundary Mass-Balance Attribution Split Bar */}
      <div className="px-3 py-2.5">
        <Card className="space-y-2 rounded-none border-border bg-muted/30 p-3 shadow-none">
          <div className="flex items-center justify-between text-xs">
            <span className="font-medium text-foreground">Transboundary Attribution</span>
            <span className="font-mono text-[11px] text-muted-foreground">120km Belt</span>
          </div>
          <div className="flex h-2 overflow-hidden rounded-none bg-muted">
            <div className="h-full bg-primary" style={{ width: `${Math.round(domesticShare * 100)}%` }} />
            <div
              className="h-full bg-destructive"
              style={{ width: `${Math.round(inflowShare * 100)}%`, backgroundColor: '#C00000' }}
            />
          </div>
          <div className="flex justify-between font-mono text-xs tabular-nums">
            <span>Domestic {Math.round(domesticShare * 100)}%</span>
            <span>Inflow {Math.round(inflowShare * 100)}%</span>
          </div>
          <div className="font-mono text-[11px] text-muted-foreground">
            {activeChevrons}/39 Inflow Nodes
          </div>
        </Card>
      </div>

      <Separator />

      {/* Section 3: 41-District Statutory Ranking Table */}
      <div className="flex min-h-0 flex-1 flex-col">
        <div className="space-y-2 px-3 pb-1.5 pt-2">
          <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            District Ranking (41)
          </span>
          <div className="relative">
            <Search size={14} strokeWidth={1.25} className="absolute left-2.5 top-2 text-muted-foreground" />
            <Input
              value={search}
              onChange={(e) => onSearch?.(e.target.value)}
              placeholder="Search 41 districts..."
              className="h-7 rounded-none bg-background pl-8 text-xs font-mono"
              aria-label="Search 41 districts"
            />
          </div>
        </div>

        <ScrollArea className="flex-1">
          <Table className="w-full text-xs">
            <TableHeader className="sticky top-0 z-10 border-b border-border bg-card">
              <TableRow>
                <TableHead className="w-8 text-center font-mono">#</TableHead>
                <TableHead className="text-left">District</TableHead>
                <TableHead className="w-14 text-center">Status</TableHead>
                <TableHead className="text-right font-mono tabular-nums">Value</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {districts.map((d) => {
                const isSelected = selectedDistrictId === d.id;
                return (
                  <TableRow
                    key={d.id}
                    data-selected={isSelected}
                    onClick={() => onSelectDistrict?.(d.id)}
                    className={cn(
                      'cursor-pointer transition-colors hover:bg-muted/60',
                      isSelected && 'bg-accent/80 font-medium'
                    )}
                  >
                    <TableCell className="py-1.5 text-center font-mono text-[11px] tabular-nums text-muted-foreground">
                      {d.rank}
                    </TableCell>
                    <TableCell className="py-1.5 text-xs font-medium">
                      <span className="inline-flex items-center gap-1.5">
                        <span>{d.name}</span>
                        {d.badge ? (
                          <Badge
                            variant="outline"
                            className="h-4 rounded-none border-dashed px-1 py-0 font-mono text-[9px] text-muted-foreground"
                            title="IDW Imputed / Estimated"
                          >
                            {d.badge}
                          </Badge>
                        ) : null}
                      </span>
                    </TableCell>
                    <TableCell className="py-1.5 text-center text-[10px] text-muted-foreground">
                      {d.hatch ? 'Hatch' : ''}
                    </TableCell>
                    <TableCell className="py-1.5 text-right">
                      <Badge
                        className="h-5 rounded-none border-0 px-1.5 py-0 font-mono text-[11px] tabular-nums"
                        style={{ backgroundColor: d.color, color: d.textColor }}
                      >
                        {d.formatted}
                      </Badge>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </ScrollArea>
      </div>
    </aside>
  );
};
