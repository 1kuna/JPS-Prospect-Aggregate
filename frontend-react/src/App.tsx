import { Suspense, lazy, memo, useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import { ErrorBoundary } from './components/ErrorBoundary';
import { LoadingProvider } from './context/LoadingContext';
import { 
  Skeleton, 
  Card, 
  CardHeader,
  Statistics,
  DatabaseOperations,
  UpdateNotification
} from './components';
import { useStore } from './store/useStore';
import { RefreshCw } from 'lucide-react';
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
  const [isStatsOpen, setIsStatsOpen] = useState(false);
  const fetchProposals = useStore(state => state.fetchProposals);
  const fetchDataSources = useStore(state => state.fetchDataSources);
  const proposals = useStore(state => state.proposals);
  const dataSources = useStore(state => state.dataSources);
  const loading = useStore(state => state.loading);
  const errors = useStore(state => state.errors);

  // Fetch data on component mount
  useEffect(() => {
    console.log('App mounted, fetching data...');
    fetchProposals().then(() => {
      console.log('Proposals fetched successfully');
    }).catch(error => {
      console.error('Error fetching proposals:', error);
    });
    
    fetchDataSources().then(() => {
      console.log('Data sources fetched successfully');
    }).catch(error => {
      console.error('Error fetching data sources:', error);
    });
  }, [fetchProposals, fetchDataSources]);

  // Log state changes for debugging
  useEffect(() => {
    console.log('Current state:', { 
      proposals, 
      dataSources, 
      loading, 
      errors 
    });
  }, [proposals, dataSources, loading, errors]);

  const handleRefresh = () => {
    // Refresh all data
    console.log('Refreshing data...');
    fetchProposals();
    fetchDataSources();
  };

  return (
    <LoadingProvider>
      <Router>
        <div className="min-h-screen bg-background flex flex-col">
          {/* Update notification */}
          <UpdateNotification onRefresh={handleRefresh} />

          {/* Navigation */}
          <header className="bg-blue-600 shadow-md">
            <div className="container mx-auto px-4 py-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-4">
                  <div className="text-xl font-bold text-white">JPS Prospect Aggregate</div>
                  <nav className="hidden md:flex space-x-4">
                    <Link to="/proposals" className="text-white hover:text-white/80 font-medium">Proposals</Link>
                    <Link to="/data-sources" className="text-white hover:text-white/80 font-medium">Data Sources</Link>
                    <button 
                      onClick={() => setIsStatsOpen(true)}
                      className="text-white hover:text-white/80 font-medium"
                    >
                      Statistics
                    </button>
                  </nav>
                </div>

                <div className="flex items-center space-x-4">
                  <div className="flex items-center text-sm text-white">
                    <RefreshCw className="h-3 w-3 mr-1 animate-pulse" />
                    <span>Real-time updates active</span>
                  </div>
                  <DatabaseOperations />
                </div>
              </div>
            </div>
          </header>

          {/* Main content */}
          <main className="flex-1 py-6">
            <div className="container mx-auto px-4">
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

          {/* Statistics Modal */}
          <Statistics isOpen={isStatsOpen} onClose={() => setIsStatsOpen(false)} />
        </div>
      </Router>
    </LoadingProvider>
  );
}

export default App;
