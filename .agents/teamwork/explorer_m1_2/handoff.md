# Milestone 1 Investigation Report: Design Tokens, Color Contrast (WCAG 2.1 AAA), and Typography

**Agent**: `explorer_m1_2`  
**State Folder**: `c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\explorer_m1_2`  
**Date**: 2026-11-11  
**Status**: COMPLETE  

---

## 1. Observation

### 1.1 Direct File Observations

1. **`docs/UI_UX_SPECIFICATION.md` (lines 124–170)**:
   - Defined surface and ink tokens:
     ```css
     /* Surface & Container Colors */
     --color-bg-canvas: #0f1716;             /* Deep atmospheric slate background */
     --color-bg-panel: #152120;              /* Card and sidebar background */
     --color-bg-panel-elevated: #1c2b2a;     /* Hover and modal drawer background */
     --color-border-subtle: #2a3a38;
     --color-border-strong: #4f625e;

     /* Text & Ink Tokens (WCAG 2.1 AAA Compliant) */
     --color-ink-primary: #e3ece9;           /* Contrast ratio 14.2:1 against bg-panel */
     --color-ink-secondary: #93a39e;         /* Contrast ratio 7.8:1 against bg-panel */
     --color-ink-tertiary: #6b7a76;          /* Minimum 4.5:1 ratio for captions */
     ```
   - Light Theme Overrides (lines 152–159):
     ```css
     --color-bg-canvas: #eef1ef;
     --color-bg-panel: #fbfcfb;
     --color-bg-panel-elevated: #ffffff;
     --color-border-subtle: #d3dad7;
     --color-border-strong: #9aa6a2;
     --color-ink-primary: #17221f;           /* Contrast ratio 15.1:1 against bg-panel */
     --color-ink-secondary: #5b6964;         /* Contrast ratio 6.9:1 against bg-panel */
     --color-ink-tertiary: #7d8c87;
     ```
   - Accents (lines 21, 75 of `src/frontend/static/css/tokens.css`):
     - Dark mode `--accent: #5fc4c4;`
     - Light mode `--accent: #0d6e72;`

2. **`src/frontend/static/css/tokens.css` (lines 51–60)**:
   - Contained non-zero border radii:
     ```css
     --radius-xs: 2px;
     --radius-sm: 4px;
     --radius-md: 6px;
     ```
   - Contained non-IBM Plex font stacks:
     ```css
     --font-display: "Barlow Condensed", "Arial Narrow", -apple-system, sans-serif;
     --font-body: "Source Sans 3", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
     --font-mono: "JetBrains Mono", ui-monospace, "SFMono-Regular", Menlo, monospace;
     ```

3. **`PROJECT.md` & `ORIGINAL_REQUEST.md` (Mandatory Rules)**:
   - "WCAG 2.1 AAA design tokens in `src/styles/tokens.css` (>= 7.0:1 contrast)"
   - "Load exclusively IBM Plex Sans, IBM Plex Sans Condensed, and IBM Plex Mono typography, enforcing tabular-nums formatting on all numeric readouts."
   - "Do not use Tailwind CSS, generic fonts, consumer icon packs (lucide-react, heroicons), emojis, 3D tilted map perspectives, backdrop-filter blur, or drop shadows; use crisp 1.25px miter-joined inline SVGs or deck.gl primitives and 1px solid structural hairlines."

### 1.2 Empirical Luminance and Contrast Measurements of Existing Tokens

Relative luminance $L$ was computed using the official W3C WCAG 2.1 formula:
$$C_{\text{linear}} = \begin{cases} C_s / 12.92 & \text{if } C_s \le 0.04045 \\ ((C_s + 0.055) / 1.055)^{2.4} & \text{if } C_s > 0.04045 \end{cases}$$
$$L = 0.2126 R_{\text{linear}} + 0.7152 G_{\text{linear}} + 0.0722 B_{\text{linear}}$$
$$\text{Contrast Ratio} = \frac{L_{\text{lighter}} + 0.05}{L_{\text{darker}} + 0.05}$$

**Measurement Results for Existing Tokens:**
- **Dark Mode Surfaces**:
  - `--bg-canvas` (`#0f1716`): $L = 0.00772$
  - `--bg-panel` (`#152120`): $L = 0.01351$
  - `--bg-panel-elevated` (`#1c2b2a`): $L = 0.02142$
  - `--bg-dock` (`#131e1d`): $L = 0.01156$
  - `--bg-inspector` (`#152120`): $L = 0.01351$
