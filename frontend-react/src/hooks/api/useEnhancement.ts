import { useState, useCallback, useEffect, useRef } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { post, del, get, ApiError } from '@/utils/apiUtils';
import { 
  EnhancementProgress,
  UnifiedEnhancementState as UnifiedEnhancementStateType,
  ProspectsQueryData,
  Prospect
} from '@/types';

// Unified enhancement state for a single prospect
export interface EnhancementState {
  status: 'idle' | 'queued' | 'processing' | 'completed' | 'failed';
  queuePosition?: number;
  currentStep?: string;
  progress: EnhancementProgress;
  error?: string;
  startedAt?: string;
  completedAt?: string;
  estimatedTimeRemaining?: number;
}

// Request to enhance a prospect
interface EnhancementRequest {
  prospect_id: string;
  force_redo?: boolean;
  user_id?: number;
}

// Queue status from backend
interface QueueStatus {
  worker_running: boolean;
  current_item?: string;
  queue_size: number;
  pending_items: Array<{
    id: string;
    type: 'individual' | 'bulk';
    priority: number;
    prospect_id?: number;
    prospect_count: number;
    enhancement_type: string;
    created_at: string;
    status: string;
  }>;
  recent_completed: Array<{
    id: string;
    type: 'individual' | 'bulk';
    prospect_id?: number;
    status: string;
    completed_at?: string;
    error_message?: string;
  }>;
}

// SSE event type
interface EnhancementProgressEvent {
  event_type: 'connected' | 'queue_position_update' | 'processing_started' | 
              'values_started' | 'values_completed' | 'values_failed' |
              'contacts_started' | 'contacts_completed' | 'contacts_failed' |
              'naics_started' | 'naics_completed' | 'naics_failed' |
              'titles_started' | 'titles_completed' | 'titles_failed' |
              'completed' | 'failed' | 'error' | 'timeout' | 'keepalive';
  timestamp: string;
  prospect_id?: string;
  data?: Record<string, unknown>;
}

type UnifiedEnhancementState = UnifiedEnhancementStateType;

/**
 * Unified enhancement hook that combines queue management, SSE progress tracking,
 * and state synchronization into a single cohesive interface
 */
