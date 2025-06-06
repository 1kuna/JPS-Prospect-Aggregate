import React from 'react';
import styles from './DataTable.module.css'; // Import CSS module
import { Button } from '@/components/ui'; // Import Button using barrel file

// Define a generic Column type for TanStack Table
export interface Column<TData> {
  accessorKey: keyof TData | string; // Revert accessorKey type
  header: string;
  cell?: (info: { row: TData }) => React.ReactNode; // Correct cell prop type
  className?: string; // Add back className
  onClick?: () => void; // Add back onClick for header
  // Add other TanStack Table column options as needed
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

  const getValue = (row: T, accessorKey: Column<T>['accessorKey']) => {
    if (typeof accessorKey === 'function') {
      // This case shouldn't happen based on current interface, but safe guard
      return 'N/A'; // Or handle appropriately
    }
    // Basic nested accessor support (e.g., 'dataSource.name')
    if (typeof accessorKey === 'string' && accessorKey.includes('.')) {
      return accessorKey.split('.').reduce((obj: any, key) => obj?.[key], row);
    }
    // Handle string that is not nested and is keyof T
    if (typeof accessorKey === 'string') {
        return row[accessorKey as keyof T];
    }
    // This path might be unreachable if accessorKey is always string or keyof T
    return 'Invalid Key'; 
  };

  // Calculate column widths (basic even distribution)
  const columnWidths = columns.map(() => `${100 / columns.length}%`);

  const tableContent = (
    <>
      {description && (
        <div className={styles.description}>{description}</div>
      )}
      {/* Apply outer border/rounding */}
      <div className={styles.tableOuterWrapper}>
        <div className="relative"> {/* Keep relative for sticky positioning */}
          {/* Sticky Header */}
          <div className={styles.stickyHeaderWrapper}>
            <table className={styles.tableBase}>
              <colgroup>
                 {columnWidths.map((width, index) => (
                    <col key={index} style={{ width }} />
                 ))}
              </colgroup>
              <thead>
                <tr>
                  {columns.map((column, index) => (
                    <th
                      key={index}
                      className={`${styles.tableHeaderCell} ${column.onClick ? styles.clickableHeader : ''}`}
                      onClick={column.onClick}
                      // style removed, handled by colgroup
                    >
                      {column.header}
                    </th>
                  ))}
                </tr>
              </thead>
            </table>
          </div>
          {/* Scrollable Body */}
          <div style={{ maxHeight: maxHeight, overflowY: 'auto' }}>
            <table className={`${styles.tableBase} ${styles.tableBody}`}>
              <colgroup>
                 {columnWidths.map((width, index) => (
                    <col key={index} style={{ width }} />
                 ))}
              </colgroup>
              <tbody>
                {isLoading ? (
                  <tr>
                    <td colSpan={columns.length} className={styles.loadingCell}>
                      Loading data...
                    </td>
                  </tr>
                ) : data.length === 0 ? (
                  <tr>
                    <td colSpan={columns.length} className={styles.emptyCell}>
                      <div className={styles.emptyCellContent}>
                        <h3 className={styles.emptyMessageText}>{emptyMessage}</h3>
                      </div>
                    </td>
                  </tr>
                ) : (
                  data.map((row, rowIndex) => (
                    <tr key={rowIndex} className={styles.tableRow}>
                      {columns.map((column, colIndex) => (
                        <td
                          key={colIndex}
                           // Combine module styles with any passed className
                          className={`${styles.tableBodyCell} ${column.className || ''}`}
                          // style removed, handled by colgroup
                        >
                          {column.cell ? column.cell({ row }) : getValue(row, column.accessorKey)}
                        </td>
                      ))}
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Pagination Controls */}
      {pagination && (
        <div className={styles.paginationWrapper}>
          {/* Rows Per Page */}
          <div className={styles.rowsPerPageWrapper}>
            <label htmlFor="rows-per-page" className={styles.mutedText}>Rows per page:</label>
            <select
              id="rows-per-page"
              value={String(pagination.perPage)}
              onChange={(e) => handlePerPageChange(e.target.value)}
              className={styles.selectInput}
            >
              {[10, 20, 50].map(size => <option key={size} value={size}>{size}</option>)}
            </select>
          </div>

          {/* Page Navigation */}
          <div className={styles.pageNavWrapper}>
            <div className={styles.pageNavInner}>
                <Button // Replaced button
                  variant="outline"
                  onClick={() => handlePageChange(Math.max(1, pagination.page - 1))}
                  disabled={pagination.page <= 1}
                >
                  Previous
                </Button>
                <span className={styles.pageInfo}>
                    Page {pagination.page} of {pagination.totalPages}
                </span>
                <Button // Replaced button
                  variant="outline"
                  onClick={() => handlePageChange(Math.min(pagination.totalPages, pagination.page + 1))}
                  disabled={pagination.page >= pagination.totalPages}
                >
                  Next
                </Button>
            </div>
          </div>

          {/* Total Items Info */}
          {pagination.totalItems != null ? ( // Check for null/undefined explicitly
            <div className={`${styles.mutedText} ${styles.totalItems}`}>
              {(pagination.page - 1) * pagination.perPage + 1}-
              {Math.min(pagination.page * pagination.perPage, pagination.totalItems)} of {pagination.totalItems}
            </div>
          ) : (
            <div></div> // Placeholder for grid alignment
          )}
        </div>
      )}
    </>
  );

  // Handle case where data is empty but not loading (simplified empty state)
  // Original emptyState rendering was slightly complex with title logic
  if (!isLoading && data.length === 0 && !title) {
      return (
          <div className={styles.simpleEmptyState}>
              {emptyMessage}
          </div>
      );
  }

  // If no title, return table content (or loading/empty state handled within)
  if (!title) {
    return tableContent;
  }

  // Wrap in Card if title exists
  return (
    <div className={styles.cardWrapper}>
      <div className={styles.cardHeader}>
        <h3 className={styles.cardTitle}>{title}</h3>
      </div>
      <div className={styles.cardContent}>
        {/* Render table content (handles its own loading/empty states) */}
        {tableContent}
      </div>
    </div>
  );
} 