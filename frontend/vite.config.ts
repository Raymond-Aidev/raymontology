import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

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
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          // React core
          'vendor-react': ['react', 'react-dom', 'react-router-dom'],
          // D3 visualization (heavy)
          'vendor-d3': ['d3'],
          // State management
          'vendor-zustand': ['zustand'],
          // UI utilities
          'vendor-utils': ['axios', 'date-fns'],
        },
      },
    },
    chunkSizeWarningLimit: 500,
  },
})
