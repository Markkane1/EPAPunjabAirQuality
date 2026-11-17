# Modern Web Platform Legacy Pattern Scan Report

**Document Reference:** `docs/MODERN_WEB_LEGACY_SCAN_REPORT.md`  
**Scan Engine:** `modern-web-guidance@latest legacy-scan` (Skill Version: `2026_11_10-47b4c80e`)  
**Target:** Project Root (`.`)  
**Date:** November 17, 2026  
**Status:** Completed & Verified  

---

## 1. Executive Summary

A deterministic legacy web platform scan was conducted across the codebase using `modern-web-guidance legacy-scan`. The scanner evaluated **52 deterministic rules across 38 guidance domains** (~20% of the modern web platform catalog) to identify obsolete APIs, deprecated CSS vendor pseudo-elements, parser-heavy DOM manipulation, and pre-ES2023 JavaScript idioms.

### Scan Summary Metrics
- **Total Findings Detected:** 21
- **Verified True Positives:** 21 (100% precision)
- **False Positives Dropped:** 0
- **Primary Impact Areas:**
  1. **CSS Scrollbar Customization:** 4 occurrences of vendor-prefixed `::-webkit-scrollbar` without standard W3C CSS properties.
  2. **Defensive Array Copying before Sorting:** 5 occurrences of shallow array copying (`.slice()`, `[...arr]`) prior to `.sort()`.
  3. **DOM Container Clearing via Parser:** 12 occurrences of `innerHTML = ''` instead of `element.replaceChildren()`.

---

## 2. Detailed Findings by Category

### Category A: Vendor `::-webkit-scrollbar` Pseudo-Elements
- **Guide ID:** `customize-scrollbar-color-and-thickness`
- **Rule ID:** `customize-scrollbar-color-and-thickness`
- **Standard Baseline:** Baseline Widely Available (CSS Scrollbars Level 1: `scrollbar-color`, `scrollbar-width`).
- **Total Instances:** 4

#### Issue Description
Styling scrollbars with `::-webkit-scrollbar` and `::-webkit-scrollbar-thumb` is a non-standard vendor extension that originated in WebKit. It does not work in Firefox without polyfills, causes layout reflows in modern rendering engines, and ignores user accessibility preferences (such as high-contrast OS scrollbars). Modern browsers support standard `scrollbar-width` and `scrollbar-color`.

#### Locations
| File | Line | Snippet |
| :--- | :---: | :--- |
| `src/frontend/static/css/tokens.css` | 775 | `.zone-4-sidebar::-webkit-scrollbar {` |
| `src/frontend/static/css/tokens.css` | 783 | `.zone-4-sidebar::-webkit-scrollbar-thumb {` |
| `ui-mock/index.html` | 98 | `aside::-webkit-scrollbar { width: 8px; }` |
| `ui-mock/index.html` | 99 | `aside::-webkit-scrollbar-thumb { background: rgba(36, 28, 22, 0.2); border-radius: 99px; }` |

#### Recommended Modernization Pattern
```css
/* Legacy Pattern */
.zone-4-sidebar::-webkit-scrollbar {
  width: 8px;
}
.zone-4-sidebar::-webkit-scrollbar-thumb {
  background: rgba(36, 28, 22, 0.2);
}

/* Modern Standard (W3C CSS Scrollbars Level 1) */
.zone-4-sidebar {
  scrollbar-width: thin;
  scrollbar-color: rgba(36, 28, 22, 0.2) transparent;
}

/* Optional graceful fallback for legacy WebKit browsers only */
@supports not (scrollbar-color: auto) {
  .zone-4-sidebar::-webkit-scrollbar { width: 8px; }
  .zone-4-sidebar::-webkit-scrollbar-thumb { background: rgba(36, 28, 22, 0.2); }
}
```

---

### Category B: Shallow Array Copying Prior to Sorting
- **Guide ID:** `js`
- **Rule ID:** `js/copying-array-methods`
- **Standard Baseline:** Baseline 2023 Widely Available (ECMAScript 2023: `toSorted()`, `toReversed()`, `with()`).
- **Total Instances:** 5

#### Issue Description
In pre-ES2023 JavaScript, `Array.prototype.sort()` mutates the underlying array in-place. To avoid state corruption, developers defensively wrote `[...arr].sort()` or `arr.slice().sort()`. ES2023 introduced non-mutating array methods (`toSorted()`, `toReversed()`, `toSpliced()`) which return a new sorted array directly, reducing allocation overhead and improving code readability.

#### Locations
| File | Line | Snippet |
| :--- | :---: | :--- |
| `src/frontend/static/js/app.js` | 1422 | `const ls = Q.frames[fr].l.slice().sort((a, b) => b[2] - a[2]);` |
| `src/frontend/static/js/canvas.js` | 1064 | `const sortedDistricts = [...this.districts].sort((a, b) => { ... });` |
| `src/workstation/state.ts` | 279 | `const sorted = [...values].sort((a, b) => a - b);` |
| `src/workstation/state.ts` | 362 | `const districts = input.districtRows.filter(...).slice().sort((a, b) => ...);` |
| `ui-mock/index.html` | 925 | `const list = A.districts.slice().sort((a, b) => { ... });` |

#### Recommended Modernization Pattern
```typescript
// Legacy Pattern
const sorted = [...values].sort((a, b) => a - b);
const ls = Q.frames[fr].l.slice().sort((a, b) => b[2] - a[2]);

// Modern Standard (ES2023 Non-Mutating Array Methods)
const sorted = values.toSorted((a, b) => a - b);
const ls = Q.frames[fr].l.toSorted((a, b) => b[2] - a[2]);
```

