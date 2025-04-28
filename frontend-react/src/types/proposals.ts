export interface Proposal {
  id: number;
  title: string;
  status: ProposalStatus;
  dataSourceId: number;
  createdAt: string;
  updatedAt: string;
  // Add other proposal-specific fields
  search?: string;
}

// Enum for Proposal Status (assuming these are possible statuses)
enum ProposalStatus {
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