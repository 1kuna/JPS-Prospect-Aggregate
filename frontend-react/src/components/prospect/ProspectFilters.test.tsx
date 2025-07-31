import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { ProspectFilters } from './ProspectFilters';
import type { ProspectFilters as ProspectFiltersType } from '@/hooks/useProspectFilters';
import type { DataSource } from '@/types';

const mockDataSources: DataSource[] = [
  {
    id: 1,
    name: 'Department of Defense',
    url: 'https://dod.mil/opportunities',
    last_scraped: '2024-01-15T10:00:00Z',
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-15T10:00:00Z'
  },
  {
    id: 2,
    name: 'Health and Human Services',
    url: 'https://hhs.gov/opportunities',
    last_scraped: '2024-01-14T09:30:00Z',
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-14T09:30:00Z'
  },
  {
    id: 3,
    name: 'Department of Homeland Security',
    url: 'https://dhs.gov/opportunities',
    last_scraped: '2024-01-13T08:45:00Z',
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-13T08:45:00Z'
  }
];

const defaultFilters: ProspectFiltersType = {
  keywords: '',
  naics: '',
  agency: '',
  dataSourceIds: [],
  ai_enrichment: 'all'
};

const defaultProps = {
  filters: defaultFilters,
  dataSources: mockDataSources,
  onFilterChange: vi.fn(),
  onDataSourceToggle: vi.fn(),
  onClearFilters: vi.fn(),
  hasActiveFilters: false,
  showAIEnhanced: false,
  onShowAIEnhancedChange: vi.fn()
};

