import { useQuery, useQueryClient } from '@tanstack/react-query';
import { get, post, ApiError } from '@/utils/apiUtils';

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
      return await get<QueueStatus>('/api/llm/queue/status');
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
      return await get<QueueItem>(`/api/llm/queue/item/${itemId}`);
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
      const response = await post(`/api/llm/queue/item/${itemId}/cancel`);
      
      // Invalidate queue status to refresh
      queryClient.invalidateQueries({ queryKey: ['enhancement-queue-status'] });
      queryClient.invalidateQueries({ queryKey: ['queue-item-status', itemId] });
      
      return response;
    } catch (error: unknown) {
      const apiError = error as ApiError;
      throw new Error(apiError.message || 'Failed to cancel queue item');
    }
  };
}

export function useStartQueueWorker() {
  const queryClient = useQueryClient();
  
  return async () => {
    try {
      const response = await post('/api/llm/queue/start-worker');
      
      // Invalidate queue status to refresh
      queryClient.invalidateQueries({ queryKey: ['enhancement-queue-status'] });
      
      return response;
    } catch (error: unknown) {
      const apiError = error as ApiError;
      throw new Error(apiError.message || 'Failed to start queue worker');
    }
  };
}

export function useStopQueueWorker() {
  const queryClient = useQueryClient();
  
  return async () => {
    try {
      const response = await post('/api/llm/queue/stop-worker');
      
      // Invalidate queue status to refresh
      queryClient.invalidateQueries({ queryKey: ['enhancement-queue-status'] });
      
      return response;
    } catch (error: unknown) {
      const apiError = error as ApiError;
      throw new Error(apiError.message || 'Failed to stop queue worker');
    }
  };
}