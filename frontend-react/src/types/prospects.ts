export interface Prospect {
  id: string | number;
  title: string;
  status: ProspectStatus;
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

export enum ProspectStatus {
  DRAFT = 'Draft',
  SUBMITTED = 'Submitted',
  REVIEW = 'In Review',
  APPROVED = 'Approved',
  REJECTED = 'Rejected',
}

export interface ProspectStatistics {
  data: {
    total: number;
    approved: number;
    pending: number;
    rejected: number;
  };
}

export interface ProspectFilters {
  status?: ProspectStatus;
  dataSourceId?: number;
  startDate?: string;
  endDate?: string;
  search?: string;
}