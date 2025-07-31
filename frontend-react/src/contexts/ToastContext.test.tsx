import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import React, { act } from 'react';
import { ToastContextProvider, useToast } from './ToastContext';
import { AppError, ErrorSeverity, ErrorCategory } from '@/types/errors';

// Mock the Toast UI components
vi.mock('@/components/ui/Toast', () => ({
  Toast: ({ children, onOpenChange, ...props }: any) => 
    React.createElement('div', { 
      'data-testid': 'toast',
      'data-variant': props.variant,
      'data-severity': props.severity,
      onClick: () => onOpenChange?.(false),
      ...props
    }, children),
  ToastClose: () => React.createElement('button', { 'data-testid': 'toast-close' }, 'Close'),
  ToastDescription: ({ children }: any) => React.createElement('div', { 'data-testid': 'toast-description' }, children),
  ToastProvider: ({ children }: any) => React.createElement('div', { 'data-testid': 'toast-provider' }, children),
  ToastTitle: ({ children }: any) => React.createElement('div', { 'data-testid': 'toast-title' }, children),
  ToastViewport: () => React.createElement('div', { 'data-testid': 'toast-viewport' }),
  ToastAction: ({ children, onClick }: any) => React.createElement('button', { 'data-testid': 'toast-action', onClick }, children),
  ToastIcon: ({ variant, severity }: any) => React.createElement('div', { 'data-testid': 'toast-icon', 'data-variant': variant, 'data-severity': severity }),
}));

// Test component that uses the toast context
const TestComponent = () => {
  const {
    showToast,
    showErrorToast,
    showSuccessToast,
    showInfoToast,
    showWarningToast
  } = useToast();

  return (
    <div>
      <button onClick={() => showToast({ title: 'Test Toast', description: 'Test description' })}>
        Show Toast
      </button>
      <button onClick={() => showErrorToast('Test Error')}>
        Show Error
      </button>
      <button onClick={() => showSuccessToast('Success!', 'Success description')}>
        Show Success
      </button>
      <button onClick={() => showInfoToast('Info message', 'Info description')}>
        Show Info
      </button>
      <button onClick={() => showWarningToast('Warning message', 'Warning description')}>
        Show Warning
      </button>
      <button onClick={() => showErrorToast(new Error('JS Error'))}>
        Show JS Error
      </button>
    </div>
  );
};

const mockAppError: AppError = {
  code: 'TEST_ERROR',
  message: 'Test error message',
  severity: ErrorSeverity.ERROR,
  category: ErrorCategory.SYSTEM,
  timestamp: new Date(),
  userMessage: 'Something went wrong',
  technicalDetails: 'Technical details here',
  recoveryActions: [
    {
      label: 'Retry',
      action: vi.fn(),
      primary: true
    }
  ]
};

