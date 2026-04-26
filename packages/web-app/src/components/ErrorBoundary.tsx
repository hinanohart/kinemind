/**
 * ErrorBoundary — catches render errors (including WebGL failures).
 * Usage:
 *   <ErrorBoundary>
 *     <StripViewer3D />
 *   </ErrorBoundary>
 */

import { Component, type ErrorInfo, type ReactNode } from "react";

interface Props {
  readonly children: ReactNode;
  /** Optional custom fallback UI. Defaults to built-in alert card. */
  readonly fallback?: ReactNode;
}

interface State {
  readonly hasError: boolean;
  readonly errorMessage: string;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, errorMessage: "" };
  }

  static getDerivedStateFromError(error: unknown): State {
    const message = error instanceof Error ? error.message : String(error);
    return { hasError: true, errorMessage: message };
  }

  override componentDidCatch(error: unknown, info: ErrorInfo): void {
    console.error("[ErrorBoundary] Caught render error:", error, info.componentStack);
  }

  private handleReset = (): void => {
    this.setState({ hasError: false, errorMessage: "" });
  };

  override render(): ReactNode {
    if (!this.state.hasError) {
      return this.props.children;
    }

    if (this.props.fallback) {
      return this.props.fallback;
    }

    return (
      <div
        role="alert"
        className="flex flex-col items-center justify-center h-full bg-slate-900 text-slate-400 text-sm p-6 gap-4 text-center"
      >
        <p className="font-semibold text-slate-200">Something went wrong</p>
        <p className="text-xs text-slate-500 max-w-xs">
          {this.state.errorMessage || "An unexpected error occurred. This may be a WebGL issue."}
        </p>
        <button
          type="button"
          onClick={this.handleReset}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-500 active:bg-blue-700 text-white text-sm font-medium rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-blue-400 focus:ring-offset-2 focus:ring-offset-slate-900"
        >
          Try again
        </button>
      </div>
    );
  }
}
