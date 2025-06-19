// Placeholder types index
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