- **Dark Mode Existing Inks**:
  - `--ink-primary` (`#e3ece9`, $L=0.82205$): CR = 13.73:1 against `--bg-panel` [PASS AAA]
  - `--ink-secondary` (`#93a39e`, $L=0.34866$):
    - Against `--bg-canvas`: CR = 6.91:1 [**FAIL AAA (< 7.0:1)**]
    - Against `--bg-panel`: CR = 6.28:1 [**FAIL AAA (< 7.0:1)**] (Note: Spec claimed 7.8:1, which was mathematically incorrect)
    - Against `--bg-panel-elevated`: CR = 5.58:1 [**FAIL AAA (< 7.0:1)**]
  - `--ink-tertiary` (`#6b7a76`, $L=0.18353$):
    - Against `--bg-canvas`: CR = 4.05:1 [**FAIL AAA (< 7.0:1)**]
    - Against `--bg-panel`: CR = 3.68:1 [**FAIL AAA (< 7.0:1)**]
  - `--accent` (`#5fc4c4`, $L=0.45898$):
    - Against `--bg-panel-elevated`: CR = 7.13:1 [PASS AAA]
    - Against `--bg-panel`: CR = 8.01:1 [PASS AAA]

- **Light Mode Surfaces**:
  - `--bg-canvas` (`#eef1ef`): $L = 0.87320$
  - `--bg-panel` (`#fbfcfb`): $L = 0.97095$
  - `--bg-panel-elevated` (`#ffffff`): $L = 1.00000$
  - `--bg-dock` (`#e8ecea`): $L = 0.83087$
  - `--bg-inspector` (`#fbfcfb`): $L = 0.97095$
- **Light Mode Existing Inks**:
  - `--ink-primary` (`#17221f`, $L=0.01425$): CR = 15.89:1 against `--bg-panel` [PASS AAA]
  - `--ink-secondary` (`#5b6964`, $L=0.13247$):
    - Against `--bg-dock`: CR = 4.83:1 [**FAIL AAA (< 7.0:1)**]
    - Against `--bg-canvas`: CR = 5.06:1 [**FAIL AAA (< 7.0:1)**]
    - Against `--bg-panel`: CR = 5.60:1 [**FAIL AAA (< 7.0:1)**]
  - `--ink-tertiary` (`#7d8c87`, $L=0.24865$):
    - Against `--bg-dock`: CR = 2.95:1 [**FAIL AAA (< 7.0:1)**]
    - Against `--bg-panel`: CR = 3.42:1 [**FAIL AAA (< 7.0:1)**]
  - `--accent` (`#0d6e72`, $L=0.12452$):
    - Against `--bg-dock`: CR = 5.05:1 [**FAIL AAA (< 7.0:1)**]
    - Against `--bg-canvas`: CR = 5.29:1 [**FAIL AAA (< 7.0:1)**]
    - Against `--bg-panel`: CR = 5.85:1 [**FAIL AAA (< 7.0:1)**]

---

## 2. Logic Chain

1. **Premise 1 (Regulatory Standard)**: Milestone 1 requires institutional atmospheric physics workstation design with WCAG 2.1 AAA luminance contrast $\ge 7.0:1$ across **all** text/surface color pairs in both dark and light modes.
2. **Premise 2 (Surface Boundaries)**: The workstation has 5 discrete layout zones with designated backgrounds:
   - Canvas: `#0f1716` (dark), `#eef1ef` (light)
   - Panel / Inspector: `#152120` (dark), `#fbfcfb` (light)
   - Panel Elevated / Modals: `#1c2b2a` (dark), `#ffffff` (light)
   - Dock: `#131e1d` (dark), `#e8ecea` (light)
   - Command Bar / Scrubber: `#111a19` (dark), `#f4f6f5` (light)
3. **Premise 3 (Mathematical Thresholds)**:
   - For Dark Mode, the brightest background is `#1c2b2a` ($L = 0.02142$). To guarantee contrast ratio $\frac{L_{\text{ink}} + 0.05}{0.02142 + 0.05} \ge 7.0$, the ink luminance must satisfy $L_{\text{ink}} \ge 7.0 \times 0.07142 - 0.05 = 0.44994$.
   - For Light Mode, the darkest background surface is `#e8ecea` ($L = 0.83087$). To guarantee contrast ratio $\frac{0.83087 + 0.05}{L_{\text{ink}} + 0.05} \ge 7.0$, the ink luminance must satisfy $L_{\text{ink}} \le \frac{0.88087}{7.0} - 0.05 = 0.07584$.
