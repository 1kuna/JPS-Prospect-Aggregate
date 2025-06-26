import { useState, useCallback, useEffect, useRef } from 'react';
import axios from 'axios';
import { EnhancementState } from './useEnhancementSSE';
import { useEnhancementQueueStatus } from './useEnhancementQueue';
import { useQueryClient } from '@tanstack/react-query';

interface EnhancementRequest {
  prospect_id: string;
  force_redo?: boolean;
  user_id?: number;
}

interface UnifiedEnhancementState {
  [prospect_id: string]: {
    queueItemId?: string;
    status: 'idle' | 'queued' | 'processing' | 'completed' | 'failed';
    queuePosition?: number;
    estimatedTimeRemaining?: number;
    currentStep?: string;
    progress?: {
      values?: { completed: boolean; skipped?: boolean; data?: any };
      contacts?: { completed: boolean; skipped?: boolean; data?: any };
      naics?: { completed: boolean; skipped?: boolean; data?: any };
      titles?: { completed: boolean; skipped?: boolean; data?: any };
    };
    error?: string;
    startedAt?: string;
    completedAt?: string;
  };
}

export function useUnifiedEnhancement() {
  const [enhancementStates, setEnhancementStates] = useState<UnifiedEnhancementState>({});
  const [activeSSEConnection, setActiveSSEConnection] = useState<string | null>(null);
  
  // Track SSE connection states
  const sseConnectionsRef = useRef<Map<string, EventSource>>(new Map());
  const enhancementStatesRef = useRef(enhancementStates);
  const queryClient = useQueryClient();
  
  // Update ref whenever state changes
  useEffect(() => {
    enhancementStatesRef.current = enhancementStates;
  }, [enhancementStates]);
  
  // Get backend queue status (reduced polling when SSE is active)
  const pollingInterval = activeSSEConnection ? 5000 : 1000; // 5s when SSE active, 1s otherwise
  const { data: queueStatus } = useEnhancementQueueStatus(pollingInterval);

  // Handle SSE state changes
  const handleSSEStateChange = useCallback((prospectId: string, sseState: EnhancementState) => {
    setEnhancementStates(prev => ({
      ...prev,
      [prospectId]: {
        ...prev[prospectId],
        status: sseState.status,
        currentStep: sseState.currentStep,
        progress: sseState.progress,
        error: sseState.error,
        queuePosition: sseState.queuePosition,
        estimatedTimeRemaining: sseState.estimatedTimeRemaining,
        startedAt: sseState.startedAt,
        completedAt: sseState.completedAt
      }
    }));
  }, []);

  // Create SSE connection for a prospect
  const createSSEConnection = useCallback((prospectId: string) => {
    // Don't create duplicate connections
    if (sseConnectionsRef.current.has(prospectId)) {
      console.log(`SSE connection already exists for prospect ${prospectId}`);
      return;
    }

    console.log(`Creating SSE connection for prospect ${prospectId}`);
    
    // Create direct EventSource connection
    const eventSource = new EventSource(`/api/llm/enhancement-progress/${prospectId}`);
    sseConnectionsRef.current.set(prospectId, eventSource);

    eventSource.onopen = () => {
      console.log(`SSE connection established for prospect ${prospectId}`);
    };

    eventSource.onmessage = (event) => {
      try {
        const sseEvent = JSON.parse(event.data);
        console.log(`SSE event received for ${prospectId}:`, sseEvent.event_type, sseEvent.data);
        
        const currentState = enhancementStatesRef.current[prospectId] || { status: 'idle', progress: {} };
        let newState: Partial<EnhancementState> = {};
        
        switch (sseEvent.event_type) {
          case 'connected':
            console.log(`SSE connected for ${prospectId}`);
            break;

          case 'queue_position_update':
            newState = {
              status: 'queued',
              queuePosition: sseEvent.data?.position as number,
              estimatedTimeRemaining: sseEvent.data?.estimated_time as number
            };
            break;

          case 'processing_started':
            newState = {
              status: 'processing',
              startedAt: sseEvent.timestamp,
              queuePosition: undefined
            };
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
                  skipped: sseEvent.data?.skipped as boolean,
                  data: sseEvent.data
                }
              }
            };
            
            // Update query cache if not skipped - use wildcard to update all prospect queries
            if (!sseEvent.data?.skipped) {
              console.log(`Updating prospect cache for ${prospectId} with values data:`, sseEvent.data);
              queryClient.setQueriesData({ queryKey: ['prospects'] }, (oldData: any) => {
                if (!oldData?.data) return oldData;
                const updatedData = {
                  ...oldData,
                  data: oldData.data.map((p: any) =>
                    p.id === prospectId ? { ...p, ...sseEvent.data } : p
                  )
                };
                console.log(`Updated prospect cache for ${prospectId}`, updatedData);
                return updatedData;
              });
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
                  skipped: sseEvent.data?.skipped as boolean,
                  data: sseEvent.data
                }
              }
            };
            
            if (!sseEvent.data?.skipped) {
              console.log(`Updating prospect cache for ${prospectId} with contacts data:`, sseEvent.data);
              queryClient.setQueriesData({ queryKey: ['prospects'] }, (oldData: any) => {
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
            newState = { currentStep: 'Classifying NAICS code...' };
            break;

          case 'naics_completed':
            newState = {
              progress: {
                ...currentState.progress,
                naics: {
                  completed: true,
                  skipped: sseEvent.data?.skipped as boolean,
                  data: sseEvent.data
                }
              }
            };
            
            if (!sseEvent.data?.skipped) {
              console.log(`Updating prospect cache for ${prospectId} with naics data:`, sseEvent.data);
              queryClient.setQueriesData({ queryKey: ['prospects'] }, (oldData: any) => {
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
            newState = { currentStep: 'Enhancing title...' };
            break;

          case 'titles_completed':
            newState = {
              progress: {
                ...currentState.progress,
                titles: {
                  completed: true,
                  skipped: sseEvent.data?.skipped as boolean,
                  data: sseEvent.data
                }
              }
            };
            
            if (!sseEvent.data?.skipped) {
              console.log(`Updating prospect cache for ${prospectId} with titles data:`, sseEvent.data);
              queryClient.setQueriesData({ queryKey: ['prospects'] }, (oldData: any) => {
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
            console.log(`*** COMPLETION EVENT RECEIVED for ${prospectId} ***`, sseEvent.data);
            newState = {
              status: 'completed',
              completedAt: sseEvent.timestamp,
              currentStep: undefined
            };
            
            console.log(`Setting enhancement state to completed for ${prospectId}`, newState);
            
            // Final cache update - invalidate all prospect queries to ensure fresh data
            console.log(`Invalidating all prospect queries for completed enhancement ${prospectId}`);
            queryClient.invalidateQueries({ queryKey: ['prospects'] });
            queryClient.invalidateQueries({ queryKey: ['ai-enrichment-status'] });
            queryClient.invalidateQueries({ queryKey: ['llm-outputs'] });
            
            console.log(`Cache invalidated for completed enhancement ${prospectId}`);
            
            // Show success toast
            if (window.showToast) {
              window.showToast({
                title: 'AI Enhancement Complete',
                message: 'Successfully enhanced prospect',
                type: 'success',
                duration: 3000
              });
            }
            
            // Clean up completed enhancement immediately (no delay)
            console.log(`Cleaning up SSE connection for completed enhancement ${prospectId}`);
            setEnhancementStates(prev => {
              const updated = { ...prev };
              delete updated[prospectId];
              console.log(`Removed ${prospectId} from enhancement states`);
              return updated;
            });
            
            // Disconnect SSE immediately
            eventSource.close();
            sseConnectionsRef.current.delete(prospectId);
            console.log(`SSE connection closed and removed for ${prospectId}`);
            break;

          case 'failed':
          case 'error':
            const errorMsg = sseEvent.data?.error as string || 'Enhancement failed';
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
            
            // Clean up failed enhancement after delay
            setTimeout(() => {
              setEnhancementStates(prev => {
                const updated = { ...prev };
                delete updated[prospectId];
                return updated;
              });
              
              // Disconnect SSE
              eventSource.close();
              sseConnectionsRef.current.delete(prospectId);
            }, 5000);
            break;

          case 'keepalive':
            // Just a heartbeat, no action needed
            break;
        }
        
        // Update state with new values
        if (Object.keys(newState).length > 0) {
          console.log(`Updating enhancement state for ${prospectId}:`, newState);
          handleSSEStateChange(prospectId, { ...currentState, ...newState } as EnhancementState);
        } else {
          console.log(`No state update needed for SSE event ${sseEvent.event_type} on ${prospectId}`);
        }
      } catch (err) {
        console.error('Failed to parse SSE event:', err);
      }
    };

    eventSource.onerror = (err) => {
      console.error(`SSE connection error for prospect ${prospectId}:`, err);
      
      // Clean up failed connection
      eventSource.close();
      sseConnectionsRef.current.delete(prospectId);
      
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
  }, [handleSSEStateChange, queryClient]);

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
      const response = await axios.post('/api/llm/enhance-single', {
        prospect_id: request.prospect_id,
        enhancement_type: 'all',
        force_redo: request.force_redo,
        user_id: request.user_id
      });

      const queueItemId = response.data.queue_item_id;

      // Update local state
      setEnhancementStates(prev => ({
        ...prev,
        [prospect_id]: {
          queueItemId,
          status: 'queued',
          queuePosition: response.data.position || (queueStatus?.queue_size || 0) + 1
        }
      }));

      // Create SSE connection immediately
      createSSEConnection(prospect_id);
      setActiveSSEConnection(prospect_id);

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
      const axiosError = error as { response?: { status: number; data: { error: string } }; message?: string };
      const errorMessage = axiosError.response?.status === 409 
        ? `Enhancement blocked: ${axiosError.response.data.error}` 
        : `Failed to queue enhancement: ${axiosError.message || 'Unknown error'}`;

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

    // Update queue positions for queued items
    const pendingItems = Array.isArray(queueStatus?.pending_items) ? queueStatus.pending_items : [];
    
    setEnhancementStates(prev => {
      const updated = { ...prev };
      
      // Update positions for items in queue
      pendingItems.forEach((item, index) => {
        if (item.type === 'individual' && item.prospect_id) {
          const prospectId = item.prospect_id.toString();
          
          // If item is being processed
          if (queueStatus.current_item === item.id) {
            // Create SSE connection if not exists
            if (!sseConnectionsRef.current.has(prospectId)) {
              createSSEConnection(prospectId);
              setActiveSSEConnection(prospectId);
            }
            
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

  // Clean up SSE connections on unmount
  useEffect(() => {
    return () => {
      sseConnectionsRef.current.forEach(connection => connection.close());
      sseConnectionsRef.current.clear();
    };
  }, []);

  // Get enhancement state for a specific prospect
  const getEnhancementState = useCallback((prospectId: string) => {
    return enhancementStatesRef.current[prospectId] || null;
  }, []);

  // Cancel an enhancement (to be implemented)
  const cancelEnhancement = useCallback(async (prospectId: string) => {
    const state = enhancementStatesRef.current[prospectId];
    if (!state || state.status !== 'queued') {
      return false;
    }

    try {
      await axios.delete(`/api/llm/enhancement-queue/${state.queueItemId}`);
      
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
      
      return true;
    } catch (error) {
      console.error('Failed to cancel enhancement:', error);
      return false;
    }
  }, []);

  return {
    queueEnhancement,
    getEnhancementState,
    cancelEnhancement,
    queueLength: Object.keys(enhancementStates).filter(
      id => enhancementStates[id].status === 'queued'
    ).length,
    isProcessing: Object.values(enhancementStates).some(
      state => state.status === 'processing'
    )
  };
}