import { Suspense, lazy } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { ErrorBoundary } from './components/ErrorBoundary';
import { AppProviders } from './contexts/AppContexts';
import styles from './App.module.css';

// Lazy load pages
const Proposals = lazy(() => import('./pages/Proposals'));
const DataSources = lazy(() => import('./pages/DataSources'));
const Dashboard = lazy(() => import('./pages/Dashboard'));
const DirectDatabaseAccess = lazy(() => import('./pages/DirectDatabaseAccess'));

// Loading fallback - replaced complex skeleton with simple text
const PageSkeleton = () => <div className={styles.pageSkeleton}>Loading page...</div>;

function App() {
  return (
    <ErrorBoundary>
      <AppProviders>
        <Router>
          <div className={styles.appContainer}>
            <Suspense fallback={<PageSkeleton />}>
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/proposals" element={<Proposals />} />
                <Route path="/data-sources" element={<DataSources />} />
                <Route path="/database" element={<DirectDatabaseAccess />} />
                <Route path="*" element={<div>Page Not Found</div>} />
              </Routes>
            </Suspense>
          </div>
        </Router>
      </AppProviders>
    </ErrorBoundary>
  );
}

export default App;
