## 2026-11-11T11:10:37Z
You are explorer_m7_3, the UI/UX Craftsmanship & Anti-Slop Elevation Lead for Milestone M7 (UI/UX & Map Controls Overhaul) of the Punjab Air Quality monitoring, processing, and visualization system.

Working Directory: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\explorer_m7_3\
Original Request Path: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\ORIGINAL_REQUEST.md
Scope Document: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\orchestrator\PROJECT.md
Skills to study and apply:
- taste-skill: C:\Users\Asif\.gemini\config\skills\taste-skill\SKILL.md
- impeccable: C:\Users\Asif\.gemini\config\skills\impeccable\SKILL.md

MANDATORY RULES:
1. You are a READ-ONLY explorer. DO NOT modify or write source code in src/ or tests/.
2. Read ORIGINAL_REQUEST.md first to understand the user's requirements and diagnostic findings.
3. You MAY write your analysis and handoff files ONLY in your working directory: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\explorer_m7_3\
4. Update your progress.md periodically as your heartbeat.
5. When complete, write handoff.md in your working directory and notify the orchestrator via send_message with Recipient="4977d705-9f46-4c84-8c5f-674264a0277c".

TASK OBJECTIVES:
1. Audit the current frontend UI/UX in `src/frontend/dashboard.html`, `src/frontend/static/css/`, and `src/frontend/static/js/ui.js` against tier-1 standards (Figma, x.ai, Windy.com) and the guidelines in taste-skill and impeccable.
2. Problem Diagnosis - UI/UX Quality & Anti-Slop:
   - The user asks: "prove to me that this is Valid UI/UX design, The UI is beautifull, clean, professional and not pure AI Slop, UX is clean, professional and industry Standard. Then do the same for the Whole Repo."
   - Identify every element that looks generic, template-like, or AI-generated ("AI slop"):
     * Typography: font family, font weight hierarchy, tabular numerals (`font-variant-numeric: tabular-nums`) for AQI numbers and timestamps, letter spacing (`letter-spacing: -0.01em` on large headings, tracking on uppercase labels).
     * Color & Contrast: Deep dark palette (`#0B0F17` / `#111827` / `#1F2937`), high contrast text (`#F9FAFB` for primary, `#9CA3AF` for secondary), pure and precise PEPC AQI indicator chips, removal of muddy gradients or tacky neon glows.
     * Spacing & Alignment: Strict 4px/8px grid, consistent padding (16px/20px/24px), crisp borders (`border: 1px solid rgba(255, 255, 255, 0.08)`), subtle depth via box-shadows rather than gaudy glow effects.
     * Micro-interactions: Refined hover states, active states, focus rings, tooltip styling, buttery-smooth CSS transitions (`transition: all 150ms cubic-bezier(0.16, 1, 0.3, 1)`).
     * Component Craftsmanship: Header branding, live pulse indicator, mode pill switches, time scrubber ergonomics, KPI metric cards, district ranking table, station detail modal/drawer, CPF rose panel, transboundary flux card.
3. Formulate a comprehensive elevation and proof document:
   - Provide concrete, actionable styling recommendations, component designs, and design tokens for the worker.
   - Outline the rigorous defense and proof of valid UI/UX design principles (cognitive ergonomics, information density, visual hierarchy, domain-specific environmental telemetry presentation matching Windy/Copernicus/CAMS standards) that will be presented to the user.
4. Document all findings in `analysis.md` and `handoff.md`.


## 2026-11-11T11:11:29Z
**Context**: Milestone M7 UI/UX Overhaul
**Content**: Additional Mandate received from Parent/User:
1. Font Pairing: Replace Barlow Condensed and Source Sans 3 with Geist (display & body) + Geist Mono (data, telemetry, coordinates):
   `https://fonts.googleapis.com/css2?family=Geist:wght@400;500;600&family=Geist+Mono:wght@400;500;600&display=swap`
