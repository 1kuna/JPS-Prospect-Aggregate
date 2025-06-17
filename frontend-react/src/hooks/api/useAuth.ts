import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
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
    const response = await fetch(`${API_BASE}/signup`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify(data),
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.message || 'Sign up failed');
    }
    
    return response.json();
  },

  signIn: async (data: SignInRequest): Promise<ApiResponse<{ user: User; message: string }>> => {
    const response = await fetch(`${API_BASE}/signin`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify(data),
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.message || 'Sign in failed');
    }
    
    return response.json();
  },

  signOut: async (): Promise<ApiResponse<{ message: string }>> => {
    const response = await fetch(`${API_BASE}/signout`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.message || 'Sign out failed');
    }
    
    return response.json();
  },

  getStatus: async (): Promise<ApiResponse<AuthStatus>> => {
    const response = await fetch(`${API_BASE}/status`, {
      method: 'GET',
      credentials: 'include',
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.message || 'Failed to get auth status');
    }
    
    return response.json();
  },

  getCurrentUser: async (): Promise<ApiResponse<{ user: User }>> => {
    const response = await fetch(`${API_BASE}/me`, {
      method: 'GET',
      credentials: 'include',
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.message || 'Failed to get current user');
    }
    
    return response.json();
  },
};

// Hook to get authentication status
export const useAuthStatus = () => {
  return useQuery({
    queryKey: ['auth', 'status'],
    queryFn: authApi.getStatus,
    retry: false,
    staleTime: 5 * 60 * 1000, // 5 minutes
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
    onSuccess: () => {
      // Clear all queries when user signs out
      queryClient.clear();
    },
  });
};