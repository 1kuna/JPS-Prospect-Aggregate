import { createContext, useContext, useState, useCallback, ReactNode } from 'react';

interface PullingContextType {
  pullingSourceIds: Record<number, boolean>;
  setPulling: (sourceId: number, isPulling: boolean) => void;
  isPulling: (sourceId: number) => boolean;
}

const PullingContext = createContext<PullingContextType | undefined>(undefined);

export function PullingProvider({ children }: { children: ReactNode }) {
  const [pullingSourceIds, setPullingSourceIds] = useState<Record<number, boolean>>({});

  const setPulling = useCallback((sourceId: number, isPulling: boolean) => {
    console.log(`[PullingContext] Setting source ${sourceId} pulling state to ${isPulling}`);
    setPullingSourceIds(prev => ({
      ...prev,
      [sourceId]: isPulling
    }));
  }, []);

  const isPulling = useCallback((sourceId: number) => {
    return !!pullingSourceIds[sourceId];
  }, [pullingSourceIds]);

  return (
    <PullingContext.Provider value={{ pullingSourceIds, setPulling, isPulling }}>
      {children}
    </PullingContext.Provider>
  );
}

export function usePulling() {
  const context = useContext(PullingContext);
  if (context === undefined) {
    throw new Error('usePulling must be used within a PullingProvider');
  }
  return context;
} 