4. **Premise 4 (Evaluation of Prior Tokens)**:
   - Prior dark `--ink-secondary` (`#93a39e`, $L=0.34866 < 0.44994$) failed AAA with only 5.58:1 to 6.91:1.
   - Prior dark `--ink-tertiary` (`#6b7a76`, $L=0.18353 < 0.44994$) failed AAA with only 3.27:1 to 4.05:1.
   - Prior light `--ink-secondary` (`#5b6964`, $L=0.13247 > 0.07584$) failed AAA with only 4.83:1 to 5.60:1.
   - Prior light `--ink-tertiary` (`#7d8c87`, $L=0.24865 > 0.07584$) failed AAA with only 2.95:1 to 3.42:1.
   - Prior light `--accent` (`#0d6e72`, $L=0.12452 > 0.07584$) failed AAA with only 5.05:1 to 5.85:1.
5. **Deduction (Calibrated Solutions)**:
   - Calibrating Dark `--ink-secondary` to `#c0cfcb` ($L = 0.60144$) raises contrast to **9.12:1 – 11.29:1** (PASS AAA).
   - Calibrating Dark `--ink-tertiary` to `#a8bbb5` ($L = 0.47202$) raises contrast to **7.31:1 – 9.04:1** (PASS AAA).
   - Keeping Dark `--accent` at `#5fc4c4` ($L = 0.45898$) maintains contrast at **7.13:1 – 8.82:1** (PASS AAA).
   - Calibrating Light `--ink-secondary` to `#34423e` ($L = 0.04974$) raises contrast to **8.83:1 – 10.53:1** (PASS AAA).
   - Calibrating Light `--ink-tertiary` to `#3d4c48` ($L = 0.06629$) raises contrast to **7.57:1 – 9.03:1** (PASS AAA).
   - Calibrating Light `--accent` to `#084e51` ($L = 0.06094$) raises contrast to **7.94:1 – 9.46:1** (PASS AAA).
6. **Premise 5 (Structural and Typography Constraints)**:
   - The prior CSS defined rounded corners (`2px`, `4px`, `6px`), drop shadows, and non-conforming fonts (`Barlow Condensed`, `Source Sans 3`, `JetBrains Mono`).
   - The workstation requirements mandate strict **0px border-radius**, **zero drop shadows**, **zero backdrop-filter blur**, **1px solid structural hairlines**, and exclusively **IBM Plex** fonts (`IBM Plex Sans`, `IBM Plex Sans Condensed`, `IBM Plex Mono`) with `tabular-nums` formatting.

---

## 3. Caveats

1. **Statutory PEPC Mid-Tone Alert Contrast**: The statutory PEPC color for Unhealthy is pure red (`#FF0000`, $L=0.2126$). A solid red background cannot achieve 7.0:1 contrast with either pure white (4.00:1) or pure black (5.25:1). Therefore, regulatory chips and alert banners must use either:
   - A dark tinted background container (e.g. `#331114`, CR > 10:1 with white text) paired with a 1px solid `#FF0000` statutory border and a `#FF0000` status dot, OR
   - High-contrast text paired with high-luminance alert badges.
   Both options are supported in our token definitions.
2. **Device Pixel Ratio**: Hairlines are specified as `1px solid`. On high-DPI displays (Retina, 2x+), browsers render 1px as 2 physical device pixels unless fractional borders are used; `1px solid` is the standard cross-browser implementation of the hairline contract.
3. **No Code Written**: In accordance with the Explorer archetype rules, no source files were modified in `src/`. Ready-to-implement CSS files and specifications are detailed below for `worker_m1`.

---

## 4. Conclusion & Complete Specifications

### 4.1 Comparative Contrast Matrix (Old vs New)

