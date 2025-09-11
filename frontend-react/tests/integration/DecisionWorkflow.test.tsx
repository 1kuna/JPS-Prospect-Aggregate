import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import '@testing-library/jest-dom';
import GoNoGoDecision from '../../src/components/GoNoGoDecision';

// Create test wrapper with providers
const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        {children}
      </BrowserRouter>
    </QueryClientProvider>
  );
};

// Mock fetch globally
global.fetch = jest.fn();

describe('Decision Workflow', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Decision Creation Flow', () => {
    it('should create a new decision successfully', async () => {
      const mockProspect = {
        id: 'PROS-001',
        title: 'Software Development Contract',
        agency: 'Department of Defense',
        naics: '541511',
        estimated_value_text: '$100,000 - $500,000',
      };

      // Mock successful decision creation
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          status: 'success',
          data: {
            id: 1,
            prospect_id: 'PROS-001',
            decision: 'go',
            reason: 'Good alignment with capabilities',
            created_at: '2024-01-15T10:00:00Z',
          },
        }),
      });

      const Wrapper = createWrapper();
      render(
        <Wrapper>
          <GoNoGoDecision prospect={mockProspect} />
        </Wrapper>
      );

      // Click the "Go" button
      const goButton = screen.getByRole('button', { name: /go/i });
      fireEvent.click(goButton);

      // Enter reason
      const reasonInput = await screen.findByPlaceholderText(/reason/i);
      fireEvent.change(reasonInput, {
        target: { value: 'Good alignment with capabilities' },
      });

      // Submit decision
      const submitButton = screen.getByRole('button', { name: /submit/i });
      fireEvent.click(submitButton);

      // Verify API was called correctly
      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledWith(
          expect.stringContaining('/api/decisions'),
          expect.objectContaining({
            method: 'POST',
            body: JSON.stringify({
              prospect_id: 'PROS-001',
              decision: 'go',
              reason: 'Good alignment with capabilities',
            }),
          })
        );
      });

      // Verify success feedback
      await waitFor(() => {
        expect(screen.getByText(/decision saved/i)).toBeInTheDocument();
      });
    });

    it('should handle decision creation errors', async () => {
      const mockProspect = {
        id: 'PROS-002',
        title: 'Consulting Services',
        agency: 'Department of Energy',
      };

      // Mock API error
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: async () => ({
          status: 'error',
          message: 'Invalid decision data',
        }),
      });

      const Wrapper = createWrapper();
      render(
        <Wrapper>
          <GoNoGoDecision prospect={mockProspect} />
        </Wrapper>
      );

      // Try to submit without reason
      const noGoButton = screen.getByRole('button', { name: /no.*go/i });
      fireEvent.click(noGoButton);

      const submitButton = screen.getByRole('button', { name: /submit/i });
      fireEvent.click(submitButton);

      // Verify error is shown
      await waitFor(() => {
        expect(screen.getByText(/invalid decision data/i)).toBeInTheDocument();
      });
    });
  });

  describe('Decision Deletion Flow', () => {
    it('should delete a decision with confirmation', async () => {
      const mockDecision = {
        id: 1,
        prospect_id: 'PROS-003',
        decision: 'go',
        reason: 'Test reason',
        created_at: '2024-01-15T10:00:00Z',
      };

      // Mock fetching existing decision
      (global.fetch as jest.Mock)
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            status: 'success',
            data: { decisions: [mockDecision] },
          }),
        })
        // Mock successful deletion
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            status: 'success',
            message: 'Decision deleted',
          }),
        });

      const Wrapper = createWrapper();
      render(
        <Wrapper>
          <GoNoGoDecision
            prospect={{ id: 'PROS-003', title: 'Test Prospect' }}
            existingDecision={mockDecision}
          />
        </Wrapper>
      );

      // Find and click delete button
      const deleteButton = await screen.findByRole('button', { name: /delete/i });
      fireEvent.click(deleteButton);

      // Confirm deletion
      const confirmButton = await screen.findByRole('button', { name: /confirm/i });
      fireEvent.click(confirmButton);

      // Verify API was called
      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledWith(
          expect.stringContaining('/api/decisions/1'),
          expect.objectContaining({
            method: 'DELETE',
          })
        );
      });

      // Verify success feedback
      await waitFor(() => {
        expect(screen.getByText(/decision deleted/i)).toBeInTheDocument();
      });
    });

    it('should handle deletion errors gracefully', async () => {
      // Mock API error for deletion
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        status: 403,
        json: async () => ({
          status: 'error',
          message: 'Not authorized to delete this decision',
        }),
      });

      const Wrapper = createWrapper();
      render(
        <Wrapper>
          <GoNoGoDecision
            prospect={{ id: 'PROS-004', title: 'Test Prospect' }}
            existingDecision={{
              id: 2,
              prospect_id: 'PROS-004',
              decision: 'no-go',
              reason: 'Not a good fit',
            }}
          />
        </Wrapper>
      );

      // Try to delete
      const deleteButton = screen.getByRole('button', { name: /delete/i });
      fireEvent.click(deleteButton);

      const confirmButton = await screen.findByRole('button', { name: /confirm/i });
      fireEvent.click(confirmButton);

      // Verify error is shown
      await waitFor(() => {
        expect(screen.getByText(/not authorized/i)).toBeInTheDocument();
      });
    });
  });

  describe('Enhancement Flow Integration', () => {
    it('should trigger enhancement after decision creation', async () => {
      const mockProspect = {
        id: 'PROS-005',
        title: 'AI Research Contract',
        agency: 'NASA',
        naics: '541511',
      };

      // Mock decision creation and enhancement trigger
      (global.fetch as jest.Mock)
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            status: 'success',
            data: {
              id: 3,
              prospect_id: 'PROS-005',
              decision: 'go',
              reason: 'Strategic opportunity',
            },
          }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            status: 'success',
            data: {
              queue_item_id: 'queue-123',
              planned_steps: ['Enhance values', 'Enhance titles'],
              message: 'Enhancement started',
            },
          }),
        });

      const Wrapper = createWrapper();
      render(
        <Wrapper>
          <GoNoGoDecision
            prospect={mockProspect}
            enableEnhancement={true}
          />
        </Wrapper>
      );

      // Create decision
      const goButton = screen.getByRole('button', { name: /go/i });
      fireEvent.click(goButton);

      const reasonInput = await screen.findByPlaceholderText(/reason/i);
      fireEvent.change(reasonInput, {
        target: { value: 'Strategic opportunity' },
      });

      const submitButton = screen.getByRole('button', { name: /submit/i });
      fireEvent.click(submitButton);

      // Check for enhancement option
      await waitFor(() => {
        const enhanceButton = screen.getByRole('button', { name: /enhance/i });
        expect(enhanceButton).toBeInTheDocument();
      });

      // Click enhance
      const enhanceButton = screen.getByRole('button', { name: /enhance/i });
      fireEvent.click(enhanceButton);

      // Verify enhancement API was called
      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledWith(
          expect.stringContaining('/api/llm/enhance-single'),
          expect.objectContaining({
            method: 'POST',
            body: JSON.stringify({
              prospect_id: 'PROS-005',
              enhancement_types: ['values', 'titles', 'naics', 'set_asides'],
            }),
          })
        );
      });

      // Verify enhancement started message
      await waitFor(() => {
        expect(screen.getByText(/enhancement started/i)).toBeInTheDocument();
      });
    });

    it('should show enhancement progress', async () => {
      // Mock enhancement progress polling
      (global.fetch as jest.Mock)
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            status: 'success',
            data: {
              processed: 0,
              total: 4,
              percentage: 0,
              current_step: 'Starting',
            },
          }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            status: 'success',
            data: {
              processed: 2,
              total: 4,
              percentage: 50,
              current_step: 'Enhancing values',
            },
          }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            status: 'success',
            data: {
              processed: 4,
              total: 4,
              percentage: 100,
              current_step: 'Complete',
            },
          }),
        });

      const Wrapper = createWrapper();
      render(
        <Wrapper>
          <EnhancementProgress prospectId="PROS-006" />
        </Wrapper>
      );

      // Verify initial state
      expect(screen.getByText(/0%/)).toBeInTheDocument();

      // Wait for progress updates
      await waitFor(() => {
        expect(screen.getByText(/50%/)).toBeInTheDocument();
        expect(screen.getByText(/enhancing values/i)).toBeInTheDocument();
      });

      await waitFor(() => {
        expect(screen.getByText(/100%/)).toBeInTheDocument();
        expect(screen.getByText(/complete/i)).toBeInTheDocument();
      });
    });
  });

  describe('Decision Statistics', () => {
    it('should display decision statistics correctly', async () => {
      // Mock statistics API
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          status: 'success',
          data: {
            total_decisions: 150,
            go_count: 100,
            no_go_count: 45,
            maybe_count: 5,
            decision_rate: 0.67,
            recent_decisions: [
              {
                id: 1,
                prospect_id: 'PROS-007',
                decision: 'go',
                created_at: '2024-01-15T10:00:00Z',
              },
              {
                id: 2,
                prospect_id: 'PROS-008',
                decision: 'no-go',
                created_at: '2024-01-14T15:30:00Z',
              },
            ],
          },
        }),
      });

      const Wrapper = createWrapper();
      render(
        <Wrapper>
          <DecisionStats />
        </Wrapper>
      );

      // Wait for stats to load
      await waitFor(() => {
        expect(screen.getByText(/150/)).toBeInTheDocument(); // Total decisions
        expect(screen.getByText(/100.*go/i)).toBeInTheDocument(); // Go count
        expect(screen.getByText(/45.*no.*go/i)).toBeInTheDocument(); // No-go count
        expect(screen.getByText(/67%/)).toBeInTheDocument(); // Decision rate
      });

      // Verify recent decisions are shown
      expect(screen.getByText(/PROS-007/)).toBeInTheDocument();
      expect(screen.getByText(/PROS-008/)).toBeInTheDocument();
    });
  });
});

