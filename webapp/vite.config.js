import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  base: './', // relative paths for GitHub Pages / local file open
  // standalone.html is a build-free demo that loads `htm` from a CDN via an
  // import map. Vite's dep scanner would try to pre-bundle that bare import and
  // fail, so restrict scanning to the real React entry.
  optimizeDeps: {
    entries: ['index.html'],
  },
})
