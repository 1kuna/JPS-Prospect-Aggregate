import { createStore } from 'vuex'
import axios from 'axios'

// Get the API base URL from environment or use default
const apiBaseUrl = process.env.VUE_APP_API_URL || 'http://localhost:5001/api'

export default createStore({
  state: {
    loading: false,
    error: null,
    dashboardData: null,
    dataSources: [],
    lastUpdated: null
  },
  getters: {
    isLoading: state => state.loading,
    hasError: state => state.error !== null,
    errorMessage: state => state.error,
    dashboardData: state => state.dashboardData,
    dataSources: state => state.dataSources,
    lastUpdated: state => state.lastUpdated
  },
  mutations: {
    SET_LOADING(state, loading) {
      state.loading = loading
    },
    SET_ERROR(state, error) {
      state.error = error
    },
    SET_DASHBOARD_DATA(state, data) {
      state.dashboardData = data
      state.lastUpdated = new Date()
    },
    SET_DATA_SOURCES(state, sources) {
      state.dataSources = sources
    }
  },
  actions: {
    async fetchDashboardData({ commit }) {
      commit('SET_LOADING', true)
      commit('SET_ERROR', null)
      
      try {
        const response = await axios.get(`${apiBaseUrl}/dashboard`)
        commit('SET_DASHBOARD_DATA', response.data)
      } catch (error) {
        commit('SET_ERROR', error.message || 'Failed to fetch dashboard data')
        console.error('Error fetching dashboard data:', error)
      } finally {
        commit('SET_LOADING', false)
      }
    },
    
    async fetchDataSources({ commit }) {
      commit('SET_LOADING', true)
      commit('SET_ERROR', null)
      
      try {
        const response = await axios.get(`${apiBaseUrl}/data-sources`)
        commit('SET_DATA_SOURCES', response.data)
      } catch (error) {
        commit('SET_ERROR', error.message || 'Failed to fetch data sources')
        console.error('Error fetching data sources:', error)
      } finally {
        commit('SET_LOADING', false)
      }
    },
    
    refreshData({ dispatch }) {
      dispatch('fetchDashboardData')
      dispatch('fetchDataSources')
    }
  }
}) 