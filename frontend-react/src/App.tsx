import { Suspense, lazy } from 'react';
import { BrowserRouter as Router } from 'react-router-dom';
import { ErrorBoundary } from './components/ErrorBoundary';
import { AppProviders } from './contexts/AppContexts';
import { 
  Skeleton, 
  Card, 
  CardHeader,
} from './components/ui';
import { Toaster } from './components/ui/toaster';

// Lazy load pages
const Proposals = lazy(() => import('./pages/Proposals'));
const DataSources = lazy(() => import('./pages/DataSources'));
const Dashboard = lazy(() => import('./pages/Dashboard'));
const DirectDatabaseAccess = lazy(() => import('./pages/DirectDatabaseAccess'));

// Loading fallback - memoized to prevent unnecessary re-renders
const PageSkeleton = () => (
  <div className="container">
    <Card>
      <CardHeader>
        <Skeleton className="h-10 w-1/4 mb-6" />
      </CardHeader>
      <div className="flex gap-4">
        {[1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-64 w-full" />
        ))}
      </div>
    </Card>
  </div>
);

function App() {
  return (
    <ErrorBoundary>
      <AppProviders>
        <Router>
          <div className="min-h-screen bg-gray-100 dark:bg-gray-900">
            <Suspense fallback={<PageSkeleton />}>
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/proposals" element={<Proposals />} />
                <Route path="/data-sources" element={<DataSources />} />
                <Route path="/database" element={<DirectDatabaseAccess />} />
              </Routes>
            </Suspense>
          </div>
          <Toaster />
        </Router>
      </AppProviders>
    </ErrorBoundary>
  );
}

export default App;
