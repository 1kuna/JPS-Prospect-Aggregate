// Type definition for pagination data
interface PaginationData {
  total: number;
  page: number;
  pageSize: number;
  // Removed optional totalPages, calculate on frontend if needed
}

export interface ApiResponse<T> {
  data: T;
  status: string;
  message?: string;
  pagination?: PaginationData;
}

// Type definition for API error response