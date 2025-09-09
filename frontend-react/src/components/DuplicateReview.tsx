import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { formatDate } from '@/utils/dateUtils';
import { get, post } from '@/utils/apiUtils';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { DuplicateScanProgress } from '@/types';
import { useToast } from '@/contexts/ToastContext';
import { useConfirmationDialog } from '@/components/ui/ConfirmationDialog';
import { ErrorSeverity, ErrorCategory } from '@/types/errors';

interface DataSource {
  id: number;
  name: string;
  prospect_count: number;
}

interface ProspectSummary {
  id: string;
  native_id: string;
  title: string;
  description: string;
  agency: string;
  naics: string;
  place_city: string;
  place_state: string;
  ai_processed: boolean;
  loaded_at: string;
}

interface DuplicateMatch extends ProspectSummary {
  confidence_score: number;
  match_type: string;
  matched_fields: string[];
}

interface DuplicateGroup {
  original: ProspectSummary;
  matches: DuplicateMatch[];
}

interface DuplicateDetectionResult {
  potential_duplicates: DuplicateGroup[];
  total_found: number;
  scan_parameters: {
    source_id?: number;
    min_confidence: number;
    limit: number;
  };
}

export function DuplicateReview() {
  const queryClient = useQueryClient();
  const { showSuccessToast, showErrorToast, showWarningToast } = useToast();
  const { confirm, ConfirmationDialog } = useConfirmationDialog();
  const [selectedSourceId, setSelectedSourceId] = useState<number | null>(null);
  const [minConfidence, setMinConfidence] = useState(0.8);
  const [scanLimit, setScanLimit] = useState<number | null>(null); // null means "All" (default)
  const [selectedGroups, setSelectedGroups] = useState<Set<number>>(new Set());
  const [selectedKeepRecords, setSelectedKeepRecords] = useState<Map<number, string>>(new Map()); // groupIndex -> recordId to keep
  const [currentScanId, setCurrentScanId] = useState<string | null>(null);
  const [scanProgress, setScanProgress] = useState<DuplicateScanProgress | null>(null);

  // Fetch data sources for filtering
  const { data: sourcesData } = useQuery<{ status: string; data: { sources: DataSource[] } }>({
    queryKey: ['duplicateSources'],
    queryFn: () => get<{ status: string; data: { sources: DataSource[] } }>('/api/duplicates/sources'),
  });

  // Progress polling query
  const { data: progressData } = useQuery<{ data: DuplicateScanProgress } | null>({
    queryKey: ['duplicateProgress', currentScanId],
    queryFn: () => currentScanId ? get<{ data: DuplicateScanProgress }>(`/api/duplicates/progress/${currentScanId}`) : null,
    enabled: !!currentScanId,
    refetchInterval: currentScanId ? 1000 : false, // Poll every second when scanning
  });

  // Duplicate detection query
  const {
    data: duplicatesData,
    isLoading: isDetecting,
    error: detectError,
    refetch: detectDuplicates,
  } = useQuery<{ status: string; data: DuplicateDetectionResult & { scan_id?: string } }>({
    queryKey: ['duplicateDetection', selectedSourceId, minConfidence, scanLimit],
    queryFn: async () => {
      setScanProgress(null);
      setCurrentScanId(null);
      
      const result = await post<{ status: string; data: DuplicateDetectionResult & { scan_id?: string } }>('/api/duplicates/detect', {
        source_id: selectedSourceId,
        min_confidence: minConfidence,
        limit: scanLimit || 10000, // Use a high number when "All" is selected
      });
      
      // Set scan ID for progress tracking if provided
      if (result.data?.scan_id) {
        // Setting scan ID
        setCurrentScanId(result.data.scan_id);
      } else {
        // No scan_id in response
      }
      
      // Response received
      
      return result;
    },
    enabled: false, // Only run when manually triggered
  });

  // Merge duplicates mutation
  const mergeDuplicatesMutation = useMutation({
    mutationFn: async ({ keepId, removeIds }: { keepId: string; removeIds: string[] }) => {
      const response = await fetch('/api/duplicates/merge', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          keep_id: keepId,
          remove_ids: removeIds,
        }),
      });
      if (!response.ok) {
        throw new Error('Failed to merge duplicates');
      }
      return response.json();
    },
    onSuccess: (data) => {
      showSuccessToast('Duplicates Merged', data.data.message || 'Duplicates merged successfully!');
      // Refresh the detection results
      detectDuplicates();
      // Clear selections
      setSelectedGroups(new Set());
      // Invalidate related queries
      queryClient.invalidateQueries({ queryKey: ['databaseStatus'] });
      queryClient.invalidateQueries({ queryKey: ['prospects'] });
    },
    onError: (error: Error) => {
      showErrorToast({
        code: 'MERGE_DUPLICATES_ERROR',
        message: error.message,
        severity: ErrorSeverity.ERROR,
        category: ErrorCategory.SYSTEM,
        timestamp: new Date(),
        userMessage: `Failed to merge duplicates: ${error.message}`,
      });
    },
  });

  const handleGroupSelection = (groupIndex: number, selected: boolean) => {
    const newSelected = new Set(selectedGroups);
    const newKeepRecords = new Map(selectedKeepRecords);
    
    if (selected) {
      newSelected.add(groupIndex);
      // Default to keeping the original record when group is first selected
      const group = duplicateGroups[groupIndex];
      if (group && !newKeepRecords.has(groupIndex)) {
        newKeepRecords.set(groupIndex, group.original.id);
      }
    } else {
      newSelected.delete(groupIndex);
      newKeepRecords.delete(groupIndex);
    }
    
    setSelectedGroups(newSelected);
    setSelectedKeepRecords(newKeepRecords);
  };

  const handleKeepRecordSelection = (groupIndex: number, recordId: string) => {
    const newKeepRecords = new Map(selectedKeepRecords);
    newKeepRecords.set(groupIndex, recordId);
    setSelectedKeepRecords(newKeepRecords);
  };

  const handleMergeSelected = async () => {
    if (selectedGroups.size === 0) {
      showWarningToast('No Selection', 'Please select at least one duplicate group to merge.');
      return;
    }

    const groupsToMerge = Array.from(selectedGroups)
      .map((index) => duplicatesData?.data.potential_duplicates[index])
      .filter((group): group is DuplicateGroup => group !== undefined);

    if (groupsToMerge.length === 0) return;

    const totalMerges = groupsToMerge.reduce((sum, group) => sum + group.matches.length, 0);
    
    const confirmed = await confirm({
      title: `Merge ${totalMerges} Duplicate Record${totalMerges !== 1 ? 's' : ''}`,
      description: 'Are you sure you want to merge the selected duplicate records?',
      details: [
        'Keep your selected record from each group',
        'Delete all other duplicate matches',
        'Preserve AI-enhanced data when possible',
        '',
        'This action cannot be undone.'
      ],
      confirmLabel: 'Merge Duplicates',
      variant: 'destructive'
    });
    
    if (!confirmed) {
      return;
    }

    // Process merges sequentially using selected keep records
    Array.from(selectedGroups).forEach((groupIndex) => {
      const group = duplicateGroups[groupIndex];
      if (group) {
        const keepId = selectedKeepRecords.get(groupIndex) || group.original.id;
        
        // Build remove list - all records except the one we're keeping
        const allRecords = [group.original, ...group.matches];
        const removeIds = allRecords
          .filter(record => record.id !== keepId)
          .map(record => record.id);
        
        mergeDuplicatesMutation.mutate({ keepId, removeIds });
      }
    });
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.9) return 'text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-950/20';
    if (confidence >= 0.8) return 'text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/20';
    if (confidence >= 0.7) return 'text-yellow-600 dark:text-yellow-400 bg-yellow-50 dark:bg-yellow-950/20';
    return 'text-muted-foreground bg-muted';
  };

  const getMatchTypeColor = (matchType: string) => {
    switch (matchType) {
      case 'exact': return 'bg-red-100 dark:bg-red-950/50 text-red-800 dark:text-red-400';
      case 'strong': return 'bg-amber-100 dark:bg-amber-950/50 text-amber-800 dark:text-amber-400';
      case 'fuzzy': return 'bg-yellow-100 dark:bg-yellow-950/50 text-yellow-800 dark:text-yellow-400';
      case 'weak': return 'bg-muted text-muted-foreground';
      default: return 'bg-muted text-muted-foreground';
    }
  };

  const duplicateGroups = duplicatesData?.data?.potential_duplicates || [];

  // Update scan progress from polling
  React.useEffect(() => {
    // Progress polling effect triggered
    if (progressData?.data) {
      // Progress update received
      setScanProgress(progressData.data);
      
      // Stop polling when scan is complete and show results
      if (progressData.data.status === 'completed' && progressData.data.results) {
        // Scan finished with results, updating duplicate data
        
        // Update the duplicates query cache with the results
        queryClient.setQueryData(
          ['duplicateDetection', selectedSourceId, minConfidence, scanLimit],
          {
            status: 'success',
            data: progressData.data.results
          }
        );
        
        setCurrentScanId(null);
      } else if (progressData.data.status === 'error') {
        // Scan failed, stopping polling
        
        // Set error state in the duplicates query cache
        queryClient.setQueryData(
          ['duplicateDetection', selectedSourceId, minConfidence, scanLimit],
          {
            status: 'error',
            error: new Error(progressData.data.message || 'Duplicate scan failed')
          }
        );
        
        setCurrentScanId(null);
      }
    }
  }, [progressData, queryClient, selectedSourceId, minConfidence, scanLimit]);


  const renderProgressBar = () => {
    // Show progress bar when detecting (regardless of progress data)
    if (!isDetecting) return null;

    // If we have progress data with error status, show error
    if (scanProgress && scanProgress.status === 'error') {
      return (
        <div className="bg-red-50 dark:bg-red-950/20 border border-red-200 dark:border-red-800 rounded-md p-4 mb-4">
          <div className="flex items-center">
            <div className="text-red-600 dark:text-red-400 mr-3">❌</div>
            <span className="text-sm font-medium text-red-800 dark:text-red-400">
              Scan Failed: {scanProgress.message || 'An error occurred during duplicate detection'}
            </span>
          </div>
        </div>
      );
    }

    // If we have actual progress data, show detailed progress
    if (scanProgress && scanProgress.total && scanProgress.total > 0) {
      const percentage = scanProgress.percentage || 0;
      const eta = scanProgress.eta;

      return (
        <div className="bg-primary/10 border border-primary/20 rounded-md p-4 mb-4">
          <div className="flex justify-between items-center mb-2">
            <span className="text-sm font-medium text-primary">
              {scanProgress.message}
            </span>
            <span className="text-xs text-primary/80">
              {scanProgress.current} / {scanProgress.total} ({percentage}%)
            </span>
          </div>
          
          <div className="w-full bg-primary/20 rounded-full h-2 mb-2">
            <div
              className="bg-primary h-2 rounded-full transition-all duration-300"
              style={{ width: `${percentage}%` }}
            ></div>
          </div>
          
          <div className="flex justify-between text-xs text-primary">
            <span>Elapsed: {scanProgress.elapsed_time}s</span>
            {eta && <span>ETA: {eta}s</span>}
          </div>
        </div>
      );
    }

    // Fallback: show simple progress indicator
    return (
      <div className="bg-blue-50 border border-blue-200 rounded-md p-4 mb-4">
        <div className="flex items-center">
          <LoadingSpinner size="sm" inline className="mr-3" />
          <span className="text-sm font-medium text-blue-800">
            Scanning for duplicates... This may take a few minutes for large datasets.
          </span>
        </div>
        
        <div className="w-full bg-primary/20 rounded-full h-2 mt-3">
          <div className="bg-primary h-2 rounded-full animate-pulse"></div>
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Duplicate Detection & Review</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div>
                <label className="block text-sm font-medium text-foreground mb-2">
                  Data Source (Optional)
                </label>
                <select
                  value={selectedSourceId || ''}
                  onChange={(e) => setSelectedSourceId(e.target.value ? parseInt(e.target.value) : null)}
                  className="w-full px-3 py-2 border border-border rounded-md bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary"
                >
                  <option value="">All Sources</option>
                  {sourcesData?.data.sources.map((source) => (
                    <option key={source.id} value={source.id}>
                      {source.name} ({source.prospect_count})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-foreground mb-2">
                  Min Confidence
                </label>
                <select
                  value={minConfidence}
                  onChange={(e) => setMinConfidence(parseFloat(e.target.value))}
                  className="w-full px-3 py-2 border border-border rounded-md bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary"
                >
                  <option value={0.6}>60% - Very Loose</option>
                  <option value={0.7}>70% - Loose</option>
                  <option value={0.8}>80% - Moderate</option>
                  <option value={0.9}>90% - Strict</option>
                  <option value={0.95}>95% - Very Strict</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-foreground mb-2">
                  Scan Limit
                </label>
                <select
                  value={scanLimit === null ? 'all' : scanLimit}
                  onChange={(e) => setScanLimit(e.target.value === 'all' ? null : parseInt(e.target.value))}
                  className="w-full px-3 py-2 border border-border rounded-md bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary"
                >
                  <option value="all">All Records (Recommended)</option>
                  <option value={100}>100 Records (Quick Test)</option>
                  <option value={500}>500 Records (Medium Test)</option>
                  <option value={1000}>1000 Records (Large Test)</option>
                </select>
              </div>

              <div className="flex items-end">
                <button
                  onClick={() => detectDuplicates()}
                  disabled={isDetecting}
                  className="w-full inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-all disabled:pointer-events-none disabled:opacity-50 bg-primary text-primary-foreground shadow-sm hover:bg-primary/80 h-9 px-4 py-2 border border-primary"
                >
                  {isDetecting ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-t-2 border-b-2 border-white mr-2"></div>
                      Scanning...
                    </>
                  ) : (
                    'Scan for Duplicates'
                  )}
                </button>
              </div>
            </div>

            {/* Progress Bar */}
            {renderProgressBar()}

            {detectError && (
              <div className="bg-red-50 dark:bg-red-950/20 border border-red-200 dark:border-red-800 rounded-md p-4">
                <p className="text-red-800 dark:text-red-400">Error: {(detectError as Error).message}</p>
              </div>
            )}

            {duplicatesData?.data && (
              <div className="bg-primary/10 border border-primary/20 rounded-md p-4">
                <p className="text-primary">
                  Found {duplicatesData.data.total_found || 0} potential duplicate group(s)
                  {duplicatesData.data.scan_parameters?.source_id && (
                    <> in source {sourcesData?.data?.sources?.find(s => s.id === duplicatesData.data.scan_parameters.source_id)?.name}</>
                  )}
                  {(duplicatesData.data.scan_parameters?.limit || 0) >= 10000 ? (
                    <> (scanned all records)</>
                  ) : (
                    <> (scanned {duplicatesData.data.scan_parameters?.limit || 0} records)</>
                  )}
                  .
                </p>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {duplicateGroups.length > 0 && (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Potential Duplicates ({duplicateGroups.length} groups)</CardTitle>
            <div className="flex space-x-2">
              <button
                onClick={() => {
                  const allGroupIndexes = duplicateGroups.map((_, i: number) => i);
                  setSelectedGroups(new Set(allGroupIndexes));
                  
                  // Initialize keep records for all groups (default to original)
                  const newKeepRecords = new Map(selectedKeepRecords);
                  allGroupIndexes.forEach((groupIndex: number) => {
                    if (!newKeepRecords.has(groupIndex)) {
                      const group = duplicateGroups[groupIndex];
                      if (group) {
                        newKeepRecords.set(groupIndex, group.original.id);
                      }
                    }
                  });
                  setSelectedKeepRecords(newKeepRecords);
                }}
                className="inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-all disabled:pointer-events-none disabled:opacity-50 border border-border bg-background text-foreground shadow-sm hover:bg-accent h-8 px-3 py-1"
              >
                Select All
              </button>
              <button
                onClick={() => {
                  setSelectedGroups(new Set());
                  setSelectedKeepRecords(new Map());
                }}
                className="inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-all disabled:pointer-events-none disabled:opacity-50 border border-border bg-background text-foreground shadow-sm hover:bg-accent h-8 px-3 py-1"
              >
                Clear All
              </button>
              <button
                onClick={handleMergeSelected}
                disabled={selectedGroups.size === 0 || mergeDuplicatesMutation.isPending}
                className="inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-all disabled:pointer-events-none disabled:opacity-50 bg-destructive text-destructive-foreground shadow-sm hover:bg-destructive/80 h-8 px-3 py-1 border border-destructive"
              >
                {mergeDuplicatesMutation.isPending ? (
                  <>
                    <div className="animate-spin rounded-full h-3 w-3 border-t-2 border-b-2 border-white mr-1"></div>
                    Merging...
                  </>
                ) : (
                  `Merge Selected (${selectedGroups.size})`
                )}
              </button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-6">
              {duplicateGroups.map((group: DuplicateGroup, groupIndex: number) => (
                <div
                  key={groupIndex}
                  className={`border rounded-lg p-4 ${
                    selectedGroups.has(groupIndex) ? 'border-primary bg-primary/10' : 'border-border'
                  }`}
                >
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-lg font-semibold">Group {groupIndex + 1}</h3>
                    <label className="flex items-center space-x-2">
                      <input
                        type="checkbox"
                        checked={selectedGroups.has(groupIndex)}
                        onChange={(e) => handleGroupSelection(groupIndex, e.target.checked)}
                        className="h-4 w-4"
                      />
                      <span className="text-sm font-medium">Select for merge</span>
                    </label>
                  </div>

                  {/* Record Selection Instructions */}
                  {selectedGroups.has(groupIndex) && (
                    <div className="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded-md">
                      <p className="text-sm font-medium text-yellow-800 mb-2">
                        🔄 Choose which record to keep (others will be deleted):
                      </p>
                    </div>
                  )}

                  {/* Original Record */}
                  <div className="mb-4">
                    <div className="flex items-center justify-between mb-2">
                      <h4 className="font-medium text-emerald-800 dark:text-emerald-400 flex items-center">
                        📍 Original Record
                        {group.original.ai_processed && (
                          <span className="ml-2 px-2 py-1 bg-violet-100 dark:bg-violet-950/50 text-violet-800 dark:text-violet-400 text-xs rounded-full">
                            AI Enhanced
                          </span>
                        )}
                      </h4>
                      {selectedGroups.has(groupIndex) && (
                        <label className="flex items-center space-x-2">
                          <input
                            type="radio"
                            name={`keep-record-${groupIndex}`}
                            checked={selectedKeepRecords.get(groupIndex) === group.original.id}
                            onChange={() => handleKeepRecordSelection(groupIndex, group.original.id)}
                            className="h-4 w-4 text-emerald-600 dark:text-emerald-400"
                          />
                          <span className="text-sm font-medium text-emerald-700 dark:text-emerald-400">Keep this record</span>
                        </label>
                      )}
                    </div>
                    <div className={`rounded p-3 text-sm border ${
                      selectedGroups.has(groupIndex) && selectedKeepRecords.get(groupIndex) === group.original.id 
                        ? 'bg-emerald-100 dark:bg-emerald-950/30 border-emerald-300 dark:border-emerald-700' 
                        : 'bg-emerald-50 dark:bg-emerald-950/20 border-emerald-200 dark:border-emerald-800'
                    }`}>
                      <div className="grid grid-cols-2 gap-2">
                        <div><strong>ID:</strong> {group.original.native_id || 'N/A'}</div>
                        <div><strong>Agency:</strong> {group.original.agency || 'N/A'}</div>
                        <div><strong>NAICS:</strong> {group.original.naics || 'N/A'}</div>
                        <div><strong>Location:</strong> {group.original.place_city}, {group.original.place_state}</div>
                      </div>
                      <div className="mt-2">
                        <div><strong>Title:</strong> {group.original.title}</div>
                        <div><strong>Description:</strong> {group.original.description}</div>
                      </div>
                      <div className="text-xs text-muted-foreground mt-2">
                        Loaded: {formatDate(group.original.loaded_at)}
                      </div>
                    </div>
                  </div>

                  {/* Duplicate Matches */}
                  <div>
                    <h4 className="font-medium text-red-800 dark:text-red-400 mb-2">
                      🔄 Potential Duplicates ({group.matches.length})
                    </h4>
                    <div className="space-y-3">
                      {group.matches.map((match: DuplicateMatch, matchIndex: number) => (
                        <div key={matchIndex} className={`rounded p-3 text-sm border ${
                          selectedGroups.has(groupIndex) && selectedKeepRecords.get(groupIndex) === match.id
                            ? 'bg-primary/20 border-primary/40'
                            : 'bg-red-50 dark:bg-red-950/20 border-red-200 dark:border-red-800'
                        }`}>
                          <div className="flex justify-between items-start mb-2">
                            <div className="flex space-x-2">
                              <span className={`px-2 py-1 rounded-full text-xs font-semibold ${getConfidenceColor(match.confidence_score)}`}>
                                {(match.confidence_score * 100).toFixed(1)}% confidence
                              </span>
                              <span className={`px-2 py-1 rounded-full text-xs font-semibold ${getMatchTypeColor(match.match_type)}`}>
                                {match.match_type}
                              </span>
                              {match.ai_processed && (
                                <span className="px-2 py-1 bg-violet-100 dark:bg-violet-950/50 text-violet-800 dark:text-violet-400 text-xs rounded-full">
                                  AI Enhanced
                                </span>
                              )}
                            </div>
                            <div className="flex items-center space-x-4">
                              <div className="text-xs text-gray-500">
                                Matched: {match.matched_fields.join(', ')}
                              </div>
                              {selectedGroups.has(groupIndex) && (
                                <label className="flex items-center space-x-2">
                                  <input
                                    type="radio"
                                    name={`keep-record-${groupIndex}`}
                                    checked={selectedKeepRecords.get(groupIndex) === match.id}
                                    onChange={() => handleKeepRecordSelection(groupIndex, match.id)}
                                    className="h-4 w-4 text-primary"
                                  />
                                  <span className="text-sm font-medium text-primary">Keep this record</span>
                                </label>
                              )}
                            </div>
                          </div>
                          <div className="grid grid-cols-2 gap-2">
                            <div><strong>ID:</strong> {match.native_id || 'N/A'}</div>
                            <div><strong>Agency:</strong> {match.agency || 'N/A'}</div>
                            <div><strong>NAICS:</strong> {match.naics || 'N/A'}</div>
                            <div><strong>Location:</strong> {match.place_city}, {match.place_state}</div>
                          </div>
                          <div className="mt-2">
                            <div><strong>Title:</strong> {match.title}</div>
                            <div><strong>Description:</strong> {match.description}</div>
                          </div>
                          <div className="text-xs text-muted-foreground mt-2">
                            Loaded: {formatDate(match.loaded_at)}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {duplicatesData && duplicateGroups.length === 0 && (
        <Card>
          <CardContent className="text-center py-8">
            <div className="text-emerald-600 dark:text-emerald-400 text-lg font-medium mb-2">
              ✅ No Duplicates Found!
            </div>
            <p className="text-muted-foreground">
              No potential duplicates were detected with the current confidence threshold.
              Try lowering the confidence level if you suspect there might be duplicates.
            </p>
          </CardContent>
        </Card>
      )}
      
      {ConfirmationDialog}
    </div>
  );
}