| Token Key | Prior Hex | Prior L | Prior Worst CR | Prior Status | Calibrated Hex | Calibrated L | Calibrated Worst CR | Calibrated Status |
|---|---|---|---|---|---|---|---|---|
| **Dark `--ink-secondary`** | `#93a39e` | 0.34866 | 5.58:1 | ❌ FAIL AAA | **`#c0cfcb`** | 0.60144 | **9.12:1** (`#1c2b2a`) | ✅ **PASS AAA** |
| **Dark `--ink-tertiary`** | `#6b7a76` | 0.18353 | 3.27:1 | ❌ FAIL AAA | **`#a8bbb5`** | 0.47202 | **7.31:1** (`#1c2b2a`) | ✅ **PASS AAA** |
| **Dark `--accent`** | `#5fc4c4` | 0.45898 | 7.13:1 | ✅ PASS AAA | **`#5fc4c4`** | 0.45898 | **7.13:1** (`#1c2b2a`) | ✅ **PASS AAA** |
| **Light `--ink-secondary`**| `#5b6964` | 0.13247 | 4.83:1 | ❌ FAIL AAA | **`#34423e`** | 0.04974 | **8.83:1** (`#e8ecea`) | ✅ **PASS AAA** |
| **Light `--ink-tertiary`** | `#7d8c87` | 0.24865 | 2.95:1 | ❌ FAIL AAA | **`#3d4c48`** | 0.06629 | **7.57:1** (`#e8ecea`) | ✅ **PASS AAA** |
| **Light `--accent`** | `#0d6e72` | 0.12452 | 5.05:1 | ❌ FAIL AAA | **`#084e51`** | 0.06094 | **7.94:1** (`#e8ecea`) | ✅ **PASS AAA** |

### 4.2 Comprehensive Matrix Across All Five Workstation Surfaces

#### Dark Mode ($\ge 7.0:1$ Target)
| Surface | Surface Hex | Surface L | `--ink-primary` (`#e3ece9`) | `--ink-secondary` (`#c0cfcb`) | `--ink-tertiary` (`#a8bbb5`) | `--accent` (`#5fc4c4`) |
|---|---|---|---|---|---|---|
| `--bg-canvas` | `#0f1716` | 0.00772 | **15.11:1** (PASS) | **11.29:1** (PASS) | **9.04:1** (PASS) | **8.82:1** (PASS) |
| `--bg-panel` | `#152120` | 0.01351 | **13.73:1** (PASS) | **10.26:1** (PASS) | **8.22:1** (PASS) | **8.01:1** (PASS) |
| `--bg-panel-elevated` | `#1c2b2a` | 0.02142 | **12.21:1** (PASS) | **9.12:1** (PASS) | **7.31:1** (PASS) | **7.13:1** (PASS) |
| `--bg-dock` | `#131e1d` | 0.01156 | **14.17:1** (PASS) | **10.58:1** (PASS) | **8.48:1** (PASS) | **8.27:1** (PASS) |
| `--bg-inspector` | `#152120` | 0.01351 | **13.73:1** (PASS) | **10.26:1** (PASS) | **8.22:1** (PASS) | **8.01:1** (PASS) |
| `--bg-command-bar` | `#111a19` | 0.00928 | **14.71:1** (PASS) | **10.99:1** (PASS) | **8.81:1** (PASS) | **8.59:1** (PASS) |
| `--bg-scrubber` | `#111a19` | 0.00928 | **14.71:1** (PASS) | **10.99:1** (PASS) | **8.81:1** (PASS) | **8.59:1** (PASS) |

#### Light Mode ($\ge 7.0:1$ Target)
| Surface | Surface Hex | Surface L | `--ink-primary` (`#17221f`) | `--ink-secondary` (`#34423e`) | `--ink-tertiary` (`#3d4c48`) | `--accent` (`#084e51`) |
|---|---|---|---|---|---|---|
| `--bg-canvas` | `#eef1ef` | 0.87320 | **14.37:1** (PASS) | **9.26:1** (PASS) | **7.94:1** (PASS) | **8.32:1** (PASS) |
| `--bg-panel` | `#fbfcfb` | 0.97095 | **15.89:1** (PASS) | **10.24:1** (PASS) | **8.78:1** (PASS) | **9.20:1** (PASS) |
| `--bg-panel-elevated` | `#ffffff` | 1.00000 | **16.34:1** (PASS) | **10.53:1** (PASS) | **9.03:1** (PASS) | **9.46:1** (PASS) |
| `--bg-dock` | `#e8ecea` | 0.83087 | **13.71:1** (PASS) | **8.83:1** (PASS) | **7.57:1** (PASS) | **7.94:1** (PASS) |
| `--bg-inspector` | `#fbfcfb` | 0.97095 | **15.89:1** (PASS) | **10.24:1** (PASS) | **8.78:1** (PASS) | **9.20:1** (PASS) |
| `--bg-command-bar` | `#f4f6f5` | 0.91737 | **15.06:1** (PASS) | **9.70:1** (PASS) | **8.32:1** (PASS) | **8.72:1** (PASS) |
| `--bg-scrubber` | `#f4f6f5` | 0.91737 | **15.06:1** (PASS) | **9.70:1** (PASS) | **8.32:1** (PASS) | **8.72:1** (PASS) |

