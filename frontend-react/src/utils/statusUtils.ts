/**
 * Get the appropriate CSS class for a given status
 */
export function getStatusColor(status: string): string {
  switch (status) {
    case 'completed':
    case 'success':
      return 'text-success dark:text-success';
    case 'failed':
    case 'error':
      return 'text-danger dark:text-danger';
    case 'working':
    case 'in_progress':
    case 'processing':
      return 'text-primary';
    case 'stopping':
      return 'text-warning dark:text-warning';
    case 'pending':
    case 'stopped':
      return 'text-warning dark:text-warning';
    case 'ready':
      return 'text-muted-foreground';
    default:
      return 'text-muted-foreground';
  }
}

/**
 * Format scraper results for display
 */
export function formatScraperResults(results: Array<{
  source_name: string;
  source_id: number;
  status: string;
  duration: number;
  message?: string;
  error?: string;
}>, totalDuration: number): { successCount: number; failedCount: number; message: string } {
  const failedScrapers = results.filter(r => r.error);
  const successCount = results.length - failedScrapers.length;
  
  const message = `${successCount}/${results.length} scrapers completed successfully in ${totalDuration}s${
    failedScrapers.length > 0 ? `. ${failedScrapers.length} failed.` : ''
  }`;
  
  return {
    successCount,
    failedCount: failedScrapers.length,
    message,
  };
}