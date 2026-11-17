import * as React from 'react';
import * as SliderPrimitive from '@radix-ui/react-slider';
import { cn } from '@/lib/utils';

const Slider = React.forwardRef<
  React.ElementRef<typeof SliderPrimitive.Root>,
  React.ComponentPropsWithoutRef<typeof SliderPrimitive.Root>
>(({ className, ...props }, ref) => (
  <SliderPrimitive.Root
    ref={ref}
    className={cn('relative flex w-full touch-none select-none items-center', className)}
    style={{ position: 'relative', display: 'flex', width: '100%', height: '24px', alignItems: 'center', touchAction: 'none', userSelect: 'none', cursor: 'pointer' }}
    {...props}
  >
    <SliderPrimitive.Track
      className="relative h-1.5 w-full grow overflow-hidden rounded-none bg-primary/20"
      style={{ position: 'relative', height: '6px', width: '100%', flexGrow: 1, backgroundColor: '#2a3a38', borderRadius: '3px', overflow: 'hidden' }}
    >
      <SliderPrimitive.Range
        className="absolute h-full bg-primary"
        style={{ position: 'absolute', height: '100%', backgroundColor: 'var(--accent, #5fc4c4)' }}
      />
    </SliderPrimitive.Track>
    <SliderPrimitive.Thumb
      className="block h-4 w-4 rounded-none border border-primary/50 bg-background shadow-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50"
      style={{ display: 'block', width: '16px', height: '16px', backgroundColor: '#e3ece9', border: '2px solid var(--accent, #5fc4c4)', borderRadius: '2px', cursor: 'grab' }}
    />
  </SliderPrimitive.Root>
));
Slider.displayName = SliderPrimitive.Root.displayName;

export { Slider };
