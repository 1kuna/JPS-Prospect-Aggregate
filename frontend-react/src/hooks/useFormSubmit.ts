import { useState, useCallback } from 'react';

interface UseFormSubmitOptions<R> {
  onSuccess?: (data: R) => void;
  onError?: (error: Error) => void;
  resetForm?: () => void;
}

interface UseFormSubmitResult<T, R> {
  loading: boolean;
  error: Error | null;
  handleSubmit: (values: T) => Promise<R | undefined>;
  reset: () => void;
}

export function useFormSubmit<T, R = any>(
  submitFn: (values: T) => Promise<R>,
  options: UseFormSubmitOptions<R> = {}
): UseFormSubmitResult<T, R> {
  const { onSuccess, onError, resetForm } = options;
  
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<Error | null>(null);

  const handleSubmit = useCallback(async (values: T): Promise<R | undefined> => {
    setLoading(true);
    setError(null);
    
    try {
      const result = await submitFn(values);
      onSuccess?.(result);
      resetForm?.();
      return result;
    } catch (err) {
      const error = err instanceof Error ? err : new Error(String(err));
      setError(error);
      onError?.(error);
      return undefined;
    } finally {
      setLoading(false);
    }
  }, [submitFn, onSuccess, onError, resetForm]);

  const reset = useCallback(() => {
    setLoading(false);
    setError(null);
  }, []);

  return { loading, error, handleSubmit, reset };
} 