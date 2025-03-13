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
  source_name: string;
  release_date: string | null;
  status: string;
}

interface DataSource {
  id: string | number;
  name: string;
  url: string;
  description: string;
  last_scraped: string | null;
}

interface DirectDBData {
  proposals: Proposal[];
  dataSources: DataSource[];
  totalProposals: number;
  totalSources: number;
  timestamp: string;
}

export default function DirectDatabaseAccess() {
  const [data, setData] = useState<DirectDBData | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    
    try {
      // Fetch data from multiple endpoints
      const [proposalsRes, dataSourcesRes, dashboardRes] = await Promise.all([
        axios.get('/api/proposals'),
        axios.get('/api/data-sources'),
        axios.get('/api/dashboard')
      ]);
      
      // Combine the data
      const combinedData: DirectDBData = {
        proposals: proposalsRes.data.data || [],
        dataSources: dataSourcesRes.data.data || [],
        totalProposals: dashboardRes.data.data?.counts?.total_proposals || 0,
        totalSources: dashboardRes.data.data?.counts?.total_sources || 0,
        timestamp: new Date().toISOString()
      };
      
      setData(combinedData);
      setLastUpdated(new Date());
    } catch (err: any) {
      console.error('Error fetching data:', err);
      setError(err.message || 'Failed to fetch data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  // If loading and no data, show skeleton
  if (loading && !data) {
    return <PageSkeleton cardCount={3} />;
  }

  // Define stats for database stats card
  const dbStats = [
    { label: 'Total Proposals:', value: data?.totalProposals || 0 },
    { label: 'Total Data Sources:', value: data?.totalSources || 0 },
    { label: 'Timestamp:', value: formatDate(data?.timestamp || '') },
  ];

  // Define table columns for proposals
  const proposalColumns = [
    { header: 'ID', accessor: 'id' as keyof Proposal },
    { header: 'Title', accessor: 'title' as keyof Proposal },
    { header: 'Agency', accessor: 'agency' as keyof Proposal },
    { header: 'Status', accessor: 'status' as keyof Proposal },
    { 
      header: 'Release Date', 
      accessor: (proposal: Proposal) => proposal.release_date ? formatDate(proposal.release_date) : 'N/A'
    },
  ];

  // Define table columns for data sources
  const dataSourceColumns = [
    { header: 'ID', accessor: 'id' as keyof DataSource },
    { header: 'Name', accessor: 'name' as keyof DataSource },
    { 
      header: 'URL', 
      accessor: (source: DataSource) => (
        <div className="truncate max-w-xs">{source.url}</div>
      )
    },
    { 
      header: 'Last Scraped', 
      accessor: (source: DataSource) => source.last_scraped ? formatDate(source.last_scraped) : 'Never'
    },
  ];

  return (
    <PageLayout
      title="Direct Database Access"
      description="Viewing data directly from the database"
      lastUpdated={lastUpdated}
      onRefresh={fetchData}
      isLoading={loading}
      error={error}
    >
      <StatsGrid columns={1}>
        <StatsCard
          title="Database Stats"
          stats={dbStats}
        />
      </StatsGrid>

      <DataTable
        title="Recent Proposals"
        data={data?.proposals.slice(0, 10) || []}
        columns={proposalColumns}
        keyField="id"
        emptyMessage={{
          title: 'No proposals found',
          description: 'There are no proposals to display.',
        }}
      />

      <DataTable
        title="Data Sources"
        data={data?.dataSources || []}
        columns={dataSourceColumns}
        keyField="id"
        emptyMessage={{
          title: 'No data sources found',
          description: 'There are no data sources to display.',
        }}
      />
    </PageLayout>
  );
} 