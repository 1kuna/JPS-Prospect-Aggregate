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
          <v-card-title>
            Data Sources
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
            
            <div v-else-if="!dataSources || dataSources.length === 0">
              <v-alert type="info">
                No data sources available. Click the refresh button to load data.
              </v-alert>
            </div>
            
            <div v-else>
              <v-row>
                <v-col
                  v-for="(source, index) in dataSources"
                  :key="index"
                  cols="12"
                  md="6"
                  lg="4"
                >
                  <v-card>
                    <v-card-title>
                      {{ source.name }}
                      <v-spacer></v-spacer>
                      <v-chip
                        :color="source.active ? 'success' : 'error'"
                        size="small"
                      >
                        {{ source.active ? 'Active' : 'Inactive' }}
                      </v-chip>
                    </v-card-title>
                    <v-card-text>
                      <p><strong>URL:</strong> {{ source.url }}</p>
                      <p><strong>Last Scrape:</strong> {{ formatDate(source.lastScrape) || 'Never' }}</p>
                      <p><strong>Proposals:</strong> {{ source.proposalCount || 0 }}</p>
                    </v-card-text>
                    <v-card-actions>
                      <v-btn
                        color="primary"
                        variant="text"
                        @click="triggerScrape(source.id)"
                        :loading="source.scraping"
                      >
                        Scrape Now
                      </v-btn>
                      <v-btn
                        :color="source.active ? 'error' : 'success'"
                        variant="text"
                        @click="toggleSourceStatus(source.id, !source.active)"
                      >
                        {{ source.active ? 'Deactivate' : 'Activate' }}
                      </v-btn>
                    </v-card-actions>
                  </v-card>
                </v-col>
              </v-row>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </div>
</template>

<script>
import { mapGetters } from 'vuex'
import axios from 'axios'

// Get the API base URL from environment or use default
const apiBaseUrl = process.env.VUE_APP_API_URL || 'http://localhost:5000/api'

export default {
  name: 'DataSources',
  data() {
    return {
      scrapingSourceIds: []
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
    // Add scraping status to each data source
    sourcesWithStatus() {
      if (!this.dataSources) return []
      return this.dataSources.map(source => ({
        ...source,
        scraping: this.scrapingSourceIds.includes(source.id)
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
        this.$store.dispatch('fetchDataSources')
      } catch (error) {
        console.error('Error triggering scrape:', error)
        this.$store.commit('SET_ERROR', 'Failed to trigger scrape')
      } finally {
        this.scrapingSourceIds = this.scrapingSourceIds.filter(id => id !== sourceId)
      }
    },
    async toggleSourceStatus(sourceId, active) {
      try {
        await axios.put(`${apiBaseUrl}/data-sources/${sourceId}`, { active })
        this.$store.dispatch('fetchDataSources')
      } catch (error) {
        console.error('Error updating source status:', error)
        this.$store.commit('SET_ERROR', 'Failed to update source status')
      }
    }
  },
  mounted() {
    this.$store.dispatch('fetchDataSources')
  }
}
</script> 