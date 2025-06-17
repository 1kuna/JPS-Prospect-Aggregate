import { useState, useCallback, useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { useEnhancementQueueStatus } from './useEnhancementQueue';

interface QueuedEnhancement {
  prospect_id: string;
  force_redo?: boolean;
  user_id?: number;
  status: 'queued' | 'processing' | 'completed' | 'failed';
  position?: number;
  error?: string;
  queue_item_id?: string;
}

interface EnhancementQueue {
  [prospect_id: string]: QueuedEnhancement;
}

interface EnhanceSingleProspectRequest {
  prospect_id: string;
  force_redo?: boolean;
  user_id?: number;
}

export function useProspectEnhancementQueue() {
  const [queue, setQueue] = useState<EnhancementQueue>({});
  const [isProcessing, setIsProcessing] = useState(false);
  const queryClient = useQueryClient();
  
  // Get queue status from backend
  const { data: queueStatus } = useEnhancementQueueStatus(2000);

  const addToQueue = useCallback(async (request: EnhanceSingleProspectRequest) => {
    const { prospect_id } = request;
    
    try {
      // Add to backend queue
      const response = await axios.post('/api/llm/enhance-single', {
        prospect_id: request.prospect_id,
        enhancement_type: 'all',
        force_redo: request.force_redo,
        user_id: request.user_id
      });

      // Add to local state for immediate UI feedback
      setQueue(prev => ({
        ...prev,
        [prospect_id]: {
          ...request,
          status: 'queued',
          queue_item_id: response.data.queue_item_id,
          position: (queueStatus?.queue_size || 0) + 1
        }
      }));

      // Show queued toast
      if (window.showToast) {
        window.showToast({
          title: 'Enhancement Queued',
          message: `Prospect enhancement request added to priority queue`,
          type: 'info',
          duration: 2000
        });
      }

      return response.data.queue_item_id;
    } catch (error: unknown) {
      // Handle error
      const errorResponse = error as { response?: { status: number; data: { error: string } }; message?: string };
      const errorMessage = errorResponse.response?.status === 409 
        ? `Enhancement blocked: ${errorResponse.response.data.error}` 
        : `Failed to queue enhancement: ${errorResponse.message || 'Unknown error'}`;

      setQueue(prev => ({
        ...prev,
        [prospect_id]: {
          ...request,
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
  }, [queueStatus]);

  // Monitor backend queue and update local state
  useEffect(() => {
    if (!queueStatus) return;

    // Update local queue based on backend status
    setQueue(prev => {
      const newQueue = { ...prev };

      // Check each local queue item against backend status
      Object.entries(newQueue).forEach(([prospectId, localItem]) => {
        if (!localItem.queue_item_id) return;

        // Find corresponding backend item
        const backendItem = queueStatus.pending_items.find(item => 
          item.id === localItem.queue_item_id
        );

        if (backendItem) {
          // Update status and position from backend
          newQueue[prospectId] = {
            ...localItem,
            status: backendItem.status as 'queued' | 'processing' | 'completed' | 'failed',
            position: queueStatus.pending_items.indexOf(backendItem) + 1
          };
        } else {
          // Check if completed
          const completedItem = queueStatus.recent_completed.find(item => 
            item.id === localItem.queue_item_id
          );

          if (completedItem) {
            if (completedItem.status === 'completed') {
              // Mark as completed and show success
              newQueue[prospectId] = {
                ...localItem,
                status: 'completed'
              };

              // Show success toast
              if (window.showToast) {
                window.showToast({
                  title: 'AI Enhancement Complete',
                  message: `Successfully enhanced prospect`,
                  type: 'success',
                  duration: 3000
                });
              }

              // Invalidate queries to refresh data
              queryClient.invalidateQueries({ queryKey: ['prospects'] });
              queryClient.invalidateQueries({ queryKey: ['ai-enrichment-status'] });
              queryClient.invalidateQueries({ queryKey: ['llm-outputs'] });

              // Remove from queue after delay
              setTimeout(() => {
                setQueue(prev => {
                  const updatedQueue = { ...prev };
                  delete updatedQueue[prospectId];
                  return updatedQueue;
                });
              }, 2000);
            } else if (completedItem.status === 'failed') {
              // Mark as failed and show error
              newQueue[prospectId] = {
                ...localItem,
                status: 'failed',
                error: completedItem.error_message || 'Enhancement failed'
              };

              // Show error toast
              if (window.showToast) {
                window.showToast({
                  title: 'Enhancement Failed',
                  message: completedItem.error_message || 'Enhancement failed',
                  type: 'error',
                  duration: 5000
                });
              }

              // Remove from queue after delay
              setTimeout(() => {
                setQueue(prev => {
                  const updatedQueue = { ...prev };
                  delete updatedQueue[prospectId];
                  return updatedQueue;
                });
              }, 5000);
            }
          }
        }
      });

      return newQueue;
    });

    // Update processing status
    setIsProcessing(queueStatus.current_item !== null);
  }, [queueStatus, queryClient]);

  const getProspectStatus = useCallback((prospect_id: string) => {
    return queue[prospect_id] || null;
  }, [queue]);

  const removeFromQueue = useCallback((prospect_id: string) => {
    setQueue(prev => {
      const newQueue = { ...prev };
      delete newQueue[prospect_id];
      return newQueue;
    });
  }, []);

  return {
    addToQueue,
    getProspectStatus,
    removeFromQueue,
    queueLength: Object.keys(queue).length,
    isProcessing
  };
}