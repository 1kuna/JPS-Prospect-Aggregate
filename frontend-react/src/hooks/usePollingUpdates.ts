import { useEffect, useCallback, useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';

interface PollingOptions {
  onProspectUpdate?: (prospectId: string, updates: any) => void;
  enableAnimations?: boolean;
  baseInterval?: number; // Base polling interval in ms
  activeInterval?: number; // Faster polling during active enhancements
}


export const usePollingUpdates = (options: PollingOptions = {}) => {
  const {
    onProspectUpdate,
    enableAnimations = true,
    baseInterval = 5000, // 5 seconds normal polling
    activeInterval = 2000, // 2 seconds during active enhancements
  } = options;

  const queryClient = useQueryClient();
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const lastSeenTimestamps = useRef<Map<string, string>>(new Map());
  const recentlyUpdatedProspects = useRef<Set<string>>(new Set());
  const animationTimeouts = useRef<Map<string, NodeJS.Timeout>>(new Map());
  
  // Track if any prospects are being enhanced
  const [hasActiveEnhancements, setHasActiveEnhancements] = useState(false);
  const [isPolling, setIsPolling] = useState(false);

  // Check for active enhancements by monitoring the queue status
  const checkForActiveEnhancements = useCallback(async () => {
    try {
      const response = await fetch('/api/llm/queue/status');
      if (response.ok) {
        const queueStatus = await response.json();
        // Only show as active if there are items in the queue
        const hasActive = queueStatus.queue_size > 0;
        setHasActiveEnhancements(hasActive);
        return hasActive;
      }
    } catch (error) {
      console.warn('Failed to check queue status:', error);
    }
    return false;
  }, []);

  // Fetch prospects and detect changes
  const checkForUpdates = useCallback(async () => {
    try {
      // Get current prospects data
      const currentData = queryClient.getQueryData(['prospects']);
      if (!currentData || !(currentData as any).data) {
        return;
      }

      const prospects = (currentData as any).data;
      const updatedProspects: string[] = [];

      // Check each prospect for updates
      prospects.forEach((prospect: any) => {
        const lastSeen = lastSeenTimestamps.current.get(prospect.id);
        const currentTimestamp = prospect.ollama_processed_at || prospect.loaded_at;
        
        // If this prospect has a newer timestamp, it was updated
        if (currentTimestamp && currentTimestamp !== lastSeen) {
          lastSeenTimestamps.current.set(prospect.id, currentTimestamp);
          
          if (lastSeen) { // Only trigger animation if we've seen this prospect before
            updatedProspects.push(prospect.id);
            onProspectUpdate?.(prospect.id, prospect);
          }
        }
      });

      // Handle animations for updated prospects
      if (enableAnimations && updatedProspects.length > 0) {
        updatedProspects.forEach(prospectId => {
          // Add to recently updated set
          recentlyUpdatedProspects.current.add(prospectId);
          
          // Clear any existing timeout for this prospect
          const existingTimeout = animationTimeouts.current.get(prospectId);
          if (existingTimeout) {
            clearTimeout(existingTimeout);
          }
          
          // Set new timeout to remove animation
          const timeout = setTimeout(() => {
            recentlyUpdatedProspects.current.delete(prospectId);
            animationTimeouts.current.delete(prospectId);
            
            // Trigger a re-render by invalidating queries
            queryClient.invalidateQueries({ queryKey: ['prospects'], refetchType: 'none' });
          }, 3000); // Animation lasts 3 seconds
          
          animationTimeouts.current.set(prospectId, timeout);
        });

        // Trigger re-render to show animations
        queryClient.invalidateQueries({ queryKey: ['prospects'], refetchType: 'none' });
      }

    } catch (error) {
      console.warn('Failed to check for updates:', error);
    }
  }, [queryClient, onProspectUpdate, enableAnimations]);

  // Start/stop polling based on activity
  const startPolling = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
    }

    const pollInterval = hasActiveEnhancements ? activeInterval : baseInterval;
    
    intervalRef.current = setInterval(async () => {
      await checkForActiveEnhancements();
      await checkForUpdates();
    }, pollInterval);
    
    setIsPolling(true);
  }, [hasActiveEnhancements, activeInterval, baseInterval, checkForActiveEnhancements, checkForUpdates]);

  const stopPolling = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    setIsPolling(false);
  }, []);

  // Initialize polling
  useEffect(() => {
    startPolling();
    
    return () => {
      stopPolling();
      // Clear all animation timeouts
      animationTimeouts.current.forEach(timeout => clearTimeout(timeout));
      animationTimeouts.current.clear();
    };
  }, [startPolling, stopPolling]);

  // Restart polling when activity status changes
  useEffect(() => {
    if (isPolling) {
      startPolling();
    }
  }, [hasActiveEnhancements, startPolling, isPolling]);

  // Check if a prospect was recently updated (for animations)
  const isProspectRecentlyUpdated = useCallback((prospectId: string) => {
    return recentlyUpdatedProspects.current.has(prospectId);
  }, []);

  // Manual trigger for immediate check (useful after user actions)
  const triggerUpdate = useCallback(async () => {
    await checkForActiveEnhancements();
    await checkForUpdates();
  }, [checkForActiveEnhancements, checkForUpdates]);

  return {
    isPolling,
    hasActiveEnhancements,
    isProspectRecentlyUpdated,
    triggerUpdate,
    startPolling,
    stopPolling,
  };
};