import { PageLayout } from '@/components/layout';
import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { createColumnHelper, flexRender, getCoreRowModel, useReactTable } from '@tanstack/react-table';
import { useState, useCallback } from 'react';
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

// Updated Prospect interface based on backend model
interface Prospect {
  id: string; // Primary key, string (UUID)
  native_id: string | null; // From source system
  title: string; // Main title/name of the prospect
  description: string | null;
  agency: string | null;
  naics: string | null;
  estimated_value: string | null; // Represented as string in to_dict
  est_value_unit: string | null;
  release_date: string | null; // ISO date string
  award_date: string | null; // ISO date string
  award_fiscal_year: number | null;
  place_city: string | null;
  place_state: string | null;
  place_country: string | null;
  contract_type: string | null;
  set_aside: string | null;
  loaded_at: string | null; // ISO datetime string
  extra: Record<string, any> | null; // JSON object
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
}

const fetchProspects = async (page: number, limit: number, filters?: ProspectFilters): Promise<{ data: Prospect[], total: number, totalPages: number }> => {
  const queryParams = new URLSearchParams();
  queryParams.append('page', page.toString());
  queryParams.append('limit', limit.toString());
  
  if (filters) {
    if (filters.naics) queryParams.append('naics', filters.naics);
    if (filters.keywords) queryParams.append('keywords', filters.keywords);
    if (filters.agency) queryParams.append('agency', filters.agency);
  }
  
  const url = `/api/prospects?${queryParams.toString()}`;
  console.log('Fetching prospects from:', url);
  
  try {
    const response = await fetch(url);
    console.log('Response status:', response.status);
    console.log('Response headers:', response.headers);
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ message: 'Failed to fetch prospects and parse error response' }));
      console.error('Error response:', errorData);
      throw new Error(errorData.error || `Network response was not ok: ${response.statusText}`);
    }
    
    const result: { prospects: Prospect[], pagination: { total_items: number, total_pages: number, page: number, per_page: number } } = await response.json();
    
    // Debug logging
    console.log('API Response:', result);
    console.log('Prospects count:', result.prospects?.length);
    console.log('First prospect:', result.prospects?.[0]);
    
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

const columns = [
  columnHelper.accessor((row) => {
    // Try multiple sources for title
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
      return <div className="w-full truncate" title={value || 'No Title'}>{value || 'No Title'}</div>;
    },
    size: 350,
  }),
  columnHelper.accessor((row) => row.extra?.agency || row.agency, {
    id: 'agency',
    header: 'Agency',
    cell: info => {
      const value = info.getValue();
      return <div className="w-full truncate" title={value || 'N/A'}>{value || 'N/A'}</div>;
    },
    size: 200,
  }),
  columnHelper.accessor('naics', {
    header: 'NAICS',
    cell: info => {
      const value = info.getValue();
      return <div className="w-full truncate" title={value || 'N/A'}>{value || 'N/A'}</div>;
    },
    size: 120,
  }),
  columnHelper.accessor((row) => row.extra?.acquisition_phase || row.contract_type, {
    id: 'status',
    header: 'Status',
    cell: info => {
      const value = info.getValue();
      return <div className="w-full truncate" title={value || 'N/A'}>{value || 'N/A'}</div>;
    },
    size: 150,
  }),
];

