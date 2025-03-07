<template>
  <div>
    <v-alert
      v-if="hasError"
      type="error"
      dismissible
      variant="tonal"
      border="start"
      class="mb-4"
    >
      {{ errorMessage }}
    </v-alert>

    <!-- Page header with title and last updated info -->
    <div class="d-flex align-center mb-4">
      <h1 class="text-h4 font-weight-bold">Data Sources</h1>
      <v-spacer></v-spacer>
      <v-chip
        v-if="lastUpdated"
        color="primary"
        size="small"
        variant="outlined"
        prepend-icon="mdi-clock-outline"
      >
        Last updated: {{ formatDate(lastUpdated) }}
      </v-chip>
    </div>

    <!-- Loading state -->
    <v-progress-linear
      v-if="isLoading"
      indeterminate
      color="primary"
      class="mb-4"
    ></v-progress-linear>
    
    <!-- No data state -->
    <v-alert
      v-else-if="!dataSources || dataSources.length === 0"
      type="info"
      variant="tonal"
      border="start"
      icon="mdi-information-outline"
    >
      No data sources available. Click the refresh button to load data.
    </v-alert>
    
    <!-- Advanced Features Section -->
    <v-card elevation="1" class="mb-6">
      <v-card-title class="py-3 px-6">
        <v-icon size="small" color="primary" class="mr-2">mdi-tools</v-icon>
        Advanced Features
      </v-card-title>
      
      <v-divider></v-divider>
      
      <v-card-text class="py-4">
        <v-row>
          <v-col cols="12" md="6" lg="3">
            <v-btn
              block
              color="primary"
              variant="tonal"
              prepend-icon="mdi-database-refresh"
              @click="rebuildDatabase"
              class="mb-2"
            >
              Rebuild Database
            </v-btn>
          </v-col>
          
          <v-col cols="12" md="6" lg="3">
            <v-btn
              block
              color="primary"
              variant="tonal"
              prepend-icon="mdi-database-plus"
              @click="initializeDatabase"
              class="mb-2"
            >
              Initialize Database
            </v-btn>
          </v-col>
          
          <v-col cols="12" md="6" lg="3">
            <v-btn
              block
              color="error"
              variant="tonal"
              prepend-icon="mdi-delete"
              @click="deleteAllFiles"
              class="mb-2"
            >
              Delete All Files
            </v-btn>
          </v-col>
          
          <v-col cols="12" md="6" lg="3">
            <v-btn
              block
              color="warning"
              variant="tonal"
              prepend-icon="mdi-heart-pulse"
              @click="runHealthChecks"
              class="mb-2"
            >
              Run Health Checks
            </v-btn>
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>
    
    <!-- Data sources grid -->
    <div v-if="dataSources && dataSources.length > 0">
      <v-row>
        <v-col
          v-for="(source, index) in sourcesWithStatus"
          :key="index"
          cols="12"
          md="6"
          lg="4"
          class="d-flex"
        >
          <v-card elevation="1" class="w-100">
            <v-card-item>
              <template v-slot:prepend>
                <v-avatar
                  :color="source.active ? 'success' : 'grey'"
                  class="mr-3"
                  size="42"
                >
                  <v-icon color="white">
                    {{ source.active ? 'mdi-database-check' : 'mdi-database-off' }}
                  </v-icon>
                </v-avatar>
              </template>
              
              <v-card-title class="text-h6 pb-0">
                {{ source.name }}
              </v-card-title>
              
              <v-card-subtitle class="pt-1">
                <v-chip
                  :color="source.active ? 'success' : 'error'"
                  size="x-small"
                  variant="tonal"
                  class="mt-1"
                >
                  {{ source.active ? 'Active' : 'Inactive' }}
                </v-chip>
                
                <v-chip
                  v-if="source.health"
                  :color="source.health.status === 'working' ? 'success' : 'error'"
                  size="x-small"
                  variant="tonal"
                  class="mt-1 ml-1"
                >
                  {{ source.health.status === 'working' ? 'Healthy' : 'Unhealthy' }}
                </v-chip>
              </v-card-subtitle>
            </v-card-item>
            
            <v-divider class="mx-4"></v-divider>
            
            <v-card-text class="pt-4">
              <div class="d-flex align-center mb-2">
                <v-icon size="small" color="grey" class="mr-2">mdi-link</v-icon>
                <span class="text-body-2 text-medium-emphasis text-truncate">{{ source.url }}</span>
              </div>
              
              <div class="d-flex align-center mb-2">
                <v-icon size="small" color="grey" class="mr-2">mdi-calendar-clock</v-icon>
                <span class="text-body-2 text-medium-emphasis">
                  Last Scrape: {{ formatDate(source.lastScrape) || 'Never' }}
                </span>
              </div>
              
              <div class="d-flex align-center">
                <v-icon size="small" color="grey" class="mr-2">mdi-file-document-multiple</v-icon>
                <span class="text-body-2 text-medium-emphasis">
                  Proposals: {{ source.proposalCount || 0 }}
                </span>
              </div>
              
              <div v-if="source.health && source.health.message" class="d-flex align-center mt-2">
                <v-icon size="small" color="grey" class="mr-2">mdi-information</v-icon>
                <span class="text-body-2 text-medium-emphasis">
                  {{ source.health.message }}
                </span>
              </div>
            </v-card-text>
            
            <v-card-actions class="px-4 pb-4">
              <v-btn
                color="primary"
                variant="tonal"
                prepend-icon="mdi-refresh"
                @click="triggerScrape(source.id)"
                :loading="source.scraping"
                :disabled="!source.active"
                size="small"
              >
                Scrape Now
              </v-btn>
              
              <v-btn
                color="warning"
                variant="tonal"
                prepend-icon="mdi-heart-pulse"
                @click="checkSourceHealth(source.id)"
                :loading="source.checkingHealth"
                size="small"
                class="ml-2"
              >
                Check Health
              </v-btn>
              
              <v-spacer></v-spacer>
              
              <v-btn
                :color="source.active ? 'error' : 'success'"
                variant="tonal"
                :prepend-icon="source.active ? 'mdi-close' : 'mdi-check'"
                @click="toggleSourceStatus(source.id, !source.active)"
                size="small"
              >
                {{ source.active ? 'Deactivate' : 'Activate' }}
              </v-btn>
            </v-card-actions>
          </v-card>
        </v-col>
      </v-row>
    </div>
    
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
  </div>
