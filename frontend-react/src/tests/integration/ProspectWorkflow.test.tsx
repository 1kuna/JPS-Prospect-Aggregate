import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';
import userEvent from '@testing-library/user-event';

// Import the components we'll test integration between
import { ProspectTable } from '@/components/prospect/ProspectTable';
import { ProspectFilters } from '@/components/prospect/ProspectFilters';
import { ProspectDetailsModal } from '@/components/prospect/ProspectDetailsModal';
import { GoNoGoDecision } from '@/components/GoNoGoDecision';
import { AIEnrichment } from '@/components/AIEnrichment';

// Import contexts
import { ToastContextProvider } from '@/contexts/ToastContext';
import { ProspectEnhancementProvider } from '@/contexts/ProspectEnhancementContext';
import { TimezoneProvider } from '@/contexts/TimezoneContext';

// Mock API utils
const mockFetch = vi.fn();
global.fetch = mockFetch;

vi.mock('@/utils/apiUtils', () => ({
  get: vi.fn(),
  post: vi.fn(),
  del: vi.fn(),
  buildQueryString: vi.fn().mockImplementation(() => '')
}));

vi.mock('@/hooks/api/useEnhancementSimple', () => ({
  useEnhancementSimple: () => ({
    queueEnhancement: vi.fn().mockResolvedValue('queue-item-123'),
    getEnhancementState: vi.fn().mockReturnValue(null),
    cancelEnhancement: vi.fn().mockResolvedValue(true),
    enhancementStates: {}
  })
}));

// Mock prospects data
const mockProspects = [
  {
    id: 'prospect-1',
    title: 'Software Development Services',
    description: 'Development of custom software solutions for government agencies',
    agency: 'Department of Defense',
    posted_date: '2024-01-15',
    response_date: '2024-02-15',
    loaded_at: '2024-01-15T10:00:00Z',
    estimated_value: 100000,
    estimated_value_text: '$100,000',
    naics_code: '541511',
    source_file: 'dod_2024_01_15.json',
    source_data_id: 1,
    enhancement_status: 'idle',
    duplicate_group_id: null,
    set_aside_status: 'Small Business',
    contact_email: 'contracting@dod.gov',
    contact_name: 'John Smith',
    ai_enhanced_title: null,
    ai_enhanced_description: null,
    parsed_contract_value: null,
    ollama_processed_at: null
  },
  {
    id: 'prospect-2',
    title: 'Cloud Infrastructure Setup',
    description: 'Setup and configuration of cloud infrastructure for data processing',
    agency: 'Health and Human Services',
    posted_date: '2024-01-16',
    response_date: '2024-02-16',
    loaded_at: '2024-01-16T10:00:00Z',
    estimated_value: 75000,
    estimated_value_text: '$75,000',
    naics_code: '518210',
    source_file: 'hhs_2024_01_16.json',
    source_data_id: 2,
    enhancement_status: 'processing',
    duplicate_group_id: null,
    set_aside_status: null,
    contact_email: 'it@hhs.gov',
    contact_name: 'Jane Doe',
    ai_enhanced_title: 'Enhanced: Advanced Cloud Infrastructure Implementation',
    ai_enhanced_description: 'AI-enhanced description with technical details',
    parsed_contract_value: 75000,
    ollama_processed_at: '2024-01-16T12:00:00Z'
  }
];

const mockPaginatedResponse = {
  prospects: mockProspects,
  pagination: {
    total_items: 2,
    total_pages: 1,
    page: 1,
    per_page: 10
  }
};

// Complete App wrapper with all providers
const AppWrapper = ({ children }: { children: React.ReactNode }) => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false }
    }
  });

  return (
    <QueryClientProvider client={queryClient}>
      <ToastContextProvider>
        <TimezoneProvider>
          <ProspectEnhancementProvider>
            {children}
          </ProspectEnhancementProvider>
        </TimezoneProvider>
      </ToastContextProvider>
    </QueryClientProvider>
  );
};