### 4.3 Statutory PEPC 7-Tier Scale Specification

| Tier # | Statutory Category | AQI Range | PM2.5 (24h) | Official Hex | Relative Luminance $L$ | Recommended Badge Text Ink | Contrast Ratio on Badge |
|---|---|---|---|---|---|---|---|
| Tier 0 | **Good** | $(0, 50]$ | $(0.0, 15.0]\ \mu\text{g/m}^3$ | `#00B050` | 0.31630 | `#000000` | **7.33:1** (PASS AAA) |
| Tier 1 | **Satisfactory** | $(50, 100]$ | $(15.0, 35.0]\ \mu\text{g/m}^3$ | `#92D050` | 0.51802 | `#000000` | **11.36:1** (PASS AAA) |
| Tier 2 | **Moderate** | $(100, 150]$ | $(35.0, 70.0]\ \mu\text{g/m}^3$ | `#FFFF00` | 0.92780 | `#000000` | **19.56:1** (PASS AAA) |
| Tier 3 | **Unhealthy (Sensitive)** | $(150, 200]$ | $(70.0, 140.0]\ \mu\text{g/m}^3$ | `#ED7D31` | 0.32894 | `#000000` | **7.58:1** (PASS AAA) |
| Tier 4 | **Unhealthy** | $(200, 300]$ | $(140.0, 250.0]\ \mu\text{g/m}^3$ | `#FF0000` | 0.21260 | Alert container: `#ffffff` on `#381215` | **12.45:1** (PASS AAA) |
| Tier 5 | **Very Unhealthy** | $(300, 400]$ | $(250.0, 350.0]\ \mu\text{g/m}^3$ | `#7030A0` | 0.08097 | `#ffffff` | **8.02:1** (PASS AAA) |
| Tier 6 | **Hazardous** | $(400, 500]$ | $> 350.0\ \mu\text{g/m}^3$ | `#C00000` | 0.11206 | Alert container: `#ffffff` on `#330a0a` | **13.52:1** (PASS AAA) |
| Clamp | **Emergency** | $> 500$ (Clamp) | $> 500.0\ \mu\text{g/m}^3$ | `#4A154B` | 0.02758 | `#ffffff` | **13.54:1** (PASS AAA) |

---

### 4.4 Proposed Complete `src/styles/tokens.css`

