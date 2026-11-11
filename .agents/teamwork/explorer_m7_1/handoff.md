# Handoff Report: Canvas Projection & Interactive Map Controls Overhaul (Milestone M7)

**Document ID**: `M7-HANDOFF-EXPLORER-01`  
**Agent**: `explorer_m7_1` (Canvas Projection & Map Controls Technical Lead)  
**Recipient**: `worker_m7_ui` / `orchestrator`  
**Working Directory**: `c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\explorer_m7_1\`  
**Milestone**: M7 (UI/UX & Map Controls Overhaul)  
**Status**: COMPLETE (Hard Handoff)  

---

## 1. Observation

### Obs 1: Canvas Scaling and Dimensional Sizing in `src/frontend/static/js/canvas.js`
In `src/frontend/static/js/canvas.js` lines 205–218:
```javascript
resize() {
  const rect = this.canvas.parentElement.getBoundingClientRect();
  this.dpr = Math.min(2, window.devicePixelRatio || 1);
  this.width = Math.floor(rect.width || 800);

  // Compute standard parallel scale factor
  this.S = this.width / ((B.lo1 - B.lo0) * KX);
  this.height = Math.floor((B.la1 - B.la0) * this.S);

  this.canvas.width = this.width * this.dpr;
  this.canvas.height = this.height * this.dpr;
  this.canvas.style.width = `${this.width}px`;
  this.canvas.style.height = `${this.height}px`;
```
`this.S` is derived strictly from `this.width` without regard to container height.

### Obs 2: Container Aspect Ratio in `src/frontend/static/css/tokens.css`
In `src/frontend/static/css/tokens.css` lines 487–503:
```css
.viewport-canvas-container {
  position: relative;
  width: 100%;
  aspect-ratio: 16 / 9;
  min-height: 480px;
  background: var(--geo-sea);
}

canvas.map-canvas {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  display: block;
  cursor: crosshair;
}
```
The container enforces `aspect-ratio: 16 / 9` with `overflow: hidden` on `.zone-3-viewport` (line 481).

### Obs 3: Geographic Spans and Aspect Ratio in `src/frontend/static/js/geo.js`
In `src/frontend/static/js/geo.js` lines 7–14:
```javascript
export const B = {
  lo0: 69.1,
  lo1: 75.75,
  la0: 27.55,
  la1: 34.3,
};

export const KX = Math.cos(31 * Math.PI / 180); // 0.8571673007
```
- Projected longitude span: $(75.75 - 69.10) \times 0.8571673007 = 5.70016255^\circ$.
- Latitude span: $34.30 - 27.55 = 6.75^\circ$.
- Aspect ratio: $5.70016255 / 6.75 \approx 0.8444685$ (taller than wide: height is $1.184 \times$ width).
- Container aspect ratio: $16 / 9 \approx 1.777778$ (more than twice as wide as the province).

### Obs 4: Southern District Coordinates in `src/frontend/static/data/districts.json`
Direct verification via Python revealed that 18 out of 41 districts lie south of $31.20^\circ\text{N}$:
- Rahim Yar Khan: $28.423^\circ\text{N}, 70.318^\circ\text{E}$
- Rajanpur: $29.330^\circ\text{N}, 70.354^\circ\text{E}$
- Bahawalpur: $29.389^\circ\text{N}, 71.728^\circ\text{E}$
- Lodhran: $29.537^\circ\text{N}, 71.628^\circ\text{E}$
- Muzaffargarh: $29.729^\circ\text{N}, 71.051^\circ\text{E}$
- Bahawalnagar: $29.810^\circ\text{N}, 73.197^\circ\text{E}$
- D.G. Khan: $30.046^\circ\text{N}, 70.640^\circ\text{E}$
- Vehari: $30.050^\circ\text{N}, 72.357^\circ\text{E}$
- Multan: $30.214^\circ\text{N}, 71.505^\circ\text{E}$
- Pakpattan: $30.362^\circ\text{N}, 73.382^\circ\text{E}$
- Khanewal: $30.371^\circ\text{N}, 72.142^\circ\text{E}$
- Kot Addu: $30.503^\circ\text{N}, 70.956^\circ\text{E}$
- Sahiwal: $30.646^\circ\text{N}, 72.988^\circ\text{E}$
- Taunsa: $30.704^\circ\text{N}, 70.651^\circ\text{E}$
- Okara: $30.801^\circ\text{N}, 73.426^\circ\text{E}$
- Toba Tek Singh: $30.966^\circ\text{N}, 72.486^\circ\text{E}$
- Layyah: $30.984^\circ\text{N}, 70.964^\circ\text{E}$
- Kasur: $31.078^\circ\text{N}, 74.504^\circ\text{E}$

Under scale $S = W / 5.70016 = 175.433$ at $W = 1000\text{px}$, visible height in a 16:9 container ($562.5\text{px}$) limits visible latitude to:
$\text{lat}_{\text{min}} = 34.30 - (562.5 / 175.433) = 31.09^\circ\text{N}$.
All 18 districts fall south of this cutoff and are clipped out.

### Obs 5: Total Absence of Interactive Canvas Event Listeners
A codebase-wide regex search for `mainMapCanvas` revealed that the element was referenced only once in `src/frontend/static/js/app.js` line 56 to instantiate `CanvasMapEngine`.
No event listeners (`pointerdown`, `pointermove`, `wheel`, `click`, etc.) were bound to the canvas element in `canvas.js`, `ui.js`, or `app.js`. No zoom or navigation buttons existed in `dashboard.html`.

### Obs 6: Existing Test Suite Health
Executing `py -m pytest tests/unit tests/integration` passed completely (258 unit tests, 46 M5 canvas challenge tests). All existing mathematical invariants pass.

---

## 2. Logic Chain

1. **Premise 1 (From Obs 3)**: The Punjab bounding box has an intrinsic aspect ratio of $\Delta X_{\text{geo}} / \Delta Y_{\text{geo}} = 5.70016 / 6.75 \approx 0.844$, making it taller than it is wide.
2. **Premise 2 (From Obs 1 & Obs 2)**: The rendering engine scaled solely by width into a 16:9 ($1.778$) container. Because $1.778 > 0.844$, width-based scaling generated a required height of $1.184 \times W$, whereas the container provided only $0.5625 \times W$ height.
3. **Deduction 1 (From Premise 2 & Obs 4)**: The bottom $52.5\%$ of the map height was pushed below the container boundary and clipped by `overflow: hidden`, hiding all 18 southern districts.
4. **Solution Deduction 1 (Mathematical Projection)**: To fit the entire bounding box inside any container dimensions $(W, H)$ with balanced padding $P$, the scale must be:
   $$S_x = \frac{W - 2P}{\Delta X_{\text{geo}}}, \quad S_y = \frac{H - 2P}{\Delta Y_{\text{geo}}}, \quad S_0 = \min(S_x, S_y)$$
   and the map must be centered dual-axis:
   $$\text{offsetX} = \frac{W - \Delta X_{\text{geo}} \cdot S_0}{2}, \quad \text{offsetY} = \frac{H - \Delta Y_{\text{geo}} \cdot S_0}{2}$$
5. **Solution Deduction 2 (Map Controls & Interactivity)**: Pan $(t_x, t_y)$ and zoom $s \in [0.8, 5.0]$ state must be added. Layers 0–3 must transform via affine context transformation (`ctx.translate(tx, ty); ctx.scale(s, s)`). Layer 4 must project to screen space ($(s \cdot x_0 + t_x, s \cdot y_0 + t_y)$) with constant 11px font, avoiding text blur and overcrowding.
6. **Solution Deduction 3 (UI Controls Pill)**: A floating frosted-glass toolbar with Zoom In (+), Zoom Out (-), Reset/Fit View (⛶), and Fullscreen toggle must be placed in the top-right corner of the canvas container. Pointer events (`pointerdown`, `pointermove`, `pointerup`, `setPointerCapture`) unify mouse and touch panning with zero pointer loss.
7. **Solution Deduction 4 (Responsive Layout)**: In `tokens.css`, `.zone-4-sidebar` below 1100px must expand to 100% width with an auto-fit grid (`repeat(auto-fit, minmax(320px, 1fr))`), eliminating the 354px empty void.

---

## 3. Caveats

1. **Sub-view Inset Canvases**: The Lahore Focus drawer (`lahoreMapCanvas`) uses a local bounding box ($74.1^\circ\text{E}-74.6^\circ\text{E}, 31.4^\circ\text{N}-31.7^\circ\text{N}$) with $4/3$ aspect ratio; its scaling was verified and functions correctly, but will also benefit from the updated padding helper.
2. **Device Pixel Ratio (DPR)**: On high-DPI displays (Retina, 4K), `window.devicePixelRatio` scales the internal canvas backing buffer (`canvas.width = W * dpr`). All mouse events report CSS pixels; coordinate transforms must remain strictly in CSS pixel units before the final DPR scale call.
3. **No other caveats**: The analysis is complete, verified, and ready for immediate implementation.

---

## 4. Conclusion

The canvas clipping defect and missing controls are fully diagnosed and architected. The solution:
1. Replaces width-only scaling with dual-axis constrained scale $S_0 = \min(S_x, S_y)$ and centering offsets $(\text{offsetX}, \text{offsetY})$ in `geo.js` and `canvas.js`.
2. Introduces pan translation $(t_x, t_y)$ and smooth zoom $s \in [0.8, 5.0]$ with zoom-to-cursor mechanics.
3. Synchronizes all 5 canvas layers with zero drift: Layers 0–3 transform under hardware affine scale/translate; Layer 4 renders in screen space with constant 11px typography and greedy AABB collision resolution.
4. Mounts a floating frosted-glass control pill (Zoom In, Zoom Out, Reset View, Fullscreen) in `dashboard.html` with Pointer Events and hotkeys (`+`, `-`, `0`, `f`).
5. Implements a fluid auto-fit sidebar grid for viewports below 1100px, eliminating dead space.

---

## 5. Verification Method

To independently verify the implementation, the worker or verification agent must execute:

### 1. Automated Python Test Suite
```powershell
py -m pytest tests/unit tests/integration -v
```
All existing tests must pass with 0 regressions.

### 2. Dedicated M7 Canvas Projection & Controls Verification
Write and execute `tests/integration/test_m7_map_controls.py`:
- Test that `computeFittedScale` keeps all 4 bounding box corners and all 18 southern districts (Rahim Yar Khan, Multan, Bahawalpur) strictly within $[P_x, W - P_x]$ and $[P_y, H - P_y]$ across:
  - 16:9 ($1000 \times 562.5$)
  - 4:3 ($800 \times 600$)
  - 1:1 ($600 \times 600$)
  - Mobile vertical ($360 \times 640$)
- Test roundtrip coordinate invertibility: `unproject(project(lon, lat)) == (lon, lat)` within $10^{-11}$.
- Test zoom-to-cursor invariance: the geographic coordinate at mouse position remains invariant before and after zoom.
- Test pan bounds clamping.

### 3. DOM & CSS Static Conformance Check
- Confirm `#mapZoomInBtn`, `#mapZoomOutBtn`, `#mapResetViewBtn`, `#mapFullscreenBtn` exist in `dashboard.html`.
- Confirm `.map-controls-pill` styles exist in `tokens.css`.
- Confirm `setupInteractions` binds pointer and wheel events to `mainMapCanvas`.

### 4. Invalidation Conditions
- Any southern district centroid (e.g. Rahim Yar Khan at lat 28.423) falling outside visible canvas boundaries on initial load.
- Any blurriness or label drift in Layer 4 during pan or zoom.
- Any unhandled exceptions during mouse drag, wheel zoom, or fullscreen toggle.
