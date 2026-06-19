// ─── Atoms Index ──────────────────────────────────────────────
// Atomic Design — primitive, single-purpose UI building blocks.
// Each atom should have zero knowledge of business logic.

export { Button, buttonVariants } from './button';
export type { ButtonProps } from './button';

export { Input } from './input';
export type { InputProps } from './input';

export { Label } from './label';

export { Avatar, AvatarImage, AvatarFallback } from './avatar';

export { Badge, badgeVariants } from './badge';
export type { BadgeProps } from './badge';

export { Separator } from './separator';

export { Textarea } from './textarea';
export type { TextareaProps } from './textarea';

export { Skeleton } from './skeleton';

export { Switch } from './switch';

export {
  Tooltip,
  TooltipTrigger,
  TooltipContent,
  TooltipProvider,
} from './tooltip';
