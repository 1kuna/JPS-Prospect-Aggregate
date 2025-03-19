// Main hooks
export { default as useData } from './useData';
export * from './useData';

// Adapters for backwards compatibility
export { useDataFetchingAdapter, useStoreDataAdapter } from './adapters';

/**
 * @deprecated Use useData hook instead which combines the features of useDataFetching and useStoreData
 */
export { default as useDataFetching } from './useDataFetching';
export * from './useDataFetching';

export { default as useForm } from './useForm';
export * from './useForm';

/**
 * @deprecated Use useData hook instead which combines the features of useDataFetching and useStoreData
 */
export { default as useStoreData } from './useStoreData';
export * from './useStoreData';

export { default as useReactQuery } from './useReactQuery';
export * from './useReactQuery';

export { default as useToast } from './use-toast';
export * from './use-toast';

// Entity-specific hooks
export * from './useDataSources';
export { useStoreSelectors } from './useStoreSelectors';
export {
  useDataSourcesSelectors,
  useProposalsSelectors,
  useStatisticsSelectors,
  useSystemSelectors,
  useUISelectors
} from './useStoreSelectors';

// Re-export persisted store selectors
export {
  selectUserPreferences,
  selectTheme,
  selectTableView,
  selectLastVisitedPage,
  selectIsNavOpen
} from '../store/usePersistedStore';

// Re-export selectors for convenience
export * from '../store/selectors';

// Legacy hooks (deprecated) - will be removed in the next major version
/**
 * @deprecated Use useData or useReactQuery hooks instead. This hook will be removed in the next major version.
 */
export * from './useFetch';

/**
 * @deprecated Use useForm instead. This hook will be removed in the next major version.
 */
export * from './useFormSubmit'; 