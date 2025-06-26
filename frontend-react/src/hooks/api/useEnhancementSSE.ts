import { useEffect, useRef, useState, useCallback } from 'react';
import { useQueryClient } from '@tanstack/react-query';

export interface EnhancementState {
  status: 'idle' | 'queued' | 'processing' | 'completed' | 'failed';
  queuePosition?: number;
  currentStep?: string;
  progress: {
    values?: { completed: boolean; skipped?: boolean; data?: any };
    contacts?: { completed: boolean; skipped?: boolean; data?: any };
    naics?: { completed: boolean; skipped?: boolean; data?: any };
    titles?: { completed: boolean; skipped?: boolean; data?: any };
  };
  error?: string;
  startedAt?: string;
  completedAt?: string;
  estimatedTimeRemaining?: number;
}

export interface SSEEvent {
  event_type: string;
  timestamp: string;
  prospect_id?: string;
  data?: Record<string, unknown>;
}

interface UseEnhancementSSEOptions {
  onStateChange?: (state: EnhancementState) => void;
  onComplete?: () => void;
  onError?: (error: string) => void;
  autoReconnect?: boolean;
  reconnectDelay?: number;
}

export function useEnhancementSSE(
  prospectId: string | null,
  options: UseEnhancementSSEOptions = {}
) {
  const [state, setState] = useState<EnhancementState>({
    status: 'idle',
    progress: {}
  });
  const [isConnected, setIsConnected] = useState(false);
  
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const stateRef = useRef(state);
  const queryClient = useQueryClient();
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;
  
  // Default options
  const {
    onStateChange,
    onComplete,
    onError,
    autoReconnect = true,
    reconnectDelay = 3000
  } = options;

  // Update state ref when state changes
  useEffect(() => {
    stateRef.current = state;
  }, [state]);

  const updateState = useCallback((updates: Partial<EnhancementState>) => {
    setState(prev => {
      const newState = { ...prev, ...updates };
      onStateChange?.(newState);
      return newState;
    });
  }, [onStateChange]);

  const handleSSEMessage = useCallback((event: MessageEvent) => {
    try {
      const sseEvent: SSEEvent = JSON.parse(event.data);
      
      switch (sseEvent.event_type) {
        case 'connected':
          setIsConnected(true);
          break;

        case 'queue_position_update':
          updateState({
            status: 'queued',
            queuePosition: sseEvent.data?.position as number,
            estimatedTimeRemaining: sseEvent.data?.estimated_time as number
          });
          break;

        case 'processing_started':
          updateState({
            status: 'processing',
            startedAt: sseEvent.timestamp,
            queuePosition: undefined
          });
          break;

        case 'values_started':
          updateState({ currentStep: 'Parsing contract values...' });
          break;

        case 'values_completed':
          updateState({
            progress: {
              ...stateRef.current.progress,
              values: {
                completed: true,
                skipped: sseEvent.data?.skipped as boolean,
                data: sseEvent.data
              }
            }
          });
          
          // Update query cache if not skipped
          if (!sseEvent.data?.skipped && prospectId) {
            queryClient.setQueryData(['prospects'], (oldData: any) => {
              if (!oldData?.data) return oldData;
              return {
                ...oldData,
                data: oldData.data.map((p: any) =>
                  p.id === prospectId ? { ...p, ...sseEvent.data } : p
                )
              };
            });
          }
          break;

        case 'contacts_started':
          updateState({ currentStep: 'Extracting contact information...' });
          break;

        case 'contacts_completed':
          updateState({
            progress: {
              ...stateRef.current.progress,
              contacts: {
                completed: true,
                skipped: sseEvent.data?.skipped as boolean,
                data: sseEvent.data
              }
            }
          });
          
          if (!sseEvent.data?.skipped && prospectId) {
            queryClient.setQueryData(['prospects'], (oldData: any) => {
              if (!oldData?.data) return oldData;
              return {
                ...oldData,
                data: oldData.data.map((p: any) =>
                  p.id === prospectId ? { ...p, ...sseEvent.data } : p
                )
              };
            });
          }
          break;

        case 'naics_started':
          updateState({ currentStep: 'Classifying NAICS code...' });
          break;

        case 'naics_completed':
          updateState({
            progress: {
              ...stateRef.current.progress,
              naics: {
                completed: true,
                skipped: sseEvent.data?.skipped as boolean,
                data: sseEvent.data
              }
            }
          });
          
          if (!sseEvent.data?.skipped && prospectId) {
            queryClient.setQueryData(['prospects'], (oldData: any) => {
              if (!oldData?.data) return oldData;
              return {
                ...oldData,
                data: oldData.data.map((p: any) =>
                  p.id === prospectId ? { ...p, ...sseEvent.data } : p
                )
              };
            });
          }
          break;

        case 'titles_started':
          updateState({ currentStep: 'Enhancing title...' });
          break;

        case 'titles_completed':
          updateState({
            progress: {
              ...stateRef.current.progress,
              titles: {
                completed: true,
                skipped: sseEvent.data?.skipped as boolean,
                data: sseEvent.data
              }
            }
          });
          
          if (!sseEvent.data?.skipped && prospectId) {
            queryClient.setQueryData(['prospects'], (oldData: any) => {
              if (!oldData?.data) return oldData;
              return {
                ...oldData,
                data: oldData.data.map((p: any) =>
                  p.id === prospectId ? { ...p, ...sseEvent.data } : p
                )
              };
            });
          }
          break;

        case 'completed':
          updateState({
            status: 'completed',
            completedAt: sseEvent.timestamp,
            currentStep: undefined
          });
          
          // Final cache update
          if (prospectId) {
            queryClient.invalidateQueries({ queryKey: ['prospects'] });
            queryClient.invalidateQueries({ queryKey: ['ai-enrichment-status'] });
            queryClient.invalidateQueries({ queryKey: ['llm-outputs'] });
          }
          
          onComplete?.();
          break;

        case 'failed':
        case 'error':
          const errorMsg = sseEvent.data?.error as string || 'Enhancement failed';
          updateState({
            status: 'failed',
            error: errorMsg,
            currentStep: undefined
          });
          onError?.(errorMsg);
          break;

        case 'keepalive':
          // Just a heartbeat, no action needed
          break;
      }
    } catch (err) {
      console.error('Failed to parse SSE event:', err);
    }
  }, [prospectId, queryClient, updateState, onComplete, onError]);

  const connect = useCallback((id: string) => {
    // Clean up existing connection
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    // Clear any pending reconnect
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    // Reset state
    setState({
      status: 'idle',
      progress: {}
    });
    setIsConnected(false);

    // Create new SSE connection
    const eventSource = new EventSource(`/api/llm/enhancement-progress/${id}`);
    eventSourceRef.current = eventSource;

    eventSource.onopen = () => {
      setIsConnected(true);
      reconnectAttempts.current = 0; // Reset on successful connection
      console.log('SSE connection established for prospect:', id);
    };

    eventSource.onmessage = handleSSEMessage;

    eventSource.onerror = (err) => {
      console.error('SSE connection error:', err);
      setIsConnected(false);
      
      // Attempt reconnect if enabled and under retry limit
      if (autoReconnect && reconnectAttempts.current < maxReconnectAttempts) {
        reconnectAttempts.current += 1;
        const delay = Math.min(reconnectDelay * reconnectAttempts.current, 30000); // Max 30s delay
        
        reconnectTimeoutRef.current = setTimeout(() => {
          console.log(`Attempting to reconnect SSE (attempt ${reconnectAttempts.current}/${maxReconnectAttempts})...`);
          connect(id);
        }, delay);
      } else {
        console.error('Max SSE reconnection attempts reached');
        onError?.('Connection failed after multiple attempts');
      }
    };

    return eventSource;
  }, [handleSSEMessage, autoReconnect, reconnectDelay]);

  const disconnect = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    
    setIsConnected(false);
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

  return {
    state,
    isConnected,
    connect,
    disconnect
  };
}