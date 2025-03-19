import { createContext, useContext, useState, useCallback, ReactNode } from 'react';

// Loading Context
interface LoadingContextType {
  isLoading: boolean;
  setLoading: (loading: boolean) => void;
  loadingMessage: string;
  setLoadingMessage: (message: string) => void;
}

const LoadingContext = createContext<LoadingContextType | undefined>(undefined);

export const LoadingProvider = ({ children }: { children: ReactNode }) => {
  const [isLoading, setIsLoading] = useState(false);
  const [loadingMessage, setLoadingMessage] = useState('Loading...');

  const setLoading = (loading: boolean) => {
    setIsLoading(loading);
  };

  return (
    <LoadingContext.Provider
      value={{
        isLoading,
        setLoading,
        loadingMessage,
        setLoadingMessage,
      }}
    >
      {children}
    </LoadingContext.Provider>
  );
};

export const useLoading = (): LoadingContextType => {
  const context = useContext(LoadingContext);
  if (context === undefined) {
    throw new Error('useLoading must be used within a LoadingProvider');
  }
  return context;
};

// Pulling Context
interface PullingContextType {
  pullingSourceIds: Record<number, boolean>;
  setPulling: (sourceId: number, isPulling: boolean) => void;
  isPulling: (sourceId: number) => boolean;
}

const PullingContext = createContext<PullingContextType | undefined>(undefined);

export const PullingProvider = ({ children }: { children: ReactNode }) => {
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
};

export const usePulling = () => {
  const context = useContext(PullingContext);
  if (context === undefined) {
    throw new Error('usePulling must be used within a PullingProvider');
  }
  return context;
};

// Combined Provider for convenience
export const AppProviders = ({ children }: { children: ReactNode }) => {
  return (
    <PullingProvider>
      <LoadingProvider>
        {children}
      </LoadingProvider>
    </PullingProvider>
  );
}; 