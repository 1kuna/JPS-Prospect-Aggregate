import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Label } from '@/components/ui/label';
import { useTimezoneDate } from '@/hooks/useTimezoneDate';
import { useEnhancementQueueService } from '@/hooks/api/useEnhancementQueueService';
import { getStatusColor } from '@/utils/statusUtils';
import { PlayIcon, StopIcon, ChevronDownIcon, ChevronRightIcon } from '@radix-ui/react-icons';

type EnhancementType = 'all' | 'values' | 'naics' | 'naics_code' | 'naics_description' | 'titles' | 'set_asides';

export function AIEnrichment() {
  const [enhancementType, setEnhancementType] = useState<EnhancementType>('all');
  const [skipExisting, setSkipExisting] = useState<'skip' | 'fill'>('skip');
  const [expandedOutputs, setExpandedOutputs] = useState<Set<number>>(new Set());
  const [isLocalProcessing, setIsLocalProcessing] = useState(false);
  
  const { formatLastProcessed, formatUserDate } = useTimezoneDate();
  
  const {
    enrichmentStatus: status,
    iterativeProgress: progress,
    llmOutputs,
    isLoadingEnrichment: isLoadingStatus,
    isLoadingLLMOutputs: isLoadingOutputs,
    startIterative,
    stopIterative,
    isStartingIterative,
    isStoppingIterative
  } = useEnhancementQueueService({
    llmOutputsType: enhancementType
  });

  // Sync local processing state with server state
  useEffect(() => {
    if (progress?.status === 'idle' || progress?.status === 'completed' || progress?.status === 'error') {
      setIsLocalProcessing(false);
    } else if (progress?.status === 'processing' || progress?.status === 'stopping') {
      setIsLocalProcessing(true);
    }
  }, [progress?.status]);

  const isProcessing = isLocalProcessing || progress?.status === 'processing' || progress?.status === 'stopping';

  const handleStart = () => {
    setIsLocalProcessing(true);
    startIterative({ 
      enhancement_type: enhancementType,
      skip_existing: skipExisting === 'skip'
    });
  };

  const handleStop = () => {
    setIsLocalProcessing(false);
    stopIterative();
  };

  // Removed local formatDate function - using timezone-aware formatting

  const toggleOutputExpanded = (outputId: number) => {
    setExpandedOutputs(prev => {
      const newSet = new Set(prev);
      if (newSet.has(outputId)) {
        newSet.delete(outputId);
      } else {
        newSet.add(outputId);
      }
      return newSet;
    });
  };


  return (
    <div className="space-y-6">
      {/* Top row: Status Overview and Controls side by side */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Status Overview - Takes up 3/4 of the space */}
        <Card className="lg:col-span-3">
          <CardHeader>
            <CardTitle className="flex items-center">
              AI Enrichment Status
              {status?.total_prospects && (
                <div className="ml-auto text-sm font-normal text-muted-foreground">
                  {(status?.processed_prospects ?? 0).toLocaleString()} of {(status?.total_prospects ?? 0).toLocaleString()} processed
                </div>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {isLoadingStatus ? (
              <div className="flex items-center justify-center h-32">
                <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-primary"></div>
              </div>
            ) : status ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                {/* NAICS Coverage */}
                <div className="bg-primary/10 dark:bg-primary/10 p-4 rounded-lg border border-primary/20 dark:border-primary/20">
                  <h4 className="font-semibold text-primary dark:text-primary mb-2">NAICS Classification</h4>
                  <div className="space-y-1 text-sm">
                    <div className="flex justify-between">
                      <span>Original:</span>
                      <span className="font-medium">{status?.naics_coverage?.original?.toLocaleString?.() ?? '0'}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>AI Classified:</span>
                      <span className="font-medium text-primary dark:text-primary">{status?.naics_coverage?.llm_inferred?.toLocaleString?.() ?? '0'}</span>
                    </div>
                    <div className="flex justify-between border-t border-primary/30 dark:border-primary/20 pt-1 font-medium">
                      <span>Coverage:</span>
                      <span>{(status?.naics_coverage?.total_percentage ?? 0).toFixed(1)}%</span>
                    </div>
                  </div>
                </div>

                {/* Value Parsing */}
                <div className="bg-success-light/10 dark:bg-success/10 p-4 rounded-lg border border-success/20 dark:border-success/20">
                  <h4 className="font-semibold text-success-dark dark:text-success mb-2">Value Parsing</h4>
                  <div className="space-y-1 text-sm">
                    <div className="flex justify-between">
                      <span>Parsed Values:</span>
                      <span className="font-medium text-success-dark dark:text-success">{status?.value_parsing?.parsed_count?.toLocaleString?.() ?? '0'}</span>
                    </div>
                    <div className="flex justify-between border-t border-emerald-500/30 dark:border-emerald-400/20 pt-1 font-medium">
                      <span>Coverage:</span>
                      <span>{(status?.value_parsing?.total_percentage ?? 0).toFixed(1)}%</span>
                    </div>
                  </div>
                </div>

                {/* Set-Aside Standardization */}
                <div className="bg-warning-light/10 dark:bg-warning/10 p-4 rounded-lg border border-warning/20 dark:border-warning/20">
                  <h4 className="font-semibold text-warning-dark dark:text-warning mb-2">Set-Aside Standardization</h4>
                  <div className="space-y-1 text-sm">
                    <div className="flex justify-between">
                      <span>Standardized Set-Asides:</span>
                      <span className="font-medium text-warning-dark dark:text-warning">{status?.set_aside_standardization?.standardized_count?.toLocaleString?.() ?? '0'}</span>
                    </div>
                    <div className="flex justify-between border-t border-amber-500/30 dark:border-amber-400/20 pt-1 font-medium">
                      <span>Coverage:</span>
                      <span>{(status?.set_aside_standardization?.total_percentage ?? 0).toFixed(1)}%</span>
                    </div>
                  </div>
                </div>

                {/* Title Enhancement */}
                <div className="bg-violet-500/10 dark:bg-violet-400/10 p-4 rounded-lg border border-violet-500/20 dark:border-violet-400/20">
                  <h4 className="font-semibold text-violet-700 dark:text-violet-300 mb-2">Title Enhancement</h4>
                  <div className="space-y-1 text-sm">
                    <div className="flex justify-between">
                      <span>Enhanced Titles:</span>
                      <span className="font-medium text-violet-700 dark:text-violet-300">{status.title_enhancement?.enhanced_count?.toLocaleString() || '0'}</span>
                    </div>
                    <div className="flex justify-between border-t border-violet-500/30 dark:border-violet-400/20 pt-1 font-medium">
                      <span>Coverage:</span>
                      <span>{status.title_enhancement?.total_percentage?.toFixed(1) || '0.0'}%</span>
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-danger">Failed to load AI enrichment status</div>
            )}

            {status?.last_processed && (
              <div className="mt-4 text-sm text-muted-foreground border-t pt-4">
                <div className="flex justify-between">
                  <span>Last processed:</span>
                  <span>{formatLastProcessed(status?.last_processed)}</span>
                </div>
                {status?.model_version && (
                  <div className="flex justify-between">
                    <span>Model version:</span>
                    <span className="font-mono">{status?.model_version}</span>
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>
        {/* Right Column: AI Enrichment Controls - Takes up 1/4 of the space */}
        <Card>
          <CardHeader>
            <CardTitle>Controls</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {/* Enhancement Type Selection */}
              <div className="space-y-2">
                <Label htmlFor="enhancement-type">Enhancement Type</Label>
                <Select 
                  value={enhancementType} 
                  onValueChange={(value: EnhancementType) => setEnhancementType(value)}
                  disabled={isProcessing}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Enhancements</SelectItem>
                    <SelectItem value="values">Value Parsing</SelectItem>
                    <SelectItem value="naics">NAICS (both values)</SelectItem>
                    <SelectItem value="naics_code">NAICS (code only)</SelectItem>
                    <SelectItem value="naics_description">NAICS (description only)</SelectItem>
                    <SelectItem value="titles">Title Enhancement</SelectItem>
                    <SelectItem value="set_asides">Set-Aside Standardization</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* Skip Existing Selection */}
              <div className="space-y-2">
                <Label>Processing Mode</Label>
                <div className="space-y-2">
                  <label className="flex items-center space-x-2">
                    <input
                      type="radio"
                      name="processing-mode"
                      value="skip"
                      checked={skipExisting === 'skip'}
                      onChange={(e) => setSkipExisting(e.target.value as 'skip' | 'fill')}
                      disabled={isProcessing}
                      className="h-4 w-4 text-primary"
                    />
                    <span className="text-sm font-normal cursor-pointer">
                      Skip existing AI data
                    </span>
                  </label>
                  <label className="flex items-center space-x-2">
                    <input
                      type="radio"
                      name="processing-mode"
                      value="fill"
                      checked={skipExisting === 'fill'}
                      onChange={(e) => setSkipExisting(e.target.value as 'skip' | 'fill')}
                      disabled={isProcessing}
                      className="h-4 w-4 text-primary"
                    />
                    <span className="text-sm font-normal cursor-pointer">
                      Replace existing AI data
                    </span>
                  </label>
                </div>
              </div>

              <div className="space-y-2">
                {!isProcessing ? (
                  <Button
                    onClick={handleStart}
                    disabled={isStartingIterative}
                    className="w-full bg-success hover:bg-success-dark dark:bg-success dark:hover:bg-success-dark text-white">
                    <PlayIcon className="mr-2 h-4 w-4 text-white" />
                    Start Enhancement
                  </Button>
                ) : (
                  <Button
                    onClick={handleStop}
                    disabled={isStoppingIterative || progress?.status === 'stopping'}
                    variant="destructive"
                    className="w-full bg-destructive hover:bg-destructive/90 dark:bg-destructive dark:hover:bg-destructive/90 text-destructive-foreground disabled:bg-muted dark:disabled:bg-muted disabled:text-muted-foreground">
                    <StopIcon className="mr-2 h-4 w-4 text-white" />
                    {progress?.status === 'stopping' ? 'Stopping...' : 'Stop Enhancement'}
                  </Button>
                )}
              </div>

              {/* Progress Display */}
              {progress && (progress.status === 'processing' || progress.processed > 0) && (
                <div className="space-y-3">
                  {/* Progress Bar */}
                  <div className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span className={`font-medium ${getStatusColor(progress.status)}`}>
                        Status: {progress.status.charAt(0).toUpperCase() + progress.status.slice(1)}
                      </span>
                      <span className="text-muted-foreground">
                        {progress.processed.toLocaleString()} / {progress.total.toLocaleString()}
                      </span>
                    </div>
                    <div className="w-full bg-secondary dark:bg-secondary rounded-full h-3">
                      <div 
                        className="bg-primary dark:bg-primary h-3 rounded-full transition-all duration-500"
                        style={{ width: `${progress.percentage}%` }}
                      />
                    </div>
                    <div className="text-center text-sm font-medium">
                      {progress.percentage.toFixed(1)}% Complete
                    </div>
                  </div>

                  {/* Current Processing Info */}
                  {progress.current_prospect && progress.status === 'processing' && (
                    <div className="bg-primary/10 dark:bg-primary/10 border border-primary/20 dark:border-primary/20 p-3 rounded-lg">
                      <div className="text-sm">
                        <span className="font-medium text-primary dark:text-primary">Currently processing: </span>
                        <span className="text-primary/80 dark:text-primary/80">{progress.current_prospect.title}</span>
                      </div>
                    </div>
                  )}

                  {/* Errors */}
                  {(((progress?.error_count ?? 0) > 0) || (progress?.errors && progress.errors.length > 0)) && (
                    <div className="bg-destructive/10 border border-destructive/20 p-3 rounded-lg">
                      <div className="text-sm text-destructive">
                        <span className="font-medium">Errors encountered: </span>
                        {progress?.error_count || progress?.errors?.length || 0} prospect(s) failed
                        {progress?.errors && progress.errors.length > 0 && (
                          <span className="text-xs ml-2">(showing last {progress.errors.length})</span>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Error Messages */}
              {progress?.error_message && (
                <div className="text-destructive text-sm">
                  Error: {progress.error_message}
                </div>
              )}

              {/* Success Messages */}
              {progress?.status === 'completed' && (
                <div className="bg-success-light/10 border border-success/20 p-3 rounded-lg">
                  <div className="text-success-dark dark:text-success font-medium">Enhancement completed successfully!</div>
                  <div className="text-success dark:text-success text-sm mt-1">
                    Processed all {progress.processed} available records
                  </div>
                </div>
              )}

              {progress?.status === 'stopped' && (
                <div className="bg-warning-light/10 border border-warning/20 p-3 rounded-lg">
                  <div className="text-warning-dark dark:text-warning font-medium">Enhancement stopped</div>
                  <div className="text-warning dark:text-warning text-sm mt-1">
                    Processed {progress.processed} records before stopping
                  </div>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Full width LLM Output Log below */}
      <Card>
        <CardHeader>
          <CardTitle>LLM Output Log</CardTitle>
        </CardHeader>
        <CardContent>
            {isLoadingOutputs ? (
              <div className="flex items-center justify-center h-32">
                <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-primary"></div>
              </div>
            ) : llmOutputs && llmOutputs.length > 0 ? (
              <div className="space-y-3 max-h-[700px] overflow-y-auto">
                {llmOutputs.map((output) => {
                  const isExpanded = expandedOutputs.has(output.id);
                  return (
                    <div key={output.id} className={`border rounded-lg p-3 ${output.success ? 'bg-success-light/5 border-success/20 dark:bg-success/5 dark:border-success/20' : 'bg-destructive/5 border-destructive/20 dark:bg-destructive/5 dark:border-destructive/20'}`}>
                      {/* Header with basic info */}
                      <div className="flex justify-between items-start">
                        <div className="flex-1">
                          <div className="flex items-center gap-2">
                            <Button
                              variant="ghost"
                              size="sm"
                              className="p-0 h-auto"
                              onClick={() => toggleOutputExpanded(output.id)}
                            >
                              {isExpanded ? <ChevronDownIcon className="h-4 w-4" /> : <ChevronRightIcon className="h-4 w-4" />}
                            </Button>
                            <div className="text-sm">
                              <span className="font-medium">{output.prospect_title || 'Unknown Prospect'}</span>
                              <span className="text-muted-foreground ml-2">({output.enhancement_type})</span>
                            </div>
                          </div>
                          
                          {/* Quick summary of result when collapsed */}
                          {!isExpanded && output.parsed_result && (
                            <div className="ml-6 mt-1 text-xs text-muted-foreground">
                              {output.enhancement_type === 'naics' && 'code' in output.parsed_result && (
                                <span>NAICS: {String(output.parsed_result.code)} - {'description' in output.parsed_result ? String(output.parsed_result.description) : ''}</span>
                              )}
                              {output.enhancement_type === 'values' && 'single' in output.parsed_result && (
                                <span>Value: ${Number(output.parsed_result.single).toLocaleString()}</span>
                              )}
                              {output.enhancement_type === 'titles' && 'enhanced_title' in output.parsed_result && (
                                <span>Enhanced Title: {String(output.parsed_result.enhanced_title)}</span>
                              )}
                              {output.enhancement_type === 'set_asides' && 'standardized_set_aside' in output.parsed_result && (
                                <span>Set-Aside: {String(output.parsed_result.standardized_set_aside)}</span>
                              )}
                            </div>
                          )}
                        </div>
                        <div className="flex items-center gap-2">
                          {output.processing_time && (
                            <span className="text-xs text-muted-foreground">{output.processing_time.toFixed(2)}s</span>
                          )}
                          <span className="text-xs text-muted-foreground">{formatUserDate(output.timestamp, 'datetime')}</span>
                        </div>
                      </div>
                      
                      {/* Expandable details */}
                      {isExpanded && (
                        <div className="mt-3 space-y-2">
                          {/* LLM Response */}
                          <div className="text-sm">
                            <span className="font-medium">Response:</span>
                            <pre className="mt-1 p-2 bg-card rounded border text-xs overflow-x-auto max-h-32 overflow-y-auto">
                              {output.response}
                            </pre>
                          </div>
                          
                          {/* Parsed Result */}
                          {output.parsed_result && (
                            <div className="text-sm">
                              <span className="font-medium">Parsed Result:</span>
                              <pre className="mt-1 p-2 bg-card rounded border text-xs overflow-x-auto">
                                {JSON.stringify(output.parsed_result, null, 2)}
                              </pre>
                            </div>
                          )}
                          
                          {/* Error Message */}
                          {output.error_message && (
                            <div className="text-sm text-destructive">
                              <span className="font-medium">Error:</span> {output.error_message}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                No LLM outputs yet. Start an enhancement to see outputs here.
              </div>
            )}
          </CardContent>
      </Card>
    </div>
  );
}
