export interface Prospect {
  id: string | number;
  nativeId?: string;
  title: string;
  aiEnhancedTitle?: string;
  description?: string;
  agency?: string;
  naicsCode?: string;
  naicsDescription?: string;
  naicsSource?: string;
  estimatedValue?: string | number;
  estValueUnit?: string;
  valueOriginalText?: string;
  valueMin?: number;
  valueMax?: number;
  valueSingleEstimate?: number;
  releaseDate?: string;
  awardDate?: string;
  awardFiscalYear?: number;
  placeCity?: string;
  placeState?: string;
  placeCountry?: string;
  contractType?: string;
  setAside?: string;
  primaryContactEmail?: string;
  primaryContactName?: string;
  loadedAt?: string;
  ollamaProcessedAt?: string;
  ollamaModelVersion?: string;
  enhancementStatus?: string;
  enhancementStartedAt?: string;
  enhancementUserId?: number;
  extra?: any;
  link?: string;
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