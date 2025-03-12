import React from 'react';
import { Button } from '@/components/ui/button';
import { Alert, AlertTitle, AlertDescription } from '@/components/ui/alert';
import { Skeleton } from '@/components/ui/skeleton';
import { formatDate } from '@/lib/utils';

interface PageLayoutProps {
  title: string;
  description?: string;
  lastUpdated?: string | Date | null;
  isLoading?: boolean;
  error?: { message: string } | string | null;
  onRefresh?: () => void;
  actions?: React.ReactNode;
  children: React.ReactNode;
}

export function PageLayout({
  title,
  description,
  lastUpdated,
  isLoading = false,
  error = null,
  onRefresh,
  actions,
  children,
}: PageLayoutProps) {
  const errorMessage = typeof error === 'string' ? error : error?.message;

  return (
    <div className="container mx-auto py-6">
      {/* Page header with title and last updated info */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold">{title}</h1>
          {description && <p className="text-muted-foreground mt-1">{description}</p>}
        </div>
        <div className="flex items-center gap-4">
          {lastUpdated && (
            <span className="text-sm text-muted-foreground">
              Last updated: {formatDate(lastUpdated)}
            </span>
          )}
          {onRefresh && (
            <Button onClick={onRefresh} disabled={isLoading}>
              {isLoading ? 'Refreshing...' : 'Refresh'}
            </Button>
          )}
          {actions}
        </div>
      </div>

      {/* Error state */}
      {error && (
        <Alert variant="destructive" className="mb-6">
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>{errorMessage}</AlertDescription>
        </Alert>
      )}

      {/* Content */}
      {children}
    </div>
  );
}

export function PageSkeleton({ cardCount = 3 }: { cardCount?: number }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      {Array.from({ length: cardCount }, (_, i) => (
        <div key={i} className="rounded-md border border-gray-200 bg-white shadow-sm p-6">
          <div className="border-b border-gray-200 pb-4 mb-4">
            <Skeleton className="h-8 w-3/4 mb-2" />
            <Skeleton className="h-4 w-1/2" />
          </div>
          <Skeleton className="h-24 w-full" />
        </div>
      ))}
    </div>
  );
} 