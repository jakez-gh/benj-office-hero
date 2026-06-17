import React from 'react';
import { cn } from '../../lib/cn';
import { Alert } from './Alert';

function isNetworkError(msg: string): boolean {
  return /failed to fetch|network error/i.test(msg);
}

interface ErrorBannerProps {
  error: string;
  className?: string;
}

/**
 * Renders an error as a destructive alert, unless the error is a network-level
 * failure (backend unreachable), in which case it shows a softer amber warning.
 */
export const ErrorBanner: React.FC<ErrorBannerProps> = ({ error, className }) => {
  if (isNetworkError(error)) {
    return (
      <Alert variant="warning" className={cn('mb-4', className)}>
        Service temporarily unavailable &mdash; we&rsquo;ll reconnect automatically.
      </Alert>
    );
  }
  return (
    <Alert variant="destructive" role="alert" className={cn('mb-4', className)}>
      {error}
    </Alert>
  );
};
