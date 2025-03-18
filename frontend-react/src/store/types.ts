import { ProposalsState } from './slices/proposalsSlice';
import { DataSourcesState } from './slices/dataSourcesSlice';
import { UIState } from './slices/uiSlice';
import { StatisticsState } from './slices/statisticsSlice';
import { SystemState } from './slices/systemSlice';

export interface StoreState extends 
  ProposalsState,
  DataSourcesState,
  UIState,
  StatisticsState,
  SystemState 
{} 