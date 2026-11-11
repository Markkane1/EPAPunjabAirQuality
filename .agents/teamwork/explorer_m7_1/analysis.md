# Technical Analysis: Canvas Projection & Interactive Map Controls Overhaul (Milestone M7)

**Document ID**: `M7-ARCH-ANALYSIS-01`  
**Author**: `explorer_m7_1` (Canvas Projection & Map Controls Technical Lead)  
**Target Milestone**: M7 (UI/UX & Map Controls Overhaul)  
**Status**: APPROVED FOR IMPLEMENTATION  

---

## 1. Executive Summary

Milestone M7 addresses critical UI/UX diagnostic failures identified in operational testing:
1. **Canvas Clipping of Southern Punjab**: Under current rendering, the entire southern half of the province (18 out of 41 districts, including Multan, Bahawalpur, Rahim Yar Khan, D.G. Khan, Rajanpur, and Muzaffargarh) is clipped outside the viewport. The map canvas calculated its scale factor solely from width into a 16:9 container, ignoring Punjab's tall aspect ratio (~0.84).
2. **Total Absence of Map Controls & Interactivity**: The map canvas was completely static with zero pointer drag, mouse wheel zoom, touch gestures, or UI navigation buttons (Zoom In, Zoom Out, Fit/Reset View, Fullscreen). Clicking on districts did nothing.
3. **Responsive Void**: On screen widths below 1100px (e.g. 714px in user telemetry screenshots), the layout left a massive ~354px empty black void due to fixed sidebar dimensions.

This analysis provides the exact mathematical formulations, coordinate transformation architectures, multi-layer synchronization mechanisms, and step-by-step implementation blueprints to resolve these defects according to tier-1 scientific instrument standards (/taste-skill and /impeccable).

---

## 2. Comprehensive Problem Diagnosis

### 2.1 Geographic Geometry of the Punjab Airshed

The canonical bounding box $B$ encompassing Punjab, its 41 administrative districts, 79 AQMS stations, 6 aerodromes, and transboundary borders is defined as:
$$\text{lo}_0 = 69.10^\circ\text{E}, \quad \text{lo}_1 = 75.75^\circ\text{E}$$
$$\text{la}_0 = 27.55^\circ\text{N}, \quad \text{la}_1 = 34.30^\circ\text{N}$$

The cartographic projection is Equirectangular (Plate Carrée) with standard parallel $\phi_0 = 31.0^\circ\text{N}$:
$$K_X = \cos(31^\circ) = 0.8571673007021123$$

The projected geographic spans are:
$$\Delta X_{\text{geo}} = (\text{lo}_1 - \text{lo}_0) \cdot K_X = (75.75 - 69.10) \cdot 0.8571673007 = 5.70016255^\circ$$
$$\Delta Y_{\text{geo}} = \text{la}_1 - \text{la}_0 = 34.30 - 27.55 = 6.75^\circ$$

The intrinsic projected aspect ratio $\text{AR}_{\text{Punjab}}$ is:
$$\text{AR}_{\text{Punjab}} = \frac{\Delta X_{\text{geo}}}{\Delta Y_{\text{geo}}} = \frac{5.70016255}{6.75} \approx 0.8444685$$

**Key Insight**: Punjab is significantly taller than it is wide ($6.75^\circ$ of latitude vs $5.70^\circ$ of projected longitude). In physical pixels at any scale $S$, its height is $1.184 \times$ its width.

### 2.2 Forensic Inspection of Existing Code

