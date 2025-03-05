<template>
  <div>
    <v-alert
      v-if="hasError"
      type="error"
      dismissible
    >
      {{ errorMessage }}
    </v-alert>

    <v-row>
      <v-col cols="12">
        <v-card>
          <v-card-title class="d-flex align-center">
            <span>Dashboard</span>
            <v-spacer></v-spacer>
            <v-chip v-if="lastUpdated" color="primary" size="small">
              Last updated: {{ formatDate(lastUpdated) }}
            </v-chip>
          </v-card-title>
          <v-card-text>
            <v-progress-linear
              v-if="isLoading"
              indeterminate
              color="primary"
            ></v-progress-linear>
            
            <div v-else-if="!dashboardData">
              <v-alert type="info">
                No data available. Click the refresh button to load data.
              </v-alert>
            </div>
            
            <div v-else>
              <!-- Summary Cards -->
              <v-row>
                <v-col cols="12" md="4">
                  <v-card>
                    <v-card-title>Total Proposals</v-card-title>
                    <v-card-text class="text-h3 text-center">
                      {{ dashboardData.totalProposals || 0 }}
                    </v-card-text>
                  </v-card>
                </v-col>
                
                <v-col cols="12" md="4">
                  <v-card>
                    <v-card-title>Active Sources</v-card-title>
                    <v-card-text class="text-h3 text-center">
                      {{ dashboardData.activeSources || 0 }}
                    </v-card-text>
                  </v-card>
                </v-col>
                
                <v-col cols="12" md="4">
                  <v-card>
                    <v-card-title>Last Scrape</v-card-title>
                    <v-card-text class="text-h5 text-center">
                      {{ formatDate(dashboardData.lastScrape) || 'Never' }}
                    </v-card-text>
                  </v-card>
                </v-col>
              </v-row>
              
              <!-- Proposals Table -->
              <v-card class="mt-4">
                <v-card-title>
                  Recent Proposals
                  <v-spacer></v-spacer>
                  <v-text-field
                    v-model="search"
                    append-icon="mdi-magnify"
                    label="Search"
                    single-line
                    hide-details
                  ></v-text-field>
                </v-card-title>
                
                <v-data-table
                  :headers="headers"
                  :items="dashboardData.proposals || []"
                  :search="search"
                  :loading="isLoading"
                  class="elevation-1"
                >
                  <template v-slot:item.date="{ item }">
                    {{ formatDate(item.date) }}
                  </template>
                </v-data-table>
              </v-card>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </div>
</template>

<script>
import { mapGetters } from 'vuex'

export default {
  name: 'Dashboard',
  data() {
    return {
      search: '',
      headers: [
        { title: 'ID', key: 'id' },
        { title: 'Title', key: 'title' },
        { title: 'Source', key: 'source' },
        { title: 'Date', key: 'date' },
        { title: 'Status', key: 'status' }
      ]
    }
  },
  computed: {
    ...mapGetters([
      'isLoading',
      'hasError',
      'errorMessage',
      'dashboardData',
      'lastUpdated'
    ])
  },
  methods: {
    formatDate(dateString) {
      if (!dateString) return 'N/A'
      const date = new Date(dateString)
      return date.toLocaleString()
    }
  },
  mounted() {
    this.$store.dispatch('fetchDashboardData')
  }
}
</script> 