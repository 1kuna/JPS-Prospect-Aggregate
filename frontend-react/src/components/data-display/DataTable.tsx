import React from 'react';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Pagination, PaginationContent, PaginationItem, PaginationLink, PaginationNext, PaginationPrevious } from '@/components/ui/pagination';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertTitle, AlertDescription } from '@/components/ui/alert';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

interface Column<T> {
  header: string;
  accessor: keyof T | ((item: T) => React.ReactNode);
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
  keyField: keyof T;
  pagination?: PaginationInfo;
  onPageChange?: (page: number) => void;
  onPerPageChange?: (perPage: number) => void;
  isLoading?: boolean;
  emptyMessage?: {
    title: string;
    description: string;
  };
  maxHeight?: string;
}

export function DataTable<T>({
  title,
  description,
  data,
  columns,
  keyField,
  pagination,
  onPageChange,
  onPerPageChange,
  isLoading = false,
  emptyMessage = { title: 'No data found', description: 'There are no items to display.' },
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

  const renderCell = (item: T, column: Column<T>) => {
    if (typeof column.accessor === 'function') {
      return column.accessor(item);
    }
    return item[column.accessor] as React.ReactNode;
  };

  const tableContent = (
    <>
      {description && (
        <div className="text-sm text-muted-foreground mb-2">
          {description}
        </div>
      )}
      <div className="rounded-md border">
        <div style={{ maxHeight, overflowY: 'auto' }}>
          <Table>
            <TableHeader className="sticky top-0 bg-background z-10">
              <TableRow>
                {columns.map((column, index) => (
                  <TableHead 
                    key={index} 
                    className={column.className}
                    onClick={column.onClick}
                    style={column.onClick ? { cursor: 'pointer' } : undefined}
                  >
                    {column.header}
                  </TableHead>
                ))}
              </TableRow>
            </TableHeader>
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
                      <h3 className="font-medium">{emptyMessage.title}</h3>
                      <p className="text-sm text-muted-foreground">{emptyMessage.description}</p>
                    </div>
                  </TableCell>
                </TableRow>
              ) : (
                data.map((item) => (
                  <TableRow key={String(item[keyField])}>
                    {columns.map((column, index) => (
                      <TableCell key={index} className={column.className}>
                        {renderCell(item, column)}
                      </TableCell>
                    ))}
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>
      </div>

      {/* Pagination and Per Page Controls */}
      {pagination && pagination.totalPages > 0 && (
        <div className="flex items-center justify-between mt-4">
          <div className="flex items-center gap-2">
            <span className="text-sm text-muted-foreground">Rows per page:</span>
            <Select
              value={String(pagination.perPage)}
              onValueChange={handlePerPageChange}
            >
              <SelectTrigger className="w-[80px] h-8">
                <SelectValue placeholder={pagination.perPage} />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="10">10</SelectItem>
                <SelectItem value="25">25</SelectItem>
                <SelectItem value="50">50</SelectItem>
                <SelectItem value="100">100</SelectItem>
              </SelectContent>
            </Select>
          </div>
          
          <Pagination>
            <PaginationContent>
              <PaginationItem>
                <PaginationPrevious
                  onClick={() => handlePageChange(Math.max(1, pagination.page - 1))}
                  className={pagination.page <= 1 ? 'pointer-events-none opacity-50' : 'cursor-pointer'}
                />
              </PaginationItem>

              {Array.from({ length: Math.min(5, pagination.totalPages) }, (_, i) => {
                // Show pages around the current page
                let pageToShow;
                if (pagination.totalPages <= 5) {
                  pageToShow = i + 1;
                } else {
                  const startPage = Math.max(1, pagination.page - 2);
                  pageToShow = startPage + i;
                  if (pageToShow > pagination.totalPages) {
                    return null;
                  }
                }

                return (
                  <PaginationItem key={pageToShow}>
                    <PaginationLink
                      onClick={() => handlePageChange(pageToShow)}
                      isActive={pageToShow === pagination.page}
                    >
                      {pageToShow}
                    </PaginationLink>
                  </PaginationItem>
                );
              })}

              <PaginationItem>
                <PaginationNext
                  onClick={() => handlePageChange(Math.min(pagination.totalPages, pagination.page + 1))}
                  className={pagination.page >= pagination.totalPages ? 'pointer-events-none opacity-50' : 'cursor-pointer'}
                />
              </PaginationItem>
            </PaginationContent>
          </Pagination>
          
          {pagination.totalItems && (
            <div className="text-sm text-muted-foreground">
              {(pagination.page - 1) * pagination.perPage + 1}-
              {Math.min(pagination.page * pagination.perPage, pagination.totalItems)} of {pagination.totalItems}
            </div>
          )}
        </div>
      )}
    </>
  );

  const emptyState = (
    <Alert>
      <AlertTitle>{emptyMessage.title}</AlertTitle>
      <AlertDescription>{emptyMessage.description}</AlertDescription>
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