In `src/frontend/static/js/canvas.js` (lines 205–225):
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
...
```

And in `src/frontend/static/css/tokens.css` (lines 487–503):
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

### 2.3 Mathematical Proof of the Southern Clipping Defect

1. Let container width be $W = 1000\text{px}$.
2. Due to `aspect-ratio: 16 / 9`, the container CSS height is $H_{\text{container}} = 1000 \times \frac{9}{16} = 562.5\text{px}$.
3. `canvas.js` computes:
   $$S = \frac{W}{\Delta X_{\text{geo}}} = \frac{1000}{5.70016} \approx 175.433$$
   $$H_{\text{needed}} = \Delta Y_{\text{geo}} \cdot S = 6.75 \times 175.433 = 1184.17\text{px}$$
4. The canvas sets `height = 1184px`. However, `.zone-3-viewport` has `overflow: hidden`, and the container is only $562.5\text{px}$ high.
5. In the forward projection:
   $$y(\text{lat}) = (\text{la}_1 - \text{lat}) \cdot S = (34.30 - \text{lat}) \cdot 175.433$$
   Setting $y = 562.5\text{px}$ (the bottom edge of the visible viewport):
   $$\text{lat}_{\text{cutoff}} = 34.30 - \frac{562.5}{175.433} = 34.30 - 3.206 = 31.09^\circ\text{N}$$

**Conclusion**: Any district or station south of $31.09^\circ\text{N}$ is completely clipped outside the canvas viewport.

### 2.4 Census of Clipped Southern Districts

Empirical analysis of `src/frontend/static/data/districts.json` reveals that **18 out of 41 districts (43.9% of the province)** lie south of $31.2^\circ\text{N}$:

| # | District | Centroid Latitude | Centroid Longitude | Monitoring Status |
|---|----------|-------------------|-------------------|-------------------|
| 1 | Rahim Yar Khan | 28.423°N | 70.318°E | Monitored (Fixed AQMS) |
| 2 | Rajanpur | 29.330°N | 70.354°E | Unmonitored (IDW Imputed) |
| 3 | Bahawalpur | 29.389°N | 71.728°E | Monitored (Fixed AQMS) |
| 4 | Lodhran | 29.537°N | 71.628°E | Unmonitored (IDW Imputed) |
| 5 | Muzaffargarh | 29.729°N | 71.051°E | Monitored (Fixed AQMS) |
| 6 | Bahawalnagar | 29.810°N | 73.197°E | Monitored (Fixed AQMS) |
| 7 | D.G. Khan | 30.046°N | 70.640°E | Monitored (Fixed AQMS) |
| 8 | Vehari | 30.050°N | 72.357°E | Monitored (Fixed AQMS) |
| 9 | Multan | 30.214°N | 71.505°E | Monitored (Airport METAR + AQMS) |
| 10 | Pakpattan | 30.362°N | 73.382°E | Unmonitored (IDW Imputed) |
| 11 | Khanewal | 30.371°N | 72.142°E | Monitored (Fixed AQMS) |
| 12 | Kot Addu | 30.503°N | 70.956°E | Unmonitored (IDW Imputed) |
| 13 | Sahiwal | 30.646°N | 72.988°E | Monitored (Fixed AQMS) |
| 14 | Taunsa | 30.704°N | 70.651°E | Unmonitored (IDW Imputed) |
| 15 | Okara | 30.801°N | 73.426°E | Monitored (Fixed AQMS) |
| 16 | Toba Tek Singh | 30.966°N | 72.486°E | Unmonitored (IDW Imputed) |
| 17 | Layyah | 30.984°N | 70.964°E | Unmonitored (IDW Imputed) |
| 18 | Kasur | 31.078°N | 74.504°E | Monitored (Border Transboundary) |

All 18 districts, including critical regional cities and air quality hubs (Multan, Bahawalpur, Rahim Yar Khan), were hidden from the user.

---

## 3. Exact Mathematical Formulation for Dynamic Projection & Centering

### 3.1 Aspect-Ratio Adaptive Scaling

To guarantee that the entire bounding box fits inside any viewport (whether 16:9 widescreen, 4:3 console, 1:1 square, or 9:16 mobile) with balanced margins:

Let:
- $W$: Canvas buffer width in CSS pixels
- $H$: Canvas buffer height in CSS pixels
- $P_x, P_y$: Horizontal and vertical padding ($P \in [24, 32]\text{px}$, standard $28\text{px}$)
- $W_{\text{avail}} = W - 2 \cdot P_x$
- $H_{\text{avail}} = H - 2 \cdot P_y$

Calculate scale constraints in both dimensions:
$$S_x = \frac{W_{\text{avail}}}{\Delta X_{\text{geo}}} = \frac{W - 2 \cdot P_x}{(\text{lo}_1 - \text{lo}_0) \cdot K_X}$$
$$S_y = \frac{H_{\text{avail}}}{\Delta Y_{\text{geo}}} = \frac{H - 2 \cdot P_y}{\text{la}_1 - \text{la}_0}$$

The canonical baseline scale $S_0$ is the strict minimum:
$$S_0 = \min(S_x, S_y)$$

### 3.2 Dual-Axis Centering Offsets

The physical dimensions of the mapped bounding box at scale $S_0$ are:
$$W_{\text{map}} = \Delta X_{\text{geo}} \cdot S_0 = (\text{lo}_1 - \text{lo}_0) \cdot K_X \cdot S_0$$
$$H_{\text{map}} = \Delta Y_{\text{geo}} \cdot S_0 = (\text{la}_1 - \text{la}_0) \cdot S_0$$

The centering offsets that place the bounding box precisely in the center of the canvas with equal margins on opposite edges are:
$$\text{offsetX} = \frac{W - W_{\text{map}}}{2} = \frac{W - (\text{lo}_1 - \text{lo}_0) \cdot K_X \cdot S_0}{2}$$
$$\text{offsetY} = \frac{H - H_{\text{map}}}{2} = \frac{H - (\text{la}_1 - \text{la}_0) \cdot S_0}{2}$$

### 3.3 Forward and Inverse Projection Functions

The forward projection maps $(\lambda, \phi) = (\text{lon}, \text{lat})$ to canvas baseline coordinates $(x_0, y_0)$:
$$x_0(\lambda) = \text{offsetX} + (\lambda - \text{lo}_0) \cdot K_X \cdot S_0$$
$$y_0(\phi) = \text{offsetY} + (\text{la}_1 - \phi) \cdot S_0$$

The inverse projection maps canvas baseline coordinates $(x_0, y_0)$ back to $(\lambda, \phi)$:
$$\lambda(x_0) = \frac{x_0 - \text{offsetX}}{K_X \cdot S_0} + \text{lo}_0$$
$$\phi(y_0) = \text{la}_1 - \frac{y_0 - \text{offsetY}}{S_0}$$

### 3.4 Verification Across Multiple Viewport Ratios

Let $P = 28\text{px}$.

#### Case A: 16:9 Viewport ($W = 1000\text{px}, H = 562.5\text{px}$)
- $W_{\text{avail}} = 944\text{px}, H_{\text{avail}} = 506.5\text{px}$
- $S_x = 944 / 5.70016 = 165.61$
- $S_y = 506.5 / 6.75 = 75.037$
- $S_0 = \min(165.61, 75.037) = 75.037$ (Height-constrained)
- $W_{\text{map}} = 427.72\text{px}, H_{\text{map}} = 506.5\text{px}$
- $\text{offsetX} = (1000 - 427.72) / 2 = 286.14\text{px}$
- $\text{offsetY} = (562.5 - 506.5) / 2 = 28.00\text{px}$
- **Southernmost Point** ($\phi = 27.55^\circ\text{N}$): $y = 28.00 + 506.50 = 534.50\text{px} < 562.5\text{px}$ (Visible with $28\text{px}$ bottom margin).

#### Case B: Mobile / Narrow Viewport ($W = 682\text{px}, H = 480\text{px}, P = 24\text{px}$)
- $W_{\text{avail}} = 634\text{px}, H_{\text{avail}} = 432\text{px}$
- $S_x = 634 / 5.70016 = 111.22$
- $S_y = 432 / 6.75 = 64.00$
- $S_0 = 64.00$ (Height-constrained)
- $W_{\text{map}} = 364.81\text{px}, H_{\text{map}} = 432.00\text{px}$
- $\text{offsetX} = (682 - 364.81) / 2 = 158.60\text{px}$
- $\text{offsetY} = (480 - 432.00) / 2 = 24.00\text{px}$
- **Rahim Yar Khan** ($28.423^\circ\text{N}, 70.318^\circ\text{E}$):
  $x = 158.60 + (70.318 - 69.10) \cdot 0.857167 \cdot 64.00 = 225.40\text{px}$
  $y = 24.00 + (34.30 - 28.423) \cdot 64.00 = 400.13\text{px} < 480\text{px}$ (Fully visible!).

#### Case C: Vertical Mobile Screen ($W = 360\text{px}, H = 640\text{px}, P = 20\text{px}$)
- $W_{\text{avail}} = 320\text{px}, H_{\text{avail}} = 600\text{px}$
- $S_x = 320 / 5.70016 = 56.138$
- $S_y = 600 / 6.75 = 88.889$
- $S_0 = 56.138$ (Width-constrained!)
- $W_{\text{map}} = 320.00\text{px}, H_{\text{map}} = 378.93\text{px}$
- $\text{offsetX} = 20.00\text{px}$
- $\text{offsetY} = (640 - 378.93) / 2 = 130.54\text{px}$
- **All corners**: $x \in [20, 340]\text{px}$, $y \in [130.5, 509.5]\text{px}$ (Perfect vertical centering).

---

## 4. Pan, Zoom & Coordinate Transformation Architecture

### 4.1 State Variables and Limits

The interactive map state maintains:
- `zoom`: Current magnification factor $s \in [s_{\min}, s_{\max}] = [0.8, 5.0]$ (Default: $1.0$).
- `panX`: Horizontal translation $t_x$ in screen pixels (Default: $0.0$).
- `panY`: Vertical translation $t_y$ in screen pixels (Default: $0.0$).

### 4.2 Smooth Zoom Centered at Cursor Pivot

When zooming via mouse wheel or pinch gesture at screen position $(m_x, m_y)$, the geographic point under the cursor must remain strictly stationary on screen.

Let:
- $s_{\text{cur}}$: Current zoom factor
- $s_{\text{target}}$: Clamped new zoom factor $\max(0.8, \min(5.0, s_{\text{target}}))$
- $(m_x, m_y)$: Screen coordinate of mouse pointer or viewport center

The base map coordinate $(x_0, y_0)$ under $(m_x, m_y)$ before zoom is:
$$x_0 = \frac{m_x - t_x}{s_{\text{cur}}}$$
$$y_0 = \frac{m_y - t_y}{s_{\text{cur}}}$$

After zooming to $s_{\text{target}}$, we require:
$$m_x = s_{\text{target}} \cdot x_0 + t_{x, \text{new}} \implies t_{x, \text{new}} = m_x - \frac{s_{\text{target}}}{s_{\text{cur}}} (m_x - t_x)$$
$$t_{y, \text{new}} = m_y - \frac{s_{\text{target}}}{s_{\text{cur}}} (m_y - t_y)$$

### 4.3 Screen-to-Geo and Geo-to-Screen Mapping

With pan $(t_x, t_y)$ and zoom $s$:

**Forward Mapping (`geoToScreen`)**:
$$x_{\text{screen}}(\lambda) = t_x + s \cdot \left[ \text{offsetX} + (\lambda - \text{lo}_0) \cdot K_X \cdot S_0 \right]$$
$$y_{\text{screen}}(\phi) = t_y + s \cdot \left[ \text{offsetY} + (\text{la}_1 - \phi) \cdot S_0 \right]$$

**Inverse Mapping (`screenToGeo`)**:
$$\lambda(x_{\text{screen}}) = \frac{\frac{x_{\text{screen}} - t_x}{s} - \text{offsetX}}{K_X \cdot S_0} + \text{lo}_0$$
$$\phi(y_{\text{screen}}) = \text{la}_1 - \frac{\frac{y_{\text{screen}} - t_y}{s} - \text{offsetY}}{S_0}$$

### 4.4 Pan Bounds Clamping

To prevent users from losing the map in an infinite void:
$$t_x \in \left[ -W_{\text{map}} \cdot s - 0.6 W, \; 0.6 W \right]$$
$$t_y \in \left[ -H_{\text{map}} \cdot s - 0.6 H, \; 0.6 H \right]$$
At default zoom $s = 1.0$, $t_x \in [-0.3 W, 0.3 W]$ and $t_y \in [-0.3 H, 0.3 H]$.

---

## 5. Multi-Layer Canvas Synchronization Architecture

The canvas renderer uses 5 decoupled layers. Pan and zoom must synchronize across all 5 layers with zero spatial drift and zero raster blur.

```
+-----------------------------------------------------------------------------------------+
|                                CanvasMapEngine.render()                                 |
+-----------------------------------------------------------------------------------------+
| 1. ctx.save(); ctx.scale(dpr, dpr); ctx.clearRect(0, 0, width, height);                |
| 2. Fill sea background: ctx.fillStyle = tokens.geoSea; ctx.fillRect(0, 0, width, height)|
|                                                                                         |
| 3. HARDWARE AFFINE CONTEXT TRANSFORM:                                                   |
|    ctx.save();                                                                          |
|    ctx.translate(panX, panY);                                                           |
|    ctx.scale(zoom, zoom);                                                               |
|    +---------------------------------------------------------------------------------+  |
|    | Layer 0: Static Basemap (Path2D provinces, India fill, Punjab, dashed border)   |  |
|    | Layer 1: IDW Continuous Surface (fcCanvas drawImage clipped to pjPath)          |  |
|    | Layer 2: 1300-Particle Advection (Float32Array ring buffer in base coords)      |  |
|    | Layer 3: Transport Flux Vectors & Border Normal Chevrons                        |  |
|    +---------------------------------------------------------------------------------+  |
|    ctx.restore();                                                                       |
|                                                                                         |
| 4. SCREEN-SPACE CRISP RENDERING (Native 1:1 text & node pixels):                         |
|    +---------------------------------------------------------------------------------+  |
|    | Layer 4: Station Glyphs, District Nodes & Greedy 12-Offset Collision-Free Labels|  |
|    |          - Screen coordinates: (s * x0 + panX, s * y0 + panY)                   |  |
|    |          - Constant 11px JetBrains Mono font                                    |  |
|    |          - Dual-pass contrast halos (zero raster stretching)                    |  |
|    |          - Leader lines for disp > 20px                                         |  |
|    +---------------------------------------------------------------------------------+  |
| 5. ctx.restore();                                                                       |
+-----------------------------------------------------------------------------------------+
```

### Detailed Layer Invariants:

1. **Layer 0 (Basemap)**:
   - Base paths are compiled into `Path2D` objects with scale $S_0$ and centering offsets $(\text{offsetX}, \text{offsetY})$.
   - Rendered inside the affine context transform (`ctx.translate(panX, panY); ctx.scale(zoom, zoom);`).
   - Zero path re-compilation needed during pan and zoom; hardware executes clipping and path fills instantaneously.

2. **Layer 1 (IDW Raster Surface & Choropleth)**:
   - Offscreen raster `fcCanvas` covers $(W, H)$ in downsampled 5px cells.
   - Bilinear upsampling (`imageSmoothingEnabled = true`) smoothly interpolates colors.
   - Clipped to `this.paths.pjPath`.
   - Because `pjPath` and `fcCanvas` are both rendered inside the affine context transform, the surface and boundary clip move in lockstep without edge bleeding or spatial drift.

3. **Layer 2 (1300-Particle Advection Simulation)**:
   - Particle positions $(x, y)$ in `particleState` live in base coordinates $(x_0, y_0)$.
   - Boundary checks (`hit.isPointInPath(this.paths.pjPath, x, y)`) run against the unscaled hit canvas base path.
   - Drawn inside the affine transform. Line width is scale-compensated:
     $$\text{lineWidth} = \max(0.5, \frac{0.9}{\sqrt{s}})$$
   - This prevents particles from turning into fat bars when zoomed in or vanishing when zoomed out.

4. **Layer 3 (Transport Vectors & Chevrons)**:
   - Bezier curve endpoints and 39 border normal nodes are in base coordinates.
   - Line widths and arrowhead dimensions are scaled by $1 / \sqrt{s}$ to preserve visual elegance.

5. **Layer 4 (Station Glyphs & Labels)**:
   - **Crucial Architectural Decision**: Rendered outside the affine context transform (in native screen space).
   - Each district node is projected to screen:
     $$x_{\text{scr}} = t_x + s \cdot \text{dist.xy}[0]$$
     $$y_{\text{scr}} = t_y + s \cdot \text{dist.xy}[1]$$
   - Node circle radius remains constant (5px normal, 8px selected).
   - Typography remains crisp 11px JetBrains Mono with 3px contrast halo.
   - Greedy 12-offset AABB collision detection runs in screen pixels. As the user zooms in, districts spread out on screen, naturally resolving collisions and eliminating label overlap!

---

## 6. Interactive Map Controls UI/UX Specification

### 6.1 Floating Frosted-Glass Map Controls Pill

Positioned in the top-right corner of `.viewport-canvas-container`:

```html
<div class="map-controls-pill" role="toolbar" aria-label="Map Navigation Controls">
  <button type="button" class="map-ctrl-btn" id="mapZoomInBtn" aria-label="Zoom In" title="Zoom In (+)">
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
      <line x1="12" y1="5" x2="12" y2="19"></line>
      <line x1="5" y1="12" x2="19" y2="12"></line>
    </svg>
  </button>
  <button type="button" class="map-ctrl-btn" id="mapZoomOutBtn" aria-label="Zoom Out" title="Zoom Out (−)">
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
      <line x1="5" y1="12" x2="19" y2="12"></line>
    </svg>
  </button>
  <div class="map-ctrl-divider"></div>
  <button type="button" class="map-ctrl-btn" id="mapResetViewBtn" aria-label="Reset / Fit Province View" title="Reset / Fit Province View (⛶)">
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
      <path d="M3 9V5a2 2 0 0 1 2-2h4"></path>
      <path d="M15 3h4a2 2 0 0 1 2 2v4"></path>
      <path d="M21 15v4a2 2 0 0 1-2 2h-4"></path>
      <path d="M9 21H5a2 2 0 0 1-2-2v-4"></path>
    </svg>
  </button>
  <button type="button" class="map-ctrl-btn" id="mapFullscreenBtn" aria-label="Toggle Fullscreen" title="Toggle Fullscreen (F)">
    <svg id="fullscreenExpandIcon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
      <polyline points="15 3 21 3 21 9"></polyline>
      <polyline points="9 21 3 21 3 15"></polyline>
      <line x1="21" y1="3" x2="14" y2="10"></line>
      <line x1="3" y1="21" x2="10" y2="14"></line>
    </svg>
  </button>
