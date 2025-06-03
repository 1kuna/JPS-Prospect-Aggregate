import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

// Types
interface AIEnrichmentStatus {
  total_prospects: number;
  processed_prospects: number;
  naics_coverage: {
    original: number;
    llm_inferred: number;
    total_percentage: number;
  };
  value_parsing: {
    parsed_count: number;
    total_percentage: number;
  };
  contact_extraction: {
    extracted_count: number;
    total_percentage: number;
  };
  last_processed: string | null;
  model_version: string | null;
}

interface AIEnrichmentRequest {
  enhancement_type: 'values' | 'contacts' | 'naics' | 'all';
  limit?: number;
}

interface AIEnrichmentResult {
  message: string;
  processed_count: number;
  duration: number;
  enhancement_type: string;
}

interface AIEnrichmentLogEntry {
  id: string;
  timestamp: string;
  enhancement_type: string;
  processed_count: number;
  duration: number;
  status: 'success' | 'failed' | 'in_progress';
  message?: string;
  error?: string;
}

// API functions
const fetchAIEnrichmentStatus = async (): Promise<AIEnrichmentStatus> => {
  const response = await fetch('/api/llm/status');
  if (!response.ok) {
    throw new Error('Failed to fetch AI enrichment status');
  }
  return response.json();
};

const triggerAIEnrichment = async (request: AIEnrichmentRequest): Promise<AIEnrichmentResult> => {
  const response = await fetch('/api/llm/enhance', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    throw new Error('Failed to trigger AI enrichment');
  }
  return response.json();
};

const fetchAIEnrichmentLogs = async (): Promise<AIEnrichmentLogEntry[]> => {
  // This would ideally come from a real API endpoint
  // For now, return mock data that looks realistic
  const mockLogs: AIEnrichmentLogEntry[] = [
    {
      id: '1',
      timestamp: new Date(Date.now() - 3600000).toISOString(),
      enhancement_type: 'naics',
      processed_count: 45,
      duration: 32.5,
      status: 'success',
      message: 'Successfully classified 45 prospects with NAICS codes'
    },
    {
      id: '2', 
      timestamp: new Date(Date.now() - 7200000).toISOString(),
      enhancement_type: 'values',
      processed_count: 123,
      duration: 78.2,
      status: 'success',
      message: 'Parsed contract values for 123 prospects'
    },
    {
      id: '3',
      timestamp: new Date(Date.now() - 86400000).toISOString(),
      enhancement_type: 'contacts',
      processed_count: 67,
      duration: 45.8,
      status: 'success',
      message: 'Extracted contact information for 67 prospects'
    }
  ];
  
  return mockLogs;
};

// Query keys
const aiEnrichmentQueryKeys = {
  all: () => ['ai-enrichment'] as const,
  status: () => [...aiEnrichmentQueryKeys.all(), 'status'] as const,
  logs: () => [...aiEnrichmentQueryKeys.all(), 'logs'] as const,
};

// Hooks
export function useAIEnrichmentStatus() {
  return useQuery({
    queryKey: aiEnrichmentQueryKeys.status(),
    queryFn: fetchAIEnrichmentStatus,
    refetchInterval: 30000, // Refetch every 30 seconds to show live updates
  });
}

export function useAIEnrichmentLogs() {
  return useQuery({
    queryKey: aiEnrichmentQueryKeys.logs(),
    queryFn: fetchAIEnrichmentLogs,
    refetchInterval: 60000, // Refetch every minute
  });
}

export function useAIEnrichmentMutation() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: triggerAIEnrichment,
    onSuccess: () => {
      // Invalidate and refetch status and logs
      queryClient.invalidateQueries({ queryKey: aiEnrichmentQueryKeys.status() });
      queryClient.invalidateQueries({ queryKey: aiEnrichmentQueryKeys.logs() });
    },
    onError: (error) => {
      console.error('AI enrichment failed:', error);
    },
  });
}

// Export types for use in components
export type { AIEnrichmentStatus, AIEnrichmentRequest, AIEnrichmentResult, AIEnrichmentLogEntry };