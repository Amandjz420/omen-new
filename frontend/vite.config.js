import {defineConfig} from 'vite';

export default defineConfig({
  // The automatic JSX runtime: files need not import React. Without it, JSX compiles
  // to React.createElement and every file must import React or fail when it renders.
  esbuild: {jsx: 'automatic'},
  server: {port: 5173, strictPort: true, proxy: {'/api': 'http://127.0.0.1:8000'}},
  build: {
    rollupOptions: {
      // "use client" marks components for server rendering; a browser-only build
      // ignores it, so the notice is noise that would hide real warnings.
      onwarn(warning, warn) {
        if (warning.code === 'MODULE_LEVEL_DIRECTIVE' && /use client/.test(warning.message)) return;
        warn(warning);
      },
      output: {
        // Libraries change rarely, so they sit in their own file that phones keep cached
        // between releases; each screen is loaded only when it is opened.
        manualChunks(id) {
          if (id.includes('node_modules/@mantine') || id.includes('node_modules/@floating-ui')) return 'mantine';
          if (id.includes('node_modules/react') || id.includes('node_modules/scheduler') || id.includes('node_modules/@tanstack')) return 'react';
        },
      },
    },
  },
  test: {environment: 'jsdom', setupFiles: ['./src/test/setup.js'], include: ['src/**/*.test.{js,jsx}'], css: true},
});
