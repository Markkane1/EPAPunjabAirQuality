# Original User Request

## Parameters
[skip-interview]
How this run was launched; not part of the task.

## Initial Request — 2026-11-10T12:39:30Z

Build the full end-to-end Punjab Air Quality monitoring, processing, and visualization system according to the specifications in docs/, organizing the codebase with clean architecture, software engineering principles, component-driven design patterns, and high reusability to support both live external streams and custom user datasets.

Working directory: c:\Users\Asif\Downloads\Punjab Air Quality
Integrity mode: development

## Reference Specifications
- docs/ARCHITECTURE_OVERVIEW.md
- docs/DATA_SOURCES_AND_STREAMS.md
- docs/TRANSFORMATION_LOGIC_SPEC.md
- docs/DATA_PIPELINES_ARCHITECTURE.md
- docs/SYSTEM_ARCHITECTURE.md
- docs/UI_UX_SPECIFICATION.md

## Requirements

### R1. Archive Existing Workspace Artifacts
Move existing project files (index.html and the collector/ directory) into a new directory named "original System", while preserving docs/ and .agents/ in the project root.

### R2. Data Pipeline & Ingestion Engine
Implement modular data ingestion pipelines adhering to docs/DATA_SOURCES_AND_STREAMS.md and docs/DATA_PIPELINES_ARCHITECTURE.md. Connect to accessible live external data feeds where available, extract station metadata and historical records from the original artifacts for baseline data templating, and provide clear interfaces allowing the system to ingest and test against user-provided CSV and custom datasets.

### R3. Transformation Logic Implementation
Implement the scientific transformation algorithms as defined in docs/TRANSFORMATION_LOGIC_SPEC.md, including IDW spatial interpolation, CPF polar roses, pollutant flux calculations, and PEPC breakpoint calculations, adhering to clean architecture with decoupled pure functions and documented mathematical inputs/outputs.

### R4. Core Services & Backend Architecture
Implement the backend architecture and API services specified in docs/SYSTEM_ARCHITECTURE.md and docs/ARCHITECTURE_OVERVIEW.md, maintaining strict boundary separation between data sources, business logic, storage adapters, and presentation interfaces.

### R5. Component-Driven UI/UX Dashboard
Implement the interactive user interface specified in docs/UI_UX_SPECIFICATION.md, adhering to component-driven design patterns, responsive layouts, clear visual hierarchy, accessible color palettes, and real-time visualization components.

### R6. Automated Verification and Test Suite
Implement automated test suites covering pipeline data ingestion, mathematical transformation algorithms, backend API contracts, and UI component rendering against the specifications in docs/.

## Acceptance Criteria

### Workspace Archival
- [ ] index.html and collector/ are relocated under original System/.
- [ ] docs/ remains intact in the workspace root.

### Pipeline and Ingestion
- [ ] Pipeline modules ingest data from configured live endpoints or fallback to schema-conforming templates seeded from station data in original System/index.html.
- [ ] An ingestion adapter exists that accepts and validates user-provided CSV datasets conforming to the specification schema.

### Transformation Logic
- [ ] Automated tests verify IDW spatial interpolation, CPF polar rose calculations, flux calculations, and PEPC breakpoints against known reference fixtures with deterministic output matching docs/TRANSFORMATION_LOGIC_SPEC.md.

### System Architecture & APIs
- [ ] Clean architecture boundaries are established with isolated domain models, business logic, data access abstractions, and API routing.
- [ ] Backend API endpoints serve station metadata, live/current readings, historical trends, and spatial interpolation outputs.

### UI/UX Interface
- [ ] Frontend dashboard renders station map, pollutant breakdown metrics, wind/flux indicators, and historical trend charts according to docs/UI_UX_SPECIFICATION.md.
- [ ] Interactive UI components respond to filter, station selection, and time-range queries without unhandled errors.

### Automated Test Verification
- [ ] Unit and integration test suites pass completely via automated test runners with zero failures.

## Follow-up — 2026-11-10T13:12:52Z

Resume the full system build for the Punjab Air Quality platform. Continue implementing the decoupled system according to the specifications in docs/ and .agents/teamwork/orchestrator/PROJECT.md, incorporating /impeccable and /taste-skill for high-end UI design, clean architecture, software engineering principles, component-driven design patterns, and reusability. Milestone M1 (archival) is already completed.


## Follow-up — 2026-11-10T13:15:37Z

resume Subagents, please if they were terminated, respawn

## Follow-up — 2026-11-11T03:57:42Z

Quota has reset and the server restarted. Please check on the active Milestone M3 verification gate (reviewer_m3_1, reviewer_m3_2, challenger_m3_1, challenger_m3_2, auditor_m3_1 — revive or re-dispatch any stopped verification agents), complete M3 certification, and continue sequentially with Milestone M4 (Core Backend Services & API Gateway), Milestone M5 (Component-Driven UI/UX Dashboard with /impeccable and /taste-skill), and Milestone M6 (Final E2E Integration & Audit).


