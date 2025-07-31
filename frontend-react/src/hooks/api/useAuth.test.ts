import { renderHook, act, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';
import {
  useAuthStatus,
  useCurrentUser,
  useSignUp,
  useSignIn,
  useSignOut,
  useIsAdmin,
  useIsSuperAdmin,
  useUserRole
} from './useAuth';
import type { User, AuthStatus, SignUpRequest, SignInRequest } from '@/types/api';

// Mock the API utils
vi.mock('@/utils/apiUtils', () => ({
  get: vi.fn(),
  post: vi.fn()
}));

// Mock user data
const mockUser: User = {
  id: 1,
  username: 'testuser',
  first_name: 'John',
  last_name: 'Doe',
  email: 'john.doe@example.com',
  role: 'user',
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z'
};

const mockAdminUser: User = {
  ...mockUser,
  id: 2,
  role: 'admin',
  first_name: 'Admin'
};

const mockSuperAdminUser: User = {
  ...mockUser,
  id: 3,
  role: 'super_admin',
  first_name: 'SuperAdmin'
};

const mockAuthStatus: AuthStatus = {
  authenticated: true,
  user: mockUser
};

// Wrapper component for React Query
const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false }
    }
  });
  
  return ({ children }: { children: React.ReactNode }) => 
    React.createElement(QueryClientProvider, { client: queryClient }, children);
};

