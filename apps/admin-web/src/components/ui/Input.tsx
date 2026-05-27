import * as React from 'react';
import { cn } from '../../lib/cn';

export interface InputProps
  extends React.InputHTMLAttributes<HTMLInputElement> {
  /** Render with an error visual state (red border + ring). */
  error?: boolean;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type = 'text', error = false, ...props }, ref) => {
    return (
      <input
        ref={ref}
        type={type}
        aria-invalid={error || undefined}
        className={cn(
          'flex h-10 w-full rounded-md border bg-white px-3 py-2 text-sm text-neutral-900 placeholder:text-neutral-400',
          'ring-offset-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2',
          'disabled:cursor-not-allowed disabled:bg-neutral-50 disabled:text-neutral-500',
          'file:border-0 file:bg-transparent file:text-sm file:font-medium',
          error
            ? 'border-danger-600 focus-visible:ring-danger-600'
            : 'border-neutral-300 focus-visible:ring-primary-600',
          className
        )}
        {...props}
      />
    );
  }
);
Input.displayName = 'Input';
