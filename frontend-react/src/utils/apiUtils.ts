/**
 * API utilities for consistent HTTP request handling across the application
 */

export interface ApiError extends Error {
  status?: number;
  statusText?: string;
}

export interface FetchOptions extends RequestInit {
  timeout?: number;
}

/**
 * Enhanced fetch with consistent error handling and timeout support
 * @param url - Request URL
 * @param options - Fetch options with optional timeout
 * @returns Promise resolving to parsed JSON response
 * @throws ApiError with detailed error information
 */
export const fetchWithErrorHandling = async <T = unknown>(
  url: string,
  options: FetchOptions = {}
): Promise<T> => {
  const { timeout = 30000, ...fetchOptions } = options;

  // Create abort controller for timeout
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);

  try {
    const response = await fetch(url, {
      ...fetchOptions,
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      // Try to get error details from response
      let errorData: { error?: string; message?: string } = {};
      try {
        errorData = await response.json();
      } catch {
        // If JSON parsing fails, use default error structure
        errorData = {
          error: `HTTP ${response.status}: ${response.statusText}`,
          message: `Request failed with status ${response.status}`,
        };
      }

      const apiError = new Error(
        errorData.error || errorData.message || `Request failed: ${response.statusText}`
      ) as ApiError;
      
      apiError.status = response.status;
      apiError.statusText = response.statusText;
      
      throw apiError;
    }

    // Handle empty responses
    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
      return await response.json();
    } else {
      return await response.text() as T;
    }
  } catch (error) {
    clearTimeout(timeoutId);

    if (error instanceof Error && error.name === 'AbortError') {
      throw new Error(`Request timeout after ${timeout}ms`);
    }

    // Re-throw API errors
    if (error instanceof Error && 'status' in error) {
      throw error;
    }

    // Handle network errors
    throw new Error(`Network error: ${error instanceof Error ? error.message : 'Unknown error'}`);
  }
};

/**
 * GET request with error handling
 * @param url - Request URL
 * @param options - Fetch options
 * @returns Promise resolving to parsed JSON response
 */
export const get = <T = unknown>(url: string, options: FetchOptions = {}): Promise<T> => {
  return fetchWithErrorHandling<T>(url, {
    ...options,
    method: 'GET',
  });
};

/**
 * POST request with error handling
 * @param url - Request URL
 * @param data - Request body data
 * @param options - Fetch options
 * @returns Promise resolving to parsed JSON response
 */
export const post = <T = unknown>(
  url: string,
  data?: unknown,
  options: FetchOptions = {}
): Promise<T> => {
  return fetchWithErrorHandling<T>(url, {
    ...options,
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    body: data ? JSON.stringify(data) : undefined,
  });
};

/**
 * PUT request with error handling
 * @param url - Request URL
 * @param data - Request body data
 * @param options - Fetch options
 * @returns Promise resolving to parsed JSON response
 */
export const put = <T = unknown>(
  url: string,
  data?: unknown,
  options: FetchOptions = {}
): Promise<T> => {
  return fetchWithErrorHandling<T>(url, {
    ...options,
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    body: data ? JSON.stringify(data) : undefined,
  });
};

/**
 * DELETE request with error handling
 * @param url - Request URL
 * @param options - Fetch options
 * @returns Promise resolving to parsed JSON response
 */
export const del = <T = unknown>(url: string, options: FetchOptions = {}): Promise<T> => {
  return fetchWithErrorHandling<T>(url, {
    ...options,
    method: 'DELETE',
  });
};

/**
 * Handles common API response patterns
 * @param response - API response with status and data structure
 * @returns The data portion of the response
 * @throws Error if response indicates failure
 */
export const handleApiResponse = <T = unknown>(response: {
  status: string;
  data?: T;
  message?: string;
  error?: string;
}): T => {
  if (response.status === 'success' && response.data) {
    return response.data;
  }

  if (response.status === 'error') {
    throw new Error(response.error || response.message || 'API request failed');
  }

  throw new Error('Invalid API response format');
};

/**
 * Creates query string from object parameters
 * @param params - Object with query parameters
 * @returns URL-encoded query string
 */
export const buildQueryString = (params: Record<string, string | number | boolean | undefined | null>): string => {
  const searchParams = new URLSearchParams();

  Object.entries(params).forEach(([key, value]) => {
    if (value !== null && value !== undefined && value !== '') {
      searchParams.append(key, String(value));
    }
  });

  const queryString = searchParams.toString();
  return queryString ? `?${queryString}` : '';
};

/**
 * Utility for building API URLs with base path and query parameters
 * @param endpoint - API endpoint path
 * @param params - Query parameters
 * @param baseUrl - Base URL (defaults to current origin)
 * @returns Complete URL string
 */
export const buildApiUrl = (
  endpoint: string,
  params?: Record<string, string | number | boolean | undefined | null>,
  baseUrl?: string
): string => {
  const base = baseUrl || '';
  const path = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  const query = params ? buildQueryString(params) : '';
  
  return `${base}${path}${query}`;
};