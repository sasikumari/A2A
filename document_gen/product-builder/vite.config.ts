import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8001',
        changeOrigin: true,
      },
      '/agents': {
        target: 'http://localhost:5000',
        changeOrigin: true,
      },
      '/deploy': {
        target: 'http://localhost:5000',
        changeOrigin: true,
      },
      '/git': {
        target: 'http://localhost:5000',
        changeOrigin: true,
      },
      '/push': {
        target: 'http://localhost:5000',
        changeOrigin: true,
      },
      '/stream': {
        target: 'http://localhost:5000',
        changeOrigin: true,
      },
      '/workflow2': {
        target: 'http://localhost:5000',
        changeOrigin: true,
      },
      '/current-version': {
        target: 'http://localhost:5000',
        changeOrigin: true,
      },
      '/limits': {
        target: 'http://localhost:5000',
        changeOrigin: true,
      },
    },
  },
})