</div>
```

### 6.2 Styling Rules (`tokens.css`)

```css
.map-controls-pill {
  position: absolute;
  top: 14px;
  right: 16px;
  z-index: 20;
  display: flex;
  flex-direction: column;
  background: var(--bg-panel-overlay);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.35);
  overflow: hidden;
}

.map-ctrl-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  padding: 0;
  border: none;
  background: transparent;
  color: var(--ink-primary);
  cursor: pointer;
  transition: background-color 0.15s ease, color 0.15s ease, transform 0.1s ease;
}

.map-ctrl-btn:hover {
  background: var(--bg-panel-elevated);
  color: var(--accent);
}

.map-ctrl-btn:active {
  transform: scale(0.92);
  background: var(--border-subtle);
}

.map-ctrl-btn:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: -2px;
}

.map-ctrl-divider {
  height: 1px;
  background: var(--border-subtle);
  margin: 0 4px;
}
```

### 6.3 Pointer & Gesture Event Handling

```javascript
setupInteractions(onSelectDistrict) {
  const canvas = this.canvas;
  canvas.style.cursor = 'grab';
  canvas.style.touchAction = 'none'; // Prevent browser gesture conflicts

  // Pointer Drag (Pan)
  canvas.addEventListener('pointerdown', (e) => {
    canvas.setPointerCapture(e.pointerId);
    this.isDragging = true;
    this.dragStartX = e.clientX;
    this.dragStartY = e.clientY;
    this.initialPanX = this.panX;
    this.initialPanY = this.panY;
    this.hasDragged = false;
    canvas.style.cursor = 'grabbing';
  });

  canvas.addEventListener('pointermove', (e) => {
    if (this.isDragging) {
      const dx = e.clientX - this.dragStartX;
      const dy = e.clientY - this.dragStartY;
      if (Math.hypot(dx, dy) > 4) {
        this.hasDragged = true;
      }
      this.panX = this.initialPanX + dx;
      this.panY = this.initialPanY + dy;
      this.clampPan();
    } else {
      const rect = canvas.getBoundingClientRect();
      const sx = e.clientX - rect.left;
      const sy = e.clientY - rect.top;
      const hit = this.findDistrictAt(sx, sy);
      canvas.style.cursor = hit ? 'pointer' : 'grab';
    }
  });

  const endDrag = (e) => {
    if (!this.isDragging) return;
    this.isDragging = false;
    try { canvas.releasePointerCapture(e.pointerId); } catch (_) {}
    canvas.style.cursor = 'grab';

    if (!this.hasDragged) {
      // Direct District Click Selection
      const rect = canvas.getBoundingClientRect();
      const sx = e.clientX - rect.left;
      const sy = e.clientY - rect.top;
      const hitDistrict = this.findDistrictAt(sx, sy);
      if (hitDistrict && onSelectDistrict) {
        onSelectDistrict(hitDistrict);
      }
    }
  };

  canvas.addEventListener('pointerup', endDrag);
  canvas.addEventListener('pointercancel', endDrag);

  // Wheel Zoom (centered at mouse)
  canvas.addEventListener('wheel', (e) => {
    e.preventDefault();
    const rect = canvas.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;
    const zoomFactor = Math.exp(-e.deltaY * 0.0018);
    this.zoomTo(this.zoom * zoomFactor, mouseX, mouseY);
  }, { passive: false });
}
```

### 6.4 Keyboard Hotkeys

In `ui.js`:
- `+` or `=`: Zoom In
- `-` or `_`: Zoom Out
- `0` or `Escape`: Reset/Fit View
- `f` or `F`: Toggle Fullscreen

---

## 7. Step-by-Step Implementation Guide for Worker

The worker should implement the changes across these 6 files:

### File 1: `src/frontend/static/js/geo.js`
1. Update `project(lon, lat, S, ox = 0, oy = 0)` and `unproject(x, y, S, ox = 0, oy = 0)` to support optional centering offsets while maintaining 100% backward compatibility.
2. Export `computeFittedScale(width, height, padding = 28)`:
   ```javascript
   export function computeFittedScale(width, height, padding = 28) {
     const dLonProj = (B.lo1 - B.lo0) * KX;
     const dLat = B.la1 - B.la0;
     const availW = Math.max(10, width - padding * 2);
     const availH = Math.max(10, height - padding * 2);
     const Sx = availW / dLonProj;
     const Sy = availH / dLat;
     const S = Math.min(Sx, Sy);
     const mapW = dLonProj * S;
     const mapH = dLat * S;
     const offsetX = (width - mapW) / 2;
     const offsetY = (height - mapH) / 2;
     return { S, offsetX, offsetY, mapW, mapH };
   }
   ```
3. Update `compilePaths(GEO, IND, TBG, districts, S, ox = 0, oy = 0)` and `addRingToPath` to pass offsets `ox, oy`.

### File 2: `src/frontend/static/js/canvas.js`
1. Import `computeFittedScale` from `./geo.js`.
2. Add navigation properties to `CanvasMapEngine` constructor:
   `offsetX, offsetY, mapW, mapH, zoom, panX, panY, minZoom, maxZoom, isDragging, dragStartX, dragStartY, initialPanX, initialPanY, hasDragged`.
3. Update `resize()` to calculate `fit = computeFittedScale(this.width, this.height, 28)`.
4. Add methods:
   - `zoomIn(factor)`
   - `zoomOut(factor)`
   - `resetView()`
   - `zoomTo(targetZoom, pivotX, pivotY)`
   - `panBy(dx, dy)`
   - `clampPan()`
   - `screenToGeo(screenX, screenY)`
   - `geoToScreen(lon, lat)`
   - `findDistrictAt(screenX, screenY, maxDistancePx = 18)`
   - `setupInteractions(onSelectDistrict)`
5. Update `render(state)`:
   - Wrap Layers 0, 1, 2, 3 in `ctx.save(); ctx.translate(this.panX, this.panY); ctx.scale(this.zoom, this.zoom); ... ctx.restore();`.
   - Scale line widths in Layer 2 and Layer 3 by $1 / \sqrt{\text{zoom}}$.
   - Update Layer 4 to project each district coordinate to screen space:
     `const sx = this.panX + this.zoom * dist.xy[0];`
     `const sy = this.panY + this.zoom * dist.xy[1];`
     Render node circles, labels, halos, and leader lines in native 1:1 screen resolution with greedy AABB collision search.

### File 3: `src/frontend/static/js/app.js`
1. In `init()`, call `this.canvasEngine.setupInteractions((districtName) => this.selectDistrict(districtName));`.
2. In `recompilePaths()`:
   Pass `this.canvasEngine.offsetX` and `this.canvasEngine.offsetY` to `compilePaths(...)` and `project(lon, lat, S, ox, oy)`.

### File 4: `src/frontend/dashboard.html`
1. Insert the `.map-controls-pill` container with `#mapZoomInBtn`, `#mapZoomOutBtn`, `#mapResetViewBtn`, `#mapFullscreenBtn` inside `.viewport-canvas-container`.

