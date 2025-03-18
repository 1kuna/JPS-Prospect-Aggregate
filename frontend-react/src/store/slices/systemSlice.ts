import { StateCreator } from 'zustand';
import { 
  rebuildDatabase, 
  initializeDatabase, 
  resetEverything, 
  manageBackups 
} from '../api';

export interface SystemState {
  backups: any[];
  loading: { databaseOperations: boolean };
  errors: { databaseOperations: any | null };
  lastUpdated: Date | null;
  
  // Actions
  rebuildDatabase: () => Promise<any>;
  initializeDatabase: () => Promise<any>;
  resetEverything: () => Promise<any>;
  manageBackups: (action: 'create' | 'restore' | 'list', backupId?: string) => Promise<any>;
}

export const systemSlice: StateCreator<SystemState> = (set, get) => ({
  backups: [],
  loading: { databaseOperations: false },
  errors: { databaseOperations: null },
  lastUpdated: null,
  
  rebuildDatabase: async () => {
    set((state) => ({ loading: { ...state.loading, databaseOperations: true } }));
    try {
      const response = await rebuildDatabase();
      set({ 
        loading: { ...get().loading, databaseOperations: false },
        errors: { ...get().errors, databaseOperations: null },
        lastUpdated: new Date()
      });
      return response;
    } catch (error: any) {
      console.error('Error rebuilding database:', error);
      set({ 
        loading: { ...get().loading, databaseOperations: false },
        errors: { ...get().errors, databaseOperations: { message: error.message } }
      });
      throw error;
    }
  },
  
  initializeDatabase: async () => {
    set((state) => ({ loading: { ...state.loading, databaseOperations: true } }));
    try {
      const response = await initializeDatabase();
      set({ 
        loading: { ...get().loading, databaseOperations: false },
        errors: { ...get().errors, databaseOperations: null },
        lastUpdated: new Date()
      });
      return response;
    } catch (error: any) {
      console.error('Error initializing database:', error);
      set({ 
        loading: { ...get().loading, databaseOperations: false },
        errors: { ...get().errors, databaseOperations: { message: error.message } }
      });
      throw error;
    }
  },
  
  resetEverything: async () => {
    set((state) => ({ loading: { ...state.loading, databaseOperations: true } }));
    try {
      const response = await resetEverything();
      set({ 
        loading: { ...get().loading, databaseOperations: false },
        errors: { ...get().errors, databaseOperations: null },
        lastUpdated: new Date()
      });
      return response;
    } catch (error: any) {
      console.error('Error resetting database:', error);
      set({ 
        loading: { ...get().loading, databaseOperations: false },
        errors: { ...get().errors, databaseOperations: { message: error.message } }
      });
      throw error;
    }
  },
  
  manageBackups: async (action, backupId) => {
    set((state) => ({ loading: { ...state.loading, databaseOperations: true } }));
    try {
      const response = await manageBackups(action, backupId);
      
      // If we're listing backups, update the backups list
      if (action === 'list' && response.data) {
        set({ backups: response.data });
      }
      
      set({ 
        loading: { ...get().loading, databaseOperations: false },
        errors: { ...get().errors, databaseOperations: null },
        lastUpdated: new Date()
      });
      
      return response;
    } catch (error: any) {
      console.error('Error managing backups:', error);
      set({ 
        loading: { ...get().loading, databaseOperations: false },
        errors: { ...get().errors, databaseOperations: { message: error.message } }
      });
      throw error;
    }
  }
}); 