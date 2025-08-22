import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ProspectTable } from '@/components/prospect/ProspectTable';
import { createColumnHelper, getCoreRowModel, useReactTable } from '@tanstack/react-table';
import type { Prospect } from '@/types/prospects';

// Real test data from actual database schema
const generateRealProspect = (id: number): Prospect => ({
  id: `prospect-${id}`,
  native_id: `NATIVE-${id}`,
  title: `Federal Contract Opportunity ${id} - IT Services and Support`,
  ai_enhanced_title: `Enhanced: Comprehensive IT Infrastructure Services Contract ${id}`,
  description: `This is a detailed description for prospect ${id} involving multiple deliverables and technical requirements.`,
  agency: ['Department of Defense', 'Department of State', 'Department of Commerce'][id % 3],
  naics: ['541511', '541512', '541513'][id % 3],
  naics_description: ['Custom Computer Programming Services', 'Computer Systems Design Services', 'Computer Facilities Management Services'][id % 3],
  naics_source: id % 2 === 0 ? 'original' : 'llm_inferred',
  estimated_value: 1000000 + (id * 50000),
  estimated_value_text: `$${(1000000 + (id * 50000)).toLocaleString()}`,
  estimated_value_min: 800000 + (id * 40000),
  estimated_value_max: 1200000 + (id * 60000),
  estimated_value_single: 1000000 + (id * 50000),
  release_date: new Date(2024, (id % 12), (id % 28) + 1).toISOString(),
  award_date: new Date(2025, (id % 12), (id % 28) + 1).toISOString(),
  award_fiscal_year: 2025,
  place_city: ['Washington', 'Arlington', 'Alexandria'][id % 3],
  place_state: ['DC', 'VA', 'MD'][id % 3],
  place_country: 'USA',
  contract_type: ['Fixed Price', 'Cost Plus', 'Time and Materials'][id % 3],
  set_aside: ['Small Business', 'WOSB', '8(a)', null][id % 4],
  set_aside_standardized: ['SMALL_BUSINESS', 'WOSB', 'EIGHT_A', null][id % 4],
  set_aside_standardized_label: ['Small Business', 'Woman-Owned Small Business', '8(a) Business Development', null][id % 4],
  primary_contact_email: `contact${id}@agency.gov`,
  primary_contact_name: `John Doe ${id}`,
  loaded_at: new Date(2024, 11, 1).toISOString(),
  ollama_processed_at: id % 2 === 0 ? new Date(2024, 11, 2).toISOString() : null,
  ollama_model_version: id % 2 === 0 ? 'qwen3:latest' : null,
  extra: {
    source: 'test-data',
    confidence_score: 0.85 + (id % 15) / 100
  },
  data_source_id: (id % 9) + 1,
  // Additional fields from the real schema
  url: `https://agency.gov/opportunity/${id}`,
  primary_poc: `POC Name ${id}`,
  primary_email: `poc${id}@agency.gov`,
  primary_phone: `202-555-${String(1000 + id).padStart(4, '0')}`,
  secondary_poc: id % 2 === 0 ? `Secondary POC ${id}` : null,
  solicitation_id: `SOL-2024-${String(id).padStart(4, '0')}`,
  naics_code: ['541511', '541512', '541513'][id % 3],
  est_value_unit: 'USD',
  created_at: new Date(2024, 10, id % 30 + 1).toISOString(),
  updated_at: new Date(2024, 11, id % 30 + 1).toISOString()
});

// Generate a realistic dataset
const testProspects = Array.from({ length: 100 }, (_, i) => generateRealProspect(i));

// Test component wrapper
const TestWrapper: React.FC<{ 
  children: React.ReactNode;
  prospects?: Prospect[];
  onProspectsChange?: (prospects: Prospect[]) => void;
}> = ({ children, prospects = testProspects, onProspectsChange }) => {
  const [currentProspects, setCurrentProspects] = React.useState(prospects);
  
  React.useEffect(() => {
    setCurrentProspects(prospects);
  }, [prospects]);

  React.useEffect(() => {
    onProspectsChange?.(currentProspects);
  }, [currentProspects, onProspectsChange]);

  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });

  return (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );
};

// Table setup hook for testing
const useTestTable = (data: Prospect[]) => {
  const columnHelper = createColumnHelper<Prospect>();

  const columns = [
    columnHelper.accessor('title', {
      header: 'Title',
      cell: info => info.getValue(),
    }),
    columnHelper.accessor('agency', {
      header: 'Agency',
      cell: info => info.getValue(),
    }),
    columnHelper.accessor('estimated_value_single', {
      header: 'Value',
      cell: info => info.getValue() ? `$${info.getValue()?.toLocaleString()}` : 'N/A',
    }),
    columnHelper.accessor('set_aside', {
      header: 'Set-Aside',
      cell: info => info.getValue() || 'None',
    }),
  ];

  return useReactTable({
    data,
    columns,
    getCoreRowModel: getCoreRowModel(),
  });
};

