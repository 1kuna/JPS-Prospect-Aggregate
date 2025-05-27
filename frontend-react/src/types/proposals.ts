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
  data: {
    total: number;
    approved: number;
    pending: number;
    rejected: number;
  };
}

export interface ProposalFilters {
  status?: ProposalStatus;
  dataSourceId?: number;
  startDate?: string;
  endDate?: string;
  search?: string;
}