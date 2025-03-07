import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import store from './store'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import 'vuetify/styles'
import '@mdi/font/css/materialdesignicons.css'

const vuetify = createVuetify({
  components,
  directives,
  theme: {
    defaultTheme: 'light',
    themes: {
      light: {
        dark: false,
        colors: {
          primary: '#3f51b5',    // Indigo
          secondary: '#5c6bc0',  // Indigo Lighten-1
          accent: '#8c9eff',     // Indigo Accent-1
          error: '#f44336',      // Red
          info: '#03a9f4',       // Light Blue
          success: '#4caf50',    // Green
          warning: '#ff9800'     // Orange
        }
      }
    },
    options: {
      customProperties: true,
      variations: true
    }
  },
  defaults: {
    VCard: {
      elevation: 1,
      rounded: 'lg'
    },
    VBtn: {
      rounded: 'lg',
      elevation: 0
    },
    VTextField: {
      variant: 'outlined',
      density: 'comfortable'
    },
    VAlert: {
      variant: 'tonal',
      border: 'start'
    }
  }
})

const app = createApp(App)

app.use(store)
app.use(router)
app.use(vuetify)

app.mount('#app') 