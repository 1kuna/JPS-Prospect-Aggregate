import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { 
  useAIEnrichmentStatus, 
  useAIEnrichmentLogs, 
  useAIEnrichmentMutation,
  type AIEnrichmentRequest 
} from '@/hooks/api/useAIEnrichment';

export function AIEnrichment() {
  const [enhancementType, setEnhancementType] = useState<'values' | 'contacts' | 'naics' | 'all'>('all');
  const [limit, setLimit] = useState<string>('100');
  
  const { data: status, isLoading: isLoadingStatus } = useAIEnrichmentStatus();
  const { data: logs, isLoading: isLoadingLogs } = useAIEnrichmentLogs();
  const enhancementMutation = useAIEnrichmentMutation();

  const handleTriggerEnrichment = () => {
    const request: AIEnrichmentRequest = {
      enhancement_type: enhancementType,
      limit: limit ? parseInt(limit) : undefined,
    };
    
    enhancementMutation.mutate(request);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString();
  };

  const formatDuration = (duration: number) => {
    if (duration < 60) {
      return `${duration.toFixed(1)}s`;
    }
    const minutes = Math.floor(duration / 60);
    const seconds = duration % 60;
    return `${minutes}m ${seconds.toFixed(0)}s`;
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'success':
        return 'text-green-600';
      case 'failed':
        return 'text-red-600';
      case 'in_progress':
        return 'text-blue-600';
      default:
        return 'text-gray-600';
    }
  };

  return (
    <div className="space-y-6">
      {/* Status Overview */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center">
            AI Enrichment Status
            {status?.total_prospects && (
              <div className="ml-auto text-sm font-normal text-gray-600">
                {status.processed_prospects.toLocaleString()} of {status.total_prospects.toLocaleString()} processed
              </div>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoadingStatus ? (
            <div className="flex items-center justify-center h-32">
              <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-blue-600"></div>
            </div>
          ) : status ? (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {/* NAICS Coverage */}
              <div className="bg-blue-50 p-4 rounded-lg border border-blue-200">
                <h4 className="font-semibold text-blue-800 mb-2">NAICS Classification</h4>
                <div className="space-y-1 text-sm">
                  <div className="flex justify-between">
                    <span>Original:</span>
                    <span className="font-medium">{status.naics_coverage.original.toLocaleString()}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>AI Classified:</span>
                    <span className="font-medium text-blue-700">{status.naics_coverage.llm_inferred.toLocaleString()}</span>
                  </div>
                  <div className="flex justify-between border-t border-blue-300 pt-1 font-medium">
                    <span>Coverage:</span>
                    <span>{status.naics_coverage.total_percentage.toFixed(1)}%</span>
                  </div>
                </div>
              </div>

              {/* Value Parsing */}
              <div className="bg-green-50 p-4 rounded-lg border border-green-200">
                <h4 className="font-semibold text-green-800 mb-2">Value Parsing</h4>
                <div className="space-y-1 text-sm">
                  <div className="flex justify-between">
                    <span>Parsed Values:</span>
                    <span className="font-medium text-green-700">{status.value_parsing.parsed_count.toLocaleString()}</span>
                  </div>
                  <div className="flex justify-between border-t border-green-300 pt-1 font-medium">
                    <span>Coverage:</span>
                    <span>{status.value_parsing.total_percentage.toFixed(1)}%</span>
                  </div>
                </div>
              </div>

              {/* Contact Extraction */}
              <div className="bg-orange-50 p-4 rounded-lg border border-orange-200">
                <h4 className="font-semibold text-orange-800 mb-2">Contact Extraction</h4>
                <div className="space-y-1 text-sm">
                  <div className="flex justify-between">
                    <span>Extracted Contacts:</span>
                    <span className="font-medium text-orange-700">{status.contact_extraction.extracted_count.toLocaleString()}</span>
                  </div>
                  <div className="flex justify-between border-t border-orange-300 pt-1 font-medium">
                    <span>Coverage:</span>
                    <span>{status.contact_extraction.total_percentage.toFixed(1)}%</span>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="text-red-600">Failed to load AI enrichment status</div>
          )}

          {status?.last_processed && (
            <div className="mt-4 text-sm text-gray-600 border-t pt-4">
              <div className="flex justify-between">
                <span>Last processed:</span>
                <span>{formatDate(status.last_processed)}</span>
              </div>
              {status.model_version && (
                <div className="flex justify-between">
                  <span>Model version:</span>
                  <span className="font-mono">{status.model_version}</span>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Control Panel */}
      <Card>
        <CardHeader>
          <CardTitle>AI Enrichment Controls</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="space-y-2">
                <Label htmlFor="enhancement-type">Enhancement Type</Label>
                <Select value={enhancementType} onValueChange={(value: 'values' | 'contacts' | 'naics' | 'all') => setEnhancementType(value)}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Enhancements</SelectItem>
                    <SelectItem value="values">Value Parsing</SelectItem>
                    <SelectItem value="contacts">Contact Extraction</SelectItem>
                    <SelectItem value="naics">NAICS Classification</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="limit">Limit (optional)</Label>
                <Input
                  id="limit"
                  type="number"
                  placeholder="e.g., 100"
                  value={limit}
                  onChange={(e) => setLimit(e.target.value)}
                />
              </div>

              <div className="space-y-2">
                <Label>&nbsp;</Label>
                <Button
                  onClick={handleTriggerEnrichment}
                  disabled={enhancementMutation.isPending}
                  className="w-full bg-blue-600 hover:bg-blue-700"
                >
                  {enhancementMutation.isPending ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-t-2 border-b-2 border-white mr-2"></div>
                      Processing...
                    </>
                  ) : (
                    'Start Enhancement'
                  )}
                </Button>
              </div>
            </div>

            {enhancementMutation.isError && (
              <div className="text-red-600 text-sm mt-2">
                Error: {enhancementMutation.error?.message || 'Failed to start enhancement'}
              </div>
            )}

            {enhancementMutation.isSuccess && enhancementMutation.data && (
              <div className="bg-green-50 border border-green-200 p-3 rounded-lg mt-2">
                <div className="text-green-800 font-medium">{enhancementMutation.data.message}</div>
                <div className="text-green-700 text-sm mt-1">
                  Processed {enhancementMutation.data.processed_count} records in {formatDuration(enhancementMutation.data.duration)}
                </div>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Recent Activity Log */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Activity</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoadingLogs ? (
            <div className="flex items-center justify-center h-32">
              <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-blue-600"></div>
            </div>
          ) : logs && logs.length > 0 ? (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Timestamp</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Records</TableHead>
                    <TableHead>Duration</TableHead>
                    <TableHead>Message</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {logs.map((log) => (
                    <TableRow key={log.id}>
                      <TableCell className="text-sm">
                        {formatDate(log.timestamp)}
                      </TableCell>
                      <TableCell>
                        <span className="px-2 py-1 bg-gray-100 text-gray-700 text-xs rounded">
                          {log.enhancement_type}
                        </span>
                      </TableCell>
                      <TableCell>
                        <span className={`font-medium ${getStatusColor(log.status)}`}>
                          {log.status}
                        </span>
                      </TableCell>
                      <TableCell className="font-mono text-sm">
                        {log.processed_count.toLocaleString()}
                      </TableCell>
                      <TableCell className="text-sm">
                        {formatDuration(log.duration)}
                      </TableCell>
                      <TableCell className="text-sm text-gray-600">
                        {log.message || log.error}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          ) : (
            <div className="text-center py-8 text-gray-500">
              No recent activity found
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}