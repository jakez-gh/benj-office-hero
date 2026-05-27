import * as React from 'react';
import { cn } from '../../lib/cn';

export type SkeletonProps = React.HTMLAttributes<HTMLDivElement>;

export const Skeleton = React.forwardRef<HTMLDivElement, SkeletonProps>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn('animate-pulse-soft rounded-md bg-neutral-200', className)}
      {...props}
    />
  )
);
Skeleton.displayName = 'Skeleton';
