import axios from 'axios';

// Create axios instance with default config
const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
    'Cache-Control': 'no-cache',
    'Pragma': 'no-cache'
  },
  timeout: 10000, // 10 seconds timeout
});

// Add response interceptor for debugging
api.interceptors.response.use(
  response => {
    console.log(`API Response [${response.config.url}]:`, response.data);
    return response;
  },
  error => {
    console.error(`API Error [${error.config?.url}]:`, error.response?.data || error.message);
    return Promise.reject(error);
  }
);

// Add request interceptor for debugging
api.interceptors.request.use(
  config => {
    // Add timestamp to GET requests to prevent caching
    if (config.method?.toLowerCase() === 'get') {
      config.params = {
        ...config.params,
        _t: new Date().getTime()
      };
    }
    
    console.log(`API Request [${config.method?.toUpperCase()}] ${config.url}:`, config.params || config.data);
    return config;
  },
  error => {
    console.error('API Request Error:', error);
    return Promise.reject(error);
  }
);

// Define types
interface PaginationParams {
  page?: number;
  perPage?: number;
  sortBy?: string;
  sortOrder?: string;
}

interface DataSourceData {
  name: string;
  url: string;
  description?: string;
  status?: string;
}

// Simplified API functions
export async function fetchDashboardData({ page = 1, perPage = 50 }: PaginationParams = {}) {
  try {
    const response = await api.get('/dashboard', {
      params: { page, per_page: perPage },
    });
    return response.data;
  } catch (error) {
    console.error('Error in fetchDashboardData:', error);
    throw error;
  }
}

export async function fetchProposals({ page = 1, perPage = 50, sortBy = 'release_date', sortOrder = 'desc' }: PaginationParams = {}) {
  try {
    const response = await api.get('/proposals', {
      params: { page, per_page: perPage, sort_by: sortBy, sort_order: sortOrder },
    });
    return response.data;
  } catch (error) {
    console.error('Error in fetchProposals:', error);
    throw error;
  }
}

export async function fetchDataSources() {
  try {
    console.log('API: Fetching data sources...');
    const response = await api.get('/data-sources', {
      // Increase timeout for this specific request
      timeout: 15000, // 15 seconds
      // Force fresh data
      headers: {
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache',
        'Expires': '0'
      },
      // Add a timestamp to prevent caching
      params: {
        _t: new Date().getTime()
      }
    });
    console.log('API: Data sources fetch successful');
    return response.data;
  } catch (error: any) {
    // Enhance error logging
    if (error.response) {
      // The request was made and the server responded with a status code
      // that falls out of the range of 2xx
      console.error('API: Data sources fetch error - Server responded with:', {
        status: error.response.status,
        data: error.response.data
      });
    } else if (error.request) {
      // The request was made but no response was received
      console.error('API: Data sources fetch error - No response received:', error.request);
    } else {
      // Something happened in setting up the request that triggered an Error
      console.error('API: Data sources fetch error - Request setup error:', error.message);
    }
    
    // Add more context to the error
    const enhancedError = error;
    enhancedError.message = `Failed to fetch data sources: ${error.message}`;
    throw enhancedError;
  }
}

export async function updateDataSource(id: string | number, data: DataSourceData) {
  try {
    const response = await api.put(`/data-sources/${id}`, data);
    return response.data;
  } catch (error) {
    console.error('Error in updateDataSource:', error);
    throw error;
  }
}

export async function createDataSource(data: DataSourceData) {
  try {
    const response = await api.post('/data-sources', data);
    return response.data;
  } catch (error) {
    console.error('Error in createDataSource:', error);
    throw error;
  }
}

export async function deleteDataSource(id: string | number) {
  try {
    const response = await api.delete(`/data-sources/${id}`);
    return response.data;
  } catch (error) {
    console.error('Error in deleteDataSource:', error);
    throw error;
  }
}

export async function pullDataSource(id: string | number) {
  try {
    const response = await api.post(`/data-sources/${id}/pull`);
    return response.data;
  } catch (error) {
    console.error('Error in pullDataSource:', error);
    throw error;
  }
}

export async function getScraperStatus(id: string | number) {
  try {
    const response = await api.get(`/data-sources/${id}/status`);
    return response.data;
  } catch (error) {
    console.error('Error in getScraperStatus:', error);
    throw error;
  }
}

// New API functions for statistics and database operations
export async function fetchStatistics() {
  try {
    const response = await api.get('/statistics');
    return response.data;
  } catch (error) {
    console.error('Error in fetchStatistics:', error);
    throw error;
  }
}

export async function rebuildDatabase() {
  try {
    const response = await api.post('/database/rebuild');
    return response.data;
  } catch (error) {
    console.error('Error in rebuildDatabase:', error);
    throw error;
  }
}

export async function initializeDatabase() {
  try {
    const response = await api.post('/database/initialize');
    return response.data;
  } catch (error) {
    console.error('Error in initializeDatabase:', error);
    throw error;
  }
}

export async function resetEverything() {
  try {
    const response = await api.post('/database/reset');
    return response.data;
  } catch (error) {
    console.error('Error in resetEverything:', error);
    throw error;
  }
}

export async function manageBackups(action: 'create' | 'restore' | 'list', backupId?: string) {
  try {
    let response;
    if (action === 'create') {
      response = await api.post('/database/backups');
    } else if (action === 'restore' && backupId) {
      response = await api.post(`/database/backups/${backupId}/restore`);
    } else {
      response = await api.get('/database/backups');
    }
    return response.data;
  } catch (error) {
    console.error('Error in manageBackups:', error);
    throw error;
  }
}

export default api; 