import React from 'react';
import { PageLayout } from './PageLayout';
import { Alert, AlertTitle, AlertDescription, Button, Spinner } from '@/components/ui';

interface DataPageLayoutProps<T> {
  title: string;
  subtitle?: string;
  data: T | T[] | null;
  loading: boolean;
  error: Error | null;
  onRefresh: () => void;
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
        <div className="flex justify-center items-center h-[500px]">
          <Spinner className="h-8 w-8" />
        </div>
      </PageLayout>
    );
  }

  // Error state
  if (error && (!data || (Array.isArray(data) && data.length === 0))) {
    return (
      <PageLayout title={title} subtitle={subtitle}>
        <div className="space-y-6">
          <Alert variant="destructive">
            <AlertTitle>Error loading data</AlertTitle>
            <AlertDescription>{error.message}</AlertDescription>
          </Alert>
          <Button onClick={onRefresh}>Retry</Button>
        </div>
      </PageLayout>
    );
  }

  // Empty state
  if (!data || (Array.isArray(data) && data.length === 0)) {
    return (
      <PageLayout title={title} subtitle={subtitle}>
        <Alert>
          <AlertTitle>No data available</AlertTitle>
          <AlertDescription>{emptyMessage}</AlertDescription>
        </Alert>
        <Button onClick={onRefresh} className="mt-4">Refresh</Button>
      </PageLayout>
    );
  }

  // Main content
  return (
    <PageLayout title={title} subtitle={subtitle}>
      <div className="space-y-4">
        {renderHeader && (
          <div className="flex justify-between items-center">
            {renderHeader()}
          </div>
        )}
        {renderContent(data)}
      </div>
    </PageLayout>
  );
} 