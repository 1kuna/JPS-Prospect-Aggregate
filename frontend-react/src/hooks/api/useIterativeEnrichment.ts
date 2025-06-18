import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';

export type EnhancementType = 'all' | 'values' | 'contacts' | 'naics' | 'titles';

export interface IterativeProgress {
  status: 'idle' | 'processing' | 'completed' | 'stopped' | 'stopping' | 'error';
  current_type: EnhancementType | null;
  processed: number;
  total: number;
  percentage: number;
  current_prospect: {
    id: number;
    title: string;
  } | null;
  started_at: string | null;
  errors: Array<{
    prospect_id: number;
    error?: string;
    timestamp: string;
  }>;
  error_message?: string;
}

export interface StartEnhancementRequest {
  enhancement_type: EnhancementType;
  skip_existing?: boolean;
}

export interface OperationResult {
  status: string;
  message: string;
  processed_count?: number;
  total_to_process?: number;
}

// Start iterative enhancement
export function useStartIterativeEnhancement() {
  const queryClient = useQueryClient();
  
  return useMutation<OperationResult, Error, StartEnhancementRequest>({
    mutationFn: async (data) => {
      const response = await axios.post('/api/llm/iterative/start', data);
      return response.data;
    },
    onSuccess: () => {
      // Invalidate progress query to trigger refresh
      queryClient.invalidateQueries({ queryKey: ['iterative-progress'] });
      queryClient.invalidateQueries({ queryKey: ['ai-enrichment-status'] });
    },
  });
}

// Stop iterative enhancement
export function useStopIterativeEnhancement() {
  const queryClient = useQueryClient();
  
  return useMutation<OperationResult, Error>({
    mutationFn: async () => {
      const response = await axios.post('/api/llm/iterative/stop');
      return response.data;
    },
    onSuccess: () => {
      // Invalidate progress query
      queryClient.invalidateQueries({ queryKey: ['iterative-progress'] });
      queryClient.invalidateQueries({ queryKey: ['ai-enrichment-status'] });
      queryClient.invalidateQueries({ queryKey: ['ai-enrichment-logs'] });
    },
  });
}

// Get current progress
export function useIterativeProgress(enabled = true) {
  return useQuery<IterativeProgress>({
    queryKey: ['iterative-progress'],
    queryFn: async () => {
      const response = await axios.get('/api/llm/iterative/progress');
      return response.data;
    },
    refetchInterval: (query) => {
      const data = query.state.data;
      // Poll more frequently when processing
      if (data?.status === 'processing') {
        return 1000; // 1 second when processing
      }
      return 5000; // 5 seconds when idle
    },
    enabled,
  });
}