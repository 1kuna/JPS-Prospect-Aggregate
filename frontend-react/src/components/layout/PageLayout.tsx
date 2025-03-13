import React from 'react';
import { Skeleton } from '@/components/ui';

interface PageLayoutProps {
  title?: string;
  description?: string;
  subtitle?: string;
  children: React.ReactNode;
  isLoading?: boolean;
}

export function PageLayout({ 
  title, 
  description,
  subtitle,
  children, 
  isLoading = false 
}: PageLayoutProps) {
  return (
    <div className="space-y-6">
      <div className="space-y-2">
        {title && (
          <h1 className="text-3xl font-bold tracking-tight">{title}</h1>
        )}
        {subtitle && (
          <p className="text-sm text-muted-foreground">{subtitle}</p>
        )}
        {description && (
          <p className="text-muted-foreground">{description}</p>
        )}
      </div>
      {isLoading ? <PageSkeleton /> : children}
    </div>
  );
}

export function PageSkeleton() {
  return (
    <div className="space-y-6">
      <div className="space-y-4">
        <Skeleton className="h-8 w-[250px]" />
        <Skeleton className="h-4 w-[350px]" />
      </div>
      <div className="space-y-4">
        <Skeleton className="h-[300px] w-full" />
      </div>
    </div>
  );
} 