/// <reference types="vitest" />
import { defineConfig, mergeConfig } from 'vite'
import { defineConfig as defineTestConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import path from 'path'

// Base Vite configuration
const viteConfig = defineConfig({
  plugins: [react()],
  base: '/',
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  css: {
    postcss: './postcss.config.js'
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:5001',
        changeOrigin: true,
        secure: false,
      },
    },
  },
})

// Test configuration
const testConfig = defineTestConfig({
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
    css: true,
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html', 'json'],
      exclude: [
        'node_modules/',
        'src/test/',
        'src/main.tsx',
        'src/vite-env.d.ts',
        '**/*.d.ts',
        '**/*.config.{ts,js}',
        'dist/',
        'build/',
      ],
    },
  },
})

// https://vitejs.dev/config/
export default mergeConfig(viteConfig, testConfig)
