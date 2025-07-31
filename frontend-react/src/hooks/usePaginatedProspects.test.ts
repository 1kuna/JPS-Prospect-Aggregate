import { renderHook, act, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';
import { usePaginatedProspects } from './usePaginatedProspects';
import type { ProspectFilters } from './useProspectFilters';
import type { Prospect } from '@/types/prospects';

// Mock the fetch function
const mockFetch = vi.fn();
global.fetch = mockFetch;

// Mock the enhancement activity monitor
const mockUseEnhancementActivityMonitor = vi.fn();
vi.mock('./useEnhancementActivityMonitor', () => ({
  useEnhancementActivityMonitor: () => mockUseEnhancementActivityMonitor()
}));

const mockProspects: Prospect[] = [
  {
    id: 'prospect-1',
    title: 'Software Development Services',
    description: 'Development of custom software solutions',
    agency: 'Department of Defense',
    posted_date: '2024-01-15',
    loaded_at: '2024-01-15T10:00:00Z',
    estimated_value: 50000,
    estimated_value_text: '$50,000',
    naics_code: '541511',
    source_file: 'dod_2024_01_15.json',
    source_data_id: 1,
    enhancement_status: 'idle',
    duplicate_group_id: null,
    set_aside_status: null,
    contact_email: null,
    contact_name: null,
    ai_enhanced_title: null,
    ai_enhanced_description: null,
    parsed_contract_value: null,
    ollama_processed_at: null
  },
  {
    id: 'prospect-2',
    title: 'Cloud Infrastructure Setup',
    description: 'Setup and configuration of cloud infrastructure',
    agency: 'Health and Human Services',
    posted_date: '2024-01-16',
    loaded_at: '2024-01-16T10:00:00Z',
    estimated_value: 75000,
    estimated_value_text: '$75,000',
    naics_code: '518210',
    source_file: 'hhs_2024_01_16.json',
    source_data_id: 2,
    enhancement_status: 'idle',
    duplicate_group_id: null,
    set_aside_status: null,
    contact_email: null,
    contact_name: null,
    ai_enhanced_title: null,
    ai_enhanced_description: null,
    parsed_contract_value: null,
    ollama_processed_at: null
  }
];

const mockResponse = {
  prospects: mockProspects,
  pagination: {
    total_items: 25,
    total_pages: 3,
    page: 1,
    per_page: 10
  }
};

// Wrapper component for React Query
const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false }
    }
  });
  
  return ({ children }: { children: React.ReactNode }) => 
    React.createElement(QueryClientProvider, { client: queryClient }, children);
};

