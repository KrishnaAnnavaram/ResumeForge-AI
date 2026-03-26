import { Component, type ReactNode } from "react";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

/**
 * ErrorBoundary — catches React render errors and shows a fallback UI.
 * Wraps every screen to prevent one broken screen from crashing the app.
 */
export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: { componentStack: string }) {
    console.error("[ErrorBoundary]", error, info.componentStack);
  }

  render() {
    if (this.state.hasError) {
      return (
        this.props.fallback ?? (
          <div className="min-h-screen flex items-center justify-center bg-gray-50">
            <div className="max-w-md w-full bg-white rounded-xl shadow p-8 text-center">
              <div className="text-4xl mb-4">⚠️</div>
              <h2 className="text-xl font-bold text-gray-800 mb-2">
                Something went wrong
              </h2>
              <p className="text-gray-500 text-sm mb-6">
                {this.state.error?.message ?? "An unexpected error occurred."}
              </p>
              <button
                className="px-5 py-2 bg-brand-600 text-white rounded-lg hover:bg-brand-700 transition"
                onClick={() => {
                  this.setState({ hasError: false, error: null });
                  window.location.href = "/";
                }}
              >
                Start over
              </button>
            </div>
          </div>
        )
      );
    }
    return this.props.children;
  }
}
