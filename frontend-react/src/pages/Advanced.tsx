import { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { PageLayout } from '@/components/layout';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { DatabaseManagement } from '@/components/DatabaseManagement';
import { AIEnrichment } from '@/components/AIEnrichment';
import { DuplicateReview } from '@/components/DuplicateReview';
import { formatDate } from '@/utils/dateUtils';
import { get, post } from '@/utils/apiUtils';
import { LoadingButton } from '@/components/ui/LoadingButton';
import { ErrorDisplay } from '@/components/ui/ErrorDisplay';
import { CenteredSpinner } from '@/components/ui/LoadingSpinner';

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
  const [searchParams, setSearchParams] = useSearchParams();
  const activeTab = searchParams.get('tab') || 'data-sources';
  const activeSubTab = searchParams.get('subtab') || 'overview';
  const queryClient = useQueryClient();
  const [runningScrapers, setRunningScrapers] = useState<Set<number>>(new Set());
  const [runAllInProgress, setRunAllInProgress] = useState(false);

  // Fetch data sources
  const { data: sources, isLoading, error } = useQuery<{ status: string; data: DataSource[] }>({
    queryKey: ['dataSources'],
    queryFn: () => get<{ status: string; data: DataSource[] }>('/api/data-sources/'),
  });

  // Mutation for running individual scraper
  const runScraperMutation = useMutation({
    mutationFn: (sourceId: number) => post(`/api/data-sources/${sourceId}/pull`),
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
    mutationFn: () => post('/api/data-sources/run-all'),
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

  const setActiveTab = (tab: string, subtab?: string) => {
    const params: any = { tab };
    if (subtab) {
      params.subtab = subtab;
    }
    setSearchParams(params);
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

  const tabs = [
    { id: 'data-sources', label: 'Data Sources', description: 'Manage data sources and scrapers' },
    { 
      id: 'database', 
      label: 'Database', 
      description: 'Database management and operations',
      subTabs: [
        { id: 'overview', label: 'Overview' },
        { id: 'duplicates', label: 'Duplicate Review' }
      ]
    },
    { id: 'ai-enrichment', label: 'AI Enhancement', description: 'AI enrichment controls and status monitoring' }
  ];

  const currentTab = tabs.find(tab => tab.id === activeTab) || tabs[0];

  const renderTabContent = () => {
    switch (activeTab) {
      case 'database':
        return renderDatabaseTab();
      case 'ai-enrichment':
        return <AIEnrichment />;
      case 'data-sources':
      default:
        return renderDataSourcesTab();
    }
  };

  const renderDatabaseTab = () => {
    const currentTab = tabs.find(tab => tab.id === 'database');
    const subTabs = currentTab?.subTabs || [];
    
    return (
      <div className="space-y-6">
        {/* SubTab Navigation */}
        {subTabs.length > 0 && (
          <div className="border-b border-gray-200">
            <nav className="-mb-px flex space-x-8">
              {subTabs.map((subTab) => (
                <button
                  key={subTab.id}
                  onClick={() => setActiveTab('database', subTab.id)}
                  className={`
                    py-2 px-1 border-b-2 font-medium text-sm
                    ${activeSubTab === subTab.id
                      ? 'border-blue-500 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                    }
                  `}
                >
                  {subTab.label}
                </button>
              ))}
            </nav>
          </div>
        )}

        {/* SubTab Content */}
        {activeSubTab === 'duplicates' ? <DuplicateReview /> : <DatabaseManagement />}
      </div>
    );
  };

  const renderDataSourcesTab = () => {
    if (isLoading) {
      return <CenteredSpinner text="Loading data sources..." height="h-64" />;
    }

    if (error) {
      return <ErrorDisplay error={error as Error} title="Failed to load data sources" />;
    }

    const dataSources = sources?.data || [];

    return (
      <div className="space-y-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Data Sources</CardTitle>
            <LoadingButton
              onClick={handleRunAllScrapers}
              isLoading={runAllInProgress}
              loadingText="Running All Scrapers..."
              disabled={dataSources.length === 0}
              className="bg-blue-600 hover:bg-blue-700"
            >
              Pull All Sources
            </LoadingButton>
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
                        <TableCell className="text-sm">{formatDate(source.last_scraped, { fallback: 'Never' })}</TableCell>
                        <TableCell>{source.prospectCount}</TableCell>
                        <TableCell>
                          <LoadingButton
                            size="sm"
                            onClick={() => handleRunScraper(source.id)}
                            isLoading={isRunning}
                            loadingText="Running..."
                            disabled={runAllInProgress}
                            className="bg-green-600 hover:bg-green-700"
                          >
                            Run Scraper
                          </LoadingButton>
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
    );
  };

  return (
    <PageLayout title="Advanced" subtitle={currentTab.description}>
      <div className="space-y-6">
        {/* Tab Navigation */}
        <div className="border-b border-gray-200">
          <nav className="-mb-px flex space-x-8">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`
                  py-2 px-1 border-b-2 font-medium text-sm
                  ${activeTab === tab.id
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }
                `}
              >
                {tab.label}
              </button>
            ))}
          </nav>
        </div>

        {/* Tab Content */}
        {renderTabContent()}
      </div>
    </PageLayout>
  );
}