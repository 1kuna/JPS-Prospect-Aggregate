import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { 
  ApiResponse, 
  GoNoGoDecision, 
  DecisionStats,
  CreateDecisionRequest 
} from '../../types/api';

const API_BASE = '/api/decisions';

// Decision API functions
const decisionsApi = {
  createDecision: async (data: CreateDecisionRequest): Promise<ApiResponse<{ decision: GoNoGoDecision; message: string }>> => {
    const response = await fetch(`${API_BASE}/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify(data),
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.message || 'Failed to save decision');
    }
    
    return response.json();
  },

  getProspectDecisions: async (prospectId: string): Promise<ApiResponse<{ prospect_id: string; decisions: GoNoGoDecision[]; total_decisions: number }>> => {
    const response = await fetch(`${API_BASE}/${prospectId}`, {
      method: 'GET',
      credentials: 'include',
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.message || 'Failed to get prospect decisions');
    }
    
    return response.json();
  },

  getMyDecisions: async (page = 1, perPage = 50): Promise<ApiResponse<{ decisions: GoNoGoDecision[]; pagination: any }>> => {
    const response = await fetch(`${API_BASE}/my?page=${page}&per_page=${perPage}`, {
      method: 'GET',
      credentials: 'include',
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.message || 'Failed to get decisions');
    }
    
    return response.json();
  },

  getDecisionStats: async (): Promise<ApiResponse<DecisionStats>> => {
    const response = await fetch(`${API_BASE}/stats`, {
      method: 'GET',
      credentials: 'include',
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.message || 'Failed to get decision stats');
    }
    
    return response.json();
  },

  deleteDecision: async (decisionId: number): Promise<ApiResponse<{ message: string }>> => {
    const response = await fetch(`${API_BASE}/${decisionId}`, {
      method: 'DELETE',
      credentials: 'include',
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.message || 'Failed to delete decision');
    }
    
    return response.json();
  },
};

// Hook to get decisions for a specific prospect
export const useProspectDecisions = (prospectId: string | null) => {
  return useQuery({
    queryKey: ['decisions', 'prospect', prospectId],
    queryFn: () => decisionsApi.getProspectDecisions(prospectId!),
    enabled: !!prospectId,
    staleTime: 1 * 60 * 1000, // 1 minute
    retry: 1, // Only retry once
    retryDelay: 1000, // Wait 1 second before retry
  });
};

// Hook to get current user's decisions
export const useMyDecisions = (page = 1, perPage = 50) => {
  return useQuery({
    queryKey: ['decisions', 'my', page, perPage],
    queryFn: () => decisionsApi.getMyDecisions(page, perPage),
    staleTime: 2 * 60 * 1000, // 2 minutes
  });
};

// Hook to get decision statistics
export const useDecisionStats = () => {
  return useQuery({
    queryKey: ['decisions', 'stats'],
    queryFn: decisionsApi.getDecisionStats,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
};

// Hook to create or update a decision
export const useCreateDecision = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: decisionsApi.createDecision,
    onSuccess: (_, variables) => {
      // Invalidate queries related to this prospect
      queryClient.invalidateQueries({ 
        queryKey: ['decisions', 'prospect', variables.prospect_id] 
      });
      // Invalidate user's decisions and stats
      queryClient.invalidateQueries({ 
        queryKey: ['decisions', 'my'] 
      });
      queryClient.invalidateQueries({ 
        queryKey: ['decisions', 'stats'] 
      });
    },
  });
};

// Hook to delete a decision
export const useDeleteDecision = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: decisionsApi.deleteDecision,
    onSuccess: () => {
      // Invalidate all decision queries
      queryClient.invalidateQueries({ 
        queryKey: ['decisions'] 
      });
    },
  });
};