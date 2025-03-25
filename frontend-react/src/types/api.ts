import { AxiosError } from 'axios';

export interface PaginationData {
  page: number;
  per_page: number;
  total_items: number;
  total_pages: number;
}

export interface ApiResponse<T> {
  data: T;
  status: string;
  message?: string;
  pagination?: PaginationData;
}

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public data?: any
  ) {
    super(message);
    this.name = 'ApiError';
  }

  static fromAxiosError(error: AxiosError): ApiError {
    return new ApiError(
      error.response?.data?.message || error.message,
      error.response?.status || 500,
      error.response?.data
    );
  }
}

export interface QueryConfig<T = any> {
  enabled?: boolean;
  staleTime?: number;
  cacheTime?: number;
  retry?: number | boolean;
  retryDelay?: number;
  onSuccess?: (data: T) => void;
  onError?: (error: ApiError) => void;
  onSettled?: (data: T | undefined, error: ApiError | null) => void;
}

export interface MutationConfig<T = any, V = any> {
  onSuccess?: (data: T, variables: V) => void | Promise<void>;
  onError?: (error: ApiError, variables: V) => void;
  onSettled?: (data: T | undefined, error: ApiError | null, variables: V) => void;
} 