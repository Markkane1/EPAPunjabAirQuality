## 2026-11-11T08:18:25Z
You are explorer_m5_canvas, a read-only exploration agent.
Your working directory is: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\explorer_m5_canvas
Orchestrator conversation ID: dfe9ab49-5b73-4c71-b636-dccdcc9080ee

MANDATORY INPUTS:
- ORIGINAL_REQUEST.md: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\ORIGINAL_REQUEST.md
- PROJECT.md: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\orchestrator\PROJECT.md
- docs/UI_UX_SPECIFICATION.md: c:\Users\Asif\Downloads\Punjab Air Quality\docs\UI_UX_SPECIFICATION.md
- docs/TRANSFORMATION_LOGIC_SPEC.md: c:\Users\Asif\Downloads\Punjab Air Quality\docs\TRANSFORMATION_LOGIC_SPEC.md
- original System/index.html: c:\Users\Asif\Downloads\Punjab Air Quality\original System\index.html
- data/baseline/districts.json: c:\Users\Asif\Downloads\Punjab Air Quality\data\baseline\districts.json
- src/domain/math/projection.py: c:\Users\Asif\Downloads\Punjab Air Quality\src\domain\math\projection.py
- src/domain/math/idw.py: c:\Users\Asif\Downloads\Punjab Air Quality\src\domain\math\idw.py

MISSION:
Investigate and design the 5-Layer Canvas/Vector Map Rendering Engine for Milestone M5:
1. Examine docs/UI_UX_SPECIFICATION.md §3 and original System/index.html:
   - Layer 0: Static Basemap: Extract exact coordinate paths and topology for Punjab administrative boundaries, 41 district boundaries, and adjacent international borderlands (India, Kashmir, Sindh, KPK, Balochistan).
   - Layer 1: Continuous Wind-Steered IDW Surface Rasterizer: Equirectangular projection (KX = cos 31° = 0.857167), 2D grid rasterization, anisotropic wind-steering multiplier [0.3, 1.7], and distance confidence opacity taper [95, 235].
   - Layer 2: 1300-Particle Wind Advection Simulation: Float32Array ring buffer (x, y, age, maxAge, speed), bilinear wind field interpolation (u, v from nearest stations and airports), velocity saturation, boundary wrap/respawn.
   - Layer 3: Transport Flux Vectors & Border Chevrons: Quadratic bezier arcs linking source to receptor districts, pulsating chevron arrows for 39 border normal nodes, color-coded by magnitude and net balance.
   - Layer 4: Station Glyphs & Collision-Free District Labels: Sensor status markers, active concentration tooltips, collision-free text placement matching M4 `get_label_placement` coordinates and leader lines.
2. Design the 60 FPS Animation & Synchronization Architecture:
   - Decoupled offscreen canvas rendering / double-buffering.
   - Sub-hourly continuous temporal lerp between hourly slices: C(t) = (1 - alpha)*C_h0 + alpha*C_h1.
   - Smooth play/pause, scrub scrubbing, and window resize responsiveness (1200x900 base canvas scaled via CSS).
3. DO NOT WRITE OR MODIFY CODE. You are read-only.
4. Write your comprehensive rendering engine blueprint to c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\explorer_m5_canvas\handoff.md and send a completion message back to the orchestrator.
