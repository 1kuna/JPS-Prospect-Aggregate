import { ProposalsState } from './slices/proposalsSlice';
import { DataSourcesState } from './slices/dataSourcesSlice';
import { AnalyticsState } from './slices/analyticsSlice';
import { SystemState } from './slices/systemSlice';
import { UIState } from './slices/uiSlice';

// Combined state type
export type StoreState = DataSourcesState &
  ProposalsState &
  AnalyticsState &
  SystemState &
  UIState; 