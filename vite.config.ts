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
