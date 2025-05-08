import React from 'react';
import styles from './PageLayout.module.css'; // Import CSS module

interface PageLayoutProps {
  title?: string;
  description?: string;
  subtitle?: string;
  children: React.ReactNode;
}

export function PageLayout({ 
  title, 
  description,
  subtitle,
  children, 
}: PageLayoutProps) {
  return (
    <div className={styles.pageLayoutContainer}>
      <div className={styles.headerContainer}>
        {title && (
          <h1 className={styles.pageTitle}>{title}</h1>
        )}
        {subtitle && (
          <p className={styles.pageSubtitle}>{subtitle}</p>
        )}
        {description && (
          <p className={styles.pageDescription}>{description}</p>
        )}
      </div>
      {children}
    </div>
  );
}

// Replaced skeleton placeholders with simple text
export function PageSkeleton() {
  return (
    <div className={styles.skeletonContainer}>
      <div>Loading content...</div>
    </div>
  );
} 