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
  }) => void;
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
  const queueLength = Object.values(enhancementStates).filter(s => s.status === 'queued').length;
  const isProcessing = Object.values(enhancementStates).some(s => s.status === 'processing');

  // Adapt the interface to match existing API
  const contextValue: ProspectEnhancementContextType = {
    addToQueue: queueEnhancement,
    getProspectStatus: (prospect_id: string | undefined) => {
      if (!prospect_id) return null;
      const state = getEnhancementState(prospect_id);
      if (!state) return null;
      
      // Convert completedSteps array to progress object for backward compatibility
      const progress: any = {};
      if (state.completedSteps) {
        state.completedSteps.forEach(step => {
          progress[step] = { completed: true, skipped: false };
        });
      }
      
      return {
        prospect_id,
        status: state.status,
        queuePosition: state.queuePosition,
        queueSize: state.queueSize,
        estimatedTimeRemaining: undefined, // Not used in simple version
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