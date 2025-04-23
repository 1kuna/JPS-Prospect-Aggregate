import React from 'react';
import { PageLayout } from './PageLayout';
import styles from './DataPageLayout.module.css'; // Import CSS module
// import { Alert, AlertTitle, AlertDescription, Button, Spinner } from '@/components/ui'; // Removed imports

interface DataPageLayoutProps<T> {
  title: string;
  subtitle?: string;
  data: T | T[] | null;
  loading: boolean;
  error: Error | null;
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
          {/* <Spinner className="h-8 w-8" /> */}
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
          // style={{ border: '1px solid red', backgroundColor: '#fff5f5', padding: '1rem', margin: '1rem 0' }} // Remove inline style
        >
          <h3 className={styles.errorTitle}/* style={{ color: 'red', fontWeight: 'bold' }} */>Error loading data</h3> {/* Apply CSS module class & remove inline style */}
          <p>{error.message}</p> {/* Replaced AlertDescription */}
          {onRefresh && (
            <button // Replaced Button
              className={styles.actionButton} // Apply button styles
              // style={{ marginTop: '1rem', padding: '0.25rem 0.75rem', border: '1px solid #ccc', borderRadius: '0.25rem' }} // Remove inline style
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
          // style={{ border: '1px solid #facc15', backgroundColor: '#fefce8', padding: '1rem', margin: '1rem 0' }} // Remove inline style
        >
          <h3 className={styles.emptyTitle} /* style={{ fontWeight: 'bold' }} */>No data available</h3> {/* Apply CSS module class & remove inline style */}
          <p>{emptyMessage}</p> {/* Replaced AlertDescription */}
        </div>
        {onRefresh && (
          <button // Replaced Button
            className={styles.actionButton} // Apply button styles
            // style={{ marginTop: '1rem', padding: '0.25rem 0.75rem', border: '1px solid #ccc', borderRadius: '0.25rem' }} // Remove inline style
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