import { useQuery } from '@tanstack/react-query';
import axios from 'axios';

export interface LLMOutput {
  id: number;
  timestamp: string;
  prospect_id: string;
  prospect_title: string | null;
  enhancement_type: 'values' | 'contacts' | 'naics' | 'titles';
  prompt: string;
  response: string;
  parsed_result: any;
  success: boolean;
  error_message: string | null;
  processing_time: number | null;
}

interface LLMOutputsParams {
  limit?: number;
  enhancement_type?: 'all' | 'values' | 'contacts' | 'naics' | 'titles';
}

export function useLLMOutputs(params: LLMOutputsParams = {}) {
  const { limit = 50, enhancement_type = 'all' } = params;
  
  return useQuery<LLMOutput[]>({
    queryKey: ['llm-outputs', limit, enhancement_type],
    queryFn: async () => {
      const response = await axios.get('/api/llm/outputs', {
        params: { limit, enhancement_type }
      });
      return response.data;
    },
    refetchInterval: 2000, // Refresh every 2 seconds to show new outputs
  });
}