## Follow-up — 2026-11-11T03:58:47Z

resume where you got inturrupted, Respawn Subagents if they were terminated abruptly

## Follow-up — 2026-11-11T05:42:29Z

User requested to continue. Please check on `worker_m4_backend` (revive or inspect progress on `tests/integration/test_api_endpoints.py` and the M4 verification gate), complete M4 certification, and continue sequentially with Milestone M5 (Component-Driven UI/UX Dashboard with /impeccable and /taste-skill) and Milestone M6 (Final E2E Integration & Audit).



## Follow-up — 2026-11-11T11:06:52Z

[New Assignment: UI/UX & Map Controls Overhaul per /taste-skill and /goal]

User Request:
"1st i cannot see the whole Map in the canvas, dont have any map related control. 2ndly, look at this screen shot (and Main page), and prove to me that this is Valid UI/UX design, The UI is beautifull, clean, professional and not pure AI Slop, UX is clean, professional and industry Standard. Then do the same for the Whole Repo."

Diagnostic Findings from Uploaded Screenshot (714x1024px viewport):
1. Canvas Clipping: Punjab bounding box (69.1°E-75.75°E, 27.55°N-34.3°N) has an aspect ratio of ~0.84 (taller than wide: 6.75° lat vs 5.70° projected lon). Current canvas scales only by width into a 16:9 container, causing southern Punjab (Multan, Bahawalpur, Rahim Yar Khan, D.G. Khan) to be cut off outside the viewport.
2. Missing Map Controls: No Zoom In (+), Zoom Out (-), Reset/Fit View (⛶), Fullscreen, mouse drag panning, or mouse wheel zoom controls exist on the canvas.
3. Responsive Layout Breakdown & Dead Space: At screen widths below 1100px (e.g. 714px in the user's screenshot), the console collapses into a single column, but the sidebar cards retain a fixed 360px width, leaving ~354px of empty black void on the right.
4. UI/UX Craftsmanship (taste-skill standard): Elevate typography, spacing, contrast, micro-interactions, and visual layout to tier-1 standards (Figma / x.ai / Windy.com standard), eliminating all AI-slop anti-patterns across the dashboard and repo.

Please orchestrate this comprehensive UI/UX and Map controls overhaul, re-verify all suites, and report back.


## Follow-up — 2026-11-11T11:10:43Z

[taste-skill Typography & Visual Overhaul Mandate]

The user specifically called out the fonts and typography as looking like "PURE AI SLOP" (referencing Barlow Condensed, tiny 10px uppercase screaming labels, and unbalanced weights).

In strict adherence to `taste-skill/references/system.md` and `taste-skill/references/layout-v4.md`:
1. Font Pairing:
   - Replace Barlow Condensed and Source Sans 3 with the official taste-skill pairing for technical/data platforms:
     `Geist` (for display and body) + `Geist Mono` (for data, telemetry, and coordinates):
     `https://fonts.googleapis.com/css2?family=Geist:wght@400;500;600&family=Geist+Mono:wght@400;500;600&display=swap`
     (Or `Host Grotesk` + `JetBrains Mono`).
2. Type Rules (per system.md):
   - Sentence case everywhere — remove all `text-transform: uppercase;` screaming labels (e.g., change "LIVE SYNC: ACTIVE" to "Live sync: Active", "POLLUTANT SPECIES:" to "Pollutant species", etc.).
   - No micro-text: Absolutely NOTHING under 13px anywhere on the page (replace all 10px/11px font sizes with 13px minimum).
   - Weights: Headline weights at 500 (not 700 or 800); use tight tracking (`letter-spacing: -0.03em` to `-0.045em`) and scale to carry them instead of loud bolding. Text at 400 and 500 only.
   - Body & list text at 14px–16px with line-height 1.5–1.6. Tabular numerals (`font-variant-numeric: tabular-nums`) on all data values.
3. Palette & Ground Overhaul:
   - Discard the murky greenish-olive palette (`#0f1716`, `#152120`, `#0b1211`).
   - Adopt true neutral, precision instrument slate/carbon:
     Canvas backdrop: `#0a0d14`
     Panels/Cards: `#121620`
     Elevated surfaces: `#1a202c`
     Borders/Hairlines: `rgba(255, 255, 255, 0.08)`
     Text: Primary `#f1f5f9` (90%+ contrast), Secondary `#94a3b8` (minimum 4.5:1).
   - Interface remains 95% neutral; color is reserved strictly for real data (pollutant concentration scales).

Ensure the orchestrator and frontend workers implement this exact typography and palette specification.


## Follow-up — 2026-11-11T11:13:38Z

[URGENT OVERRIDE: User UI & Typography Standards Contract]

The user has provided an explicit, mandatory UI & Typography Standards specification to replace any prior font instructions:

## 1. Typography & Font Pairing
- **BANNED FONTS**: NEVER use `Inter`, `Geist`, `Arial`, `Roboto`, or system defaults for the entire layout. Do NOT pair `Space Grotesk` with generic dark mode. (NOTE: Do NOT use Geist!).
- **No Cliché Serif Accents**: Do NOT italicize random words in headlines using `Instrument Serif` or `Fraunces`.
- **Deliberate Pairing (Google Fonts)**:
  - **Display / Headings**: Use `Plus Jakarta Sans` (or `Outfit`) with tight letter-spacing (`letter-spacing: -0.025em`).
  - **Body / UI Controls**: Use `DM Sans` (or `Public Sans`) at `15px–16px` with generous line-height (`1.6`).
  - **Monospace**: `JetBrains Mono` ONLY for actual data readings, station IDs, and tabular numbers (`font-variant-numeric: tabular-nums`). NEVER use monospace for general badges, navigation tabs, or dates!

## 2. Visual Hierarchy & Contrast
- Strong typographic contrast: Distinct heading sizes, clear subtitles, body text at 15–16px.
- Dark theme text: `#F9FAFB` primary (>14:1), `#9CA3AF` secondary (>5:1).
- Light theme text: `#111827` primary, `#4B5563` secondary.

## 3. Anti-Slop Styling & Layout Rules
- **No Banned Effects**: ZERO purple-to-blue gradients, ZERO ambient glowing blobs/orbs, ZERO unnecessary `backdrop-blur`.
- **No Card Soup**: Do NOT wrap every single item in heavy bordered cards. Use clean whitespace, subtle 1px hairlines (`rgba(255, 255, 255, 0.08)` / `border-zinc-200`), and structured alignment.
- **No Fake Metadata Chains**: Remove middle-dot clutter (e.g. rewrite header to clean concise titles without ` · ` chains).

Update orchestrator 54af003e-ff4b-41db-8b3f-1aaeff591027 and explorer_m7_3 immediately with this binding specification.


## Follow-up — 2026-11-11T11:16:24Z

[MANDATORY CONTRACT EXTENSION: Dashboard UI & Data Visualization Standards]

The user has provided an additional, strict specification for Dashboard UI & Data Visualization:

## 1. Typography & Data Legibility
- **Banned Fonts**: Never use `Inter`, `Geist`, or `Arial`.
- **UI & Navigation**: Use `Plus Jakarta Sans` or `DM Sans` (13px–14px for dense controls, 15px for primary labels).
- **Tabular Numbers (Mandatory)**: Every single metric, reading, timestamp, percentage, and table column containing numbers MUST enforce `font-variant-numeric: tabular-nums` (with `JetBrains Mono` or UI font) so digits align vertically and never jitter.
- **No Fake Metadata Chains**: Never use middle-dot separators (` • ` / ` · `). Use clean columns, alignment, or quiet micro-labels.

## 2. Anti-Slop Layout & Surface Hierarchy (Stop "Card Soup")
- **No Nested Cards**: NEVER place a bordered card inside another bordered card.
- **Flat Surface Hierarchy**: Subtle slate canvas (`#09090B` dark / `#F8FAFC` light), crisp 1px hairline borders (`rgba(255, 255, 255, 0.08)` / `border-zinc-200`), and zero drop shadows.
- **Kill the 4-Card KPI Row**: Unify top metrics into a single cohesive summary strip separated by subtle 1px vertical dividers, or pair them directly with the primary chart/canvas.
- **Density & Spacing**: Generous internal container padding (20px–24px), while keeping data tables and lists compact, scannable, and strictly grid-aligned.

## 3. Charts & Color Discipline
- **Disciplined Palette**: No decorative neon glows, heavy area gradients, or glassmorphic overlays. Keep chart gridlines ultra-subtle (`stroke-dasharray="3 3"` low opacity).
- **Semantic Status**: Muted, low-saturation badges (e.g. soft amber background with dark amber text) — never bright neon pills.
- Note: Air Quality statutory scale continues to follow regulatory PEPC thresholds cleanly.

## 4. Tables, Empty States & Micro-Interactions
- **High-Craft Tables**: Text columns left-aligned, numerical columns strictly right-aligned with tabular numbers. Consistent row heights (40px–44px) and subtle hover background highlights (`rgba(255, 255, 255, 0.04)`), never heavy zebra striping.
- **Intentional Empty States**: Zero blank white/black voids or unhelpful placeholders.

Apply these standards directly across `src/frontend/` (tokens.css, dashboard.html, ui.js, canvas.js).
