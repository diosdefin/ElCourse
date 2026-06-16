import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'  // ← Добавьте эту строку!

export default defineConfig({
  plugins: [
    vue(),
  ],
  resolve: {  // ← Добавьте этот блок!
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
})