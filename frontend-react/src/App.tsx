import { Suspense, lazy, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { ErrorBoundary } from './components/ErrorBoundary';
import { Navigation } from './components/layout';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import styles from './App.module.css';

// Lazy load pages
const Proposals = lazy(() => import('./pages/Proposals'));
const DataSources = lazy(() => import('./pages/DataSources'));
const Dashboard = lazy(() => import('./pages/Dashboard'));
const DirectDatabaseAccess = lazy(() => import('./pages/DirectDatabaseAccess'));
const Advanced = lazy(() => import('./pages/Advanced'));

// Loading fallback - replaced complex skeleton with simple text
const PageSkeleton = () => <div className={styles.pageSkeleton}>Loading page...</div>;

// Create a client
const queryClient = new QueryClient();

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
        <Router>
          <div className={styles.appContainer}>
            <Navigation />
            <Suspense fallback={<PageSkeleton />}>
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/proposals" element={<Proposals />} />
                <Route path="/data-sources" element={<DataSources />} />
                <Route path="/database" element={<DirectDatabaseAccess />} />
                <Route path="/advanced" element={<Advanced />} />
                <Route path="*" element={<div>Page Not Found</div>} />
              </Routes>
            </Suspense>
          </div>
        </Router>
      </QueryClientProvider>
    </ErrorBoundary>
  );
}

export default App;
