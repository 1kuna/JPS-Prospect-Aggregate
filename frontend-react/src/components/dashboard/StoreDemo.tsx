import { useAnalyticsData } from '@/hooks/use-analytics';
import { useGetAllDataSources } from '@/hooks/use-data-sources';
import { toast } from '@/hooks/use-toast';

export default function StoreDemo() {
  // Use the new React Query hooks
  const { 
    data: dataSources, 
    isLoading: dataSourcesLoading,
    error: dataSourcesError
  } = useGetAllDataSources();

  const {
    statistics,
    dashboard,
    isLoading: analyticsLoading,
    isError: analyticsError,
    error: analyticsErrorData
  } = useAnalyticsData();

  // Show error toasts if needed
  if (dataSourcesError) {
    toast.error({
      title: 'Error',
      description: 'Failed to load data sources: ' + dataSourcesError.message
    });
  }

  if (analyticsError && analyticsErrorData) {
    toast.error({
      title: 'Error',
      description: 'Failed to load analytics: ' + analyticsErrorData.message
    });
  }

  const isLoading = dataSourcesLoading || analyticsLoading;

  if (isLoading) {
    return <div>Loading...</div>;
  }

  return (
    <div>
      <h2>Data Sources</h2>
      <ul>
        {dataSources?.data.map(source => (
          <li key={source.id}>{source.name}</li>
        ))}
      </ul>

      <h2>Statistics</h2>
      {statistics && (
        <div>
          <p>Total Proposals: {statistics.totalProposals}</p>
          <p>Active Data Sources: {statistics.activeDataSources}</p>
        </div>
      )}

      <h2>Recent Activity</h2>
      {dashboard?.recentProposals.map(proposal => (
        <div key={proposal.id}>
          <p>{proposal.title}</p>
          <small>{new Date(proposal.createdAt).toLocaleDateString()}</small>
        </div>
      ))}
    </div>
  );
} 