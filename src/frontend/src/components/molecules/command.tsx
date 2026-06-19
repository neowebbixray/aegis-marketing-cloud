'use client';

import * as React from 'react';
import { Dialog, DialogContent } from '@/components/molecules/dialog';
import { cn } from '@/lib/utils';
import { Search } from 'lucide-react';

interface CommandDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  children: React.ReactNode;
}

function CommandDialog({ open, onOpenChange, children }: CommandDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="overflow-hidden p-0 shadow-lg max-w-[550px]">
        <Command className="[&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:font-medium [&_[cmdk-group-heading]]:text-muted-foreground [&_[cmdk-group]:not([hidden])_~[cmdk-group]]:pt-0 [&_[cmdk-group]]:px-2 [&_[cmdk-input-wrapper]_svg]:h-5 [&_[cmdk-input-wrapper]_svg]:w-5 [&_[cmdk-input]]:h-12 [&_[cmdk-item]]:px-2 [&_[cmdk-item]]:py-3 [&_[cmdk-item]_svg]:h-5 [&_[cmdk-item]_svg]:w-5">
          {children}
        </Command>
      </DialogContent>
    </Dialog>
  );
}

// ─── Command Primitive (lightweight, no external dep) ─────

interface CommandProps extends React.HTMLAttributes<HTMLDivElement> {}

function Command({ className, ...props }: CommandProps) {
  return (
    <div
      className={cn(
        'flex h-full w-full flex-col overflow-hidden rounded-md bg-popover text-popover-foreground',
        className
      )}
      {...props}
    />
  );
}

interface CommandInputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  wrapperClassName?: string;
}

const CommandInput = React.forwardRef<HTMLInputElement, CommandInputProps>(
  ({ className, wrapperClassName, ...props }, ref) => (
    <div
      className={cn('flex items-center border-b px-3', wrapperClassName)}
      cmdk-input-wrapper=""
    >
      <Search className="mr-2 h-4 w-4 shrink-0 opacity-50" />
      <input
        ref={ref}
        className={cn(
          'flex h-11 w-full rounded-md bg-transparent py-3 text-sm outline-none placeholder:text-muted-foreground disabled:cursor-not-allowed disabled:opacity-50',
          className
        )}
        {...props}
      />
    </div>
  )
);
CommandInput.displayName = 'CommandInput';

interface CommandListProps extends React.HTMLAttributes<HTMLDivElement> {}

function CommandList({ className, ...props }: CommandListProps) {
  return (
    <div
      className={cn('max-h-[300px] overflow-y-auto overflow-x-hidden', className)}
      {...props}
    />
  );
}

interface CommandEmptyProps extends React.HTMLAttributes<HTMLDivElement> {}

function CommandEmpty({ className, ...props }: CommandEmptyProps) {
  return (
    <div
      className={cn('py-6 text-center text-sm text-muted-foreground', className)}
      {...props}
    />
  );
}

interface CommandGroupProps extends React.HTMLAttributes<HTMLDivElement> {
  heading?: string;
}

function CommandGroup({ className, heading, children, ...props }: CommandGroupProps) {
  return (
    <div
      className={cn(
        'overflow-hidden p-1 text-foreground [&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:py-1.5 [&_[cmdk-group-heading]]:text-xs [&_[cmdk-group-heading]]:font-medium [&_[cmdk-group-heading]]:text-muted-foreground',
        className
      )}
      {...props}
    >
      {heading && <div cmdk-group-heading="">{heading}</div>}
      {children}
    </div>
  );
}

interface CommandItemProps extends React.HTMLAttributes<HTMLDivElement> {
  onSelect?: () => void;
  disabled?: boolean;
}

function CommandItem({
  className,
  onSelect,
  disabled,
  children,
  ...props
}: CommandItemProps) {
  return (
    <div
      role="option"
      aria-disabled={disabled}
      data-disabled={disabled}
      onClick={disabled ? undefined : onSelect}
      className={cn(
        'relative flex cursor-default select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none aria-selected:bg-accent aria-selected:text-accent-foreground data-[disabled=true]:pointer-events-none data-[disabled=true]:opacity-50 hover:bg-accent hover:text-accent-foreground cursor-pointer',
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}
CommandItem.displayName = 'CommandItem';

interface CommandShortcutProps extends React.HTMLAttributes<HTMLSpanElement> {}

function CommandShortcut({ className, ...props }: CommandShortcutProps) {
  return (
    <span
      className={cn('ml-auto text-xs tracking-widest text-muted-foreground', className)}
      {...props}
    />
  );
}
CommandShortcut.displayName = 'CommandShortcut';

export {
  Command,
  CommandDialog,
  CommandInput,
  CommandList,
  CommandEmpty,
  CommandGroup,
  CommandItem,
  CommandShortcut,
};
