const { defineConfig } = require('@vue/cli-service')

module.exports = defineConfig({
  transpileDependencies: true,
  // Output to Flask static directory
  outputDir: '../static/vue',
  // Set the public path to match Flask's static URL
  publicPath: process.env.NODE_ENV === 'production' ? '/static/vue/' : '/',
  // Configure dev server to proxy API requests to Flask
  devServer: {
    proxy: {
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true
      }
    }
  }
}) 