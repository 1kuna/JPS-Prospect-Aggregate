import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { get, post } from '@/utils/apiUtils';
import { useClearDataSourceData } from '@/hooks/api/useDataSources';
import { useToast } from '@/contexts/ToastContext';
import { formatScraperResults } from '@/utils/statusUtils';
import { DataSource } from '@/types';
import { ErrorSeverity, ErrorCategory } from '@/types/errors';

interface ScraperResult {
  source_name: string;
  source_id: number;
  status: string;
  duration: number;
  message?: string;
  error?: string;
}

export function useDataSourceManagement() {
  const queryClient = useQueryClient();
  const { showSuccessToast, showErrorToast } = useToast();
  const clearDataMutation = useClearDataSourceData();

  // Fetch data sources with frequent updates when scrapers are running
  const { data: sources, isLoading, error } = useQuery<{ status: string; data: DataSource[] }>({
    queryKey: ['dataSources'],
    queryFn: () => get<{ status: string; data: DataSource[] }>('/api/data-sources/'),
    refetchInterval: 5000, // Check every 5 seconds for simplicity
    refetchIntervalInBackground: true,
  });

  // Mutation for running all scrapers
  const runAllScrapersMutation = useMutation({
    mutationFn: () => post<{
      message: string;
      total_duration: number;
      results?: ScraperResult[];
    }>('/api/data-sources/run-all'),
    onSuccess: (data) => {
      // All scrapers completed - show results
      if (data.results) {
        const { message } = formatScraperResults(data.results, data.total_duration);
        showSuccessToast('Scraper Run Complete', message);
      }
    },
    onSettled: () => {
      // Refetch data sources to update status
      queryClient.invalidateQueries({ queryKey: ['dataSources'] });
    },
  });

  // Handle clearing data source data
  const handleClearData = async (id: DataSource['id'], sourceName: string) => {
    try {
      const result = await clearDataMutation.mutateAsync(id);
      showSuccessToast(
        'Data Cleared',
        `Successfully cleared ${result.deleted_count} prospects from ${sourceName}.`
      );
      // Query invalidation is handled by the mutation's onSuccess
    } catch (err) {
      // Failed to clear data source data
      showErrorToast({
        code: 'CLEAR_DATA_ERROR',
        message: err instanceof Error ? err.message : 'Failed to clear data source data',
        severity: ErrorSeverity.ERROR,
        category: ErrorCategory.SYSTEM,
        timestamp: new Date(),
        userMessage: 'Failed to clear data source data. Please try again.',
      });
    }
  };

  return {
    // Data
    sources,
    isLoading,
    error,
    
    // Mutations
    runAllScrapersMutation,
    clearDataMutation,
    
    // Handlers
    handleClearData,
  };
}