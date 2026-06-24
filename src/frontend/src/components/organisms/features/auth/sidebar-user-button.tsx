'use client';

import {
  User,
  Settings,
  LogOut,
} from 'lucide-react';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/atoms/avatar';
import { Button } from '@/components/atoms/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/molecules/dropdown-menu';
import { useAuthStore } from '@/stores/auth-store';
import { getInitials } from '@/lib/utils';

export function SidebarUserButton({ collapsed }: { collapsed: boolean }) {
  const user = useAuthStore((s) => s.user);
  const { logout } = useAuthStore();

  if (!user) return null;

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          className={
            collapsed
              ? 'w-full flex justify-center p-2'
              : 'w-full flex items-center gap-3 justify-start px-2'
          }
        >
          <Avatar className="h-8 w-8">
            <AvatarImage src={user.avatar_url ?? undefined} />
            <AvatarFallback>{getInitials(user.display_name ?? '')}</AvatarFallback>
          </Avatar>
          {!collapsed && (
            <div className="flex-1 text-left">
              <p className="text-sm font-medium leading-none">{user.display_name}</p>
              <p className="text-xs text-muted-foreground mt-0.5">{user.email}</p>
            </div>
          )}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" side="top" className="w-56">
        <DropdownMenuLabel>My Account</DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem>
          <User className="mr-2 h-4 w-4" />
          Profile
        </DropdownMenuItem>
        <DropdownMenuItem>
          <Settings className="mr-2 h-4 w-4" />
          Settings
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={logout} className="text-destructive">
          <LogOut className="mr-2 h-4 w-4" />
          Sign Out
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
