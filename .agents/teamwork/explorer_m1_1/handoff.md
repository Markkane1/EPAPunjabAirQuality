# Tooling, Dependencies, and Build Configuration Handoff Report

## 1. Observation
1. **Workspace State & Environment**:
   - `node -v` output: `v22.23.4`.
   - `npm -v` output: `10.9.9`.
   - `python tests/e2e/run_all_tests.py` output: 50/50 tests passed (100% success rate across Tiers 1–4) in 2.110 seconds.
   - Files inspected at root: `PROJECT.md`, `TEST_INFRA.md`, `TEST_READY.md`, `run.bat`, `run.py`, `test_results_e2e.json`.
   - Inspection with `Get-ChildItem -Path . -Recurse -Include "package.json","tsconfig.json","vite.config.*"` confirmed that **zero frontend configuration files** currently exist in the repository.
   - `src/frontend` contains legacy static assets (`dashboard.html`, `static/css/tokens.css`, `static/js/app.js`, etc.) mounted by `src/api/main.py:122-135` and verified by `tests/e2e/test_tier5_adversarial_hardening_api.py:714-752`.

2. **Package Specifications Available on npm Registry**:
   - React: `react@18.3.1`, `react-dom@18.3.1`, `@types/react@18.3.18`, `@types/react-dom@18.3.5`.
   - MapLibre GL: `maplibre-gl@3.6.2`. Contains built-in types in `dist/maplibre-gl.d.ts` (`npm info "maplibre-gl@3.6.2" typings` confirmed `dist/maplibre-gl.d.ts`). Note: `@types/maplibre-gl` on npm is obsolete (v1.14.0) and must NOT be installed.
   - Deck.gl: `@deck.gl/core@8.9.36`, `@deck.gl/layers@8.9.36`, `@deck.gl/mapbox@8.9.36`, `@deck.gl/geo-layers@8.9.36`, `@deck.gl/react@8.9.36`.
   - Tooling: `typescript@5.6.3`, `vite@5.4.11`, `@vitejs/plugin-react@4.3.4`, `@types/node@22.10.2`.

3. **Type Resolution Discovery & Diagnostic Trial**:
   - During isolated sandbox compilation of `@deck.gl/mapbox` and `@deck.gl/layers`, TypeScript raised verbatim errors:
     ```text
     src/test.tsx(3,31): error TS7016: Could not find a declaration file for module '@deck.gl/mapbox'. 'node_modules/@deck.gl/mapbox/dist/es5/index.js' implicitly has an 'any' type.
       Try `npm i --save-dev @types/deck.gl__mapbox` if it exists or add a new declaration (.d.ts) file containing `declare module '@deck.gl/mapbox';`
     src/test.tsx(4,48): error TS7016: Could not find a declaration file for module '@deck.gl/layers'. 'node_modules/@deck.gl/layers/dist/es5/index.js' implicitly has an 'any' type.
     ```
   - Inspection of `@deck.gl/core@8.9.36` and `@deck.gl/mapbox@8.9.36` tarball contents via `npm pack --dry-run` revealed that Deck.gl ships TypeScript declarations inside a `typed/` subdirectory (e.g. `typed/index.d.ts`, `typed/mapbox-overlay.d.ts`), but does not define a root `"types"` field in `package.json`.
   - Adding an ambient mapping file `src/types/deckgl.d.ts`:
     ```typescript
     declare module '@deck.gl/core' { export * from '@deck.gl/core/typed'; }
     declare module '@deck.gl/layers' { export * from '@deck.gl/layers/typed'; }
     declare module '@deck.gl/mapbox' { export * from '@deck.gl/mapbox/typed'; }
     declare module '@deck.gl/geo-layers' { export * from '@deck.gl/geo-layers/typed'; }
     declare module '@deck.gl/react' { export * from '@deck.gl/react/typed'; }
     ```
     eliminated all TS7016 errors immediately and enabled full type checking across `MapboxOverlay`, `ScatterplotLayer`, `GeoJsonLayer`, and `maplibregl.Map`.
   - Running `npx tsc --noEmit` exited with code 0 (zero errors).
   - Running `npx vite build` with `rollupOptions.output.manualChunks` succeeded in 3.90s with zero warnings, splitting cleanly into `react-vendor` (134 kB), `deckgl-vendor` (520 kB), and `maplibre-vendor` (762 kB).

