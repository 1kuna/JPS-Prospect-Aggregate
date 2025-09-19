import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { ReloadIcon, ChevronDownIcon, ExclamationTriangleIcon } from '@radix-ui/react-icons';
import { GoNoGoDecision } from '@/components/GoNoGoDecision';
import { EnhancementButtonWithSelector } from '@/components/EnhancementButtonWithSelector';
import { EnhancementProgress } from '@/components/EnhancementProgress';
import { EnhancementErrorBoundary } from '@/components/EnhancementErrorBoundary';
import { useIsSuperAdmin } from '@/hooks/api/useAuth';
import type { Prospect } from '@/types/prospects';
import { useState, useEffect, useMemo } from 'react';

interface ProspectDetailsModalProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  selectedProspect: Prospect | null;
  showAIEnhanced: boolean;
  onShowAIEnhancedChange: (checked: boolean) => void;
  getProspectStatus: (id: string) => {
    status?: 'idle' | 'queued' | 'processing' | 'completed' | 'failed' | string;
    currentStep?: string;
    queuePosition?: number;
    progress?: {
      titles?: { completed: boolean; skipped?: boolean; skipReason?: string };
      naics?: { completed: boolean; skipped?: boolean; skipReason?: string };
      values?: { completed: boolean; skipped?: boolean; skipReason?: string };
      contacts?: { completed: boolean; skipped?: boolean; skipReason?: string };
      set_asides?: { completed: boolean; skipped?: boolean; skipReason?: string };
    };
    enhancementTypes?: string[];
    plannedSteps?: Record<string, { will_process: boolean; reason?: string | null }>;
    error?: string | null;
  } | null;
  addToQueue?: (params: { prospect_id: string; force_redo: boolean; user_id: number; enhancement_types?: string[] }) => Promise<string>;
  formatUserDate: (dateString: string | null | undefined, format?: 'date' | 'datetime' | 'time' | 'relative', options?: Partial<Record<string, unknown>>) => string;
}

