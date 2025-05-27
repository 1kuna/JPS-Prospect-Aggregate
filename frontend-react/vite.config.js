import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';
// https://vitejs.dev/config/
export default defineConfig({
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
});
