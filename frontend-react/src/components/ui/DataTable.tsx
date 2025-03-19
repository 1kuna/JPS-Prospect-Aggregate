import React, { useState, useCallback, useMemo, useEffect, useRef } from 'react';
import {
  Table,
  TableHeader,
  TableBody,
  TableFooter,
  TableHead,
  TableRow,
  TableCell,
  TableCaption,
} from './table';
import { Skeleton } from './skeleton';
import { Pagination } from './pagination';
import { FixedSizeList as List } from 'react-window';

export interface Column<T> {
  key: string;
  header: React.ReactNode;
  cell: (item: T, index: number) => React.ReactNode;
  sortable?: boolean;
  width?: string;
  align?: 'left' | 'center' | 'right';
  className?: string;
}

export interface DataTableProps<T> {
  /**
   * The data array to display in the table
   */
  data: T[];
  
  /**
   * Column definitions for the table
   */
  columns: Column<T>[];
  
  /**
   * Function to get a unique key for each row
   */
  rowKey: (item: T) => string | number;
  
  /**
   * Called when a row is clicked, makes the row clickable if provided
   */
  onRowClick?: (item: T) => void;
  
  /**
   * Currently sorted column key
   */
  sortColumn?: string;
  
  /**
   * Current sort direction
   */
  sortDirection?: 'asc' | 'desc';
  
  /**
   * Called when a sortable column header is clicked
   */
  onSort?: (column: string, direction: 'asc' | 'desc') => void;
  
  /**
   * Message to show when there is no data
   */
  emptyMessage?: React.ReactNode;
  
  /**
   * Whether the table is in a loading state
   */
  loading?: boolean;
  
  /**
   * Content to show in the table header area
   */
  headerContent?: React.ReactNode;
  
  /**
   * Content to show in the table footer area
   */
  footerContent?: React.ReactNode;
  
  /**
   * Caption for the table (accessibility)
   */
  caption?: string;
  
  /**
   * Additional CSS class
   */
  className?: string;
  
  /**
   * Whether to add zebra striping to rows
   */
  striped?: boolean;
  
  /**
   * Whether to add borders between rows
   */
  bordered?: boolean;
  
  /**
   * Whether to make the table compact
   */
  compact?: boolean;
  
  /**
   * Whether to add hover effect to rows
   */
  hover?: boolean;
  
  /**
   * Enable client-side pagination
   */
  pagination?: boolean;
  
  /**
   * Number of rows per page when pagination is enabled
   */
  pageSize?: number;
  
  /**
   * Current page number when pagination is enabled
   */
  currentPage?: number;
  
  /**
   * Total number of items (for server-side pagination)
   */
  totalItems?: number;
  
  /**
   * Function called when page changes (for server-side pagination)
   */
  onPageChange?: (page: number) => void;
  
  /**
   * Whether the table is sortable on the client side
   */
  clientSideSorting?: boolean;
  
  /**
   * Custom row renderer
   */
  renderRow?: (item: T, index: number, columns: Column<T>[]) => React.ReactNode;
  
  /**
   * Extra CSS classes to apply to rows
   */
  rowClassName?: string | ((item: T, index: number) => string);

  /**
   * Enable virtualization for better performance with large datasets
   */
  virtualized?: boolean;
  
  /**
   * Height of the virtualized table (required when virtualized=true)
   */
  height?: number;
  
  /**
   * Height of each row in the virtualized table
   */
  rowHeight?: number;
}

/**
 * Enhanced table component with sorting, loading states, pagination, and more
 */
