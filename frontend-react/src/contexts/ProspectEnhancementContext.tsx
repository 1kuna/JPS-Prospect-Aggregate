import { createContext, useContext, ReactNode } from 'react';
import { useEnhancementSimple } from '@/hooks/api/useEnhancementSimple';
import { EnhancementStepData } from '@/types';

interface ProspectEnhancementStatus {
  prospect_id: string;
  status: 'idle' | 'queued' | 'processing' | 'completed' | 'failed';
  queuePosition?: number;
  queueSize?: number;
  estimatedTimeRemaining?: number;
  currentStep?: string;
  progress?: {
    values?: EnhancementStepData;
    contacts?: EnhancementStepData;
    naics?: EnhancementStepData;
    titles?: EnhancementStepData;
    set_asides?: EnhancementStepData;
  };
  enhancementTypes?: string[];
  error?: string;
}

interface ProspectEnhancementContextType {
  addToQueue: (request: {
    prospect_id: string;
    force_redo?: boolean;
    user_id?: number;
    enhancement_types?: string[];
  }) => Promise<string>;
  getProspectStatus: (prospect_id: string | undefined) => ProspectEnhancementStatus | null;
  cancelEnhancement: (prospect_id: string) => Promise<boolean>;
  queueLength: number;
  isProcessing: boolean;
}

const ProspectEnhancementContext = createContext<ProspectEnhancementContextType | undefined>(undefined);

export function ProspectEnhancementProvider({ children }: { children: ReactNode }) {
  const {
    queueEnhancement,
    getEnhancementState,
    cancelEnhancement,
    enhancementStates
  } = useEnhancementSimple();
  
  // Derive queue length and processing status from enhancement states
  const queueLength = Object.values(enhancementStates).filter(s => ['queued', 'processing'].includes(s.status)).length;
  const isProcessing = Object.values(enhancementStates).some(s => s.status === 'processing');

  // Adapt the interface to match existing API
  const contextValue: ProspectEnhancementContextType = {
    addToQueue: queueEnhancement,
    getProspectStatus: (prospect_id: string | undefined) => {
      if (!prospect_id) return null;
      const state = getEnhancementState(prospect_id);
      if (!state) return null;
      
      // Initialize progress object with all possible enhancement types
      const progress: Record<string, EnhancementStepData> = {} as Record<string, EnhancementStepData>;
      const baseEnhancementTypes = state.enhancementTypes || ['titles', 'values', 'naics', 'set_asides'];
      const progressKeys = state.progress ? Object.keys(state.progress) : [];
      const plannedKeys = state.plannedSteps ? Object.keys(state.plannedSteps) : [];
      const allEnhancementTypes = Array.from(new Set([...baseEnhancementTypes, ...progressKeys, ...plannedKeys]));
      
      // Initialize all enhancement types based on planned steps
      allEnhancementTypes.forEach(type => {
        // Check if this step is planned to be skipped
        if (state.plannedSteps && state.plannedSteps[type]) {
          const planned = state.plannedSteps[type];
          const baseProgress = (state.progress?.[type] ?? {}) as EnhancementStepData;
          const willProcess = planned.will_process;
          progress[type] = {
            ...baseProgress,
            completed: Boolean(baseProgress.completed) && willProcess,
            skipped: willProcess ? Boolean(baseProgress.skipped) : true,
            skipReason: !willProcess ? planned.reason || 'already_enhanced' : baseProgress.skipReason
          };
        } else {
          // No planned steps info, default behavior
          const baseProgress = (state.progress?.[type] ?? {}) as EnhancementStepData;
          progress[type] = {
            ...baseProgress,
            completed: Boolean(baseProgress.completed),
            skipped: Boolean(baseProgress.skipped),
            skipReason: baseProgress.skipReason
          };
        }
      });
      
      // Mark completed steps
      if (state.completedSteps) {
        state.completedSteps.forEach(step => {
          if (progress[step] !== undefined) {
            // If it was already marked as skipped, keep that status
            // Otherwise mark as completed
            if (!progress[step].skipped) {
              progress[step] = {
                ...progress[step],
                completed: true,
                skipped: false
              };
            }
          }
        });
      }
      
      // Determine if a step was skipped during processing (runtime skip)
      // This is inferred when a step is in completedSteps but the currentStep mentions "already"
      if (state.currentStep?.toLowerCase().includes('already')) {
        const currentType = allEnhancementTypes.find(type => 
          state.currentStep?.toLowerCase().includes(type.replace('_', ' '))
        );
        if (currentType && progress[currentType]) {
          progress[currentType].skipped = true;
        }
      }
      
      return {
        prospect_id,
        status: state.status,
        queuePosition: state.queuePosition,
        queueSize: state.queueSize,
        estimatedTimeRemaining: state.estimatedTimeRemaining,
        currentStep: state.currentStep,
        progress,
        enhancementTypes: state.enhancementTypes,
        error: state.error
      };
    },
    cancelEnhancement,
    queueLength,
    isProcessing
  };

  return (
    <ProspectEnhancementContext.Provider value={contextValue}>
      {children}
    </ProspectEnhancementContext.Provider>
  );
}

export function useProspectEnhancement() {
  const context = useContext(ProspectEnhancementContext);
  if (context === undefined) {
    throw new Error('useProspectEnhancement must be used within a ProspectEnhancementProvider');
  }
  return context;
}
