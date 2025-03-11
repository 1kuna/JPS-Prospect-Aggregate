import axios from 'axios';

// Create axios instance with default config
const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

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
  return (await api.get('/dashboard', {
    params: { page, per_page: perPage },
  })).data;
}

export async function fetchProposals({ page = 1, perPage = 50, sortBy = 'release_date', sortOrder = 'desc' }: PaginationParams = {}) {
  return (await api.get('/proposals', {
    params: { page, per_page: perPage, sort_by: sortBy, sort_order: sortOrder },
  })).data;
}

export async function fetchDataSources() {
  return (await api.get('/data-sources')).data;
}

export async function updateDataSource(id: string | number, data: DataSourceData) {
  return (await api.put(`/data-sources/${id}`, data)).data;
}

export async function createDataSource(data: DataSourceData) {
  return (await api.post('/data-sources', data)).data;
}

export async function deleteDataSource(id: string | number) {
  return (await api.delete(`/data-sources/${id}`)).data;
}

export default api; 