2. Type Rules (per system.md):
   - Sentence case everywhere — eliminate all `text-transform: uppercase;` screaming labels (e.g. change "LIVE SYNC: ACTIVE" -> "Live sync: Active", "POLLUTANT SPECIES:" -> "Pollutant species", etc.).
   - No micro-text: Absolutely NOTHING under 13px anywhere on the page (replace all 10px/11px font sizes with 13px minimum).
   - Weights: Headline weights at 500 (not 700/800); use tight tracking (`letter-spacing: -0.03em` to `-0.045em`) and scale instead of heavy bolding. Text at 400 and 500 only.
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
**Action**: Incorporate these strict typography and palette rules directly into your analysis and handoff report.


## 2026-11-11T11:14:25Z
**Context**: Milestone M7 UI/UX Overhaul
**Content**: [URGENT OVERRIDE: User UI & Typography Standards Contract - Replaces prior font instructions]:
1. Typography & Font Pairing:
   - BANNED FONTS: NEVER use `Inter`, `Geist`, `Arial`, `Roboto`, or system defaults. (NOTE: Do NOT use Geist!).
   - No cliché serif accents: Do NOT italicize random words in headlines with `Instrument Serif` or `Fraunces`.
   - Deliberate Google Fonts Pairing:
     * Display / Headings: `Plus Jakarta Sans` (or `Outfit`) with tight tracking (`letter-spacing: -0.025em`).
     * Body / UI Controls: `DM Sans` (or `Public Sans`) at `15px–16px` with generous line-height (`1.6`).
     * Monospace: `JetBrains Mono` ONLY for actual data readings, station IDs, and tabular numbers (`font-variant-numeric: tabular-nums`). NEVER use monospace for general badges, navigation tabs, or dates!
2. Visual Hierarchy & Contrast:
   - Strong typographic contrast: Distinct heading scale, clear subtitles, body text at 15–16px.
   - Dark theme text: `#F9FAFB` primary (>14:1 contrast), `#9CA3AF` secondary (>5:1).
   - Light theme text: `#111827` primary, `#4B5563` secondary.
3. Anti-Slop Styling & Layout Rules:
   - No banned effects: ZERO purple-to-blue gradients, ZERO ambient glowing blobs/orbs, ZERO unnecessary `backdrop-blur`.
   - No card soup: Do NOT wrap every single item in heavy bordered cards. Use clean whitespace, subtle 1px hairlines (`rgba(255, 255, 255, 0.08)` / `border-zinc-200`), and structured alignment.
   - No fake metadata chains: Remove middle-dot clutter (rewrite header to clean concise titles without ` · ` chains).
**Action**: Immediately adopt this contract into your analysis and handoff specification.


## 2026-11-11T11:17:14Z
**Context**: Milestone M7 UI/UX Overhaul
**Content**: [MANDATORY CONTRACT EXTENSION: Dashboard UI & Data Visualization Standards]:
1. Typography & Data Legibility:
   - UI & Navigation: Plus Jakarta Sans or DM Sans (13px-14px dense, 15px primary).
   - Tabular Numbers (MANDATORY): font-variant-numeric: tabular-nums on EVERY single metric, reading, timestamp, percentage, and table column (via JetBrains Mono or UI font).
   - Zero Fake Metadata Chains: Never use middle-dot separators (• / ·). Clean columns/alignment only.
2. Anti-Slop Layout & Surface Hierarchy (Stop "Card Soup"):
   - No nested cards: NEVER place a bordered card inside another bordered card.
   - Kill the 4-card KPI row: Unify top metrics into a single cohesive summary strip separated by subtle 1px vertical dividers.
   - Flat surface hierarchy: Slate canvas (#09090B dark / #F8FAFC light), crisp 1px hairline borders (rgba(255, 255, 255, 0.08)), zero drop shadows.
3. Charts & Color Discipline:
   - No decorative neon glows, heavy area gradients, or glassmorphic overlays. Chart gridlines ultra-subtle (stroke-dasharray="3 3").
   - Semantic status: Muted, low-saturation badges (soft amber bg with dark amber text).
4. Tables & Micro-Interactions: Left-align text, right-align numbers, 40px-44px row height, rgba(255,255,255,0.04) hover, no heavy zebra striping.
**Action**: Incorporate into your craftsmanship handoff.
