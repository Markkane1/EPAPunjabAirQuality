# Milestone 1: Explorer Synthesis & Implementation Directives

## 1. Tooling & Dependencies (from Explorer M1.1)
- `package.json` with React 18.3.1, MapLibre GL 3.6.2, Deck.gl 8.9.36, Vite 5.4.11, TypeScript 5.6.3.
- Ambient type declarations in `src/types/deckgl.d.ts` re-exporting from `@deck.gl/*/typed`.
- `tsconfig.json` with `"moduleResolution": "bundler"`, `"skipLibCheck": true`, `"paths": { "@/*": ["src/*"] }`.
- `vite.config.ts` with vendor manual chunks (`deckgl-vendor`, `maplibre-vendor`, `react-vendor`).
- Zero banned dependencies (`tailwindcss`, `lucide-react`, `heroicons`, `feather-icons`).

## 2. Design Tokens & Typography (from Explorer M1.2)
- `src/styles/tokens.css`:
  - Dark mode surfaces: `--bg-canvas: #0f1716`, `--bg-panel: #152120`, `--bg-panel-elevated: #1c2b2a`, `--bg-dock: #131e1d`, `--bg-inspector: #152120`.
  - Dark mode calibrated inks (WCAG AAA >= 7.0:1):
    - `--ink-primary: #e3ece9` (CR 13.73:1 against bg-panel)
    - `--ink-secondary: #c0cfcb` (CR 9.12:1 against bg-panel-elevated, 10.15:1 against bg-panel)
    - `--ink-tertiary: #a8bbb5` (CR 7.31:1 against bg-panel-elevated, 8.13:1 against bg-panel)
    - `--accent: #5fc4c4` (CR 7.13:1 against bg-panel-elevated, 7.93:1 against bg-panel)
  - Light mode surfaces: `--bg-canvas: #eef1ef`, `--bg-panel: #fbfcfb`, `--bg-panel-elevated: #ffffff`, `--bg-dock: #e8ecea`, `--bg-inspector: #fbfcfb`.
  - Light mode calibrated inks (WCAG AAA >= 7.0:1):
    - `--ink-primary: #17221f` (CR 15.89:1 against bg-panel)
    - `--ink-secondary: #34423e` (CR 8.83:1 against bg-dock, 10.23:1 against bg-panel)
    - `--ink-tertiary: #3d4c48` (CR 7.57:1 against bg-dock, 8.78:1 against bg-panel)
    - `--accent: #084e51` (CR 7.94:1 against bg-dock, 9.20:1 against bg-panel)
  - Statutory PEPC colors: Good `#00B050`, Satisfactory `#92D050`, Moderate `#FFFF00`, Unhealthy for Sensitive Groups `#ED7D31`, Unhealthy `#FF0000`, Very Unhealthy `#7030A0`, Hazardous `#C00000`.
  - Structural: `--border-hairline: 1px solid #2a3a38` (dark) / `1px solid #d3dad7` (light), `--radius-none: 0px`, zero drop-shadows, zero backdrop blur.
- `src/styles/typography.css`:
  - IBM Plex Sans for body/labels, IBM Plex Sans Condensed for high-density tables/chips, IBM Plex Mono for telemetry/coordinates/timestamps.
  - Strict `font-variant-numeric: tabular-nums` for all numbers.
  - Zero emojis.

## 3. Layout Shell, HTML Entrypoint & Canonical Domain Types (from Explorer M1.3)
- `index.html`:
  - Pure HTML5, loading IBM Plex font families via Google Fonts.
  - Document title without emojis: `EPA Punjab Air Quality Workstation - Atmospheric Monitoring Console`.
  - Root element `<div id="root"></div>`.
- `src/styles/grid.module.css`:
  - Rigid 100vw x 100vh CSS Grid container with 5 named grid areas (`command-bar`, `spatial-dock`, `map-canvas`, `receptor-inspector`, `temporal-scrubber`).
- `src/App.tsx`:
  - Clean React functional component implementing the 5-zone grid shell with header, aside, main, aside, footer semantics and ARIA live regions.
- `src/main.tsx`:
  - React 18 `createRoot` mounting App to `#root`, importing `tokens.css` and `typography.css`.
- `src/domain/types/index.ts`:
  - Comprehensive canonical TypeScript contracts for:
    - 9 statutory pollutants (`AQI`, `PM2.5`, `PM10`, `NO2`, `SO2`, `CO`, `O3`, `NO`, `NOX`)
    - 7 PEPC grades
    - Stations (fixed vs mobile, Lahore micro-airshed, Wazirabad blacklist)
    - Districts (centroid `[lon, lat]`, boundary GeoJSON, `is_estimated` flag)
    - Observations & Telemetry
    - WindVectors (4 states: active, calm, dropout, blacklisted)
    - BorderNodes (39 transboundary normal vectors)
    - AdvectionFlux & CPF Wind Rose
    - Workstation state contracts (LayerId, Selection, Viewport)
