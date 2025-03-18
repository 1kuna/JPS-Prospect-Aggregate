import { Socket } from 'socket.io-client';
import { StateCreator } from 'zustand';
import { createToast } from '../useStore';

export type WebSocketMiddlewareState = {
  isSocketConnected: boolean;
  socketError: string | null;
  setupWebSocketListeners: () => void;
  clearSocketError: () => void;
};

export const createWebSocketMiddleware = (socket: Socket) => 
  (set: any, get: any): WebSocketMiddlewareState => ({
    isSocketConnected: false,
    socketError: null,
    
    setupWebSocketListeners: () => {
      // Connection events
      socket.on('connect', () => {
        console.log('WebSocket connected');
        set({ isSocketConnected: true, socketError: null });
      });
      
      socket.on('disconnect', (reason) => {
        console.warn('WebSocket disconnected:', reason);
        set({ isSocketConnected: false });
        
        if (reason === 'io server disconnect') {
          // The server has forcefully disconnected the socket
          setTimeout(() => {
            console.log('Attempting to reconnect...');
            socket.connect();
          }, 5000); // Try to reconnect after 5 seconds
        }
      });
      
      socket.on('connect_error', (error) => {
        console.error('WebSocket connection error:', error);
        set({ isSocketConnected: false, socketError: error.message });
      });
      
      // Data updates
      socket.on('dataSourceUpdated', (updatedSource) => {
        const currentSources = get().dataSources;
        if (!currentSources) return;
        
        const updatedSources = currentSources.map((source: any) => 
          source.id === updatedSource.id ? { ...source, ...updatedSource } : source
        );
        
        set({ dataSources: updatedSources });
        createToast(
          'Data Source Updated', 
          `"${updatedSource.name}" has been updated`, 
          'default',
          3000
        );
      });
      
      socket.on('dataSourceDeleted', (id) => {
        const currentSources = get().dataSources;
        if (!currentSources) return;
        
        const filteredSources = currentSources.filter((source: any) => source.id !== id);
        set({ dataSources: filteredSources });
      });
      
      socket.on('newProposalsAdded', (data) => {
        // Refresh proposals if we're on the proposals page
        if (window.location.pathname.includes('/proposals')) {
          get().fetchProposals();
        }
        
        // Update the data source proposal count
        const { dataSourceId, count } = data;
        const currentSources = get().dataSources;
        if (!currentSources) return;
        
        const updatedSources = currentSources.map((source: any) => 
          source.id === dataSourceId 
            ? { ...source, proposalCount: (source.proposalCount || 0) + count } 
            : source
        );
        
        set({ dataSources: updatedSources });
        
        // Show a toast notification
        createToast(
          'New Proposals', 
          `${count} new proposals added from a data source`, 
          'success',
          5000
        );
      });
      
      socket.on('scrapingComplete', (data) => {
        const { dataSourceId, success, error, proposalsAdded } = data;
        
        // Refresh the data sources to get updated last scraped time
        get().fetchDataSources();
        
        // Turn off the pulling progress indicator
        get().setPullingProgress(dataSourceId, false);
        
        // Show a toast with the result
        if (success) {
          createToast(
            'Scraping Complete', 
            `Added ${proposalsAdded} new proposals`, 
            'success',
            5000
          );
        } else {
          createToast(
            'Scraping Failed', 
            error || 'An error occurred while scraping', 
            'destructive',
            0 // Don't auto-dismiss error toasts
          );
        }
      });
      
      socket.on('databaseOperationComplete', (data) => {
        const { operation, success, error } = data;
        
        // Refresh data as needed based on the operation
        if (success) {
          if (['rebuild', 'reset', 'restore'].includes(operation)) {
            // These operations affect multiple data types
            get().fetchDataSources();
            get().fetchProposals();
            get().fetchStatistics();
          } else if (operation === 'backup') {
            // Refresh the backups list
            get().manageBackups('list');
          }
          
          createToast(
            'Operation Complete', 
            `${operation.charAt(0).toUpperCase() + operation.slice(1)} completed successfully`, 
            'success',
            5000
          );
        } else {
          createToast(
            'Operation Failed', 
            error || `${operation} operation failed`, 
            'destructive',
            0
          );
        }
      });
    },
    
    clearSocketError: () => {
      set({ socketError: null });
    }
  }); 