describe('ToastContext', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.clearAllMocks();
    vi.useRealTimers();
  });

  it('provides toast context to children', () => {
    render(
      <ToastContextProvider>
        <TestComponent />
      </ToastContextProvider>
    );

    expect(screen.getByText('Show Toast')).toBeInTheDocument();
    expect(screen.getByText('Show Error')).toBeInTheDocument();
    expect(screen.getByText('Show Success')).toBeInTheDocument();
  });

  it('throws error when useToast is used outside provider', () => {
    // Suppress console.error for this test
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    
    expect(() => {
      render(<TestComponent />);
    }).toThrow('useToast must be used within a ToastProvider');
  
    consoleSpy.mockRestore();
  });

  it('shows basic toast with title and description', () => {
    render(
      <ToastContextProvider>
        <TestComponent />
      </ToastContextProvider>
    );

    fireEvent.click(screen.getByText('Show Toast'));

    expect(screen.getByTestId('toast')).toBeInTheDocument();
    expect(screen.getByTestId('toast-title')).toHaveTextContent('Test Toast');
    expect(screen.getByTestId('toast-description')).toHaveTextContent('Test description');
  });

  it('shows error toast with correct styling', () => {
    render(
      <ToastContextProvider>
        <TestComponent />
      </ToastContextProvider>
    );

    fireEvent.click(screen.getByText('Show Error'));

    const toast = screen.getByTestId('toast');
    expect(toast).toBeInTheDocument();
    expect(toast).toHaveAttribute('data-variant', 'destructive');
    expect(screen.getByTestId('toast-title')).toHaveTextContent('Error');
    expect(screen.getByTestId('toast-description')).toHaveTextContent('Test Error');
  });

  it('shows success toast with correct styling', () => {
    render(
      <ToastContextProvider>
        <TestComponent />
      </ToastContextProvider>
    );

    fireEvent.click(screen.getByText('Show Success'));

    const toast = screen.getByTestId('toast');
    expect(toast).toBeInTheDocument();
    expect(toast).toHaveAttribute('data-variant', 'success');
    expect(screen.getByTestId('toast-title')).toHaveTextContent('Success!');
    expect(screen.getByTestId('toast-description')).toHaveTextContent('Success description');
  });

  it('shows info toast with correct styling', () => {
    render(
      <ToastContextProvider>
        <TestComponent />
      </ToastContextProvider>
    );

    fireEvent.click(screen.getByText('Show Info'));

    const toast = screen.getByTestId('toast');
    expect(toast).toBeInTheDocument();
    expect(toast).toHaveAttribute('data-variant', 'info');
    expect(toast).toHaveAttribute('data-severity', 'info');
    expect(screen.getByTestId('toast-title')).toHaveTextContent('Info message');
  });

  it('shows warning toast with correct styling', () => {
    render(
      <ToastContextProvider>
        <TestComponent />
      </ToastContextProvider>
    );

    fireEvent.click(screen.getByText('Show Warning'));

    const toast = screen.getByTestId('toast');
    expect(toast).toBeInTheDocument();
    expect(toast).toHaveAttribute('data-variant', 'warning');
    expect(toast).toHaveAttribute('data-severity', 'warning');
    expect(screen.getByTestId('toast-title')).toHaveTextContent('Warning message');
  });

  it('handles JavaScript Error objects', () => {
    render(
      <ToastContextProvider>
        <TestComponent />
      </ToastContextProvider>
    );

    fireEvent.click(screen.getByText('Show JS Error'));

    const toast = screen.getByTestId('toast');
    expect(toast).toBeInTheDocument();
    expect(toast).toHaveAttribute('data-variant', 'destructive');
    expect(screen.getByTestId('toast-title')).toHaveTextContent('Error');
    expect(screen.getByTestId('toast-description')).toHaveTextContent('JS Error');
  });

  it('handles AppError objects with recovery actions', () => {
    const TestAppErrorComponent = () => {
      const { showErrorToast } = useToast();
      return (
        <button onClick={() => showErrorToast(mockAppError)}>
          Show App Error
        </button>
      );
    };

    render(
      <ToastContextProvider>
        <TestAppErrorComponent />
      </ToastContextProvider>
    );

    fireEvent.click(screen.getByText('Show App Error'));

    const toast = screen.getByTestId('toast');
    expect(toast).toBeInTheDocument();
    expect(toast).toHaveAttribute('data-variant', 'destructive');
    expect(toast).toHaveAttribute('data-severity', 'error');
    expect(screen.getByTestId('toast-title')).toHaveTextContent('Something went wrong');
    expect(screen.getByTestId('toast-description')).toHaveTextContent('Technical details here');
    
    // Should show recovery action
    expect(screen.getByTestId('toast-action')).toHaveTextContent('Retry');
  });

  it('calls recovery action when clicked', () => {
    const TestAppErrorComponent = () => {
      const { showErrorToast } = useToast();
      return (
        <button onClick={() => showErrorToast(mockAppError)}>
          Show App Error
        </button>
      );
    };

    render(
      <ToastContextProvider>
        <TestAppErrorComponent />
      </ToastContextProvider>
    );

    fireEvent.click(screen.getByText('Show App Error'));
    fireEvent.click(screen.getByTestId('toast-action'));

    expect(mockAppError.recoveryActions![0].action).toHaveBeenCalled();
  });

  it('auto-removes toasts after duration', async () => {
    render(
      <ToastContextProvider>
        <TestComponent />
      </ToastContextProvider>
    );

    fireEvent.click(screen.getByText('Show Toast'));
    expect(screen.getByTestId('toast')).toBeInTheDocument();

    // Fast-forward time by 5 seconds (default duration)
    act(() => {
      vi.advanceTimersByTime(5000);
    });

    await waitFor(() => {
      expect(screen.queryByTestId('toast')).not.toBeInTheDocument();
    });
  });

  it('uses custom duration for different toast types', async () => {
    render(
      <ToastContextProvider>
        <TestComponent />
      </ToastContextProvider>
    );

    // Success toast has 3 second duration
    fireEvent.click(screen.getByText('Show Success'));
    expect(screen.getByTestId('toast')).toBeInTheDocument();

    act(() => {
      vi.advanceTimersByTime(3000);
    });

    await waitFor(() => {
      expect(screen.queryByTestId('toast')).not.toBeInTheDocument();
    });
  });

  it('error toasts have 8 second duration', async () => {
    render(
      <ToastContextProvider>
        <TestComponent />
      </ToastContextProvider>
    );

    fireEvent.click(screen.getByText('Show Error'));
    expect(screen.getByTestId('toast')).toBeInTheDocument();

    // Should still be there after 5 seconds
    act(() => {
      vi.advanceTimersByTime(5000);
    });

    expect(screen.getByTestId('toast')).toBeInTheDocument();

    // Should be gone after 8 seconds
    act(() => {
      vi.advanceTimersByTime(3000);
    });

    await waitFor(() => {
      expect(screen.queryByTestId('toast')).not.toBeInTheDocument();
    });
  });

  it('allows manual dismissal of toasts', async () => {
    render(
      <ToastContextProvider>
        <TestComponent />
      </ToastContextProvider>
    );

    fireEvent.click(screen.getByText('Show Toast'));
    expect(screen.getByTestId('toast')).toBeInTheDocument();

    fireEvent.click(screen.getByTestId('toast'));

    await waitFor(() => {
      expect(screen.queryByTestId('toast')).not.toBeInTheDocument();
    });
  });

  it('handles multiple toasts simultaneously', () => {
    render(
      <ToastContextProvider>
        <TestComponent />
      </ToastContextProvider>
    );

    fireEvent.click(screen.getByText('Show Toast'));
    fireEvent.click(screen.getByText('Show Error'));
    fireEvent.click(screen.getByText('Show Success'));

    const toasts = screen.getAllByTestId('toast');
    expect(toasts).toHaveLength(3);
  });

  it('sets up global window.showToast function', () => {
    render(
      <ToastContextProvider>
        <TestComponent />
      </ToastContextProvider>
    );

    expect(window.showToast).toBeDefined();
    expect(typeof window.showToast).toBe('function');

    // Test global function
    act(() => {
      window.showToast({
        title: 'Global Toast',
        message: 'Global message',
        type: 'success'
      });
    });

    expect(screen.getByTestId('toast')).toBeInTheDocument();
    expect(screen.getByTestId('toast-title')).toHaveTextContent('Global Toast');
    expect(screen.getByTestId('toast-description')).toHaveTextContent('Global message');
    
    const toast = screen.getByTestId('toast');
    expect(toast).toHaveAttribute('data-variant', 'success');
  });

  it('cleans up global function on unmount', () => {
    const { unmount } = render(
      <ToastContextProvider>
        <TestComponent />
      </ToastContextProvider>
    );

    expect(window.showToast).toBeDefined();

    unmount();

    expect(window.showToast).toBeUndefined();
  });

  it('handles toast with no description', () => {
    const TestNoDescriptionComponent = () => {
      const { showToast } = useToast();
      return (
        <button onClick={() => showToast({ title: 'Title Only' })}>
          Show Title Only
        </button>
      );
    };

    render(
      <ToastContextProvider>
        <TestNoDescriptionComponent />
      </ToastContextProvider>
    );

    fireEvent.click(screen.getByText('Show Title Only'));

    expect(screen.getByTestId('toast-title')).toHaveTextContent('Title Only');
    expect(screen.queryByTestId('toast-description')).not.toBeInTheDocument();
  });

  it('handles custom toast options', () => {
    const TestCustomToastComponent = () => {
      const { showToast } = useToast();
      return (
        <button onClick={() => showToast({
          title: 'Custom Toast',
          description: 'Custom description',
          variant: 'warning',
          severity: ErrorSeverity.WARNING,
          duration: 10000
        })}>
          Show Custom Toast
        </button>
      );
    };

    render(
      <ToastContextProvider>
        <TestCustomToastComponent />
      </ToastContextProvider>
    );

    fireEvent.click(screen.getByText('Show Custom Toast'));

    const toast = screen.getByTestId('toast');
    expect(toast).toHaveAttribute('data-variant', 'warning');
    expect(toast).toHaveAttribute('data-severity', 'warning');
  });

  it('handles AppError without recovery actions', () => {
    const errorWithoutActions: AppError = {
      ...mockAppError,
      recoveryActions: undefined
    };

    const TestNoActionsComponent = () => {
      const { showErrorToast } = useToast();
      return (
        <button onClick={() => showErrorToast(errorWithoutActions)}>
          Show Error No Actions
        </button>
      );
    };

    render(
      <ToastContextProvider>
        <TestNoActionsComponent />
      </ToastContextProvider>
    );

    fireEvent.click(screen.getByText('Show Error No Actions'));

    expect(screen.getByTestId('toast')).toBeInTheDocument();
    expect(screen.queryByTestId('toast-action')).not.toBeInTheDocument();
  });

  it('handles AppError with fallback message', () => {
    const errorWithoutUserMessage: AppError = {
      ...mockAppError,
      userMessage: undefined
    };

    const TestFallbackComponent = () => {
      const { showErrorToast } = useToast();
      return (
        <button onClick={() => showErrorToast(errorWithoutUserMessage)}>
          Show Error Fallback
        </button>
      );
    };

    render(
      <ToastContextProvider>
        <TestFallbackComponent />
      </ToastContextProvider>
    );

    fireEvent.click(screen.getByText('Show Error Fallback'));

    expect(screen.getByTestId('toast-title')).toHaveTextContent('Test error message');
  });

  it('generates unique IDs for toasts', () => {
    render(
      <ToastContextProvider>
        <TestComponent />
      </ToastContextProvider>
    );

    fireEvent.click(screen.getByText('Show Toast'));
    fireEvent.click(screen.getByText('Show Error'));

    const toasts = screen.getAllByTestId('toast');
    expect(toasts).toHaveLength(2);
    // Each toast should be a separate element
    expect(toasts[0]).not.toBe(toasts[1]);
  });

  it('handles global toast with different types', () => {
    render(
      <ToastContextProvider>
        <TestComponent />
      </ToastContextProvider>
    );

    const testCases = [
      { type: 'success', expectedVariant: 'success' },
      { type: 'error', expectedVariant: 'destructive' },
      { type: 'info', expectedVariant: 'info' },
      { type: 'warning', expectedVariant: 'warning' },
      { type: 'unknown', expectedVariant: 'info' } // fallback
    ];

    testCases.forEach(({ type, expectedVariant }, index) => {
      act(() => {
        window.showToast({
          title: `Test ${type}`,
          message: 'Test message',
          type
        });
      });

      const toasts = screen.getAllByTestId('toast');
      const currentToast = toasts[index];
      expect(currentToast).toHaveAttribute('data-variant', expectedVariant);
    });
  });
});