```css
/* ==========================================================================
   EPA PUNJAB AIR QUALITY WORKSTATION - DESIGN SYSTEM TOKENS
   Strict WCAG 2.1 AAA Luminance Contrast (>= 7.0:1) Across All Text/Surfaces
   Institutional Physics Console: 1px Hairlines | 0px Radius | 0 Blur | 0 Shadows
   ========================================================================== */

:root {
  /* ==========================================
     Surfaces & Workstation Grid Zones (Dark)
     ========================================== */
  --bg-canvas: #0f1716;              /* Zone 3 Central planimetric map canvas */
  --bg-panel: #152120;               /* Base panel surface */
  --bg-panel-elevated: #1c2b2a;      /* Hover states, modal dialogs, drawers */
  --bg-dock: #131e1d;                /* Zone 2 Spatial Control Dock */
  --bg-inspector: #152120;           /* Zone 4 Receptor Inspector */
  --bg-command-bar: #111a19;         /* Zone 1 Top Command Bar */
  --bg-scrubber: #111a19;            /* Zone 5 Temporal Playback Scrubber */
  --bg-overlay: rgba(15, 23, 22, 0.92);

  /* ==========================================
     Structural Hairlines & Dividers (Dark)
     ========================================== */
  --border-subtle: #2a3a38;
  --border-strong: #4f625e;
  --border-hairline: 1px solid var(--border-subtle);
  --border-hairline-strong: 1px solid var(--border-strong);
  --border-hairline-accent: 1px solid var(--accent);
  --border-width-hairline: 1px;
  --border-style-hairline: solid;

  /* ==========================================
     Text & Ink Tokens (Dark Mode - All >= 7.0:1)
     ========================================== */
  --ink-primary: #e3ece9;            /* Luminance 0.82205 | 12.21:1 to 15.11:1 */
  --ink-secondary: #c0cfcb;          /* Luminance 0.60144 | 9.12:1 to 11.29:1 */
  --ink-tertiary: #a8bbb5;           /* Luminance 0.47202 | 7.31:1 to 9.04:1 */
  --ink-inverse: #111a19;            /* High-contrast text on bright chips */

  /* ==========================================
     Accent, Focus & Instrument Status (Dark)
     ========================================== */
  --accent: #5fc4c4;                 /* Luminance 0.45898 | 7.13:1 to 8.82:1 */
  --accent-soft: rgba(95, 196, 196, 0.12);
  --focus-ring: 2px solid var(--accent);
  --focus-offset: 2px;
  --pulse-live: #00B050;
  --pulse-warn: #ED7D31;
  --pulse-user: #5fc4c4;

  /* ==========================================
     Statutory PEPC 7-Stop Palette & Contrast Inks
     ========================================== */
  --pepc-good: #00B050;
  --pepc-satisfactory: #92D050;
  --pepc-moderate: #FFFF00;
  --pepc-unhealthy-sensitive: #ED7D31;
  --pepc-unhealthy: #FF0000;
  --pepc-very-unhealthy: #7030A0;
  --pepc-hazardous: #C00000;
  --pepc-emergency: #4A154B;

  --pepc-good-ink: #000000;          /* 7.33:1 on #00B050 */
  --pepc-satisfactory-ink: #000000;  /* 11.36:1 on #92D050 */
  --pepc-moderate-ink: #000000;      /* 19.56:1 on #FFFF00 */
  --pepc-unhealthy-sensitive-ink: #000000; /* 7.58:1 on #ED7D31 */
  --pepc-unhealthy-ink: #ffffff;
  --pepc-very-unhealthy-ink: #ffffff;/* 8.02:1 on #7030A0 */
  --pepc-hazardous-ink: #ffffff;
  --pepc-emergency-ink: #ffffff;    /* 13.54:1 on #4A154B */

  /* ==========================================
     Cartographic Fills (Deck.gl & MapLibre)
     ========================================== */
  --geo-sea: #0b1211;
  --geo-land: #162120;
  --geo-punjab: #1d2d2c;
  --geo-district-border: #4f625e;
  --geo-international: #ff7a6b;
  --geo-india-fill: #26231a;

  /* ==========================================
     Physical Advection & Transport Dynamics
     ========================================== */
  --flow-link: #e3f4f2;
  --flow-particle: rgba(225, 245, 242, 0.38);
  --flow-inflow: #ff6b5e;            /* Cross-border easterly inflow chevron */
  --flow-outflow: #5fc4c4;           /* Cross-border outflow chevron */

  /* ==========================================
     Rigid Structural Constraints (Strict Bans)
     ========================================== */
  --radius-none: 0px;
  --radius-xs: 0px;
  --radius-sm: 0px;
  --radius-md: 0px;
  --radius-lg: 0px;
  --border-radius-none: 0px;

  --shadow-none: none;
  --shadow-card: none;
  --shadow-overlay: none;
  --box-shadow-none: none;

  --blur-none: none;
  --backdrop-blur-none: none;

  --svg-stroke-width: 1.25px;
  --svg-stroke-linejoin: miter;
  --svg-stroke-linecap: square;

  /* ==========================================
     8-Point Spatial Layout Grid Dimensions
     ========================================== */
  --space-xxs: 2px;
  --space-xs: 4px;
  --space-sm: 8px;
  --space-md: 16px;
  --space-lg: 24px;
  --space-xl: 32px;
  --space-xxl: 48px;

  --dock-width: 360px;
  --inspector-width: 380px;
  --command-bar-height: 48px;
  --scrubber-height: 64px;
}

/* ==========================================================================
   Light Mode Overrides (Strict WCAG 2.1 AAA All Inks >= 7.0:1)
   ========================================================================== */
[data-theme="light"], :root[data-theme="light"] {
  --bg-canvas: #eef1ef;
  --bg-panel: #fbfcfb;
  --bg-panel-elevated: #ffffff;
  --bg-dock: #e8ecea;
  --bg-inspector: #fbfcfb;
  --bg-command-bar: #f4f6f5;
  --bg-scrubber: #f4f6f5;
  --bg-overlay: rgba(238, 241, 239, 0.94);

  --border-subtle: #d3dad7;
  --border-strong: #9aa6a2;

  /* Calibrated Light Inks (Luminances <= 0.075 to beat dock at 0.83087) */
  --ink-primary: #17221f;            /* Luminance 0.01425 | 13.71:1 to 16.34:1 */
  --ink-secondary: #34423e;          /* Luminance 0.04974 | 8.83:1 to 10.53:1 */
  --ink-tertiary: #3d4c48;           /* Luminance 0.06629 | 7.57:1 to 9.03:1 */
  --ink-inverse: #fbfcfb;

  --accent: #084e51;                 /* Luminance 0.06094 | 7.94:1 to 9.46:1 */
  --accent-soft: rgba(8, 78, 81, 0.12);
  --pulse-live: #00873d;
  --pulse-warn: #cf6217;
  --pulse-user: #084e51;

  --geo-sea: #e3e8e5;
  --geo-land: #eceeec;
  --geo-punjab: #f8f9f8;
  --geo-district-border: #9aa6a2;
  --geo-international: #a3261f;
  --geo-india-fill: #efe8d8;

  --flow-link: #18302f;
  --flow-particle: rgba(20, 40, 40, 0.32);
  --flow-inflow: #c4312a;
  --flow-outflow: #084e51;
}

/* Enforce absolute suppression of rounded corners, drop shadows, and blur */
*, *::before, *::after {
  border-radius: 0px !important;
  box-shadow: none !important;
  text-shadow: none !important;
  backdrop-filter: none !important;
  -webkit-backdrop-filter: none !important;
}
```

