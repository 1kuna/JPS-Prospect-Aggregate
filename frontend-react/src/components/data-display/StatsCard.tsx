import React from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';

interface StatItem {
  label: string;
  value: React.ReactNode;
  className?: string;
}

interface StatsCardProps {
  title: string;
  description?: string;
  stats: StatItem[];
  className?: string;
  isLoading?: boolean;
}

export function StatsCard({ title, description, stats, className, isLoading = false }: StatsCardProps) {
  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        {description && <CardDescription>{description}</CardDescription>}
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          {isLoading ? (
            // Loading skeleton
            Array.from({ length: stats.length || 3 }, (_, i) => (
              <div key={i} className="flex justify-between items-center">
                <Skeleton className="h-4 w-1/3" />
                <Skeleton className="h-4 w-1/4" />
              </div>
            ))
          ) : (
            // Actual stats
            stats.map((stat, index) => (
              <div key={index} className="flex justify-between items-center">
                <span>{stat.label}</span>
                <span className={`font-medium ${stat.className || ''}`}>{stat.value}</span>
              </div>
            ))
          )}
        </div>
      </CardContent>
    </Card>
  );
}

interface StatsGridProps {
  children: React.ReactNode;
  columns?: 1 | 2 | 3 | 4;
  className?: string;
}

export function StatsGrid({ children, columns = 3, className }: StatsGridProps) {
  const gridCols = {
    1: 'grid-cols-1',
    2: 'grid-cols-1 md:grid-cols-2',
    3: 'grid-cols-1 md:grid-cols-2 lg:grid-cols-3',
    4: 'grid-cols-1 md:grid-cols-2 lg:grid-cols-4',
  };

  return (
    <div className={`grid ${gridCols[columns]} gap-6 mb-8 ${className || ''}`}>
      {children}
    </div>
  );
} 