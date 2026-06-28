import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

const backendUrl = process.env.VITE_BACKEND_URL || 'http://127.0.0.1:8000';

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    host: true,
    port: 5173,
    proxy: {
      '/health': backendUrl,
      '/upload': backendUrl,
      '/profile': backendUrl,
      '/analyze': backendUrl,
      '/history': backendUrl,
      '/report': backendUrl,
    }
  }
})
