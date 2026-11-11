# BRIEFING — 2026-11-11T11:17:15Z

## Mission
Investigate canvas projection clipping of southern Punjab and design full pan/zoom/fit/fullscreen controls and multi-layer synchronization for M7.

## 🔒 My Identity
- Archetype: explorer
- Roles: Canvas Projection & Map Controls Technical Lead
- Working directory: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\explorer_m7_1\
- Original parent: 54af003e-ff4b-41db-8b3f-1aaeff591027
- Milestone: M7 (UI/UX & Map Controls Overhaul)

## 🔒 Key Constraints
- Read-only investigation — do NOT implement in src/ or tests/
- Write only to working directory: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\explorer_m7_1\
- Self-contained handoff with 5-component report
- Strict verification of mathematical projection, aspect ratio, layer sync, and hit-testing

## Current Parent
- Conversation ID: 54af003e-ff4b-41db-8b3f-1aaeff591027
- Updated: not yet

## Investigation State
- **Explored paths**:
  - `src/frontend/static/js/canvas.js` (5 layers, sizing, particle buffers, rasterizer, label collision)
  - `src/frontend/static/js/geo.js` (Equirectangular Plate Carrée projection with $K_X = \cos 31^\circ$, Path2D compilation)
  - `src/frontend/static/js/ui.js` (UI event listeners, CPF rose, sparkline, tables, CSV modal)
  - `src/frontend/static/js/app.js` (App coordinator, RAF animation loop, 10Hz throttle, path compilation)
  - `src/frontend/dashboard.html` (DOM zones 1-5, canvas viewport, cards)
  - `src/frontend/static/css/tokens.css` (Layout grid, canvas container 16:9, typography, tokens)
  - `tests/integration/test_m5_canvas_challenge.py` (M5 regression invariants)
- **Key findings**:
  - **Root Cause of Southern Punjab Clipping**: The canvas scaling factor was computed solely from width ($S = W / (d\text{Lon} \cdot K_X)$). Since Punjab's projected aspect ratio is $0.844$ (taller than wide), while the viewport container was fixed at 16:9 ($1.778$), the map required $1.184 \times W$ height. In a 1000px wide container with 562.5px height, everything south of $31.09^\circ\text{N}$ (18 out of 41 districts, including Multan, Bahawalpur, Rahim Yar Khan, D.G. Khan, Rajanpur, Muzaffargarh) was clipped out.
  - **Missing Controls & Canvas Interactivity**: No pointer/mouse/touch listeners or navigation buttons existed on `mainMapCanvas`. The map was entirely static.
  - **Dynamic Projection Solution**: Calculate $S_0 = \min(S_x, S_y)$ using available width and height with balanced padding ($P \in [24, 32]\text{px}$) and compute centering offsets $\text{offsetX} = (W - W_{\text{map}})/2$, $\text{offsetY} = (H - H_{\text{map}})/2$.
  - **Pan/Zoom Transformation**: Maintain zoom $s \in [0.8, 5.0]$ and pan $(t_x, t_y)$. Zoom to cursor keeps the mouse coordinate invariant. Layers 0–3 render with hardware affine context transform (`ctx.translate(tx, ty); ctx.scale(s, s)`). Layer 4 renders in screen space ($(s \cdot x_0 + t_x, s \cdot y_0 + t_y)$) with constant 11px font and dual-pass halo, ensuring 100% crisp typography without blur.
  - **Responsive Layout Dead Space**: Below 1100px, `.zone-4-sidebar` should expand to 100% width with a responsive multi-column auto-fit grid (`repeat(auto-fit, minmax(320px, 1fr))`), completely eliminating the 354px empty void.
- **Unexplored areas**: None for M7 canvas projection & map controls scope.

## Key Decisions Made
- Formulate exact backward-compatible mathematical signatures for `project(lon, lat, S, ox, oy)`, `unproject(x, y, S, ox, oy)`, and `computeFittedScale(width, height, padding)`.
- Use Pointer Events API with `setPointerCapture` for unified mouse, touch, and pen interactions.
- Provide full SVG-based floating control pill in `.viewport-canvas-container` with frosted glass styling per /taste-skill.

## Artifact Index
- DISPATCH.md — Stored prompt dispatch
- BRIEFING.md — Working memory and status
- progress.md — Liveness heartbeat and milestone tracker
- analysis.md — Full technical analysis and code designs
- handoff.md — 5-component handoff report for worker
