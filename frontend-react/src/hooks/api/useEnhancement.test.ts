import { renderHook, act, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';
import { useEnhancement } from './useEnhancement';

// Define types locally since they're not exported from the main hook
interface EnhancementRequest {
  prospect_id: string;
  force_redo?: boolean;
  user_id?: number;
  enhancement_types?: string[];
}

interface QueueStatus {
  worker_running: boolean;
  current_item?: string;
  queue_size: number;
  pending_items: Array<{
    id: string;
    type: 'individual' | 'bulk';
    priority: number;
    prospect_id?: number;
    prospect_count: number;
    enhancement_type: string;
    created_at: string;
    status: string;
  }>;
  recent_completed: Array<{
    id: string;
    type: 'individual' | 'bulk';
    prospect_id?: number;
    status: string;
    completed_at?: string;
    error_message?: string;
  }>;
}

interface EnhancementProgressEvent {
  event_type: 'connected' | 'queue_position_update' | 'processing_started' | 
              'titles_started' | 'titles_completed' | 'titles_failed' |
              'values_started' | 'values_completed' | 'values_failed' |
              'naics_started' | 'naics_completed' | 'naics_failed' |
              'set_asides_started' | 'set_asides_completed' | 'set_asides_failed' |
              'completed' | 'failed' | 'error' | 'timeout' | 'keepalive';
  timestamp: string;
  prospect_id?: string;
  data?: Record<string, unknown>;
}

// Mock the API utils
vi.mock('@/utils/apiUtils', () => ({
  get: vi.fn(),
  post: vi.fn(),
  del: vi.fn(),
  ApiError: class ApiError extends Error {
    status: number;
    constructor(message: string, status: number) {
      super(message);
      this.status = status;
    }
  }
}));

// Mock EventSource
class MockEventSource {
  url: string;
  onopen: ((event: Event) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
  readyState: number = 1;

  constructor(url: string) {
    this.url = url;
    // Simulate connection after a brief delay
    setTimeout(() => {
      this.onopen?.(new Event('open'));
    }, 10);
  }

  close() {
    this.readyState = 2;
  }

  // Helper method to simulate incoming messages
  simulateMessage(data: any) {
    if (this.onmessage) {
      const event = new MessageEvent('message', {
        data: JSON.stringify(data)
      });
      this.onmessage(event);
    }
  }

  // Helper method to simulate errors
  simulateError() {
    if (this.onerror) {
      this.onerror(new Event('error'));
    }
  }
}

// Store references to created EventSource instances
const mockEventSources: MockEventSource[] = [];

global.EventSource = vi.fn().mockImplementation((url: string) => {
  const mockSource = new MockEventSource(url);
  mockEventSources.push(mockSource);
  return mockSource;
}) as any;

// Mock window.showToast
const mockShowToast = vi.fn();
global.window = {
  ...global.window,
  showToast: mockShowToast
};

// Mock setTimeout/clearTimeout for enhancement timeouts
vi.mock('timers', () => ({
  setTimeout: vi.fn((fn, delay) => {
    const id = Math.random();
    // Optionally execute the function immediately for testing
    return id;
  }),
  clearTimeout: vi.fn()
}));

// Test data
const mockQueueStatus: QueueStatus = {
  worker_running: true,
  current_item: 'item-123',
  queue_size: 3,
  pending_items: [
    {
      id: 'item-1',
      type: 'individual',
      priority: 1,
      prospect_id: 1,
      prospect_count: 1,
      enhancement_type: 'all',
      created_at: '2024-01-15T10:00:00Z',
      status: 'pending'
    },
    {
      id: 'item-2',
      type: 'individual',
      priority: 2,
      prospect_id: 2,
      prospect_count: 1,
      enhancement_type: 'values',
      created_at: '2024-01-15T10:01:00Z',
      status: 'pending'
    }
  ],
  recent_completed: [
    {
      id: 'completed-1',
      type: 'individual',
      prospect_id: 123,
      status: 'completed',
      completed_at: '2024-01-15T09:55:00Z'
    }
  ]
};

const mockEnhancementRequest: EnhancementRequest = {
  prospect_id: 'prospect-123',
  force_redo: false,
  user_id: 1,
  enhancement_types: ['values', 'titles']
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

describe('useEnhancement', () => {
  let mockGet: any;
  let mockPost: any;
  let mockDel: any;

  beforeEach(async () => {
    vi.clearAllMocks();
    mockEventSources.length = 0;
    vi.useFakeTimers();
    
    // Get mocked functions
    const { get, post, del } = await import('@/utils/apiUtils');
    mockGet = get;
    mockPost = post;
    mockDel = del;
    
    // Default mock responses
    mockGet.mockResolvedValue(mockQueueStatus);
    mockPost.mockResolvedValue({
      queue_item_id: 'new-item-123',
      position: 1,
      worker_running: true,
      message: 'Enhancement queued successfully'
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
    vi.useRealTimers();
    mockEventSources.forEach(source => source.close());
    mockEventSources.length = 0;
  });

  describe('Initialization', () => {
    it('initializes with correct default state', () => {
      const { result } = renderHook(() => useEnhancement(), {
        wrapper: createWrapper()
      });

      expect(result.current.enhancementStates).toEqual({});
      expect(result.current.queueLength).toBe(0);
      expect(result.current.isProcessing).toBe(false);
      expect(typeof result.current.queueEnhancement).toBe('function');
      expect(typeof result.current.getEnhancementState).toBe('function');
      expect(typeof result.current.cancelEnhancement).toBe('function');
    });

    it('fetches queue status on mount', async () => {
      renderHook(() => useEnhancement(), {
        wrapper: createWrapper()
      });

      // Fast-forward timers to trigger the initial fetch
      act(() => {
        vi.advanceTimersByTime(100);
      });

      await waitFor(() => {
        expect(mockGet).toHaveBeenCalledWith('/api/llm/queue/status');
      });
    });

    it('polls queue status at regular intervals', async () => {
      renderHook(() => useEnhancement(), {
        wrapper: createWrapper()
      });

      // Fast-forward initial fetch
      act(() => {
        vi.advanceTimersByTime(100);
      });

      await waitFor(() => {
        expect(mockGet).toHaveBeenCalledTimes(1);
      });

      // Fast-forward polling interval (1000ms)
      act(() => {
        vi.advanceTimersByTime(1000);
      });

      await waitFor(() => {
        expect(mockGet).toHaveBeenCalledTimes(2);
      });
    });
  });

  describe('Queue Enhancement', () => {
    it('queues enhancement successfully', async () => {
      const { result } = renderHook(() => useEnhancement(), {
        wrapper: createWrapper()
      });

      let queueItemId: string;
      await act(async () => {
        queueItemId = await result.current.queueEnhancement(mockEnhancementRequest);
      });

      expect(mockPost).toHaveBeenCalledWith('/api/llm/enhance-single', {
        prospect_id: 'prospect-123',
        enhancement_type: 'values,titles',
        force_redo: false,
        user_id: 1
      });

      expect(queueItemId!).toBe('new-item-123');
      expect(result.current.enhancementStates['prospect-123']).toEqual({
        queueItemId: 'new-item-123',
        status: 'queued',
        queuePosition: 1,
        progress: {}
      });
    });

    it('creates SSE connection when queuing enhancement', async () => {
      const { result } = renderHook(() => useEnhancement(), {
        wrapper: createWrapper()
      });

      await act(async () => {
        await result.current.queueEnhancement(mockEnhancementRequest);
      });

      expect(global.EventSource).toHaveBeenCalledWith('/api/llm/enhancement-progress/prospect-123');
      expect(mockEventSources).toHaveLength(1);
    });

    it('prevents duplicate queuing', async () => {
      const { result } = renderHook(() => useEnhancement(), {
        wrapper: createWrapper()
      });

      // Queue first enhancement
      await act(async () => {
        await result.current.queueEnhancement(mockEnhancementRequest);
      });

      // Try to queue again
      await act(async () => {
        const secondResult = await result.current.queueEnhancement(mockEnhancementRequest);
        expect(secondResult).toBe('new-item-123'); // Returns existing queue item ID
      });

      expect(mockPost).toHaveBeenCalledTimes(1);
      expect(mockShowToast).toHaveBeenCalledWith({
        title: 'Already Queued',
        message: 'Prospect is already being enhanced',
        type: 'info',
        duration: 2000
      });
    });

    it('handles queue enhancement errors', async () => {
      const error = new Error('Queue full');
      mockPost.mockRejectedValue(error);

      const { result } = renderHook(() => useEnhancement(), {
        wrapper: createWrapper()
      });

      await act(async () => {
        try {
          await result.current.queueEnhancement(mockEnhancementRequest);
        } catch (e) {
          expect(e).toBe(error);
        }
      });

      expect(result.current.enhancementStates['prospect-123']?.status).toBe('failed');
      expect(mockShowToast).toHaveBeenCalledWith({
        title: 'Enhancement Failed',
        message: 'Failed to queue enhancement: Queue full',
        type: 'error',
        duration: 5000
      });
    });
  });

  describe('SSE Event Handling', () => {
    it('handles queue position updates', async () => {
      const { result } = renderHook(() => useEnhancement(), {
        wrapper: createWrapper()
      });

      await act(async () => {
        await result.current.queueEnhancement(mockEnhancementRequest);
      });

      const eventSource = mockEventSources[0];
      const positionUpdateEvent: EnhancementProgressEvent = {
        event_type: 'queue_position_update',
        timestamp: '2024-01-15T10:00:00Z',
        prospect_id: 'prospect-123',
        data: { position: 2, estimated_time: 30 }
      };

      act(() => {
        eventSource.simulateMessage(positionUpdateEvent);
      });

      expect(result.current.enhancementStates['prospect-123']).toEqual(
        expect.objectContaining({
          status: 'queued',
          queuePosition: 2,
          estimatedTimeRemaining: 30
        })
      );
    });

    it('handles processing started event', async () => {
      const { result } = renderHook(() => useEnhancement(), {
        wrapper: createWrapper()
      });

      await act(async () => {
        await result.current.queueEnhancement(mockEnhancementRequest);
      });

      const eventSource = mockEventSources[0];
      const processingEvent: EnhancementProgressEvent = {
        event_type: 'processing_started',
        timestamp: '2024-01-15T10:00:00Z',
        prospect_id: 'prospect-123'
      };

      act(() => {
        eventSource.simulateMessage(processingEvent);
      });

      expect(result.current.enhancementStates['prospect-123']).toEqual(
        expect.objectContaining({
          status: 'processing',
          startedAt: '2024-01-15T10:00:00Z',
          queuePosition: undefined
        })
      );
    });

    it('handles step progress events', async () => {
      const { result } = renderHook(() => useEnhancement(), {
        wrapper: createWrapper()
      });

      await act(async () => {
        await result.current.queueEnhancement(mockEnhancementRequest);
      });

      const eventSource = mockEventSources[0];

      // Values started
      act(() => {
        eventSource.simulateMessage({
          event_type: 'values_started',
          timestamp: '2024-01-15T10:00:00Z',
          prospect_id: 'prospect-123'
        });
      });

      expect(result.current.enhancementStates['prospect-123']?.currentStep).toBe('Parsing contract values...');

      // Values completed
      act(() => {
        eventSource.simulateMessage({
          event_type: 'values_completed',
          timestamp: '2024-01-15T10:00:01Z',
          prospect_id: 'prospect-123',
          data: { 
            skipped: false, 
            parsed_contract_value: 50000,
            estimated_value_text: '$50,000'
          }
        });
      });

      expect(result.current.enhancementStates['prospect-123']?.progress.values).toEqual({
        completed: true,
        skipped: false,
        data: {
          skipped: false,
          parsed_contract_value: 50000,
          estimated_value_text: '$50,000'
        }
      });
    });

    it('handles enhancement completion', async () => {
      const { result } = renderHook(() => useEnhancement(), {
        wrapper: createWrapper()
      });

      await act(async () => {
        await result.current.queueEnhancement(mockEnhancementRequest);
      });

      const eventSource = mockEventSources[0];
      const completionEvent: EnhancementProgressEvent = {
        event_type: 'completed',
        timestamp: '2024-01-15T10:05:00Z',
        prospect_id: 'prospect-123',
        data: { ollama_processed_at: '2024-01-15T10:05:00Z' }
      };

      act(() => {
        eventSource.simulateMessage(completionEvent);
      });

      expect(result.current.enhancementStates['prospect-123']).toEqual(
        expect.objectContaining({
          status: 'completed',
          completedAt: '2024-01-15T10:05:00Z',
          currentStep: undefined
        })
      );

      expect(mockShowToast).toHaveBeenCalledWith({
        title: 'AI Enhancement Complete',
        message: 'Successfully enhanced prospect',
        type: 'success',
        duration: 3000
      });
    });

    it('handles enhancement failures', async () => {
      const { result } = renderHook(() => useEnhancement(), {
        wrapper: createWrapper()
      });

      await act(async () => {
        await result.current.queueEnhancement(mockEnhancementRequest);
      });

      const eventSource = mockEventSources[0];
      const failureEvent: EnhancementProgressEvent = {
        event_type: 'failed',
        timestamp: '2024-01-15T10:05:00Z',
        prospect_id: 'prospect-123',
        data: { error: 'LLM service unavailable' }
      };

      act(() => {
        eventSource.simulateMessage(failureEvent);
      });

      expect(result.current.enhancementStates['prospect-123']).toEqual(
        expect.objectContaining({
          status: 'failed',
          error: 'LLM service unavailable',
          currentStep: undefined
        })
      );

      expect(mockShowToast).toHaveBeenCalledWith({
        title: 'Enhancement Failed',
        message: 'LLM service unavailable',
        type: 'error',
        duration: 5000
      });
    });

    it('handles SSE connection errors', async () => {
      const { result } = renderHook(() => useEnhancement(), {
        wrapper: createWrapper()
      });

      await act(async () => {
        await result.current.queueEnhancement(mockEnhancementRequest);
      });

      const eventSource = mockEventSources[0];
      
      // Set state to processing first
      act(() => {
        eventSource.simulateMessage({
          event_type: 'processing_started',
          timestamp: '2024-01-15T10:00:00Z',
          prospect_id: 'prospect-123'
        });
      });

      // Simulate connection error
      act(() => {
        eventSource.simulateError();
      });

      expect(mockShowToast).toHaveBeenCalledWith({
        title: 'Connection Lost',
        message: 'Enhancement connection lost. Please refresh to see latest status.',
        type: 'error',
        duration: 5000
      });
    });
  });

  describe('Enhancement State Management', () => {
    it('gets enhancement state for prospect', async () => {
      const { result } = renderHook(() => useEnhancement(), {
        wrapper: createWrapper()
      });

      await act(async () => {
        await result.current.queueEnhancement(mockEnhancementRequest);
      });

      const state = result.current.getEnhancementState('prospect-123');
      expect(state).toEqual({
        queueItemId: 'new-item-123',
        status: 'queued',
        queuePosition: 1,
        progress: {}
      });

      const nonExistentState = result.current.getEnhancementState('non-existent');
      expect(nonExistentState).toBeNull();
    });

    it('cancels enhancement successfully', async () => {
      mockDel.mockResolvedValue({ success: true });

      const { result } = renderHook(() => useEnhancement(), {
        wrapper: createWrapper()
      });

      await act(async () => {
        await result.current.queueEnhancement(mockEnhancementRequest);
      });

      let cancelled: boolean;
      await act(async () => {
        cancelled = await result.current.cancelEnhancement('prospect-123');
      });

      expect(cancelled!).toBe(true);
      expect(mockDel).toHaveBeenCalledWith('/api/llm/enhancement-queue/new-item-123');
      expect(result.current.enhancementStates['prospect-123']).toBeUndefined();
    });

    it('handles cancellation failures', async () => {
      mockDel.mockRejectedValue(new Error('Cancellation failed'));

      const { result } = renderHook(() => useEnhancement(), {
        wrapper: createWrapper()
      });

      await act(async () => {
        await result.current.queueEnhancement(mockEnhancementRequest);
      });

      let cancelled: boolean;
      await act(async () => {
        cancelled = await result.current.cancelEnhancement('prospect-123');
      });

      expect(cancelled!).toBe(false);
    });

    it('does not cancel non-queued enhancements', async () => {
      const { result } = renderHook(() => useEnhancement(), {
        wrapper: createWrapper()
      });

      let cancelled: boolean;
      await act(async () => {
        cancelled = await result.current.cancelEnhancement('non-existent');
      });

      expect(cancelled!).toBe(false);
      expect(mockDel).not.toHaveBeenCalled();
    });
  });

  describe('Queue Status Integration', () => {
    it('syncs with backend queue status', async () => {
      const { result } = renderHook(() => useEnhancement(), {
        wrapper: createWrapper()
      });

      // Simulate queue status with items
      const queueStatusWithItems: QueueStatus = {
        ...mockQueueStatus,
        current_item: 'item-prospect-123',
        pending_items: [
          {
            id: 'item-prospect-123',
            type: 'individual',
            priority: 1,
            prospect_id: 123,
            prospect_count: 1,
            enhancement_type: 'all',
            created_at: '2024-01-15T10:00:00Z',
            status: 'processing'
          }
        ]
      };

      mockGet.mockResolvedValue(queueStatusWithItems);

      // Trigger queue status fetch
      act(() => {
        vi.advanceTimersByTime(100);
      });

      await waitFor(() => {
        expect(result.current.queueStatus).toEqual(queueStatusWithItems);
      });

      // Should update enhancement states based on queue status  
      expect(result.current.enhancementStates['123']).toEqual(
        expect.objectContaining({
          queueItemId: 'item-prospect-123',
          status: 'processing',
          queuePosition: undefined
        })
      );
    });

    it('calculates queue metrics correctly', async () => {
      const { result } = renderHook(() => useEnhancement(), {
        wrapper: createWrapper()
      });

      // Add multiple prospects to queue
      await act(async () => {
        await result.current.queueEnhancement({ prospect_id: 'prospect-1' });
        await result.current.queueEnhancement({ prospect_id: 'prospect-2' });
      });

      // Set one to processing
      act(() => {
        const eventSource = mockEventSources[0];
        eventSource.simulateMessage({
          event_type: 'processing_started',
          timestamp: '2024-01-15T10:00:00Z',
          prospect_id: 'prospect-1'
        });
      });

      expect(result.current.queueLength).toBe(1); // Only queued items
      expect(result.current.isProcessing).toBe(true);
    });
  });

  describe('Worker Controls', () => {
    it('starts queue worker successfully', async () => {
      mockPost.mockResolvedValue({ success: true });

      const { result } = renderHook(() => useEnhancement(), {
        wrapper: createWrapper()
      });

      let started: boolean;
      await act(async () => {
        started = await result.current.startQueueWorker();
      });

      expect(started!).toBe(true);
      expect(mockPost).toHaveBeenCalledWith('/api/llm/queue/start-worker');
    });

    it('stops queue worker successfully', async () => {
      mockPost.mockResolvedValue({ success: true });

      const { result } = renderHook(() => useEnhancement(), {
        wrapper: createWrapper()
      });

      let stopped: boolean;
      await act(async () => {
        stopped = await result.current.stopQueueWorker();
      });

      expect(stopped!).toBe(true);
      expect(mockPost).toHaveBeenCalledWith('/api/llm/queue/stop-worker');
    });

    it('handles worker control errors', async () => {
      const error = { status: 500, message: 'Worker control failed' };
      mockPost.mockRejectedValue(error);

      const { result } = renderHook(() => useEnhancement(), {
        wrapper: createWrapper()
      });

      let started: boolean;
      await act(async () => {
        started = await result.current.startQueueWorker();
      });

      expect(started!).toBe(false);
      expect(mockShowToast).toHaveBeenCalledWith({
        title: 'Failed to start worker',
        message: 'Worker control failed',
        type: 'error',
        duration: 3000
      });
    });
  });

  describe('Cleanup', () => {
    it('cleans up SSE connections on unmount', () => {
      const { unmount } = renderHook(() => useEnhancement(), {
        wrapper: createWrapper()
      });

      // Create some connections
      act(async () => {
        const { result } = renderHook(() => useEnhancement(), {
          wrapper: createWrapper()
        });
        await result.current.queueEnhancement({ prospect_id: 'prospect-1' });
        await result.current.queueEnhancement({ prospect_id: 'prospect-2' });
      });

      expect(mockEventSources.length).toBeGreaterThan(0);

      unmount();

      // All connections should be closed
      mockEventSources.forEach(source => {
        expect(source.readyState).toBe(2); // CLOSED
      });
    });

    it('cleans up completed enhancements after delay', async () => {
      const { result } = renderHook(() => useEnhancement(), {
        wrapper: createWrapper()
      });

      await act(async () => {
        await result.current.queueEnhancement(mockEnhancementRequest);
      });

      const eventSource = mockEventSources[0];
      
      // Complete the enhancement
      act(() => {
        eventSource.simulateMessage({
          event_type: 'completed',
          timestamp: '2024-01-15T10:05:00Z',
          prospect_id: 'prospect-123',
          data: { ollama_processed_at: '2024-01-15T10:05:00Z' }
        });
      });

      expect(result.current.enhancementStates['prospect-123']?.status).toBe('completed');

      // Fast-forward cleanup delay (5 seconds)
      act(() => {
        vi.advanceTimersByTime(5000);
      });

      // Enhancement should be removed from state
      expect(result.current.enhancementStates['prospect-123']).toBeUndefined();
    });
  });

  describe('Polling Behavior', () => {
    it('reduces polling interval when SSE is active', async () => {
      const { result } = renderHook(() => useEnhancement(), {
        wrapper: createWrapper()
      });

      // Initial polling interval should be 1000ms
      act(() => {
        vi.advanceTimersByTime(1000);
      });

      await waitFor(() => {
        expect(mockGet).toHaveBeenCalledTimes(2); // Initial + first poll
      });

      // Queue enhancement (creates SSE connection)
      await act(async () => {
        await result.current.queueEnhancement(mockEnhancementRequest);
      });

      // Should now poll at 5000ms interval
      act(() => {
        vi.advanceTimersByTime(5000);
      });

      await waitFor(() => {
        expect(mockGet).toHaveBeenCalledTimes(3);
      });
    });
  });
});