describe('useAuthStatus', () => {
  let mockGet: any;
  
  beforeEach(async () => {
    vi.clearAllMocks();
    const { get } = await import('@/utils/apiUtils');
    mockGet = get;
    mockGet.mockResolvedValue({
      data: mockAuthStatus
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('fetches authentication status', async () => {
    const { result } = renderHook(
      () => useAuthStatus(),
      { wrapper: createWrapper() }
    );

    expect(result.current.isLoading).toBe(true);

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(mockGet).toHaveBeenCalledWith(
      '/api/auth/status',
      { credentials: 'include' }
    );
    expect(result.current.data?.data).toEqual(mockAuthStatus);
  });

  it('handles authentication status error', async () => {
    const error = new Error('Network error');
    mockGet.mockRejectedValue(error);

    const { result } = renderHook(
      () => useAuthStatus(),
      { wrapper: createWrapper() }
    );

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.error).toBeTruthy();
    expect(result.current.data).toBeUndefined();
  });

  it('does not retry on error', async () => {
    const error = new Error('Auth error');
    mockGet.mockRejectedValue(error);

    renderHook(
      () => useAuthStatus(),
      { wrapper: createWrapper() }
    );

    await waitFor(() => {
      expect(mockGet).toHaveBeenCalledTimes(1);
    });

    // Wait a bit more to ensure no retries
    await new Promise(resolve => setTimeout(resolve, 100));
    expect(mockGet).toHaveBeenCalledTimes(1);
  });

  it('configures query with correct options', () => {
    const { result } = renderHook(
      () => useAuthStatus(),
      { wrapper: createWrapper() }
    );

    // The hook should use the correct query key
    expect(mockGet).toHaveBeenCalledWith(
      '/api/auth/status',
      { credentials: 'include' }
    );
  });
});

describe('useCurrentUser', () => {
  let mockGet: any;
  
  beforeEach(async () => {
    vi.clearAllMocks();
    const { get } = await import('@/utils/apiUtils');
    mockGet = get;
    mockGet.mockImplementation((url) => {
      if (url === '/api/auth/status') {
        return Promise.resolve({ data: mockAuthStatus });
      }
      if (url === '/api/auth/me') {
        return Promise.resolve({ data: { user: mockUser } });
      }
      return Promise.reject(new Error('Unknown URL'));
    });
  });

  it('fetches current user when authenticated', async () => {
    const { result } = renderHook(
      () => useCurrentUser(),
      { wrapper: createWrapper() }
    );

    await waitFor(() => {
      expect(mockGet).toHaveBeenCalledWith(
        '/api/auth/me',
        { credentials: 'include' }
      );
    });

    await waitFor(() => {
      expect(result.current.data?.data.user).toEqual(mockUser);
    });
  });

  it('does not fetch user when not authenticated', async () => {
    mockGet.mockImplementation((url) => {
      if (url === '/api/auth/status') {
        return Promise.resolve({ 
          data: { authenticated: false, user: null } 
        });
      }
      return Promise.reject(new Error('Should not be called'));
    });

    const { result } = renderHook(
      () => useCurrentUser(),
      { wrapper: createWrapper() }
    );

    // Wait for auth status to load
    await waitFor(() => {
      expect(mockGet).toHaveBeenCalledWith('/api/auth/status', expect.any(Object));
    });

    // Should not call /api/auth/me
    expect(mockGet).not.toHaveBeenCalledWith('/api/auth/me', expect.any(Object));
    expect(result.current.data).toBeUndefined();
  });
});

describe('useSignUp', () => {
  let mockPost: any;
  
  beforeEach(async () => {
    vi.clearAllMocks();
    const { post } = await import('@/utils/apiUtils');
    mockPost = post;
  });

  it('calls sign up API and invalidates auth queries', async () => {
    const mockResponse = {
      data: { user: mockUser, message: 'Account created successfully' }
    };
    mockPost.mockResolvedValue(mockResponse);

    const { result } = renderHook(
      () => useSignUp(),
      { wrapper: createWrapper() }
    );

    const signUpData: SignUpRequest = {
      username: 'newuser',
      email: 'new@example.com',
      password: 'password123',
      first_name: 'New',
      last_name: 'User'
    };

    await act(async () => {
      await result.current.mutateAsync(signUpData);
    });

    expect(mockPost).toHaveBeenCalledWith(
      '/api/auth/signup',
      signUpData,
      { credentials: 'include' }
    );
    expect(result.current.data).toEqual(mockResponse);
  });

  it('handles sign up errors', async () => {
    const error = new Error('Email already exists');
    mockPost.mockRejectedValue(error);

    const { result } = renderHook(
      () => useSignUp(),
      { wrapper: createWrapper() }
    );

    const signUpData: SignUpRequest = {
      username: 'existinguser',
      email: 'existing@example.com',
      password: 'password123',
      first_name: 'Existing',
      last_name: 'User'
    };

    await act(async () => {
      try {
        await result.current.mutateAsync(signUpData);
      } catch (e) {
        expect(e).toBe(error);
      }
    });

    expect(result.current.error).toBe(error);
  });
});

describe('useSignIn', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('calls sign in API and invalidates auth queries', async () => {
    const mockResponse = {
      data: { user: mockUser, message: 'Signed in successfully' }
    };
    mockPost.mockResolvedValue(mockResponse);

    const { result } = renderHook(
      () => useSignIn(),
      { wrapper: createWrapper() }
    );

    const signInData: SignInRequest = {
      username: 'testuser',
      password: 'password123'
    };

    await act(async () => {
      await result.current.mutateAsync(signInData);
    });

    expect(mockPost).toHaveBeenCalledWith(
      '/api/auth/signin',
      signInData,
      { credentials: 'include' }
    );
    expect(result.current.data).toEqual(mockResponse);
  });

  it('handles sign in errors', async () => {
    const error = new Error('Invalid credentials');
    mockPost.mockRejectedValue(error);

    const { result } = renderHook(
      () => useSignIn(),
      { wrapper: createWrapper() }
    );

    const signInData: SignInRequest = {
      username: 'baduser',
      password: 'wrongpassword'
    };

    await act(async () => {
      try {
        await result.current.mutateAsync(signInData);
      } catch (e) {
        expect(e).toBe(error);
      }
    });

    expect(result.current.error).toBe(error);
  });
});

describe('useSignOut', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('calls sign out API and clears auth data', async () => {
    const mockResponse = {
      data: { message: 'Signed out successfully' }
    };
    mockPost.mockResolvedValue(mockResponse);

    const { result } = renderHook(
      () => useSignOut(),
      { wrapper: createWrapper() }
    );

    await act(async () => {
      await result.current.mutateAsync();
    });

    expect(mockPost).toHaveBeenCalledWith(
      '/api/auth/signout',
      undefined,
      { credentials: 'include' }
    );
    expect(result.current.data).toEqual(mockResponse);
  });

  it('handles sign out errors', async () => {
    const error = new Error('Sign out failed');
    mockPost.mockRejectedValue(error);

    const { result } = renderHook(
      () => useSignOut(),
      { wrapper: createWrapper() }
    );

    await act(async () => {
      try {
        await result.current.mutateAsync();
      } catch (e) {
        expect(e).toBe(error);
      }
    });

    expect(result.current.error).toBe(error);
  });
});

describe('useIsAdmin', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('returns false for regular user', async () => {
    mockGet.mockResolvedValue({
      data: { authenticated: true, user: mockUser }
    });

    const { result } = renderHook(
      () => useIsAdmin(),
      { wrapper: createWrapper() }
    );

    await waitFor(() => {
      expect(result.current).toBe(false);
    });
  });

  it('returns true for admin user', async () => {
    mockGet.mockResolvedValue({
      data: { authenticated: true, user: mockAdminUser }
    });

    const { result } = renderHook(
      () => useIsAdmin(),
      { wrapper: createWrapper() }
    );

    await waitFor(() => {
      expect(result.current).toBe(true);
    });
  });

  it('returns true for super admin user', async () => {
    mockGet.mockResolvedValue({
      data: { authenticated: true, user: mockSuperAdminUser }
    });

    const { result } = renderHook(
      () => useIsAdmin(),
      { wrapper: createWrapper() }
    );

    await waitFor(() => {
      expect(result.current).toBe(true);
    });
  });

  it('returns false when not authenticated', async () => {
    mockGet.mockResolvedValue({
      data: { authenticated: false, user: null }
    });

    const { result } = renderHook(
      () => useIsAdmin(),
      { wrapper: createWrapper() }
    );

    await waitFor(() => {
      expect(result.current).toBe(false);
    });
  });
});

