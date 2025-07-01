import { createContext, useContext, ReactNode } from 'react';
import { useUnifiedEnhancement } from '@/hooks/api/useUnifiedEnhancement';
import { EnhancementStepData } from '@/types';

interface ProspectEnhancementStatus {
  prospect_id: string;
  status: 'idle' | 'queued' | 'processing' | 'completed' | 'failed';
  queuePosition?: number;
  estimatedTimeRemaining?: number;
  currentStep?: string;
  progress?: {
    values?: EnhancementStepData;
    contacts?: EnhancementStepData;
    naics?: EnhancementStepData;
    titles?: EnhancementStepData;
  };
  error?: string;
}

interface ProspectEnhancementContextType {
  addToQueue: (request: {
    prospect_id: string;
    force_redo?: boolean;
    user_id?: number;
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
    queueLength,
    isProcessing
  } = useUnifiedEnhancement();

  // Adapt the interface to match existing API
  const contextValue: ProspectEnhancementContextType = {
    addToQueue: queueEnhancement,
    getProspectStatus: (prospect_id: string | undefined) => {
      if (!prospect_id) return null;
      const state = getEnhancementState(prospect_id);
      if (!state) return null;
      
      return {
        prospect_id,
        status: state.status,
        queuePosition: state.queuePosition,
        estimatedTimeRemaining: state.estimatedTimeRemaining,
        currentStep: state.currentStep,
        progress: state.progress,
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