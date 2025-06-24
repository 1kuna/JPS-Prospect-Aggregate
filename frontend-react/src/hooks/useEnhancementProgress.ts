import { useEffect, useRef, useState, useCallback } from 'react';
import { useQueryClient } from '@tanstack/react-query';

export interface EnhancementProgressEvent {
  event_type: 'connected' | 'values_started' | 'values_completed' | 'values_failed' |
              'contacts_started' | 'contacts_completed' | 'contacts_failed' |
              'naics_started' | 'naics_completed' | 'naics_failed' |
              'titles_started' | 'titles_completed' | 'titles_failed' |
              'completed' | 'timeout' | 'error' | 'keepalive';
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
  
  const enhancementTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  
  const eventSourceRef = useRef<EventSource | null>(null);
  const queryClient = useQueryClient();
  
  // Use refs to store current callbacks and avoid dependency issues
  const callbacksRef = useRef(options);
  callbacksRef.current = options;

  const disconnect = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    
    // Clear enhancement timeout
    if (enhancementTimeoutRef.current) {
      clearTimeout(enhancementTimeoutRef.current);
      enhancementTimeoutRef.current = null;
    }
    
    setIsConnected(false);
    setIsEnhancing(false);
    setCurrentStep(null);
  }, []);

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
        callbacksRef.current.onProgressUpdate?.(progressEvent);

        switch (progressEvent.event_type) {
          case 'connected':
            setIsConnected(true);
            break;

          case 'values_started':
            setIsEnhancing(true);
            setCurrentStep('Parsing contract values...');
            
            // Set enhancement timeout (2 minutes max)
            if (enhancementTimeoutRef.current) {
              clearTimeout(enhancementTimeoutRef.current);
            }
            enhancementTimeoutRef.current = setTimeout(() => {
              console.warn('Enhancement timeout - forcing cleanup');
              setError('Enhancement timed out');
              callbacksRef.current.onError?.('Enhancement timed out');
              disconnect();
            }, 120000); // 2 minutes
            break;

          case 'values_completed': {
            const isSkipped = progressEvent.data?.skipped === true;
            if (!isSkipped) {
              setProgress(prev => ({ ...prev, ...progressEvent.data }));
              callbacksRef.current.onFieldUpdate?.('values', progressEvent.data || {});
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
            } else {
              // Step was skipped - no need to update data
              console.log(`Values step skipped for prospect ${id}: ${progressEvent.data?.reason}`);
            }
            break;
          }

          case 'contacts_started':
            setCurrentStep('Extracting contact information...');
            break;

          case 'contacts_completed': {
            const isSkipped = progressEvent.data?.skipped === true;
            if (!isSkipped) {
              setProgress(prev => ({ ...prev, ...progressEvent.data }));
              callbacksRef.current.onFieldUpdate?.('contacts', progressEvent.data || {});
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
            } else {
              // Step was skipped - no need to update data
              console.log(`Contacts step skipped for prospect ${id}: ${progressEvent.data?.reason}`);
            }
            break;
          }

          case 'naics_started':
            setCurrentStep('Classifying NAICS code...');
            break;

          case 'naics_completed': {
            const isSkipped = progressEvent.data?.skipped === true;
            if (!isSkipped) {
              setProgress(prev => ({ ...prev, ...progressEvent.data }));
              callbacksRef.current.onFieldUpdate?.('naics', progressEvent.data || {});
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
            } else {
              // Step was skipped - no need to update data
              console.log(`NAICS step skipped for prospect ${id}: ${progressEvent.data?.reason}`);
            }
            break;
          }

          case 'titles_started':
            setCurrentStep('Enhancing title...');
            break;

          case 'titles_completed': {
            const isSkipped = progressEvent.data?.skipped === true;
            if (!isSkipped) {
              setProgress(prev => ({ ...prev, ...progressEvent.data }));
              callbacksRef.current.onFieldUpdate?.('titles', progressEvent.data || {});
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
            } else {
              // Step was skipped - no need to update data
              console.log(`Titles step skipped for prospect ${id}: ${progressEvent.data?.reason}`);
            }
            break;
          }

          case 'completed':
            setIsEnhancing(false);
            setCurrentStep(null);
            // Update with completion data including timestamp
            if (progressEvent.data?.ollama_processed_at) {
              callbacksRef.current.onFieldUpdate?.('completion', {
                enhancement_status: 'idle',
                ollama_processed_at: progressEvent.data.ollama_processed_at
              });
            }
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
            callbacksRef.current.onComplete?.();
            // Force disconnect to ensure cleanup
            setTimeout(() => disconnect(), 100);
            break;

          case 'values_failed':
          case 'contacts_failed':
          case 'naics_failed':
          case 'titles_failed': {
            const errorMsg = (progressEvent.data?.error as string) || 'Enhancement step failed';
            setError(errorMsg);
            callbacksRef.current.onError?.(errorMsg);
            break;
          }

          case 'keepalive':
            // Just a keepalive message, no action needed
            break;

          case 'timeout': {
            const reason = progressEvent.data?.reason as string;
            const errorMessage = reason === 'idle_timeout' ? 
              'Enhancement timed out due to inactivity' : 
              'Enhancement timed out';
            setError(errorMessage);
            setIsEnhancing(false);
            setCurrentStep(null);
            callbacksRef.current.onError?.(errorMessage);
            disconnect();
            break;
          }

          case 'error': {
            const errorMessage = (progressEvent.data?.error as string) || 'Unknown error occurred';
            setError(errorMessage);
            setIsEnhancing(false);
            setCurrentStep(null);
            callbacksRef.current.onError?.(errorMessage);
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
      callbacksRef.current.onError?.('Connection to enhancement progress lost');
    };

  }, [queryClient, disconnect]);

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
      // Clear timeout on unmount
      if (enhancementTimeoutRef.current) {
        clearTimeout(enhancementTimeoutRef.current);
      }
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