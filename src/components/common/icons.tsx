import * as React from 'react';

export interface IconProps extends React.SVGAttributes<SVGSVGElement> {
  size?: number | string;
  strokeWidth?: number | string;
}

function baseProps(props: IconProps) {
  const { size = 24, strokeWidth = 1.25, width, height, strokeLinejoin = 'miter', strokeLinecap = 'square', ...rest } = props;
  return {
    width: width ?? size,
    height: height ?? size,
    viewBox: '0 0 24 24',
    fill: 'none',
    stroke: 'currentColor',
    strokeWidth,
    strokeLinecap,
    strokeLinejoin,
    ...rest,
  };
}

export const Activity = React.forwardRef<SVGSVGElement, IconProps>((props, ref) => (
  <svg ref={ref} {...baseProps(props)}>
    <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
  </svg>
));
Activity.displayName = 'Activity';

export const AlertOctagon = React.forwardRef<SVGSVGElement, IconProps>((props, ref) => (
  <svg ref={ref} {...baseProps(props)}>
    <polygon points="7.86 2 16.14 2 22 7.86 22 16.14 16.14 22 7.86 22 2 16.14 2 7.86 7.86 2" />
    <line x1="12" y1="8" x2="12" y2="12" />
    <line x1="12" y1="16" x2="12.01" y2="16" />
  </svg>
));
AlertOctagon.displayName = 'AlertOctagon';

export const AlertTriangle = React.forwardRef<SVGSVGElement, IconProps>((props, ref) => (
  <svg ref={ref} {...baseProps(props)}>
    <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z" />
    <line x1="12" y1="9" x2="12" y2="13" />
    <line x1="12" y1="17" x2="12.01" y2="17" />
  </svg>
));
AlertTriangle.displayName = 'AlertTriangle';

export const Check = React.forwardRef<SVGSVGElement, IconProps>((props, ref) => (
  <svg ref={ref} {...baseProps(props)}>
    <polyline points="20 6 9 17 4 12" />
  </svg>
));
Check.displayName = 'Check';

export const ChevronDown = React.forwardRef<SVGSVGElement, IconProps>((props, ref) => (
  <svg ref={ref} {...baseProps(props)}>
    <polyline points="6 9 12 15 18 9" />
  </svg>
));
ChevronDown.displayName = 'ChevronDown';

export const ChevronUp = React.forwardRef<SVGSVGElement, IconProps>((props, ref) => (
  <svg ref={ref} {...baseProps(props)}>
    <polyline points="18 15 12 9 6 15" />
  </svg>
));
ChevronUp.displayName = 'ChevronUp';

export const ChevronRight = React.forwardRef<SVGSVGElement, IconProps>((props, ref) => (
  <svg ref={ref} {...baseProps(props)}>
    <polyline points="9 18 15 12 9 6" />
  </svg>
));
ChevronRight.displayName = 'ChevronRight';

export const GitBranch = React.forwardRef<SVGSVGElement, IconProps>((props, ref) => (
  <svg ref={ref} {...baseProps(props)}>
    <line x1="6" y1="3" x2="6" y2="15" />
    <circle cx="18" cy="6" r="3" />
    <circle cx="6" cy="18" r="3" />
    <path d="M18 9a9 9 0 0 1-9 9" />
  </svg>
));
GitBranch.displayName = 'GitBranch';

export const Layers = React.forwardRef<SVGSVGElement, IconProps>((props, ref) => (
  <svg ref={ref} {...baseProps(props)}>
    <polygon points="12 2 2 7 12 12 22 7 12 2" />
    <polyline points="2 17 12 22 22 17" />
    <polyline points="2 12 12 17 22 12" />
  </svg>
));
Layers.displayName = 'Layers';

export const Map = React.forwardRef<SVGSVGElement, IconProps>((props, ref) => (
  <svg ref={ref} {...baseProps(props)}>
    <polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6" />
    <line x1="8" y1="2" x2="8" y2="18" />
    <line x1="16" y1="6" x2="16" y2="22" />
  </svg>
));
Map.displayName = 'Map';

export const MapIcon = Map;

export const Maximize2 = React.forwardRef<SVGSVGElement, IconProps>((props, ref) => (
  <svg ref={ref} {...baseProps(props)}>
    <polyline points="15 3 21 3 21 9" />
    <polyline points="9 21 3 21 3 15" />
    <line x1="21" y1="3" x2="14" y2="10" />
    <line x1="3" y1="21" x2="10" y2="14" />
  </svg>
));
Maximize2.displayName = 'Maximize2';

export const Moon = React.forwardRef<SVGSVGElement, IconProps>((props, ref) => (
  <svg ref={ref} {...baseProps(props)}>
    <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
  </svg>
));
Moon.displayName = 'Moon';

export const Pause = React.forwardRef<SVGSVGElement, IconProps>((props, ref) => (
  <svg ref={ref} {...baseProps(props)}>
    <rect x="6" y="4" width="4" height="16" />
    <rect x="14" y="4" width="4" height="16" />
  </svg>
));
Pause.displayName = 'Pause';