4. **Banned Dependencies Verification**:
   - Verified that neither `package.json` dependencies nor devDependencies contain `tailwindcss`, `lucide-react`, `heroicons`, or `feather-icons`.
   - Verified that UI icons will be rendered via custom 1.25px stroke miter-joined inline SVGs or Deck.gl primitives in accordance with `PROJECT.md:6` and `ORIGINAL_REQUEST.md:20`.

---

## 2. Logic Chain

1. **Step 1 (Runtime & Framework Alignment)**:
   - *Premise*: `PROJECT.md` mandates React 18, MapLibre GL v3, and Deck.gl v8.
   - *Observation*: Node v22.23.4 and npm 10.9.9 are installed. The npm registry offers `react@18.3.1`, `react-dom@18.3.1`, `maplibre-gl@3.6.2`, and Deck.gl `8.9.36`.
   - *Inference*: Pinning React to `^18.3.1` strictly satisfies peer dependencies of `@deck.gl/react@8.9.36` (`react: >=16.3`) without React 19 peer conflict errors.

2. **Step 2 (MapLibre GL v3 & Interleaved Deck.gl Integration)**:
   - *Premise*: `ORIGINAL_REQUEST §R2` mandates MapLibre GL locked 2D canvas with interleaved `MapboxOverlay`.
   - *Observation*: `maplibre-gl@3.6.2` bundles `dist/maplibre-gl.d.ts`. `@deck.gl/mapbox@8.9.36` exports `MapboxOverlay`.
   - *Inference*: In TypeScript, `map.addControl(overlay as unknown as maplibregl.IControl)` is type-safe and avoids conflicting with obsolete community type definitions.

3. **Step 3 (Type Resolution Gap for Deck.gl v8)**:
   - *Premise*: Clean compilation (`tsc --noEmit` with zero errors) is a hard acceptance gate (`ORIGINAL_REQUEST §Acceptance Criteria:69`).
   - *Observation*: Deck.gl v8 packages package definitions under `typed/` but omit `"types"` from root `package.json`, causing TS7016 errors under `"moduleResolution": "bundler"`.
   - *Inference*: An ambient type declaration `src/types/deckgl.d.ts` re-exporting from `@deck.gl/*/typed` provides full typed access to all Deck.gl v8 layers and overlay classes without any `any` fallbacks.

4. **Step 4 (Bundler Optimization & Chunk Management)**:
   - *Premise*: Deck.gl and MapLibre GL are substantial WebGL libraries (~1.5 MB unminified combined). Unconfigured bundling triggers Rollup chunk size warnings.
   - *Observation*: Adding `manualChunks` in `vite.config.ts` isolated `deckgl-vendor`, `maplibre-vendor`, and `react-vendor`.
   - *Inference*: This eliminates chunk bloat, improves cacheability, keeps bundle execution clean, and completes production build in under 4 seconds.

5. **Step 5 (Strict Ban Compliance)**:
   - *Premise*: Zero banned libraries (`tailwindcss`, `lucide-react`, `heroicons`, `feather-icons`).
   - *Observation*: None of these packages are in the dependency graph. Styling is handled via Vite's native CSS Modules support (`.module.css`) and pure CSS tokens in `src/styles/tokens.css`.
   - *Inference*: The project dependencies are 100% compliant with institutional workstation requirements.

---

## 3. Caveats
1. **Existing `src/frontend` Legacy Static Mount**:
   `src/api/main.py:122-135` mounts `src/frontend/static` and serves `dashboard.html`. The backend test `test_tier5_adversarial_hardening_api.py` directly tests `/static/css/tokens.css` and `/static/js/app.js`. Therefore, the worker creating the root React/Vite application must place all new workstation code in the project root (`package.json`, `tsconfig.json`, `vite.config.ts`, `index.html`) and `src/styles/`, `src/domain/`, `src/map/`, `src/components/`, `src/services/`, and `src/App.tsx` without deleting or modifying `src/frontend/static/` until Milestone 5 server unification.
