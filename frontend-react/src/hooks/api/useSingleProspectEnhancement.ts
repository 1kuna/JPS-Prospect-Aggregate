import { useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';

interface EnhanceSingleProspectRequest {
  prospect_id: string;
  force_redo?: boolean;
  user_id?: number;
}

interface EnhanceSingleProspectResponse {
  status: string;
  message: string;
  processed?: boolean;
  enhancements?: string[];
  queue_item_id?: string;
  prospect_id?: string;
  priority?: string;
}

interface EnhancementBlockedResponse {
  error: string;
  status: 'blocked';
  enhancement_status: 'in_progress';
  enhancement_user_id: number;
}

export function useSingleProspectEnhancement() {
  const queryClient = useQueryClient();
  
  return useMutation<EnhanceSingleProspectResponse, Error, EnhanceSingleProspectRequest>({
    mutationFn: async ({ prospect_id, force_redo = false, user_id = 1 }) => {
      try {
        const response = await axios.post('/api/llm/enhance-single', {
          prospect_id,
          enhancement_type: 'all',
          force_redo,
          user_id
        });
        return response.data;
      } catch (error: any) {
        // Handle enhancement blocked response (409 status)
        if (error.response?.status === 409) {
          const blockedData: EnhancementBlockedResponse = error.response.data;
          throw new Error(`Enhancement blocked: ${blockedData.error}`);
        }
        throw error;
      }
    },
    onSuccess: (_data, variables) => {
      // Invalidate queries to refresh data
      queryClient.invalidateQueries({ queryKey: ['prospects'] });
      queryClient.invalidateQueries({ queryKey: ['ai-enrichment-status'] });
      queryClient.invalidateQueries({ queryKey: ['llm-outputs'] });
      // Invalidate the specific prospect if there's a query for it
      queryClient.invalidateQueries({ queryKey: ['prospect', variables.prospect_id] });
    },
  });
}