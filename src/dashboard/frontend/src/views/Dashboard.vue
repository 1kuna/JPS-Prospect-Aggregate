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
      <h1 class="text-h4 font-weight-bold">Dashboard</h1>
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
      v-else-if="!dashboardData"
      type="info"
      variant="tonal"
      border="start"
      icon="mdi-information-outline"
    >
      No data available. Click the refresh button to load data.
    </v-alert>
    
    <!-- Dashboard content -->
    <div v-else>
      <!-- Proposals Table with Filters - Moved to top for prominence -->
      <v-row>
        <!-- Filters Panel -->
        <v-col cols="12" md="3" lg="2">
          <v-card elevation="1" class="mb-6">
            <v-card-title class="py-3 px-4">
              <v-icon size="small" color="primary" class="mr-2">mdi-filter</v-icon>
              Filters
            </v-card-title>
            
            <v-divider></v-divider>
            
            <v-card-text class="py-2">
              <!-- Search filter -->
              <v-text-field
                v-model="search"
                prepend-inner-icon="mdi-magnify"
                label="Search proposals"
                single-line
                hide-details
                density="compact"
                variant="outlined"
                class="mb-4"
              ></v-text-field>
              
              <!-- Status filter -->
              <v-select
                v-model="statusFilter"
                label="Status"
                :items="['All', 'Active', 'Pending', 'Completed', 'Cancelled']"
                variant="outlined"
                density="compact"
                hide-details
                class="mb-4"
              ></v-select>
              
              <!-- Source filter -->
              <v-select
                v-model="sourceFilter"
                label="Source"
                :items="sourceOptions"
                variant="outlined"
                density="compact"
                hide-details
                class="mb-4"
              ></v-select>
              
              <!-- Date range filter -->
              <v-menu
                v-model="dateMenu"
                :close-on-content-click="false"
                location="bottom"
              >
                <template v-slot:activator="{ props }">
                  <v-text-field
                    v-bind="props"
                    v-model="dateRangeText"
                    label="Date Range"
                    prepend-inner-icon="mdi-calendar"
                    readonly
                    variant="outlined"
                    density="compact"
                    hide-details
                    class="mb-4"
                  ></v-text-field>
                </template>
                <v-date-picker
                  v-model="dateRange"
                  range
                  @update:model-value="dateMenu = false"
                ></v-date-picker>
              </v-menu>
              
              <!-- NAICS code filter -->
              <v-autocomplete
                v-model="naicsFilter"
                label="NAICS Code"
                :items="naicsCodes"
                variant="outlined"
                density="compact"
                hide-details
                class="mb-4"
              ></v-autocomplete>
              
              <!-- Set-aside filter -->
              <v-select
                v-model="setAsideFilter"
                label="Set-Aside"
                :items="setAsideOptions"
                variant="outlined"
                density="compact"
                hide-details
                class="mb-4"
              ></v-select>
              
              <!-- Reset filters button -->
              <v-btn
                block
                color="primary"
                variant="tonal"
                prepend-icon="mdi-refresh"
                @click="resetFilters"
                class="mt-2"
              >
                Reset Filters
              </v-btn>
            </v-card-text>
          </v-card>
        </v-col>
        
        <!-- Proposals Table -->
        <v-col cols="12" md="9" lg="10">
          <v-card elevation="1" class="mb-6">
            <v-card-title class="py-4 px-6">
              <v-icon size="small" color="primary" class="mr-2">mdi-table</v-icon>
              Recent Proposals
            </v-card-title>
            
            <v-divider></v-divider>
            
            <v-data-table
              :headers="headers"
              :items="filteredProposals"
              :loading="isLoading"
              loading-text="Loading proposals..."
              no-data-text="No proposals available"
              class="proposal-table"
            >
              <template v-slot:item="{ item, columns }">
                <tr 
                  @click="showProposalDetails(item)"
                  class="proposal-row"
                >
                  <td v-for="(column, i) in columns" :key="i">
                    <template v-if="column.key === 'status'">
                      <v-chip
                        :color="getStatusColor(item.status)"
                        size="small"
                        variant="tonal"
                      >
                        {{ item.status }}
                      </v-chip>
                    </template>
                    <template v-else-if="column.key === 'date'">
                      {{ formatDate(item.date) }}
                    </template>
                    <template v-else>
                      {{ item[column.key] }}
                    </template>
                  </td>
                </tr>
              </template>
            </v-data-table>
          </v-card>
        </v-col>
      </v-row>
      
      <!-- Summary Cards - Condensed into a single row -->
      <v-row>
        <v-col cols="12" md="4">
          <v-card elevation="1" class="h-100">
            <v-card-text class="d-flex flex-column align-center py-4">
              <v-icon
                size="36"
                color="primary"
                class="mb-1"
              >mdi-file-document-multiple-outline</v-icon>
              <span class="text-h6 font-weight-medium mb-1">Total Proposals</span>
              <span class="text-h4 font-weight-bold primary--text">
                {{ dashboardData.totalProposals || 0 }}
              </span>
            </v-card-text>
          </v-card>
        </v-col>
        
        <v-col cols="12" md="4">
          <v-card elevation="1" class="h-100">
            <v-card-text class="d-flex flex-column align-center py-4">
              <v-icon
                size="36"
                color="success"
                class="mb-1"
              >mdi-database-check-outline</v-icon>
              <span class="text-h6 font-weight-medium mb-1">Active Sources</span>
              <span class="text-h4 font-weight-bold success--text">
                {{ dashboardData.activeSources || 0 }}
              </span>
            </v-card-text>
          </v-card>
        </v-col>
        
        <v-col cols="12" md="4">
          <v-card elevation="1" class="h-100">
            <v-card-text class="d-flex flex-column align-center py-4">
              <v-icon
                size="36"
                color="info"
                class="mb-1"
              >mdi-calendar-clock</v-icon>
              <span class="text-h6 font-weight-medium mb-1">Last Scrape</span>
              <span class="text-subtitle-1 font-weight-bold info--text">
                {{ formatDate(dashboardData.lastScrape) || 'Never' }}
              </span>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>
      
      <!-- Advanced Features Section -->
      <v-card elevation="1" class="mt-6">
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
      
      <!-- Health Info Section (shown when health checks are run) -->
      <v-card v-if="healthResults.length > 0" elevation="1" class="mt-6">
        <v-card-title class="py-3 px-6">
          <v-icon size="small" color="warning" class="mr-2">mdi-heart-pulse</v-icon>
          Health Information
        </v-card-title>
        
        <v-divider></v-divider>
        
        <v-card-text class="py-4">
          <v-row>
            <v-col v-for="(result, index) in healthResults" :key="index" cols="12" md="6" lg="4">
              <v-card outlined>
                <v-card-title class="py-2">
                  {{ result.sourceName }}
                  <v-spacer></v-spacer>
                  <v-icon
                    :color="result.status === 'working' ? 'success' : 'error'"
                  >
                    {{ result.status === 'working' ? 'mdi-check-circle' : 'mdi-alert-circle' }}
                  </v-icon>
                </v-card-title>
                <v-divider></v-divider>
                <v-card-text>
                  <p><strong>Status:</strong> {{ result.status === 'working' ? 'Working' : 'Not Working' }}</p>
                  <p v-if="result.message"><strong>Message:</strong> {{ result.message }}</p>
                  <p v-if="result.lastCheck"><strong>Last Check:</strong> {{ formatDate(result.lastCheck) }}</p>
                </v-card-text>
              </v-card>
            </v-col>
          </v-row>
        </v-card-text>
      </v-card>
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
    
    <!-- Proposal Details Dialog -->
    <v-dialog v-model="proposalDialog.show" max-width="800px">
      <v-card>
        <v-card-title class="py-3 px-6 text-h5">
          {{ proposalDialog.proposal ? proposalDialog.proposal.title : 'Proposal Details' }}
          <v-spacer></v-spacer>
          <v-btn icon @click="proposalDialog.show = false">
            <v-icon>mdi-close</v-icon>
          </v-btn>
        </v-card-title>
        
        <v-divider></v-divider>
        
        <v-card-text v-if="proposalDialog.proposal" class="py-4">
          <v-row>
            <v-col cols="12" md="6">
              <p class="text-subtitle-2 font-weight-bold mb-1">ID</p>
              <p class="mb-3">{{ proposalDialog.proposal.id }}</p>
              
              <p class="text-subtitle-2 font-weight-bold mb-1">Source</p>
              <p class="mb-3">{{ proposalDialog.proposal.source }}</p>
              
              <p class="text-subtitle-2 font-weight-bold mb-1">Date</p>
              <p class="mb-3">{{ formatDate(proposalDialog.proposal.date) }}</p>
              
              <p class="text-subtitle-2 font-weight-bold mb-1">Status</p>
              <v-chip
                :color="getStatusColor(proposalDialog.proposal.status)"
                size="small"
                variant="tonal"
                class="mb-3"
              >
                {{ proposalDialog.proposal.status }}
              </v-chip>
            </v-col>
            
            <v-col cols="12" md="6">
              <p class="text-subtitle-2 font-weight-bold mb-1">NAICS Code</p>
              <p class="mb-3">{{ proposalDialog.proposal.naicsCode || 'N/A' }}</p>
              
              <p class="text-subtitle-2 font-weight-bold mb-1">Set-Aside</p>
              <p class="mb-3">{{ proposalDialog.proposal.setAside || 'N/A' }}</p>
              
              <p class="text-subtitle-2 font-weight-bold mb-1">Agency</p>
              <p class="mb-3">{{ proposalDialog.proposal.agency || 'N/A' }}</p>
              
              <p class="text-subtitle-2 font-weight-bold mb-1">Due Date</p>
              <p class="mb-3">{{ formatDate(proposalDialog.proposal.dueDate) || 'N/A' }}</p>
            </v-col>
            
            <v-col cols="12">
              <p class="text-subtitle-2 font-weight-bold mb-1">Description</p>
              <p class="mb-3">{{ proposalDialog.proposal.description || 'No description available.' }}</p>
              
              <v-btn
                v-if="proposalDialog.proposal.url"
                color="primary"
                variant="tonal"
                prepend-icon="mdi-open-in-new"
                :href="proposalDialog.proposal.url"
                target="_blank"
                class="mt-2"
              >
                View Original
              </v-btn>
            </v-col>
          </v-row>
        </v-card-text>
        
        <v-card-text v-else class="py-4 text-center">
          <v-progress-circular indeterminate color="primary"></v-progress-circular>
          <p class="mt-2">Loading proposal details...</p>
        </v-card-text>
      </v-card>
    </v-dialog>
  </div>
