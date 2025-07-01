import { PageLayout } from '@/components/layout';
import { useQuery, keepPreviousData } from '@tanstack/react-query';
import { createColumnHelper, flexRender, getCoreRowModel, useReactTable } from '@tanstack/react-table';
import { useState, useCallback, useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useProspectEnhancement } from '@/contexts/ProspectEnhancementContext';
import { useTimezoneDate } from '@/hooks/useTimezoneDate';
import { useEnhancementActivityMonitor } from '@/hooks/useEnhancementActivityMonitor';
import { ReloadIcon } from '@radix-ui/react-icons';
import { Switch } from '@/components/ui/switch';
import { GoNoGoDecision } from '@/components/GoNoGoDecision';
import { useListDataSources } from '@/hooks/api/useDataSources';
import { DataSource } from '@/types';
import { EnhancementButton } from '@/components/EnhancementButton';
import { EnhancementProgress } from '@/components/EnhancementProgress';
import { EnhancementErrorBoundary } from '@/components/EnhancementErrorBoundary';

// Updated Prospect interface based on backend model
interface Prospect {
  id: string; // Primary key, string (UUID)
  native_id: string | null; // From source system
  title: string; // Main title/name of the prospect
  ai_enhanced_title: string | null; // NEW: AI-enhanced title
  description: string | null;
  agency: string | null;
  naics: string | null;
  naics_description: string | null; // NEW: NAICS description
  naics_source: string | null; // NEW: 'original', 'llm_inferred', 'llm_enhanced'
  estimated_value: string | null; // Represented as string in to_dict
  est_value_unit: string | null;
  estimated_value_text: string | null; // NEW: Original value as text
  estimated_value_min: string | null; // NEW: LLM-parsed minimum
  estimated_value_max: string | null; // NEW: LLM-parsed maximum
  estimated_value_single: string | null; // NEW: LLM best estimate
  release_date: string | null; // ISO date string
  award_date: string | null; // ISO date string
  award_fiscal_year: number | null;
  // Animation properties for real-time updates
  _recentlyUpdated?: string;
  _updateTimestamp?: number;
  place_city: string | null;
  place_state: string | null;
  place_country: string | null;
  contract_type: string | null;
  set_aside: string | null;
  primary_contact_email: string | null; // NEW: LLM-extracted email
  primary_contact_name: string | null; // NEW: LLM-extracted name
  loaded_at: string | null; // ISO datetime string
  ollama_processed_at: string | null; // NEW: When LLM processing completed
  ollama_model_version: string | null; // NEW: Which LLM version was used
  enhancement_status: string | null; // NEW: 'idle', 'in_progress', 'failed'
  enhancement_started_at: string | null; // NEW: When enhancement started
  enhancement_user_id: number | null; // NEW: User ID who started enhancement
  extra: Record<string, unknown> | null; // JSON object
  source_id: number | null;
  source_name: string | null; // Name of the data source
}

// Mock API call functions - replace with actual API calls
// const fetchProspectCount = async (): Promise<{ count: number }> => {
//   await new Promise(resolve => setTimeout(resolve, 300));
//   return { count: 583 }; // Example count
// };

interface ProspectFilters {
  naics?: string;
  keywords?: string;
  agency?: string;
  ai_enrichment?: 'all' | 'enhanced' | 'original';
  dataSourceIds?: number[];
}

const fetchProspects = async (page: number, limit: number, filters?: ProspectFilters): Promise<{ data: Prospect[], total: number, totalPages: number }> => {
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
  
  try {
    const response = await fetch(url);
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ message: 'Failed to fetch prospects and parse error response' }));
      console.error('Error response:', errorData);
      throw new Error(errorData.error || `Network response was not ok: ${response.statusText}`);
    }
    
    const result: { prospects: Prospect[], pagination: { total_items: number, total_pages: number, page: number, per_page: number } } = await response.json();
    
    
    // Map the backend response structure to what the frontend expects
    return {
      data: result.prospects,
      total: result.pagination.total_items,
      totalPages: result.pagination.total_pages
    };
  } catch (error) {
    console.error('Fetch error:', error);
    throw error;
  }
};

const columnHelper = createColumnHelper<Prospect>();

// Column definitions moved inside the component to access showAIEnhanced state

