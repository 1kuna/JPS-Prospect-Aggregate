import { Suspense, lazy, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { ErrorBoundary } from './components/ErrorBoundary';
import { Navigation } from './components/layout';
import { AuthProvider } from './components/AuthProvider';
import { AuthGuard } from './components/AuthGuard';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ProspectEnhancementProvider } from './contexts/ProspectEnhancementContext';
import { TimezoneProvider } from './contexts/TimezoneContext';
import { useAuth } from './hooks/api/useAuth';
import styles from './App.module.css';

// Lazy load pages
const Prospects = lazy(() => import('./pages/Prospects'));
const DataSources = lazy(() => import('./pages/DataSources'));
const Dashboard = lazy(() => import('./pages/Dashboard'));
const DirectDatabaseAccess = lazy(() => import('./pages/DirectDatabaseAccess'));
const Advanced = lazy(() => import('./pages/Advanced'));

// Loading fallback - replaced complex skeleton with simple text
const PageSkeleton = () => <div className={styles.pageSkeleton}>Loading page...</div>;

// Create a client
const queryClient = new QueryClient();

// Wrapper component to pass user data to TimezoneProvider
function AppWithProviders() {
  const { user } = useAuth();
  
  return (
    <TimezoneProvider user={user}>
      <ProspectEnhancementProvider>
        <Router>
          <AuthGuard>
            <div className={styles.appContainer}>
              <Navigation />
              <Suspense fallback={<PageSkeleton />}>
                <Routes>
                  <Route path="/" element={<Dashboard />} />
                  <Route path="/prospects" element={<Prospects />} />
                  <Route path="/data-sources" element={<DataSources />} />
                  <Route path="/database" element={<DirectDatabaseAccess />} />
                  <Route path="/advanced" element={<Advanced />} />
                  <Route path="*" element={<div>Page Not Found</div>} />
                </Routes>
              </Suspense>
            </div>
          </AuthGuard>
        </Router>
      </ProspectEnhancementProvider>
    </TimezoneProvider>
  );
}

function App() {
  console.log('App component loaded!');
  // Effect to toggle .dark class on <html> based on OS/browser preference
  useEffect(() => {
    // Ensure the .dark class is not present if we're forcing light mode
    document.documentElement.classList.remove('dark');
  }, []);

  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <AppWithProviders />
        </AuthProvider>
      </QueryClientProvider>
    </ErrorBoundary>
  );
}

export default App;
