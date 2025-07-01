import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { get, post } from '@/utils/apiUtils';
import { 
  ApiResponse, 
  User, 
  AuthStatus, 
  SignUpRequest, 
  SignInRequest 
} from '../../types/api';

const API_BASE = '/api/auth';

// Auth API functions
const authApi = {
  signUp: async (data: SignUpRequest): Promise<ApiResponse<{ user: User; message: string }>> => {
    return await post<ApiResponse<{ user: User; message: string }>>(
      `${API_BASE}/signup`, 
      data,
      { credentials: 'include' }
    );
  },

  signIn: async (data: SignInRequest): Promise<ApiResponse<{ user: User; message: string }>> => {
    return await post<ApiResponse<{ user: User; message: string }>>(
      `${API_BASE}/signin`,
      data,
      { credentials: 'include' }
    );
  },

  signOut: async (): Promise<ApiResponse<{ message: string }>> => {
    return await post<ApiResponse<{ message: string }>>(
      `${API_BASE}/signout`,
      undefined,
      { credentials: 'include' }
    );
  },

  getStatus: async (): Promise<ApiResponse<AuthStatus>> => {
    return await get<ApiResponse<AuthStatus>>(
      `${API_BASE}/status`,
      { credentials: 'include' }
    );
  },

  getCurrentUser: async (): Promise<ApiResponse<{ user: User }>> => {
    return await get<ApiResponse<{ user: User }>>(
      `${API_BASE}/me`,
      { credentials: 'include' }
    );
  },
};

// Hook to get authentication status
export const useAuthStatus = () => {
  return useQuery({
    queryKey: ['auth', 'status'],
    queryFn: authApi.getStatus,
    retry: false,
    staleTime: 0, // Always consider auth data stale for immediate updates
    refetchOnWindowFocus: false, // Prevent unnecessary refetches on focus
  });
};

// Hook to get current user
export const useCurrentUser = () => {
  const { data: authStatus } = useAuthStatus();
  
  return useQuery({
    queryKey: ['auth', 'user'],
    queryFn: authApi.getCurrentUser,
    enabled: authStatus?.data?.authenticated === true,
    retry: false,
  });
};

// Hook for sign up
export const useSignUp = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: authApi.signUp,
    onSuccess: () => {
      // Invalidate auth queries to refetch status
      queryClient.invalidateQueries({ queryKey: ['auth'] });
    },
  });
};

// Hook for sign in
export const useSignIn = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: authApi.signIn,
    onSuccess: () => {
      // Invalidate auth queries to refetch status
      queryClient.invalidateQueries({ queryKey: ['auth'] });
    },
  });
};

// Hook for sign out
export const useSignOut = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: authApi.signOut,
    onSuccess: async () => {
      // Set auth status to unauthenticated immediately for instant UI update
      queryClient.setQueryData(['auth', 'status'], {
        data: {
          authenticated: false,
          user: null
        }
      });
      
      // Clear all cached data
      queryClient.clear();
      
      // Force immediate refetch of auth status to ensure consistency
      await queryClient.refetchQueries({ 
        queryKey: ['auth', 'status'], 
        type: 'active' 
      });
    },
  });
};