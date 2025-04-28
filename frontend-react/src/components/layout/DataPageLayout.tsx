import React from 'react';
import { PageLayout } from './PageLayout';
import styles from './DataPageLayout.module.css'; // Import CSS module

interface DataPageLayoutProps<T> {
  title: string;
  subtitle?: string;
  data: T | T[] | null;
  loading: boolean;
  error?: Error | null; // Make error optional
  onRefresh?: () => void; // Made optional as it wasn't always used
  emptyMessage?: string;
  renderHeader?: () => React.ReactNode;
  renderContent: (data: T | T[]) => React.ReactNode;
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
  renderContent
}: DataPageLayoutProps<T>) {
  // Loading state
  if (loading && (!data || (Array.isArray(data) && data.length === 0))) {
    return (
      <PageLayout title={title} subtitle={subtitle} isLoading={true}>
        {/* Apply loading styles */}
        <div className={styles.loadingContainer}>
          <div>Loading data...</div> {/* Replaced Spinner */}
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
          <h3 className={styles.errorTitle}>Error loading data</h3> {/* Apply CSS module class & remove inline style */}
          <p>{error.message}</p> {/* Replaced AlertDescription */}
          {onRefresh && (
            <button // Replaced Button
              className={styles.actionButton} // Apply button styles
              onClick={onRefresh}
            >
              Retry
            </button>
          )}
        </div>
      </PageLayout>
    );
  }

  // Empty state
  if (!data || (Array.isArray(data) && data.length === 0)) {
    return (
      <PageLayout title={title} subtitle={subtitle}>
         {/* Apply empty box styles */}
        <div
          className={styles.emptyBox} // Apply CSS module class
        >
          <h3 className={styles.emptyTitle}>No data available</h3> {/* Apply CSS module class & remove inline style */}
          <p>{emptyMessage}</p> {/* Replaced AlertDescription */}
        </div>
        {onRefresh && (
          <button // Replaced Button
            className={styles.actionButton} // Apply button styles
            onClick={onRefresh}
          >
            Refresh
          </button>
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
        {renderContent(data)}
      </div>
    </PageLayout>
  );
} 