describe('ProspectFilters', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders all filter components', () => {
    render(<ProspectFilters {...defaultProps} />);
    
    expect(screen.getByText('Filters')).toBeInTheDocument();
    expect(screen.getByLabelText('Keywords')).toBeInTheDocument();
    expect(screen.getByLabelText('NAICS Code')).toBeInTheDocument();
    expect(screen.getByLabelText('Agency')).toBeInTheDocument();
    expect(screen.getByText('Data Source')).toBeInTheDocument();
    expect(screen.getByText('AI Enrichment')).toBeInTheDocument();
    expect(screen.getByText('Show AI Enhancements')).toBeInTheDocument();
  });

  it('shows clear all button when filters are active', () => {
    render(<ProspectFilters {...defaultProps} hasActiveFilters={true} />);
    
    expect(screen.getByText('Clear All')).toBeInTheDocument();
  });

  it('hides clear all button when no filters are active', () => {
    render(<ProspectFilters {...defaultProps} hasActiveFilters={false} />);
    
    expect(screen.queryByText('Clear All')).not.toBeInTheDocument();
  });

  it('handles keywords input change', async () => {
    const user = userEvent.setup();
    const onFilterChange = vi.fn();
    const props = { ...defaultProps, onFilterChange };
    
    render(<ProspectFilters {...props} />);
    
    const keywordsInput = screen.getByLabelText('Keywords');
    await user.type(keywordsInput, 'software');
    
    // Check that onChange was called progressively for each character
    expect(onFilterChange).toHaveBeenCalledTimes(8);
    expect(onFilterChange).toHaveBeenNthCalledWith(1, 'keywords', 's');
    expect(onFilterChange).toHaveBeenNthCalledWith(8, 'keywords', 'e');
  });

  it('handles NAICS code input change', async () => {
    const user = userEvent.setup();
    const onFilterChange = vi.fn();
    const props = { ...defaultProps, onFilterChange };
    
    render(<ProspectFilters {...props} />);
    
    const naicsInput = screen.getByLabelText('NAICS Code');
    await user.type(naicsInput, '54151');
    
    expect(onFilterChange).toHaveBeenCalledTimes(5);
    expect(onFilterChange).toHaveBeenNthCalledWith(1, 'naics', '5');
    expect(onFilterChange).toHaveBeenNthCalledWith(5, 'naics', '1');
  });

  it('handles agency input change', async () => {
    const user = userEvent.setup();
    const onFilterChange = vi.fn();
    const props = { ...defaultProps, onFilterChange };
    
    render(<ProspectFilters {...props} />);
    
    const agencyInput = screen.getByLabelText('Agency');
    await user.type(agencyInput, 'DOD');
    
    expect(onFilterChange).toHaveBeenCalledTimes(3);
    expect(onFilterChange).toHaveBeenNthCalledWith(1, 'agency', 'D');
    expect(onFilterChange).toHaveBeenNthCalledWith(2, 'agency', 'O');
    expect(onFilterChange).toHaveBeenNthCalledWith(3, 'agency', 'D');
  });

  it('displays all data sources with checkboxes', () => {
    render(<ProspectFilters {...defaultProps} />);
    
    expect(screen.getByText('Department of Defense')).toBeInTheDocument();
    expect(screen.getByText('Health and Human Services')).toBeInTheDocument();
    expect(screen.getByText('Department of Homeland Security')).toBeInTheDocument();
    
    const checkboxes = screen.getAllByRole('checkbox');
    expect(checkboxes).toHaveLength(3); // 3 data sources (switch is not a checkbox)
  });

  it('handles data source toggle', async () => {
    const user = userEvent.setup();
    render(<ProspectFilters {...defaultProps} />);
    
    const dodCheckbox = screen.getByRole('checkbox', { name: /department of defense/i });
    await user.click(dodCheckbox);
    
    expect(defaultProps.onDataSourceToggle).toHaveBeenCalledWith(1);
  });

  it('shows selected data sources as checked', () => {
    const filtersWithSources: ProspectFiltersType = {
      ...defaultFilters,
      dataSourceIds: [1, 3]
    };
    
    render(<ProspectFilters {...defaultProps} filters={filtersWithSources} />);
    
    const dodCheckbox = screen.getByRole('checkbox', { name: /department of defense/i });
    const dhsCheckbox = screen.getByRole('checkbox', { name: /department of homeland security/i });
    const hhsCheckbox = screen.getByRole('checkbox', { name: /health and human services/i });
    
    expect(dodCheckbox).toBeChecked();
    expect(dhsCheckbox).toBeChecked();
    expect(hhsCheckbox).not.toBeChecked();
  });

  it('shows message when no data sources available', () => {
    render(<ProspectFilters {...defaultProps} dataSources={[]} />);
    
    expect(screen.getByText('No data sources available')).toBeInTheDocument();
  });

  it('renders AI enrichment select with correct initial value', () => {
    render(<ProspectFilters {...defaultProps} />);
    
    const select = screen.getByRole('combobox');
    expect(select).toBeInTheDocument();
    expect(select).toHaveAttribute('data-state', 'closed');
  });

  it('handles show AI enhancements toggle', async () => {
    const user = userEvent.setup();
    render(<ProspectFilters {...defaultProps} />);
    
    const toggle = screen.getByRole('switch');
    await user.click(toggle);
    
    expect(defaultProps.onShowAIEnhancedChange).toHaveBeenCalledWith(true);
  });

  it('shows correct toggle state and description', () => {
    const { rerender } = render(<ProspectFilters {...defaultProps} showAIEnhanced={false} />);
    
    expect(screen.getByText('Showing original data only')).toBeInTheDocument();
    
    rerender(<ProspectFilters {...defaultProps} showAIEnhanced={true} />);
    
    expect(screen.getByText('Showing AI-enhanced data in table')).toBeInTheDocument();
  });

  it('handles clear all filters button click', async () => {
    const user = userEvent.setup();
    render(<ProspectFilters {...defaultProps} hasActiveFilters={true} />);
    
    const clearButton = screen.getByText('Clear All');
    await user.click(clearButton);
    
    expect(defaultProps.onClearFilters).toHaveBeenCalled();
  });

  it('displays active filter summary when filters are applied', () => {
    const activeFilters: ProspectFiltersType = {
      keywords: 'software',
      naics: '541511',
      agency: 'DOD',
      dataSourceIds: [1, 2],
      ai_enrichment: 'enhanced'
    };
    
    render(<ProspectFilters {...defaultProps} filters={activeFilters} hasActiveFilters={true} />);
    
    expect(screen.getByText('Active filters:')).toBeInTheDocument();
    expect(screen.getByText('Keywords: software')).toBeInTheDocument();
    expect(screen.getByText('NAICS: 541511')).toBeInTheDocument();
    expect(screen.getByText('Agency: DOD')).toBeInTheDocument();
    expect(screen.getByText('AI: Enhanced Only')).toBeInTheDocument();
    expect(screen.getByText('Source: Department of Defense')).toBeInTheDocument();
    expect(screen.getByText('Source: Health and Human Services')).toBeInTheDocument();
  });

  it('allows removing individual filters from summary', async () => {
    const user = userEvent.setup();
    const activeFilters: ProspectFiltersType = {
      keywords: 'software',
      naics: '541511',
      agency: 'DOD',
      dataSourceIds: [1],
      ai_enrichment: 'enhanced'
    };
    
    render(<ProspectFilters {...defaultProps} filters={activeFilters} hasActiveFilters={true} />);
    
    // Remove keywords filter
    const keywordsRemoveButton = screen.getByText('Keywords: software').nextElementSibling;
    await user.click(keywordsRemoveButton as Element);
    
    expect(defaultProps.onFilterChange).toHaveBeenCalledWith('keywords', '');
    
    // Remove NAICS filter
    const naicsRemoveButton = screen.getByText('NAICS: 541511').nextElementSibling;
    await user.click(naicsRemoveButton as Element);
    
    expect(defaultProps.onFilterChange).toHaveBeenCalledWith('naics', '');
    
    // Remove agency filter
    const agencyRemoveButton = screen.getByText('Agency: DOD').nextElementSibling;
    await user.click(agencyRemoveButton as Element);
    
    expect(defaultProps.onFilterChange).toHaveBeenCalledWith('agency', '');
    
    // Remove AI enrichment filter
    const aiRemoveButton = screen.getByText('AI: Enhanced Only').nextElementSibling;
    await user.click(aiRemoveButton as Element);
    
    expect(defaultProps.onFilterChange).toHaveBeenCalledWith('ai_enrichment', 'all');
    
    // Remove data source filter
    const sourceRemoveButton = screen.getByText('Source: Department of Defense').nextElementSibling;
    await user.click(sourceRemoveButton as Element);
    
    expect(defaultProps.onDataSourceToggle).toHaveBeenCalledWith(1);
  });

  it('displays filter values correctly in inputs', () => {
    const filtersWithValues: ProspectFiltersType = {
      keywords: 'AI development',
      naics: '541511',
      agency: 'Defense',
      dataSourceIds: [2],
      ai_enrichment: 'original'
    };
    
    render(<ProspectFilters {...defaultProps} filters={filtersWithValues} />);
    
    expect(screen.getByDisplayValue('AI development')).toBeInTheDocument();
    expect(screen.getByDisplayValue('541511')).toBeInTheDocument();
    expect(screen.getByDisplayValue('Defense')).toBeInTheDocument();
  });

  it('shows correct placeholder text in inputs', () => {
    render(<ProspectFilters {...defaultProps} />);
    
    expect(screen.getByPlaceholderText('Search in title, description...')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('e.g., 541511, 334')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('e.g., DOD, HHS, DHS')).toBeInTheDocument();
  });

  it('handles keyboard navigation in inputs', async () => {
    const user = userEvent.setup();
    render(<ProspectFilters {...defaultProps} />);
    
    const keywordsInput = screen.getByLabelText('Keywords');
    const naicsInput = screen.getByLabelText('NAICS Code');
    
    await user.click(keywordsInput);
    await user.keyboard('{Tab}');
    
    expect(naicsInput).toHaveFocus();
  });

  it('maintains focus after filter changes', async () => {
    const user = userEvent.setup();
    render(<ProspectFilters {...defaultProps} />);
    
    const keywordsInput = screen.getByLabelText('Keywords');
    await user.click(keywordsInput);
    await user.type(keywordsInput, 'test');
    
    expect(keywordsInput).toHaveFocus();
  });

  it('shows data source count in scrollable container', () => {
    const manyDataSources: DataSource[] = Array.from({ length: 10 }, (_, i) => ({
      id: i + 1,
      name: `Data Source ${i + 1}`,
      url: `https://source${i + 1}.gov`,
      last_scraped: '2024-01-15T10:00:00Z',
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-15T10:00:00Z'
    }));
    
    render(<ProspectFilters {...defaultProps} dataSources={manyDataSources} />);
    
    const dataSourceContainer = screen.getByText('Data Source 1').closest('.max-h-48');
    expect(dataSourceContainer).toHaveClass('overflow-y-auto');
    
    // All data sources should be rendered
    for (let i = 1; i <= 10; i++) {
      expect(screen.getByText(`Data Source ${i}`)).toBeInTheDocument();
    }
  });

  it('handles edge case with undefined filter values', () => {
    const undefinedFilters: ProspectFiltersType = {
      keywords: undefined as any,
      naics: undefined as any,
      agency: undefined as any,
      dataSourceIds: undefined as any,
      ai_enrichment: undefined as any
    };
    
    render(<ProspectFilters {...defaultProps} filters={undefinedFilters} />);
    
    const keywordsInput = screen.getByLabelText('Keywords');
    const naicsInput = screen.getByLabelText('NAICS Code');
    const agencyInput = screen.getByLabelText('Agency');
    
    expect(keywordsInput).toHaveValue('');
    expect(naicsInput).toHaveValue('');
    expect(agencyInput).toHaveValue('');
  });

  it('shows AI enrichment select component', () => {
    render(<ProspectFilters {...defaultProps} />);
    
    const select = screen.getByRole('combobox');
    expect(select).toBeInTheDocument();
    expect(screen.getByText('AI Enrichment')).toBeInTheDocument();
  });

  it('applies correct styling classes', () => {
    render(<ProspectFilters {...defaultProps} />);
    
    const container = screen.getByText('Filters').closest('.w-80');
    expect(container).toHaveClass('flex-shrink-0');
    
    const card = screen.getByText('Filters').closest('.shadow-lg');
    expect(card).toBeInTheDocument();
  });

  it('supports accessibility features', () => {
    render(<ProspectFilters {...defaultProps} />);
    
    // Labels should be associated with inputs
    const keywordsInput = screen.getByLabelText('Keywords');
    const naicsInput = screen.getByLabelText('NAICS Code');
    const agencyInput = screen.getByLabelText('Agency');
    
    expect(keywordsInput).toHaveAttribute('id', 'keywords');
    expect(naicsInput).toHaveAttribute('id', 'naics');
    expect(agencyInput).toHaveAttribute('id', 'agency');
    
    // Switch should have proper labeling
    const aiSwitch = screen.getByRole('switch');
    expect(aiSwitch).toHaveAttribute('id', 'show-ai-table');
  });
});