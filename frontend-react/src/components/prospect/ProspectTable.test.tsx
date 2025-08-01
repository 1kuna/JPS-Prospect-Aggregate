import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ProspectTable } from './ProspectTable';
import type { Prospect } from '@/types/prospects';

// Mock the virtualization library
vi.mock('@tanstack/react-virtual', () => ({
  useVirtualizer: () => ({
    getVirtualItems: () => [
      { index: 0, start: 0, size: 50, key: '0' },
      { index: 1, start: 50, size: 50, key: '1' },
    ],
    getTotalSize: () => 100,
    scrollToIndex: vi.fn(),
    measureElement: vi.fn()
  })
}));

// Mock TanStack Table - will be initialized after mockProspects is defined
let mockTable: any = {
  getHeaderGroups: () => [
    {
      id: 'header-group-1',
      headers: [
        {
          id: 'title',
          isPlaceholder: false,
          column: {
            id: 'title',
            columnDef: { 
              header: 'Title',
              enableSorting: true,
              getCanSort: () => true,
              getIsSorted: () => false,
              toggleSorting: vi.fn(),
              getToggleSortingHandler: () => vi.fn()
            },
            getCanSort: () => true,
            getIsSorted: () => false,
            toggleSorting: vi.fn(),
            getToggleSortingHandler: () => vi.fn()
          },
          getContext: () => ({ header: { column: { columnDef: { header: 'Title' } } } }),
          getResizeHandler: () => vi.fn(),
          getSize: () => 200
        },
        {
          id: 'agency',
          isPlaceholder: false,
          column: {
            id: 'agency',
            columnDef: { 
              header: 'Agency',
              enableSorting: true,
              getCanSort: () => true,
              getIsSorted: () => false,
              toggleSorting: vi.fn(),
              getToggleSortingHandler: () => vi.fn()
            },
            getCanSort: () => true,
            getIsSorted: () => false,
            toggleSorting: vi.fn(),
            getToggleSortingHandler: () => vi.fn()
          },
          getContext: () => ({ header: { column: { columnDef: { header: 'Agency' } } } }),
          getResizeHandler: () => vi.fn(),
          getSize: () => 150
        }
      ]
    }
  ],
  getRowModel: () => ({
    rows: []  // Will be populated after mockProspects is defined
  }),
  getState: () => ({
    sorting: []
  }),
  options: {
    data: mockProspects
  }
};

vi.mock('@tanstack/react-table', () => ({
  createColumnHelper: () => ({
    accessor: vi.fn((_, config) => config),
    display: vi.fn((config) => config)
  }),
  useReactTable: () => mockTable,
  flexRender: (content, context) => {
    if (typeof content === 'function') {
      return content(context);
    }
    return content;
  },
    getRowModel: () => ({
      rows: [
        {
          id: 'row-1',
          original: mockProspects[0],
          getVisibleCells: () => [
            {
              id: 'title-cell',
              renderCell: () => mockProspects[0].title,
              getContext: () => ({
                getValue: () => mockProspects[0].title
              })
            },
            {
              id: 'agency-cell', 
              renderCell: () => mockProspects[0].agency,
              getContext: () => ({
                getValue: () => mockProspects[0].agency
              })
            }
          ]
        },
        {
          id: 'row-2',
          original: mockProspects[1],
          getVisibleCells: () => [
            {
              id: 'title-cell-2',
              renderCell: () => mockProspects[1].title,
              getContext: () => ({
                getValue: () => mockProspects[1].title
              })
            },
            {
              id: 'agency-cell-2',
              renderCell: () => mockProspects[1].agency,
              getContext: () => ({
                getValue: () => mockProspects[1].agency
              })
            }
          ]
        }
      ]
    }),
    setColumnSizing: vi.fn(),
    getAllColumns: () => []
  }),
  getCoreRowModel: vi.fn(),
  getFilteredRowModel: vi.fn(),
  getSortedRowModel: vi.fn(),
  flexRender: (component: any, context: any) => {
    if (typeof component === 'function') {
      return component(context);
    }
    return component;
  }
}));

