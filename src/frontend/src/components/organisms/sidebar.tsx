'use client';

import * as React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  BarChart3,
  Users,
  Briefcase,
  GitBranch,
  Megaphone,
  Brain,
  SearchIcon,
  Share2,
  Settings,
  Menu,
  LayoutDashboard,
  CreditCard,
  Webhook,
  ImageIcon,
  BookOpen,
  FileText,
  SlidersHorizontal,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/atoms/button';
import { Separator } from '@/components/atoms/separator';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/atoms/tooltip';
import { SidebarUserButton } from '@/components/organisms/features/auth/sidebar-user-button';

// ─── Types ────────────────────────────────────────────────

interface NavItem {
  label: string;
  href: string;
  icon: React.ElementType;
  badge?: string;
}

interface NavGroup {
  title: string;
  items: NavItem[];
}

// ─── Navigation Configuration ──────────────────────────────

const navGroups: NavGroup[] = [
  {
    title: 'Overview',
    items: [
      { label: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
    ],
  },
  {
    title: 'CRM',
    items: [
      { label: 'Contacts', href: '/crm/contacts', icon: Users },
      { label: 'Deals', href: '/crm/deals', icon: Briefcase },
      { label: 'Pipelines', href: '/crm/pipelines', icon: GitBranch },
      { label: 'Custom Fields', href: '/crm/custom-fields', icon: SlidersHorizontal },
    ],
  },
  {
    title: 'Marketing',
    items: [
      { label: 'Campaigns', href: '/marketing/campaigns', icon: Megaphone },
      { label: 'Social', href: '/marketing/social', icon: Share2 },
      { label: 'SEO', href: '/marketing/seo', icon: SearchIcon },
    ],
  },
  {
    title: 'Analytics',
    items: [
      { label: 'Overview', href: '/analytics', icon: BarChart3 },
      { label: 'Reports', href: '/analytics/reports', icon: FileText },
    ],
  },
  {
    title: 'AI Suite',
    items: [
      { label: 'Playground', href: '/ai-suite', icon: Brain },
    ],
  },
  {
    title: 'Content',
    items: [
      { label: 'Knowledge', href: '/knowledge', icon: BookOpen },
      { label: 'Media', href: '/media', icon: ImageIcon },
    ],
  },
  {
    title: 'Operations',
    items: [
      { label: 'Webhooks', href: '/webhooks', icon: Webhook },
      { label: 'Billing', href: '/billing', icon: CreditCard },
    ],
  },
];

const bottomItems: NavItem[] = [
  { label: 'Settings', href: '/settings', icon: Settings },
];

// ─── Sidebar Component ────────────────────────────────────

export function Sidebar({
  collapsed,
  onToggle,
}: {
  collapsed: boolean;
  onToggle: () => void;
}) {
  const pathname = usePathname();

  const isActive = (href: string) => {
    // Exact match for home; prefix match for sub-routes
    if (href === '/dashboard') return pathname === '/dashboard';
    return pathname.startsWith(href);
  };

  return (
    <aside
      className={cn(
        'fixed left-0 top-0 z-30 flex h-screen flex-col border-r bg-background transition-all duration-300',
        collapsed ? 'w-16' : 'w-64'
      )}
    >
      {/* ── Logo / Brand ── */}
      <div
        className={cn(
          'flex h-16 items-center border-b px-4',
          collapsed ? 'justify-center' : 'justify-between'
        )}
      >
        <Link href="/dashboard" className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground text-sm font-bold">
            AM
          </div>
          {!collapsed && (
            <span className="text-base font-semibold tracking-tight">Aegis</span>
          )}
        </Link>
        <Button
          variant="ghost"
          size="icon"
          onClick={onToggle}
          className="hidden lg:flex h-7 w-7"
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {collapsed ? (
            <ChevronRight className="h-4 w-4" />
          ) : (
            <ChevronLeft className="h-4 w-4" />
          )}
        </Button>
      </div>

      {/* ── Navigation ── */}
      <nav className="flex-1 overflow-y-auto px-2 py-4 scrollbar-thin">
        {navGroups.map((group) => (
          <div key={group.title} className="mb-4">
            {!collapsed && (
              <p className="mb-1 px-2 text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">
                {group.title}
              </p>
            )}
            <ul className="space-y-0.5">
              {group.items.map((item) => {
                const active = isActive(item.href);
                const Icon = item.icon;
                const navLink = (
                  <li>
                    <Link
                      href={item.href}
                      className={cn(
                        'flex items-center gap-3 rounded-lg px-2 py-2 text-sm font-medium transition-colors',
                        active
                          ? 'bg-primary/10 text-primary'
                          : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground',
                        collapsed && 'justify-center px-0'
                      )}
                    >
                      <Icon className="h-5 w-5 shrink-0" />
                      {!collapsed && (
                        <span className="truncate">{item.label}</span>
                      )}
                      {!collapsed && item.badge && (
                        <span className="ml-auto rounded-full bg-primary/10 px-2 py-0.5 text-[11px] font-medium text-primary">
                          {item.badge}
                        </span>
                      )}
                    </Link>
                  </li>
                );

                if (collapsed) {
                  return (
                    <Tooltip key={item.href} delayDuration={300}>
                      <TooltipTrigger asChild>{navLink}</TooltipTrigger>
                      <TooltipContent side="right" className="ml-2">
                        {item.label}
                      </TooltipContent>
                    </Tooltip>
                  );
                }
                return navLink;
              })}
            </ul>
          </div>
        ))}
      </nav>

      {/* ── Bottom Section ── */}
      <div className="border-t px-2 py-3">
        <ul className="space-y-0.5">
          {bottomItems.map((item) => {
            const active = isActive(item.href);
            const Icon = item.icon;
            const navLink = (
              <li key={item.href}>
                <Link
                  href={item.href}
                  className={cn(
                    'flex items-center gap-3 rounded-lg px-2 py-2 text-sm font-medium transition-colors',
                    active
                      ? 'bg-primary/10 text-primary'
                      : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground',
                    collapsed && 'justify-center px-0'
                  )}
                >
                  <Icon className="h-5 w-5 shrink-0" />
                  {!collapsed && <span>{item.label}</span>}
                </Link>
              </li>
            );

            if (collapsed) {
              return (
                <Tooltip key={item.href} delayDuration={300}>
                  <TooltipTrigger asChild>{navLink}</TooltipTrigger>
                  <TooltipContent side="right" className="ml-2">
                    {item.label}
                  </TooltipContent>
                </Tooltip>
              );
            }
            return navLink;
          })}
        </ul>

        {!collapsed && <Separator className="my-2" />}
        <SidebarUserButton collapsed={collapsed} />
      </div>
    </aside>
  );
}