export default function Dashboard() {
  console.log('Dashboard component loaded!');
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage, setItemsPerPage] = useState(10);
  const [selectedProspect, setSelectedProspect] = useState<Prospect | null>(null);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  
  // Filter states
  const [filters, setFilters] = useState<ProspectFilters>({
    naics: '',
    keywords: '',
    agency: ''
  });

  // const { data: countData, isLoading: isLoadingCount } = useQuery({
  //   queryKey: ['prospectCount'],
  //   queryFn: fetchProspectCount,
  // });

  console.log('About to call useQuery with:', { currentPage, itemsPerPage });
  
  const { data: prospectsData, isLoading: isLoadingProspects, isFetching: isFetchingProspects } = useQuery({
    queryKey: ['prospects', currentPage, itemsPerPage, filters],
    queryFn: () => fetchProspects(currentPage, itemsPerPage, filters),
    placeholderData: keepPreviousData,
  });
  
  console.log('useQuery result:', { prospectsData, isLoadingProspects, isFetchingProspects });

  const table = useReactTable({
    data: prospectsData?.data || [],
    columns,
    getCoreRowModel: getCoreRowModel(),
    manualPagination: true,
    rowCount: prospectsData?.total || 0,
  });

  const totalPages = prospectsData?.totalPages || 0;

  const handlePageChange = (page: number) => {
    if (page < 1 || page > totalPages) return;
    setCurrentPage(page);
  }

  const handlePreviousPage = () => {
    setCurrentPage((prev) => Math.max(prev - 1, 1));
  };

  const handleNextPage = () => {
    setCurrentPage((prev) => Math.min(prev + 1, totalPages));
  };

  const handleItemsPerPageChange = (value: string) => {
    setItemsPerPage(Number(value));
    setCurrentPage(1);
  };
  
  const handleFilterChange = useCallback((filterKey: keyof ProspectFilters, value: string) => {
    setFilters(prev => ({ ...prev, [filterKey]: value }));
    setCurrentPage(1); // Reset to first page when filters change
  }, []);
  
  const clearFilters = useCallback(() => {
    setFilters({ naics: '', keywords: '', agency: '' });
    setCurrentPage(1);
  }, []);
  
  const hasActiveFilters = Object.values(filters).some(value => value && value.trim() !== '');
  
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
            </CardHeader>
            <CardContent className="pt-6 px-6 pb-6 relative">
              {(isLoadingProspects || isFetchingProspects) && (!prospectsData?.data || prospectsData.data.length === 0) && (
                <div className="flex flex-col items-center justify-center h-96 space-y-4">
                  <div className="animate-spin rounded-full h-16 w-16 border-t-4 border-b-4 border-blue-600"></div>
                  <p className="text-lg font-semibold text-gray-700">Loading prospects...</p>
                  <p className="text-sm text-gray-600">Please wait while we fetch the data.</p>
                </div>
              )}
              {!(isLoadingProspects || isFetchingProspects) && (!prospectsData?.data || prospectsData.data.length === 0) && (
                  <div className="flex flex-col items-center justify-center h-96 text-center space-y-3">
                      <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-20 h-20 text-gray-400">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 6.75h7.5M8.25 12h7.5m-7.5 5.25h7.5M3.75 6.75h.007v.008H3.75V6.75Zm.375 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0ZM3.75 12h.007v.008H3.75V12Zm.375 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm-.375 5.25h.007v.008H3.75v-.008Zm.375 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Z" />
                          <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 8.25v8.25a2.25 2.25 0 0 0 2.25 2.25h15a2.25 2.25 0 0 0 2.25-2.25V8.25m-19.5 0V6c0-1.243.81-2.25 1.907-2.25H19.5A2.25 2.25 0 0 1 21.75 6v2.25m-19.5 0a2.25 2.25 0 0 0 2.25 2.25h15a2.25 2.25 0 0 0 2.25-2.25m-19.5 0V6.75" />
                      </svg>
                      <p className="text-2xl font-semibold text-gray-700">No Prospects Found</p>
                      <p className="text-gray-600 max-w-md">It looks like there are no prospects matching your current criteria. Try adjusting filters or adding new prospects.</p>
                  </div>
              )}
              {prospectsData && prospectsData.data.length > 0 && (
                <>
                  {/* Combined overflow container, height increased by 1rem */}
                  <div className="h-[464px] overflow-y-auto overflow-x-auto rounded-lg border border-gray-200 shadow-sm">
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
                        {table.getRowModel().rows.map((row, rowIndex) => (
                          <TableRow 
                            key={row.id} 
                            className={`transition-colors duration-150 ease-in-out hover:bg-gray-100 cursor-pointer ${rowIndex % 2 === 0 ? 'bg-white' : 'bg-gray-50/50'} data-[state=selected]:bg-blue-50 data-[state=selected]:hover:bg-blue-100`}
                            onClick={() => {
                              setSelectedProspect(row.original);
                              setIsDialogOpen(true);
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
                        ))}
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
               {(isLoadingProspects || isFetchingProspects) && prospectsData && prospectsData.data.length > 0 && (
                   <div className="absolute inset-0 bg-white/80 backdrop-blur-sm flex items-center justify-center rounded-md z-10">
                      <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-blue-600"></div>
                      <p className="ml-3 text-base font-medium text-gray-700">Updating data...</p>
                  </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Prospect Details Dialog */}
      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-2xl font-bold pr-8">
              {(() => {
                if (!selectedProspect) return 'Prospect Details';
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
            </DialogTitle>
            <DialogDescription>
              Full details for this prospect opportunity
            </DialogDescription>
          </DialogHeader>
          
          {selectedProspect && (
            <div className="space-y-6 mt-6">
              {/* Basic Information */}
              <div>
                <h3 className="text-lg font-semibold mb-3 text-gray-900">Basic Information</h3>
                <div className="grid grid-cols-1 gap-4 bg-gray-50 p-4 rounded-lg">
                  <div>
                    <span className="font-medium text-gray-700">Title:</span>
                    <p className="mt-1 text-gray-900">{(() => {
                      if (selectedProspect.title) return selectedProspect.title;
                      if (selectedProspect.extra?.summary && typeof selectedProspect.extra.summary === 'string') {
                        return selectedProspect.extra.summary;
                      }
                      if (selectedProspect.native_id) {
                        const agency = selectedProspect.extra?.agency || selectedProspect.agency || 'Unknown Agency';
                        return `${agency} - ${selectedProspect.native_id}`;
                      }
                      return 'N/A';
                    })()}</p>
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
                    <div>
                      <span className="font-medium text-gray-700">NAICS:</span>
                      <p className="mt-1 text-gray-900">{selectedProspect.naics || 'N/A'}</p>
                    </div>
                  </div>
                </div>
              </div>

              {/* Financial Information */}
              <div>
                <h3 className="text-lg font-semibold mb-3 text-gray-900">Financial Information</h3>
                <div className="grid grid-cols-2 gap-4 bg-gray-50 p-4 rounded-lg">
                  <div>
                    <span className="font-medium text-gray-700">Estimated Value:</span>
                    <p className="mt-1 text-gray-900">
                      {selectedProspect.estimated_value || 'N/A'}
                      {selectedProspect.est_value_unit && ` ${selectedProspect.est_value_unit}`}
                    </p>
                  </div>
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

              {/* Dates */}
              <div>
                <h3 className="text-lg font-semibold mb-3 text-gray-900">Important Dates</h3>
                <div className="grid grid-cols-2 gap-4 bg-gray-50 p-4 rounded-lg">
                  <div>
                    <span className="font-medium text-gray-700">Release Date:</span>
                    <p className="mt-1 text-gray-900">
                      {selectedProspect.release_date 
                        ? new Date(selectedProspect.release_date).toLocaleDateString()
                        : 'N/A'}
                    </p>
                  </div>
                  <div>
                    <span className="font-medium text-gray-700">Award Date:</span>
                    <p className="mt-1 text-gray-900">
                      {selectedProspect.award_date 
                        ? new Date(selectedProspect.award_date).toLocaleDateString()
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

              {/* Extra Information */}
              {selectedProspect.extra && Object.keys(selectedProspect.extra).length > 0 && (
                <div>
                  <h3 className="text-lg font-semibold mb-3 text-gray-900">Additional Information</h3>
                  <div className="bg-gray-50 p-4 rounded-lg">
                    <pre className="text-sm text-gray-900 whitespace-pre-wrap font-mono">
                      {JSON.stringify(selectedProspect.extra, null, 2)}
                    </pre>
                  </div>
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
                        ? new Date(selectedProspect.loaded_at).toLocaleString()
                        : 'N/A'}
                    </p>
                  </div>
                  <div>
                    <span className="font-medium text-gray-700">ID:</span>
                    <p className="mt-1 text-gray-900 font-mono text-sm">{selectedProspect.id}</p>
                  </div>
                </div>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </PageLayout>
  );
} 