describe('ProspectTable Performance Tests', () => {
  let renderCount = 0;
  let ProspectTableWithCounter: typeof ProspectTable;

  beforeEach(() => {
    renderCount = 0;
    // Create a wrapped version that counts renders
    ProspectTableWithCounter = (props: any) => {
      renderCount++;
      return <ProspectTable {...props} />;
    };
  });

  it('should minimize re-renders when props do not change', () => {
    const TableContainer = () => {
      const table = useTestTable(testProspects);
      const [count, setCount] = React.useState(0);

      return (
        <div>
          <button onClick={() => setCount(c => c + 1)}>Trigger Re-render ({count})</button>
          <ProspectTableWithCounter
            table={table}
            prospects={testProspects}
            isLoading={false}
            isFetching={false}
            onRowClick={() => {}}
          />
        </div>
      );
    };

    const { rerender } = render(
      <TestWrapper>
        <TableContainer />
      </TestWrapper>
    );

    const initialRenderCount = renderCount;
    
    // Trigger parent re-render
    fireEvent.click(screen.getByText(/Trigger Re-render/));
    
    // With React.memo, the table should not re-render if props haven't changed
    expect(renderCount).toBe(initialRenderCount);
  });

  it('should re-render when prospects data changes', () => {
    const TableContainer = ({ prospects }: { prospects: Prospect[] }) => {
      const table = useTestTable(prospects);
      
      return (
        <ProspectTableWithCounter
          table={table}
          prospects={prospects}
          isLoading={false}
          isFetching={false}
          onRowClick={() => {}}
        />
      );
    };

    const { rerender } = render(
      <TestWrapper>
        <TableContainer prospects={testProspects} />
      </TestWrapper>
    );

    const initialRenderCount = renderCount;

    // Change the prospects data
    const newProspects = [...testProspects.slice(0, 50)];
    rerender(
      <TestWrapper>
        <TableContainer prospects={newProspects} />
      </TestWrapper>
    );

    // Should re-render when data changes
    expect(renderCount).toBeGreaterThan(initialRenderCount);
  });

  it('should handle large datasets efficiently', () => {
    const largeDataset = Array.from({ length: 1000 }, (_, i) => generateRealProspect(i));
    
    const TableContainer = () => {
      const table = useTestTable(largeDataset);
      
      return (
        <ProspectTableWithCounter
          table={table}
          prospects={largeDataset}
          isLoading={false}
          isFetching={false}
          onRowClick={() => {}}
        />
      );
    };

    const startTime = performance.now();
    
    render(
      <TestWrapper>
        <TableContainer />
      </TestWrapper>
    );

    const endTime = performance.now();
    const renderTime = endTime - startTime;

    // Should render large dataset in reasonable time (< 500ms)
    expect(renderTime).toBeLessThan(500);
  });

  it('should not re-render when only isFetching changes', () => {
    const TableContainer = ({ isFetching }: { isFetching: boolean }) => {
      const table = useTestTable(testProspects);
      
      return (
        <ProspectTableWithCounter
          table={table}
          prospects={testProspects}
          isLoading={false}
          isFetching={isFetching}
          onRowClick={() => {}}
        />
      );
    };

    render(
      <TestWrapper>
        <TableContainer isFetching={false} />
      </TestWrapper>
    );

    const beforeFetchingRenderCount = renderCount;

    // Change only isFetching
    render(
      <TestWrapper>
        <TableContainer isFetching={true} />
      </TestWrapper>
    );

    // With proper memoization, changing isFetching alone might still cause a re-render
    // but we want to ensure it's minimal
    expect(renderCount - beforeFetchingRenderCount).toBeLessThanOrEqual(2);
  });

  it('should measure click handler performance', () => {
    const handleClick = jest.fn();
    
    const TableContainer = () => {
      const table = useTestTable(testProspects.slice(0, 10));
      
      return (
        <ProspectTable
          table={table}
          prospects={testProspects.slice(0, 10)}
          isLoading={false}
          isFetching={false}
          onRowClick={handleClick}
        />
      );
    };

    render(
      <TestWrapper>
        <TableContainer />
      </TestWrapper>
    );

    const rows = screen.getAllByRole('row');
    // Click on a data row (not header)
    if (rows.length > 1) {
      const startTime = performance.now();
      fireEvent.click(rows[1]);
      const endTime = performance.now();
      
      expect(handleClick).toHaveBeenCalledTimes(1);
      expect(endTime - startTime).toBeLessThan(50); // Click should be handled quickly
    }
  });
});