</template>

<script>
import { mapGetters } from 'vuex'
import axios from 'axios'

// Get the API base URL from environment or use default
const apiBaseUrl = process.env.VUE_APP_API_URL || 'http://localhost:5001/api'

export default {
  name: 'Dashboard',
  data() {
    return {
      search: '',
      headers: [
        { title: 'ID', key: 'id', align: 'start', sortable: true },
        { title: 'Title', key: 'title', align: 'start', sortable: true },
        { title: 'Source', key: 'source', align: 'start', sortable: true },
        { title: 'Date', key: 'date', align: 'start', sortable: true },
        { title: 'Status', key: 'status', align: 'start', sortable: true }
      ],
      healthResults: [],
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
      },
      // New properties for filters
      statusFilter: 'All',
      sourceFilter: 'All',
      dateRange: [],
      dateMenu: false,
      naicsFilter: null,
      setAsideFilter: 'All',
      // New property for proposal details dialog
      proposalDialog: {
        show: false,
        proposal: null
      }
    }
  },
  computed: {
    ...mapGetters([
      'isLoading',
      'hasError',
      'errorMessage',
      'dashboardData',
      'lastUpdated'
    ]),
    // Computed property for filtered proposals
    filteredProposals() {
      if (!this.dashboardData || !this.dashboardData.proposals) {
        return []
      }
      
      let filtered = [...this.dashboardData.proposals]
      
      // Apply search filter
      if (this.search) {
        const searchLower = this.search.toLowerCase()
        filtered = filtered.filter(proposal => 
          proposal.title.toLowerCase().includes(searchLower) ||
          proposal.id.toString().includes(searchLower) ||
          proposal.source.toLowerCase().includes(searchLower)
        )
      }
      
      // Apply status filter
      if (this.statusFilter !== 'All') {
        filtered = filtered.filter(proposal => proposal.status === this.statusFilter)
      }
      
      // Apply source filter
      if (this.sourceFilter !== 'All') {
        filtered = filtered.filter(proposal => proposal.source === this.sourceFilter)
      }
      
      // Apply date range filter
      if (this.dateRange.length === 2) {
        const startDate = new Date(this.dateRange[0])
        const endDate = new Date(this.dateRange[1])
        endDate.setHours(23, 59, 59, 999) // End of day
        
        filtered = filtered.filter(proposal => {
          const proposalDate = new Date(proposal.date)
          return proposalDate >= startDate && proposalDate <= endDate
        })
      }
      
      // Apply NAICS filter
      if (this.naicsFilter) {
        filtered = filtered.filter(proposal => 
          proposal.naicsCode === this.naicsFilter
        )
      }
      
      // Apply set-aside filter
      if (this.setAsideFilter !== 'All') {
        filtered = filtered.filter(proposal => 
          proposal.setAside === this.setAsideFilter
        )
      }
      
      return filtered
    },
    // Computed property for date range text
    dateRangeText() {
      if (!this.dateRange || this.dateRange.length === 0) {
        return ''
      }
      
      if (this.dateRange.length === 1) {
        return this.formatDateShort(this.dateRange[0])
      }
      
      return `${this.formatDateShort(this.dateRange[0])} - ${this.formatDateShort(this.dateRange[1])}`
    },
    // Computed property for source options
    sourceOptions() {
      if (!this.dashboardData || !this.dashboardData.proposals) {
        return ['All']
      }
      
      const sources = new Set(this.dashboardData.proposals.map(p => p.source))
      return ['All', ...Array.from(sources)]
    },
    // Computed property for NAICS codes
    naicsCodes() {
      if (!this.dashboardData || !this.dashboardData.proposals) {
        return []
      }
      
      const naicsCodes = new Set()
      this.dashboardData.proposals.forEach(p => {
        if (p.naicsCode) {
          naicsCodes.add(p.naicsCode)
        }
      })
      
      return Array.from(naicsCodes)
    },
    // Computed property for set-aside options
    setAsideOptions() {
      if (!this.dashboardData || !this.dashboardData.proposals) {
        return ['All']
      }
      
      const setAsides = new Set()
      this.dashboardData.proposals.forEach(p => {
        if (p.setAside) {
          setAsides.add(p.setAside)
        }
      })
      
      return ['All', ...Array.from(setAsides)]
    }
  },
  methods: {
    formatDate(dateString) {
      if (!dateString) return 'N/A'
      const date = new Date(dateString)
      return date.toLocaleString()
    },
    formatDateShort(dateString) {
      if (!dateString) return ''
      const date = new Date(dateString)
      return date.toLocaleDateString()
    },
    getStatusColor(status) {
      const statusMap = {
        'Active': 'success',
        'Pending': 'warning',
        'Completed': 'info',
        'Cancelled': 'error'
      }
      return statusMap[status] || 'grey'
    },
    // New method to reset filters
    resetFilters() {
      this.search = ''
      this.statusFilter = 'All'
      this.sourceFilter = 'All'
      this.dateRange = []
      this.naicsFilter = null
      this.setAsideFilter = 'All'
    },
    // New method to show proposal details
    showProposalDetails(proposal) {
      this.proposalDialog.proposal = proposal
      this.proposalDialog.show = true
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
        this.healthResults = []
        this.showSnackbar('Running health checks...', 'info')
        
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
              result.sourceName = source.name
              return result
            })
        )
        
        // Wait for all health checks to complete
        this.healthResults = await Promise.all(healthCheckPromises)
        
        // Count successes and failures
        const successes = this.healthResults.filter(result => 
          result.success && result.status === 'working'
        ).length
        
        const failures = this.healthResults.filter(result => 
          result.success && result.status === 'not_working'
        ).length
        
        const errors = this.healthResults.filter(result => !result.success).length
        
        this.showSnackbar(`Health checks completed: ${successes} working, ${failures} not working, ${errors} errors.`)
      } catch (error) {
        console.error('Error running health checks:', error)
        this.showSnackbar('Failed to run health checks: ' + error.message, 'error')
      }
    }
  },
  mounted() {
    this.$store.dispatch('fetchDashboardData')
  }
}
</script>

<style scoped>
.max-width-300 {
  max-width: 300px;
}

.h-100 {
  height: 100%;
}

.proposal-row {
  cursor: pointer;
  transition: background-color 0.2s;
}

.proposal-row:hover {
  background-color: rgba(0, 0, 0, 0.05);
}
</style> 