import { useState, useCallback, useEffect, useRef } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import axios from 'axios';

interface QueuedEnhancement {
  prospect_id: string;
  force_redo?: boolean;
  user_id?: number;
  status: 'queued' | 'processing' | 'completed' | 'failed';
  position?: number;
  error?: string;
}

interface EnhancementQueue {
  [prospect_id: string]: QueuedEnhancement;
}

interface EnhanceSingleProspectRequest {
  prospect_id: string;
  force_redo?: boolean;
  user_id?: number;
}

interface EnhanceSingleProspectResponse {
  status: string;
  message: string;
  processed: boolean;
  enhancements: string[];
}

export function useProspectEnhancementQueue() {
  const [queue, setQueue] = useState<EnhancementQueue>({});
  const [isProcessing, setIsProcessing] = useState(false);
  const queryClient = useQueryClient();
  const processingRef = useRef(false);

  const addToQueue = useCallback((request: EnhanceSingleProspectRequest) => {
    const { prospect_id } = request;
    
    setQueue(prev => {
      const newQueue = { ...prev };
      
      // Add to queue with queued status
      newQueue[prospect_id] = {
        ...request,
        status: 'queued',
        position: Object.values(newQueue).filter(item => item.status === 'queued').length + 1
      };
      
      return newQueue;
    });
  }, []);

  // Process queue when items are added
  useEffect(() => {
    const processNext = async () => {
      if (processingRef.current) return;
      
      const queuedItems = Object.entries(queue).filter(([_, item]) => item.status === 'queued');
      if (queuedItems.length === 0) return;

      processingRef.current = true;
      setIsProcessing(true);

      const [prospectId, queuedItem] = queuedItems[0];

      try {
        // Update status to processing
        setQueue(prev => ({
          ...prev,
          [prospectId]: { ...prev[prospectId], status: 'processing' }
        }));

        // Make the API call
        const response = await axios.post('/api/llm/enhance-single', {
          prospect_id: queuedItem.prospect_id,
          enhancement_type: 'all',
          force_redo: queuedItem.force_redo,
          user_id: queuedItem.user_id
        });

        // Mark as completed
        setQueue(prev => ({
          ...prev,
          [prospectId]: { ...prev[prospectId], status: 'completed' }
        }));

        // Show success toast
        if (window.showToast) {
          const enhancements = response.data.enhancements || [];
          if (enhancements.length > 0) {
            const enhancementTypes = enhancements.map((e: string) => {
              switch(e) {
                case 'values': return 'Value Parsing';
                case 'contacts': return 'Contact Extraction';
                case 'naics': return 'NAICS Classification';
                case 'titles': return 'Title Enhancement';
                default: return e;
              }
            });
            
            window.showToast({
              title: 'AI Enhancement Complete',
              message: `Enhanced prospect with: ${enhancementTypes.join(', ')}`,
              type: 'success',
              duration: 3000
            });
          } else {
            window.showToast({
              title: 'Enhancement Complete',
              message: 'Prospect was already fully enhanced',
              type: 'info',
              duration: 2000
            });
          }
        }

        // Invalidate queries to refresh data
        queryClient.invalidateQueries({ queryKey: ['prospects'] });
        queryClient.invalidateQueries({ queryKey: ['ai-enrichment-status'] });
        queryClient.invalidateQueries({ queryKey: ['llm-outputs'] });

        // Remove from queue after a delay to show success
        setTimeout(() => {
          setQueue(prev => {
            const newQueue = { ...prev };
            delete newQueue[prospectId];
            return newQueue;
          });
        }, 2000);

      } catch (error: any) {
        // Mark as failed
        const errorMessage = error.response?.status === 409 
          ? `Enhancement blocked: ${error.response.data.error}` 
          : `Failed to enhance prospect: ${error.message}`;

        setQueue(prev => ({
          ...prev,
          [prospectId]: { 
            ...prev[prospectId], 
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

        // Remove from queue after showing error
        setTimeout(() => {
          setQueue(prev => {
            const newQueue = { ...prev };
            delete newQueue[prospectId];
            return newQueue;
          });
        }, 5000);
      } finally {
        processingRef.current = false;
        setIsProcessing(false);
        
        // Update queue positions for remaining items
        setQueue(prev => {
          const newQueue = { ...prev };
          const remaining = Object.entries(newQueue)
            .filter(([_, item]) => item.status === 'queued')
            .sort((a, b) => (a[1].position || 0) - (b[1].position || 0));

          remaining.forEach(([id, item], index) => {
            newQueue[id] = { ...item, position: index + 1 };
          });

          return newQueue;
        });
      }
    };

    processNext();
  }, [queue, queryClient]);

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