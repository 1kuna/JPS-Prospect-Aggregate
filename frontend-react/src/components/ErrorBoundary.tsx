import React from 'react';
import { Alert, AlertTitle, AlertDescription } from './ui/alert';
import { Button } from './ui/button';

interface ErrorBoundaryProps {
  fallback?: React.ReactNode;
  children: React.ReactNode;
  onError?: (error: Error, errorInfo: React.ErrorInfo) => void;
  resetOnPropsChange?: boolean;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error?: Error;
  errorInfo?: React.ErrorInfo;
}

class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo): void {
    // Update state with error info for more detailed reporting
    this.setState({ errorInfo });
    
    if (this.props.onError) {
      this.props.onError(error, errorInfo);
    }
    
    // Log to error reporting service
    console.error('Error caught by boundary:', error);
    console.error('Component stack:', errorInfo.componentStack);
  }
  
  // Reset error state when props change if resetOnPropsChange is true
  componentDidUpdate(prevProps: ErrorBoundaryProps) {
    if (
      this.props.resetOnPropsChange && 
      this.state.hasError && 
      prevProps.children !== this.props.children
    ) {
      this.setState({ hasError: false, error: undefined, errorInfo: undefined });
    }
  }

  render(): React.ReactNode {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }
      
      return (
        <div className="error-boundary-container p-4 bg-white rounded-md shadow-md">
          <Alert variant="destructive" className="my-4">
            <AlertTitle>Something went wrong</AlertTitle>
            <AlertDescription>
              <p className="mb-2">{this.state.error?.message || 'An unexpected error occurred'}</p>
              {this.state.error?.stack && (
                <details className="mt-2">
                  <summary className="cursor-pointer text-sm">View technical details</summary>
                  <pre className="mt-2 text-xs overflow-auto p-2 bg-gray-100 rounded">
                    {this.state.error.stack}
                  </pre>
                </details>
              )}
            </AlertDescription>
            <div className="mt-4">
              <Button 
                variant="outline" 
                onClick={() => this.setState({ hasError: false, error: undefined, errorInfo: undefined })}
              >
                Try again
              </Button>
            </div>
          </Alert>
        </div>
      );
    }

    return this.props.children;
  }
}

export { ErrorBoundary }; 