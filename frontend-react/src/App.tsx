import { Suspense, lazy, memo, useState, useEffect } from 'react';
import { BrowserRouter as Router, Link, useLocation } from 'react-router-dom';
import { ErrorBoundary } from './components/ErrorBoundary';
import { LoadingProvider } from './context/LoadingContext';
import { ToastProvider as OldToastProvider } from './context/ToastContext';
import { ToastProvider } from './components/ui/ToastContainer';
import { 
  Skeleton, 
  Card, 
  CardHeader,
  Statistics,
  DatabaseOperations,
  Toaster
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

// RouteContainer component to force remounting when route changes
const RouteContainer = () => {
  const location = useLocation();
  const [isStatsOpen, setIsStatsOpen] = useState(false);
  const fetchProposals = useStore(state => state.fetchProposals);
  const fetchDataSources = useStore(state => state.fetchDataSources);
  const proposals = useStore(state => state.proposals);
  const dataSources = useStore(state => state.dataSources);
  const loading = useStore(state => state.loading);
  const errors = useStore(state => state.errors);

  // Fetch data on component mount
  useEffect(() => {
    console.log('App mounted, fetching initial data...');
    
    // Create an async function to handle the fetching
    const fetchInitialData = async () => {
      try {
        // Fetch proposals first
        console.log('Fetching proposals...');
        await fetchProposals();
        console.log('Proposals fetched successfully');
        
        // Then fetch data sources
        console.log('Fetching data sources...');
        await fetchDataSources();
        console.log('Data sources fetched successfully');
      } catch (error) {
        console.error('Error fetching initial data:', error);
      }
    };
    
    // Call the async function
    fetchInitialData();
    
    // Set up a refresh interval (every 5 minutes)
    const refreshInterval = setInterval(() => {
      console.log('Auto-refreshing data...');
      fetchProposals().catch(error => {
        console.error('Error auto-refreshing proposals:', error);
      });
      fetchDataSources().catch(error => {
        console.error('Error auto-refreshing data sources:', error);
      });
    }, 5 * 60 * 1000); // 5 minutes
    
    // Clean up the interval on component unmount
    return () => {
      clearInterval(refreshInterval);
    };
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

  // Log when location changes
  useEffect(() => {
    console.log('Location changed to:', location.pathname);
    
    // Fetch data based on current route
    if (location.pathname === '/data-sources') {
      console.log('Fetching data sources for /data-sources route');
      fetchDataSources().catch(error => {
        console.error('Error fetching data sources on route change:', error);
      });
    } else if (location.pathname === '/proposals' || location.pathname === '/') {
      console.log('Fetching proposals for /proposals route');
      fetchProposals().catch(error => {
        console.error('Error fetching proposals on route change:', error);
      });
    }
  }, [location.pathname, fetchDataSources, fetchProposals]);

  // Determine which component to render based on the current route
  const renderRouteContent = () => {
    if (location.pathname === '/data-sources') {
      return <DataSources key="data-sources" />;
    } else if (location.pathname === '/proposals' || location.pathname === '/') {
      return <Proposals key="proposals" />;
    }
    return null;
  };

  return (
    <div className="min-h-screen bg-background flex flex-col">
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
              {renderRouteContent()}
            </Suspense>
          </ErrorBoundary>
        </div>
      </main>

      {/* Statistics Modal */}
      <Statistics isOpen={isStatsOpen} onClose={() => setIsStatsOpen(false)} />
    </div>
  );
};

function App() {
  return (
    <LoadingProvider>
      <OldToastProvider>
        <ToastProvider>
          <Router>
            <RouteContainer />
            <Toaster />
          </Router>
        </ToastProvider>
      </OldToastProvider>
    </LoadingProvider>
  );
}

export default App;
