import { StateCreator } from 'zustand';
import { api } from '../api';
import { createAsyncSlice } from '../middleware/createAsyncSlice';

export interface Proposal {
  id: number | string;
  title: string;
  agency: string;
  release_date?: string;
  status: string;
  data_source_id: number;
  [key: string]: any;
}

export interface PaginationData {
  page: number;
  perPage: number;
  totalCount: number;
  totalPages: number;
}

export interface ProposalsState {
  // Data
  proposals: Proposal[];
  proposalsLoading: boolean;
  proposalsError: { message: string } | null;
  
  // Pagination state
  proposalsPagination: PaginationData | null;
  
  // Actions
  fetchProposals: (params?: { 
    page?: number; 
    perPage?: number; 
    sortBy?: string; 
    sortOrder?: string 
  }) => Promise<Proposal[]>;
}

export const proposalsSlice: StateCreator<ProposalsState> = (set, get) => {
  const proposalsAsync = createAsyncSlice<Proposal[], ProposalsState>(
    'proposals',
    {
      fetchProposals: async (params = {}) => {
        const response = await api.fetchProposals(params);
        
        // Store pagination data
        const normalizedPagination = response.pagination ? {
          page: response.pagination.page,
          perPage: response.pagination.per_page,
          totalPages: response.pagination.total_pages,
          totalCount: response.pagination.total_items
        } : null;
        
        // Update pagination state
        set({ proposalsPagination: normalizedPagination });
        
        return response.data || [];
      }
    },
    [] // Initial empty array
  )(set, get);
  
  return {
    // Include the async slice
    ...proposalsAsync,
    
    // Additional state (initialized with defaults)
    proposalsPagination: null,
  };
}; 