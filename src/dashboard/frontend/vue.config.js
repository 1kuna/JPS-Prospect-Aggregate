const { defineConfig } = require('@vue/cli-service')

module.exports = defineConfig({
  transpileDependencies: true,
  // Output to Flask static directory
  outputDir: '../static/vue',
  // Always use the production path for consistency
  publicPath: process.env.NODE_ENV === 'production' ? '/static/vue/' : '/',
  // Ensure index.html is generated
  indexPath: 'index.html',
  // Configure dev server to proxy API requests to Flask
  devServer: {
    proxy: {
      '/api': {
        target: 'http://localhost:5001',
        changeOrigin: true
      }
    },
    // Ensure history mode works properly
    historyApiFallback: true
  },
  // Configure webpack to handle assets properly
  configureWebpack: {
    output: {
      // Ensure filenames are consistent
      filename: 'js/[name].[hash].js',
      chunkFilename: 'js/[name].[hash].js'
    }
  },
  // Ensure proper handling of static assets
  chainWebpack: config => {
    // Set the correct base URL for assets
    config.plugin('html').tap(args => {
      args[0].publicPath = process.env.NODE_ENV === 'production' ? '/static/vue/' : '/'
      return args
    })
  }
}) 