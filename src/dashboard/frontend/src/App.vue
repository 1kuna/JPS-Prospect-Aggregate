<template>
  <v-app>
    <!-- Modern app bar with subtle elevation and improved spacing -->
    <v-app-bar 
      app 
      elevation="1"
      color="white"
      height="64"
    >
      <v-app-bar-nav-icon 
        @click="drawer = !drawer"
        color="primary"
        class="ml-2"
      ></v-app-bar-nav-icon>
      
      <v-toolbar-title class="text-h5 font-weight-medium ml-2">
        JPS Proposal Forecast
      </v-toolbar-title>
      
      <v-spacer></v-spacer>
      
      <v-btn
        icon
        @click="refreshData"
        color="primary"
        class="mr-2"
        elevation="0"
      >
        <v-tooltip location="bottom">
          <template v-slot:activator="{ props }">
            <v-icon v-bind="props">mdi-refresh</v-icon>
          </template>
          <span>Refresh Data</span>
        </v-tooltip>
      </v-btn>
    </v-app-bar>

    <!-- Improved navigation drawer with better styling -->
    <v-navigation-drawer
      v-model="drawer"
      app
      color="grey-lighten-5"
      :width="280"
      elevation="2"
    >
      <v-list class="py-4">
        <v-list-item class="mb-4 px-4">
          <div class="text-h6 font-weight-bold primary--text">
            JPS Proposal Forecast
          </div>
        </v-list-item>
        
        <v-divider class="mb-2"></v-divider>
        
        <v-list-item
          v-for="(item, i) in menuItems"
          :key="i"
          :to="item.path"
          :prepend-icon="item.icon"
          :title="item.title"
          rounded="lg"
          class="mb-1 mx-2"
          active-color="primary"
        ></v-list-item>
        
        <v-divider class="my-2"></v-divider>
        
        <v-list-subheader class="text-uppercase font-weight-bold">
          Advanced Features
        </v-list-subheader>
        
        <v-list-item
          v-for="(item, i) in advancedItems"
          :key="i"
          @click="handleAdvancedAction(item.action)"
          :prepend-icon="item.icon"
          :title="item.title"
          rounded="lg"
          class="mb-1 mx-2"
          active-color="primary"
        ></v-list-item>
      </v-list>
      
      <template v-slot:append>
        <div class="pa-4">
          <v-btn
            block
            color="primary"
            variant="tonal"
            prepend-icon="mdi-refresh"
            @click="refreshData"
          >
            Refresh Data
          </v-btn>
        </div>
      </template>
    </v-navigation-drawer>

    <!-- Main content area with improved spacing -->
    <v-main class="bg-grey-lighten-4">
      <v-container fluid class="pa-4">
        <router-view ref="currentView"></router-view>
      </v-container>
    </v-main>

    <!-- Modern footer with subtle styling -->
    <v-footer app class="bg-white px-4" elevation="1" height="40">
      <span class="text-caption text-grey">
        &copy; {{ new Date().getFullYear() }} JPS Proposal Forecast Aggregator
      </span>
      <v-spacer></v-spacer>
      <span class="text-caption text-grey">v1.0.0</span>
    </v-footer>
    
    <!-- Confirmation Dialog -->
    <v-dialog v-model="confirmDialog.show" max-width="500">
      <v-card>
        <v-card-title class="text-h5">{{ confirmDialog.title }}</v-card-title>
        <v-card-text>
          <p v-html="confirmDialog.message"></p>
          <v-text-field
            v-if="confirmDialog.requireInput"
            v-model="confirmDialog.input"
            :label="confirmDialog.inputLabel"
            variant="outlined"
            class="mt-4"
          ></v-text-field>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="grey-darken-1" variant="text" @click="confirmDialog.show = false">Cancel</v-btn>
          <v-btn color="error" variant="tonal" @click="confirmAction">Confirm</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
    
    <!-- Success/Error Snackbar -->
    <v-snackbar v-model="snackbar.show" :color="snackbar.color" :timeout="snackbar.timeout">
      {{ snackbar.text }}
      <template v-slot:actions>
        <v-btn variant="text" @click="snackbar.show = false">Close</v-btn>
      </template>
    </v-snackbar>
  </v-app>
</template>

<script>
export default {
  name: 'App',
  data() {
    return {
      drawer: false,
      menuItems: [
        { title: 'Dashboard', path: '/', icon: 'mdi-view-dashboard' },
        { title: 'Data Sources', path: '/data-sources', icon: 'mdi-database' }
      ],
      advancedItems: [
        { title: 'Rebuild Database', action: 'rebuildDatabase', icon: 'mdi-database-refresh' },
        { title: 'Initialize Database', action: 'initializeDatabase', icon: 'mdi-database-plus' },
        { title: 'Delete All Files', action: 'deleteAllFiles', icon: 'mdi-delete' },
        { title: 'Run Health Checks', action: 'runHealthChecks', icon: 'mdi-heart-pulse' }
      ],
      confirmDialog: {
        show: false,
        title: '',
        message: '',
        requireInput: false,
        inputLabel: '',
        input: '',
        action: null
      },
      snackbar: {
        show: false,
        text: '',
        color: 'success',
        timeout: 5000
      }
    }
  },
  methods: {
    refreshData() {
      // Emit an event to refresh data
      this.$store.dispatch('refreshData')
      this.showSnackbar('Refreshing data...')
    },
    handleAdvancedAction(action) {
      // Close the drawer
      this.drawer = false
      
      // Get the current view component
      const currentView = this.$refs.currentView
      
      // Check if the current view has the requested method
      if (currentView && typeof currentView[action] === 'function') {
        // Call the method on the current view
        currentView[action]()
      } else {
        // If the method doesn't exist on the current view, show an error
        this.showSnackbar('This feature is not available on the current page. Please navigate to Dashboard or Data Sources.', 'warning')
      }
    },
    showConfirmDialog(title, message, action, requireInput = false, inputLabel = '') {
      this.confirmDialog = {
        show: true,
        title,
        message,
        requireInput,
        inputLabel,
        input: '',
        action
      }
    },
    confirmAction() {
      if (this.confirmDialog.requireInput && 
          this.confirmDialog.input !== this.confirmDialog.inputLabel) {
        this.showSnackbar('Please type the confirmation text exactly as shown', 'error')
        return
      }
      
      this.confirmDialog.show = false
      if (typeof this.confirmDialog.action === 'function') {
        this.confirmDialog.action()
      }
    },
    showSnackbar(text, color = 'success', timeout = 5000) {
      this.snackbar = {
        show: true,
        text,
        color,
        timeout
      }
    }
  }
}
</script>

<style>
/* Global styles */
:root {
  --border-radius: 12px;
}

.v-card {
  border-radius: var(--border-radius) !important;
}

.v-btn {
  letter-spacing: 0.5px;
}

.v-card-title {
  font-weight: 600 !important;
}
</style> 