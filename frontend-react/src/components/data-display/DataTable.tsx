import React from 'react';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Pagination, PaginationContent, PaginationItem, PaginationLink, PaginationNext, PaginationPrevious } from '@/components/ui/pagination';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Alert, AlertTitle, AlertDescription } from '@/components/ui/alert';

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
  isLoading?: boolean;
  emptyMessage?: {
    title: string;
    description: string;
  };
}

export function DataTable<T>({
  title,
  description,
  data,
  columns,
  keyField,
  pagination,
  onPageChange,
  isLoading = false,
  emptyMessage = { title: 'No data found', description: 'There are no items to display.' },
}: DataTableProps<T>) {
  const handlePageChange = (page: number) => {
    if (onPageChange) {
      onPageChange(page);
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
      <div className="rounded-md border">
        <Table>
          <TableHeader>
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
            {data.map((item) => (
              <TableRow key={String(item[keyField])}>
                {columns.map((column, index) => (
                  <TableCell key={index} className={column.className}>
                    {renderCell(item, column)}
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      {/* Pagination */}
      {pagination && pagination.totalPages > 1 && (
        <div className="flex justify-center mt-4">
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

  // If no title is provided, just return the table content
  if (!title) {
    return content;
  }

  // Otherwise, wrap in a card
  return (
    <Card className="mb-6">
      {title && (
        <CardHeader>
          <CardTitle>{title}</CardTitle>
          {description && <CardDescription>{description}</CardDescription>}
        </CardHeader>
      )}
      <CardContent>
        {content}
      </CardContent>
    </Card>
  );
} 