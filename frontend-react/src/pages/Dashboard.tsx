import { PageLayout } from '@/components/layout';
import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { createColumnHelper, flexRender, getCoreRowModel, useReactTable } from '@tanstack/react-table';
import { useState } from 'react';
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
import {
  Pagination,
  PaginationContent,
  PaginationEllipsis,
  PaginationItem,
  PaginationLink,
  PaginationNext,
  PaginationPrevious,
} from "@/components/ui/pagination";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

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

const fetchProspects = async (page: number, limit: number): Promise<{ data: Prospect[], total: number, totalPages: number }> => {
  console.log('Fetching prospects from:', `/api/prospects?page=${page}&limit=${limit}`);
  
  try {
    const response = await fetch(`/api/prospects?page=${page}&limit=${limit}`);
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
  columnHelper.accessor((row) => row.extra?.summary || row.title, {
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
    cell: info => info.getValue() ?? 'N/A',
    size: 200,
  }),
  columnHelper.accessor('naics', {
    header: 'NAICS',
    cell: info => info.getValue() ?? 'N/A',
    size: 120,
  }),
  columnHelper.accessor((row) => row.extra?.acquisition_phase || row.contract_type, {
    id: 'status',
    header: 'Status',
    cell: info => info.getValue() ?? 'N/A',
    size: 150,
  }),
];

export default function Dashboard() {
  console.log('Dashboard component loaded!');
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage, setItemsPerPage] = useState(10); // Default items per page

  // const { data: countData, isLoading: isLoadingCount } = useQuery({
  //   queryKey: ['prospectCount'],
  //   queryFn: fetchProspectCount,
  // });

  console.log('About to call useQuery with:', { currentPage, itemsPerPage });
  
  const { data: prospectsData, isLoading: isLoadingProspects, isFetching: isFetchingProspects } = useQuery({
    queryKey: ['prospects', currentPage, itemsPerPage],
    queryFn: () => fetchProspects(currentPage, itemsPerPage),
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
    setCurrentPage(1); // Reset to first page
  };
  
  const renderPaginationItems = () => {
    const pageItems = [];
    const SPREAD = 2; // Number of pages to show on each side of current page

    if (totalPages <= 1) return null; // No pagination needed for 1 or 0 pages

    // Previous Button
    pageItems.push(
      <PaginationItem key="prev">
        <Button
          variant="outline"
          size="sm"
          onClick={handlePreviousPage}
          disabled={currentPage === 1}
          className="h-9 px-3"
        >
          <PaginationPrevious className="h-4 w-4 mr-1" /> 
        </Button>
      </PaginationItem>
    );

    // Page numbers logic
    if (totalPages <= 5) { // Show all pages if 5 or less
      for (let i = 1; i <= totalPages; i++) {
        pageItems.push(
          <PaginationItem key={i}>
            <PaginationLink href="#" isActive={currentPage === i} onClick={(e) => { e.preventDefault(); handlePageChange(i);}} className="w-9 h-9 flex items-center justify-center">
              {i}
            </PaginationLink>
          </PaginationItem>
        );
      }
    } else {
      // First page
      pageItems.push(
        <PaginationItem key={1}>
          <PaginationLink href="#" isActive={currentPage === 1} onClick={(e) => { e.preventDefault(); handlePageChange(1);}} className="w-9 h-9 flex items-center justify-center">1</PaginationLink>
        </PaginationItem>
      );

      // Ellipsis or pages after first page
      if (currentPage > SPREAD + 1) {
        pageItems.push(<PaginationItem key="start-ellipsis"><PaginationEllipsis /></PaginationItem>);
      }

      let startPage = Math.max(2, currentPage - SPREAD + (currentPage === totalPages - SPREAD +1 ? 1:0) + (currentPage === SPREAD+2 && totalPages > 5 ? -1:0) );
      let endPage = Math.min(totalPages - 1, currentPage + SPREAD - (currentPage === SPREAD ? 1:0) - (currentPage === totalPages-(SPREAD+1) && totalPages > 5 ? -1:0));

      // Adjust window if near the beginning
       if (currentPage <= SPREAD ) {
           endPage = Math.min(totalPages -1, SPREAD * 2 +1 );
       }
       // Adjust window if near the end
       if (currentPage >= totalPages - SPREAD +1 ){
           startPage = Math.max(2, totalPages - SPREAD * 2 );
       }


      for (let i = startPage; i <= endPage; i++) {
        pageItems.push(
          <PaginationItem key={i}>
            <PaginationLink href="#" isActive={currentPage === i} onClick={(e) => { e.preventDefault(); handlePageChange(i);}} className="w-9 h-9 flex items-center justify-center">
              {i}
            </PaginationLink>
          </PaginationItem>
        );
      }

      // Ellipsis or pages before last page
      if (currentPage < totalPages - SPREAD) {
        pageItems.push(<PaginationItem key="end-ellipsis"><PaginationEllipsis /></PaginationItem>);
      }

      // Last page
      pageItems.push(
        <PaginationItem key={totalPages}>
          <PaginationLink href="#" isActive={currentPage === totalPages} onClick={(e) => { e.preventDefault(); handlePageChange(totalPages);}} className="w-9 h-9 flex items-center justify-center">{totalPages}</PaginationLink>
        </PaginationItem>
      );
    }

    // Next Button
    pageItems.push(
      <PaginationItem key="next">
        <Button
          variant="outline"
          size="sm"
          onClick={handleNextPage}
          disabled={currentPage === totalPages}
          className="h-9 px-3"
        >
          <PaginationNext className="h-4 w-4 ml-1" />
        </Button>
      </PaginationItem>
    );

    return pageItems;
  };

  return (
    <PageLayout
      title="Dashboard"
      subtitle="Overview of your data collection system"
    >
      {/* Flex container for main content and statistics */}
      <div className="flex justify-between items-start gap-6">
        {/* Prospects List Card - Main content (allow to grow) */}
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
                    <Table className="min-w-full divide-y divide-gray-200">
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
                            className={`transition-colors duration-150 ease-in-out hover:bg-gray-100 ${rowIndex % 2 === 0 ? 'bg-white' : 'bg-gray-50/50'} data-[state=selected]:bg-blue-50 data-[state=selected]:hover:bg-blue-100`}
                          >
                            {row.getVisibleCells().map(cell => (
                              <TableCell 
                                key={cell.id} 
                                className="px-6 py-4 whitespace-nowrap text-sm text-gray-800 align-top"
                                style={{ width: cell.column.getSize() !== 0 ? cell.column.getSize() : undefined }}
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
                    <div className="mt-6 flex flex-col sm:flex-row items-center justify-between space-y-4 sm:space-y-0">
                       <p className="text-sm font-medium text-gray-700">
                          Showing <span className="font-semibold">{prospectsData.data.length}</span> of <span className="font-semibold">{prospectsData?.total.toLocaleString()}</span> results
                       </p>
                      <Pagination>
                        <PaginationContent>
                          {renderPaginationItems() }
                        </PaginationContent>
                      </Pagination>
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

        {/* Prospect Statistics Card - Positioned to the right, smaller */}
        <div className="w-64 flex-shrink-0">
          <Card> {/* Removed shadow-lg to make it less prominent */} 
            <CardHeader className="pb-2 pt-0"> {/* Adjusted padding */}
              <CardTitle className="text-base font-semibold text-black">Prospect Statistics</CardTitle> {/* Smaller title */} 
            </CardHeader>
            <CardContent className="pt-2 pb-4"> {/* Adjusted padding */}
              {/* {isLoadingCount ? ( */}
              {isLoadingProspects ? ( // Use isLoadingProspects as count will come from prospectsData
                <p className="text-gray-600 animate-pulse text-sm">Loading...</p>
              ) : (
                // <p className="text-xl font-semibold text-blue-600">{countData?.count.toLocaleString()}</p> /* Smaller number */ 
                <p className="text-xl font-semibold text-blue-600">{prospectsData?.total.toLocaleString()}</p>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </PageLayout>
  );
} 