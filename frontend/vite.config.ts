import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Dev proxy kills CORS entirely: browser only ever sees same-origin /api/*.
export default defineConfig({
  plugins: [react()],
  server: {
    host: true, // expose on LAN so phones can scan QR codes against this dev server
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
});