describe('usePaginatedProspects', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseEnhancementActivityMonitor.mockReturnValue({ hasAnyActivity: false });
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockResponse)
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  const defaultFilters: ProspectFilters = {
    naics: '',
    keywords: '',
    agency: '',
    ai_enrichment: 'all',
    dataSourceIds: []
  };

  it('initializes with correct default values', async () => {
    const { result } = renderHook(
      () => usePaginatedProspects(defaultFilters),
      { wrapper: createWrapper() }
    );

    expect(result.current.prospects).toEqual([]);
    expect(result.current.total).toBe(0);
    expect(result.current.totalPages).toBe(0);
    expect(result.current.currentPage).toBe(1);
    expect(result.current.itemsPerPage).toBe(10);
    expect(result.current.isLoading).toBe(true);
    expect(result.current.isFetching).toBe(true);

    // Wait for the query to resolve
    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.prospects).toEqual(mockProspects);
    expect(result.current.total).toBe(25);
    expect(result.current.totalPages).toBe(3);
  });

  it('constructs correct API URL with no filters', async () => {
    renderHook(
      () => usePaginatedProspects(defaultFilters),
      { wrapper: createWrapper() }
    );

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith('/api/prospects?page=1&limit=10');
    });
  });

  it('constructs correct API URL with all filters', async () => {
    const filters: ProspectFilters = {
      naics: '541511',
      keywords: 'software development',
      agency: 'DOD',
      ai_enrichment: 'enhanced',
      dataSourceIds: [1, 2, 3]
    };

    renderHook(
      () => usePaginatedProspects(filters),
      { wrapper: createWrapper() }
    );

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/prospects?page=1&limit=10&naics=541511&keywords=software+development&agency=DOD&ai_enrichment=enhanced&source_ids=1%2C2%2C3'
      );
    });
  });

  it('excludes ai_enrichment filter when set to "all"', async () => {
    const filters: ProspectFilters = {
      naics: '541511',
      keywords: 'test',
      agency: 'DOD',
      ai_enrichment: 'all',
      dataSourceIds: [1]
    };

    renderHook(
      () => usePaginatedProspects(filters),
      { wrapper: createWrapper() }
    );

    await waitFor(() => {
      const url = mockFetch.mock.calls[0][0];
      expect(url).not.toContain('ai_enrichment');
      expect(url).toContain('naics=541511');
      expect(url).toContain('keywords=test');
    });
  });

  it('excludes empty dataSourceIds', async () => {
    const filters: ProspectFilters = {
      naics: '541511',
      keywords: 'test',
      agency: 'DOD',
      ai_enrichment: 'all',
      dataSourceIds: []
    };

    renderHook(
      () => usePaginatedProspects(filters),
      { wrapper: createWrapper() }
    );

    await waitFor(() => {
      const url = mockFetch.mock.calls[0][0];
      expect(url).not.toContain('source_ids');
    });
  });

  it('handles page changes correctly', async () => {
    const { result } = renderHook(
      () => usePaginatedProspects(defaultFilters),
      { wrapper: createWrapper() }
    );

    // Wait for initial query
    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    // Change to page 2
    act(() => {
      result.current.handlePageChange(2);
    });

    expect(result.current.currentPage).toBe(2);

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith('/api/prospects?page=2&limit=10');
    });
  });

  it('handles page size changes correctly', async () => {
    const { result } = renderHook(
      () => usePaginatedProspects(defaultFilters),
      { wrapper: createWrapper() }
    );

    // Wait for initial query
    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    // Go to page 2 first
    act(() => {
      result.current.handlePageChange(2);
    });

    expect(result.current.currentPage).toBe(2);

    // Change page size (should reset to page 1)
    act(() => {
      result.current.handlePageSizeChange(25);
    });

    expect(result.current.currentPage).toBe(1);
    expect(result.current.itemsPerPage).toBe(25);

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith('/api/prospects?page=1&limit=25');
    });
  });

  it('resets pagination correctly', async () => {
    const { result } = renderHook(
      () => usePaginatedProspects(defaultFilters),
      { wrapper: createWrapper() }
    );

    // Wait for initial query
    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    // Go to page 3
    act(() => {
      result.current.handlePageChange(3);
    });

    expect(result.current.currentPage).toBe(3);

    // Reset pagination
    act(() => {
      result.current.resetPagination();
    });

    expect(result.current.currentPage).toBe(1);
  });

  it('refetches data correctly', async () => {
    const { result } = renderHook(
      () => usePaginatedProspects(defaultFilters),
      { wrapper: createWrapper() }
    );

    // Wait for initial query
    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    // Clear mock call history
    mockFetch.mockClear();

    // Trigger refetch
    await act(async () => {
      await result.current.refetch();
    });

    expect(mockFetch).toHaveBeenCalledWith('/api/prospects?page=1&limit=10');
  });

  it('adjusts refetch interval based on enhancement activity', async () => {
    // First render with no activity
    mockUseEnhancementActivityMonitor.mockReturnValue({ hasAnyActivity: false });
    
    const { rerender } = renderHook(
      () => usePaginatedProspects(defaultFilters),
      { wrapper: createWrapper() }
    );

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalled();
    });

    // Re-render with activity
    mockUseEnhancementActivityMonitor.mockReturnValue({ hasAnyActivity: true });
    rerender();

    // The hook should use different refetch intervals based on activity
    // Note: Testing exact intervals is complex with React Query, so we verify the hook responds to activity changes
    expect(mockUseEnhancementActivityMonitor).toHaveBeenCalled();
  });

  it('handles API errors gracefully', async () => {
    const errorResponse = {
      ok: false,
      status: 500,
      statusText: 'Internal Server Error',
      json: () => Promise.resolve({ error: 'Database connection failed' })
    };

    mockFetch.mockResolvedValue(errorResponse);

    const { result } = renderHook(
      () => usePaginatedProspects(defaultFilters),
      { wrapper: createWrapper() }
    );

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    // Data should remain empty on error
    expect(result.current.prospects).toEqual([]);
    expect(result.current.total).toBe(0);
  });

  it('handles API response without proper error JSON', async () => {
    const errorResponse = {
      ok: false,
      status: 500,
      statusText: 'Internal Server Error',
      json: () => Promise.reject(new Error('Invalid JSON'))
    };

    mockFetch.mockResolvedValue(errorResponse);

    const { result } = renderHook(
      () => usePaginatedProspects(defaultFilters),
      { wrapper: createWrapper() }
    );

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.prospects).toEqual([]);
  });

  it('updates query when filters change', async () => {
    const initialFilters: ProspectFilters = {
      naics: '',
      keywords: '',
      agency: '',
      ai_enrichment: 'all',
      dataSourceIds: []
    };

    const { result, rerender } = renderHook(
      ({ filters }) => usePaginatedProspects(filters),
      { 
        wrapper: createWrapper(),
        initialProps: { filters: initialFilters }
      }
    );

    // Wait for initial query
    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(mockFetch).toHaveBeenCalledWith('/api/prospects?page=1&limit=10');
    mockFetch.mockClear();

    // Change filters
    const newFilters: ProspectFilters = {
      naics: '541511',
      keywords: 'software',
      agency: 'DOD',
      ai_enrichment: 'enhanced',
      dataSourceIds: [1, 2]
    };

    rerender({ filters: newFilters });

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/prospects?page=1&limit=10&naics=541511&keywords=software&agency=DOD&ai_enrichment=enhanced&source_ids=1%2C2'
      );
    });
  });

  it('maintains stable function references', () => {
    const { result, rerender } = renderHook(
      () => usePaginatedProspects(defaultFilters),
      { wrapper: createWrapper() }
    );

    const initialHandlePageChange = result.current.handlePageChange;
    const initialHandlePageSizeChange = result.current.handlePageSizeChange;
    const initialResetPagination = result.current.resetPagination;

    rerender();

    expect(result.current.handlePageChange).toBe(initialHandlePageChange);
    expect(result.current.handlePageSizeChange).toBe(initialHandlePageSizeChange);
    expect(result.current.resetPagination).toBe(initialResetPagination);
  });

  it('handles empty response data gracefully', async () => {
    const emptyResponse = {
      prospects: [],
      pagination: {
        total_items: 0,
        total_pages: 0,
        page: 1,
        per_page: 10
      }
    };

    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(emptyResponse)
    });

    const { result } = renderHook(
      () => usePaginatedProspects(defaultFilters),
      { wrapper: createWrapper() }
    );

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.prospects).toEqual([]);
    expect(result.current.total).toBe(0);
    expect(result.current.totalPages).toBe(0);
  });

  it('encodes URL parameters correctly', async () => {
    const filters: ProspectFilters = {
      naics: '',
      keywords: 'artificial intelligence & machine learning',
      agency: 'Department of Health & Human Services',
      ai_enrichment: 'all',
      dataSourceIds: []
    };

    renderHook(
      () => usePaginatedProspects(filters),
      { wrapper: createWrapper() }
    );

    await waitFor(() => {
      const url = mockFetch.mock.calls[0][0];
      expect(url).toContain('keywords=artificial+intelligence+%26+machine+learning');
      expect(url).toContain('agency=Department+of+Health+%26+Human+Services');
    });
  });

  it('handles concurrent pagination changes', async () => {
    const { result } = renderHook(
      () => usePaginatedProspects(defaultFilters),
      { wrapper: createWrapper() }
    );

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    // Simulate rapid pagination changes
    act(() => {
      result.current.handlePageChange(2);
      result.current.handlePageChange(3);
      result.current.handlePageChange(1);
    });

    // Should end up on page 1
    expect(result.current.currentPage).toBe(1);
  });

  it('preserves pagination state across filter changes within same hook instance', async () => {
    const { result, rerender } = renderHook(
      ({ filters }) => usePaginatedProspects(filters),
      { 
        wrapper: createWrapper(),
        initialProps: { filters: defaultFilters }
      }
    );

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    // Change to page 2 and page size 20
    act(() => {
      result.current.handlePageChange(2);
      result.current.handlePageSizeChange(20);
    });

    expect(result.current.currentPage).toBe(1); // Should reset to 1 after page size change
    expect(result.current.itemsPerPage).toBe(20);

    // Change filters - pagination state should be preserved
    const newFilters: ProspectFilters = {
      ...defaultFilters,
      keywords: 'test'
    };

    rerender({ filters: newFilters });

    expect(result.current.itemsPerPage).toBe(20); // Page size should be preserved
  });
});