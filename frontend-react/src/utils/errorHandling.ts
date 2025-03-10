import { AxiosError } from 'axios';

/**
 * Formats an API error into a user-friendly message
 */
export function formatApiError(error: unknown): string {
  if (error instanceof AxiosError) {
    // Handle Axios errors
    if (error.response) {
      // The request was made and the server responded with a status code
      // that falls out of the range of 2xx
      const data = error.response.data;
      
      if (typeof data === 'string') {
        return data;
      }
      
      if (data && typeof data === 'object' && 'message' in data) {
        return String(data.message);
      }
      
      if (data && typeof data === 'object' && 'error' in data) {
        return String(data.error);
      }
      
      return `Server error: ${error.response.status}`;
    } else if (error.request) {
      // The request was made but no response was received
      return 'No response from server. Please check your connection.';
    } else {
      // Something happened in setting up the request
      return `Error: ${error.message}`;
    }
  }
  
  // Handle other types of errors
  if (error instanceof Error) {
    return error.message;
  }
  
  return String(error);
}

/**
 * Determines if an error is a network error
 */
export function isNetworkError(error: unknown): boolean {
  if (error instanceof AxiosError) {
    return !error.response && !!error.request;
  }
  return false;
}

/**
 * Determines if an error is a server error (5xx)
 */
export function isServerError(error: unknown): boolean {
  if (error instanceof AxiosError && error.response) {
    return error.response.status >= 500;
  }
  return false;
}

/**
 * Determines if an error is a client error (4xx)
 */
export function isClientError(error: unknown): boolean {
  if (error instanceof AxiosError && error.response) {
    return error.response.status >= 400 && error.response.status < 500;
  }
  return false;
}

/**
 * Creates a retry function with exponential backoff
 */
export function createRetryFunction(
  fn: () => Promise<any>,
  maxRetries = 3,
  initialDelay = 1000
): () => Promise<any> {
  let retryCount = 0;
  
  const retry = async (): Promise<any> => {
    try {
      return await fn();
    } catch (error) {
      if (retryCount >= maxRetries || !isServerError(error)) {
        throw error;
      }
      
      retryCount++;
      const delay = initialDelay * Math.pow(2, retryCount - 1);
      
      console.log(`Retrying (${retryCount}/${maxRetries}) after ${delay}ms...`);
      
      return new Promise(resolve => {
        setTimeout(() => resolve(retry()), delay);
      });
    }
  };
  
  return retry;
} 