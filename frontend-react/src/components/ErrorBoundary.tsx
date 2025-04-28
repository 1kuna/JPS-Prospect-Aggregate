import React from 'react';
import styles from './ErrorBoundary.module.css'; // Import CSS module
// Removed imports from deleted ./ui directory
// import { Alert, AlertTitle, AlertDescription } from './ui/alert';
// import { Button } from './ui/button';

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
    } else {
      // Default logging if no onError handler is provided
      console.error('ErrorBoundary caught an error:', error, errorInfo);
    }
    
    // Log to error reporting service
    console.error('Error caught by boundary:', error);
    console.error('Component stack:', errorInfo.componentStack);
  }
  
  // Reset error state when props change if resetOnPropsChange is true
  componentDidUpdate(prevProps: ErrorBoundaryProps) {
    // Reset the error state if resetOnPropsChange is true and children have changed
    if (
      this.props.resetOnPropsChange &&
      this.state.hasError &&
      // Simple check, might need deeper comparison for complex children
      prevProps.children !== this.props.children
    ) {
      this.resetErrorState();
    }
  }

  resetErrorState = () => {
    this.setState({ hasError: false, error: undefined, errorInfo: undefined });
  }

  render(): React.ReactNode {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }
      
      // Render default fallback UI
      return (
        <div className={styles.errorContainer}> {/* Use CSS module class */}
          <h2 className={styles.errorTitle}>Something went wrong</h2>
          <p className={styles.errorMessage}>{this.state.error?.message || 'An unexpected error occurred'}</p>
          {this.state.error?.stack && (
             // Use CSS module class for details container
            <details className={styles.detailsContainer}>
               {/* Use CSS module class for summary */}
              <summary className={styles.detailsSummary}>View technical details</summary>
              {/* Use CSS module class for pre */}
              <pre
                className={styles.detailsPre} // Use CSS module class
              >
                {this.state.error.stack}
              </pre>
            </details>
          )}
           {/* Use CSS module class for button container */}
          <div className={styles.buttonContainer}>
            <button // Replaced Button with standard <button>
              className={styles.tryAgainButton} // Use CSS module class
              onClick={this.resetErrorState}
            >
              Try again
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export { ErrorBoundary }; 