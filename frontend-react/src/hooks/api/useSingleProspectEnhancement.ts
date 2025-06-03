import { useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';

interface EnhanceSingleProspectRequest {
  prospect_id: string;
}

interface EnhanceSingleProspectResponse {
  status: string;
  message: string;
  processed: boolean;
}

export function useSingleProspectEnhancement() {
  const queryClient = useQueryClient();
  
  return useMutation<EnhanceSingleProspectResponse, Error, EnhanceSingleProspectRequest>({
    mutationFn: async ({ prospect_id }) => {
      const response = await axios.post('/api/llm/enhance-single', {
        prospect_id,
        enhancement_type: 'all'
      });
      return response.data;
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