</template>

<script>
import { mapGetters } from 'vuex'
import axios from 'axios'

// Get the API base URL from environment or use default
const apiBaseUrl = process.env.VUE_APP_API_URL || 'http://localhost:5001/api'

export default {
  name: 'DataSources',
  data() {
    return {
      scrapingSourceIds: [],
      checkingHealthSourceIds: [],
      sourceHealthData: {},
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
  computed: {
    ...mapGetters([
      'isLoading',
      'hasError',
      'errorMessage',
      'dataSources',
      'lastUpdated'
    ]),
    // Add scraping status and health data to each data source
    sourcesWithStatus() {
      if (!this.dataSources) return []
      return this.dataSources.map(source => ({
        ...source,
        scraping: this.scrapingSourceIds.includes(source.id),
        checkingHealth: this.checkingHealthSourceIds.includes(source.id),
        health: this.sourceHealthData[source.id] || null
      }))
    }
  },
  methods: {
    formatDate(dateString) {
      if (!dateString) return 'N/A'
      const date = new Date(dateString)
      return date.toLocaleString()
    },
    async triggerScrape(sourceId) {
      this.scrapingSourceIds.push(sourceId)
      
      try {
        await axios.post(`${apiBaseUrl}/data-sources/${sourceId}/scrape`)
        this.showSnackbar('Scrape initiated successfully')
        this.$store.dispatch('fetchDataSources')
      } catch (error) {
        console.error('Error triggering scrape:', error)
        this.showSnackbar('Failed to trigger scrape: ' + error.message, 'error')
      } finally {
        this.scrapingSourceIds = this.scrapingSourceIds.filter(id => id !== sourceId)
      }
    },
    async toggleSourceStatus(sourceId, active) {
      try {
        await axios.put(`${apiBaseUrl}/data-sources/${sourceId}`, { active })
        this.showSnackbar(`Source ${active ? 'activated' : 'deactivated'} successfully`)
        this.$store.dispatch('fetchDataSources')
      } catch (error) {
        console.error('Error updating source status:', error)
        this.showSnackbar('Failed to update source status: ' + error.message, 'error')
      }
    },
    async checkSourceHealth(sourceId) {
      this.checkingHealthSourceIds.push(sourceId)
      
      try {
        const response = await axios.post(`${apiBaseUrl}/scraper-status/${sourceId}/check`)
        this.sourceHealthData = {
          ...this.sourceHealthData,
          [sourceId]: response.data
        }
        
        const status = response.data.status === 'working' ? 'healthy' : 'unhealthy'
        this.showSnackbar(`Source is ${status}`)
      } catch (error) {
        console.error('Error checking source health:', error)
        this.showSnackbar('Failed to check source health: ' + error.message, 'error')
      } finally {
        this.checkingHealthSourceIds = this.checkingHealthSourceIds.filter(id => id !== sourceId)
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
    },
    rebuildDatabase() {
      this.showConfirmDialog(
        'Rebuild Database',
        'WARNING: This will rebuild the database from scratch.<br><br>' +
        'This operation will:<br>' +
        '1. Create a backup of the current database<br>' +
        '2. Rebuild the database structure<br>' +
        '3. Preserve your data<br><br>' +
        'The application may need to be restarted after this operation.',
        this.performDatabaseRebuild
      )
    },
    async performDatabaseRebuild() {
      try {
        await axios.post(`${apiBaseUrl}/rebuild-db`)
        this.showSnackbar('Database rebuild started. The application may need to be restarted.')
      } catch (error) {
        console.error('Error rebuilding database:', error)
        this.showSnackbar('Failed to rebuild database: ' + error.message, 'error')
      }
    },
    initializeDatabase() {
      this.showConfirmDialog(
        'Initialize Database',
        'WARNING: This will delete the current database and create a new one!<br><br>' +
        'This operation will:<br>' +
        '1. Delete ALL existing data<br>' +
        '2. Create a new empty database<br>' +
        '3. Initialize the data sources<br><br>' +
        'This operation cannot be undone. All your data will be permanently lost.',
        this.performDatabaseInitialization,
        true,
        'INIT'
      )
    },
    async performDatabaseInitialization() {
      try {
        await axios.post(`${apiBaseUrl}/init-db`)
        this.showSnackbar('Database initialization started. The page will reload shortly.')
        setTimeout(() => window.location.reload(), 5000)
      } catch (error) {
        console.error('Error initializing database:', error)
        this.showSnackbar('Failed to initialize database: ' + error.message, 'error')
      }
    },
    deleteAllFiles() {
      this.showConfirmDialog(
        'Delete All Files',
        'WARNING: This is a destructive operation!<br><br>' +
        'This will:<br>' +
        '1. Delete ALL downloaded files<br>' +
        '2. Delete ALL database backups<br>' +
        '3. Delete the current database<br>' +
        '4. Create a new empty database<br><br>' +
        'This operation cannot be undone. All your data will be permanently lost.',
        this.performDeleteAllFiles,
        true,
        'RESET'
      )
    },
    async performDeleteAllFiles() {
      try {
        await axios.post(`${apiBaseUrl}/reset-everything`)
        this.showSnackbar('Reset initiated. The application will be reloaded shortly.')
        setTimeout(() => window.location.reload(), 5000)
      } catch (error) {
        console.error('Error resetting everything:', error)
        this.showSnackbar('Failed to reset: ' + error.message, 'error')
      }
    },
    async runHealthChecks() {
      try {
        this.showSnackbar('Running health checks for all sources...', 'info')
        
        // Get all data sources
        const sourcesResponse = await axios.get(`${apiBaseUrl}/data-sources`)
        const sources = sourcesResponse.data
        
        if (!sources || sources.length === 0) {
          this.showSnackbar('No data sources found', 'warning')
          return
        }
        
        // Run health checks for each source
        const healthCheckPromises = sources.map(source => 
          axios.post(`${apiBaseUrl}/scraper-status/${source.id}/check`)
            .then(response => {
              const result = response.data
              // Store health data for each source
              this.sourceHealthData = {
                ...this.sourceHealthData,
                [source.id]: result
              }
              return result
            })
        )
        
        // Wait for all health checks to complete
        const results = await Promise.all(healthCheckPromises)
        
        // Count successes and failures
        const successes = results.filter(result => 
          result.success && result.status === 'working'
        ).length
        
        const failures = results.filter(result => 
          result.success && result.status === 'not_working'
        ).length
        
        const errors = results.filter(result => !result.success).length
        
        this.showSnackbar(`Health checks completed: ${successes} working, ${failures} not working, ${errors} errors.`)
      } catch (error) {
        console.error('Error running health checks:', error)
        this.showSnackbar('Failed to run health checks: ' + error.message, 'error')
      }
    }
  },
  mounted() {
    this.$store.dispatch('fetchDataSources')
  }
}
</script>

<style scoped>
.w-100 {
  width: 100%;
}

.text-truncate {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
}
</style> 