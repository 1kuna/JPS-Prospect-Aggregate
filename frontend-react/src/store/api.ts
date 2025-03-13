import axios from 'axios';

// Create axios instance with default config
const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
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
    const response = await api.get('/data-sources');
    return response.data;
  } catch (error) {
    console.error('Error in fetchDataSources:', error);
    throw error;
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