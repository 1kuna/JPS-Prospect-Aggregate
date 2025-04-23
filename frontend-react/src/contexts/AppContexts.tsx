import React, { ReactNode } from 'react';
// import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
// import { AuthProvider } from './AuthContext';
// import { SettingsProvider } from './SettingsContext';
// import { NotificationProvider } from './NotificationContext';

// // Create a client (consider moving this if it grows complex)
// const queryClient = new QueryClient(); // Removed QueryClient instance

interface AppProvidersProps {
  children: ReactNode;
}

export const AppProviders: React.FC<AppProvidersProps> = ({ children }) => {
  return (
    // <QueryClientProvider client={queryClient}> // Removed QueryClientProvider
      // <AuthProvider>
        // <SettingsProvider>
          // <NotificationProvider>
            {children}
          // </NotificationProvider>
        // </SettingsProvider>
      // </AuthProvider>
    // </QueryClientProvider>
  );
};

export function AppContexts({ children }: { children: React.ReactNode }) {
  return (
    <>
      {children}
    </>
  );
} 