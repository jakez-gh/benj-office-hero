import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// see docs for individual slices on proxy settings
export default defineConfig({
  plugins: [react()],
  define: {
    __APP_VERSION__: JSON.stringify(
      require('../../package.json').version || '0.0.0'
    )
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false
      }
    }
  }
});
