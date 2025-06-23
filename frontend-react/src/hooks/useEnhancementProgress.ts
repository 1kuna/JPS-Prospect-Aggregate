import { useEffect, useRef, useState, useCallback } from 'react';
import { useQueryClient } from '@tanstack/react-query';

export interface EnhancementProgressEvent {
  event_type: 'connected' | 'values_started' | 'values_completed' | 'values_failed' |
              'contacts_started' | 'contacts_completed' | 'contacts_failed' |
              'naics_started' | 'naics_completed' | 'naics_failed' |
              'titles_started' | 'titles_completed' | 'titles_failed' |
              'completed' | 'timeout' | 'error';
  timestamp: string;
  prospect_id?: string;
  data?: Record<string, unknown>;
}

interface UseEnhancementProgressOptions {
  onProgressUpdate?: (event: EnhancementProgressEvent) => void;
  onFieldUpdate?: (field: string, value: Record<string, unknown>) => void;
  onComplete?: () => void;
  onError?: (error: string) => void;
}

export function useEnhancementProgress(
  prospectId: string | null,
  options: UseEnhancementProgressOptions = {}
) {
  const [isConnected, setIsConnected] = useState(false);
  const [isEnhancing, setIsEnhancing] = useState(false);
  const [currentStep, setCurrentStep] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState<Record<string, unknown>>({});
  
  const eventSourceRef = useRef<EventSource | null>(null);
  const queryClient = useQueryClient();
  
  const { onProgressUpdate, onFieldUpdate, onComplete, onError } = options;

  const connect = useCallback((id: string) => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    // Clear previous state
    setIsConnected(false);
    setIsEnhancing(false);
    setCurrentStep(null);
    setError(null);
    setProgress({});

    const eventSource = new EventSource(`/api/llm/enhancement-progress/${id}`);
    eventSourceRef.current = eventSource;

    eventSource.onopen = () => {
      setIsConnected(true);
      setError(null);
    };

    eventSource.onmessage = (event) => {
      try {
        const progressEvent: EnhancementProgressEvent = JSON.parse(event.data);
        onProgressUpdate?.(progressEvent);

        switch (progressEvent.event_type) {
          case 'connected':
            setIsConnected(true);
            break;

          case 'values_started':
            setIsEnhancing(true);
            setCurrentStep('Parsing contract values...');
            break;

          case 'values_completed':
            setProgress(prev => ({ ...prev, ...progressEvent.data }));
            onFieldUpdate?.('values', progressEvent.data || {});
            // Optimistically update query cache
            queryClient.setQueryData(['prospects'], (oldData: unknown) => {
              if (!oldData || typeof oldData !== 'object' || !('data' in oldData)) return oldData;
              const dataObj = oldData as { data: Array<Record<string, unknown>> };
              return {
                ...dataObj,
                data: dataObj.data.map((prospect: Record<string, unknown>) =>
                  prospect.id === id
                    ? { ...prospect, ...progressEvent.data, _recentlyUpdated: 'values', _updateTimestamp: Date.now() }
                    : prospect
                )
              };
            });
            break;

          case 'contacts_started':
            setCurrentStep('Extracting contact information...');
            break;

          case 'contacts_completed':
            setProgress(prev => ({ ...prev, ...progressEvent.data }));
            onFieldUpdate?.('contacts', progressEvent.data || {});
            // Optimistically update query cache
            queryClient.setQueryData(['prospects'], (oldData: unknown) => {
              if (!oldData || typeof oldData !== 'object' || !('data' in oldData)) return oldData;
              const dataObj = oldData as { data: Array<Record<string, unknown>> };
              return {
                ...dataObj,
                data: dataObj.data.map((prospect: Record<string, unknown>) =>
                  prospect.id === id
                    ? { ...prospect, ...progressEvent.data, _recentlyUpdated: 'contacts', _updateTimestamp: Date.now() }
                    : prospect
                )
              };
            });
            break;

          case 'naics_started':
            setCurrentStep('Classifying NAICS code...');
            break;

          case 'naics_completed':
            setProgress(prev => ({ ...prev, ...progressEvent.data }));
            onFieldUpdate?.('naics', progressEvent.data || {});
            // Optimistically update query cache
            queryClient.setQueryData(['prospects'], (oldData: unknown) => {
              if (!oldData || typeof oldData !== 'object' || !('data' in oldData)) return oldData;
              const dataObj = oldData as { data: Array<Record<string, unknown>> };
              return {
                ...dataObj,
                data: dataObj.data.map((prospect: Record<string, unknown>) =>
                  prospect.id === id
                    ? { ...prospect, ...progressEvent.data, _recentlyUpdated: 'naics', _updateTimestamp: Date.now() }
                    : prospect
                )
              };
            });
            break;

          case 'titles_started':
            setCurrentStep('Enhancing title...');
            break;

          case 'titles_completed':
            setProgress(prev => ({ ...prev, ...progressEvent.data }));
            onFieldUpdate?.('titles', progressEvent.data || {});
            // Optimistically update query cache
            queryClient.setQueryData(['prospects'], (oldData: unknown) => {
              if (!oldData || typeof oldData !== 'object' || !('data' in oldData)) return oldData;
              const dataObj = oldData as { data: Array<Record<string, unknown>> };
              return {
                ...dataObj,
                data: dataObj.data.map((prospect: Record<string, unknown>) =>
                  prospect.id === id
                    ? { ...prospect, ...progressEvent.data, _recentlyUpdated: 'titles', _updateTimestamp: Date.now() }
                    : prospect
                )
              };
            });
            break;

          case 'completed':
            setIsEnhancing(false);
            setCurrentStep(null);
            // Final update to mark as completed
            queryClient.setQueryData(['prospects'], (oldData: unknown) => {
              if (!oldData || typeof oldData !== 'object' || !('data' in oldData)) return oldData;
              const dataObj = oldData as { data: Array<Record<string, unknown>> };
              return {
                ...dataObj,
                data: dataObj.data.map((prospect: Record<string, unknown>) =>
                  prospect.id === id
                    ? { ...prospect, enhancement_status: 'idle', ollama_processed_at: progressEvent.data?.ollama_processed_at }
                    : prospect
                )
              };
            });
            // Invalidate queries to ensure fresh data
            queryClient.invalidateQueries({ queryKey: ['prospects'] });
            onComplete?.();
            disconnect();
            break;

          case 'values_failed':
          case 'contacts_failed':
          case 'naics_failed':
          case 'titles_failed': {
            const errorMsg = (progressEvent.data?.error as string) || 'Enhancement step failed';
            setError(errorMsg);
            onError?.(errorMsg);
            break;
          }

          case 'timeout':
            setError('Enhancement timed out');
            setIsEnhancing(false);
            setCurrentStep(null);
            onError?.('Enhancement timed out');
            disconnect();
            break;

          case 'error': {
            const errorMessage = (progressEvent.data?.error as string) || 'Unknown error occurred';
            setError(errorMessage);
            setIsEnhancing(false);
            setCurrentStep(null);
            onError?.(errorMessage);
            disconnect();
            break;
          }
        }
      } catch (err) {
        console.error('Failed to parse SSE event:', err);
        setError('Failed to parse progress update');
      }
    };

    eventSource.onerror = (err) => {
      console.error('SSE connection error:', err);
      setIsConnected(false);
      setError('Connection to enhancement progress lost');
      onError?.('Connection to enhancement progress lost');
    };

  }, [onProgressUpdate, onFieldUpdate, onComplete, onError, queryClient]);

  const disconnect = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    setIsConnected(false);
    setIsEnhancing(false);
    setCurrentStep(null);
  }, []);

  // Connect when prospectId is provided
  useEffect(() => {
    if (prospectId) {
      connect(prospectId);
    } else {
      disconnect();
    }

    return () => {
      disconnect();
    };
  }, [prospectId, connect, disconnect]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  return {
    isConnected,
    isEnhancing,
    currentStep,
    error,
    progress,
    connect: (id: string) => connect(id),
    disconnect
  };
}