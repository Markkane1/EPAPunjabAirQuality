import React from 'react';
import { Pause, Play, SkipBack, SkipForward } from '../common/icons';
import { Button } from '../ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Slider } from '../ui/slider';
import { cn } from '../../lib/utils';
import type { PlaybackRate, WorkstationModel } from '../../workstation/state';

export interface TimelineScrubberProps {
  className?: string;
  hourIndex: number;
  lerpAlpha: number;
  isPlaying: boolean;
  playbackSpeed: PlaybackRate;
  scrubber: WorkstationModel['scrubber'];
  horizon: number[];
  totalHours?: number;
  onStep?: (delta: -1 | 1) => void;
  onTogglePlay?: () => void;
  onSpeed?: (speed: PlaybackRate) => void;
  onScrub?: (position: number) => void;
}

function HorizonSparkline({ values }: { values: number[] }) {
  if (values.length < 2) return null;
  const max = Math.max(...values, 1);
  const width = 640;
  const height = 28;
  const step = width / (values.length - 1);
  const d = values
    .map((val, idx) => `${idx === 0 ? 'M' : 'L'} ${idx * step} ${height - (val / max) * (height - 2)}`)
    .join(' ');
  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      className="pointer-events-none absolute inset-x-0 bottom-1 h-7 w-full"
      aria-hidden="true"
    >
      <path d={d} className="fill-none stroke-primary/70" strokeWidth="1.5" />
    </svg>
  );
}

export const TimelineScrubber: React.FC<TimelineScrubberProps> = ({
  className,
  hourIndex,
  lerpAlpha,
  isPlaying,
  playbackSpeed,
  scrubber,
  horizon,
  totalHours,
  onStep,
  onTogglePlay,
  onSpeed,
  onScrub,
}) => {
  const position = hourIndex + lerpAlpha;
  const maxHour = Math.max(0, (totalHours ?? (horizon.length || 216)) - 1);

  // Keyboard shortcut listener for spacebar and arrow navigation
  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;
      if (e.code === 'Space') {
        e.preventDefault();
        onTogglePlay?.();
      } else if (e.code === 'ArrowLeft') {
        e.preventDefault();
        onStep?.(-1);
      } else if (e.code === 'ArrowRight') {
        e.preventDefault();
        onStep?.(1);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onTogglePlay, onStep]);

  return (
    <footer
      id="temporal-scrubber"
      data-zone="temporal-scrubber"
      className={cn("z-30 flex h-20 shrink-0 items-center gap-4 border-t border-border bg-card px-4", className)}
    >
      {/* Transport Controls */}
      <div className="flex shrink-0 items-center gap-1.5">
        <Button
          variant="outline"
          size="icon"
          className="h-8 w-8 rounded-none"
          onClick={() => onStep?.(-1)}
          aria-label="Previous Hour"
        >
          <SkipBack size={14} strokeWidth={1.25} />
        </Button>
        <Button
          variant="default"
          size="icon"
          className="h-8 w-8 rounded-none shadow-none"
          onClick={() => onTogglePlay?.()}
          aria-label={isPlaying ? 'Pause' : 'Play'}
        >
          {isPlaying ? <Pause size={14} strokeWidth={1.25} /> : <Play size={14} strokeWidth={1.25} />}
        </Button>
        <Button
          variant="outline"
          size="icon"
          className="h-8 w-8 rounded-none"
          onClick={() => onStep?.(1)}
          aria-label="Next Hour"
        >
          <SkipForward size={14} strokeWidth={1.25} />
        </Button>

        <Select value={playbackSpeed} onValueChange={(val) => onSpeed?.(val as PlaybackRate)}>
          <SelectTrigger className="h-8 w-[70px] rounded-none font-mono text-xs" aria-label="Playback speed">
            <SelectValue />
          </SelectTrigger>
          <SelectContent className="rounded-none">
            {(['1x', '2x', '4x', '8x'] as PlaybackRate[]).map((rate) => (
              <SelectItem key={rate} value={rate} className="rounded-none">
                {rate}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Timestamp & Sub-Hourly Lerp Chip */}
      <div className="flex shrink-0 flex-col justify-center rounded-none border border-border bg-muted/50 px-3 py-1">
        <span className="font-mono text-xs font-bold tabular-nums text-foreground">{scrubber.timestampLine}</span>
        <span className="font-mono text-[10px] tabular-nums text-muted-foreground">{scrubber.detailLine}</span>
      </div>

      {/* Horizon Sparkline & Range Slider */}
      <div className="relative min-w-0 flex-1">
        <HorizonSparkline values={horizon} />
        <Slider
          min={0}
          max={maxHour}
          step={0.01}
          value={[position]}
          onValueChange={(val) => onScrub?.(val[0] ?? 0)}
          aria-label={`${maxHour + 1}-Hour Timeline Scrubber`}
        />
      </div>
    </footer>
  );
};
