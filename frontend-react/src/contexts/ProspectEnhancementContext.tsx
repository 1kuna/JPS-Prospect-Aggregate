import React, { createContext, useContext, ReactNode } from 'react';
import { useProspectEnhancementQueue } from '@/hooks/api/useProspectEnhancementQueue';

interface ProspectEnhancementContextType {
  addToQueue: (request: {
    prospect_id: string;
    force_redo?: boolean;
    user_id?: number;
  }) => void;
  getProspectStatus: (prospect_id: string) => {
    prospect_id: string;
    force_redo?: boolean;
    user_id?: number;
    status: 'queued' | 'processing' | 'completed' | 'failed';
    position?: number;
    error?: string;
  } | null;
  removeFromQueue: (prospect_id: string) => void;
  queueLength: number;
  isProcessing: boolean;
}

const ProspectEnhancementContext = createContext<ProspectEnhancementContextType | undefined>(undefined);

export function ProspectEnhancementProvider({ children }: { children: ReactNode }) {
  const queueManager = useProspectEnhancementQueue();

  return (
    <ProspectEnhancementContext.Provider value={queueManager}>
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