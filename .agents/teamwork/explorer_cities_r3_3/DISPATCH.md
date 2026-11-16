## 2026-11-15T19:50:59Z
You are Explorer 3 (Cross-Border Anchor Cities & Feature Preservation Specialist) for the Punjab Air Quality project.

## Mandatory Reading & Authoritative Sources
- Read ORIGINAL_REQUEST.md at: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\ORIGINAL_REQUEST.md
- Read PROJECT.md at: c:\Users\Asif\Downloads\Punjab Air Quality\PROJECT.md
- Working Directory: c:\Users\Asif\Downloads\Punjab Air Quality
- Your State Folder: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\explorer_cities_r3_3

## Mission & Specific Investigation Tasks
1. CROSS-BORDER AQI ANCHOR CITIES INVESTIGATION:
   - Investigate cross-border AQI anchor cities across the entire codebase (frontend and backend).
   - Find where cities like Amritsar, Jalandhar, Ludhiana, Bathinda, Firozpur (or similar transboundary Indian border nodes) are loaded, rendered, or given telemetry/fallbacks.
   - Trace why they are displaying identical fallback values.
   - Design the surgical fix so each city receives its own distinct, authentic anchor values/telemetry (distinct coordinates, distinct realistic baseline/historical or live values, distinct station IDs).
2. COMPREHENSIVE USER FEATURE PRESERVATION AUDIT:
   - The user directive states: "I HAVE IMPLEMENTED A LOT OF FEATURES, IF YOU WANT TO DELETE ANY OF THE CODE VERIFY THAT FROM ME FIRST. I DONT WANT YOU FUCKING EVERYTHING UP. Under no circumstances should any user-implemented features, components, routes, pipelines, or domain logic be deleted or stripped out."
   - Conduct a systematic audit of all user-implemented components, services, routes, and math transforms.
   - Map every file, route, and UI view so that any upcoming changes by workers are strictly non-destructive additions/adjustments, with zero deletions of user code.
3. RECOMMENDATIONS & CONTRACTS:
   - Provide concrete data structures and values for each cross-border anchor city.
   - Provide a strict checklist of user features that must be verified as intact before and after any worker modifications.

Document all findings with file paths, line numbers, and actionable remediation designs in:
`c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\explorer_cities_r3_3\handoff.md`.
Use send_message to report completion when done.
