import axios, { InternalAxiosRequestConfig } from 'axios';

// Create axios instance with default config
const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add request interceptor for handling auth tokens if needed
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // You can add auth tokens here if needed
    return config;
  },
  (error: any) => Promise.reject(error)
);

// Add response interceptor for error handling
api.interceptors.response.use(
  (response: any) => response,
  (error: any) => {
    // Handle common errors here
    if (error.response) {
      // Server responded with an error status
      console.error('API Error:', error.response.status, error.response.data);
    } else if (error.request) {
      // Request was made but no response received
      console.error('API No Response:', error.request);
    } else {
      // Something else happened
      console.error('API Error:', error.message);
    }
    return Promise.reject(error);
  }
);

// API functions
export async function fetchDashboardData({ page = 1, perPage = 50 } = {}) {
  const response = await api.get('/dashboard', {
    params: {
      page,
      per_page: perPage,
    },
  });
  return response.data;
}

export async function fetchDataSources() {
  const response = await api.get('/data_sources');
  return response.data;
}

export async function updateDataSource(id: string, data: any) {
  const response = await api.put(`/data_sources/${id}`, data);
  return response.data;
}

export async function createDataSource(data: any) {
  const response = await api.post('/data_sources', data);
  return response.data;
}

export async function deleteDataSource(id: string) {
  const response = await api.delete(`/data_sources/${id}`);
  return response.data;
}

export default api; 