### File 5: `src/frontend/static/js/ui.js`
1. Bind click listeners for the 4 navigation buttons in `bindEvents()`.
2. Implement `toggleMapFullscreen()`.
3. Add keyboard hotkeys (`+`, `-`, `0`, `Escape`, `f`) in `window.addEventListener('keydown', ...)`.

### File 6: `src/frontend/static/css/tokens.css`
1. Add `.map-controls-pill` and `.map-ctrl-btn` styles.
2. In `.viewport-canvas-container`, set `min-height: 520px; aspect-ratio: 16 / 10;`.
3. In responsive media query `@media (max-width: 1100px)`:
   Ensure `.zone-4-sidebar` expands to 100% width with a responsive grid:
   ```css
   @media (max-width: 1100px) {
     .console-body {
       grid-template-columns: 1fr;
     }
     .zone-4-sidebar {
       width: 100%;
       display: grid;
       grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
       gap: 12px;
     }
   }
   @media (max-width: 680px) {
     .zone-4-sidebar {
       grid-template-columns: 1fr;
     }
   }
   ```

---

## 8. Verification Strategy & Test Plan

1. **Unit Tests (`tests/unit/test_transformations.py` or new M7 test)**:
   - Verify `computeFittedScale` produces identical aspect ratios across 16:9, 4:3, 1:1, and 9:16 viewports.
   - Verify all 4 bounding box corners and southern districts (Rahim Yar Khan, Multan, Bahawalpur) map strictly within $[P_x, W - P_x]$ and $[P_y, H - P_y]$.
   - Verify roundtrip invertibility: `unproject(project(lon, lat)) == (lon, lat)`.
2. **Integration Tests (`tests/integration/test_m7_map_controls.py`)**:
   - Verify pan translation and zoom math in Node.js / headless Python runner.
   - Verify click hit-testing maps back to the correct district name under arbitrary pan and zoom.
   - Verify zero DOM memory leaks during continuous pan/zoom manipulation.
3. **Automated Suite Run**:
   - Run `py -m pytest tests/unit tests/integration` to ensure 100% passing test status with zero regressions.
