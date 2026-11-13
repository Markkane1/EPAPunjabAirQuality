# Task Assignment: Explorer 1 (Normalizer & Schema Traps)

## Working Directory
c:\Users\Asif\Downloads\Punjab Air Quality

## State Folder
c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\explorer_m2_1

## Objective
Analyze the codebase, specifications, and baseline data to design the complete specification and implementation blueprint for `src/domain/normalizer/dataNormalizer.ts` addressing all 5 Schema Traps:
1. Trap 1: Invert district centroid `[lat, lon]` to `[lon, lat]` while strictly preserving `label` and `boundary` `[lon, lat]` unchanged.
2. Trap 2: Differentiate aerodrome wind telemetry dropouts (`null`) from aerodynamic calm ($0.0 \le w_s < 0.500$ m/s).
3. Trap 3: Hard-block wind vector rendering for Station 172 (Wazirabad) due to $140^\circ$ physical vane offset blacklist; set `anemometerBlacklisted: true` and flag as `ANEMOMETER BLACKLISTED (VANE OFFSET)`.
4. Trap 4: Dynamically compute fixed (74) vs mobile (5) station counts from active station records.
5. Trap 5: Unify divergent estimation flags (`est`, `is_monitored`) into canonical `is_estimated: boolean` and trigger diagonal cross-hatching on district polygons.

## Files to Inspect
- `c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\ORIGINAL_REQUEST.md` (MUST read first)
- `c:\Users\Asif\Downloads\Punjab Air Quality\PROJECT.md`
- `c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\sub_orch_m2\SCOPE.md`
- `c:\Users\Asif\Downloads\Punjab Air Quality\src\domain\types\index.ts`
- `c:\Users\Asif\Downloads\Punjab Air Quality\data\baseline\baseline_data.json`
- `c:\Users\Asif\Downloads\Punjab Air Quality\data\baseline\airports.json`
- `c:\Users\Asif\Downloads\Punjab Air Quality\docs\SYSTEM_ARCHITECTURE.md`

## Output Requirements
Produce a comprehensive handoff report at `c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\explorer_m2_1\handoff.md` detailing:
- Exact data schemas of raw inputs vs normalized outputs.
- Step-by-step logic for normalizing districts, stations, observations, wind vectors, and aerodromes.
- Explicit safeguards for Traps 1-5.
- Recommended function signatures and exports for `src/domain/normalizer/dataNormalizer.ts`.


## 2026-11-11T14:00:00Z
Received dispatch message from parent 67ce931e-e2b3-4aba-ae9e-6d61493eb56a:
You are Explorer 1 for Milestone 2: Domain Physics, Normalizer & Schema Trap Engine.
Investigate and design the complete specification and implementation blueprint for `src/domain/normalizer/dataNormalizer.ts` addressing all 5 Schema Traps.
Write final report to `.agents/teamwork/explorer_m2_1/handoff.md`.
