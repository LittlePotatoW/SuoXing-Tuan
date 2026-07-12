import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/relay': {
        target: 'http://39.105.129.111:8001',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/relay/, ''),
      },
    },
  },
})
