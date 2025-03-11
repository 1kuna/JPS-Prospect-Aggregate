import { useState, useEffect } from 'react';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Alert, AlertTitle, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';

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
      
      console.log('Combined data:', combinedData);
      
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

  const formatDate = (dateString: string | null): string => {
    if (!dateString) return 'N/A';
    try {
      return new Date(dateString).toLocaleString();
    } catch (e) {
      return dateString;
    }
  };

  if (loading && !data) {
    return (
      <div className="container mx-auto py-6">
        <Card>
          <CardHeader>
            <CardTitle>Direct Database Access</CardTitle>
            <CardDescription>Loading data directly from the database...</CardDescription>
          </CardHeader>
          <CardContent>
            <Skeleton className="h-64 w-full" />
          </CardContent>
        </Card>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container mx-auto py-6">
        <Alert variant="destructive">
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
        <Button className="mt-4" onClick={fetchData}>Retry</Button>
      </div>
    );
  }

  return (
    <div className="container mx-auto py-6">
      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Direct Database Access</CardTitle>
          <CardDescription>
            Viewing data directly from the database
            {lastUpdated && ` (Last updated: ${lastUpdated.toLocaleString()})`}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
            <Card>
              <CardHeader>
                <CardTitle>Database Stats</CardTitle>
              </CardHeader>
              <CardContent>
                <p>Total Proposals: {data?.totalProposals || 0}</p>
                <p>Total Data Sources: {data?.totalSources || 0}</p>
                <p>Timestamp: {formatDate(data?.timestamp || null)}</p>
              </CardContent>
            </Card>
          </div>

          <div className="mb-6">
            <h3 className="text-lg font-medium mb-2">Recent Proposals</h3>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>ID</TableHead>
                  <TableHead>Title</TableHead>
                  <TableHead>Agency</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Release Date</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data?.proposals.slice(0, 10).map((proposal) => (
                  <TableRow key={proposal.id}>
                    <TableCell>{proposal.id}</TableCell>
                    <TableCell>{proposal.title}</TableCell>
                    <TableCell>{proposal.agency}</TableCell>
                    <TableCell>{proposal.status}</TableCell>
                    <TableCell>{formatDate(proposal.release_date)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>

          <div>
            <h3 className="text-lg font-medium mb-2">Data Sources</h3>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>ID</TableHead>
                  <TableHead>Name</TableHead>
                  <TableHead>URL</TableHead>
                  <TableHead>Last Scraped</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data?.dataSources.map((source) => (
                  <TableRow key={source.id}>
                    <TableCell>{source.id}</TableCell>
                    <TableCell>{source.name}</TableCell>
                    <TableCell className="truncate max-w-xs">{source.url}</TableCell>
                    <TableCell>{formatDate(source.last_scraped)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
      <Button onClick={fetchData}>Refresh Data</Button>
    </div>
  );
} 