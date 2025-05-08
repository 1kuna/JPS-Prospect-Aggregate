export interface Proposal {
  id: string | number;
  title: string;
  status: ProposalStatus;
  dataSource?: {
    id: string | number;
    name: string;
  };
  dataSourceId?: number;
  createdAt: string;
  updatedAt?: string;
  url?: string;
  search?: string;
}

export enum ProposalStatus {
  DRAFT = 'Draft',
  SUBMITTED = 'Submitted',
  REVIEW = 'In Review',
  APPROVED = 'Approved',
  REJECTED = 'Rejected',
}

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