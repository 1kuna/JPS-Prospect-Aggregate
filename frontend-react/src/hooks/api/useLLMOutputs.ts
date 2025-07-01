import { useQuery } from '@tanstack/react-query';
import { get, buildQueryString } from '@/utils/apiUtils';
import { LLMParsedResult } from '@/types';

export interface LLMOutput {
  id: number;
  timestamp: string;
  prospect_id: string;
  prospect_title: string | null;
  enhancement_type: 'values' | 'contacts' | 'naics' | 'titles';
  prompt: string;
  response: string;
  parsed_result: LLMParsedResult;
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
      const queryParams = buildQueryString({ limit, enhancement_type });
      return await get<LLMOutput[]>(`/api/llm/outputs${queryParams}`);
    },
    refetchInterval: 2000, // Refresh every 2 seconds to show new outputs
  });
}