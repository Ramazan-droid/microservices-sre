import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  
  base: '/',                    // Important for production
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    cssCodeSplit: true,         // Better CSS handling
    rollupOptions: {
      output: {
        manualChunks: undefined
      }
    }
  },
  
  css: {
    devSourcemap: true,
  }
})