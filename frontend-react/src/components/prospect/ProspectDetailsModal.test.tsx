import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { ProspectDetailsModal } from './ProspectDetailsModal';
import type { Prospect } from '@/types/prospects';

// Mock child components
vi.mock('@/components/GoNoGoDecision', () => ({
  GoNoGoDecision: () => <div data-testid="go-no-go-decision">GoNoGoDecision</div>
}));

vi.mock('@/components/EnhancementButton', () => ({
  EnhancementButton: ({ onClick, enhancementTypes }: any) => (
    <button data-testid="enhancement-button" onClick={() => onClick(enhancementTypes)}>
      Enhance with AI
    </button>
  )
}));

vi.mock('@/components/EnhancementProgress', () => ({
  EnhancementProgress: ({ status }: any) => (
    <div data-testid="enhancement-progress">Progress: {status}</div>
  )
}));

vi.mock('@/components/EnhancementErrorBoundary', () => ({
  EnhancementErrorBoundary: ({ children }: any) => <>{children}</>
}));

vi.mock('@/hooks/api/useAuth', () => ({
  useIsSuperAdmin: () => true
}));

describe('ProspectDetailsModal', () => {
  const mockProspect: Prospect = {
    id: '1',
    native_id: 'TEST-123',
    title: 'Test Contract Opportunity',
    ai_enhanced_title: 'Enhanced Test Contract',
    description: 'This is a test description',
    agency: 'Department of Test',
    naics: '541511',
    naics_description: 'Custom Computer Programming Services',
    naics_source: 'llm_inferred',
    estimated_value: '300000',
    est_value_unit: 'USD',
    estimated_value_text: '$100,000 - $500,000',
    estimated_value_min: '100000',
    estimated_value_max: '500000',
    estimated_value_single: '300000',
    release_date: '2024-01-15',
    award_date: null,
    award_fiscal_year: null,
    place_city: 'Washington',
    place_state: 'DC',
    place_country: 'USA',
    contract_type: 'Fixed Price',
    set_aside: 'Small Business',
    inferred_set_aside: 'SMALL_BUSINESS',
    inferred_naics: '541511',
    inferred_naics_description: 'Custom Computer Programming Services',
    primary_contact_email: 'john.doe@agency.gov',
    primary_contact_name: 'John Doe',
    loaded_at: '2024-01-01T00:00:00Z',
    ollama_processed_at: '2024-01-05T00:00:00Z',
    ollama_model_version: 'qwen3-latest',
    enhancement_status: 'completed',
    enhancement_started_at: '2024-01-05T00:00:00Z',
    enhancement_user_id: null,
    extra: null,
    source_id: 1,
    source_name: 'Test Source'
  };

  const defaultProps = {
    isOpen: true,
    onOpenChange: vi.fn(),
    selectedProspect: mockProspect,
    showAIEnhanced: false,
    onShowAIEnhancedChange: vi.fn(),
    getProspectStatus: vi.fn(() => null),
    addToQueue: vi.fn(),
    formatUserDate: vi.fn((date: string | null | undefined) => date || '')
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders prospect details when open', () => {
    render(<ProspectDetailsModal {...defaultProps} />);
    
    expect(screen.getByText('Contract Details')).toBeInTheDocument();
    expect(screen.getByText('Test Contract Opportunity')).toBeInTheDocument();
    expect(screen.getByText('Department of Test')).toBeInTheDocument();
  });

  it('does not render when closed', () => {
    render(<ProspectDetailsModal {...defaultProps} isOpen={false} />);
    
    expect(screen.queryByText('Contract Details')).not.toBeInTheDocument();
  });

  it('handles null prospect gracefully', () => {
    render(<ProspectDetailsModal {...defaultProps} selectedProspect={null} />);
    
    expect(screen.queryByText('Test Contract Opportunity')).not.toBeInTheDocument();
  });

  it('toggles AI enhanced data display', async () => {
    const user = userEvent.setup();
    render(<ProspectDetailsModal {...defaultProps} />);
    
    const toggle = screen.getByRole('switch', { name: /show ai enhanced/i });
    
    // Initially shows original data
    expect(screen.getByText('Test Contract Opportunity')).toBeInTheDocument();
    expect(screen.queryByText('Enhanced Test Contract')).not.toBeInTheDocument();
    
    // Toggle to show AI enhanced
    await user.click(toggle);
    expect(defaultProps.onShowAIEnhancedChange).toHaveBeenCalledWith(true);
  });

  it('displays enhancement progress when processing', () => {
    const getProspectStatus = vi.fn(() => ({
      status: 'processing',
      currentStep: 'Analyzing values',
      queuePosition: 3,
      progress: {
        titles: { completed: true },
        naics: { completed: false },
        values: { completed: false },
        contacts: { completed: false }
      }
    }));
    
    render(<ProspectDetailsModal {...defaultProps} getProspectStatus={getProspectStatus} />);
    
    expect(screen.getByTestId('enhancement-progress')).toBeInTheDocument();
    expect(screen.getByText('Progress: processing')).toBeInTheDocument();
  });

  it('handles enhancement button click with selected types', async () => {
    const user = userEvent.setup();
    render(<ProspectDetailsModal {...defaultProps} />);
    
    // Open enhancement type dropdown
    const dropdownTrigger = screen.getByRole('button', { name: /select enhancements/i });
    await user.click(dropdownTrigger);
    
    // Deselect some options
    const naicsCheckbox = screen.getByRole('menuitemcheckbox', { name: /naics/i });
    await user.click(naicsCheckbox);
    
    // Click enhancement button
    const enhanceButton = screen.getByTestId('enhancement-button');
    await user.click(enhanceButton);
    
    // Verify addToQueue was called with correct parameters
    expect(defaultProps.addToQueue).toHaveBeenCalledWith({
      prospect_id: '1',
      force_redo: false,
      user_id: expect.any(Number),
      enhancement_types: expect.arrayContaining(['values', 'titles', 'set_asides'])
    });
    
    // Verify NAICS was not included
    expect(defaultProps.addToQueue).toHaveBeenCalledWith(
      expect.objectContaining({
        enhancement_types: expect.not.arrayContaining(['naics'])
      })
    );
  });

  it('displays all prospect fields correctly', () => {
    render(<ProspectDetailsModal {...defaultProps} />);
    
    // Basic Information
    expect(screen.getByText('Small Business')).toBeInTheDocument();
    expect(screen.getByText('541511')).toBeInTheDocument();
    expect(screen.getByText('$100,000 - $500,000')).toBeInTheDocument();
    
    // Contact Information
    expect(screen.getByText('John Doe')).toBeInTheDocument();
    expect(screen.getByText('john.doe@agency.gov')).toBeInTheDocument();
    expect(screen.getByText('Test Office')).toBeInTheDocument();
    expect(screen.getByText('Washington, DC')).toBeInTheDocument();
    
    // Description
    expect(screen.getByText('This is a test description')).toBeInTheDocument();
  });

  it('shows raw data toggle for super admin', async () => {
    const user = userEvent.setup();
    render(<ProspectDetailsModal {...defaultProps} />);
    
    const rawDataToggle = screen.getByRole('switch', { name: /show raw data/i });
    expect(rawDataToggle).toBeInTheDocument();
    
    await user.click(rawDataToggle);
    
    // Should show raw data section
    expect(screen.getByText('Raw Data')).toBeInTheDocument();
  });

  it('handles select all/deselect all enhancement types', async () => {
    const user = userEvent.setup();
    render(<ProspectDetailsModal {...defaultProps} />);
    
    // Open dropdown
    const dropdownTrigger = screen.getByRole('button', { name: /select enhancements/i });
    await user.click(dropdownTrigger);
    
    // Click deselect all
    const deselectAllButton = screen.getByText('Deselect All');
    await user.click(deselectAllButton);
    
    // Click enhancement button - should not call addToQueue with empty types
    const enhanceButton = screen.getByTestId('enhancement-button');
    await user.click(enhanceButton);
    
    // Verify addToQueue was called with empty enhancement_types
    expect(defaultProps.addToQueue).toHaveBeenCalledWith(
      expect.objectContaining({
        enhancement_types: []
      })
    );
    
    // Now select all
    await user.click(dropdownTrigger);
    const selectAllButton = screen.getByText('Select All');
    await user.click(selectAllButton);
    
    await user.click(enhanceButton);
    
    // Verify all types are included
    expect(defaultProps.addToQueue).toHaveBeenCalledWith(
      expect.objectContaining({
        enhancement_types: ['values', 'titles', 'naics', 'set_asides']
      })
    );
  });

  it('displays AI enrichment indicators', () => {
    render(<ProspectDetailsModal {...defaultProps} />);
    
    // Look for AI enrichment badges
    const badges = screen.getAllByText('✨');
    expect(badges.length).toBeGreaterThan(0);
  });

  it('handles prospect without enhanced fields', () => {
    const basicProspect = {
      ...mockProspect,
      title_enhanced: null,
      naics: null,
      estimated_value_single: null,
      ollama_processed_at: null
    };
    
    render(<ProspectDetailsModal {...defaultProps} selectedProspect={basicProspect} />);
    
    // Should still render without errors
    expect(screen.getByText('Test Contract Opportunity')).toBeInTheDocument();
    
    // Should not show AI badges
    const badges = screen.queryAllByText('✨');
    expect(badges.length).toBe(0);
  });

  it('formats dates using the provided formatter', () => {
    const formatUserDate = vi.fn((date: string) => 'Formatted Date');
    render(<ProspectDetailsModal {...defaultProps} formatUserDate={formatUserDate} />);
    
    expect(formatUserDate).toHaveBeenCalledWith('2024-01-15', 'date', {});
    expect(formatUserDate).toHaveBeenCalledWith('2024-02-15', 'date', {});
    expect(screen.getAllByText('Formatted Date')).toHaveLength(2);
  });

  it('closes modal when close button is clicked', async () => {
    const user = userEvent.setup();
    render(<ProspectDetailsModal {...defaultProps} />);
    
    const closeButton = screen.getByRole('button', { name: /close/i });
    await user.click(closeButton);
    
    expect(defaultProps.onOpenChange).toHaveBeenCalledWith(false);
  });
});