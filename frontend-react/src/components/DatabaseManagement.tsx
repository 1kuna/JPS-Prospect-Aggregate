import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface DatabaseStatus {
  prospect_count: number;
  prospects_with_source: number;
  prospects_without_source: number;
  ai_enriched_count: number;
  original_count: number;
  data_source_count: number;
  status_record_count: number;
  database_size_bytes: number | null;
  timestamp: string;
}

interface AIPreservationConfig {
  preserve_ai_data_on_refresh: boolean;
  description: string;
}

export function DatabaseManagement() {
  const queryClient = useQueryClient();
  const [isClearing, setIsClearing] = useState(false);

  // Fetch database status
  const { data: statusData, isLoading, error, refetch } = useQuery<{ status: string; data: DatabaseStatus }>({
    queryKey: ['databaseStatus'],
    queryFn: async () => {
      const response = await fetch('/api/database/status');
      if (!response.ok) {
        throw new Error('Failed to fetch database status');
      }
      return response.json();
    },
  });

  // Fetch AI preservation config
  const { data: aiConfigData, isLoading: isLoadingConfig } = useQuery<{ status: string; data: AIPreservationConfig }>({
    queryKey: ['aiPreservationConfig'],
    queryFn: async () => {
      const response = await fetch('/api/config/ai-preservation');
      if (!response.ok) {
        throw new Error('Failed to fetch AI preservation config');
      }
      return response.json();
    },
  });

  // Mutation for clearing all database
  const clearDatabaseMutation = useMutation({
    mutationFn: async () => {
      const response = await fetch('/api/database/clear', {
        method: 'POST',
      });
      if (!response.ok) {
        throw new Error('Failed to clear database');
      }
      return response.json();
    },
    onMutate: () => {
      setIsClearing(true);
    },
    onSuccess: (data) => {
      alert(`Database cleared successfully!\n\n${data.message}`);
      // Refetch all relevant data
      queryClient.invalidateQueries({ queryKey: ['databaseStatus'] });
      queryClient.invalidateQueries({ queryKey: ['dataSources'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      queryClient.invalidateQueries({ queryKey: ['proposals'] });
      queryClient.invalidateQueries({ queryKey: ['prospects'] });
    },
    onError: (error: Error) => {
      alert(`Failed to clear database: ${error.message}`);
    },
    onSettled: () => {
      setIsClearing(false);
    },
  });

  // Mutation for clearing AI entries
  const clearAIMutation = useMutation({
    mutationFn: async () => {
      const response = await fetch('/api/database/clear-ai', {
        method: 'POST',
      });
      if (!response.ok) {
        throw new Error('Failed to clear AI entries');
      }
      return response.json();
    },
    onMutate: () => {
      setIsClearing(true);
    },
    onSuccess: (data) => {
      alert(`AI entries cleared successfully!\n\n${data.message}`);
      // Refetch all relevant data
      queryClient.invalidateQueries({ queryKey: ['databaseStatus'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      queryClient.invalidateQueries({ queryKey: ['proposals'] });
      queryClient.invalidateQueries({ queryKey: ['prospects'] });
      queryClient.invalidateQueries({ queryKey: ['ai-enrichment-status'] });
    },
    onError: (error: Error) => {
      alert(`Failed to clear AI entries: ${error.message}`);
    },
    onSettled: () => {
      setIsClearing(false);
    },
  });

  // Mutation for clearing original entries
  const clearOriginalMutation = useMutation({
    mutationFn: async () => {
      const response = await fetch('/api/database/clear-original', {
        method: 'POST',
      });
      if (!response.ok) {
        throw new Error('Failed to clear original entries');
      }
      return response.json();
    },
    onMutate: () => {
      setIsClearing(true);
    },
    onSuccess: (data) => {
      alert(`Original entries cleared successfully!\n\n${data.message}`);
      // Refetch all relevant data
      queryClient.invalidateQueries({ queryKey: ['databaseStatus'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      queryClient.invalidateQueries({ queryKey: ['proposals'] });
      queryClient.invalidateQueries({ queryKey: ['prospects'] });
    },
    onError: (error: Error) => {
      alert(`Failed to clear original entries: ${error.message}`);
    },
    onSettled: () => {
      setIsClearing(false);
    },
  });

  // Mutation for updating AI preservation config
  const updateAIConfigMutation = useMutation({
    mutationFn: async (newValue: boolean) => {
      const response = await fetch('/api/config/ai-preservation', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ preserve_ai_data_on_refresh: newValue }),
      });
      if (!response.ok) {
        throw new Error('Failed to update AI preservation config');
      }
      return response.json();
    },
    onSuccess: (data) => {
      alert(`AI preservation setting updated!\n\n${data.data.message}`);
      queryClient.invalidateQueries({ queryKey: ['aiPreservationConfig'] });
    },
    onError: (error: Error) => {
      alert(`Failed to update AI preservation setting: ${error.message}`);
    },
  });

  const formatFileSize = (bytes: number | null) => {
    if (!bytes) return 'Unknown';
    const units = ['B', 'KB', 'MB', 'GB'];
    let size = bytes;
    let unitIndex = 0;
    
    while (size >= 1024 && unitIndex < units.length - 1) {
      size /= 1024;
      unitIndex++;
    }
    
    return `${size.toFixed(1)} ${units[unitIndex]}`;
  };

  const formatDate = (dateString: string) => {
    // The backend sends ISO format without Z, but it's UTC
    // Add Z if not present to ensure proper UTC parsing
    const dateStr = dateString.includes('Z') || dateString.includes('+') || dateString.includes('-') 
      ? dateString 
      : dateString + 'Z';
    const date = new Date(dateStr);
    return date.toLocaleString();
  };


  if (isLoading) {
    return (
      <div className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle>Database Management</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-center h-32">
              <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-blue-600"></div>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle>Database Management</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-red-600">Error loading database status: {(error as Error).message}</div>
            <Button onClick={() => refetch()} className="mt-4">
              Retry
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  const status = statusData?.data;

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Database Status</CardTitle>
        </CardHeader>
        <CardContent>
          {status && (
            <div className="grid grid-cols-2 gap-4">
              <div>
                <h4 className="font-medium text-gray-900">Total Prospects</h4>
                <p className="text-2xl font-bold text-blue-600">{status.prospect_count.toLocaleString()}</p>
                <p className="text-xs text-gray-500">
                  {status.prospects_with_source.toLocaleString()} with source, {status.prospects_without_source.toLocaleString()} orphaned
                </p>
              </div>
              <div>
                <h4 className="font-medium text-gray-900">Prospect Types</h4>
                <div className="space-y-1">
                  <p className="text-sm">
                    <span className="font-semibold text-green-600">{status.original_count.toLocaleString()}</span>
                    <span className="text-gray-600"> original</span>
                  </p>
                  <p className="text-sm">
                    <span className="font-semibold text-purple-600">{status.ai_enriched_count.toLocaleString()}</span>
                    <span className="text-gray-600"> AI enriched</span>
                  </p>
                </div>
              </div>
              <div>
                <h4 className="font-medium text-gray-900">Data Sources</h4>
                <p className="text-2xl font-bold text-green-600">{status.data_source_count}</p>
              </div>
              <div>
                <h4 className="font-medium text-gray-900">Status Records</h4>
                <p className="text-2xl font-bold text-purple-600">{status.status_record_count.toLocaleString()}</p>
              </div>
              <div>
                <h4 className="font-medium text-gray-900">Database Size</h4>
                <p className="text-2xl font-bold text-orange-600">{formatFileSize(status.database_size_bytes)}</p>
              </div>
              <div>
                <h4 className="font-medium text-gray-900">Last Updated</h4>
                <p className="text-sm text-gray-600">{formatDate(status.timestamp)}</p>
              </div>
            </div>
          )}
          <div className="mt-4">
            <Button onClick={() => refetch()} variant="outline">
              Refresh Status
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Database Operations</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-6">
            {/* Clear AI Entries */}
            <div>
              <h4 className="font-medium text-gray-900 mb-2">Clear AI Entries Only</h4>
              <p className="text-sm text-gray-600 mb-3">
                Remove all AI-enriched prospects, enrichment logs, and LLM outputs. Original scraped data will remain.
              </p>
              <button 
                className="inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-all disabled:pointer-events-none disabled:opacity-50 bg-purple-600 text-white shadow-xs hover:bg-purple-700 h-9 px-4 py-2"
                disabled={isClearing}
                onClick={() => {
                  if (window.confirm(
                    `Are you sure you want to clear all AI entries? This action cannot be undone.\n\n` +
                    `This will delete:\n` +
                    `• ${status?.ai_enriched_count.toLocaleString()} AI-enriched prospects\n` +
                    `• All AI enrichment logs\n` +
                    `• All LLM outputs`
                  )) {
                    clearAIMutation.mutate();
                  }
                }}
              >
                {clearAIMutation.isPending ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-t-2 border-b-2 border-white mr-2"></div>
                    Clearing AI Entries...
                  </>
                ) : (
                  'Clear AI Entries'
                )}
              </button>
            </div>

            {/* Clear Original Entries */}
            <div>
              <h4 className="font-medium text-gray-900 mb-2">Clear Original Entries Only</h4>
              <p className="text-sm text-gray-600 mb-3">
                Remove all non-AI-enriched (original scraped) prospects. AI-enriched data will remain.
              </p>
              <button 
                className="inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-all disabled:pointer-events-none disabled:opacity-50 bg-orange-600 text-white shadow-xs hover:bg-orange-700 h-9 px-4 py-2"
                disabled={isClearing}
                onClick={() => {
                  if (window.confirm(
                    `Are you sure you want to clear all original entries? This action cannot be undone.\n\n` +
                    `This will delete:\n` +
                    `• ${status?.original_count.toLocaleString()} original prospects`
                  )) {
                    clearOriginalMutation.mutate();
                  }
                }}
              >
                {clearOriginalMutation.isPending ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-t-2 border-b-2 border-white mr-2"></div>
                    Clearing Original Entries...
                  </>
                ) : (
                  'Clear Original Entries'
                )}
              </button>
            </div>

            {/* Clear All */}
            <div>
              <h4 className="font-medium text-gray-900 mb-2">Clear All Database</h4>
              <p className="text-sm text-gray-600 mb-3">
                This will permanently delete ALL prospects and scraper status records from the database. 
                Data sources will remain but their last_scraped timestamps will be reset.
              </p>
              <button 
                className="inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-all disabled:pointer-events-none disabled:opacity-50 bg-red-600 text-white shadow-xs hover:bg-red-700 h-9 px-4 py-2"
                disabled={isClearing}
                onClick={() => {
                  if (window.confirm(
                    `Are you sure you want to clear the ENTIRE database? This action cannot be undone.\n\n` +
                    `This will delete:\n` +
                    `• ${status?.prospect_count.toLocaleString()} total prospects\n` +
                    `• ${status?.status_record_count.toLocaleString()} scraper status records\n` +
                    `• All last_scraped timestamps`
                  )) {
                    clearDatabaseMutation.mutate();
                  }
                }}
              >
                {clearDatabaseMutation.isPending ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-t-2 border-b-2 border-white mr-2"></div>
                    Clearing All...
                  </>
                ) : (
                  'Clear All Database'
                )}
              </button>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>AI Data Preservation Settings</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoadingConfig ? (
            <div className="flex items-center justify-center h-16">
              <div className="animate-spin rounded-full h-6 w-6 border-t-2 border-b-2 border-blue-600"></div>
            </div>
          ) : (
            <div className="space-y-4">
              <div>
                <h4 className="font-medium text-gray-900 mb-2">Preserve AI-Enhanced Data During Refreshes</h4>
                <p className="text-sm text-gray-600 mb-4">
                  {aiConfigData?.data?.description || 'Controls whether AI-enhanced fields are preserved when data sources are refreshed.'}
                </p>
                <div className="flex items-center space-x-4">
                  <div className="flex items-center space-x-2">
                    <span className="text-sm font-medium">
                      Current Setting: 
                      <span className={`ml-2 px-2 py-1 rounded-full text-xs font-semibold ${
                        aiConfigData?.data?.preserve_ai_data_on_refresh 
                          ? 'bg-green-100 text-green-800' 
                          : 'bg-red-100 text-red-800'
                      }`}>
                        {aiConfigData?.data?.preserve_ai_data_on_refresh ? 'ENABLED' : 'DISABLED'}
                      </span>
                    </span>
                  </div>
                </div>
                <div className="flex space-x-2 mt-4">
                  <button 
                    className="inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-all disabled:pointer-events-none disabled:opacity-50 bg-green-600 text-white shadow-xs hover:bg-green-700 h-9 px-4 py-2"
                    disabled={updateAIConfigMutation.isPending || aiConfigData?.data?.preserve_ai_data_on_refresh}
                    onClick={() => updateAIConfigMutation.mutate(true)}
                  >
                    {updateAIConfigMutation.isPending ? (
                      <div className="animate-spin rounded-full h-4 w-4 border-t-2 border-b-2 border-white mr-2"></div>
                    ) : null}
                    Enable Protection
                  </button>
                  <button 
                    className="inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-all disabled:pointer-events-none disabled:opacity-50 bg-orange-600 text-white shadow-xs hover:bg-orange-700 h-9 px-4 py-2"
                    disabled={updateAIConfigMutation.isPending || !aiConfigData?.data?.preserve_ai_data_on_refresh}
                    onClick={() => {
                      if (window.confirm(
                        'Are you sure you want to disable AI data preservation?\\n\\n' +
                        'This will allow data source refreshes to overwrite AI-enhanced fields like:\\n' +
                        '• NAICS codes and descriptions\\n' +
                        '• Parsed contact information\\n' +
                        '• LLM-enhanced values\\n\\n' +
                        'Consider this carefully as it may undo AI processing work.'
                      )) {
                        updateAIConfigMutation.mutate(false);
                      }
                    }}
                  >
                    {updateAIConfigMutation.isPending ? (
                      <div className="animate-spin rounded-full h-4 w-4 border-t-2 border-b-2 border-white mr-2"></div>
                    ) : null}
                    Disable Protection
                  </button>
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}