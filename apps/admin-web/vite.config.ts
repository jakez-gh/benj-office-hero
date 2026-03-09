import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import fs from 'fs';
import path from 'path';

// see docs for individual slices on proxy settings
const packageJson = JSON.parse(
  fs.readFileSync(path.resolve(__dirname, '../../package.json'), 'utf-8')
);

export default defineConfig({
  plugins: [react()],
  define: {
    __APP_VERSION__: JSON.stringify(packageJson.version || '0.0.0')
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
        rewrite: (path) => path.replace(/^\/api/, '')
      }
    }
  }
});
