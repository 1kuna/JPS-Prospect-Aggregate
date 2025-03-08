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
      <!-- Debug info (remove in production) -->
      <v-card v-if="dashboardData && dashboardData.pagination" class="mb-4 pa-2" color="grey-lighten-4">
        <pre>Page: {{ page }}, Items per page: {{ itemsPerPage }}, Total count: {{ totalCount }}</pre>
        <pre>Pagination data: {{ JSON.stringify(dashboardData.pagination, null, 2) }}</pre>
      </v-card>
      
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
                {{ dashboardData.total_proposals || 0 }}
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
                {{ dashboardData.active_sources || 0 }}
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
              <span class="text-h6 font-weight-medium mb-1">Last Updated</span>
              <span class="text-subtitle-1 font-weight-bold info--text">
                {{ formatDate(dashboardData.last_scrape) || 'Never' }}
              </span>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>

      <!-- Main content area -->
      <v-row class="mt-4">
        <v-col cols="12">
          <v-card elevation="2" class="rounded-lg">
            <v-card-title class="d-flex align-center">
              <span class="text-h5">Recent Proposals</span>
              <v-spacer></v-spacer>
              <v-btn
                icon
                @click="refreshData"
                :loading="isLoading"
                color="primary"
              >
                <v-icon>mdi-refresh</v-icon>
              </v-btn>
            </v-card-title>
            
            <!-- Data table -->
            <v-data-table
              :headers="headers"
              :items="filteredProposals"
              :loading="isLoading"
              :items-per-page="itemsPerPage"
              :page="page"
              :server-items-length="totalCount"
              @update:page="updatePage"
              @update:items-per-page="updateItemsPerPage"
              class="elevation-0"
              @click:row="showProposalDetails"
              :footer-props="{
                'items-per-page-options': [10, 20, 50, 100],
                'show-current-page': true,
                'show-first-last-page': true,
                'items-per-page-text': 'Rows per page:'
              }"
            >
              <!-- Custom formatting for table cells -->
              <template v-slot:item.date="{ item }">
                {{ formatDate(item.date) }}
              </template>
              
              <template v-slot:item.status="{ item }">
                <v-chip
                  :color="getStatusColor(item.status)"
                  text-color="white"
                  size="small"
                >
                  {{ item.status }}
                </v-chip>
              </template>
              
              <!-- No data placeholder -->
              <template v-slot:no-data>
                <div class="text-center py-6">
                  <v-icon size="large" color="grey-lighten-1" class="mb-2">mdi-database-off</v-icon>
                  <div class="text-body-1 text-grey-darken-1">No proposals found</div>
                </div>
              </template>
            </v-data-table>
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

export default {
  name: 'Dashboard',
  data() {
    return {
      headers: [
        { title: 'ID', key: 'id', align: 'start', sortable: true },
        { title: 'Title', key: 'title', align: 'start', sortable: true },
        { title: 'Source', key: 'source', align: 'start', sortable: true },
        { title: 'Date', key: 'date', align: 'start', sortable: true },
        { title: 'Status', key: 'status', align: 'start', sortable: true }
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
      },
      // Proposal details dialog
      proposalDialog: {
        show: false,
        proposal: null
      },
      itemsPerPage: 10,
      page: 1
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
      
      return this.dashboardData.proposals
    },
    // Computed property for total count
    totalCount() {
      if (!this.dashboardData || !this.dashboardData.pagination) {
        return 0
      }
      
      return this.dashboardData.pagination.total_count || 0
    }
  },
  methods: {
    // Fetch data on component mount
    fetchData() {
      console.log(`Fetching dashboard data with page=${this.page}, perPage=${this.itemsPerPage}`);
      
      this.$store.dispatch('fetchDashboardData', {
        page: this.page,
        perPage: this.itemsPerPage
      }).then(() => {
        console.log('Dashboard data fetched:', this.dashboardData);
        if (this.dashboardData && this.dashboardData.pagination) {
          console.log('Pagination data:', this.dashboardData.pagination);
        }
      }).catch(error => {
        console.error('Error fetching dashboard data:', error);
      });
    },
    // Format date for display
    formatDate(dateString) {
      if (!dateString) return 'N/A'
      
      const date = new Date(dateString)
      return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
      })
    },
    // Get color for status chip
    getStatusColor(status) {
      const statusColors = {
        'Active': 'green',
        'Pending': 'amber-darken-2',
        'Completed': 'blue',
        'Cancelled': 'red',
        'Draft': 'grey'
      }
      
      return statusColors[status] || 'grey'
    },
    // Method to confirm action
    confirmAction() {
      if (this.confirmDialog.requireInput && this.confirmDialog.input !== 'CONFIRM') {
        this.showSnackbar('Please type CONFIRM to proceed', 'error')
        return
      }
      
      if (typeof this.confirmDialog.action === 'function') {
        this.confirmDialog.action()
      }
      
      this.confirmDialog.show = false
      this.confirmDialog.input = ''
    },
    // Method to show snackbar
    showSnackbar(text, color = 'success') {
      this.snackbar.text = text
      this.snackbar.color = color
      this.snackbar.show = true
    },
    // Show proposal details
    showProposalDetails(proposal) {
      this.proposalDialog.proposal = proposal
      this.proposalDialog.show = true
    },
    // Method to refresh data
    refreshData() {
      this.fetchData()
    },
    // Method to update page
    updatePage(page) {
      this.page = page
      this.fetchData()
    },
    // Method to update items per page
    updateItemsPerPage(itemsPerPage) {
      this.itemsPerPage = itemsPerPage
      this.fetchData()
    }
  },
  mounted() {
    this.fetchData()
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