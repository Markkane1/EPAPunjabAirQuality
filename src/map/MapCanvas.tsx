import { forwardRef, useEffect, useImperativeHandle, useRef, useState } from 'react';
import maplibregl, { type Map as MlMap } from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import { MapboxOverlay } from '@deck.gl/mapbox';
import type {
  AirportStation,
  LayerId,
  NormalizedDistrict,
  NormalizedStation,
  PollutantKey,
  SelectedEntity,
  SurfaceMode,
} from '../domain/types';
import { createChoroplethLayers } from './layers/ChoroplethLayer';
import { createFluxLayers } from './layers/FluxLayer';
import { createStationLayers } from './layers/StationLayer';
import { createSurfaceLayer } from './layers/SurfaceLayer';
import { createWindLayers } from './layers/WindLayer';

export interface MapHandle {
  zoomIn: () => void;
  zoomOut: () => void;
  reset: () => void;
  flyTo: (center: [number, number], zoom?: number) => void;
  flyToLahore: () => void;
}

export interface MapCanvasProps {
  districts?: NormalizedDistrict[];
  stations?: NormalizedStation[];
  airports?: AirportStation[];
  borderSamples?: number[][];
  districtValues?: Record<string, number | null>;
  stationValues?: Record<string, number | null>;
  pm25Values?: Record<string, number | null>;
  districtWinds?: Record<string, [u: number, v: number]>;
  stationWinds?: Record<string, [u: number, v: number]>;
  airportWinds?: Record<string, [u: number, v: number]>;
  pollutant?: PollutantKey;
  surfaceMode?: SurfaceMode;
  layers?: Record<LayerId, boolean>;
  selectedEntity?: SelectedEntity | null;
  onSelect?: (entity: { kind: 'district' | 'station' | 'airport'; id: string; name: string }) => void;
  hourIndex?: number;
  lerpAlpha?: number;
}

export const PUNJAB_BOUNDS: [[number, number], [number, number]] = [
  [69.3, 27.7],
  [75.5, 34.15],
];

export const LAHORE_CENTER: [number, number] = [74.3587, 31.5204];

export const MAP_LOCK = {
  pitch: 0 as const,
  maxPitch: 0,
  bearing: 0,
  dragRotate: false,
  touchPitch: false,
};

