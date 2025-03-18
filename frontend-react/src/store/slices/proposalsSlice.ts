import { StateCreator } from 'zustand';
import { fetchProposals } from '../api';

export interface ProposalsState {
  proposals: any[];
  proposalsPagination: {
    page: number;
    perPage: number;
    totalCount: number;
    totalPages: number;
  } | null;
  loading: { proposals: boolean };
  errors: { proposals: any | null };
  
  // Actions
  fetchProposals: (params?: { 
    page?: number; 
    perPage?: number; 
    sortBy?: string; 
    sortOrder?: string 
  }) => Promise<void>;
}

export const proposalsSlice: StateCreator<ProposalsState> = (set, get) => ({
  proposals: [],
  proposalsPagination: null,
  loading: { proposals: false },
  errors: { proposals: null },
  
  fetchProposals: async (params = {}) => {
    set((state) => ({ loading: { ...state.loading, proposals: true } }));
    try {
      const data = await fetchProposals(params);
      
      // Normalize pagination data to ensure consistent property names
      const normalizedPagination = data.pagination ? {
        page: data.pagination.page,
        perPage: data.pagination.per_page,
        totalPages: data.pagination.total_pages,
        totalCount: data.pagination.total_items
      } : null;
      
      set({ 
        proposals: data.data || [], 
        proposalsPagination: normalizedPagination,
        loading: { ...get().loading, proposals: false },
        errors: { ...get().errors, proposals: null }
      });
      
      return data.data;
    } catch (error: any) {
      console.error('Error fetching proposals:', error);
      set({ 
        loading: { ...get().loading, proposals: false },
        errors: { ...get().errors, proposals: { message: error.message } }
      });
      throw error;
    }
  },
}); 