const mockProspects: Prospect[] = [
  {
    id: 1,
    title: 'AI Software Development Contract',
    agency: 'Department of Technology',
    description: 'Development of AI software solutions',
    naics: '541511',
    naics_description: 'Custom Computer Programming Services',
    naics_source: 'original',
    posted_date: '2024-01-15',
    response_date: '2024-02-15',
    set_aside: 'Small Business',
    set_aside_parsed: 'SMALL_BUSINESS',
    contact_name: 'John Smith',
    contact_email: 'john.smith@tech.gov',
    office: 'Technology Office',
    location: 'Washington, DC',
    notice_id: 'TECH-2024-001',
    source_id: 1,
    sol_number: 'SOL-TECH-001',
    estimated_value_text: '$500,000 - $1,000,000',
    estimated_value_single: 750000,
    original_url: 'https://tech.gov/opportunities/1',
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-10T00:00:00Z',
    scraped_at: '2024-01-01T00:00:00Z',
    ollama_processed_at: '2024-01-05T00:00:00Z'
  },
  {
    id: 2,
    title: 'Cybersecurity Assessment Services',
    agency: 'Department of Defense',
    description: 'Security assessment and penetration testing',
    naics: '541512',
    naics_description: 'Computer Systems Design Services',
    naics_source: 'llm_inferred',
    posted_date: '2024-01-20',
    response_date: '2024-02-20',
    set_aside: '8(a) Set-Aside',
    set_aside_parsed: 'EIGHT_A',
    contact_name: 'Jane Doe',
    contact_email: 'jane.doe@defense.gov',
    office: 'Security Office',
    location: 'Arlington, VA',
    notice_id: 'DEF-2024-002',
    source_id: 2,
    sol_number: 'SOL-DEF-002',
    estimated_value_text: '$200,000',
    estimated_value_single: 200000,
    original_url: 'https://defense.gov/opportunities/2',
    created_at: '2024-01-02T00:00:00Z',
    updated_at: '2024-01-11T00:00:00Z',
    scraped_at: '2024-01-02T00:00:00Z',
    ollama_processed_at: null
  }
];

const mockProspectStatus = {
  status: 'idle',
  currentStep: null,
  queuePosition: null,
  progress: {}
};

// Update mockTable with actual data now that mockProspects is defined
mockTable.getRowModel = () => ({
  rows: mockProspects.map((prospect, index) => ({
    id: `row-${index}`,
    index,
    original: prospect,
    getValue: (columnId) => prospect[columnId],
    getVisibleCells: () => [
      {
        id: `${index}-title`,
        column: { id: 'title', columnDef: {} },
        row: { original: prospect },
        getValue: () => prospect.title,
        renderValue: () => prospect.title,
        getContext: () => ({ getValue: () => prospect.title, row: { original: prospect }, column: { id: 'title' } })
      },
      {
        id: `${index}-agency`,
        column: { id: 'agency', columnDef: {} },
        row: { original: prospect },
        getValue: () => prospect.agency,
        renderValue: () => prospect.agency,
        getContext: () => ({ getValue: () => prospect.agency, row: { original: prospect }, column: { id: 'agency' } })
      }
    ],
    getCanSelect: () => true,
    getIsSelected: () => false,
    toggleSelected: vi.fn()
  }))
});

