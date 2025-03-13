import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui';

interface StatsCardProps {
  title: string;
  value: string | number;
  description?: string;
  icon?: React.ReactNode;
  className?: string;
  trend?: any;
}

export function StatsCard({ 
  title, 
  value, 
  description, 
  icon, 
  className,
  trend 
}: StatsCardProps) {
  return (
    <Card className={className}>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        {icon && <div className="h-4 w-4 text-muted-foreground">{icon}</div>}
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        {description && (
          <p className="text-xs text-muted-foreground">{description}</p>
        )}
        {trend && (
          <div className="text-xs text-muted-foreground mt-1">
            {typeof trend === 'object' ? (
              <span className={trend.direction === 'up' ? 'text-green-500' : 'text-red-500'}>
                {trend.value}% {trend.direction === 'up' ? '↑' : '↓'}
              </span>
            ) : (
              <span>{trend}</span>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

interface StatsGridProps {
  children: React.ReactNode;
  columns?: number;
  className?: string;
}

export function StatsGrid({ 
  children, 
  columns = 3, 
  className 
}: StatsGridProps) {
  const gridCols = {
    1: 'grid-cols-1',
    2: 'grid-cols-1 md:grid-cols-2',
    3: 'grid-cols-1 md:grid-cols-2 lg:grid-cols-3',
    4: 'grid-cols-1 md:grid-cols-2 lg:grid-cols-4',
  };

  return (
    <div className={`grid gap-4 ${gridCols[columns as keyof typeof gridCols]} ${className || ''}`}>
      {children}
    </div>
  );
} 