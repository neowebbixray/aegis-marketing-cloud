'use client';

// Re-export sonner as our toast system
import { toast } from 'sonner';

export { toast };

// shadcn-compatible toast component wrapper
import * as React from 'react';
import { cn } from '@/lib/utils';

interface ToastProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'destructive' | 'success';
}

function Toast({ className, variant = 'default', ...props }: ToastProps) {
  return (
    <div
      className={cn(
        'group pointer-events-auto relative flex w-full items-center justify-between space-x-4 overflow-hidden rounded-md border p-6 shadow-lg transition-all',
        {
          'border-border bg-background text-foreground': variant === 'default',
          'border-destructive bg-destructive text-destructive-foreground': variant === 'destructive',
          'border-success-500 bg-success-50 text-success-900 dark:bg-success-950 dark:text-success-100':
            variant === 'success',
        },
        className
      )}
      {...props}
    />
  );
}

export { Toast };