---

### 4.5 Proposed Complete `src/styles/typography.css`

```css
/* ==========================================================================
   EPA PUNJAB AIR QUALITY WORKSTATION - TYPOGRAPHY SPECIFICATION
   Exclusively IBM Plex Sans | IBM Plex Sans Condensed | IBM Plex Mono
   Strict Tabular-Nums Formatting | Zero Emojis Enforced
   ========================================================================== */

:root {
  --font-body: "IBM Plex Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  --font-condensed: "IBM Plex Sans Condensed", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  --font-mono: "IBM Plex Mono", "SFMono-Regular", Menlo, Monaco, Consolas, monospace;
}

/* ==========================================
   Global Base Typography & Anti-Aliasing
   ========================================== */
html {
  font-family: var(--font-body);
  font-size: 13px;
  line-height: 1.45;
  color: var(--ink-primary);
  background-color: var(--bg-canvas);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-rendering: optimizeLegibility;
}

body {
  font-family: var(--font-body);
  color: var(--ink-primary);
  background-color: var(--bg-canvas);
  margin: 0;
  padding: 0;
  overflow: hidden; /* Rigid 100vw x 100vh Workstation Layout */
}

/* ==========================================
   Tabular-Nums Enforcement (Mandatory)
   ========================================== */
.tabular-nums,
.num,
.metric,
.telemetry-val,
.coordinate,
.timestamp,
.station-code,
table td.numeric,
input[type="number"] {
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
  font-feature-settings: "tnum" 1, "zero" 1;
}

/* ==========================================
   Typographic Scale Classes
   ========================================== */

/* Display Header: Workstation title & major alert banners */
.display-header {
  font-family: var(--font-body);
  font-size: 20px;
  line-height: 24px;
  font-weight: 700;
  letter-spacing: -0.01em;
  color: var(--ink-primary);
}

/* Section Header: Dock titles, inspector panels, drawer headings */
.section-header {
  font-family: var(--font-condensed);
  font-size: 14px;
  line-height: 18px;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--ink-secondary);
}

/* Component Label: Toolbar buttons, select boxes, table headers */
.component-label {
  font-family: var(--font-body);
  font-size: 12px;
  line-height: 16px;
  font-weight: 600;
  letter-spacing: 0.02em;
  color: var(--ink-secondary);
}

/* Body Scientific: Qualitative analysis, methodology text, notes */
.body-scientific {
  font-family: var(--font-body);
  font-size: 13px;
  line-height: 18px;
  font-weight: 400;
  color: var(--ink-primary);
}

/* Data Dense Matrix / Tables / Compact Chips */
.dense-data,
.data-chip,
.ranking-cell {
  font-family: var(--font-condensed);
  font-size: 12px;
  line-height: 15px;
  font-weight: 500;
  color: var(--ink-primary);
}

/* Telemetry Readout: Live concentrations, scalars, wind vector magnitudes */
.telemetry-value {
  font-family: var(--font-mono);
  font-size: 16px;
  line-height: 20px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  color: var(--ink-primary);
}

/* Caption / Coordinate / Ticks: Map axes, timestamps, lat/lon */
.caption-tick {
  font-family: var(--font-mono);
  font-size: 10px;
  line-height: 13px;
  font-weight: 400;
  font-variant-numeric: tabular-nums;
  letter-spacing: 0.03em;
  color: var(--ink-tertiary);
}

/* ==========================================
   Strict Absence of Emojis
   ========================================== */
/* Emoji font fallbacks (Apple Color Emoji, Segoe UI Emoji, Noto Color Emoji)
   are intentionally omitted from all font-family definitions above.
   Institutional standards mandate inline SVG icons (1.25px stroke) and deck.gl
   geometry glyphs exclusively. */
```

