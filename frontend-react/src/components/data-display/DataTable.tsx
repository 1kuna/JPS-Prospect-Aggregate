import React from 'react';
import {
  Table,
  TableBody,
  TableCell,
  TableRow,
} from '@/components/ui';
import { Pagination, PaginationContent, PaginationItem, PaginationNext, PaginationPrevious } from '@/components/ui/pagination';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertTitle } from '@/components/ui/alert';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

export interface Column<T> {
  header: string;
  accessorKey: keyof T | ((row: T) => any);
  cell?: (row: T) => React.ReactNode;
  className?: string;
  onClick?: () => void;
}

interface PaginationInfo {
  page: number;
  perPage: number;
  totalPages: number;
  totalItems?: number;
}

interface DataTableProps<T> {
  title?: string;
  description?: string;
  data: T[];
  columns: Column<T>[];
  pagination?: PaginationInfo;
  onPageChange?: (page: number) => void;
  onPerPageChange?: (perPage: number) => void;
  isLoading?: boolean;
  emptyMessage?: string;
  maxHeight?: string;
}

export function DataTable<T>({
  title,
  description,
  data,
  columns,
  pagination,
  onPageChange,
  onPerPageChange,
  isLoading = false,
  emptyMessage = 'No data available',
  maxHeight = '500px',
}: DataTableProps<T>) {
  const handlePageChange = (page: number) => {
    if (onPageChange) {
      onPageChange(page);
    }
  };

  const handlePerPageChange = (value: string) => {
    if (onPerPageChange) {
      onPerPageChange(Number(value));
    }
  };

  const getValue = (row: T, column: Column<T>) => {
    if (typeof column.accessorKey === 'function') {
      return column.accessorKey(row);
    }
    return row[column.accessorKey];
  };

  // Calculate column widths
  const columnWidths = columns.map(() => {
    // Distribute width evenly or use custom widths if needed
    return `${100 / columns.length}%`;
  });

  const tableContent = (
    <>
      {description && (
        <div className="text-sm text-muted-foreground mb-2">
          {description}
        </div>
      )}
      <div className="rounded-md border">
        <div className="relative">
          <div className="sticky top-0 z-20 bg-blue-900 w-full shadow-md">
            <table className="w-full border-collapse">
              <thead>
                <tr>
                  {columns.map((column, index) => (
                    <th 
                      key={index} 
                      className="text-white font-semibold text-left p-4"
                      onClick={column.onClick}
                      style={{
                        width: columnWidths[index],
                        ...(column.onClick ? { cursor: 'pointer' } : {})
                      }}
                    >
                      {column.header}
                    </th>
                  ))}
                </tr>
              </thead>
            </table>
          </div>
          <div style={{ maxHeight, overflowY: 'auto' }}>
            <Table>
              <TableBody>
                {isLoading ? (
                  <TableRow>
                    <TableCell colSpan={columns.length} className="h-24 text-center">
                      Loading data...
                    </TableCell>
                  </TableRow>
                ) : data.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={columns.length} className="h-24 text-center">
                      <div className="flex flex-col items-center justify-center">
                        <h3 className="font-medium">{emptyMessage}</h3>
                      </div>
                    </TableCell>
                  </TableRow>
                ) : (
                  data.map((row, rowIndex) => (
                    <TableRow key={rowIndex}>
                      {columns.map((column, colIndex) => (
                        <TableCell 
                          key={colIndex} 
                          className={column.className}
                          style={{ width: columnWidths[colIndex] }}
                        >
                          {column.cell ? column.cell(row) : getValue(row, column)}
                        </TableCell>
                      ))}
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
        </div>
      </div>

      {/* Pagination and Per Page Controls */}
      {pagination && (
        <div className="grid grid-cols-1 md:grid-cols-3 items-center gap-4 mt-4">
          <div className="flex items-center gap-2 justify-start">
            <span className="text-sm text-muted-foreground">Rows per page:</span>
            <Select
              value={String(pagination.perPage)}
              onValueChange={handlePerPageChange}
              defaultValue={String(pagination.perPage)}
            >
              <SelectTrigger className="w-[80px] h-8 bg-white dark:bg-slate-800 text-black dark:text-white border">
                <SelectValue>{pagination.perPage}</SelectValue>
              </SelectTrigger>
              <SelectContent className="bg-white dark:bg-slate-800 text-black dark:text-white border shadow-md rounded-md">
                <SelectItem value="10" className="text-black dark:text-white hover:bg-gray-100 dark:hover:bg-slate-700">10</SelectItem>
                <SelectItem value="20" className="text-black dark:text-white hover:bg-gray-100 dark:hover:bg-slate-700">20</SelectItem>
                <SelectItem value="50" className="text-black dark:text-white hover:bg-gray-100 dark:hover:bg-slate-700">50</SelectItem>
              </SelectContent>
            </Select>
          </div>
          
          <div className="flex justify-center">
            <Pagination>
              <PaginationContent>
                <PaginationItem>
                  <PaginationPrevious
                    onClick={() => handlePageChange(Math.max(1, pagination.page - 1))}
                    className={`${pagination.page <= 1 ? 'pointer-events-none opacity-50' : 'cursor-pointer'} bg-white dark:bg-slate-800 text-black dark:text-white`}
                  />
                </PaginationItem>

                <PaginationItem>
                  <span className="flex items-center justify-center px-3 h-9 bg-white dark:bg-slate-800 text-black dark:text-white border rounded-md mx-1">
                    Page {pagination.page} of {pagination.totalPages}
                  </span>
                </PaginationItem>

                <PaginationItem>
                  <PaginationNext
                    onClick={() => handlePageChange(Math.min(pagination.totalPages, pagination.page + 1))}
                    className={`${pagination.page >= pagination.totalPages ? 'pointer-events-none opacity-50' : 'cursor-pointer'} bg-white dark:bg-slate-800 text-black dark:text-white`}
                  />
                </PaginationItem>
              </PaginationContent>
            </Pagination>
          </div>
          
          {pagination.totalItems ? (
            <div className="text-sm text-muted-foreground text-right">
              {(pagination.page - 1) * pagination.perPage + 1}-
              {Math.min(pagination.page * pagination.perPage, pagination.totalItems)} of {pagination.totalItems}
            </div>
          ) : (
            <div></div> // Empty div to maintain the grid layout
          )}
        </div>
      )}
    </>
  );

  const emptyState = (
    <Alert>
      <AlertTitle>{emptyMessage}</AlertTitle>
    </Alert>
  );

  const content = data.length > 0 ? tableContent : emptyState;

  // If no title is provided, just return the table content directly
  if (!title) {
    return content;
  }

  // Otherwise, wrap in a card with title
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent>
        {content}
      </CardContent>
    </Card>
  );
} 