export default function Dashboard() {
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage, setItemsPerPage] = useState(10);
  const [selectedProspectId, setSelectedProspectId] = useState<string | null>(null);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [showAIEnhanced, setShowAIEnhanced] = useState(true);
  // Enhancement tracking simplified with unified system
  
  // Filter states
  const [filters, setFilters] = useState<ProspectFilters>({
    naics: '',
    keywords: '',
    agency: '',
    ai_enrichment: 'all',
    dataSourceIds: []  // Changed to array for multiple selection
  });

  // Data sources hook
  const { data: dataSourcesData } = useListDataSources();
  const dataSources = dataSourcesData?.data || [];

  // Enhancement hook
  const { addToQueue, getProspectStatus } = useProspectEnhancement();
  
  // Timezone hook for date formatting
  const { formatUserDate } = useTimezoneDate();
  
  // Activity monitoring for intelligent polling and refresh
  const { hasAnyActivity } = useEnhancementActivityMonitor();

  // Enhancement system simplified - unified hooks handle progress and updates

  // const { data: countData, isLoading: isLoadingCount } = useQuery({
  //   queryKey: ['prospectCount'],
  //   queryFn: fetchProspectCount,
  // });

  
  const { data: prospectsData, isLoading: isLoadingProspects, isFetching: isFetchingProspects } = useQuery({
    queryKey: ['prospects', currentPage, itemsPerPage, filters],
    queryFn: () => fetchProspects(currentPage, itemsPerPage, filters),
    placeholderData: keepPreviousData,
    staleTime: 5000, // Data stays fresh for 5 seconds
    refetchInterval: hasAnyActivity ? 2000 : 30000, // Faster refetch during activity
    refetchOnWindowFocus: false, // Don't refetch when tab gains focus
  });

  // Get live prospect data from cache for modal (updates in real-time)
  const selectedProspect = useMemo(() => {
    if (!selectedProspectId || !prospectsData?.data) return null;
    const found = prospectsData.data.find((p: Prospect) => p.id === selectedProspectId) || null;
    if (found) {
      console.log(`Modal prospect data updated for ${selectedProspectId}:`, {
        ollama_processed_at: found.ollama_processed_at,
        ai_enhanced_title: found.ai_enhanced_title,
        estimated_value_single: found.estimated_value_single
      });
    }
    return found;
  }, [selectedProspectId, prospectsData?.data]);
  

  // Define columns inside component to access showAIEnhanced state
  const columns = useMemo(() => [
    columnHelper.accessor((row) => {
      // Check if we should show AI enhanced title
      if (showAIEnhanced && row.ai_enhanced_title) {
        return row.ai_enhanced_title;
      }
      // Otherwise show original title logic
      if (row.title) return row.title;
      if (row.extra?.summary && typeof row.extra.summary === 'string') return row.extra.summary;
      // Fallback: construct from agency and native_id
      if (row.native_id) {
        const agency = row.extra?.agency || row.agency || 'Unknown Agency';
        return `${agency} - ${row.native_id}`;
      }
      return 'No Title';
    }, {
      id: 'title',
      header: 'Title',
      cell: info => {
        const value = info.getValue();
        const row = info.row.original;
        const isAIEnhanced = showAIEnhanced && !!row.ai_enhanced_title && row.title !== row.ai_enhanced_title;
        const title = isAIEnhanced 
          ? `${value} (AI Enhanced)` 
          : value || 'No Title';
        
        return (
          <div className="w-full truncate" title={title}>
            <span className={isAIEnhanced ? 'text-blue-700 font-medium' : ''}>
              {String(value) || 'No Title'}
            </span>
          </div>
        );
      },
      size: 350,
    }),
    columnHelper.accessor((row) => row.extra?.agency || row.agency, {
      id: 'agency',
      header: 'Agency',
      cell: info => {
        const value = info.getValue();
        return <div className="w-full truncate" title={String(value) || 'N/A'}>{String(value) || 'N/A'}</div>;
      },
      size: 200,
    }),
    columnHelper.accessor((row) => {
      const naics = showAIEnhanced ? row.naics : (row.naics_source === 'llm_inferred' ? null : row.naics);
      const description = showAIEnhanced ? row.naics_description : null;
      
      if (!naics) return 'N/A';
      
      const display = description ? `${naics} - ${description}` : naics;
      
      return display;
    }, {
      id: 'naics',
      header: 'NAICS',
      cell: info => {
        const value = info.getValue();
        const row = info.row.original;
        const isAIEnhanced = row.naics_source === 'llm_inferred';
        const title = isAIEnhanced 
          ? `${value} (AI Classified)` 
          : row.naics_source === 'original' 
          ? `${value} (Original)` 
          : value;
        
        return (
          <div className="w-full truncate" title={title}>
            <span className={isAIEnhanced && showAIEnhanced ? 'text-blue-700 font-medium' : ''}>
              {value}
            </span>
            {isAIEnhanced && showAIEnhanced && (
              <div className="w-2 h-2 bg-blue-500 rounded-full inline-block ml-2" title="AI Enhanced"></div>
            )}
          </div>
        );
      },
      size: 200,
    }),
    columnHelper.accessor((row) => {
      // Show enhanced estimated value if available and toggle is on, otherwise fall back to original
      if (showAIEnhanced && row.estimated_value_single) {
        const single = parseFloat(row.estimated_value_single);
        if (single >= 1000000) {
          return `$${(single / 1000000).toFixed(1)}M`;
        } else if (single >= 1000) {
          return `$${(single / 1000).toFixed(0)}K`;
        } else {
          return `$${single.toFixed(0)}`;
        }
      }
      
      // Original value logic
      if (row.estimated_value_text) {
        return row.estimated_value_text;
      } else if (row.estimated_value) {
        const value = parseFloat(row.estimated_value);
        if (value >= 1000000) {
          return `$${(value / 1000000).toFixed(1)}M`;
        } else if (value >= 1000) {
          return `$${(value / 1000).toFixed(0)}K`;
        } else {
          return `$${value.toFixed(0)}`;
        }
      }
      return 'N/A';
    }, {
      id: 'estimated_value',
      header: 'Est. Value',
      cell: info => {
        const value = info.getValue();
        const row = info.row.original;
        const isAIEnhanced = showAIEnhanced && !!row.estimated_value_single;
        
        return (
          <div title={value} className={isAIEnhanced ? 'text-green-700 font-medium' : ''}>
            {value}
            {isAIEnhanced && (
              <div className="w-2 h-2 bg-green-500 rounded-full inline-block ml-2" title="AI Parsed"></div>
            )}
          </div>
        );
      },
      size: 120,
    }),
    columnHelper.accessor((row) => row.extra?.acquisition_phase || row.contract_type, {
      id: 'contract_type',
      header: 'Type',
      cell: info => {
        const value = info.getValue();
        return <div className="w-full truncate" title={String(value) || 'N/A'}>{String(value) || 'N/A'}</div>;
      },
      size: 150,
    }),
  ], [showAIEnhanced]);

  const table = useReactTable({
    data: prospectsData?.data || [],
    columns,
    getCoreRowModel: getCoreRowModel(),
    manualPagination: true,
    rowCount: prospectsData?.total || 0,
  });

  const totalPages = prospectsData?.totalPages || 0;

  const handlePageChange = useCallback((page: number) => {
    if (page < 1 || page > totalPages) return;
    setCurrentPage(page);
  }, [totalPages]);

  const handlePreviousPage = useCallback(() => {
    setCurrentPage((prev) => Math.max(prev - 1, 1));
  }, []);

  const handleNextPage = useCallback(() => {
    setCurrentPage((prev) => Math.min(prev + 1, totalPages));
  }, [totalPages]);

  const handleItemsPerPageChange = useCallback((value: string) => {
    setItemsPerPage(Number(value));
    setCurrentPage(1);
  }, []);
  
  const handleFilterChange = useCallback((filterKey: keyof ProspectFilters, value: string) => {
    setFilters(prev => ({ ...prev, [filterKey]: value }));
    setCurrentPage(1); // Reset to first page when filters change
  }, []);
  
  const handleDataSourceToggle = useCallback((sourceId: number) => {
    setFilters(prev => {
      const currentIds = prev.dataSourceIds || [];
      const newIds = currentIds.includes(sourceId)
        ? currentIds.filter((id: number) => id !== sourceId)
        : [...currentIds, sourceId];
      return { ...prev, dataSourceIds: newIds };
    });
    setCurrentPage(1);
  }, []);
  
  const handleRowClick = useCallback((prospect: Prospect) => {
    setSelectedProspectId(prospect.id);
    setIsDialogOpen(true);
  }, []);
  
  const clearFilters = useCallback(() => {
    setFilters({ naics: '', keywords: '', agency: '', ai_enrichment: 'all', dataSourceIds: [] });
    setCurrentPage(1);
  }, []);
  
  const hasActiveFilters = Object.entries(filters).some(([key, value]) => {
    if (key === 'ai_enrichment') {
      return value && value !== 'all';
    }
    if (key === 'dataSourceIds') {
      return Array.isArray(value) && value.length > 0;
    }
    return value && value.trim() !== '';
  });
  
  const renderPaginationItems = () => {
    const pageItems = [];

    if (totalPages <= 1) return null; // No pagination needed for 1 or 0 pages

    // Previous Button
    pageItems.push(
      <Button
        key="prev"
        variant="outline"
        size="sm"
        onClick={handlePreviousPage}
        disabled={currentPage === 1}
        className="h-8 px-2 sm:px-3 flex items-center gap-1"
      >
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
          <path fillRule="evenodd" d="M12.707 5.293a1 1 0 010 1.414L9.414 10l3.293 3.293a1 1 0 01-1.414 1.414l-4-4a1 1 0 010-1.414l4-4a1 1 0 011.414 0z" clipRule="evenodd" />
        </svg>
        <span className="hidden sm:inline">Previous</span>
      </Button>
    );

    // Page numbers logic
    if (totalPages <= 5) { // Show all pages if 5 or less
      for (let i = 1; i <= totalPages; i++) {
        pageItems.push(
          <Button
            key={i}
            variant={currentPage === i ? "default" : "outline"}
            size="sm"
            onClick={() => handlePageChange(i)}
            className="h-8 min-w-[2rem] px-2"
          >
            {i}
          </Button>
        );
      }
    } else {
      // First page
      pageItems.push(
        <Button
          key={1}
          variant={currentPage === 1 ? "default" : "outline"}
          size="sm"
          onClick={() => handlePageChange(1)}
          className="h-8 min-w-[2.5rem] px-3"
        >
          1
        </Button>
      );

      // Ellipsis after first page
      if (currentPage > 4) {
        pageItems.push(
          <span key="start-ellipsis" className="text-gray-400 px-2">...</span>
        );
      }

      // Middle pages - show fewer pages to avoid cramping
      let startPage, endPage;
      
      if (currentPage <= 3) {
        // Near the beginning
        startPage = 2;
        endPage = Math.min(4, totalPages - 1);
      } else if (currentPage >= totalPages - 2) {
        // Near the end
        startPage = Math.max(totalPages - 3, 2);
        endPage = totalPages - 1;
      } else {
        // In the middle
        startPage = currentPage - 1;
        endPage = currentPage + 1;
      }

      for (let i = startPage; i <= endPage; i++) {
        pageItems.push(
          <Button
            key={i}
            variant={currentPage === i ? "default" : "outline"}
            size="sm"
            onClick={() => handlePageChange(i)}
            className="h-8 min-w-[2rem] px-2"
          >
            {i}
          </Button>
        );
      }

      // Ellipsis before last page
      if (currentPage < totalPages - 3) {
        pageItems.push(
          <span key="end-ellipsis" className="text-gray-400 px-2">...</span>
        );
      }

      // Last page
      pageItems.push(
        <Button
          key={totalPages}
          variant={currentPage === totalPages ? "default" : "outline"}
          size="sm"
          onClick={() => handlePageChange(totalPages)}
          className="h-8 min-w-[2.5rem] px-3"
        >
          {totalPages}
        </Button>
      );
    }

    // Next Button
    pageItems.push(
      <Button
        key="next"
        variant="outline"
        size="sm"
        onClick={handleNextPage}
        disabled={currentPage === totalPages}
        className="h-8 px-2 sm:px-3 flex items-center gap-1"
      >
        <span className="hidden sm:inline">Next</span>
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
          <path fillRule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clipRule="evenodd" />
        </svg>
      </Button>
    );

    return pageItems;
  };

  return (
    <PageLayout
      title="Dashboard"
      subtitle="Overview of your data collection system"
    >
      {/* Main container with filters and content */}
      <div className="flex gap-6">
        {/* Filters Sidebar */}
        <div className="w-80 flex-shrink-0">
          <Card className="shadow-lg">
            <CardHeader className="pb-4">
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg font-semibold text-black">Filters</CardTitle>
                {hasActiveFilters && (
                  <Button 
                    variant="outline" 
                    size="sm" 
                    onClick={clearFilters}
                    className="text-xs px-2 py-1 h-7"
                  >
                    Clear All
                  </Button>
                )}
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Keywords Filter */}
              <div className="space-y-2">
                <Label htmlFor="keywords" className="text-sm font-medium text-gray-700">
                  Keywords
                </Label>
                <Input
                  id="keywords"
                  placeholder="Search in title, description..."
                  value={filters.keywords || ''}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) => handleFilterChange('keywords', e.target.value)}
                  className="text-sm"
                />
              </div>
              
              {/* NAICS Code Filter */}
              <div className="space-y-2">
                <Label htmlFor="naics" className="text-sm font-medium text-gray-700">
                  NAICS Code
                </Label>
                <Input
                  id="naics"
                  placeholder="e.g., 541511, 334"
                  value={filters.naics || ''}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) => handleFilterChange('naics', e.target.value)}
                  className="text-sm"
                />
              </div>
              
              {/* Agency Filter */}
              <div className="space-y-2">
                <Label htmlFor="agency" className="text-sm font-medium text-gray-700">
                  Agency
                </Label>
                <Input
                  id="agency"
                  placeholder="e.g., DOD, HHS, DHS"
                  value={filters.agency || ''}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) => handleFilterChange('agency', e.target.value)}
                  className="text-sm"
                />
              </div>
              
              {/* Data Source Filter */}
              <div className="space-y-2">
                <Label className="text-sm font-medium text-gray-700">
                  Data Source
                </Label>
                <div className="max-h-48 overflow-y-auto border rounded-md p-3 space-y-2">
                  {dataSources.map((source: DataSource) => (
                    <label 
                      key={source.id} 
                      className="flex items-center space-x-2 cursor-pointer hover:bg-gray-50 p-1 rounded"
                    >
                      <input
                        type="checkbox"
                        checked={filters.dataSourceIds?.includes(source.id) || false}
                        onChange={() => handleDataSourceToggle(source.id)}
                        className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                      />
                      <span className="text-sm text-gray-700">{source.name}</span>
                    </label>
                  ))}
                  {dataSources.length === 0 && (
                    <div className="text-sm text-gray-500 text-center py-2">
                      No data sources available
                    </div>
                  )}
                </div>
              </div>
              
              {/* AI Enrichment Filter */}
              <div className="space-y-2">
                <Label htmlFor="ai-enrichment" className="text-sm font-medium text-gray-700">
                  AI Enrichment
                </Label>
                <Select value={filters.ai_enrichment || 'all'} onValueChange={(value: 'all' | 'enhanced' | 'original') => handleFilterChange('ai_enrichment', value)}>
                  <SelectTrigger className="text-sm">
                    <SelectValue placeholder="All prospects" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Prospects</SelectItem>
                    <SelectItem value="enhanced">AI Enhanced Only</SelectItem>
                    <SelectItem value="original">Original Data Only</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              
              {/* Show AI Enhancements Toggle */}
              <div className="space-y-2 pt-2 border-t border-gray-200">
                <div className="flex items-center justify-between">
                  <Label htmlFor="show-ai-table" className="text-sm font-medium text-gray-700">
                    Show AI Enhancements
                  </Label>
                  <Switch
                    id="show-ai-table"
                    checked={showAIEnhanced}
                    onCheckedChange={setShowAIEnhanced}
                  />
                </div>
                <p className="text-xs text-gray-500">
                  {showAIEnhanced ? 'Showing AI-enhanced data in table' : 'Showing original data only'}
                </p>
              </div>
              
              {/* Filter Summary */}
              {hasActiveFilters && (
                <div className="pt-2 border-t border-gray-200">
                  <p className="text-xs text-gray-600 mb-2">Active filters:</p>
                  <div className="space-y-1">
                    {filters.keywords && (
                      <div className="text-xs bg-blue-50 text-blue-700 px-2 py-1 rounded flex justify-between items-center">
                        <span>Keywords: {filters.keywords}</span>
                        <button 
                          onClick={() => handleFilterChange('keywords', '')}
                          className="ml-1 text-blue-500 hover:text-blue-700"
                        >
                          ×
                        </button>
                      </div>
                    )}
                    {filters.naics && (
                      <div className="text-xs bg-green-50 text-green-700 px-2 py-1 rounded flex justify-between items-center">
                        <span>NAICS: {filters.naics}</span>
                        <button 
                          onClick={() => handleFilterChange('naics', '')}
                          className="ml-1 text-green-500 hover:text-green-700"
                        >
                          ×
                        </button>
                      </div>
                    )}
                    {filters.agency && (
                      <div className="text-xs bg-purple-50 text-purple-700 px-2 py-1 rounded flex justify-between items-center">
                        <span>Agency: {filters.agency}</span>
                        <button 
                          onClick={() => handleFilterChange('agency', '')}
                          className="ml-1 text-purple-500 hover:text-purple-700"
                        >
                          ×
                        </button>
                      </div>
                    )}
                    {filters.dataSourceIds && filters.dataSourceIds.length > 0 && (
                      filters.dataSourceIds.map((sourceId: number) => {
                        const source = dataSources.find((s: DataSource) => s.id === sourceId);
                        return (
                          <div key={sourceId} className="text-xs bg-orange-50 text-orange-700 px-2 py-1 rounded flex justify-between items-center">
                            <span>Source: {source ? source.name : sourceId}</span>
                            <button 
                              onClick={() => handleDataSourceToggle(sourceId)}
                              className="ml-1 text-orange-500 hover:text-orange-700"
                            >
                              ×
                            </button>
                          </div>
                        );
                      })
                    )}
                    {filters.ai_enrichment && filters.ai_enrichment !== 'all' && (
                      <div className="text-xs bg-indigo-50 text-indigo-700 px-2 py-1 rounded flex justify-between items-center">
                        <span>AI: {filters.ai_enrichment === 'enhanced' ? 'Enhanced Only' : 'Original Only'}</span>
                        <button 
                          onClick={() => handleFilterChange('ai_enrichment', 'all')}
                          className="ml-1 text-indigo-500 hover:text-indigo-700"
                        >
                          ×
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
        
        {/* Prospects List Card - Main content */}
        <div className="flex-grow">
          <Card className="shadow-lg">
            <CardHeader className="flex flex-row items-center justify-between py-5 px-6 border-b border-gray-200">
              <CardTitle className="text-2xl font-bold text-black">Prospects List</CardTitle>
              <div className="flex items-center space-x-4">
                {/* Real-time connection status */}
                <div className="flex items-center space-x-2">
                  <div className={`w-2 h-2 rounded-full ${hasAnyActivity ? 'bg-green-500' : 'bg-gray-500'} ${hasAnyActivity ? 'animate-pulse' : ''}`}></div>
                  <span className="text-xs text-gray-600">
                    {hasAnyActivity ? 'Live updates' : 'Idle'}
                  </span>
                </div>
                
                <div className="flex items-center space-x-2">
                  <span className="text-sm font-medium text-gray-600">Rows per page:</span>
                  <Select value={itemsPerPage.toString()} onValueChange={handleItemsPerPageChange}>
                    <SelectTrigger className="w-[80px] h-9 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
                      <SelectValue placeholder={itemsPerPage} />
                    </SelectTrigger>
                    <SelectContent>
                      {[10, 20, 30, 50, 100].map(val => (
                        <SelectItem key={val} value={val.toString()} className="text-sm">
                          {val}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </CardHeader>
            <CardContent className="pt-6 px-6 pb-6 relative">
              {isLoadingProspects && (
                <div className="flex flex-col items-center justify-center h-96 space-y-4">
                  <div className="animate-spin rounded-full h-16 w-16 border-t-4 border-b-4 border-blue-600"></div>
                  <p className="text-lg font-semibold text-gray-700">Loading prospects...</p>
                  <p className="text-sm text-gray-600">Please wait while we fetch the data.</p>
                </div>
              )}
              {!isLoadingProspects && (!prospectsData?.data || prospectsData.data.length === 0) && (
                  <div className="flex flex-col items-center justify-center h-96 text-center space-y-3">
                      <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-20 h-20 text-gray-400">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 6.75h7.5M8.25 12h7.5m-7.5 5.25h7.5M3.75 6.75h.007v.008H3.75V6.75Zm.375 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0ZM3.75 12h.007v.008H3.75V12Zm.375 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm-.375 5.25h.007v.008H3.75v-.008Zm.375 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Z" />
                          <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 8.25v8.25a2.25 2.25 0 0 0 2.25 2.25h15a2.25 2.25 0 0 0 2.25-2.25V8.25m-19.5 0V6c0-1.243.81-2.25 1.907-2.25H19.5A2.25 2.25 0 0 1 21.75 6v2.25m-19.5 0a2.25 2.25 0 0 0 2.25 2.25h15a2.25 2.25 0 0 0 2.25-2.25m-19.5 0V6.75" />
                      </svg>
                      <p className="text-2xl font-semibold text-gray-700">No Prospects Found</p>
                      <p className="text-gray-600 max-w-md">It looks like there are no prospects matching your current criteria. Try adjusting filters or adding new prospects.</p>
                  </div>
              )}
              {prospectsData && prospectsData.data && prospectsData.data.length > 0 && (
                <>
                  {/* Combined overflow container, height increased by 1rem */}
                  <div className={`h-[464px] overflow-y-auto overflow-x-auto rounded-lg border border-gray-200 shadow-sm transition-opacity duration-500 ease-in-out ${isFetchingProspects && !isLoadingProspects ? 'opacity-80' : 'opacity-100'}`}>
                    <Table className="min-w-full divide-y divide-gray-200 table-fixed">
                      {/* TableHeader with a softer, custom shadow */}
                      <TableHeader className="sticky top-0 z-10 bg-gray-50 shadow-[0_2px_8px_rgba(0,0,0,0.08)]">
                        {table.getHeaderGroups().map(headerGroup => (
                          <TableRow key={headerGroup.id}>
                            {headerGroup.headers.map(header => (
                              <TableHead 
                                key={header.id} 
                                className="px-6 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider whitespace-nowrap"
                                style={{ width: header.getSize() !== 0 ? header.getSize() : undefined }}
                              >
                                {header.isPlaceholder
                                  ? null
                                  : flexRender(
                                      header.column.columnDef.header,
                                      header.getContext()
                                    )}
                              </TableHead>
                            ))}
                          </TableRow>
                        ))}
                      </TableHeader>
                      <TableBody className="bg-white divide-y divide-gray-200">
                        {table.getRowModel().rows.map((row, rowIndex) => {
                          const isRecentlyUpdated = false; // Animation removed for performance
                          
                          return (
                            <TableRow 
                              key={row.id} 
                              className={`transition-all duration-300 ease-in-out hover:bg-gray-100 cursor-pointer ${
                                rowIndex % 2 === 0 ? 'bg-white' : 'bg-gray-50/50'
                              } data-[state=selected]:bg-blue-50 data-[state=selected]:hover:bg-blue-100 ${
                                isRecentlyUpdated ? 'animate-pulse bg-gradient-to-r from-green-50 to-blue-50 border-l-4 border-l-blue-500 shadow-lg scale-[1.01]' : ''
                              }`}
                              onClick={() => handleRowClick(row.original)}
                              style={{
                                animation: isRecentlyUpdated ? 'highlightUpdate 2s ease-in-out' : undefined
                              }}
                            >
                              {row.getVisibleCells().map(cell => (
                                <TableCell 
                                  key={cell.id} 
                                  className="px-6 py-4 whitespace-nowrap text-sm text-gray-800 align-top overflow-hidden"
                                  style={{ 
                                    width: cell.column.getSize() !== 0 ? cell.column.getSize() : undefined,
                                    maxWidth: cell.column.getSize() !== 0 ? cell.column.getSize() : undefined
                                  }}
                                >
                                  {flexRender(cell.column.columnDef.cell, cell.getContext())}
                                </TableCell>
                              ))}
                            </TableRow>
                          );
                        })}
                      </TableBody>
                    </Table>
                  </div>
                  {totalPages > 1 && (
                    <div className="mt-6 flex flex-col sm:flex-row items-center justify-between gap-4">
                       <p className="text-sm font-medium text-gray-700">
                          Showing <span className="font-semibold">{((currentPage - 1) * itemsPerPage + 1)}-{Math.min(currentPage * itemsPerPage, prospectsData?.total || 0)}</span> of <span className="font-semibold">{prospectsData?.total.toLocaleString()}</span> results
                       </p>
                      <div className="flex items-center gap-2">
                        {renderPaginationItems()}
                      </div>
                    </div>
                  )}
                </>
              )}
               {/* Show polling indicator when actively enhancing or fetching */}
               {(hasAnyActivity || (isFetchingProspects && !isLoadingProspects)) && prospectsData && prospectsData.data.length > 0 && (
                   <div className="absolute top-2 right-2 bg-blue-50/90 backdrop-blur-sm rounded-full px-2 py-1 shadow-sm border border-blue-200 flex items-center gap-1.5 z-10">
                      <div className="animate-spin rounded-full h-3 w-3 border-t-2 border-b-2 border-blue-500"></div>
                      <p className="text-xs font-medium text-blue-700">
                        {hasAnyActivity ? 'AI Enhancing' : 'Updating'}
                      </p>
                  </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Prospect Details Dialog */}
      <Dialog open={isDialogOpen} onOpenChange={(open) => {
        setIsDialogOpen(open);
        if (!open) setSelectedProspectId(null);
      }}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-2xl font-bold pr-8">
              <span className={selectedProspect?.ai_enhanced_title ? 'text-blue-700' : ''}>
                {(() => {
                  if (!selectedProspect) return 'Prospect Details';
                  // Prioritize AI-enhanced title if available
                  if (selectedProspect.ai_enhanced_title) return selectedProspect.ai_enhanced_title;
                  // Use the same logic as the table column
                  if (selectedProspect.title) return selectedProspect.title;
                  if (selectedProspect.extra?.summary && typeof selectedProspect.extra.summary === 'string') {
                    return selectedProspect.extra.summary;
                  }
                  if (selectedProspect.native_id) {
                    const agency = selectedProspect.extra?.agency || selectedProspect.agency || 'Unknown Agency';
                    return `${agency} - ${selectedProspect.native_id}`;
                  }
                  return 'Prospect Details';
                })()}
              </span>
              {(() => {
                if (!selectedProspect) return null;
                const status = getProspectStatus(selectedProspect.id);
                const isActive = ['queued', 'processing'].includes(status?.status as string);
                if (!isActive) return null;
                
                return (
                  <div className="inline-flex items-center ml-3 px-2 py-1 text-xs font-medium bg-yellow-100 text-yellow-800 rounded-full">
                    <ReloadIcon className="mr-1 h-3 w-3 animate-spin" />
                    {status?.currentStep || status?.status === 'queued' ? `Queued (#${status.queuePosition})` : 'Being Enhanced'}
                  </div>
                );
              })()}
            </DialogTitle>
            <DialogDescription>
              Full details for this prospect opportunity
            </DialogDescription>
          </DialogHeader>
          
          {selectedProspect && (
            <div className="space-y-6 mt-6">
              {/* Enhancement Button */}
              {!selectedProspect.ollama_processed_at && (
                <div className="flex justify-end">
                  <EnhancementErrorBoundary>
                    <EnhancementButton 
                      prospect={selectedProspect}
                      userId={1}
                    />
                  </EnhancementErrorBoundary>
                </div>
              )}
              
              {/* Enhancement Progress */}
              <EnhancementErrorBoundary>
                <EnhancementProgress 
                  status={getProspectStatus(selectedProspect?.id || '')}
                  isVisible={(() => {
                    if (!selectedProspect) return false;
                    const status = getProspectStatus(selectedProspect.id);
                    // Show progress when queued, processing, or recently completed
                    return ['queued', 'processing', 'completed'].includes(status?.status as string);
                  })()}
                />
              </EnhancementErrorBoundary>
              
              {/* Enhancement Status */}
              {selectedProspect.ollama_processed_at && (
                <div className="bg-blue-50 border border-blue-200 p-3 rounded-lg">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center text-sm text-blue-800">
                      <div className="w-2 h-2 bg-blue-500 rounded-full mr-2"></div>
                      {selectedProspect.ollama_processed_at ? 
                        `AI Enhanced on ${formatUserDate(selectedProspect.ollama_processed_at, 'datetime')}` : 
                        'Not enhanced'
                      }
                    </div>
                    <Button
                      onClick={() => {
                        if (selectedProspect) {
                          addToQueue({
                            prospect_id: selectedProspect.id,
                            force_redo: true,
                            user_id: 1
                          });
                        }
                      }}
                      disabled={(() => {
                        const queueStatus = getProspectStatus(selectedProspect?.id);
                        return queueStatus?.status === 'processing' || 
                               queueStatus?.status === 'queued';
                      })()}
                      variant="outline"
                      size="sm"
                      className="text-blue-700 border-blue-300 hover:bg-blue-100 disabled:bg-gray-100 disabled:text-gray-400"
                    >
                      {(() => {
                        const queueStatus = getProspectStatus(selectedProspect?.id);
                        if (queueStatus?.status === 'processing') {
                          return (
                            <>
                              <ReloadIcon className="mr-2 h-3 w-3 animate-spin" />
                              {queueStatus?.currentStep || 'Re-enhancing...'}
                            </>
                          );
                        } else if (queueStatus?.status === 'queued') {
                          return (
                            <>
                              <ReloadIcon className="mr-2 h-3 w-3 animate-spin" />
                              Queued (#{queueStatus.queuePosition})
                            </>
                          );
                        } else {
                          return 'Redo Enhancement';
                        }
                      })()}
                    </Button>
                  </div>
                </div>
              )}
              
              {/* AI Enhancement Toggle */}
              <div className="bg-gray-50 border border-gray-200 p-3 rounded-lg">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <Label htmlFor="ai-toggle" className="text-sm font-medium text-gray-700">
                      Show AI-Enhanced Fields
                    </Label>
                    <Switch
                      id="ai-toggle"
                      checked={showAIEnhanced}
                      onCheckedChange={setShowAIEnhanced}
                    />
                  </div>
                  <div className="text-xs text-gray-500">
                    {showAIEnhanced ? 'Showing AI-enhanced data where available' : 'Showing original data only'}
                  </div>
                </div>
              </div>

              {/* Go/No-Go Decision */}
              <div className="bg-blue-50 border border-blue-200 p-4 rounded-lg">
                <GoNoGoDecision 
                  prospectId={selectedProspect.id} 
                  prospectTitle={selectedProspect.ai_enhanced_title || selectedProspect.title}
                  compact={false} 
                />
              </div>

              {/* Basic Information */}
              <div>
                <h3 className="text-lg font-semibold mb-3 text-gray-900">Basic Information</h3>
                <div className="grid grid-cols-1 gap-4 bg-gray-50 p-4 rounded-lg">
                  <div className={`${(() => {
                    const status = getProspectStatus(selectedProspect.id);
                    const isTitleActive = status?.currentStep?.toLowerCase().includes('title') || 
                                        status?.currentStep?.toLowerCase().includes('enhancing');
                    const isTitleCompleted = status?.progress?.titles?.completed;
                    
                    // Only show animation if actively processing titles and not yet completed
                    return (isTitleActive && !isTitleCompleted) ? 'animate-pulse bg-blue-50 border border-blue-200 rounded p-2' : '';
                  })()}`}>
                    <span className="font-medium text-gray-700">Title:</span>
                    {(() => {
                      const status = getProspectStatus(selectedProspect.id);
                      const isTitleActive = status?.currentStep?.toLowerCase().includes('title') || 
                                          status?.currentStep?.toLowerCase().includes('enhancing');
                      const isTitleCompleted = status?.progress?.titles?.completed;
                      
                      // Only show spinner if actively processing titles and not yet completed
                      return (isTitleActive && !isTitleCompleted) ? (
                        <span className="ml-2 text-xs px-2 py-1 rounded bg-blue-100 text-blue-700 animate-pulse inline-flex items-center">
                          <ReloadIcon className="w-3 h-3 mr-1 animate-spin" />
                          Enhancing...
                        </span>
                      ) : null;
                    })()}
                    <p className="mt-1 text-gray-900">{(() => {
                      // Use AI-enhanced title if toggle is on and available
                      if (showAIEnhanced && selectedProspect.ai_enhanced_title) {
                        return selectedProspect.ai_enhanced_title;
                      }
                      // Otherwise use original logic
                      if (selectedProspect.title) return selectedProspect.title;
                      if (selectedProspect.extra?.summary && typeof selectedProspect.extra.summary === 'string') {
                        return selectedProspect.extra.summary;
                      }
                      if (selectedProspect.native_id) {
                        const agency = selectedProspect.extra?.agency || selectedProspect.agency || 'Unknown Agency';
                        return `${agency} - ${selectedProspect.native_id}`;
                      }
                      return 'N/A';
                    })()}
                    {(() => {
                      const status = getProspectStatus(selectedProspect.id);
                      const isTitleActive = status?.currentStep?.toLowerCase().includes('title') || 
                                          status?.currentStep?.toLowerCase().includes('enhancing');
                      const isTitleCompleted = status?.progress?.titles?.completed;
                      
                      return showAIEnhanced && selectedProspect.ai_enhanced_title && selectedProspect.title && !(isTitleActive && !isTitleCompleted);
                    })() && (
                      <span className="ml-2 text-xs px-2 py-1 rounded bg-green-100 text-green-700">
                        AI Enhanced
                      </span>
                    )}
                    </p>
                  </div>
                  {selectedProspect.description && (
                    <div>
                      <span className="font-medium text-gray-700">Description:</span>
                      <p className="mt-1 text-gray-900 whitespace-pre-wrap">{selectedProspect.description}</p>
                    </div>
                  )}
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <span className="font-medium text-gray-700">Agency:</span>
                      <p className="mt-1 text-gray-900">{selectedProspect.agency || 'N/A'}</p>
                    </div>
                    <div className={`${(() => {
                      const status = getProspectStatus(selectedProspect.id);
                      const isNaicsActive = status?.currentStep?.toLowerCase().includes('naics') || 
                                          status?.currentStep?.toLowerCase().includes('classifying');
                      const isNaicsCompleted = status?.progress?.naics?.completed;
                      
                      return (isNaicsActive && !isNaicsCompleted) ? 'animate-pulse bg-blue-50 border border-blue-200 rounded p-2' : '';
                    })()}`}>
                      <span className="font-medium text-gray-700">NAICS:</span>
                      {(() => {
                        const status = getProspectStatus(selectedProspect.id);
                        const isNaicsActive = status?.currentStep?.toLowerCase().includes('naics') || 
                                            status?.currentStep?.toLowerCase().includes('classifying');
                        const isNaicsCompleted = status?.progress?.naics?.completed;
                        
                        return (isNaicsActive && !isNaicsCompleted) ? (
                          <span className="ml-2 text-xs px-2 py-1 rounded bg-blue-100 text-blue-700 animate-pulse inline-flex items-center">
                            <ReloadIcon className="w-3 h-3 mr-1 animate-spin" />
                            Classifying...
                          </span>
                        ) : null;
                      })()}
                      <p className="mt-1 text-gray-900">
                        {(() => {
                          // Show AI NAICS only if toggle is on and it's AI classified
                          if (!showAIEnhanced && selectedProspect.naics_source === 'llm_inferred') {
                            return 'N/A (Original data not available)';
                          }
                          return selectedProspect.naics || 'N/A';
                        })()}
                        {(() => {
                          const status = getProspectStatus(selectedProspect.id);
                          const isNaicsActive = status?.currentStep?.toLowerCase().includes('naics') || 
                                              status?.currentStep?.toLowerCase().includes('classifying');
                          const isNaicsCompleted = status?.progress?.naics?.completed;
                          
                          return showAIEnhanced && selectedProspect.naics_source && !(isNaicsActive && !isNaicsCompleted);
                        })() && (
                          <span className={`ml-2 text-xs px-2 py-1 rounded ${
                            selectedProspect.naics_source === 'llm_inferred' 
                              ? 'bg-blue-100 text-blue-700' 
                              : 'bg-gray-100 text-gray-600'
                          }`}>
                            {selectedProspect.naics_source === 'llm_inferred' ? 'AI Classified' : 'Original'}
                          </span>
                        )}
                      </p>
                      {showAIEnhanced && selectedProspect.naics_description && (
                        <p className="mt-1 text-sm text-gray-600">{selectedProspect.naics_description}</p>
                      )}
                    </div>
                  </div>
                </div>
              </div>

              {/* Financial Information */}
              <div>
                <h3 className="text-lg font-semibold mb-3 text-gray-900">Financial Information</h3>
                <div className="grid grid-cols-1 gap-4 bg-gray-50 p-4 rounded-lg">
                  {/* Original estimated value */}
                  <div>
                    <span className="font-medium text-gray-700">Original Estimated Value:</span>
                    <p className="mt-1 text-gray-900">
                      {selectedProspect.estimated_value_text || selectedProspect.estimated_value || 'N/A'}
                      {selectedProspect.est_value_unit && ` ${selectedProspect.est_value_unit}`}
                    </p>
                  </div>
                  
                  {/* AI-parsed values with progress indicator */}
                  {(() => {
                    const status = getProspectStatus(selectedProspect.id);
                    const isValuesActive = status?.currentStep?.toLowerCase().includes('value') || 
                                         status?.currentStep?.toLowerCase().includes('parsing');
                    const isValuesCompleted = status?.progress?.values?.completed;
                    
                    return (isValuesActive && !isValuesCompleted) ? (
                      <div className="bg-blue-50 p-3 rounded-lg border border-blue-200 animate-pulse">
                        <div className="flex items-center mb-2">
                          <span className="font-medium text-blue-800">Parsing Contract Values</span>
                          <ReloadIcon className="ml-2 w-4 h-4 animate-spin text-blue-600" />
                        </div>
                        <p className="text-sm text-blue-600">AI is analyzing the contract value text...</p>
                      </div>
                    ) : null;
                  })()}
                  
                  {/* AI-parsed values */}
                  {(() => {
                    const status = getProspectStatus(selectedProspect.id);
                    const isValuesActive = status?.currentStep?.toLowerCase().includes('value') || 
                                         status?.currentStep?.toLowerCase().includes('parsing');
                    const isValuesCompleted = status?.progress?.values?.completed;
                    
                    return showAIEnhanced && (selectedProspect.estimated_value_min || selectedProspect.estimated_value_max || selectedProspect.estimated_value_single) && !(isValuesActive && !isValuesCompleted);
                  })() && (
                    <div className="bg-green-50 p-3 rounded-lg border border-green-200">
                      <div className="flex items-center mb-2">
                        <span className="font-medium text-green-800">AI-Processed Values</span>
                        <div className="w-2 h-2 bg-green-500 rounded-full ml-2"></div>
                      </div>
                      <div className="mt-1 space-y-1">
                        {selectedProspect.estimated_value_single && (
                          <p className="text-gray-900">
                            <span className="text-sm text-gray-600">Best Estimate:</span> ${parseFloat(selectedProspect.estimated_value_single).toLocaleString()}
                          </p>
                        )}
                        {(selectedProspect.estimated_value_min || selectedProspect.estimated_value_max) && (
                          <p className="text-gray-900">
                            <span className="text-sm text-gray-600">Range:</span> 
                            ${selectedProspect.estimated_value_min ? parseFloat(selectedProspect.estimated_value_min).toLocaleString() : '?'} - 
                            ${selectedProspect.estimated_value_max ? parseFloat(selectedProspect.estimated_value_max).toLocaleString() : '?'}
                          </p>
                        )}
                      </div>
                    </div>
                  )}
                  
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <span className="font-medium text-gray-700">Contract Type:</span>
                      <p className="mt-1 text-gray-900">{selectedProspect.contract_type || 'N/A'}</p>
                    </div>
                    <div>
                      <span className="font-medium text-gray-700">Set Aside:</span>
                      <p className="mt-1 text-gray-900">{selectedProspect.set_aside || 'N/A'}</p>
                    </div>
                    <div>
                      <span className="font-medium text-gray-700">Award Fiscal Year:</span>
                      <p className="mt-1 text-gray-900">{selectedProspect.award_fiscal_year || 'N/A'}</p>
                    </div>
                  </div>
                </div>
              </div>

              {/* Dates */}
              <div>
                <h3 className="text-lg font-semibold mb-3 text-gray-900">Important Dates</h3>
                <div className="grid grid-cols-2 gap-4 bg-gray-50 p-4 rounded-lg">
                  <div>
                    <span className="font-medium text-gray-700">Release Date:</span>
                    <p className="mt-1 text-gray-900">
                      {selectedProspect.release_date 
                        ? formatUserDate(selectedProspect.release_date, 'date')
                        : 'N/A'}
                    </p>
                  </div>
                  <div>
                    <span className="font-medium text-gray-700">Award Date:</span>
                    <p className="mt-1 text-gray-900">
                      {selectedProspect.award_date 
                        ? formatUserDate(selectedProspect.award_date, 'date')
                        : 'N/A'}
                    </p>
                  </div>
                </div>
              </div>

              {/* Location */}
              <div>
                <h3 className="text-lg font-semibold mb-3 text-gray-900">Location</h3>
                <div className="bg-gray-50 p-4 rounded-lg">
                  <p className="text-gray-900">
                    {[selectedProspect.place_city, selectedProspect.place_state, selectedProspect.place_country]
                      .filter(Boolean)
                      .join(', ') || 'N/A'}
                  </p>
                </div>
              </div>

              {/* Contact Information with progress indicator */}
              {(() => {
                const status = getProspectStatus(selectedProspect.id);
                const isContactsActive = status?.currentStep?.toLowerCase().includes('contact') || 
                                       status?.currentStep?.toLowerCase().includes('extracting');
                const isContactsCompleted = status?.progress?.contacts?.completed;
                
                return (isContactsActive && !isContactsCompleted) ? (
                  <div>
                    <div className="flex items-center mb-3">
                      <h3 className="text-lg font-semibold text-gray-900">Contact Information</h3>
                      <ReloadIcon className="ml-2 w-4 h-4 animate-spin text-blue-600" />
                    </div>
                    <div className="bg-blue-50 p-4 rounded-lg border border-blue-200 animate-pulse">
                      <p className="text-blue-600 font-medium">Extracting contact information...</p>
                      <p className="text-sm text-blue-500">AI is analyzing available contact data</p>
                    </div>
                  </div>
                ) : null;
              })()}

              {/* Contact Information */}
              {(() => {
                const status = getProspectStatus(selectedProspect.id);
                const isContactsActive = status?.currentStep?.toLowerCase().includes('contact') || 
                                       status?.currentStep?.toLowerCase().includes('extracting');
                const isContactsCompleted = status?.progress?.contacts?.completed;
                
                return !(isContactsActive && !isContactsCompleted) && (selectedProspect.primary_contact_email || selectedProspect.primary_contact_name);
              })() && (
                <div>
                  {(() => {
                    // Determine if contact information was AI-extracted
                    // Contact info is AI-extracted if:
                    // 1. The prospect has been processed by LLM (ollama_processed_at exists), AND
                    // 2. We're showing AI enhanced data, AND  
                    // 3. The contact info wasn't imported from source data originally
                    
                    // For now, we'll use a simple heuristic: if ollama_processed_at exists and we're showing AI data,
                    // we assume contacts were AI-extracted. This will need refinement as we track contact source better.
                    const isAIExtracted = showAIEnhanced && selectedProspect.ollama_processed_at;
                    
                    return (
                      <>
                        <div className="flex items-center mb-3">
                          <h3 className="text-lg font-semibold text-gray-900">Contact Information</h3>
                          {isAIExtracted && (
                            <div className="w-2 h-2 bg-orange-500 rounded-full ml-2" title="AI Extracted"></div>
                          )}
                        </div>
                        <div className={`grid grid-cols-2 gap-4 p-4 rounded-lg ${
                          isAIExtracted 
                            ? 'bg-orange-50 border border-orange-200' 
                            : 'bg-gray-50 border border-gray-200'
                        }`}>
                          {selectedProspect.primary_contact_name && (
                            <div>
                              <span className={`font-medium ${isAIExtracted ? 'text-orange-800' : 'text-gray-700'}`}>
                                Primary Contact:
                              </span>
                              <p className="mt-1 text-gray-900">{selectedProspect.primary_contact_name}</p>
                            </div>
                          )}
                          {selectedProspect.primary_contact_email && (
                            <div>
                              <span className={`font-medium ${isAIExtracted ? 'text-orange-800' : 'text-gray-700'}`}>
                                Email:
                              </span>
                              <p className="mt-1 text-gray-900">
                                <a href={`mailto:${selectedProspect.primary_contact_email}`} 
                                   className="text-blue-600 hover:text-blue-800 underline">
                                  {selectedProspect.primary_contact_email}
                                </a>
                              </p>
                            </div>
                          )}
                        </div>
                        {isAIExtracted && (
                          <p className="text-xs text-gray-500 mt-2">AI-extracted contact information</p>
                        )}
                      </>
                    );
                  })()}
                </div>
              )}

              {/* System Information */}
              <div>
                <h3 className="text-lg font-semibold mb-3 text-gray-900">System Information</h3>
                <div className="grid grid-cols-2 gap-4 bg-gray-50 p-4 rounded-lg">
                  <div>
                    <span className="font-medium text-gray-700">Source:</span>
                    <p className="mt-1 text-gray-900">{selectedProspect.source_name || 'N/A'}</p>
                  </div>
                  <div>
                    <span className="font-medium text-gray-700">Native ID:</span>
                    <p className="mt-1 text-gray-900 font-mono text-sm">{selectedProspect.native_id || 'N/A'}</p>
                  </div>
                  <div>
                    <span className="font-medium text-gray-700">Loaded At:</span>
                    <p className="mt-1 text-gray-900">
                      {selectedProspect.loaded_at 
                        ? formatUserDate(selectedProspect.loaded_at)
                        : 'N/A'}
                    </p>
                  </div>
                  <div>
                    <span className="font-medium text-gray-700">ID:</span>
                    <p className="mt-1 text-gray-900 font-mono text-sm">{selectedProspect.id}</p>
                  </div>
                  {selectedProspect.ollama_processed_at && (
                    <>
                      <div>
                        <span className="font-medium text-gray-700">LLM Processed:</span>
                        <p className="mt-1 text-gray-900">
                          {formatUserDate(selectedProspect.ollama_processed_at)}
                        </p>
                      </div>
                      <div>
                        <span className="font-medium text-gray-700">LLM Model:</span>
                        <p className="mt-1 text-gray-900">{selectedProspect.ollama_model_version || 'N/A'}</p>
                      </div>
                    </>
                  )}
                </div>
              </div>

              {/* Extra Information */}
              {selectedProspect.extra && (
                <div>
                  <h3 className="text-lg font-semibold mb-3 text-gray-900">Additional Information</h3>
                  <div className="bg-gray-50 p-4 rounded-lg">
                    <pre className="text-sm text-gray-900 whitespace-pre-wrap font-mono">
                      {(() => {
                        try {
                          // If it's a string, try to parse and reformat it
                          if (typeof selectedProspect.extra === 'string') {
                            const parsed = JSON.parse(selectedProspect.extra);
                            return JSON.stringify(parsed, null, 2);
                          }
                          // If it's already an object, format it
                          return JSON.stringify(selectedProspect.extra, null, 2);
                        } catch {
                          // If parsing fails, return the original string as string
                          return String(selectedProspect.extra);
                        }
                      })()}
                    </pre>
                  </div>
                </div>
              )}

            </div>
          )}
        </DialogContent>
      </Dialog>
    </PageLayout>
  );
}
