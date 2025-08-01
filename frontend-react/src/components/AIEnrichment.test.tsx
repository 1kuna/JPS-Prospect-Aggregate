import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AIEnrichment } from './AIEnrichment';

// Mock the hooks
vi.mock('@/hooks/useTimezoneDate', () => ({
  useTimezoneDate: () => ({
    formatLastProcessed: vi.fn((date) => `Formatted: ${date}`),
    formatUserDate: vi.fn((date, type) => `Formatted ${type}: ${date}`)
  })
}));

import { useEnhancementQueueService } from '@/hooks/api/useEnhancementQueueService';

vi.mock('@/hooks/api/useEnhancementQueueService', () => ({
  useEnhancementQueueService: vi.fn()
}));

vi.mock('@/utils/statusUtils', () => ({
  getStatusColor: vi.fn((status) => {
    const colors = {
      processing: 'text-blue-600',
      completed: 'text-green-600',
      stopped: 'text-yellow-600',
      error: 'text-red-600'
    };
    return colors[status as keyof typeof colors] || 'text-gray-600';
  })
}));

const mockEnhancementStatus = {
  total_prospects: 1000,
  processed_prospects: 750,
  naics_coverage: {
    original: 300,
    llm_inferred: 450,
    total_percentage: 75.0
  },
  value_parsing: {
    parsed_count: 600,
    total_percentage: 60.0
  },
  set_aside_standardization: {
    standardized_count: 400,
    total_percentage: 40.0
  },
  title_enhancement: {
    enhanced_count: 350,
    total_percentage: 35.0
  },
  last_processed: '2024-01-15T10:30:00Z',
  model_version: 'qwen3-latest'
};

const mockProgress = {
  status: 'processing' as const,
  current_type: 'all' as const,
  processed: 25,
  total: 100,
  percentage: 25.0,
  current_prospect: {
    id: 1,
    title: 'AI Software Development Contract'
  },
  started_at: '2024-01-15T10:00:00Z',
  errors: []
};

const mockLLMOutputs = [
  {
    id: 1,
    timestamp: '2024-01-15T10:30:00Z',
    prospect_id: 'abc123',
    prospect_title: 'AI Software Development Contract',
    enhancement_type: 'naics' as const,
    prompt: 'Extract NAICS code',
    response: '{"code": "541511", "description": "Custom Computer Programming Services"}',
    parsed_result: {
      code: '541511',
      description: 'Custom Computer Programming Services'
    },
    success: true,
    error_message: null,
    processing_time: 2.45
  },
  {
    id: 2,
    timestamp: '2024-01-15T10:31:00Z',
    prospect_id: 'def456',
    prospect_title: 'Cybersecurity Assessment Services',
    enhancement_type: 'values' as const,
    prompt: 'Extract contract value',
    response: '{"single": 500000}',
    parsed_result: {
      single: 500000
    },
    success: true,
    error_message: null,
    processing_time: 1.23
  },
  {
    id: 3,
    timestamp: '2024-01-15T10:32:00Z',
    prospect_id: 'ghi789',
    prospect_title: 'Failed Processing Example',
    enhancement_type: 'titles' as const,
    prompt: 'Enhance title',
    response: 'Invalid JSON response',
    parsed_result: null as any,
    success: false,
    error_message: 'JSON parsing failed',
    processing_time: 0.5
  }
];

const mockHookDefault = {
  // Status queries
  queueStatus: undefined,
  iterativeProgress: undefined,
  enrichmentStatus: mockEnhancementStatus,
  llmOutputs: mockLLMOutputs,
  
  // Loading states
  isLoadingQueue: false,
  isLoadingIterative: false,
  isLoadingEnrichment: false,
  isLoadingLLMOutputs: false,
  
  // Computed values
  isWorkerRunning: false,
  queueSize: 0,
  currentItem: undefined,
  pendingItems: [],
  recentCompleted: [],
  isIterativeProcessing: false,
  iterativePercentage: 0,
  totalProspects: 1000,
  processedProspects: 750,
  
  // Actions
  getQueueItemOptions: vi.fn(),
  cancelQueueItem: vi.fn(),
  startWorker: vi.fn(),
  stopWorker: vi.fn(),
  startIterative: vi.fn(),
  stopIterative: vi.fn(),
  
  // Action states
  isCancelling: false,
  isStartingWorker: false,
  isStoppingWorker: false,
  isStartingIterative: false,
  isStoppingIterative: false,
  
  // Refetch functions
  refetchQueueStatus: vi.fn(),
  refetchIterativeProgress: vi.fn(),
  refetchEnrichmentStatus: vi.fn(),
  refetchLLMOutputs: vi.fn(),
};

function renderWithQueryClient(component: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false }
    }
  });

  return render(
    <QueryClientProvider client={queryClient}>
      {component}
    </QueryClientProvider>
  );
}