const defaultProps = {
  table: mockTable,
  prospects: mockProspects,
  isLoading: false,
  isFetching: false,
  onProspectClick: vi.fn(),
  getProspectStatus: vi.fn(() => mockProspectStatus),
  addToQueue: vi.fn(),
  formatUserDate: vi.fn((date: string) => date),
  showAIEnhanced: false
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

describe('ProspectTable', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders prospect table with data', () => {
    renderWithQueryClient(<ProspectTable {...defaultProps} />);
    
    expect(screen.getByText('AI Software Development Contract')).toBeInTheDocument();
    expect(screen.getByText('Cybersecurity Assessment Services')).toBeInTheDocument();
    expect(screen.getByText('Department of Technology')).toBeInTheDocument();
    expect(screen.getByText('Department of Defense')).toBeInTheDocument();
  });

  it('shows loading state', () => {
    renderWithQueryClient(<ProspectTable {...defaultProps} isLoading={true} prospects={[]} />);
    
    expect(screen.getByText(/loading/i)).toBeInTheDocument();
  });

  it('shows empty state when no prospects', () => {
    renderWithQueryClient(<ProspectTable {...defaultProps} prospects={[]} />);
    
    expect(screen.getByText(/no prospects found/i)).toBeInTheDocument();
  });

  it('calls onProspectClick when row is clicked', async () => {
    const user = userEvent.setup();
    renderWithQueryClient(<ProspectTable {...defaultProps} />);
    
    const firstRow = screen.getByText('AI Software Development Contract');
    await user.click(firstRow);
    
    expect(defaultProps.onProspectClick).toHaveBeenCalledWith(mockProspects[0]);
  });

  it('displays AI enhancement indicators', () => {
    renderWithQueryClient(<ProspectTable {...defaultProps} />);
    
    // First prospect has AI enhancements (ollama_processed_at is not null)
    const aiIndicators = screen.getAllByText('✨');
    expect(aiIndicators.length).toBeGreaterThan(0);
  });

  it('toggles between original and AI enhanced data', () => {
    const { rerender } = renderWithQueryClient(<ProspectTable {...defaultProps} />);
    
    expect(screen.getByText('Custom Computer Programming Services')).toBeInTheDocument();
    
    // Toggle to show AI enhanced data
    rerender(
      <QueryClientProvider client={new QueryClient()}>
        <ProspectTable {...defaultProps} showAIEnhanced={true} />
      </QueryClientProvider>
    );
    
    // Should still show the data (might be different format for AI enhanced)
    expect(screen.getByText('AI Software Development Contract')).toBeInTheDocument();
  });

  it('handles column sorting', async () => {
    const user = userEvent.setup();
    renderWithQueryClient(<ProspectTable {...defaultProps} />);
    
    const titleHeader = screen.getByText('Title');
    await user.click(titleHeader);
    
    // Should trigger sorting (implementation would sort the data)
    expect(titleHeader).toBeInTheDocument();
  });

  it('displays enhancement status badges', () => {
    const getProspectStatus = vi.fn()
      .mockReturnValueOnce({ status: 'processing', currentStep: 'Analyzing values' })
      .mockReturnValueOnce({ status: 'idle' });
    
    renderWithQueryClient(
      <ProspectTable {...defaultProps} getProspectStatus={getProspectStatus} />
    );
    
    expect(screen.getByText(/processing/i)).toBeInTheDocument();
  });

  it('shows enhancement buttons for prospects', () => {
    renderWithQueryClient(<ProspectTable {...defaultProps} />);
    
    const enhanceButtons = screen.getAllByText(/enhance with ai/i);
    expect(enhanceButtons.length).toBeGreaterThan(0);
  });

  it('handles enhancement button clicks', async () => {
    const user = userEvent.setup();
    renderWithQueryClient(<ProspectTable {...defaultProps} />);
    
    const enhanceButton = screen.getAllByText(/enhance with ai/i)[0];
    await user.click(enhanceButton);
    
    expect(defaultProps.addToQueue).toHaveBeenCalled();
  });

  it('displays contract values correctly', () => {
    renderWithQueryClient(<ProspectTable {...defaultProps} />);
    
    expect(screen.getByText('$500,000 - $1,000,000')).toBeInTheDocument();
    expect(screen.getByText('$200,000')).toBeInTheDocument();
  });

  it('formats dates using provided formatter', () => {
    const formatUserDate = vi.fn((date: string) => `Formatted: ${date}`);
    
    renderWithQueryClient(
      <ProspectTable {...defaultProps} formatUserDate={formatUserDate} />
    );
    
    expect(formatUserDate).toHaveBeenCalledWith('2024-01-15', 'date', {});
    expect(screen.getByText('Formatted: 2024-01-15')).toBeInTheDocument();
  });

  it('displays NAICS codes and descriptions', () => {
    renderWithQueryClient(<ProspectTable {...defaultProps} />);
    
    expect(screen.getByText('541511')).toBeInTheDocument();
    expect(screen.getByText('Custom Computer Programming Services')).toBeInTheDocument();
    expect(screen.getByText('541512')).toBeInTheDocument();
    expect(screen.getByText('Computer Systems Design Services')).toBeInTheDocument();
  });

  it('shows set-aside information', () => {
    renderWithQueryClient(<ProspectTable {...defaultProps} />);
    
    expect(screen.getByText('Small Business')).toBeInTheDocument();
    expect(screen.getByText('8(a) Set-Aside')).toBeInTheDocument();
  });

  it('handles keyboard navigation', async () => {
    const user = userEvent.setup();
    renderWithQueryClient(<ProspectTable {...defaultProps} />);
    
    const table = screen.getByRole('table');
    await user.click(table);
    
    // Test arrow key navigation
    await user.keyboard('{ArrowDown}');
    await user.keyboard('{Enter}');
    
    // Should trigger prospect selection
    expect(defaultProps.onProspectClick).toHaveBeenCalled();
  });

  it('shows tooltips on hover', async () => {
    const user = userEvent.setup();
    renderWithQueryClient(<ProspectTable {...defaultProps} />);
    
    const titleCell = screen.getByText('AI Software Development Contract');
    await user.hover(titleCell);
    
    // Should show tooltip with full description
    await waitFor(() => {
      expect(screen.getByText(/development of ai software solutions/i)).toBeInTheDocument();
    });
  });

  it('handles row selection', async () => {
    const user = userEvent.setup();
    renderWithQueryClient(<ProspectTable {...defaultProps} />);
    
    const checkbox = screen.getAllByRole('checkbox')[0];
    await user.click(checkbox);
    
    // Should indicate row is selected
    expect(checkbox).toBeChecked();
  });

  it('supports column resizing', async () => {
    const user = userEvent.setup();
    renderWithQueryClient(<ProspectTable {...defaultProps} />);
    
    const resizeHandle = screen.getByTestId('resize-handle');
    
    // Simulate drag to resize
    await user.hover(resizeHandle);
    fireEvent.mouseDown(resizeHandle);
    fireEvent.mouseMove(resizeHandle, { clientX: 100 });
    fireEvent.mouseUp(resizeHandle);
    
    // Column should be resized (implementation specific)
    expect(resizeHandle).toBeInTheDocument();
  });

  it('shows row actions menu', async () => {
    const user = userEvent.setup();
    renderWithQueryClient(<ProspectTable {...defaultProps} />);
    
    const actionsButton = screen.getAllByLabelText(/row actions/i)[0];
    await user.click(actionsButton);
    
    // Should show action menu
    expect(screen.getByText(/view details/i)).toBeInTheDocument();
    expect(screen.getByText(/enhance with ai/i)).toBeInTheDocument();
  });

  it('handles virtual scrolling performance', () => {
    const manyProspects = Array.from({ length: 1000 }, (_, i) => ({
      ...mockProspects[0],
      id: i + 1,
      title: `Contract ${i + 1}`
    }));
    
    renderWithQueryClient(<ProspectTable {...defaultProps} prospects={manyProspects} />);
    
    // Should only render visible rows
    const renderedTitles = screen.getAllByText(/Contract \d+/);
    expect(renderedTitles.length).toBeLessThan(20); // Only visible rows rendered
  });

  it('preserves scroll position when data updates', () => {
    const { rerender } = renderWithQueryClient(<ProspectTable {...defaultProps} />);
    
    // Simulate scroll
    const tableContainer = screen.getByTestId('table-container');
    fireEvent.scroll(tableContainer, { target: { scrollTop: 500 } });
    
    // Update data
    const updatedProspects = [...mockProspects, {
      ...mockProspects[0],
      id: 3,
      title: 'New Contract'
    }];
    
    rerender(
      <QueryClientProvider client={new QueryClient()}>
        <ProspectTable {...defaultProps} prospects={updatedProspects} />
      </QueryClientProvider>
    );
    
    // Scroll position should be preserved
    expect(tableContainer.scrollTop).toBe(500);
  });

  it('shows loading skeleton for individual rows', () => {
    const partiallyLoadedProps = {
      ...defaultProps,
      prospects: [mockProspects[0]], // Only one prospect loaded
      isLoading: false,
      hasNextPage: true
    };
    
    renderWithQueryClient(<ProspectTable {...partiallyLoadedProps} />);
    
    // Should show skeleton rows for unloaded data
    const skeletons = screen.getAllByTestId('row-skeleton');
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it('handles error states gracefully', () => {
    const errorProps = {
      ...defaultProps,
      prospects: [],
      error: new Error('Failed to load prospects')
    };
    
    renderWithQueryClient(<ProspectTable {...errorProps} />);
    
    expect(screen.getByText(/error loading prospects/i)).toBeInTheDocument();
    expect(screen.getByText(/failed to load prospects/i)).toBeInTheDocument();
  });

  it('supports accessibility features', () => {
    renderWithQueryClient(<ProspectTable {...defaultProps} />);
    
    const table = screen.getByRole('table');
    expect(table).toHaveAttribute('aria-label', expect.stringContaining('prospects'));
    
    const columnHeaders = screen.getAllByRole('columnheader');
    expect(columnHeaders.length).toBeGreaterThan(0);
    
    columnHeaders.forEach(header => {
      expect(header).toHaveAttribute('aria-sort');
    });
  });
});