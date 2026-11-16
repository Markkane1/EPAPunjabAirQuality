# BRIEFING — 2026-11-15T20:05:00Z

## Mission
Investigate cross-border AQI anchor cities, diagnose identical fallback values, and conduct a comprehensive audit of all user-implemented features to enforce zero code deletion.

## 🔒 My Identity
- Archetype: Teamwork explorer
- Roles: Cross-Border Anchor Cities Specialist, User Feature Preservation Auditor
- Working directory: c:\Users\Asif\Downloads\Punjab Air Quality
- State folder: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\explorer_cities_r3_3
- Original parent: f2fa7191-2b95-4f46-b1cb-ef6f552d742b
- Milestone: Investigation and Audit

## 🔒 Key Constraints
- Read-only investigation — do NOT implement / modify source code directly
- Under no circumstances should any user-implemented features, components, routes, pipelines, or domain logic be deleted or stripped out
- Verify cross-border anchor cities (Amritsar, Jalandhar, Ludhiana, Bathinda, Firozpur, etc.) across frontend and backend
- Concrete data structures and values for anchor cities with distinct telemetry/fallbacks

## Current Parent
- Conversation ID: f2fa7191-2b95-4f46-b1cb-ef6f552d742b
- Updated: 2026-11-15T20:05:00Z

## Investigation State
- **Explored paths**:
  - `src/infrastructure/database/seeder.py` (lines 493-528)
  - `src/infrastructure/repositories/baseline_repository.py` (lines 1224-1246)
  - `src/infrastructure/repositories/persistent_repository.py` (lines 900-934)
  - `src/pipelines/iqair.py` (lines 30-37, 248-261)
  - `src/pipelines/metar.py` (line 32 VIAR)
  - `src/pipelines/cams.py` (lines 28-35)
  - `src/pipelines/firms.py` (lines 209-235)
  - `src/frontend/static/js/api.js` (lines 133-150)
  - `src/frontend/static/js/canvas.js` (lines 955-987)
  - `src/frontend/static/js/ui.js` (lines 893-920)
  - `src/frontend/static/js/app.js` (lines 213-251, 662-698)
  - `src/frontend/dashboard.html` (all 6 views and zones)
  - `src/api/routes/observations.py` (lines 56-69)
  - `src/services/observation_service.py` (lines 421-432)
- **Key findings**:
  1. Identified root cause in `seeder.py:502`: identical equation `c_aqi = 210.0 + 50.0 * math.sin((idx + 2) / 10.0)` applied to every city indiscriminately across all hours, ignoring `c_info['base_aqi']`.
  2. Identified secondary fallback issues: `baseline_repository.py:1244` hardcoded `"status": "Severe"` for all cities; `api.js:144-149` lacked `latitude`/`longitude` causing map canvas skip.
  3. Formulated canonical distinct values and coordinates for 6 anchor cities: Amritsar, Firozpur, Jalandhar, Ludhiana, Bathinda, Delhi NCR.
  4. Cataloged complete user feature inventory spanning 6 architecture tiers with zero deletion rule.
- **Unexplored areas**: None within the scope of this investigation.

## Key Decisions Made
- Define distinct CPCB station IDs, exact coordinates, authentic baseline values, and diurnal variations for all 6 anchor cities.
- Provide a zero-deletion compliance gate checklist for any worker implementing fixes.

## Artifact Index
- DISPATCH.md — Dispatch instructions from orchestrator
- BRIEFING.md — Current agent state and memory
- progress.md — Liveness heartbeat and milestone tracking
- handoff.md — Comprehensive analysis and audit report
