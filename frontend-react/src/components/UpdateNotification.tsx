import { useState, useEffect } from 'react';
import { useStore } from '@/store/useStore';
import { Alert, AlertDescription, AlertTitle, Button } from '@/components/ui';
import { RefreshCw, X } from 'lucide-react';

interface UpdateNotificationProps {
  pollingInterval?: number; // in milliseconds
  onRefresh: () => void;
}

export function UpdateNotification({ 
  pollingInterval = 10000, 
  onRefresh 
}: UpdateNotificationProps) {
  const [isVisible, setIsVisible] = useState(false);
  const [lastChecked, setLastChecked] = useState<Date | null>(null);
  const lastUpdated = useStore(state => state.lastUpdated);

  // Check for updates periodically
  useEffect(() => {
    const checkForUpdates = () => {
      // If we have a lastChecked time and a lastUpdated time
      if (lastChecked && lastUpdated) {
        // If the data was updated after our last check
        if (lastUpdated > lastChecked) {
          setIsVisible(true);
        }
      }
      
      // Update the last checked time
      setLastChecked(new Date());
    };

    // Initial check
    checkForUpdates();
    
    // Set up interval for checking
    const intervalId = setInterval(checkForUpdates, pollingInterval);
    
    // Clean up interval on unmount
    return () => clearInterval(intervalId);
  }, [lastChecked, lastUpdated, pollingInterval]);

  const handleRefresh = () => {
    onRefresh();
    setIsVisible(false);
    setLastChecked(new Date());
  };

  const handleDismiss = () => {
    setIsVisible(false);
    setLastChecked(new Date());
  };

  if (!isVisible) {
    return null;
  }

  return (
    <Alert className="fixed top-4 left-1/2 transform -translate-x-1/2 z-50 w-auto min-w-[300px] shadow-lg">
      <div className="flex items-center justify-between">
        <div className="flex items-center">
          <RefreshCw className="h-4 w-4 mr-2" />
          <div>
            <AlertTitle>New data available!</AlertTitle>
            <AlertDescription>
              Click refresh to update your view with the latest data.
            </AlertDescription>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button size="sm" onClick={handleRefresh}>
            Refresh
          </Button>
          <Button size="icon" variant="ghost" onClick={handleDismiss}>
            <X className="h-4 w-4" />
            <span className="sr-only">Dismiss</span>
          </Button>
        </div>
      </div>
    </Alert>
  );
} 