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
  extra?: Record<string, unknown>;
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
  dataSourceIds?: number[];  // Changed to array for multiple selection
  startDate?: string;
  endDate?: string;
  search?: string;
  keywords?: string;
  naics?: string;
  agency?: string;
}

// Query data structure for prospects
export interface ProspectsQueryData {
  data: Prospect[];
  pagination?: {
    page: number;
    pageSize: number;
    total: number;
  };
}