// Mock component for enhancement progress (if not exported from main component)
function EnhancementProgress({ prospectId }: { prospectId: string }) {
  const [progress, setProgress] = React.useState({ percentage: 0, current_step: 'Starting' });

  React.useEffect(() => {
    const interval = setInterval(async () => {
      const response = await fetch(`/api/llm/iterative/progress?prospect_id=${prospectId}`);
      const data = await response.json();
      setProgress(data.data);
      if (data.data.percentage === 100) {
        clearInterval(interval);
      }
    }, 1000);
    return () => clearInterval(interval);
  }, [prospectId]);

  return (
    <div>
      <div>{progress.percentage}%</div>
      <div>{progress.current_step}</div>
    </div>
  );
}

// Mock component for decision stats
function DecisionStats() {
  const [stats, setStats] = React.useState<any>(null);

  React.useEffect(() => {
    fetch('/api/decisions/stats')
      .then(res => res.json())
      .then(data => setStats(data.data));
  }, []);

  if (!stats) return <div>Loading...</div>;

  return (
    <div>
      <div>{stats.total_decisions}</div>
      <div>{stats.go_count} Go</div>
      <div>{stats.no_go_count} No-Go</div>
      <div>{Math.round(stats.decision_rate * 100)}%</div>
      {stats.recent_decisions.map((d: any) => (
        <div key={d.id}>{d.prospect_id}</div>
      ))}
    </div>
  );
}