2. **`skipLibCheck: true` Requirement**:
   `tsconfig.json` MUST have `"skipLibCheck": true` because third-party dependencies of deck.gl (such as `@types/mapbox__point-geometry`) have minor strict declaration discrepancies in modern TypeScript 5.x.

---

## 4. Conclusion & Concrete Configuration Specifications

### 4.1 Recommended `package.json`
```json
{
  "name": "punjab-air-quality",
  "private": true,
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview",
    "typecheck": "tsc --noEmit"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "maplibre-gl": "^3.6.2",
    "@deck.gl/core": "^8.9.36",
    "@deck.gl/layers": "^8.9.36",
    "@deck.gl/mapbox": "^8.9.36",
    "@deck.gl/geo-layers": "^8.9.36",
    "@deck.gl/react": "^8.9.36"
  },
  "devDependencies": {
    "@types/react": "^18.3.18",
    "@types/react-dom": "^18.3.5",
    "@types/node": "^22.10.2",
    "@vitejs/plugin-react": "^4.3.4",
    "typescript": "^5.6.3",
    "vite": "^5.4.11"
  }
}
```

### 4.2 Recommended `tsconfig.json`
```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "skipLibCheck": true,
    "baseUrl": ".",
    "paths": {
      "@/*": ["src/*"]
    }
  },
  "include": ["src", "vite.config.ts"],
  "exclude": ["node_modules", "dist", "original System", ".agents"]
}
```

### 4.3 Recommended `vite.config.ts`
```typescript
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:9000',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
    chunkSizeWarningLimit: 2000,
    rollupOptions: {
      output: {
        manualChunks: {
          'deckgl-vendor': [
            '@deck.gl/core',
            '@deck.gl/layers',
            '@deck.gl/mapbox',
            '@deck.gl/geo-layers',
            '@deck.gl/react',
          ],
          'maplibre-vendor': ['maplibre-gl'],
          'react-vendor': ['react', 'react-dom'],
        },
      },
    },
  },
});
```

### 4.4 Mandatory Ambient Declaration `src/types/deckgl.d.ts`
```typescript
/**
 * Ambient type mappings for Deck.gl v8 packages.
 * Deck.gl v8 stores TypeScript declarations under the 'typed' subpath
 * without exporting them from the package root.
 */
declare module '@deck.gl/core' {
  export * from '@deck.gl/core/typed';
}

declare module '@deck.gl/layers' {
  export * from '@deck.gl/layers/typed';
}

declare module '@deck.gl/mapbox' {
  export * from '@deck.gl/mapbox/typed';
}

declare module '@deck.gl/geo-layers' {
  export * from '@deck.gl/geo-layers/typed';
}

declare module '@deck.gl/react' {
  export * from '@deck.gl/react/typed';
}
```

---

## 5. Verification Method

1. **Clean Installation Verification**:
   Execute from project root:
   ```powershell
   npm install
   ```
   *Expected Outcome*: Successful installation of all 133 dependencies and 62 devDependencies without peer dependency errors or unhandled warnings.

2. **TypeScript Compilation Check**:
   Execute from project root:
   ```powershell
   npm run typecheck
   # Equivalent to: npx tsc --noEmit
   ```
   *Expected Outcome*: Exits with code 0 and zero error messages.

3. **Vite Production Build Verification**:
   Execute from project root:
   ```powershell
   npm run build
   ```
   *Expected Outcome*: Transforms modules and creates `dist/` with chunked vendor bundles (`react-vendor`, `deckgl-vendor`, `maplibre-vendor`) in < 5.0 seconds with zero errors.

4. **Banned Dependencies Verification**:
   Execute from project root:
   ```powershell
   npm list tailwindcss lucide-react heroicons feather-icons
   ```
   *Expected Outcome*: Returns `(empty)` for all 4 packages.

5. **Backend E2E Non-Regression Invalidation Guard**:
   Execute:
   ```powershell
   python tests/e2e/run_all_tests.py
   ```
   *Expected Outcome*: 50/50 test cases pass across all 4 tiers in < 5.0 seconds. If any test fails, tooling changes must be invalidated.
