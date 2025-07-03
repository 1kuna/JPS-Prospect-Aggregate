import { useState, useCallback } from 'react';
import { useQuery, keepPreviousData } from '@tanstack/react-query';
import { useEnhancementActivityMonitor } from './useEnhancementActivityMonitor';
import type { ProspectFilters } from './useProspectFilters';

// Match the Dashboard's Prospect interface for now
interface Prospect {
  id: string;
  native_id: string | null;
  title: string;
  ai_enhanced_title: string | null;
  description: string | null;
  agency: string | null;
  naics: string | null;
  naics_description: string | null;
  naics_source: string | null;
  estimated_value: string | null;
  est_value_unit: string | null;
  estimated_value_text: string | null;
  estimated_value_min: string | null;
  estimated_value_max: string | null;
  estimated_value_single: string | null;
  release_date: string | null;
  award_date: string | null;
  award_fiscal_year: number | null;
  _recentlyUpdated?: string;
  _updateTimestamp?: number;
  place_city: string | null;
  place_state: string | null;
  place_country: string | null;
  contract_type: string | null;
  set_aside: string | null;
  primary_contact_email: string | null;
  primary_contact_name: string | null;
  loaded_at: string | null;
  ollama_processed_at: string | null;
  ollama_model_version: string | null;
  enhancement_status: string | null;
  enhancement_started_at: string | null;
  enhancement_user_id: number | null;
  extra: Record<string, unknown> | null;
  source_id: number | null;
  source_name: string | null;
}

interface ProspectResponse {
  data: Prospect[];
  total: number;
  totalPages: number;
}

const fetchProspects = async (page: number, limit: number, filters?: ProspectFilters): Promise<ProspectResponse> => {
  const queryParams = new URLSearchParams();
  queryParams.append('page', page.toString());
  queryParams.append('limit', limit.toString());
  
  if (filters) {
    if (filters.naics) queryParams.append('naics', filters.naics);
    if (filters.keywords) queryParams.append('keywords', filters.keywords);
    if (filters.agency) queryParams.append('agency', filters.agency);
    if (filters.ai_enrichment && filters.ai_enrichment !== 'all') {
      queryParams.append('ai_enrichment', filters.ai_enrichment);
    }
    if (filters.dataSourceIds && filters.dataSourceIds.length > 0) {
      queryParams.append('source_ids', filters.dataSourceIds.join(','));
    }
  }
  
  const url = `/api/prospects?${queryParams.toString()}`;
  
  const response = await fetch(url);
  
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ message: 'Failed to fetch prospects and parse error response' }));
    throw new Error(errorData.error || `Network response was not ok: ${response.statusText}`);
  }
  
  const result: { prospects: Prospect[], pagination: { total_items: number, total_pages: number, page: number, per_page: number } } = await response.json();
  
  return {
    data: result.prospects,
    total: result.pagination.total_items,
    totalPages: result.pagination.total_pages
  };
};

export function usePaginatedProspects(filters: ProspectFilters) {
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage, setItemsPerPage] = useState(10);
  
  const { hasAnyActivity } = useEnhancementActivityMonitor();
  
  const { data: prospectsData, isLoading, isFetching, refetch } = useQuery({
    queryKey: ['prospects', currentPage, itemsPerPage, filters],
    queryFn: () => fetchProspects(currentPage, itemsPerPage, filters),
    placeholderData: keepPreviousData,
    staleTime: 5000,
    refetchInterval: hasAnyActivity ? 2000 : 30000,
    refetchOnWindowFocus: false,
  });

  const handlePageChange = useCallback((page: number) => {
    setCurrentPage(page);
  }, []);

  const handlePageSizeChange = useCallback((pageSize: number) => {
    setItemsPerPage(pageSize);
    setCurrentPage(1);
  }, []);

  const resetPagination = useCallback(() => {
    setCurrentPage(1);
  }, []);

  return {
    prospects: prospectsData?.data || [],
    total: prospectsData?.total || 0,
    totalPages: prospectsData?.totalPages || 0,
    currentPage,
    itemsPerPage,
    isLoading,
    isFetching,
    handlePageChange,
    handlePageSizeChange,
    resetPagination,
    refetch
  };
}