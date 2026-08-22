import React from 'react';

interface State {
  error: Error | null;
}

/** Shows a readable message instead of a silently blank page when any
 * dashboard/screen throws during render. */
export default class ErrorBoundary extends React.Component<
  { children: React.ReactNode },
  State
> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error('PashuSafe render error:', error, info.componentStack);
  }

  render() {
    if (this.state.error) {
      return (
        <div className="m-6 rounded-3xl border border-error/30 bg-error-container p-6">
          <h2 className="font-display text-lg font-bold text-on-error-container">
            ⚠️ This screen hit an error
          </h2>
          <pre className="mt-3 max-h-64 overflow-auto whitespace-pre-wrap rounded-2xl bg-surface-container-lowest p-3 font-mono text-xs text-on-error-container">
            {this.state.error.message}
            {'\n\n'}
            {this.state.error.stack}
          </pre>
          <button
            onClick={() => {
              this.setState({ error: null });
              window.location.href = '/';
            }}
            className="mt-4 rounded-2xl bg-error px-4 py-2 text-sm font-bold text-on-error"
          >
            Back to dashboard
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
