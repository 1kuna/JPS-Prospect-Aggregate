// Re-export all types
export * from './api';
export * from './prospects';
export * from './enhancement';
export * from './database';

// Legacy types - to be moved to appropriate files
export interface DataSource {
  id: number;
  name: string;
  url: string;
  description: string;
  last_scraped: string | null;
  prospectCount: number;
  last_checked: string | null;
  status: string;
  type?: string; // Optional for backward compatibility
}