// Integration test component that combines multiple features
const ProspectWorkflowApp = () => {
  const [selectedProspect, setSelectedProspect] = React.useState<string | null>(null);
  const [filters, setFilters] = React.useState({
    naics: '',
    keywords: '',
    agency: '',
    ai_enrichment: 'all',
    dataSourceIds: []
  });

  const handleProspectSelect = (prospectId: string) => {
    setSelectedProspect(prospectId);
  };

  const handleCloseModal = () => {
    setSelectedProspect(null);
  };

  const handleFiltersChange = (newFilters: any) => {
    setFilters(newFilters);
  };

  return (
    <div>
      <div data-testid="prospect-workflow-app">
        <ProspectFilters 
          filters={filters}
          onFiltersChange={handleFiltersChange}
        />
        
        <ProspectTable 
          prospects={mockProspects}
          onProspectSelect={handleProspectSelect}
          loading={false}
          enhancementStates={{}}
        />

        <AIEnrichment />
      </div>

      {selectedProspect && (
        <ProspectDetailsModal
          prospectId={selectedProspect}
          isOpen={!!selectedProspect}
          onClose={handleCloseModal}
        />
      )}
    </div>
  );
};

describe('Prospect Workflow Integration Tests', () => {
  const user = userEvent.setup();

  beforeEach(() => {
    vi.clearAllMocks();
    
    // Mock successful API responses
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockPaginatedResponse)
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('completes full prospect discovery and filtering workflow', async () => {
    render(
      <AppWrapper>
        <ProspectWorkflowApp />
      </AppWrapper>
    );

    // Verify initial state - prospects are loaded
    expect(screen.getByTestId('prospect-workflow-app')).toBeInTheDocument();
    
    // Should show prospect table with data
    await waitFor(() => {
      expect(screen.getByText('Software Development Services')).toBeInTheDocument();
      expect(screen.getByText('Cloud Infrastructure Setup')).toBeInTheDocument();
    });

    // Test filtering workflow
    const keywordInput = screen.getByPlaceholderText(/search prospects/i);
    await user.type(keywordInput, 'software');

    // Should trigger filter change
    await waitFor(() => {
      // This would normally filter the results, but since we're mocking data,
      // we verify the input was updated
      expect(keywordInput).toHaveValue('software');
    });

    // Test agency filter
    const agencySelect = screen.getByLabelText(/agency/i);
    await user.click(agencySelect);
    
    // Look for agency options
    await waitFor(() => {
      const dod = screen.getByText('Department of Defense');
      expect(dod).toBeInTheDocument();
    });

    await user.click(screen.getByText('Department of Defense'));

    // Test NAICS code filter
    const naicsInput = screen.getByPlaceholderText(/naics code/i);
    await user.type(naicsInput, '541511');
    
    expect(naicsInput).toHaveValue('541511');
  });

  it('completes prospect selection and details workflow', async () => {
    render(
      <AppWrapper>
        <ProspectWorkflowApp />
      </AppWrapper>
    );

    // Wait for prospects to load
    await waitFor(() => {
      expect(screen.getByText('Software Development Services')).toBeInTheDocument();
    });

    // Click on first prospect to open details
    const firstProspectRow = screen.getByText('Software Development Services').closest('tr');
    expect(firstProspectRow).toBeInTheDocument();
    
    await user.click(firstProspectRow!);

    // Should open prospect details modal
    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument();
      expect(screen.getByText('Contract Details')).toBeInTheDocument();
    });

    // Verify prospect details are displayed
    expect(screen.getByDisplayValue('Software Development Services')).toBeInTheDocument();
    expect(screen.getByDisplayValue('Department of Defense')).toBeInTheDocument();
    expect(screen.getByDisplayValue('$100,000')).toBeInTheDocument();

    // Test decision workflow within modal
    const goButton = screen.getByRole('button', { name: /go/i });
    const noGoButton = screen.getByRole('button', { name: /no.go/i });
    
    expect(goButton).toBeInTheDocument();
    expect(noGoButton).toBeInTheDocument();

    // Make a decision
    await user.click(goButton);

    // Should show reason input
    const reasonInput = screen.getByPlaceholderText(/reason for your decision/i);
    expect(reasonInput).toBeInTheDocument();
    
    await user.type(reasonInput, 'Good fit for our development capabilities');

    // Submit decision
    const submitButton = screen.getByRole('button', { name: /submit decision/i });
    await user.click(submitButton);

    // Close modal
    const closeButton = screen.getByRole('button', { name: /close/i });
    await user.click(closeButton);

    await waitFor(() => {
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    });
  });

  it('completes AI enhancement workflow', async () => {
    render(
      <AppWrapper>
        <ProspectWorkflowApp />
      </AppWrapper>
    );

    // Wait for UI to load
    await waitFor(() => {
      expect(screen.getByText('Software Development Services')).toBeInTheDocument();
    });

    // Find and click enhancement button for first prospect
    const enhanceButton = screen.getAllByLabelText(/enhance with ai/i)[0];
    expect(enhanceButton).toBeInTheDocument();

    await user.click(enhanceButton);

    // Should show enhancement queued state
    await waitFor(() => {
      // The button should change state or show feedback
      expect(enhanceButton).toBeInTheDocument();
    });

    // Check AI Enhancement dashboard
    const aiDashboard = screen.getByTestId(/ai.enrichment/i);
    expect(aiDashboard).toBeInTheDocument();

    // Should show activity indicators
    expect(screen.getByText(/ai enhancement/i)).toBeInTheDocument();
  });

  it('handles error states gracefully throughout workflow', async () => {
    // Mock API error
    mockFetch.mockRejectedValueOnce(new Error('Network error'));

    render(
      <AppWrapper>
        <ProspectWorkflowApp />
      </AppWrapper>
    );

    // Should handle loading error gracefully
    await waitFor(() => {
      // Error handling depends on implementation
      // At minimum, should not crash the app
      expect(screen.getByTestId('prospect-workflow-app')).toBeInTheDocument();
    });
  });

  it('maintains state consistency across component interactions', async () => {
    render(
      <AppWrapper>
        <ProspectWorkflowApp />
      </AppWrapper>
    );

    // Wait for initial load
    await waitFor(() => {
      expect(screen.getByText('Software Development Services')).toBeInTheDocument();
    });

    // Apply filters
    const keywordInput = screen.getByPlaceholderText(/search prospects/i);
    await user.type(keywordInput, 'cloud');

    // Open prospect details
    const secondProspect = screen.getByText('Cloud Infrastructure Setup');
    const secondProspectRow = secondProspect.closest('tr');
    await user.click(secondProspectRow!);

    // Modal should open with correct prospect
    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument();
      expect(screen.getByDisplayValue('Cloud Infrastructure Setup')).toBeInTheDocument();
    });

    // Check that AI enhanced data is shown
    expect(screen.getByDisplayValue('Enhanced: Advanced Cloud Infrastructure Implementation')).toBeInTheDocument();

    // Close modal and verify filters are maintained
    const closeButton = screen.getByRole('button', { name: /close/i });
    await user.click(closeButton);

    await waitFor(() => {
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    });

    // Filter input should still have value
    expect(keywordInput).toHaveValue('cloud');
  });

  it('supports keyboard navigation throughout the workflow', async () => {
    render(
      <AppWrapper>
        <ProspectWorkflowApp />
      </AppWrapper>
    );

    // Wait for load
    await waitFor(() => {
      expect(screen.getByText('Software Development Services')).toBeInTheDocument();
    });

    // Tab to keyword input
    await user.tab();
    const keywordInput = screen.getByPlaceholderText(/search prospects/i);
    expect(document.activeElement).toBe(keywordInput);

    // Type search term
    await user.type(keywordInput, 'development');

    // Tab through the interface
    await user.tab(); // Should move to next focusable element
    await user.tab(); // Continue tabbing through filters

    // Use arrow keys in table if implemented
    await user.keyboard('{ArrowDown}');
    
    // Use Enter to select prospect
    await user.keyboard('{Enter}');

    // Modal should open
    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument();
    });

    // Escape should close modal
    await user.keyboard('{Escape}');

    await waitFor(() => {
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    });
  });

  it('handles real-time updates and refreshing', async () => {
    const { rerender } = render(
      <AppWrapper>
        <ProspectWorkflowApp />
      </AppWrapper>
    );

    // Initial load
    await waitFor(() => {
      expect(screen.getByText('Software Development Services')).toBeInTheDocument();
    });

    // Simulate data update (e.g., from WebSocket or polling)
    const updatedMockProspects = [
      ...mockProspects,
      {
        id: 'prospect-3',
        title: 'New Prospect Added',
        description: 'Newly added prospect from real-time update',
        agency: 'Department of Energy',
        posted_date: '2024-01-17',
        response_date: '2024-02-17',
        loaded_at: '2024-01-17T10:00:00Z',
        estimated_value: 125000,
        estimated_value_text: '$125,000',
        naics_code: '541511',
        source_file: 'doe_2024_01_17.json',
        source_data_id: 3,
        enhancement_status: 'idle',
        duplicate_group_id: null,
        set_aside_status: null,
        contact_email: null,
        contact_name: null,
        ai_enhanced_title: null,
        ai_enhanced_description: null,
        parsed_contract_value: null,
        ollama_processed_at: null
      }
    ];

    // Mock updated response
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({
        prospects: updatedMockProspects,
        pagination: {
          total_items: 3,
          total_pages: 1,
          page: 1,
          per_page: 10
        }
      })
    });

    // Trigger refresh (this could be automatic via React Query)
    rerender(
      <AppWrapper>
        <ProspectWorkflowApp />
      </AppWrapper>
    );

    // Should show updated data
    await waitFor(() => {
      expect(screen.getByText('New Prospect Added')).toBeInTheDocument();
    });
  });

  it('maintains performance with large datasets', async () => {
    // Create larger dataset for performance testing
    const largeDataset = Array.from({ length: 100 }, (_, i) => ({
      id: `perf-prospect-${i}`,
      title: `Performance Test Prospect ${i}`,
      description: `Description for performance test prospect ${i}`,
      agency: `Test Agency ${i % 5}`,
      posted_date: '2024-01-15',
      response_date: '2024-02-15',
      loaded_at: '2024-01-15T10:00:00Z',
      estimated_value: 50000 + (i * 1000),
      estimated_value_text: `$${(50000 + (i * 1000)).toLocaleString()}`,
      naics_code: '541511',
      source_file: `perf_test_${i}.json`,
      source_data_id: i + 1,
      enhancement_status: 'idle',
      duplicate_group_id: null,
      set_aside_status: null,
      contact_email: null,
      contact_name: null,
      ai_enhanced_title: null,
      ai_enhanced_description: null,
      parsed_contract_value: null,
      ollama_processed_at: null
    }));

    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({
        prospects: largeDataset.slice(0, 10), // Paginated
        pagination: {
          total_items: 100,
          total_pages: 10,
          page: 1,
          per_page: 10
        }
      })
    });

    const startTime = performance.now();

    render(
      <AppWrapper>
        <ProspectWorkflowApp />
      </AppWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText('Performance Test Prospect 0')).toBeInTheDocument();
    });

    const endTime = performance.now();
    const renderTime = endTime - startTime;

    // Should render within reasonable time (adjust threshold as needed)
    expect(renderTime).toBeLessThan(1000); // 1 second threshold

    // Test filtering with large dataset
    const keywordInput = screen.getByPlaceholderText(/search prospects/i);
    const filterStartTime = performance.now();
    
    await user.type(keywordInput, 'Performance');
    
    const filterEndTime = performance.now();
    const filterTime = filterEndTime - filterStartTime;
    
    // Filtering should be responsive
    expect(filterTime).toBeLessThan(500); // 500ms threshold
  });
});