---

### Category C: DOM Container Clearing via `innerHTML = ''`
- **Guide ID:** `js`
- **Rule ID:** `js/replace-children-innerhtml`
- **Standard Baseline:** Baseline Widely Available (DOM Level 4: `Element.prototype.replaceChildren()`, supported since Chrome 86+, Firefox 78+, Safari 14+).
- **Total Instances:** 12

#### Issue Description
Assigning `element.innerHTML = ''` forces the browser's HTML parser to spin up, tokenize the empty string, and reset the DOM tree. Furthermore, in environments with Content Security Policy (CSP) enforcing **Trusted Types**, assigning to `innerHTML` violates security policies unless passed through an explicit sanitizer policy. The native DOM method `element.replaceChildren()` atomically removes all children in C++ engine memory without invoking the parser or triggering Trusted Types security audits.

#### Locations
| File | Line | Snippet |
| :--- | :---: | :--- |
| `src/frontend/static/js/app.js` | 146 | `selDropdown.innerHTML = '';` |
| `src/frontend/static/js/ui.js` | 185 | `this.dom.csvQuarantineArea.innerHTML = '';` |
| `src/frontend/static/js/ui.js` | 442 | `this.dom.pollutantStrip.innerHTML = '';` |
| `src/frontend/static/js/ui.js` | 665 | `this.dom.airportTableBody.innerHTML = '';` |
| `src/frontend/static/js/ui.js` | 692 | `this.dom.districtRankedList.innerHTML = '';` |
| `src/frontend/static/js/ui.js` | 733 | `this.dom.selectedDistrictTableBody.innerHTML = '';` |
| `src/frontend/static/js/ui.js` | 799 | `this.dom.lahoreTableBody.innerHTML = '';` |
| `src/frontend/static/js/ui.js` | 866 | `this.dom.crossBorderTableBody.innerHTML = '';` |
| `src/frontend/static/js/ui.js` | 1115 | `this.dom.csvQuarantineArea.innerHTML = '';` |
| `src/frontend/static/js/ui.js` | 1142 | `if (this.dom.csvQuarantineArea) this.dom.csvQuarantineArea.innerHTML = '';` |
| `src/frontend/static/js/ui.js` | 1275 | `this.dom.fireMonthlyChartContainer.innerHTML = '';` |
| `src/frontend/static/js/ui.js` | 1340 | `this.dom.panelFireTableBody.innerHTML = '';` |

#### Recommended Modernization Pattern
```javascript
// Legacy Pattern
this.dom.districtRankedList.innerHTML = '';
this.dom.pollutantStrip.innerHTML = '';

// Modern Standard (Fast, Trusted Types Compliant)
this.dom.districtRankedList.replaceChildren();
this.dom.pollutantStrip.replaceChildren();
```

---

## 3. Scope & Capabilities Note

The `legacy-scan` utility evaluates a focused subset of the web platform guidance corpus (**52 deterministic rules across 38 guides**, representing ~20% of the entire guidance database). It specifically targets high-confidence anti-patterns that can be identified deterministically across static ASTs and regex tokenizers.

Additional modern platform capabilities that can be evaluated during active feature development via `npx modern-web-guidance search "<topic>"` include:
- **CSS Container Queries & Subgrid:** Responsive widget design decoupled from the global viewport.
- **CSS `:has()` Relational Selector:** Dynamic state styling without JavaScript class toggling.
- **Dialog & Popover APIs:** Native top-layer modal and popover primitives replacing synthetic overlays.
- **View Transitions API:** Smooth state-to-state page transitions for temporal scrubbers.
- **Web Workers & OffscreenCanvas:** Offloading geostatistical IDW calculation off the main UI thread.

---

## 4. Remediation Plan

| Priority | Category | Action | Effort | Status |
| :---: | :--- | :--- | :---: | :---: |
| **High** | `replace-children-innerhtml` | Replace all 12 `element.innerHTML = ''` with `element.replaceChildren()` in `ui.js` and `app.js`. Eliminates HTML parser overhead and prepares codebase for Trusted Types. | ~10 mins | **COMPLETED** |
| **Medium** | `copying-array-methods` | Modernize array sorting in `state.ts`, `app.js`, `canvas.js`, and `index.html` to `toSorted()`. Eliminates redundant defensive shallow copies. | ~5 mins | **COMPLETED** |
| **Low** | `scrollbar-color-and-thickness` | Add `scrollbar-width: thin` and `scrollbar-color` to `.zone-4-sidebar` and `aside`. Wraps `::-webkit-scrollbar` in standard CSS. | ~5 mins | **COMPLETED** |

---

## 5. Remediation Verification & Scan Results

Following remediation, a re-scan was conducted with `npx.cmd -y modern-web-guidance@latest legacy-scan . --json`:

```json
{
  "targetDir": ".",
  "totalFindings": 0,
  "guides": [],
  "activeRuleCount": 52,
  "activeGuideCount": 38,
  "note": "No legacy patterns found across 38 guides (52 rules; ~20% of the guidance corpus). Use 'search <topic>' for feature-specific guidance.",
  "skippedDocsAndTestsCount": 8
}
```

**Verification Status:** **100% CLEAN (0 Findings Detected across all 52 deterministic rules and 38 guides).**

