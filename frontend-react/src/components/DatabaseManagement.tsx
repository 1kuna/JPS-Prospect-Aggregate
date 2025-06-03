import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface DatabaseStatus {
  prospect_count: number;
  prospects_with_source: number;
  prospects_without_source: number;
  data_source_count: number;
  status_record_count: number;
  database_size_bytes: number | null;
  timestamp: string;
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

  // Mutation for clearing database
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
    },
    onError: (error: Error) => {
      alert(`Failed to clear database: ${error.message}`);
    },
    onSettled: () => {
      setIsClearing(false);
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

  const handleClearDatabase = () => {
    clearDatabaseMutation.mutate();
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
              <div className="col-span-2">
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
          <div className="space-y-4">
            <div>
              <h4 className="font-medium text-gray-900 mb-2">Clear Database</h4>
              <p className="text-sm text-gray-600 mb-3">
                This will permanently delete all prospects and scraper status records from the database. 
                Data sources will remain but their last_scraped timestamps will be reset.
              </p>
              <button 
                className="inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-all disabled:pointer-events-none disabled:opacity-50 bg-red-600 text-white shadow-xs hover:bg-red-700 h-9 px-4 py-2"
                disabled={isClearing}
                onClick={() => {
                  if (window.confirm(
                    `Are you sure you want to clear the database? This action cannot be undone.\n\n` +
                    `This will delete:\n` +
                    `• ${status?.prospect_count.toLocaleString()} prospects\n` +
                    `• ${status?.status_record_count.toLocaleString()} scraper status records\n` +
                    `• All last_scraped timestamps`
                  )) {
                    handleClearDatabase();
                  }
                }}
              >
                {isClearing ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-t-2 border-b-2 border-white mr-2"></div>
                    Clearing...
                  </>
                ) : (
                  'Clear Database'
                )}
              </button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}