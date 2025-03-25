import { ApiResponse } from './api';

export interface Proposal {
  id: number;
  title: string;
  status: ProposalStatus;
  dataSourceId: number;
  createdAt: string;
  updatedAt: string;
  // Add other proposal-specific fields
}

export type ProposalStatus = 'draft' | 'pending' | 'approved' | 'rejected';

export interface ProposalStatistics {
  total: number;
  byStatus: Record<ProposalStatus, number>;
  recentActivity: {
    date: string;
    count: number;
  }[];
}

export interface ProposalFilters {
  status?: ProposalStatus;
  dataSourceId?: number;
  startDate?: string;
  endDate?: string;
  search?: string;
}

export interface ProposalListResponse extends ApiResponse<Proposal[]> {}
export interface ProposalResponse extends ApiResponse<Proposal> {}
export interface ProposalStatisticsResponse extends ApiResponse<ProposalStatistics> {} 