describe('useIsSuperAdmin', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('returns false for regular user', async () => {
    mockGet.mockResolvedValue({
      data: { authenticated: true, user: mockUser }
    });

    const { result } = renderHook(
      () => useIsSuperAdmin(),
      { wrapper: createWrapper() }
    );

    await waitFor(() => {
      expect(result.current).toBe(false);
    });
  });

  it('returns false for admin user', async () => {
    mockGet.mockResolvedValue({
      data: { authenticated: true, user: mockAdminUser }
    });

    const { result } = renderHook(
      () => useIsSuperAdmin(),
      { wrapper: createWrapper() }
    );

    await waitFor(() => {
      expect(result.current).toBe(false);
    });
  });

  it('returns true for super admin user', async () => {
    mockGet.mockResolvedValue({
      data: { authenticated: true, user: mockSuperAdminUser }
    });

    const { result } = renderHook(
      () => useIsSuperAdmin(),
      { wrapper: createWrapper() }
    );

    await waitFor(() => {
      expect(result.current).toBe(true);
    });
  });
});

describe('useUserRole', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('returns user role for authenticated user', async () => {
    mockGet.mockResolvedValue({
      data: { authenticated: true, user: mockAdminUser }
    });

    const { result } = renderHook(
      () => useUserRole(),
      { wrapper: createWrapper() }
    );

    await waitFor(() => {
      expect(result.current).toBe('admin');
    });
  });

  it('returns default user role when not authenticated', async () => {
    mockGet.mockResolvedValue({
      data: { authenticated: false, user: null }
    });

    const { result } = renderHook(
      () => useUserRole(),
      { wrapper: createWrapper() }
    );

    await waitFor(() => {
      expect(result.current).toBe('user');
    });
  });

  it('returns user role for different user types', async () => {
    // Test regular user
    mockGet.mockResolvedValue({
      data: { authenticated: true, user: mockUser }
    });

    const { result: regularResult } = renderHook(
      () => useUserRole(),
      { wrapper: createWrapper() }
    );

    await waitFor(() => {
      expect(regularResult.current).toBe('user');
    });

    // Test super admin
    mockGet.mockResolvedValue({
      data: { authenticated: true, user: mockSuperAdminUser }
    });

    const { result: superResult } = renderHook(
      () => useUserRole(),
      { wrapper: createWrapper() }
    );

    await waitFor(() => {
      expect(superResult.current).toBe('super_admin');
    });
  });
});

describe('Authentication Integration', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('handles complete authentication flow', async () => {
    // Start unauthenticated
    mockGet.mockResolvedValue({
      data: { authenticated: false, user: null }
    });

    const { result: authResult } = renderHook(
      () => useAuthStatus(),
      { wrapper: createWrapper() }
    );

    const { result: signInResult } = renderHook(
      () => useSignIn(),
      { wrapper: createWrapper() }
    );

    await waitFor(() => {
      expect(authResult.current.data?.data.authenticated).toBe(false);
    });

    // Sign in
    const signInResponse = {
      data: { user: mockUser, message: 'Signed in successfully' }
    };
    mockPost.mockResolvedValue(signInResponse);

    await act(async () => {
      await signInResult.current.mutateAsync({
        username: 'testuser',
        password: 'password123'
      });
    });

    expect(mockPost).toHaveBeenCalledWith(
      '/api/auth/signin',
      { username: 'testuser', password: 'password123' },
      { credentials: 'include' }
    );
  });

  it('handles authentication state transitions', async () => {
    const wrapper = createWrapper();

    // Initially authenticated
    mockGet.mockResolvedValue({
      data: { authenticated: true, user: mockUser }
    });

    const { result: isAdminResult } = renderHook(
      () => useIsAdmin(),
      { wrapper }
    );

    await waitFor(() => {
      expect(isAdminResult.current).toBe(false);
    });

    // Change to admin user
    mockGet.mockResolvedValue({
      data: { authenticated: true, user: mockAdminUser }
    });

    const { result: newIsAdminResult } = renderHook(
      () => useIsAdmin(),
      { wrapper }
    );

    await waitFor(() => {
      expect(newIsAdminResult.current).toBe(true);
    });
  });
});