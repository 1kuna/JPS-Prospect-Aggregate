import { useState, useEffect } from 'react';
import axios from 'axios';
import { formatDate } from '@/lib/utils';
import {
  PageLayout,
  PageSkeleton,
  DataTable,
  StatsCard,
  StatsGrid,
} from '@/components';

interface Proposal {
  id: string | number;
  title: string;
  agency: string;
  release_date: string | null;
  status: string;
}

interface DashboardData {
  counts: {
    total_proposals: number;
    total_sources: number;
  };
  recent_proposals: Proposal[];
}

export default function SimpleDashboard() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    
    try {
      // Direct API call without going through the store
      const response = await axios.get('/api/dashboard');
      
      if (response.data && response.data.status === 'success' && response.data.data) {
        setData(response.data.data);
        setLastUpdated(new Date());
      } else {
        throw new Error('Invalid response format');
      }
    } catch (err: any) {
      console.error('Error fetching dashboard data:', err);
      setError(err.message || 'Failed to fetch dashboard data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  // If loading and no data, show skeleton
  if (loading && !data) {
    return <PageSkeleton cardCount={2} />;
  }

  // Define table columns
  const columns = [
    { header: 'Title', accessor: 'title' as keyof Proposal },
    { header: 'Agency', accessor: 'agency' as keyof Proposal },
    { header: 'Status', accessor: 'status' as keyof Proposal },
    { 
      header: 'Release Date', 
      accessor: (proposal: Proposal) => proposal.release_date ? formatDate(proposal.release_date) : 'N/A'
    },
  ];

  // Define stats for summary card
  const summaryStats = [
    { label: 'Total Proposals:', value: data?.counts.total_proposals || 0 },
    { label: 'Total Data Sources:', value: data?.counts.total_sources || 0 },
  ];

  return (
    <PageLayout
      title="Simple Dashboard"
      description="A simplified view of the dashboard data"
      lastUpdated={lastUpdated}
      onRefresh={fetchData}
      isLoading={loading}
      error={error}
    >
      <StatsGrid columns={1}>
        <StatsCard
          title="Summary"
          stats={summaryStats}
        />
      </StatsGrid>

      <DataTable
        title="Recent Proposals"
        data={data?.recent_proposals || []}
        columns={columns}
        keyField="id"
        emptyMessage={{
          title: 'No recent proposals',
          description: 'There are no recent proposals to display.',
        }}
      />
    </PageLayout>
  );
} 