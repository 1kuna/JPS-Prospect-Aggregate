import { StateCreator } from 'zustand';

/**
 * Creates a reusable async slice pattern for handling loading, error states, and data
 * for asynchronous operations in the store
 */
type AsyncAction<T, P extends any[]> = (...args: P) => Promise<T>;

interface AsyncActionMap {
  [key: string]: AsyncAction<any, any[]>;
}

export interface AsyncState<T> {
  data: T;
  loading: boolean;
  error: Error | null;
}

export const createAsyncSlice = <T, S extends object>(
  name: string,
  asyncActions: AsyncActionMap,
  initialData: T
) => (set: any, get: any): Record<string, any> => {
  // Create the initial state with the data, loading, and error
  const initialState = {
    [name]: initialData,
    [`${name}Loading`]: false,
    [`${name}Error`]: null,
  };
  
  // Create action creators for each async action
  const actionCreators = Object.entries(asyncActions).reduce(
    (acc, [actionName, actionFn]) => ({
      ...acc,
      [actionName]: async (...args: any[]) => {
        // Set loading state to true
        set((state: any) => ({ 
          [`${name}Loading`]: true 
        }));
        
        try {
          // Execute the async action
          const result = await actionFn(...args);
          
          // Update state with the result and reset loading/error
          set((state: any) => ({ 
            [name]: result, 
            [`${name}Loading`]: false,
            [`${name}Error`]: null
          }));
          
          return result;
        } catch (error) {
          // Handle errors
          const errorObj = error instanceof Error ? error : new Error(String(error));
          
          // Update state with the error and reset loading
          set((state: any) => ({ 
            [`${name}Loading`]: false,
            [`${name}Error`]: { message: errorObj.message, originalError: errorObj }
          }));
          
          throw errorObj;
        }
      }
    }),
    {}
  );
  
  // Return the initial state and action creators
  return {
    ...initialState,
    ...actionCreators
  };
};

// Helper function to create selectors for async state
export const createAsyncSelectors = <T>(name: string) => ({
  [`select${name.charAt(0).toUpperCase() + name.slice(1)}`]: (state: any) => state[name],
  [`select${name.charAt(0).toUpperCase() + name.slice(1)}Loading`]: (state: any) => state[`${name}Loading`],
  [`select${name.charAt(0).toUpperCase() + name.slice(1)}Error`]: (state: any) => state[`${name}Error`],
});

// Higher-order function to create domain slices
export const createDomainSlice = <T extends Record<string, any>, S extends object>(
  domainConfig: {
    name: string;
    initialState: Partial<T>;
    actions: Record<string, AsyncAction<any, any[]>>;
    extraReducers?: (set: any, get: any) => Record<string, any>;
  }
) => (set: any, get: any): Record<string, any> => {
  const { name, initialState, actions, extraReducers } = domainConfig;
  
  const asyncSlice = createAsyncSlice(name, actions, initialState)(set, get);
  const extraSlice = extraReducers ? extraReducers(set, get) : {};
  
  return {
    ...asyncSlice,
    ...extraSlice
  };
}; 