export function useEnhancement() {
  // Enhancement states for all prospects
  const [enhancementStates, setEnhancementStates] = useState<UnifiedEnhancementState>({});
  
  // Refs for stable references
  const sseConnectionsRef = useRef<Map<string, EventSource>>(new Map());
  const enhancementStatesRef = useRef(enhancementStates);
  const enhancementTimeoutsRef = useRef<Map<string, NodeJS.Timeout>>(new Map());
  const queryClient = useQueryClient();
  
  // Update ref whenever state changes
  useEffect(() => {
    enhancementStatesRef.current = enhancementStates;
  }, [enhancementStates]);

  // Poll queue status less frequently when SSE is active
  const [pollingInterval, setPollingInterval] = useState(1000);
  const [queueStatus, setQueueStatus] = useState<QueueStatus | null>(null);
  
  // Fetch queue status periodically
  useEffect(() => {
    const fetchQueueStatus = async () => {
      try {
        const status = await get<QueueStatus>('/api/llm/queue/status');
        setQueueStatus(status);
      } catch (error) {
        // Silently handle queue status fetch errors
      }
    };

    fetchQueueStatus();
    const intervalId = setInterval(fetchQueueStatus, pollingInterval);
    
    return () => clearInterval(intervalId);
  }, [pollingInterval]);

  // Update prospect data in cache
  const updateProspectCache = useCallback((prospectId: string, data: Record<string, unknown>) => {
    queryClient.setQueriesData({ queryKey: ['prospects'] }, (oldData: ProspectsQueryData | undefined) => {
      if (!oldData?.data) return oldData;
      return {
        ...oldData,
        data: oldData.data.map((p: Prospect) =>
          p.id === prospectId ? { ...p, ...data } : p
        )
      };
    });
  }, [queryClient]);

  // Handle SSE events
  const handleSSEEvent = useCallback((prospectId: string, event: EnhancementProgressEvent) => {
    const currentState = enhancementStatesRef.current[prospectId] || { status: 'idle', progress: {} };
    let newState: Partial<EnhancementState> = {};
    
    switch (event.event_type) {
      case 'connected':
        // SSE connection established
        break;

      case 'queue_position_update':
        newState = {
          status: 'queued',
          queuePosition: event.data?.position as number,
          estimatedTimeRemaining: event.data?.estimated_time as number
        };
        break;

      case 'processing_started':
        newState = {
          status: 'processing',
          startedAt: event.timestamp,
          queuePosition: undefined
        };
        
        // Set enhancement timeout (2 minutes max)
        const existingTimeout = enhancementTimeoutsRef.current.get(prospectId);
        if (existingTimeout) clearTimeout(existingTimeout);
        
        const newTimeout = setTimeout(() => {
          // Enhancement timeout
          setEnhancementStates(prev => ({
            ...prev,
            [prospectId]: {
              ...prev[prospectId],
              status: 'failed',
              error: 'Enhancement timed out',
              currentStep: undefined
            }
          }));
          
          // Close SSE connection
          const connection = sseConnectionsRef.current.get(prospectId);
          connection?.close();
          sseConnectionsRef.current.delete(prospectId);
          enhancementTimeoutsRef.current.delete(prospectId);
        }, 120000); // 2 minutes
        
        enhancementTimeoutsRef.current.set(prospectId, newTimeout);
        break;

      case 'values_started':
        newState = { currentStep: 'Parsing contract values...' };
        break;

      case 'values_completed':
        newState = {
          progress: {
            ...currentState.progress,
            values: {
              completed: true,
              skipped: event.data?.skipped as boolean,
              data: event.data
            }
          }
        };
        
        if (!event.data?.skipped) {
          updateProspectCache(prospectId, event.data || {});
        }
        break;

      case 'contacts_started':
        newState = { currentStep: 'Extracting contact information...' };
        break;

      case 'contacts_completed':
        newState = {
          progress: {
            ...currentState.progress,
            contacts: {
              completed: true,
              skipped: event.data?.skipped as boolean,
              data: event.data
            }
          }
        };
        
        if (!event.data?.skipped) {
          updateProspectCache(prospectId, event.data || {});
        }
        break;

      case 'naics_started':
        newState = { currentStep: 'Classifying NAICS code...' };
        break;

      case 'naics_completed':
        newState = {
          progress: {
            ...currentState.progress,
            naics: {
              completed: true,
              skipped: event.data?.skipped as boolean,
              data: event.data
            }
          }
        };
        
        if (!event.data?.skipped) {
          updateProspectCache(prospectId, event.data || {});
        }
        break;

      case 'titles_started':
        newState = { currentStep: 'Enhancing title...' };
        break;

      case 'titles_completed':
        newState = {
          currentStep: undefined,
          progress: {
            ...currentState.progress,
            titles: {
              completed: true,
              skipped: event.data?.skipped as boolean,
              data: event.data
            }
          }
        };
        
        if (!event.data?.skipped) {
          updateProspectCache(prospectId, event.data || {});
        }
        break;

      case 'completed':
        // Enhancement completed
        
        // Clear timeout
        const completionTimeout = enhancementTimeoutsRef.current.get(prospectId);
        if (completionTimeout) {
          clearTimeout(completionTimeout);
          enhancementTimeoutsRef.current.delete(prospectId);
        }
        
        // Finalize progress
        const finalProgress = { ...currentState.progress } as EnhancementProgress;
        const steps: Array<keyof EnhancementProgress> = ['values', 'contacts', 'naics', 'titles'];
        steps.forEach(step => {
          if (finalProgress[step]) {
            finalProgress[step] = { ...finalProgress[step], completed: true };
          }
        });
        
        newState = {
          status: 'completed',
          completedAt: event.timestamp,
          currentStep: undefined,
          progress: finalProgress
        };
        
        // Update cache with completion data
        if (event.data?.ollama_processed_at) {
          updateProspectCache(prospectId, {
            enhancement_status: 'idle',
            ollama_processed_at: event.data.ollama_processed_at
          });
        }
        
        // Invalidate queries to ensure fresh data
        queryClient.invalidateQueries({ queryKey: ['prospects'] });
        queryClient.invalidateQueries({ queryKey: ['ai-enrichment-status'] });
        queryClient.invalidateQueries({ queryKey: ['llm-outputs'] });
        
        // Show success toast
        if (window.showToast) {
          window.showToast({
            title: 'AI Enhancement Complete',
            message: 'Successfully enhanced prospect',
            type: 'success',
            duration: 3000
          });
        }
        
        // Close SSE connection
        const connection = sseConnectionsRef.current.get(prospectId);
        connection?.close();
        sseConnectionsRef.current.delete(prospectId);
        
        // Clean up completed enhancement after delay
        setTimeout(() => {
          setEnhancementStates(prev => {
            const updated = { ...prev };
            delete updated[prospectId];
            return updated;
          });
        }, 5000);
        break;

      case 'values_failed':
      case 'contacts_failed':
      case 'naics_failed':
      case 'titles_failed':
      case 'failed':
      case 'error':
      case 'timeout':
        const errorMsg = (event.data?.error as string) || 'Enhancement failed';
        
        // Clear timeout
        const errorTimeout = enhancementTimeoutsRef.current.get(prospectId);
        if (errorTimeout) {
          clearTimeout(errorTimeout);
          enhancementTimeoutsRef.current.delete(prospectId);
        }
        
        newState = {
          status: 'failed',
          error: errorMsg,
          currentStep: undefined
        };
        
        // Show error toast
        if (window.showToast) {
          window.showToast({
            title: 'Enhancement Failed',
            message: errorMsg,
            type: 'error',
            duration: 5000
          });
        }
        
        // Clean up after delay
        setTimeout(() => {
          setEnhancementStates(prev => {
            const updated = { ...prev };
            delete updated[prospectId];
            return updated;
          });
          
          const connection = sseConnectionsRef.current.get(prospectId);
          connection?.close();
          sseConnectionsRef.current.delete(prospectId);
        }, 5000);
        break;

      case 'keepalive':
        // Just a heartbeat
        break;
    }
    
    // Update state if there are changes
    if (Object.keys(newState).length > 0) {
      setEnhancementStates(prev => ({
        ...prev,
        [prospectId]: { ...currentState, ...newState } as EnhancementState
      }));
    }
  }, [queryClient, updateProspectCache]);

  // Create SSE connection for a prospect
  const createSSEConnection = useCallback((prospectId: string) => {
    // Don't create duplicate connections
    if (sseConnectionsRef.current.has(prospectId)) {
      // SSE connection already exists
      return;
    }

    // Creating SSE connection
    
    const eventSource = new EventSource(`/api/llm/enhancement-progress/${prospectId}`);
    sseConnectionsRef.current.set(prospectId, eventSource);

    // Reduce polling when SSE is active
    setPollingInterval(5000);

    eventSource.onopen = () => {
      // Connection established
    };

    eventSource.onmessage = (event) => {
      try {
        const sseEvent = JSON.parse(event.data);
        handleSSEEvent(prospectId, sseEvent);
      } catch (err) {
        // Silently handle SSE parse errors
      }
    };

    eventSource.onerror = () => {
      // SSE connection error
      
      // Clean up failed connection
      eventSource.close();
      sseConnectionsRef.current.delete(prospectId);
      
      // Reset polling interval if no active connections
      if (sseConnectionsRef.current.size === 0) {
        setPollingInterval(1000);
      }
      
      // Show error if enhancement was active
      const state = enhancementStatesRef.current[prospectId];
      if (state && ['queued', 'processing'].includes(state.status)) {
        if (window.showToast) {
          window.showToast({
            title: 'Connection Lost',
            message: 'Enhancement connection lost. Please refresh to see latest status.',
            type: 'error',
            duration: 5000
          });
        }
      }
    };
  }, [handleSSEEvent]);

  // Queue an enhancement
  const queueEnhancement = useCallback(async (request: EnhancementRequest) => {
    const { prospect_id } = request;
    
    // Check if already queued or processing
    const existingState = enhancementStatesRef.current[prospect_id];
    if (existingState && ['queued', 'processing'].includes(existingState.status)) {
      if (window.showToast) {
        window.showToast({
          title: 'Already Queued',
          message: 'Prospect is already being enhanced',
          type: 'info',
          duration: 2000
        });
      }
      return existingState.queueItemId;
    }
    
    try {
      // Add to backend queue
      const response = await post<{ queue_item_id: string; position?: number }>('/api/llm/enhance-single', {
        prospect_id: request.prospect_id,
        enhancement_type: 'all',
        force_redo: request.force_redo,
        user_id: request.user_id
      });

      const queueItemId = response.queue_item_id;

      // Update local state
      setEnhancementStates(prev => ({
        ...prev,
        [prospect_id]: {
          queueItemId,
          status: 'queued',
          queuePosition: response.position || (queueStatus?.queue_size || 0) + 1,
          progress: {}
        }
      }));

      // Create SSE connection immediately
      createSSEConnection(prospect_id);

      // Show queued toast
      if (window.showToast) {
        window.showToast({
          title: 'Enhancement Queued',
          message: 'Prospect enhancement request added to priority queue',
          type: 'info',
          duration: 2000
        });
      }

      return queueItemId;
    } catch (error: unknown) {
      const apiError = error as ApiError;
      const errorMessage = apiError.status === 409 
        ? `Enhancement blocked: ${apiError.message}` 
        : `Failed to queue enhancement: ${apiError.message || 'Unknown error'}`;

      setEnhancementStates(prev => ({
        ...prev,
        [prospect_id]: {
          ...prev[prospect_id],
          status: 'failed',
          error: errorMessage
        }
      }));

      // Show error toast
      if (window.showToast) {
        window.showToast({
          title: 'Enhancement Failed',
          message: errorMessage,
          type: 'error',
          duration: 5000
        });
      }

      throw error;
    }
  }, [queueStatus, createSSEConnection]);

  // Sync with backend queue status
  useEffect(() => {
    if (!queueStatus) return;

    const pendingItems = Array.isArray(queueStatus?.pending_items) ? queueStatus.pending_items : [];
    
    setEnhancementStates(prev => {
      const updated = { ...prev };
      
      // Update positions for items in queue
      pendingItems.forEach((item, index) => {
        if (item.type === 'individual' && item.prospect_id) {
          const prospectId = item.prospect_id.toString();
          
          // If item is being processed
          if (queueStatus.current_item === item.id) {
            updated[prospectId] = {
              ...updated[prospectId],
              queueItemId: item.id,
              status: 'processing',
              queuePosition: undefined
            };
          } else {
            // Update queue position
            updated[prospectId] = {
              ...updated[prospectId],
              queueItemId: item.id,
              status: 'queued',
              queuePosition: index + 1
            };
          }
        }
      });
      
      return updated;
    });
  }, [queueStatus, createSSEConnection]);

  // Get enhancement state for a specific prospect
  const getEnhancementState = useCallback((prospectId: string) => {
    return enhancementStatesRef.current[prospectId] || null;
  }, []);

  // Cancel an enhancement
  const cancelEnhancement = useCallback(async (prospectId: string) => {
    const state = enhancementStatesRef.current[prospectId];
    if (!state || state.status !== 'queued') {
      return false;
    }

    try {
      await del(`/api/llm/enhancement-queue/${state.queueItemId}`);
      
      // Remove from local state
      setEnhancementStates(prev => {
        const updated = { ...prev };
        delete updated[prospectId];
        return updated;
      });
      
      // Disconnect SSE if exists
      const connection = sseConnectionsRef.current.get(prospectId);
      connection?.close();
      sseConnectionsRef.current.delete(prospectId);
      
      // Clear timeout if exists
      const cancelTimeout = enhancementTimeoutsRef.current.get(prospectId);
      if (cancelTimeout) {
        clearTimeout(cancelTimeout);
        enhancementTimeoutsRef.current.delete(prospectId);
      }
      
      return true;
    } catch (error) {
      // Failed to cancel enhancement
      return false;
    }
  }, []);

  // Queue worker controls
  const startQueueWorker = useCallback(async () => {
    try {
      await post('/api/llm/queue/start-worker');
      queryClient.invalidateQueries({ queryKey: ['enhancement-queue-status'] });
      return true;
    } catch (error: unknown) {
      const apiError = error as ApiError;
      if (window.showToast) {
        window.showToast({
          title: 'Failed to start worker',
          message: apiError.message || 'Unknown error',
          type: 'error',
          duration: 3000
        });
      }
      return false;
    }
  }, [queryClient]);

  const stopQueueWorker = useCallback(async () => {
    try {
      await post('/api/llm/queue/stop-worker');
      queryClient.invalidateQueries({ queryKey: ['enhancement-queue-status'] });
      return true;
    } catch (error: unknown) {
      const apiError = error as ApiError;
      if (window.showToast) {
        window.showToast({
          title: 'Failed to stop worker',
          message: apiError.message || 'Unknown error',
          type: 'error',
          duration: 3000
        });
      }
      return false;
    }
  }, [queryClient]);

  // Clean up on unmount
  useEffect(() => {
    return () => {
      // Close all SSE connections
      sseConnectionsRef.current.forEach(connection => connection.close());
      sseConnectionsRef.current.clear();
      
      // Clear all timeouts
      enhancementTimeoutsRef.current.forEach(timeout => clearTimeout(timeout));
      enhancementTimeoutsRef.current.clear();
    };
  }, []);

  return {
    // Enhancement operations
    queueEnhancement,
    getEnhancementState,
    cancelEnhancement,
    
    // Queue status
    queueStatus,
    queueLength: Object.keys(enhancementStates).filter(
      id => enhancementStates[id].status === 'queued'
    ).length,
    isProcessing: Object.values(enhancementStates).some(
      state => state.status === 'processing'
    ),
    
    // Worker controls
    startQueueWorker,
    stopQueueWorker,
    
    // All enhancement states (for debugging/monitoring)
    enhancementStates
  };
}