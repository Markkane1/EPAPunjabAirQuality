import React from 'react';
import { Card } from '../ui/card';
import { cn } from '../../lib/utils';
import type { PollutantKey } from '../../domain/types';

export interface MultiPollutantItem {
  key: PollutantKey | 'WIND' | 'VENT';
  label: string;
  name: string;
  unit: string;
  value: number | string | null;
  statusText: string;
  colorHex: string;
  isExceedance: boolean;
}

export interface MultiPollutantGridProps {
  className?: string;
  activePollutant?: PollutantKey;
  onSelectPollutant?: (key: PollutantKey) => void;
  items?: MultiPollutantItem[];
}

const DEFAULT_POLLUTANTS: MultiPollutantItem[] = [
  { key: 'PM2.5', label: 'PM2.5', name: 'Fine Particulates', unit: 'µg/m³', value: 184.2, statusText: 'Hazardous (Tier 7)', colorHex: '#C00000', isExceedance: true },
  { key: 'PM10', label: 'PM10', name: 'Coarse Particulates', unit: 'µg/m³', value: 295.0, statusText: 'Very Unhealthy (Tier 6)', colorHex: '#7030A0', isExceedance: true },
  { key: 'NO2', label: 'NO₂', name: 'Nitrogen Dioxide', unit: 'µg/m³', value: 48.6, statusText: 'Moderate (Tier 3)', colorHex: '#FFFF00', isExceedance: false },
  { key: 'SO2', label: 'SO₂', name: 'Sulfur Dioxide', unit: 'µg/m³', value: 12.4, statusText: 'Good (Tier 1)', colorHex: '#00B050', isExceedance: false },
  { key: 'CO', label: 'CO', name: 'Carbon Monoxide', unit: 'mg/m³', value: 3.8, statusText: 'Satisfactory (Tier 2)', colorHex: '#92D050', isExceedance: false },
  { key: 'O3', label: 'O₃', name: 'Surface Ozone', unit: 'µg/m³', value: 32.1, statusText: 'Good (Tier 1)', colorHex: '#00B050', isExceedance: false },
  { key: 'AQI', label: 'AQI', name: 'PEPC Composite', unit: 'Index', value: 385, statusText: 'Hazardous (Tier 7)', colorHex: '#C00000', isExceedance: true },
  { key: 'WIND', label: 'WIND', name: 'Surface Wind 10m', unit: 'm/s', value: '1.2 m/s SE', statusText: 'Stagnant Calm (<1.5 m/s)', colorHex: '#ED7D31', isExceedance: true },
  { key: 'VENT', label: 'VENT', name: 'Ventilation Index', unit: 'm²/s', value: '180 m²/s', statusText: 'Critical Nocturnal Trap', colorHex: '#C00000', isExceedance: true },
];

export const MultiPollutantGrid: React.FC<MultiPollutantGridProps> = ({
  className,
  activePollutant = 'PM2.5',
  onSelectPollutant,
  items = DEFAULT_POLLUTANTS,
}) => {
  return (
    <div
      id="multi-pollutant-grid"
      data-zone="multi-pollutant-grid"
      className={cn("grid grid-cols-3 gap-2 p-2 bg-background/90 border border-border", className)}
    >
      {items.map((item) => {
        const isSelected = item.key === activePollutant;
        return (
          <Card
            key={item.key}
            onClick={() => {
              if (onSelectPollutant && item.key !== 'WIND' && item.key !== 'VENT') {
                onSelectPollutant(item.key as PollutantKey);
              }
            }}
            className={cn(
              "flex flex-col justify-between p-2 rounded-none border transition-colors cursor-pointer select-none",
              isSelected ? "border-primary bg-primary/5 ring-1 ring-primary" : "border-border hover:bg-muted/30"
            )}
          >
            {/* Header */}
            <div className="flex items-center justify-between gap-1">
              <span className="font-mono text-xs font-bold tracking-tight text-foreground">
                {item.label}
              </span>
              <span
                className="h-2 w-3 rounded-none shrink-0"
                style={{ backgroundColor: item.colorHex }}
                title={`PEPC Category: ${item.statusText}`}
              />
            </div>

            {/* Value & Name */}
            <div className="my-1">
              <div className="font-mono text-base font-bold tabular-nums text-foreground leading-none">
                {item.value !== null ? item.value : '—'}
                <span className="ml-1 text-[10px] font-normal text-muted-foreground">{item.unit}</span>
              </div>
              <div className="text-[10px] text-muted-foreground truncate">{item.name}</div>
            </div>

            {/* Status Footer */}
            <div className="flex items-center justify-between text-[9px] pt-1 border-t border-border/50">
              <span className="truncate text-muted-foreground font-mono">{item.statusText}</span>
              {item.isExceedance && (
                <span className="text-[9px] font-bold text-destructive shrink-0">EXCEED</span>
              )}
            </div>
          </Card>
        );
      })}
    </div>
  );
};
