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
      console.log('API Response:', response.data);
      
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
            <CardTitle>Simple Dashboard</CardTitle>
            <CardDescription>Loading dashboard data...</CardDescription>
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
          <CardTitle>Simple Dashboard</CardTitle>
          <CardDescription>
            A simplified view of the dashboard data
            {lastUpdated && ` (Last updated: ${lastUpdated.toLocaleString()})`}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
            <Card>
              <CardHeader>
                <CardTitle>Summary</CardTitle>
              </CardHeader>
              <CardContent>
                <p>Total Proposals: {data?.counts.total_proposals || 0}</p>
                <p>Total Data Sources: {data?.counts.total_sources || 0}</p>
              </CardContent>
            </Card>
          </div>

          <div>
            <h3 className="text-lg font-medium mb-2">Recent Proposals</h3>
            {data?.recent_proposals && data.recent_proposals.length > 0 ? (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Title</TableHead>
                    <TableHead>Agency</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Release Date</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.recent_proposals.map((proposal) => (
                    <TableRow key={proposal.id}>
                      <TableCell>{proposal.title}</TableCell>
                      <TableCell>{proposal.agency}</TableCell>
                      <TableCell>{proposal.status}</TableCell>
                      <TableCell>{formatDate(proposal.release_date)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            ) : (
              <p>No recent proposals found.</p>
            )}
          </div>
        </CardContent>
      </Card>
      <Button onClick={fetchData}>Refresh Data</Button>
    </div>
  );
} 