export function ProspectDetailsModal({
  isOpen,
  onOpenChange,
  selectedProspect,
  showAIEnhanced,
  onShowAIEnhancedChange,
  getProspectStatus,
  addToQueue: _addToQueue,
  formatUserDate
}: ProspectDetailsModalProps) {
  const isSuperAdmin = useIsSuperAdmin();
  const [showRawData, setShowRawData] = useState(false);
  const [enhancementStarted, setEnhancementStarted] = useState(false);
  const enhancementState = useMemo(() => {
    return selectedProspect ? getProspectStatus(selectedProspect.id) : null;
  }, [selectedProspect, getProspectStatus]);
  const isEnhancementActive = enhancementState?.status ? ['queued', 'processing'].includes(enhancementState.status) : false;
  const showCompletionBadge = Boolean(selectedProspect?.ollama_processed_at) && !enhancementStarted && !isEnhancementActive;
  type OverallStatus = 'idle' | 'queued' | 'processing' | 'completed' | 'failed';
  const toOverallStatus = (s?: string): OverallStatus | undefined =>
    s === 'idle' || s === 'queued' || s === 'processing' || s === 'completed' || s === 'failed' ? s : undefined;
  
  // Monitor enhancement status and reset the started flag when completed
  useEffect(() => {
    if (enhancementState && (enhancementState.status === 'completed' || enhancementState.status === 'failed')) {
        // Add a small delay before hiding to ensure user sees completion
        const timer = setTimeout(() => {
          setEnhancementStarted(false);
        }, 2000);
        return () => clearTimeout(timer);
    }
  }, [enhancementState]);
  
  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="text-2xl font-bold pr-8 text-foreground">
            <span>
              {(() => {
                if (!selectedProspect) return 'Prospect Details';
                // Prioritize AI-enhanced title if available
                if (selectedProspect.ai_enhanced_title) return selectedProspect.ai_enhanced_title;
                // Use the same logic as the table column
                if (selectedProspect.title) return selectedProspect.title;
                if (selectedProspect.extra?.summary && typeof selectedProspect.extra.summary === 'string') {
                  return selectedProspect.extra.summary;
                }
                if (selectedProspect.native_id) {
                  const agency = selectedProspect.extra?.agency || selectedProspect.agency || 'Unknown Agency';
                  return `${agency} - ${selectedProspect.native_id}`;
                }
                return 'Prospect Details';
              })()}
            </span>
            {(() => {
              if (!selectedProspect) return null;
              if (isEnhancementActive && enhancementState) {
                return (
                  <div className="inline-flex items-center ml-3 px-2 py-1 text-xs font-medium bg-yellow-100 text-yellow-800 rounded-full">
                    <ReloadIcon className="mr-1 h-3 w-3 animate-spin" />
                    {enhancementState.status === 'queued' ? 
                      `Queued (#${enhancementState.queuePosition || 1})` : 
                      `Processing${enhancementState.queuePosition ? ` (#${enhancementState.queuePosition})` : ''}`
                    }
                  </div>
                );
              }

              if (enhancementState?.status === 'failed') {
                return (
                  <div className="inline-flex items-center ml-3 px-2 py-1 text-xs font-medium bg-destructive/10 text-destructive border border-destructive/40 rounded-full">
                    <ExclamationTriangleIcon className="mr-1 h-3 w-3" />
                    Enhancement failed
                  </div>
                );
              }

              return null;
            })()}
          </DialogTitle>
          <DialogDescription>
            Full details for this prospect opportunity
          </DialogDescription>
        </DialogHeader>
        
        {selectedProspect && (
          <div className="space-y-6 mt-6">
            {/* Enhancement Status and Button */}
            <div className="flex items-center justify-between">
              {/* Enhancement Status - Left side */}
              {showCompletionBadge && (
                <div className="bg-blue-50 dark:bg-primary/10 border border-blue-200 dark:border-primary/20 p-3 rounded-lg">
                  <div className="flex items-center text-sm text-blue-800 dark:text-primary">
                    <div className="w-2 h-2 bg-blue-500 dark:bg-primary rounded-full mr-2"></div>
                    {`AI Enhanced on ${formatUserDate(selectedProspect.ollama_processed_at, 'datetime')}`}
                  </div>
                </div>
              )}
              
              {/* Spacer when no enhancement status */}
              {!showCompletionBadge && <div />}
              
              {/* Enhancement Button - Right side */}
              <EnhancementErrorBoundary>
                <EnhancementButtonWithSelector 
                  prospect={selectedProspect}
                  userId={1}
                  onEnhancementStart={() => setEnhancementStarted(true)}
                />
              </EnhancementErrorBoundary>
            </div>
            
            {/* Enhancement Progress */}
            <EnhancementErrorBoundary>
              <EnhancementProgress 
                status={enhancementState ? {
                  overallStatus: toOverallStatus(enhancementState.status),
                  currentStep: enhancementState.currentStep,
                  progress: enhancementState.progress,
                  enhancementTypes: enhancementState.enhancementTypes,
                  plannedSteps: enhancementState.plannedSteps,
                  error: enhancementState.error ?? null
                } : null}
                isVisible={Boolean(
                  enhancementStarted ||
                  (enhancementState && ['queued', 'processing', 'failed'].includes(enhancementState.status as string))
                )}
              />
            </EnhancementErrorBoundary>
            
            {/* AI Enhancement Toggle */}
            <div className="bg-muted border border-border p-3 rounded-lg">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <Label htmlFor="ai-toggle" className="text-sm font-medium text-muted-foreground">
                    Show AI-Enhanced Fields
                  </Label>
                  <Switch
                    id="ai-toggle"
                    checked={showAIEnhanced}
                    onCheckedChange={onShowAIEnhancedChange}
                  />
                </div>
                <div className="text-xs text-muted-foreground">
                  {showAIEnhanced ? 'Showing AI-enhanced data where available' : 'Showing original data only'}
                </div>
              </div>
            </div>

            {/* Go/No-Go Decision */}
            <div className="bg-blue-50 dark:bg-primary/10 border border-blue-200 dark:border-primary/20 p-4 rounded-lg">
              <GoNoGoDecision 
                prospectId={selectedProspect.id} 
                prospectTitle={selectedProspect.ai_enhanced_title || selectedProspect.title}
                compact={false} 
              />
            </div>

            {/* Basic Information */}
            <div>
              <h3 className="text-lg font-semibold mb-3 text-foreground">Basic Information</h3>
              <div className="grid grid-cols-1 gap-4 bg-muted p-4 rounded-lg">
                <div className={`${(() => {
                  const isTitleActive = enhancementState?.currentStep?.toLowerCase().includes('title') || 
                                      enhancementState?.currentStep?.toLowerCase().includes('enhancing');
                  const isTitleCompleted = enhancementState?.progress?.titles?.completed;
                  
                  // Only show animation if actively processing titles and not yet completed
                  return (isTitleActive && !isTitleCompleted) ? 'animate-pulse bg-blue-50 dark:bg-primary/10 border border-blue-200 dark:border-primary/20 rounded p-2' : '';
                })()}`}>
                  <span className="font-medium text-muted-foreground">Title:</span>
                  {(() => {
                    const isTitleActive = enhancementState?.currentStep?.toLowerCase().includes('title') || 
                                        enhancementState?.currentStep?.toLowerCase().includes('enhancing');
                    const isTitleCompleted = enhancementState?.progress?.titles?.completed;
                    
                    // Only show spinner if actively processing titles and not yet completed
                    return (isTitleActive && !isTitleCompleted) ? (
                      <span className="ml-2 text-xs px-2 py-1 rounded bg-blue-100 dark:bg-primary/20 text-blue-700 dark:text-primary animate-pulse inline-flex items-center">
                        <ReloadIcon className="w-3 h-3 mr-1 animate-spin" />
                        Enhancing...
                      </span>
                    ) : null;
                  })()}
                  <p className={`mt-1 ${(() => {
                    // Check if title is AI enhanced
                    const isAIEnhanced = showAIEnhanced && 
                                       selectedProspect.ai_enhanced_title && 
                                       selectedProspect.title !== selectedProspect.ai_enhanced_title;
                    return isAIEnhanced ? 'text-primary font-medium' : 'text-foreground';
                  })()}`}>{(() => {
                    // Use AI-enhanced title if toggle is on and available
                    if (showAIEnhanced && selectedProspect.ai_enhanced_title) {
                      return selectedProspect.ai_enhanced_title;
                    }
                    // Otherwise use original logic
                    if (selectedProspect.title) return selectedProspect.title;
                    if (selectedProspect.extra?.summary && typeof selectedProspect.extra.summary === 'string') {
                      return selectedProspect.extra.summary;
                    }
                    if (selectedProspect.native_id) {
                      const agency = selectedProspect.extra?.agency || selectedProspect.agency || 'Unknown Agency';
                      return `${agency} - ${selectedProspect.native_id}`;
                    }
                    return 'N/A';
                  })()}
                  </p>
                </div>
                {selectedProspect.description && (
                  <div>
                    <span className="font-medium text-muted-foreground">Description:</span>
                    <p className="mt-1 text-foreground whitespace-pre-wrap">{selectedProspect.description}</p>
                  </div>
                )}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <span className="font-medium text-muted-foreground">Agency:</span>
                    <p className="mt-1 text-foreground">{selectedProspect.agency || 'N/A'}</p>
                  </div>
                  <div className={`${(() => {
                    const isNaicsActive = enhancementState?.currentStep?.toLowerCase().includes('naics') || 
                                        enhancementState?.currentStep?.toLowerCase().includes('classifying');
                    const isNaicsCompleted = enhancementState?.progress?.naics?.completed;
                    
                    return (isNaicsActive && !isNaicsCompleted) ? 'animate-pulse bg-primary/10 border border-primary/20 rounded p-2' : '';
                  })()}`}>
                    <span className="font-medium text-muted-foreground">NAICS:</span>
                    {(() => {
                      const isNaicsActive = enhancementState?.currentStep?.toLowerCase().includes('naics') || 
                                          enhancementState?.currentStep?.toLowerCase().includes('classifying');
                      const isNaicsCompleted = enhancementState?.progress?.naics?.completed;
                      
                      return (isNaicsActive && !isNaicsCompleted) ? (
                        <span className="ml-2 text-xs px-2 py-1 rounded bg-blue-100 dark:bg-primary/20 text-blue-700 dark:text-primary animate-pulse inline-flex items-center">
                          <ReloadIcon className="w-3 h-3 mr-1 animate-spin" />
                          Classifying...
                        </span>
                      ) : null;
                    })()}
                    <p className="mt-1 text-foreground">
                      {(() => {
                        // Always show NAICS if available
                        return selectedProspect.naics || 'N/A';
                      })()}
                      {(() => {
                        const status = getProspectStatus(selectedProspect.id);
                        const isNaicsActive = status?.currentStep?.toLowerCase().includes('naics') || 
                                            status?.currentStep?.toLowerCase().includes('classifying');
                        const isNaicsCompleted = status?.progress?.naics?.completed;
                        
                        // Check if NAICS was actually changed by AI
                        const originalNaics = selectedProspect.extra?.original_naics as string | undefined;
                        const isAIEnhanced = showAIEnhanced && 
                                           selectedProspect.naics_source === 'llm_inferred' && 
                                           selectedProspect.ollama_processed_at &&
                                           selectedProspect.naics &&
                                           (!originalNaics || originalNaics !== selectedProspect.naics);
                        
                        return isAIEnhanced && !(isNaicsActive && !isNaicsCompleted);
                      })() && (
                        <span className="ml-2 text-xs px-2 py-1 rounded bg-primary/20 text-primary">
                          AI Classified
                        </span>
                      )}
                    </p>
                    {selectedProspect.naics_description && (
                      <p className="mt-1 text-sm text-muted-foreground">{selectedProspect.naics_description}</p>
                    )}
                  </div>
                </div>
              </div>
            </div>

            {/* Financial Information */}
            <div>
              <h3 className="text-lg font-semibold mb-3 text-foreground">Financial Information</h3>
              <div className="grid grid-cols-1 gap-4 bg-muted p-4 rounded-lg">
                {/* Original estimated value */}
                <div>
                  <span className="font-medium text-muted-foreground">Original Estimated Value:</span>
                  <p className="mt-1 text-foreground">
                    {selectedProspect.estimated_value_text || selectedProspect.estimated_value || 'N/A'}
                    {selectedProspect.est_value_unit && ` ${selectedProspect.est_value_unit}`}
                  </p>
                </div>
                
                {/* AI-parsed values with progress indicator */}
                {(() => {
                  const status = getProspectStatus(selectedProspect.id);
                  const isValuesActive = status?.currentStep?.toLowerCase().includes('value') || 
                                       status?.currentStep?.toLowerCase().includes('parsing');
                  const isValuesCompleted = status?.progress?.values?.completed;
                  
                  return (isValuesActive && !isValuesCompleted) ? (
                    <div className="bg-primary/10 p-3 rounded-lg border border-primary/20 animate-pulse">
                      <div className="flex items-center mb-2">
                        <span className="font-medium text-primary">Parsing Contract Values</span>
                        <ReloadIcon className="ml-2 w-4 h-4 animate-spin text-primary" />
                      </div>
                      <p className="text-sm text-primary">AI is analyzing the contract value text...</p>
                    </div>
                  ) : null;
                })()}
                
                {/* AI-parsed values */}
                {(() => {
                  const status = getProspectStatus(selectedProspect.id);
                  const isValuesActive = status?.currentStep?.toLowerCase().includes('value') || 
                                       status?.currentStep?.toLowerCase().includes('parsing');
                  const isValuesCompleted = status?.progress?.values?.completed;
                  
                  return showAIEnhanced && (selectedProspect.estimated_value_min || selectedProspect.estimated_value_max || selectedProspect.estimated_value_single) && !(isValuesActive && !isValuesCompleted);
                })() && (
                  <div className="bg-green-50 dark:bg-emerald-400/10 p-3 rounded-lg border border-green-200 dark:border-emerald-400/20">
                    <div className="flex items-center mb-2">
                      <span className="font-medium text-green-800 dark:text-emerald-300">AI-Processed Values</span>
                      <div className="w-2 h-2 bg-green-500 dark:bg-emerald-400 rounded-full ml-2"></div>
                    </div>
                    <div className="mt-1 space-y-1">
                      {/* Show range if min/max exist and single is null */}
                      {selectedProspect.estimated_value_min && selectedProspect.estimated_value_max && !selectedProspect.estimated_value_single && (
                        <p className="text-foreground">
                          <span className="text-sm text-muted-foreground">Range:</span> 
                          {(() => {
                            const min = parseFloat(selectedProspect.estimated_value_min);
                            const max = parseFloat(selectedProspect.estimated_value_max);
                            if (!isNaN(min) && !isNaN(max)) {
                              return ` $${min.toLocaleString()} - $${max.toLocaleString()}`;
                            }
                            return ' Invalid values';
                          })()}
                        </p>
                      )}
                      {/* Show single value if it exists */}
                      {selectedProspect.estimated_value_single && (
                        <p className="text-foreground">
                          <span className="text-sm text-muted-foreground">Value:</span> 
                          {(() => {
                            const single = parseFloat(selectedProspect.estimated_value_single);
                            if (!isNaN(single)) {
                              return ` $${single.toLocaleString()}`;
                            }
                            return ' Invalid value';
                          })()}
                        </p>
                      )}
                    </div>
                  </div>
                )}
                
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <span className="font-medium text-muted-foreground">Contract Type:</span>
                    <p className="mt-1 text-foreground">{selectedProspect.contract_type || 'N/A'}</p>
                  </div>
                  <div>
                    <span className="font-medium text-muted-foreground">Set Aside:</span>
                    <p className="mt-1 text-foreground">
                      {(() => {
                        // Show AI-enhanced set-aside if toggle is on and available
                        if (showAIEnhanced && selectedProspect.set_aside_standardized_label && 
                            selectedProspect.set_aside_standardized !== 'NOT_AVAILABLE') {
                          return selectedProspect.set_aside_standardized_label;
                        }
                        return selectedProspect.set_aside || 'N/A';
                      })()}
                      {showAIEnhanced && 
                       selectedProspect.set_aside_standardized_label && 
                       selectedProspect.set_aside_standardized !== 'NOT_AVAILABLE' &&
                       selectedProspect.set_aside_standardized_label !== selectedProspect.set_aside &&
                       selectedProspect.ollama_processed_at && (
                        <span className="ml-2 text-xs px-2 py-1 rounded bg-primary/20 text-primary">
                          AI Enhanced
                        </span>
                      )}
                    </p>
                  </div>
                  <div>
                    <span className="font-medium text-muted-foreground">Award Fiscal Year:</span>
                    <p className="mt-1 text-foreground">{selectedProspect.award_fiscal_year || 'N/A'}</p>
                  </div>
                </div>
              </div>
            </div>

            {/* Dates */}
            <div>
              <h3 className="text-lg font-semibold mb-3 text-foreground">Important Dates</h3>
              <div className="grid grid-cols-2 gap-4 bg-muted p-4 rounded-lg">
                <div>
                  <span className="font-medium text-muted-foreground">Release Date:</span>
                  <p className="mt-1 text-foreground">
                    {selectedProspect.release_date 
                      ? formatUserDate(selectedProspect.release_date, 'date')
                      : 'N/A'}
                  </p>
                </div>
                <div>
                  <span className="font-medium text-muted-foreground">Award Date:</span>
                  <p className="mt-1 text-foreground">
                    {selectedProspect.award_date 
                      ? formatUserDate(selectedProspect.award_date, 'date')
                      : 'N/A'}
                    {/* Tentative date indicator following AI Enhanced pattern */}
                    {Boolean(selectedProspect.extra?.award_date_is_tentative) && (
                      <span className="ml-2 text-xs px-2 py-1 rounded bg-orange-100 text-orange-700">
                        Tentative (Q{(() => {
                          const quarterStr = selectedProspect.extra?.award_quarter_original;
                          if (typeof quarterStr === 'string') {
                            const match = quarterStr.match(/Q([1-4])/);
                            return match?.[1] || '?';
                          }
                          return '?';
                        })()})
                      </span>
                    )}
                  </p>
                </div>
              </div>
            </div>

            {/* Location */}
            <div>
              <h3 className="text-lg font-semibold mb-3 text-foreground">Location</h3>
              <div className="bg-muted p-4 rounded-lg">
                <p className="text-foreground">
                  {[selectedProspect.place_city, selectedProspect.place_state, selectedProspect.place_country]
                    .filter(Boolean)
                    .join(', ') || 'N/A'}
                </p>
              </div>
            </div>

            {/* Contact Information with progress indicator */}
            {(() => {
              const isContactsActive = enhancementState?.currentStep?.toLowerCase().includes('contact') || 
                                     enhancementState?.currentStep?.toLowerCase().includes('extracting');
              const isContactsCompleted = enhancementState?.progress?.contacts?.completed;
              
              return (isContactsActive && !isContactsCompleted) ? (
                <div>
                  <div className="flex items-center mb-3">
                    <h3 className="text-lg font-semibold text-foreground">Contact Information</h3>
                    <ReloadIcon className="ml-2 w-4 h-4 animate-spin text-primary" />
                  </div>
                  <div className="bg-primary/10 p-4 rounded-lg border border-primary/20 animate-pulse">
                    <p className="text-primary font-medium">Extracting contact information...</p>
                    <p className="text-sm text-primary">AI is analyzing available contact data</p>
                  </div>
                </div>
              ) : null;
            })()}

            {/* Contact Information */}
            {(() => {
              const isContactsActive = enhancementState?.currentStep?.toLowerCase().includes('contact') || 
                                     enhancementState?.currentStep?.toLowerCase().includes('extracting');
              const isContactsCompleted = enhancementState?.progress?.contacts?.completed;
              
              return !(isContactsActive && !isContactsCompleted) && (selectedProspect.primary_contact_email || selectedProspect.primary_contact_name);
            })() && (
              <div>
                <div className="flex items-center mb-3">
                  <h3 className="text-lg font-semibold text-foreground">Contact Information</h3>
                </div>
                <div className="grid grid-cols-2 gap-4 p-4 rounded-lg bg-muted border border-border">
                  {selectedProspect.primary_contact_name && (
                    <div>
                      <span className="font-medium text-muted-foreground">
                        Primary Contact:
                      </span>
                      <p className="mt-1 text-foreground">{selectedProspect.primary_contact_name}</p>
                    </div>
                  )}
                  {selectedProspect.primary_contact_email && (
                    <div>
                      <span className="font-medium text-muted-foreground">
                        Email:
                      </span>
                      <p className="mt-1 text-foreground">
                        <a href={`mailto:${selectedProspect.primary_contact_email}`} 
                           className="text-primary hover:text-primary/80 underline">
                          {selectedProspect.primary_contact_email}
                        </a>
                      </p>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* System Information */}
            <div>
              <h3 className="text-lg font-semibold mb-3 text-foreground">System Information</h3>
              <div className="grid grid-cols-2 gap-4 bg-muted p-4 rounded-lg">
                <div>
                  <span className="font-medium text-muted-foreground">Source:</span>
                  <p className="mt-1 text-foreground">{selectedProspect.source_name || 'N/A'}</p>
                </div>
                <div>
                  <span className="font-medium text-muted-foreground">Native ID:</span>
                  <p className="mt-1 text-foreground font-mono text-sm">{selectedProspect.native_id || 'N/A'}</p>
                </div>
                <div>
                  <span className="font-medium text-muted-foreground">Loaded At:</span>
                  <p className="mt-1 text-foreground">
                    {selectedProspect.loaded_at 
                      ? formatUserDate(selectedProspect.loaded_at)
                      : 'N/A'}
                  </p>
                </div>
                <div>
                  <span className="font-medium text-muted-foreground">ID:</span>
                  <p className="mt-1 text-foreground font-mono text-sm">{selectedProspect.id}</p>
                </div>
                {selectedProspect.ollama_processed_at && (
                  <>
                    <div>
                      <span className="font-medium text-muted-foreground">LLM Processed:</span>
                      <p className="mt-1 text-foreground">
                        {formatUserDate(selectedProspect.ollama_processed_at)}
                      </p>
                    </div>
                    <div>
                      <span className="font-medium text-muted-foreground">LLM Model:</span>
                      <p className="mt-1 text-foreground">{selectedProspect.ollama_model_version || 'N/A'}</p>
                    </div>
                  </>
                )}
              </div>
            </div>

            {/* Extra Information */}
            {selectedProspect.extra && (
              <div>
                <h3 className="text-lg font-semibold mb-3 text-foreground">Additional Information</h3>
                <div className="bg-muted p-4 rounded-lg">
                  <pre className="text-sm text-foreground whitespace-pre-wrap font-mono">
                    {(() => {
                      try {
                        // If it's a string, try to parse and reformat it
                        if (typeof selectedProspect.extra === 'string') {
                          const parsed = JSON.parse(selectedProspect.extra);
                          return JSON.stringify(parsed, null, 2);
                        }
                        // If it's already an object, format it
                        return JSON.stringify(selectedProspect.extra, null, 2);
                      } catch {
                        // If parsing fails, return the original string as string
                        return String(selectedProspect.extra);
                      }
                    })()}
                  </pre>
                </div>
              </div>
            )}

            {/* Super Admin Raw Data Debug Section */}
            {isSuperAdmin && (
              <div className="mt-6 border-t pt-4">
                <button 
                  onClick={() => setShowRawData(!showRawData)}
                  className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
                >
                  <ChevronDownIcon className={`w-4 h-4 transition-transform ${showRawData ? 'rotate-180' : ''}`} />
                  {showRawData ? 'Hide' : 'Show'} Raw Data (Debug)
                </button>
                {showRawData && (
                  <div className="mt-3 p-4 bg-muted rounded-lg border border-border">
                    <div className="text-xs font-medium text-muted-foreground mb-2">Complete Raw Prospect Object:</div>
                    <pre className="text-xs font-mono text-foreground overflow-auto max-h-96 whitespace-pre-wrap">
                      {JSON.stringify(selectedProspect, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            )}

          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