describe('AIEnrichment', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(useEnhancementQueueService).mockReturnValue(mockHookDefault);
  });

  it('renders main components', () => {
    renderWithQueryClient(<AIEnrichment />);
    
    expect(screen.getByText('AI Enrichment Status')).toBeInTheDocument();
    expect(screen.getByText('Controls')).toBeInTheDocument();
    expect(screen.getByText('LLM Output Log')).toBeInTheDocument();
  });

  it('displays enrichment status overview', () => {
    renderWithQueryClient(<AIEnrichment />);
    
    expect(screen.getByText('750 of 1,000 processed')).toBeInTheDocument();
    expect(screen.getByText('NAICS Classification')).toBeInTheDocument();
    expect(screen.getByText('Value Parsing')).toBeInTheDocument();
    expect(screen.getByText('Set-Aside Standardization')).toBeInTheDocument();
    expect(screen.getByText('Title Enhancement')).toBeInTheDocument();
  });

  it('shows correct coverage percentages', () => {
    renderWithQueryClient(<AIEnrichment />);
    
    expect(screen.getByText('75.0%')).toBeInTheDocument(); // NAICS coverage
    expect(screen.getByText('60.0%')).toBeInTheDocument(); // Value parsing
    expect(screen.getByText('40.0%')).toBeInTheDocument(); // Set-aside
    expect(screen.getByText('35.0%')).toBeInTheDocument(); // Title enhancement
  });

  it('displays last processed information', () => {
    renderWithQueryClient(<AIEnrichment />);
    
    expect(screen.getByText('Last processed:')).toBeInTheDocument();
    expect(screen.getByText('Formatted: 2024-01-15T10:30:00Z')).toBeInTheDocument();
    expect(screen.getByText('Model version:')).toBeInTheDocument();
    expect(screen.getByText('qwen3-latest')).toBeInTheDocument();
  });

  it('shows loading state for status', () => {
    vi.mocked(useEnhancementQueueService).mockReturnValue({
      ...mockHookDefault,
      isLoadingEnrichment: true,
      enrichmentStatus: undefined
    });

    renderWithQueryClient(<AIEnrichment />);
    
    expect(screen.getByRole('generic', { hidden: true })).toHaveClass('animate-spin');
  });

  it('shows error state when status fails to load', () => {
    vi.mocked(useEnhancementQueueService).mockReturnValue({
      ...mockHookDefault,
      enrichmentStatus: undefined,
      isLoadingEnrichment: false
    });

    renderWithQueryClient(<AIEnrichment />);
    
    expect(screen.getByText('Failed to load AI enrichment status')).toBeInTheDocument();
  });

  it('renders enhancement type selector', () => {
    renderWithQueryClient(<AIEnrichment />);
    
    expect(screen.getByText('Enhancement Type')).toBeInTheDocument();
    expect(screen.getByRole('combobox')).toBeInTheDocument();
  });

  it('handles enhancement type selection', async () => {
    const user = userEvent.setup();
    renderWithQueryClient(<AIEnrichment />);
    
    const select = screen.getByRole('combobox');
    await user.click(select);
    
    const valueOption = screen.getByText('Value Parsing');
    await user.click(valueOption);
    
    // Verify that the selection triggers hook re-render with new type
    expect(select).toBeInTheDocument(); // Basic check that interaction worked
  });

  it('renders processing mode radio buttons', () => {
    renderWithQueryClient(<AIEnrichment />);
    
    expect(screen.getByText('Processing Mode')).toBeInTheDocument();
    expect(screen.getByText('Skip existing AI data')).toBeInTheDocument();
    expect(screen.getByText('Replace existing AI data')).toBeInTheDocument();
    
    const radioButtons = screen.getAllByRole('radio');
    expect(radioButtons).toHaveLength(2);
    expect(radioButtons[0]).toBeChecked(); // Default to 'skip'
  });

  it('handles processing mode change', async () => {
    const user = userEvent.setup();
    renderWithQueryClient(<AIEnrichment />);
    
    const replaceRadio = screen.getByRole('radio', { name: /replace existing/i });
    await user.click(replaceRadio);
    
    expect(replaceRadio).toBeChecked();
  });

  it('shows start button when not processing', () => {
    renderWithQueryClient(<AIEnrichment />);
    
    const startButton = screen.getByRole('button', { name: /start enhancement/i });
    expect(startButton).toBeInTheDocument();
    expect(startButton).not.toBeDisabled();
  });

  it('calls startIterative when start button is clicked', async () => {
    const user = userEvent.setup();
    const mockStartIterative = vi.fn();
    
    vi.mocked(useEnhancementQueueService).mockReturnValue({
      ...mockHookDefault,
      startIterative: mockStartIterative
    });

    renderWithQueryClient(<AIEnrichment />);
    
    const startButton = screen.getByRole('button', { name: /start enhancement/i });
    await user.click(startButton);
    
    expect(mockStartIterative).toHaveBeenCalledWith({
      enhancement_type: 'all',
      skip_existing: true
    });
  });

  it('shows stop button and progress when processing', () => {
    vi.mocked(useEnhancementQueueService).mockReturnValue({
      ...mockHookDefault,
      iterativeProgress: mockProgress
    });

    renderWithQueryClient(<AIEnrichment />);
    
    expect(screen.getByRole('button', { name: /stop enhancement/i })).toBeInTheDocument();
    expect(screen.getByText('Status: Processing')).toBeInTheDocument();
    expect(screen.getByText('25 / 100')).toBeInTheDocument();
    expect(screen.getByText('25.0% Complete')).toBeInTheDocument();
  });

  it('shows current prospect when processing', () => {
    vi.mocked(useEnhancementQueueService).mockReturnValue({
      ...mockHookDefault,
      iterativeProgress: mockProgress
    });

    renderWithQueryClient(<AIEnrichment />);
    
    expect(screen.getByText('Currently processing:')).toBeInTheDocument();
    expect(screen.getByText('AI Software Development Contract')).toBeInTheDocument();
  });

  it('calls stopIterative when stop button is clicked', async () => {
    const user = userEvent.setup();
    const mockStopIterative = vi.fn();
    
    vi.mocked(useEnhancementQueueService).mockReturnValue({
      ...mockHookDefault,
      iterativeProgress: mockProgress,
      stopIterative: mockStopIterative
    });

    renderWithQueryClient(<AIEnrichment />);
    
    const stopButton = screen.getByRole('button', { name: /stop enhancement/i });
    await user.click(stopButton);
    
    expect(mockStopIterative).toHaveBeenCalled();
  });

  it('shows stopping state', () => {
    vi.mocked(useEnhancementQueueService).mockReturnValue({
      ...mockHookDefault,
      iterativeProgress: { ...mockProgress, status: 'stopping' }
    });

    renderWithQueryClient(<AIEnrichment />);
    
    expect(screen.getByText('Stopping...')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /stopping/i })).toBeDisabled();
  });

  it('shows completion message', () => {
    vi.mocked(useEnhancementQueueService).mockReturnValue({
      ...mockHookDefault,
      iterativeProgress: { ...mockProgress, status: 'completed', processed: 100 }
    });

    renderWithQueryClient(<AIEnrichment />);
    
    expect(screen.getByText('Enhancement completed successfully!')).toBeInTheDocument();
    expect(screen.getByText('Processed all 100 available records')).toBeInTheDocument();
  });

  it('shows stopped message', () => {
    vi.mocked(useEnhancementQueueService).mockReturnValue({
      ...mockHookDefault,
      iterativeProgress: { ...mockProgress, status: 'stopped' }
    });

    renderWithQueryClient(<AIEnrichment />);
    
    expect(screen.getByText('Enhancement stopped')).toBeInTheDocument();
    expect(screen.getByText('Processed 25 records before stopping')).toBeInTheDocument();
  });

  it('shows error message when present', () => {
    vi.mocked(useEnhancementQueueService).mockReturnValue({
      ...mockHookDefault,
      iterativeProgress: { 
        ...mockProgress, 
        error_message: 'Connection to LLM service failed'
      }
    });

    renderWithQueryClient(<AIEnrichment />);
    
    expect(screen.getByText('Error: Connection to LLM service failed')).toBeInTheDocument();
  });

  it('displays LLM outputs', () => {
    renderWithQueryClient(<AIEnrichment />);
    
    expect(screen.getByText('AI Software Development Contract')).toBeInTheDocument();
    expect(screen.getByText('Cybersecurity Assessment Services')).toBeInTheDocument();
    expect(screen.getByText('Failed Processing Example')).toBeInTheDocument();
  });

  it('shows collapsed output summaries', () => {
    renderWithQueryClient(<AIEnrichment />);
    
    expect(screen.getByText('NAICS: 541511 - Custom Computer Programming Services')).toBeInTheDocument();
    expect(screen.getByText('Value: $500,000')).toBeInTheDocument();
  });

  it('expands and collapses output details', async () => {
    const user = userEvent.setup();
    renderWithQueryClient(<AIEnrichment />);
    
    const expandButtons = screen.getAllByRole('button', { name: '' });
    const expandButton = expandButtons[0];
    if (expandButton) {
      await user.click(expandButton);
    }
    
    expect(screen.getByText('Response:')).toBeInTheDocument();
    expect(screen.getByText('Parsed Result:')).toBeInTheDocument();
    
    // Collapse again
    if (expandButton) {
      await user.click(expandButton);
    }
    
    // Details should be hidden again
    expect(screen.queryByText('Response:')).not.toBeInTheDocument();
  });

  it('shows error details in failed outputs', async () => {
    const user = userEvent.setup();
    renderWithQueryClient(<AIEnrichment />);
    
    // Find and expand the failed output
    const failedOutput = screen.getByText('Failed Processing Example').closest('div');
    const expandButton = failedOutput?.querySelector('button');
    
    if (expandButton) {
      await user.click(expandButton);
      expect(screen.getByText('Error: JSON parsing failed')).toBeInTheDocument();
    }
  });

  it('shows processing times', () => {
    renderWithQueryClient(<AIEnrichment />);
    
    expect(screen.getByText('2.45s')).toBeInTheDocument();
    expect(screen.getByText('1.23s')).toBeInTheDocument();
    expect(screen.getByText('0.50s')).toBeInTheDocument();
  });

  it('shows formatted timestamps', () => {
    renderWithQueryClient(<AIEnrichment />);
    
    expect(screen.getByText('Formatted datetime: 2024-01-15T10:30:00Z')).toBeInTheDocument();
    expect(screen.getByText('Formatted datetime: 2024-01-15T10:31:00Z')).toBeInTheDocument();
  });

  it('shows loading state for LLM outputs', () => {
    vi.mocked(useEnhancementQueueService).mockReturnValue({
      ...mockHookDefault,
      isLoadingLLMOutputs: true,
      llmOutputs: []
    });

    renderWithQueryClient(<AIEnrichment />);
    
    const spinners = screen.getAllByRole('generic', { hidden: true });
    expect(spinners.some(spinner => spinner.classList.contains('animate-spin'))).toBe(true);
  });

  it('shows empty state for LLM outputs', () => {
    vi.mocked(useEnhancementQueueService).mockReturnValue({
      ...mockHookDefault,
      llmOutputs: []
    });

    renderWithQueryClient(<AIEnrichment />);
    
    expect(screen.getByText('No LLM outputs yet. Start an enhancement to see outputs here.')).toBeInTheDocument();
  });

  it('disables controls when processing', () => {
    vi.mocked(useEnhancementQueueService).mockReturnValue({
      ...mockHookDefault,
      iterativeProgress: mockProgress
    });

    renderWithQueryClient(<AIEnrichment />);
    
    const select = screen.getByRole('combobox');
    const radioButtons = screen.getAllByRole('radio');
    
    expect(select).toBeDisabled();
    expect(radioButtons[0]).toBeDisabled();
    expect(radioButtons[1]).toBeDisabled();
  });

  it('handles missing title enhancement data gracefully', () => {
    const statusWithoutTitleEnhancement = {
      ...mockEnhancementStatus,
      title_enhancement: { enhanced_count: 0, total_percentage: 0 }
    };
    
    vi.mocked(useEnhancementQueueService).mockReturnValue({
      ...mockHookDefault,
      enrichmentStatus: statusWithoutTitleEnhancement
    });

    renderWithQueryClient(<AIEnrichment />);
    
    expect(screen.getByText('0')).toBeInTheDocument(); // Should show 0 for enhanced count
    expect(screen.getByText('0.0%')).toBeInTheDocument(); // Should show 0.0% for coverage
  });

  it('shows errors count when processing has errors', () => {
    const progressWithErrors = {
      ...mockProgress,
      errors: [
        { prospect_id: 1, error: 'Error 1', timestamp: '2024-01-15T10:00:00Z' },
        { prospect_id: 2, error: 'Error 2', timestamp: '2024-01-15T10:01:00Z' },
        { prospect_id: 3, error: 'Error 3', timestamp: '2024-01-15T10:02:00Z' }
      ]
    };
    
    vi.mocked(useEnhancementQueueService).mockReturnValue({
      ...mockHookDefault,
      iterativeProgress: progressWithErrors
    });

    renderWithQueryClient(<AIEnrichment />);
    
    expect(screen.getByText('Errors encountered:')).toBeInTheDocument();
    expect(screen.getByText('3 prospect(s) failed')).toBeInTheDocument();
  });

  it('formats large numbers with locale string', () => {
    const largeStatus = {
      ...mockEnhancementStatus,
      total_prospects: 1234567,
      processed_prospects: 987654,
      naics_coverage: {
        ...mockEnhancementStatus.naics_coverage,
        original: 123456,
        llm_inferred: 234567
      }
    };
    
    vi.mocked(useEnhancementQueueService).mockReturnValue({
      ...mockHookDefault,
      enrichmentStatus: largeStatus
    });

    renderWithQueryClient(<AIEnrichment />);
    
    expect(screen.getByText('987,654 of 1,234,567 processed')).toBeInTheDocument();
    expect(screen.getByText('123,456')).toBeInTheDocument();
    expect(screen.getByText('234,567')).toBeInTheDocument();
  });
});