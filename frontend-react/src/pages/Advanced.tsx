import { useState } from 'react';
import { PageLayout } from '@/components/layout';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';

interface DataSource {
  id: number;
  name: string;
  url: string;
  description: string;
  last_scraped: string | null;
  prospectCount: number;
  last_checked: string | null;
  status: string;
}

interface ScraperResult {
  source_name: string;
  source_id: number;
  status: string;
  duration: number;
  message?: string;
  error?: string;
}

export default function Advanced() {
  const queryClient = useQueryClient();
  const [runningScrapers, setRunningScrapers] = useState<Set<number>>(new Set());
  const [runAllInProgress, setRunAllInProgress] = useState(false);

  // Fetch data sources
  const { data: sources, isLoading, error } = useQuery<{ status: string; data: DataSource[] }>({
    queryKey: ['dataSources'],
    queryFn: async () => {
      const response = await fetch('/api/data-sources/');
      if (!response.ok) {
        throw new Error('Failed to fetch data sources');
      }
      return response.json();
    },
  });

  // Mutation for running individual scraper
  const runScraperMutation = useMutation({
    mutationFn: async (sourceId: number) => {
      const response = await fetch(`/api/data-sources/${sourceId}/pull`, {
        method: 'POST',
      });
      if (!response.ok) {
        throw new Error('Failed to run scraper');
      }
      return response.json();
    },
    onMutate: (sourceId) => {
      setRunningScrapers(prev => new Set(prev).add(sourceId));
    },
    onSettled: (_, __, sourceId) => {
      setRunningScrapers(prev => {
        const next = new Set(prev);
        next.delete(sourceId);
        return next;
      });
      // Refetch data sources to update status
      queryClient.invalidateQueries({ queryKey: ['dataSources'] });
    },
  });

  // Mutation for running all scrapers
  const runAllScrapersMutation = useMutation({
    mutationFn: async () => {
      const response = await fetch('/api/data-sources/run-all', {
        method: 'POST',
      });
      if (!response.ok) {
        throw new Error('Failed to run all scrapers');
      }
      return response.json();
    },
    onMutate: () => {
      setRunAllInProgress(true);
    },
    onSuccess: (data) => {
      console.log('All scrapers completed:', data);
      // Show results
      if (data.results) {
        alert(`Scraper Results:\n${data.message}\nTotal Duration: ${data.total_duration}s\n\nDetails:\n${
          data.results.map((r: ScraperResult) => 
            `${r.source_name}: ${r.status} (${r.duration}s)${r.error ? ' - ' + r.error : ''}`
          ).join('\n')
        }`);
      }
    },
    onSettled: () => {
      setRunAllInProgress(false);
      // Refetch data sources to update status
      queryClient.invalidateQueries({ queryKey: ['dataSources'] });
    },
  });

  const handleRunScraper = (sourceId: number) => {
    runScraperMutation.mutate(sourceId);
  };

  const handleRunAllScrapers = () => {
    if (window.confirm('This will run all scrapers synchronously. This may take several minutes. Continue?')) {
      runAllScrapersMutation.mutate();
    }
  };

  const formatDate = (dateString: string | null) => {
    if (!dateString) return 'Never';
    // The backend sends ISO format without Z, but it's UTC
    // Add Z if not present to ensure proper UTC parsing
    const dateStr = dateString.includes('Z') || dateString.includes('+') || dateString.includes('-') 
      ? dateString 
      : dateString + 'Z';
    const date = new Date(dateStr);
    return date.toLocaleString();
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
      case 'success':
        return 'text-green-600';
      case 'failed':
        return 'text-red-600';
      case 'working':
        return 'text-blue-600';
      case 'pending':
        return 'text-yellow-600';
      default:
        return 'text-gray-600';
    }
  };

  if (isLoading) {
    return (
      <PageLayout title="Advanced" subtitle="Manage data sources and scrapers">
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-600"></div>
        </div>
      </PageLayout>
    );
  }

  if (error) {
    return (
      <PageLayout title="Advanced" subtitle="Manage data sources and scrapers">
        <div className="text-red-600">Error loading data sources: {(error as Error).message}</div>
      </PageLayout>
    );
  }

  const dataSources = sources?.data || [];

  return (
    <PageLayout title="Advanced" subtitle="Manage data sources and scrapers">
      <div className="space-y-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Data Sources</CardTitle>
            <Button
              onClick={handleRunAllScrapers}
              disabled={runAllInProgress || dataSources.length === 0}
              className="bg-blue-600 hover:bg-blue-700 text-white"
            >
              {runAllInProgress ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-t-2 border-b-2 border-white mr-2"></div>
                  Running All Scrapers...
                </>
              ) : (
                'Pull All Sources'
              )}
            </Button>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Description</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Last Scraped</TableHead>
                    <TableHead>Prospects</TableHead>
                    <TableHead>Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {dataSources.map((source) => {
                    const isRunning = runningScrapers.has(source.id);
                    return (
                      <TableRow key={source.id}>
                        <TableCell className="font-medium">{source.name}</TableCell>
                        <TableCell className="text-sm text-gray-600">{source.description}</TableCell>
                        <TableCell>
                          <span className={`font-medium ${getStatusColor(source.status)}`}>
                            {source.status}
                          </span>
                        </TableCell>
                        <TableCell className="text-sm">{formatDate(source.last_scraped)}</TableCell>
                        <TableCell>{source.prospectCount}</TableCell>
                        <TableCell>
                          <Button
                            size="sm"
                            onClick={() => handleRunScraper(source.id)}
                            disabled={isRunning || runAllInProgress}
                            className="bg-green-600 hover:bg-green-700 text-white"
                          >
                            {isRunning ? (
                              <>
                                <div className="animate-spin rounded-full h-3 w-3 border-t-2 border-b-2 border-white mr-2"></div>
                                Running...
                              </>
                            ) : (
                              'Run Scraper'
                            )}
                          </Button>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      </div>
    </PageLayout>
  );
}