export const Play = React.forwardRef<SVGSVGElement, IconProps>((props, ref) => (
  <svg ref={ref} {...baseProps(props)}>
    <polygon points="5 3 19 12 5 21 5 3" />
  </svg>
));
Play.displayName = 'Play';

export const Radio = React.forwardRef<SVGSVGElement, IconProps>((props, ref) => (
  <svg ref={ref} {...baseProps(props)}>
    <circle cx="12" cy="12" r="2" />
    <path d="M4.93 4.93a10 10 0 0 1 14.14 0" />
    <path d="M7.76 7.76a6 6 0 0 1 8.48 0" />
    <path d="M16.24 16.24a6 6 0 0 1-8.48 0" />
    <path d="M19.07 19.07a10 10 0 0 1-14.14 0" />
  </svg>
));
Radio.displayName = 'Radio';

export const Search = React.forwardRef<SVGSVGElement, IconProps>((props, ref) => (
  <svg ref={ref} {...baseProps(props)}>
    <circle cx="11" cy="11" r="8" />
    <line x1="21" y1="21" x2="16.65" y2="16.65" />
  </svg>
));
Search.displayName = 'Search';

export const SkipBack = React.forwardRef<SVGSVGElement, IconProps>((props, ref) => (
  <svg ref={ref} {...baseProps(props)}>
    <polygon points="19 20 9 12 19 4 19 20" />
    <line x1="5" y1="19" x2="5" y2="5" />
  </svg>
));
SkipBack.displayName = 'SkipBack';

export const SkipForward = React.forwardRef<SVGSVGElement, IconProps>((props, ref) => (
  <svg ref={ref} {...baseProps(props)}>
    <polygon points="5 4 15 12 5 20 5 4" />
    <line x1="19" y1="5" x2="19" y2="19" />
  </svg>
));
SkipForward.displayName = 'SkipForward';

export const SlidersHorizontal = React.forwardRef<SVGSVGElement, IconProps>((props, ref) => (
  <svg ref={ref} {...baseProps(props)}>
    <line x1="21" y1="4" x2="14" y2="4" />
    <line x1="10" y1="4" x2="3" y2="4" />
    <line x1="21" y1="12" x2="12" y2="12" />
    <line x1="8" y1="12" x2="3" y2="12" />
    <line x1="21" y1="20" x2="16" y2="20" />
    <line x1="12" y1="20" x2="3" y2="20" />
    <line x1="14" y1="2" x2="14" y2="6" />
    <line x1="8" y1="10" x2="8" y2="14" />
    <line x1="16" y1="18" x2="16" y2="22" />
  </svg>
));
SlidersHorizontal.displayName = 'SlidersHorizontal';

export const Sun = React.forwardRef<SVGSVGElement, IconProps>((props, ref) => (
  <svg ref={ref} {...baseProps(props)}>
    <circle cx="12" cy="12" r="5" />
    <line x1="12" y1="1" x2="12" y2="3" />
    <line x1="12" y1="21" x2="12" y2="23" />
    <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" />
    <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
    <line x1="1" y1="12" x2="3" y2="12" />
    <line x1="21" y1="12" x2="23" y2="12" />
    <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" />
    <line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
  </svg>
));
Sun.displayName = 'Sun';

export const Upload = React.forwardRef<SVGSVGElement, IconProps>((props, ref) => (
  <svg ref={ref} {...baseProps(props)}>
    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
    <polyline points="17 8 12 3 7 8" />
    <line x1="12" y1="3" x2="12" y2="15" />
  </svg>
));
Upload.displayName = 'Upload';

export const Wind = React.forwardRef<SVGSVGElement, IconProps>((props, ref) => (
  <svg ref={ref} {...baseProps(props)}>
    <path d="M9.59 4.59A2 2 0 1 1 11 8H2" />
    <path d="M12.59 19.41A2 2 0 1 0 14 16H2" />
    <path d="M17.73 7.73A2.5 2.5 0 1 1 19.5 12H2" />
  </svg>
));
Wind.displayName = 'Wind';

export const X = React.forwardRef<SVGSVGElement, IconProps>((props, ref) => (
  <svg ref={ref} {...baseProps(props)}>
    <line x1="18" y1="6" x2="6" y2="18" />
    <line x1="6" y1="6" x2="18" y2="18" />
  </svg>
));
X.displayName = 'X';

export const ZoomIn = React.forwardRef<SVGSVGElement, IconProps>((props, ref) => (
  <svg ref={ref} {...baseProps(props)}>
    <circle cx="11" cy="11" r="8" />
    <line x1="21" y1="21" x2="16.65" y2="16.65" />
    <line x1="11" y1="8" x2="11" y2="14" />
    <line x1="8" y1="11" x2="14" y2="11" />
  </svg>
));
ZoomIn.displayName = 'ZoomIn';

export const ZoomOut = React.forwardRef<SVGSVGElement, IconProps>((props, ref) => (
  <svg ref={ref} {...baseProps(props)}>
    <circle cx="11" cy="11" r="8" />
    <line x1="21" y1="21" x2="16.65" y2="16.65" />
    <line x1="8" y1="11" x2="14" y2="11" />
  </svg>
));
ZoomOut.displayName = 'ZoomOut';
