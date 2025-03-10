import { Suspense, lazy } from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import { ErrorBoundary } from './components/ErrorBoundary';
import { LoadingProvider } from './context/LoadingContext';
import { Skeleton } from './components/ui/skeleton';
import { Button } from './components/ui/button';

// Lazy load pages
const Dashboard = lazy(() => import('./pages/Dashboard'));
const DataSources = lazy(() => import('./pages/DataSources'));

// Loading fallback
const PageSkeleton = () => (
  <div className="container mx-auto py-6">
    <Skeleton className="h-10 w-1/4 mb-6" />
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      {[1, 2, 3].map((i) => (
        <Skeleton key={i} className="h-64 w-full" />
      ))}
    </div>
  </div>
);

function App() {
  return (
    <LoadingProvider>
      <Router>
        <div className="min-h-screen bg-background">
          {/* Navigation */}
          <header className="border-b">
            <div className="container mx-auto px-4 py-4 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <h1 className="text-xl font-bold">JPS Prospect Aggregate</h1>
              </div>
              <nav className="flex items-center gap-4">
                <Link to="/">
                  <Button variant="ghost">Dashboard</Button>
                </Link>
                <Link to="/data-sources">
                  <Button variant="ghost">Data Sources</Button>
                </Link>
              </nav>
            </div>
          </header>

          {/* Main content */}
          <main className="container mx-auto px-4">
            <ErrorBoundary>
              <Suspense fallback={<PageSkeleton />}>
                <Routes>
                  <Route path="/" element={<Dashboard />} />
                  <Route path="/data-sources" element={<DataSources />} />
                </Routes>
              </Suspense>
            </ErrorBoundary>
          </main>

          {/* Footer */}
          <footer className="border-t mt-12">
            <div className="container mx-auto px-4 py-6">
              <p className="text-center text-sm text-muted-foreground">
                &copy; {new Date().getFullYear()} JPS Prospect Aggregate. All rights reserved.
              </p>
            </div>
          </footer>
        </div>
      </Router>
    </LoadingProvider>
  );
}

export default App;
