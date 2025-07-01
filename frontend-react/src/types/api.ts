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

// User types
export interface User {
  id: number;
  email: string;
  first_name: string;
  created_at: string;
  last_login_at: string | null;
  timezone?: string; // User's preferred timezone (e.g., 'America/New_York')
  locale?: string;   // User's preferred locale (e.g., 'en-US')
}

export interface AuthStatus {
  authenticated: boolean;
  user: User | null;
}

// Decision types
export interface GoNoGoDecision {
  id: number;
  prospect_id: string;
  user_id: number;
  decision: 'go' | 'no-go';
  reason: string | null;
  created_at: string;
  updated_at: string;
  user?: User;
  prospect_title?: string;
}

export interface DecisionStats {
  total_decisions: number;
  go_decisions: number;
  nogo_decisions: number;
  recent_decisions_30d: number;
  go_percentage: number;
}

// Authentication request types
export interface SignUpRequest {
  email: string;
  first_name: string;
}

export interface SignInRequest {
  email: string;
}

export interface CreateDecisionRequest {
  prospect_id: string;
  decision: 'go' | 'no-go';
  reason?: string;
}

// Type definition for API error response
export interface ApiErrorData {
  error?: string;
  message?: string;
  status_code?: number;
  details?: Record<string, unknown>;
}

// Extended pagination with optional fields
export interface PaginationMeta extends PaginationData {
  totalPages?: number;
  hasNext?: boolean;
  hasPrevious?: boolean;
}