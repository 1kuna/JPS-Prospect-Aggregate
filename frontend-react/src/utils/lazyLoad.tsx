import React, { Suspense, lazy, ComponentType } from 'react';
import { Skeleton } from '@/components/ui/skeleton';

interface LazyLoadOptions {
  fallback?: React.ReactNode;
  preload?: boolean;
  errorBoundary?: boolean;
}

export function lazyLoad<T extends ComponentType<any>>(
  importFunc: () => Promise<{ default: T }>,
  options: LazyLoadOptions = {}
) {
  const LazyComponent = lazy(importFunc);
  
  // Preload if specified
  if (options.preload) {
    importFunc();
  }
  
  return function LazyLoadedComponent(props: React.ComponentProps<T>) {
    const fallback = options.fallback || <Skeleton className="w-full h-32" />;
    
    return (
      <Suspense fallback={fallback}>
        <LazyComponent {...props} />
      </Suspense>
    );
  };
}
// Usage example:
// const DataTable = lazyLoad(() => import('../components/DataTable'), { 
//   preload: true,
//   fallback: <TableSkeleton rows={10} /> 
// }); 
