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
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/atoms/button';
import { Badge } from '@/components/atoms/badge';
import { SidebarUserButton } from './features/auth/sidebar-user-button';

// ─── Navigation Definitions ────────────────────────────────

interface NavItem {
  title: string;
  href: string;
  icon: React.ElementType;
  badge?: string;
}

interface NavSection {
  title: string;
  items: NavItem[];
}

const navSections: NavSection[] = [
  {
    title: 'Main',
    items: [{ title: 'Dashboard', href: '/dashboard', icon: LayoutDashboard }],
  },
  {
    title: 'CRM',
    items: [
      { title: 'Contacts', href: '/crm/contacts', icon: Users },
      { title: 'Deals', href: '/crm/deals', icon: Briefcase },
      { title: 'Pipelines', href: '/crm/pipelines', icon: GitBranch },
    ],
  },
  {
    title: 'Marketing',
    items: [
      { title: 'Campaigns', href: '/marketing/campaigns', icon: Megaphone, badge: 'New' },
      { title: 'AI Suite', href: '/ai-suite', icon: Brain, badge: 'Beta' },
    ],
  },
  {
    title: 'Channels',
    items: [
      { title: 'SEO', href: '/marketing/seo', icon: SearchIcon },
      { title: 'Social', href: '/marketing/social', icon: Share2 },
    ],
  },
  {
    title: 'Analytics',
    items: [
      { title: 'Dashboards', href: '/analytics', icon: BarChart3 },
      { title: 'Reports', href: '/analytics/reports', icon: FileText },
    ],
  },
  {
    title: 'Settings',
    items: [
      { title: 'Settings', href: '/settings', icon: Settings },
      { title: 'Billing', href: '/billing', icon: CreditCard },
      { title: 'Webhooks', href: '/webhooks', icon: Webhook },
    ],
  },
  {
    title: 'Content',
    items: [
      { title: 'Media Library', href: '/media', icon: ImageIcon },
      { title: 'Knowledge Base', href: '/knowledge', icon: BookOpen },
    ],
  },
];

// ─── Icons ─────────────────────────────────────────────────

export function Sidebar({ collapsed, onToggle }: { collapsed: boolean; onToggle: () => void }) {
  const pathname = usePathname();

  return (
    <aside
      className={cn(
        'fixed inset-y-0 left-0 z-30 flex flex-col border-r bg-card transition-all duration-300',
        collapsed ? 'w-16' : 'w-64'
      )}
    >
      {/* Logo */}
      <div className="flex h-16 items-center justify-between border-b px-4">
        <Link href="/dashboard" className={cn('flex items-center gap-2', collapsed && 'justify-center w-full')}>
          <div className="rounded-lg bg-primary p-1.5">
            <BarChart3 className="h-5 w-5 text-primary-foreground" />
          </div>
          {!collapsed && <span className="font-bold text-lg">Aegis</span>}
        </Link>
        <Button
          variant="ghost"
          size="icon-sm"
          onClick={onToggle}
          className={cn('hidden lg:flex', collapsed && 'hidden')}
        >
          <Menu className="h-4 w-4" />
        </Button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto p-3 space-y-4">
        {navSections.map((section) => (
          <div key={section.title}>
            {!collapsed && (
              <p className="px-2 mb-1 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                {section.title}
              </p>
            )}
            <div className="space-y-1">
              {section.items.map((item) => {
                const isActive = pathname === item.href || pathname?.startsWith(item.href + '/');
                const Icon = item.icon;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={cn(
                      'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                      isActive
                        ? 'bg-primary/10 text-primary'
                        : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground',
                      collapsed && 'justify-center px-2'
                    )}
                    title={collapsed ? item.title : undefined}
                  >
                    <Icon className="h-5 w-5 shrink-0" />
                    {!collapsed && (
                      <>
                        <span className="flex-1">{item.title}</span>
                        {item.badge && (
                          <Badge variant="secondary" className="text-[10px] px-1.5 py-0">
                            {item.badge}
                          </Badge>
                        )}
                      </>
                    )}
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      {/* User footer */}
      {collapsed ? (
        <div className="border-t p-3 flex justify-center">
          <SidebarUserButton collapsed />
        </div>
      ) : (
        <div className="border-t p-3">
          <SidebarUserButton collapsed={false} />
        </div>
      )}
    </aside>
  );
}
