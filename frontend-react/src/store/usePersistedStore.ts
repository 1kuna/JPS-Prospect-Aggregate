import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { createPersistConfig } from './middleware/persist';

interface UserPreferences {
  theme: 'light' | 'dark' | 'system';
  language: string;
  tableSettings: {
    itemsPerPage: number;
    defaultSortField: string;
    defaultSortDirection: 'asc' | 'desc';
  };
  tableView: {
    perPage: number;
    sortBy: string;
    sortOrder: 'asc' | 'desc';
  };
  lastVisitedPage: string;
  isNavOpen: boolean;
}

interface PersistedState {
  userPreferences: UserPreferences;
  
  // Actions
  setTheme: (theme: 'light' | 'dark' | 'system') => void;
  setLanguage: (language: string) => void;
  setTableSettings: (settings: Partial<UserPreferences['tableSettings']>) => void;
  setTableView: (tableView: Partial<UserPreferences['tableView']>) => void;
  setLastVisitedPage: (page: string) => void;
  setNavOpen: (isOpen: boolean) => void;
  resetPreferences: () => void;
}

const DEFAULT_PREFERENCES: UserPreferences = {
  theme: 'system',
  language: 'en',
  tableSettings: {
    itemsPerPage: 10,
    defaultSortField: 'release_date',
    defaultSortDirection: 'desc'
  },
  tableView: {
    perPage: 25,
    sortBy: 'release_date',
    sortOrder: 'desc'
  },
  lastVisitedPage: '/',
  isNavOpen: true
};

export const usePersistedStore = create<PersistedState>()(
  persist(
    (set) => ({
      userPreferences: DEFAULT_PREFERENCES,
      
      setTheme: (theme) => set((state) => ({
        userPreferences: {
          ...state.userPreferences,
          theme
        }
      })),
      
      setLanguage: (language) => set((state) => ({
        userPreferences: {
          ...state.userPreferences,
          language
        }
      })),
      
      setTableSettings: (settings) => set((state) => ({
        userPreferences: {
          ...state.userPreferences,
          tableSettings: {
            ...state.userPreferences.tableSettings,
            ...settings
          }
        }
      })),
      
      setTableView: (tableView) => set((state) => ({
        userPreferences: {
          ...state.userPreferences,
          tableView: {
            ...state.userPreferences.tableView,
            ...tableView
          }
        }
      })),
      
      setLastVisitedPage: (page) => set((state) => ({
        userPreferences: {
          ...state.userPreferences,
          lastVisitedPage: page
        }
      })),
      
      setNavOpen: (isOpen) => set((state) => ({
        userPreferences: {
          ...state.userPreferences,
          isNavOpen: isOpen
        }
      })),
      
      resetPreferences: () => set({
        userPreferences: DEFAULT_PREFERENCES
      })
    }),
    createPersistConfig<PersistedState>('user-preferences', (state) => ({
      userPreferences: state.userPreferences
    }))
  )
);

// Helper selectors
export const selectUserPreferences = (state: PersistedState) => state.userPreferences;
export const selectTheme = (state: PersistedState) => state.userPreferences.theme;
export const selectLanguage = (state: PersistedState) => state.userPreferences.language;
export const selectTableSettings = (state: PersistedState) => state.userPreferences.tableSettings;
export const selectTableView = (state: PersistedState) => state.userPreferences.tableView;
export const selectLastVisitedPage = (state: PersistedState) => state.userPreferences.lastVisitedPage;
export const selectIsNavOpen = (state: PersistedState) => state.userPreferences.isNavOpen; 