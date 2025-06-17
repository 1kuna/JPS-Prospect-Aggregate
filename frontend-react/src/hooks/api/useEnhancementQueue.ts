import { useQuery, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';

interface QueueItem {
  id: string;
  type: 'individual' | 'bulk';
  priority: number;
  prospect_id?: number;
  prospect_count: number;
  enhancement_type: string;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled';
  progress: {
    processed: number;
    total: number;
    enhancements?: string[];
  };
  error_message?: string;
}

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

export function useEnhancementQueueStatus(refetchInterval: number = 1000) {
  return useQuery<QueueStatus>({
    queryKey: ['enhancement-queue-status'],
    queryFn: async () => {
      const response = await axios.get('/api/llm/queue/status');
      return response.data;
    },
    refetchInterval,
    staleTime: 500,
    refetchOnWindowFocus: true
  });
}

export function useQueueItemStatus(itemId: string | undefined, enabled: boolean = true) {
  return useQuery<QueueItem>({
    queryKey: ['queue-item-status', itemId],
    queryFn: async () => {
      if (!itemId) throw new Error('Item ID is required');
      const response = await axios.get(`/api/llm/queue/item/${itemId}`);
      return response.data;
    },
    enabled: enabled && !!itemId,
    refetchInterval: 1000,
    staleTime: 500
  });
}

export function useCancelQueueItem() {
  const queryClient = useQueryClient();
  
  return async (itemId: string) => {
    try {
      const response = await axios.post(`/api/llm/queue/item/${itemId}/cancel`);
      
      // Invalidate queue status to refresh
      queryClient.invalidateQueries({ queryKey: ['enhancement-queue-status'] });
      queryClient.invalidateQueries({ queryKey: ['queue-item-status', itemId] });
      
      return response.data;
    } catch (error: unknown) {
      const errorMessage = error instanceof Error && 'response' in error 
        ? (error as { response?: { data?: { error?: string } } }).response?.data?.error 
        : 'Failed to cancel queue item';
      throw new Error(errorMessage || 'Failed to cancel queue item');
    }
  };
}

export function useStartQueueWorker() {
  const queryClient = useQueryClient();
  
  return async () => {
    try {
      const response = await axios.post('/api/llm/queue/start-worker');
      
      // Invalidate queue status to refresh
      queryClient.invalidateQueries({ queryKey: ['enhancement-queue-status'] });
      
      return response.data;
    } catch (error: unknown) {
      const errorMessage = error instanceof Error && 'response' in error 
        ? (error as { response?: { data?: { error?: string } } }).response?.data?.error 
        : 'Failed to start queue worker';
      throw new Error(errorMessage || 'Failed to start queue worker');
    }
  };
}

export function useStopQueueWorker() {
  const queryClient = useQueryClient();
  
  return async () => {
    try {
      const response = await axios.post('/api/llm/queue/stop-worker');
      
      // Invalidate queue status to refresh
      queryClient.invalidateQueries({ queryKey: ['enhancement-queue-status'] });
      
      return response.data;
    } catch (error: unknown) {
      const errorMessage = error instanceof Error && 'response' in error 
        ? (error as { response?: { data?: { error?: string } } }).response?.data?.error 
        : 'Failed to stop queue worker';
      throw new Error(errorMessage || 'Failed to stop queue worker');
    }
  };
}