---

## 5. Verification Method

To independently reproduce the luminance math and verify that all proposed color tokens meet or exceed WCAG 2.1 AAA contrast ($\ge 7.0:1$), run the following automated Python verification script:

```bash
python -c "
def srgb_to_linear(c):
    c = c / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

def relative_luminance(hex_code):
    h = hex_code.lstrip('#')
    return 0.2126 * srgb_to_linear(int(h[0:2], 16)) + 0.7152 * srgb_to_linear(int(h[2:4], 16)) + 0.0722 * srgb_to_linear(int(h[4:6], 16))

def contrast_ratio(h1, h2):
    l1, l2 = relative_luminance(h1), relative_luminance(h2)
    return (max(l1, l2) + 0.05) / (min(l1, l2) + 0.05)

dark_surfaces = {'bg-canvas': '#0f1716', 'bg-panel': '#152120', 'bg-panel-elevated': '#1c2b2a', 'bg-dock': '#131e1d', 'bg-inspector': '#152120', 'bg-command-bar': '#111a19', 'bg-scrubber': '#111a19'}
dark_inks = {'ink-primary': '#e3ece9', 'ink-secondary': '#c0cfcb', 'ink-tertiary': '#a8bbb5', 'accent': '#5fc4c4'}

light_surfaces = {'bg-canvas': '#eef1ef', 'bg-panel': '#fbfcfb', 'bg-panel-elevated': '#ffffff', 'bg-dock': '#e8ecea', 'bg-inspector': '#fbfcfb', 'bg-command-bar': '#f4f6f5', 'bg-scrubber': '#f4f6f5'}
light_inks = {'ink-primary': '#17221f', 'ink-secondary': '#34423e', 'ink-tertiary': '#3d4c48', 'accent': '#084e51'}

all_passed = True
for mode, s_dict, i_dict in [('DARK', dark_surfaces, dark_inks), ('LIGHT', light_surfaces, light_inks)]:
    print(f'=== {mode} MODE VERIFICATION ===')
    for s_name, s_hex in s_dict.items():
        for i_name, i_hex in i_dict.items():
            cr = contrast_ratio(i_hex, s_hex)
            if cr < 7.0:
                all_passed = False
                print(f'FAIL: {s_name} ({s_hex}) vs {i_name} ({i_hex}) -> {cr:.2f}:1')
            else:
                print(f'PASS: {s_name} ({s_hex}) vs {i_name} ({i_hex}) -> {cr:.2f}:1')

assert all_passed, 'WCAG AAA verification failed!'
print('\nALL TEXT/SURFACE PAIRS EXCEED 7.0:1 (WCAG 2.1 AAA VERIFIED).')
"
```

**Expected Result**: All 56 color combinations (28 Dark + 28 Light) output `PASS` with ratios ranging from `7.13:1` to `16.34:1`, terminating with assertion success: `ALL TEXT/SURFACE PAIRS EXCEED 7.0:1 (WCAG 2.1 AAA VERIFIED)`.

---
*Report prepared by Explorer Agent `explorer_m1_2`.*
