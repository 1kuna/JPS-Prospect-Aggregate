import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios';

// Define standard API response type
export interface ApiResponse<T> {
  data: T;
  status: string;
  message?: string;
  pagination?: {
    page: number;
    per_page: number;
    total_items: number;
    total_pages: number;
  };
}

// Create API error class
export class ApiError extends Error {
  status: number;
  data?: any;
  
  constructor(message: string, status: number, data?: any) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

// Create the API client
const createApiClient = (config: AxiosRequestConfig = {}): AxiosInstance => {
  const client = axios.create({
    baseURL: '/api',
    headers: {
      'Content-Type': 'application/json',
    },
    ...config
  });
  
  // Request interceptor
  client.interceptors.request.use(
    (config) => {
      // You can add auth token or other headers here
      return config;
    },
    (error) => {
      return Promise.reject(error);
    }
  );
  
  // Response interceptor for normalization
  client.interceptors.response.use(
    (response: AxiosResponse): ApiResponse<any> => {
      // Normalize successful responses
      return {
        data: response.data?.data || response.data,
        status: response.data?.status || 'success',
        message: response.data?.message,
        pagination: response.data?.pagination
      };
    },
    (error) => {
      // Normalize error responses
      const message = error.response?.data?.message || error.message || 'Unknown error';
      const status = error.response?.status || 500;
      const data = error.response?.data;
      
      const normalizedError = new ApiError(message, status, data);
      throw normalizedError;
    }
  );
  
  return client;
};

// Create the API client instance
const apiClient = createApiClient();

// Type-safe API functions
export const api = {
  // ==============================
  // Data Sources
  // ==============================
  async fetchDataSources(): Promise<ApiResponse<DataSource[]>> {
    return apiClient.get('/data-sources');
  },
  
  async createDataSource(data: Partial<DataSource>): Promise<ApiResponse<DataSource>> {
    return apiClient.post('/data-sources', data);
  },
  
  async updateDataSource(id: string | number, data: Partial<DataSource>): Promise<ApiResponse<DataSource>> {
    return apiClient.put(`/data-sources/${id}`, data);
  },
  
  async deleteDataSource(id: string | number): Promise<ApiResponse<null>> {
    return apiClient.delete(`/data-sources/${id}`);
  },
  
  async pullDataSource(id: string | number): Promise<ApiResponse<any>> {
    return apiClient.post(`/data-sources/${id}/pull`);
  },
  
  async getScraperStatus(id: string | number): Promise<ApiResponse<any>> {
    return apiClient.get(`/data-sources/${id}/status`);
  },
  
  // ==============================
  // Proposals
  // ==============================
  async fetchProposals(params?: any): Promise<ApiResponse<Proposal[]>> {
    return apiClient.get('/proposals', { params });
  },
  
  async fetchProposal(id: string | number): Promise<ApiResponse<Proposal>> {
    return apiClient.get(`/proposals/${id}`);
  },
  
  // ==============================
  // Statistics & Dashboard
  // ==============================
  async fetchStatistics(): Promise<ApiResponse<any>> {
    return apiClient.get('/statistics');
  },
  
  async fetchDashboardData(params?: { page?: number; perPage?: number }): Promise<ApiResponse<any>> {
    return apiClient.get('/dashboard', { params });
  },
  
  // ==============================
  // System
  // ==============================
  async fetchSystemStatus(): Promise<ApiResponse<any>> {
    return apiClient.get('/system/status');
  },
  
  // ==============================
  // Generic Methods
  // ==============================
  async get<T>(url: string, config?: AxiosRequestConfig): Promise<ApiResponse<T>> {
    return apiClient.get(url, config);
  },
  
  async post<T>(url: string, data?: any, config?: AxiosRequestConfig): Promise<ApiResponse<T>> {
    return apiClient.post(url, data, config);
  },
  
  async put<T>(url: string, data?: any, config?: AxiosRequestConfig): Promise<ApiResponse<T>> {
    return apiClient.put(url, data, config);
  },
  
  async delete<T>(url: string, config?: AxiosRequestConfig): Promise<ApiResponse<T>> {
    return apiClient.delete(url, config);
  }
};

export default api; 