export function DataTable<T>({
  data = [],
  columns = [],
  rowKey,
  onRowClick,
  sortColumn,
  sortDirection = 'asc',
  onSort,
  emptyMessage = 'No data available',
  loading = false,
  headerContent,
  footerContent,
  caption,
  className = '',
  striped = false,
  bordered = false,
  compact = false,
  hover = false,
  pagination = false,
  pageSize = 10,
  currentPage: externalCurrentPage,
  totalItems,
  onPageChange,
  clientSideSorting = false,
  renderRow,
  rowClassName = '',
  virtualized = false,
  height = 400,
  rowHeight = 45
}: DataTableProps<T>) {
  // Internal state for client-side pagination and sorting
  const [internalCurrentPage, setInternalCurrentPage] = useState(1);
  const [internalSortColumn, setInternalSortColumn] = useState<string | undefined>(sortColumn);
  const [internalSortDirection, setInternalSortDirection] = useState<'asc' | 'desc'>(sortDirection);
  
  // Reference to the table container element for measuring
  const tableContainerRef = useRef<HTMLDivElement>(null);
  
  // Use external page if provided, otherwise use internal
  const currentPage = externalCurrentPage !== undefined ? externalCurrentPage : internalCurrentPage;
  
  // Update internal state when props change
  useEffect(() => {
    if (sortColumn !== undefined) {
      setInternalSortColumn(sortColumn);
    }
    if (sortDirection !== undefined) {
      setInternalSortDirection(sortDirection);
    }
  }, [sortColumn, sortDirection]);
  
  // Handle sorting
  const handleHeaderClick = useCallback((columnKey: string, sortable?: boolean) => {
    if (!sortable) return;
    
    // Toggle direction if same column, otherwise default to asc
    const newDirection = 
      (clientSideSorting ? internalSortColumn : sortColumn) === columnKey && 
      (clientSideSorting ? internalSortDirection : sortDirection) === 'asc' 
        ? 'desc' 
        : 'asc';
    
    if (clientSideSorting) {
      setInternalSortColumn(columnKey);
      setInternalSortDirection(newDirection);
    } else if (onSort) {
      onSort(columnKey, newDirection);
    }
  }, [clientSideSorting, internalSortColumn, internalSortDirection, sortColumn, sortDirection, onSort]);
  
  // Generate sort indicators
  const getSortIndicator = useCallback((columnKey: string) => {
    const activeColumn = clientSideSorting ? internalSortColumn : sortColumn;
    const activeDirection = clientSideSorting ? internalSortDirection : sortDirection;
    
    if (activeColumn !== columnKey) return null;
    
    return (
      <span className="ml-1 inline-block">
        {activeDirection === 'asc' ? '↑' : '↓'}
      </span>
    );
  }, [clientSideSorting, internalSortColumn, internalSortDirection, sortColumn, sortDirection]);
  
  // Handle pagination
  const handlePageChange = useCallback((page: number) => {
    if (onPageChange) {
      onPageChange(page);
    } else {
      setInternalCurrentPage(page);
    }
  }, [onPageChange]);
  
  // Sort data if client-side sorting is enabled
  const sortedData = useMemo(() => {
    if (!clientSideSorting || !internalSortColumn) return data;
    
    return [...data].sort((a: any, b: any) => {
      const aValue = a[internalSortColumn];
      const bValue = b[internalSortColumn];
      
      if (aValue === bValue) return 0;
      
      // Handle different types of values
      if (typeof aValue === 'string' && typeof bValue === 'string') {
        return internalSortDirection === 'asc'
          ? aValue.localeCompare(bValue)
          : bValue.localeCompare(aValue);
      }
      
      if (aValue instanceof Date && bValue instanceof Date) {
        return internalSortDirection === 'asc'
          ? aValue.getTime() - bValue.getTime()
          : bValue.getTime() - aValue.getTime();
      }
      
      // Default to numeric comparison
      return internalSortDirection === 'asc'
        ? (aValue > bValue ? 1 : -1)
        : (aValue < bValue ? 1 : -1);
    });
  }, [data, clientSideSorting, internalSortColumn, internalSortDirection]);
  
  // Apply pagination if enabled
  const paginatedData = useMemo(() => {
    if (!pagination) return sortedData;
    
    const startIndex = (currentPage - 1) * pageSize;
    return sortedData.slice(startIndex, startIndex + pageSize);
  }, [sortedData, pagination, currentPage, pageSize]);
  
  // Calculate total pages for client-side pagination
  const totalPages = useMemo(() => {
    if (totalItems !== undefined) {
      return Math.ceil(totalItems / pageSize);
    }
    return Math.ceil(sortedData.length / pageSize);
  }, [totalItems, sortedData.length, pageSize]);
  
  // Get row class name
  const getRowClassName = useCallback((item: T, index: number) => {
    let className = '';
    
    if (striped && index % 2 === 1) {
      className += ' bg-gray-50';
    }
    
    if (bordered) {
      className += ' border-b border-gray-200';
    }
    
    if (compact) {
      className += ' h-9';
    } else {
      className += ' h-12';
    }
    
    if (hover) {
      className += ' hover:bg-gray-100';
    }
    
    if (onRowClick) {
      className += ' cursor-pointer';
    }
    
    if (typeof rowClassName === 'function') {
      className += ` ${rowClassName(item, index)}`;
    } else if (rowClassName) {
      className += ` ${rowClassName}`;
    }
    
    return className.trim();
  }, [striped, bordered, compact, hover, onRowClick, rowClassName]);
  
  // Render a single row
  const renderTableRow = useCallback((item: T, index: number) => {
    if (renderRow) {
      return renderRow(item, index, columns);
    }
    
    return (
      <TableRow
        key={rowKey(item)}
        className={getRowClassName(item, index)}
        onClick={onRowClick ? () => onRowClick(item) : undefined}
      >
        {columns.map(column => (
          <TableCell 
            key={column.key} 
            className={column.className}
            style={{ textAlign: column.align || 'left' }}
          >
            {column.cell(item, index)}
          </TableCell>
        ))}
      </TableRow>
    );
  }, [columns, rowKey, getRowClassName, onRowClick, renderRow]);
  
  // Virtualized row renderer
  const VirtualRow = useCallback(
    ({ index, style }: { index: number; style: React.CSSProperties }) => {
      const item = paginatedData[index];
      return (
        <div style={style} className="flex w-full">
          <TableRow
            className={`w-full flex ${getRowClassName(item, index)}`}
            onClick={onRowClick ? () => onRowClick(item) : undefined}
          >
            {columns.map(column => (
              <TableCell 
                key={column.key} 
                className={`flex-1 ${column.width ? '' : 'flex-grow'} ${column.className || ''}`}
                style={{ 
                  textAlign: column.align || 'left',
                  width: column.width,
                  display: 'flex',
                  alignItems: 'center'
                }}
              >
                {column.cell(item, index)}
              </TableCell>
            ))}
          </TableRow>
        </div>
      );
    },
    [paginatedData, columns, getRowClassName, onRowClick]
  );
  
  // If data is loading, display skeleton loader
  if (loading) {
    return (
      <div className={`w-full overflow-auto ${className}`}>
        {headerContent && <div className="mb-4">{headerContent}</div>}
        
        <div className="w-full">
          <div className="border rounded-md mb-4">
            <div className="p-4 space-y-4">
              {Array.from({ length: 5 }).map((_, i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          </div>
        </div>
        
        {footerContent && <div className="mt-4">{footerContent}</div>}
      </div>
    );
  }
  
  // If no data, display empty message
  if (paginatedData.length === 0) {
    return (
      <div className={`w-full overflow-auto ${className}`}>
        {headerContent && <div className="mb-4">{headerContent}</div>}
        
        <div className="border rounded-md p-8 text-center">
          {emptyMessage}
        </div>
        
        {footerContent && <div className="mt-4">{footerContent}</div>}
      </div>
    );
  }
  
  // Render standard table or virtualized table based on the prop
  return (
    <div className={`w-full ${className}`} ref={tableContainerRef}>
      {headerContent && <div className="mb-4">{headerContent}</div>}
      
      {virtualized ? (
        // Virtualized table for better performance with large datasets
        <div className="border rounded-md overflow-hidden">
          <div className="bg-gray-50 px-4 py-3 border-b">
            <div className="flex w-full">
              {columns.map(column => (
                <div 
                  key={column.key}
                  className={`px-3 py-2 text-left text-sm font-medium text-gray-500 flex-1 ${column.width ? '' : 'flex-grow'} ${column.sortable ? 'cursor-pointer' : ''}`}
                  style={{ 
                    textAlign: column.align || 'left',
                    width: column.width 
                  }}
                  onClick={() => column.sortable && handleHeaderClick(column.key, column.sortable)}
                >
                  {column.header}
                  {getSortIndicator(column.key)}
                </div>
              ))}
            </div>
          </div>
          
          <List
            height={height}
            itemCount={paginatedData.length}
            itemSize={rowHeight}
            width="100%"
          >
            {VirtualRow}
          </List>
        </div>
      ) : (
        // Standard table for smaller datasets
        <div className="border rounded-md overflow-x-auto">
          <Table>
            {caption && <TableCaption>{caption}</TableCaption>}
            
            <TableHeader>
              <TableRow>
                {columns.map(column => (
                  <TableHead 
                    key={column.key}
                    className={`${column.sortable ? 'cursor-pointer' : ''} ${column.className || ''}`}
                    style={{ 
                      textAlign: column.align || 'left',
                      width: column.width 
                    }}
                    onClick={() => column.sortable && handleHeaderClick(column.key, column.sortable)}
                  >
                    {column.header}
                    {getSortIndicator(column.key)}
                  </TableHead>
                ))}
              </TableRow>
            </TableHeader>
            
            <TableBody>
              {paginatedData.map((item, index) => renderTableRow(item, index))}
            </TableBody>
            
            {pagination && totalPages > 1 && (
              <TableFooter>
                <TableRow>
                  <TableCell colSpan={columns.length}>
                    <div className="flex justify-end mt-4">
                      <Pagination
                        currentPage={currentPage}
                        totalPages={totalPages}
                        onPageChange={handlePageChange}
                      />
                    </div>
                  </TableCell>
                </TableRow>
              </TableFooter>
            )}
          </Table>
        </div>
      )}
      
      {/* Pagination outside of table */}
      {pagination && totalPages > 1 && !virtualized && (
        <div className="flex justify-end mt-4">
          <Pagination
            currentPage={currentPage}
            totalPages={totalPages}
            onPageChange={handlePageChange}
          />
        </div>
      )}
      
      {footerContent && <div className="mt-4">{footerContent}</div>}
    </div>
  );
} 