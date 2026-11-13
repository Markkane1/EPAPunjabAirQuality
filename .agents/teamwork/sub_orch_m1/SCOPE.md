# Scope: Milestone 1 (Foundation, Tooling & Design Tokens)

## Architecture
- React 18 + TypeScript + Vite tooling foundation with strict TypeScript config.
- Rigid 100vw x 100vh CSS Grid container with 5 discrete zones (`command-bar`, `spatial-dock`, `map-canvas`, `receptor-inspector`, `temporal-scrubber`).
- WCAG 2.1 AAA Design Tokens in `src/styles/tokens.css` with luminance contrast ratio $\ge 7.0:1$ for all text/surface pairs across both dark and light modes.
- Typography: exclusively `IBM Plex Sans`, `IBM Plex Sans Condensed`, and `IBM Plex Mono` with `font-variant-numeric: tabular-nums` for numeric readouts.
- Zero emojis in any code, UI text, or HTML.
- Zero banned dependencies (`tailwindcss`, `lucide-react`, `heroicons`, `feather-icons`).
- Canonical TypeScript types in `src/domain/types/index.ts` defining contracts for Stations, Districts, Observations, WindVectors, Airsheds, LayerIds, and PEPCGrades.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| F16 | Visual Design System & Tokens | Rigid 100vw x 100vh CSS Grid, WCAG AAA tokens $\ge 7.0:1$ in `src/styles/tokens.css`, IBM Plex typography, tabular-nums, 1.25px inline SVGs, 1px hairlines, banned dependencies guard. | M1 | `ORIGINAL_REQUEST §R1`, `PROJECT.md` |
| M1.1 | Project Tooling & Dependencies | `package.json`, `tsconfig.json`, `vite.config.ts` setup with react, react-dom, maplibre-gl, deck.gl, etc. No banned packages. Clean build. | M1 | `DISPATCH.md` |
| M1.2 | HTML Entrypoint & Typography | `index.html` loading IBM Plex fonts, zero emojis, `src/styles/typography.css` with tabular-nums. | M1 | `DISPATCH.md` |
| M1.3 | Design Tokens & WCAG AAA Contrast | `src/styles/tokens.css` providing color variables with $\ge 7.0:1$ contrast against respective backgrounds. Hairlines, 0px border-radius, no blurs or drop-shadows. | M1 | `DISPATCH.md` |
| M1.4 | Workstation Layout Shell | `src/styles/grid.module.css`, `src/App.tsx`, `src/main.tsx` establishing 5-zone layout shell with CSS grid areas. | M1 | `DISPATCH.md` |
| M1.5 | Canonical Shared Domain Types | `src/domain/types/index.ts` declaring types for stations, districts, observations, wind vectors, layers, PEPC scales. | M1 | `DISPATCH.md` |

## Milestones & Tasks
| # | Task | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | Exploration & Architecture Design | 3 Explorers investigate tooling requirements, token calculations, and layout structure. | none | DONE |
| 2 | Implementation | 1 Worker implements tooling, tokens, typography, grid, App/main, and types; verifies build. | Task 1 | DONE |
| 3 | Review & Challenge | 2 Reviewers + 2 Challengers independently verify contrast, build, typography, and clean dependencies. | Task 2 | DONE |
| 4 | Forensic Audit & Gate | 1 Forensic Auditor verifies authentic implementation; gate verdict evaluated. | Task 3 | DONE |

Gate Status: **PASS** (100% unanimous pass across all criteria)
