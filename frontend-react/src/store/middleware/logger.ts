import { StateCreator } from 'zustand';

// Debug mode flag that can be toggled based on environment
let DEBUG_MODE = process.env.NODE_ENV === 'development';

// Enable/disable debug mode programmatically
export const setDebugMode = (enabled: boolean) => {
  DEBUG_MODE = enabled;
};

/**
 * Logger middleware that logs all state changes to the console
 * This is a factory function that creates a middleware
 * 
 * @param storeName Name of the store for logging clarity
 * @returns A middleware function that wraps a state creator
 */
export function logger<T>(storeName: string) {
  return (config: StateCreator<T>): StateCreator<T> => (set, get, api) => {
    const loggedSet: typeof set = (...args) => {
      if (!DEBUG_MODE) {
        return set(...args);
      }
      
      // Get current state for comparison
      const oldState = get();
      
      // Call the original set function
      const result = set(...args);
      
      // Get the new state after the update
      const newState = get();
      
      // Log the state change with color styling
      console.groupCollapsed(
        `%c${storeName} %cState Updated ${new Date().toLocaleTimeString()}`,
        'color: #3b82f6; font-weight: bold;',
        'color: #6b7280; font-weight: normal;'
      );
      
      // Log the action (if it's a function, we can't stringify it meaningfully)
      const action = typeof args[0] === 'function' ? '<function>' : args[0];
      console.log('%cAction:', 'font-weight: bold;', action);
      
      // Find changes between old and new state and log them
      const changes: Record<string, { from: any; to: any }> = {};
      
      Object.keys(newState).forEach(key => {
        if (oldState[key] !== newState[key]) {
          changes[key] = {
            from: oldState[key],
            to: newState[key]
          };
        }
      });
      
      if (Object.keys(changes).length > 0) {
        console.log('%cChanges:', 'font-weight: bold;');
        Object.entries(changes).forEach(([key, { from, to }]) => {
          console.log(
            `%c${key}:`, 
            'color: #059669; font-weight: bold;',
            { from, to }
          );
        });
      } else {
        console.log('%cNo changes detected', 'color: #6b7280;');
      }
      
      // Log the full new state for debugging
      console.log('%cCurrent State:', 'font-weight: bold;', newState);
      
      console.groupEnd();
      
      return result;
    };
    
    return config(loggedSet, get, api);
  };
}

/**
 * Performance monitoring middleware
 * Measures the time taken to run state updates
 * 
 * @param storeName Name of the store for logging clarity
 * @returns A middleware function that wraps a state creator
 */
export function perfMonitor<T>(storeName: string) {
  return (config: StateCreator<T>): StateCreator<T> => (set, get, api) => {
    const monitoredSet: typeof set = (...args) => {
      if (!DEBUG_MODE) {
        return set(...args);
      }
      
      const label = `[${storeName}] State update`;
      console.time(label);
      
      const result = set(...args);
      
      console.timeEnd(label);
      return result;
    };
    
    return config(monitoredSet, get, api);
  };
} 