export const MapCanvas = forwardRef<MapHandle, MapCanvasProps>(function MapCanvas(
  props,
  ref
) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MlMap | null>(null);
  const overlayRef = useRef<MapboxOverlay | null>(null);
  const propsRef = useRef(props);
  propsRef.current = props;

  const [tooltip, setTooltip] = useState<{ x: number; y: number; text: string } | null>(null);

  useImperativeHandle(ref, () => ({
    zoomIn: () => mapRef.current?.zoomIn(),
    zoomOut: () => mapRef.current?.zoomOut(),
    reset: () => mapRef.current?.fitBounds(PUNJAB_BOUNDS, { padding: 28, duration: 400 }),
    flyTo: (center: [number, number], zoom = 8) => {
      mapRef.current?.flyTo({ center, zoom, duration: 800 });
    },
    flyToLahore: () => {
      mapRef.current?.flyTo({ center: LAHORE_CENTER, zoom: 10.5, duration: 800 });
    },
  }));

  // Build deck.gl layer stack
  const buildLayers = (p: MapCanvasProps) => {
    const {
      districts = [],
      stations = [],
      airports = [],
      borderSamples = [],
      districtValues = {},
      stationValues = {},
      pm25Values = {},
      districtWinds = {},
      stationWinds = {},
      airportWinds = {},
      pollutant = 'AQI',
      surfaceMode = 'anisotropic_wind_steered',
      layers = { surface: true, choropleth: true, wind: true, flux: true, stations: true },
      selectedEntity = null,
      hourIndex = 0,
      lerpAlpha = 0,
    } = p;

    const selectedId = selectedEntity?.id ?? null;
    const updateTrigger = `${hourIndex}-${lerpAlpha}-${pollutant}-${selectedId}`;

    const surface = layers.surface
      ? createSurfaceLayer({
          visible: layers.surface,
          mode: surfaceMode,
          pollutant,
          stations: stations.map((s) => ({
            id: s.id,
            name: s.name,
            latitude: s.latitude,
            longitude: s.longitude,
          })),
          stationValues,
          stationWinds,
          updateTrigger,
        })
      : null;

    const choropleth = layers.choropleth
      ? createChoroplethLayers({
          districts,
          districtValues,
          pollutant,
          visible: layers.choropleth,
          selectedDistrictId: selectedId,
          onSelect: (d) => {
            propsRef.current.onSelect?.({ kind: 'district', id: d.id, name: d.name });
          },
          onHover: (info: any) => {
            if (info.object?.properties) {
              const name = info.object.properties.name ?? '';
              const val = info.object.properties.rawVal;
              const text = val != null ? `${name}  ${val}` : name;
              setTooltip({ x: info.x + 12, y: info.y + 12, text });
            } else if (!info.object) {
              setTooltip(null);
            }
          },
          updateTrigger,
        })
      : [];

    const wind = layers.wind
      ? createWindLayers({
          districts,
          stations,
          airports,
          districtWinds,
          stationWinds,
          airportWinds,
          visible: layers.wind,
          onHover: (info: any) => {
            if (info.object?.item) {
              const item = info.object.item;
              if (item.state === 'blacklisted') {
                setTooltip({ x: info.x + 12, y: info.y + 12, text: item.blacklistReason });
              } else if (item.state === 'calm') {
                setTooltip({ x: info.x + 12, y: info.y + 12, text: `${item.name}  AERODYNAMIC CALM (< 0.50 m/s)` });
              } else if (item.state === 'dropout') {
                setTooltip({ x: info.x + 12, y: info.y + 12, text: `${item.name}  TELEMETRY DROPOUT (NULL)` });
              } else {
                setTooltip({
                  x: info.x + 12,
                  y: info.y + 12,
                  text: `${item.name}  ${item.speed?.toFixed(2)} m/s @ ${Math.round(item.direction ?? 0)}°`,
                });
              }
            } else if (!info.object) {
              setTooltip(null);
            }
          },
          updateTrigger,
        })
      : [];

    const flux = layers.flux
      ? createFluxLayers({
          districts,
          districtValues,
          pm25Values,
          districtWinds,
          borderSamples,
          pollutant,
          visible: layers.flux,
          onHover: (info: any) => {
            if (info.object?.sourceDistrict) {
              setTooltip({
                x: info.x + 12,
                y: info.y + 12,
                text: `${info.object.sourceDistrict} → ${info.object.receptorDistrict}  Flux: ${info.object.flux.toFixed(2)}`,
              });
            } else if (!info.object) {
              setTooltip(null);
            }
          },
          updateTrigger,
        })
      : [];

    const stLayer = layers.stations
      ? createStationLayers({
          stations,
          airports,
          stationValues,
          pollutant,
          visible: layers.stations,
          selectedStationId: selectedId,
          onSelect: (entity) => {
            propsRef.current.onSelect?.(entity);
          },
          onHover: (info: any) => {
            if (info.object) {
              const name = info.object.name ?? '';
              const id = info.object.id ?? '';
              const val = stationValues[id] ?? stationValues[name];
              const text = val != null ? `${name}  ${val}` : name;
              setTooltip({ x: info.x + 12, y: info.y + 12, text });
            } else if (!info.object) {
              setTooltip(null);
            }
          },
          updateTrigger,
        })
      : [];

    return [
      ...(surface ? [surface] : []),
      ...choropleth,
      ...wind,
      ...flux,
      ...stLayer,
    ];
  };

  useEffect(() => {
    const element = containerRef.current;
    if (!element) return;

    // Initialize strictly 2D Planimetric MapLibre GL map
    const map = new maplibregl.Map({
      container: element,
      style: {
        version: 8,
        sources: {},
        layers: [
          {
            id: 'background',
            type: 'background',
            paint: { 'background-color': '#0b1211' },
          },
        ],
      },
      center: [72.7, 31.15],
      zoom: 6.1,
      pitch: MAP_LOCK.pitch,
      maxPitch: MAP_LOCK.maxPitch,
      bearing: MAP_LOCK.bearing,
      dragRotate: MAP_LOCK.dragRotate,
      touchPitch: MAP_LOCK.touchPitch,
      attributionControl: false,
    });

    // Enforce rotation & pitch hard-disabling
    map.dragRotate.disable();
    map.touchZoomRotate.disableRotation();
    map.touchPitch.disable();
    map.keyboard.disableRotation();
    mapRef.current = map;

    // Deck.gl MapboxOverlay
    const overlay = new MapboxOverlay({
      interleaved: true,
      layers: buildLayers(propsRef.current),
    });
    overlayRef.current = overlay;

    map.on('load', () => {
      map.addControl(overlay as unknown as maplibregl.IControl);
      map.fitBounds(PUNJAB_BOUNDS, { padding: 28, duration: 0 });
    });

    return () => {
      overlay.finalize();
      map.remove();
      overlayRef.current = null;
      mapRef.current = null;
    };
  }, []);

  // Update Deck.gl layers when props update
  useEffect(() => {
    const overlay = overlayRef.current;
    if (!overlay) return;
    overlay.setProps({
      layers: buildLayers(props),
    });
  }, [
    props.districts,
    props.stations,
    props.airports,
    props.borderSamples,
    props.districtValues,
    props.stationValues,
    props.pm25Values,
    props.districtWinds,
    props.stationWinds,
    props.airportWinds,
    props.pollutant,
    props.surfaceMode,
    props.layers,
    props.selectedEntity,
    props.hourIndex,
    props.lerpAlpha,
  ]);

  return (
    <div
      className="absolute inset-0"
      data-pitch={MAP_LOCK.pitch}
      data-map-lock={JSON.stringify(MAP_LOCK)}
    >
      <div ref={containerRef} className="absolute inset-0" />
      {tooltip ? (
        <div
          role="tooltip"
          className="pointer-events-none z-50 rounded-none border border-border bg-popover px-2.5 py-1.5 font-mono text-xs tabular-nums text-popover-foreground"
          style={{
            position: 'absolute',
            left: tooltip.x,
            top: tooltip.y,
            boxShadow: 'none',
            borderRadius: 0,
            backdropFilter: 'none',
          }}
        >
          {tooltip.text}
        </div>
      ) : null}
    </div>
  );
});
