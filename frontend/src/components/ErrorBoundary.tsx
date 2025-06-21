import React, { Component, ErrorInfo, ReactNode } from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
    errorInfo: null
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error, errorInfo: null };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo);
    this.setState({ errorInfo });
  }

  private handleReload = () => {
    window.location.reload();
  };

  private handleReset = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
  };

  public render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-dark-900 flex items-center justify-center p-4">
          <div className="max-w-md w-full bg-dark-800 rounded-lg border border-dark-700 p-6">
            <div className="flex items-center gap-3 mb-4">
              <AlertTriangle className="w-6 h-6 text-error-500" />
              <h1 className="text-xl font-semibold text-white">Something went wrong</h1>
            </div>
            
            <p className="text-dark-300 mb-6">
              An unexpected error occurred. This has been logged and will be fixed in a future update.
            </p>
            
            {this.state.error && (
              <div className="mb-6 p-3 bg-dark-900 rounded border border-dark-600">
                <p className="text-sm text-error-400 font-mono">
                  {this.state.error.toString()}
                </p>
              </div>
            )}
            
            <div className="flex gap-3">
              <button
                onClick={this.handleReset}
                className="btn btn-secondary btn-sm flex items-center gap-2"
              >
                Try Again
              </button>
              <button
                onClick={this.handleReload}
                className="btn btn-primary btn-sm flex items-center gap-2"
              >
                <RefreshCw className="w-4 h-4" />
                Reload App
              </button>
            </div>
            
            {process.env.NODE_ENV === 'development' && this.state.errorInfo && (
              <details className="mt-6">
                <summary className="text-sm text-dark-400 cursor-pointer hover:text-dark-300">
                  Show Error Details
                </summary>
                <pre className="mt-2 p-3 bg-dark-900 rounded border border-dark-600 text-xs text-dark-300 overflow-auto">
                  {this.state.errorInfo.componentStack}
                </pre>
              </details>
            )}
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;