import React from 'react';
import { PageLayout } from './PageLayout';
import styles from './DataPageLayout.module.css'; // Import CSS module
import { Button } from '@/components/ui'; // Updated import

interface DataPageLayoutProps<T> {
  title: string;
  subtitle?: string;
  data: T | T[] | null;
  loading: boolean;
  error?: Error | null; // Make error optional
  onRefresh?: () => void; // Made optional as it wasn't always used
  emptyMessage?: string;
  renderHeader?: () => React.ReactNode;
  children: React.ReactNode; // Added children prop
  renderChildrenOnEmpty?: boolean; // New prop
}

export function DataPageLayout<T>({
  title,
  subtitle,
  data,
  loading,
  error,
  onRefresh,
  emptyMessage = 'No data available',
  renderHeader,
  children,
  renderChildrenOnEmpty = false // Default to false
}: DataPageLayoutProps<T>) {
  // Loading state
  if (loading && (!data || (Array.isArray(data) && data.length === 0))) {
    return (
      <PageLayout title={title} subtitle={subtitle}>
        {/* Apply loading styles */}
        <div className={styles.loadingContainer}>
          <div>Loading data...</div>
        </div>
      </PageLayout>
    );
  }

  // Error state
  if (error && (!data || (Array.isArray(data) && data.length === 0))) {
    return (
      <PageLayout title={title} subtitle={subtitle}>
        {/* Apply error box styles */}
        <div
          className={styles.errorBox} // Apply CSS module class
        >
          <h3 className={styles.errorTitle}>Error loading data</h3>
          <p>{error.message}</p>
          {onRefresh && (
            <Button // Replaced button
              variant="outline"
              onClick={onRefresh}
            >
              Retry
            </Button>
          )}
        </div>
      </PageLayout>
    );
  }

  // Empty state
  if (!renderChildrenOnEmpty && (!data || (Array.isArray(data) && data.length === 0))) {
    return (
      <PageLayout title={title} subtitle={subtitle}>
         {/* Apply empty box styles */}
        <div
          className={styles.emptyBox} // Apply CSS module class
        >
          <h3 className={styles.emptyTitle}>No data available</h3>
          <p>{emptyMessage}</p>
        </div>
        {onRefresh && (
          <Button // Replaced button
            variant="outline"
            onClick={onRefresh}
          >
            Refresh
          </Button>
        )}
      </PageLayout>
    );
  }

  // Main content
  return (
    <PageLayout title={title} subtitle={subtitle}>
      {/* Apply content spacing */}
      <div className={styles.contentWrapper}> {/* Use CSS module class */}
        {renderHeader && (
          // Apply header layout styles
          <div className={styles.headerWrapper}> {/* Use CSS module class */}
            {renderHeader()}
          </div>
        )}
        {children} {/* Replaced renderContent(data) with children */}
      </div>
    </PageLayout>
  );
} 