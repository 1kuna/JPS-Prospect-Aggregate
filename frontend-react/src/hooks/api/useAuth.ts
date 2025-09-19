import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import React from 'react';
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
    staleTime: 0, // Always fresh
    gcTime: 0, // Never cache
    refetchOnWindowFocus: false,
    refetchOnReconnect: true,
    structuralSharing: false, // Ensure new object references trigger re-renders
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
  const [lastError, setLastError] = React.useState<Error | null>(null);
  const [lastData, setLastData] = React.useState<ApiResponse<{ user: User; message: string }> | undefined>(undefined);

  const mutation = useMutation({
    mutationFn: authApi.signUp,
    onMutate: () => setLastError(null),
    onSuccess: (data) => {
      setLastError(null);
      setLastData(data);
      queryClient.invalidateQueries({ queryKey: ['auth'] });
    },
    onError: (error) => {
      if (error instanceof Error) setLastError(error);
    },
  });

  return {
    ...mutation,
    error: (mutation.error as Error | null) ?? lastError,
    data: (mutation.data as typeof lastData) ?? lastData,
  };
};

// Hook for sign in
export const useSignIn = () => {
  const queryClient = useQueryClient();
  const [lastError, setLastError] = React.useState<Error | null>(null);
  const [lastData, setLastData] = React.useState<ApiResponse<{ user: User; message: string }> | undefined>(undefined);

  const mutation = useMutation({
    mutationFn: authApi.signIn,
    onMutate: () => setLastError(null),
    onSuccess: (data) => {
      setLastError(null);
      setLastData(data);
      queryClient.invalidateQueries({ queryKey: ['auth'] });
    },
    onError: (error) => {
      if (error instanceof Error) setLastError(error);
    },
  });

  return {
    ...mutation,
    error: (mutation.error as Error | null) ?? lastError,
    data: (mutation.data as typeof lastData) ?? lastData,
  };
};

// Hook for sign out
export const useSignOut = () => {
  const queryClient = useQueryClient();
  const [lastError, setLastError] = React.useState<Error | null>(null);
  const [lastData, setLastData] = React.useState<ApiResponse<{ message: string }> | undefined>(undefined);

  const mutation = useMutation({
    mutationFn: authApi.signOut,
    onMutate: () => setLastError(null),
    onSuccess: (data) => {
      setLastError(null);
      setLastData(data);
      // Immediately set auth status to false
      queryClient.setQueryData(['auth', 'status'], {
        data: {
          authenticated: false,
          user: null
        }
      });
      queryClient.invalidateQueries();
      setTimeout(() => {
        queryClient.removeQueries({ predicate: (query) => query.queryKey[0] !== 'auth' });
      }, 100);
    },
    onError: (error) => {
      if (error instanceof Error) setLastError(error);
    }
  });

  return {
    ...mutation,
    error: (mutation.error as Error | null) ?? lastError,
    data: (mutation.data as typeof lastData) ?? lastData,
  };
};

// Helper function to check if user is admin
export const useIsAdmin = () => {
  const { data: authStatus } = useAuthStatus();
  const userRole = authStatus?.data?.user?.role;
  return userRole === 'admin' || userRole === 'super_admin';
};

export const useIsSuperAdmin = () => {
  const { data: authStatus } = useAuthStatus();
  return authStatus?.data?.user?.role === 'super_admin';
};

// Helper function to get user role
export const useUserRole = () => {
  const { data: authStatus } = useAuthStatus();
  return authStatus?.data?.user?.role || 'user';
};
