import { useState, useCallback, useMemo } from 'react';
import { useQuery, keepPreviousData } from '@tanstack/react-query';
import { useEnhancementActivityMonitor } from './useEnhancementActivityMonitor';
import type { ProspectFilters } from './useProspectFilters';
import type { Prospect } from '@/types/prospects';

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
    if (filters.ai_enrichment && filters.ai_enrichment !== 'all') {
      queryParams.append('ai_enrichment', filters.ai_enrichment);
    }
    if (filters.dataSourceIds && filters.dataSourceIds.length > 0) {
      queryParams.append('source_ids', filters.dataSourceIds.join(','));
    }
  }
  
  const url = `/api/prospects?${queryParams.toString()}`;
  
  const response = await fetch(url, { credentials: 'include' });
  
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ message: 'Failed to fetch prospects and parse error response' }));
    throw new Error(errorData.error || `Network response was not ok: ${response.statusText}`);
  }
  
  const json = await response.json();
  const data = json?.data || {};
  const prospects: Prospect[] = data.prospects || data.items || [];
  const pagination = data.pagination || { total_items: 0, total_pages: 0 };

  return {
    data: prospects,
    total: pagination.total_items || 0,
    totalPages: pagination.total_pages || 0,
  };
};

export function usePaginatedProspects(filters: ProspectFilters) {
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage, setItemsPerPage] = useState(10);
  // Stabilize filters in the query key to avoid rerenders from object identity
  const filtersKey = useMemo(() => JSON.stringify(filters), [filters]);
  
  const { hasAnyActivity } = useEnhancementActivityMonitor();
  
  const { data: prospectsData, isLoading, isFetching, refetch } = useQuery({
    queryKey: ['prospects', currentPage, itemsPerPage, filtersKey],
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
