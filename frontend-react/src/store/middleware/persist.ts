import { StateStorage, PersistOptions } from 'zustand/middleware';

/**
 * Custom storage implementation that wraps localStorage with error handling
 */
export const persistStorage: StateStorage = {
  getItem: (name: string): string | null => {
    try {
      const value = localStorage.getItem(name);
      return value;
    } catch (error) {
      console.error('Error retrieving from localStorage:', error);
      return null;
    }
  },
  setItem: (name: string, value: string): void => {
    try {
      localStorage.setItem(name, value);
    } catch (error) {
      console.error('Error storing in localStorage:', error);
      // If storage fails due to size limits, try to clear old data
      if (error instanceof DOMException && error.name === 'QuotaExceededError') {
        console.warn('Storage quota exceeded, clearing localStorage');
        localStorage.clear();
        try {
          localStorage.setItem(name, value);
        } catch (retryError) {
          console.error('Still failed to store data after clearing localStorage', retryError);
        }
      }
    }
  },
  removeItem: (name: string): void => {
    try {
      localStorage.removeItem(name);
    } catch (error) {
      console.error('Error removing from localStorage:', error);
    }
  }
};

/**
 * Creates a consistent name prefix for persisted stores to avoid collisions
 * @param key The store identifier
 * @returns Full storage key with app prefix
 */
export const createPersistName = (key: string): string => {
  const prefix = 'jps-prospect-';
  return `${prefix}${key}`;
};

/**
 * Creates persist configuration with default options
 * @param name Store name
 * @param partialize Optional function to filter which parts of state to persist
 * @returns PersistOptions configuration
 */
export function createPersistConfig<T>(
  name: string,
  partialize?: (state: T) => Partial<T>
): PersistOptions<T> {
  return {
    name: createPersistName(name),
    storage: persistStorage,
    partialize,
    // Only merge state if schema version matches
    version: 1,
    migrate: (persistedState: any, version) => {
      if (version === 0) {
        // Handle migration from version 0 to 1 if needed
        return persistedState as T;
      }
      return persistedState as T;
    },
    onRehydrateStorage: () => (state) => {
      if (state) {
        console.log(`Store "${name}" rehydrated successfully`);
      } else {
        console.warn(`Failed to rehydrate store "${name}"`);
      }
    }
  };
} 