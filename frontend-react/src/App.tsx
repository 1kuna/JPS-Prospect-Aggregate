import { Suspense, lazy, memo } from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import { ErrorBoundary } from './components/ErrorBoundary';
import { LoadingProvider } from './context/LoadingContext';
import { Skeleton } from './components/ui/skeleton';
import { Card, CardHeader } from './components/ui/card';
import './index.css';

// Lazy load pages
const Proposals = lazy(() => import('./pages/Proposals'));
const DataSources = lazy(() => import('./pages/DataSources'));

// Loading fallback - memoized to prevent unnecessary re-renders
const PageSkeleton = memo(() => (
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
));

function App() {
  return (
    <LoadingProvider>
      <Router>
        <div className="app-container">
          {/* Navigation */}
          <header className="navbar">
            <div className="container">
              <div className="navbar-brand">JPS Prospect Aggregate</div>
              <nav className="navbar-links">
                <Link to="/proposals">Proposals</Link>
                <Link to="/data-sources">Data Sources</Link>
              </nav>
            </div>
          </header>

          {/* Main content */}
          <main className="main-content">
            <div className="container">
              <ErrorBoundary>
                <Suspense fallback={<PageSkeleton />}>
                  <Routes>
                    <Route path="/" element={<Proposals />} />
                    <Route path="/proposals" element={<Proposals />} />
                    <Route path="/data-sources" element={<DataSources />} />
                  </Routes>
                </Suspense>
              </ErrorBoundary>
            </div>
          </main>

          {/* Footer */}
          <footer className="footer">
            <div className="container">
              <p className="text-center text-sm text-muted">
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
