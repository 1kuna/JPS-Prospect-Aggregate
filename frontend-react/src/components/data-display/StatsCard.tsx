import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui';
import styles from './StatsCard.module.css';

interface StatsCardProps {
  title: string;
  value: string | number;
  description?: string;
  icon?: React.ReactNode;
  className?: string;
  trend?: { direction: 'up' | 'down'; value: number | string };
}

export function StatsCard({ 
  title, 
  value, 
  description, 
  icon, 
  className,
  trend 
}: StatsCardProps) {
  const trendClassName = trend
    ? trend.direction === 'up' ? styles.trendUp : styles.trendDown
    : '';

  return (
    <Card className={className}>
      <CardHeader className={styles.statsCardHeader}>
        <CardTitle className={styles.statsCardTitle}>{title}</CardTitle>
        {icon && <div className={styles.statsCardIcon}>{icon}</div>}
      </CardHeader>
      <CardContent>
        <div className={styles.statsCardValue}>{value}</div>
        {description && (
          <p className={styles.statsCardDescription}>{description}</p>
        )}
        {trend && (
          <div className={styles.statsCardTrend}>
            {typeof trend === 'object' ? (
              <span className={trendClassName}>
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
  columns?: 1 | 2 | 3 | 4;
  className?: string;
}

export function StatsGrid({ 
  children, 
  columns = 3, 
  className = '' 
}: StatsGridProps) {
  const columnClass = {
    1: styles.gridCols1,
    2: styles.gridCols2,
    3: styles.gridCols3,
    4: styles.gridCols4,
  }[columns];

  const gridClassName = `${styles.statsGrid} ${columnClass} ${className}`.trim();

  return (
    <div className={gridClassName}>
      {children}
    </div>
  );
} 