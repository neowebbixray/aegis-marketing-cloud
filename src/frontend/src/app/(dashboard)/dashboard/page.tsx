'use client';

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/molecules/card';
import { Button } from '@/components/atoms/button';
import { Badge } from '@/components/atoms/badge';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/atoms/avatar';
import {
  Plus,
  Users,
  Megaphone,
  Sparkles,
  TrendingUp,
  DollarSign,
  Target,
  Clock,
  ArrowRight,
  Activity,
} from 'lucide-react';
import { formatDate, formatCurrency } from '@/lib/utils';
import { useAuthStore } from '@/stores/auth-store';

// ─── KPI Card ─────────────────────────────────────────────

interface KPICardProps {
  title: string;
  value: string;
  change?: string;
  changeType?: 'positive' | 'negative' | 'neutral';
  icon: React.ElementType;
  description?: string;
}

function KPICard({ title, value, change, changeType = 'neutral', icon: Icon, description }: KPICardProps) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          {title}
        </CardTitle>
        <div className="rounded-lg bg-primary/10 p-2">
          <Icon className="h-4 w-4 text-primary" />
        </div>
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        <div className="flex items-center gap-1 mt-1">
          {change && (
            <span
              className={cn(
                'text-xs font-medium',
                changeType === 'positive' && 'text-success-600',
                changeType === 'negative' && 'text-destructive',
                changeType === 'neutral' && 'text-muted-foreground'
              )}
            >
              {change}
            </span>
          )}
          {description && (
            <span className="text-xs text-muted-foreground">{description}</span>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

function cn(...classes: (string | undefined | null | false)[]) {
  return classes.filter(Boolean).join(' ');
}

// ─── Activity Timeline ────────────────────────────────────

interface TimelineItem {
  id: string;
  type: 'contact' | 'deal' | 'campaign' | 'system' | 'note';
  title: string;
  description: string;
  timestamp: string;
  user?: string;
}

const recentActivities: TimelineItem[] = [
  {
    id: '1',
    type: 'contact',
    title: 'New contact added',
    description: 'Sarah Johnson was added to Contacts',
    timestamp: new Date(Date.now() - 15 * 60000).toISOString(),
    user: 'You',
  },
  {
    id: '2',
    type: 'deal',
    title: 'Deal stage changed',
    description: 'Q4 Enterprise Deal moved to Negotiation',
    timestamp: new Date(Date.now() - 2 * 3600000).toISOString(),
    user: 'You',
  },
  {
    id: '3',
    type: 'campaign',
    title: 'Campaign launched',
    description: 'Summer Sale 2026 is now active',
    timestamp: new Date(Date.now() - 5 * 3600000).toISOString(),
    user: 'System',
  },
  {
    id: '4',
    type: 'note',
    title: 'Note added to deal',
    description: 'Follow-up call scheduled for next week',
    timestamp: new Date(Date.now() - 24 * 3600000).toISOString(),
    user: 'Alex M.',
  },
  {
    id: '5',
    type: 'deal',
    title: 'Deal closed',
    description: 'Acme Corp contract signed — $24,000',
    timestamp: new Date(Date.now() - 48 * 3600000).toISOString(),
    user: 'You',
  },
];

function getActivityIcon(type: TimelineItem['type']) {
  switch (type) {
    case 'contact':
      return Users;
    case 'deal':
      return TrendingUp;
    case 'campaign':
      return Megaphone;
    case 'note':
      return Activity;
    default:
      return Activity;
  }
}

// ─── AI Suggestion Widget ─────────────────────────────────

const aiSuggestions = [
  {
    title: 'Follow up with warm leads',
    description: '5 leads in the "Qualified" stage haven\'t been contacted in 7+ days.',
    action: 'View leads',
  },
  {
    title: 'Optimize email campaigns',
    description: 'Your open rates have dropped 12% this month. Try A/B testing subject lines.',
    action: 'Learn more',
  },
  {
    title: 'Content gap detected',
    description: 'You\'re missing blog content for 3 high-value keywords in your SEO strategy.',
    action: 'View gaps',
  },
];

// ─── Dashboard Page ───────────────────────────────────────

export default function DashboardPage() {
  const user = useAuthStore((s) => s.user);

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">
            Welcome back, {user?.display_name?.split(' ')[0] || 'User'}
          </h1>
          <p className="text-muted-foreground mt-1">
            Here&apos;s what&apos;s happening with your business today.
          </p>
        </div>
        <div className="hidden md:flex items-center gap-2">
          <Button variant="outline" size="sm">
            <Clock className="mr-2 h-4 w-4" />
            Generate Report
          </Button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <KPICard
          title="Today's Tasks"
          value="12"
          change="3 overdue"
          changeType="negative"
          icon={Clock}
        />
        <KPICard
          title="Active Campaigns"
          value="8"
          change="+2 this week"
          changeType="positive"
          icon={Megaphone}
        />
        <KPICard
          title="New Leads"
          value="143"
          change="+12.5% vs last week"
          changeType="positive"
          icon={Target}
        />
        <KPICard
          title="Revenue (MTD)"
          value={formatCurrency(84750)}
          change="+18.2% target"
          changeType="positive"
          icon={DollarSign}
        />
      </div>

      {/* Quick Actions */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card className="bg-primary/5 border-primary/20 hover:bg-primary/10 transition-colors cursor-pointer">
          <CardContent className="flex items-center gap-4 p-6">
            <div className="rounded-lg bg-primary p-3">
              <Users className="h-5 w-5 text-primary-foreground" />
            </div>
            <div className="flex-1">
              <p className="font-semibold">Add Contact</p>
              <p className="text-sm text-muted-foreground">Create a new contact record</p>
            </div>
            <ArrowRight className="h-5 w-5 text-primary" />
          </CardContent>
        </Card>
        <Card className="bg-accent/5 border-accent/20 hover:bg-accent/10 transition-colors cursor-pointer">
          <CardContent className="flex items-center gap-4 p-6">
            <div className="rounded-lg bg-accent p-3">
              <Megaphone className="h-5 w-5 text-accent-foreground" />
            </div>
            <div className="flex-1">
              <p className="font-semibold">New Campaign</p>
              <p className="text-sm text-muted-foreground">Launch a marketing campaign</p>
            </div>
            <ArrowRight className="h-5 w-5 text-accent" />
          </CardContent>
        </Card>
        <Card className="bg-success/5 border-success/20 hover:bg-success/10 transition-colors cursor-pointer">
          <CardContent className="flex items-center gap-4 p-6">
            <div className="rounded-lg bg-success-500 p-3">
              <Sparkles className="h-5 w-5 text-white" />
            </div>
            <div className="flex-1">
              <p className="font-semibold">Generate Content</p>
              <p className="text-sm text-muted-foreground">AI-powered content creation</p>
            </div>
            <ArrowRight className="h-5 w-5 text-success-600" />
          </CardContent>
        </Card>
      </div>

      {/* Two-column layout */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* Activity Timeline */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-lg">Recent Activity</CardTitle>
            <CardDescription>Latest actions across your workspace</CardDescription>
          </CardHeader>
          <CardContent className="space-y-0">
            {recentActivities.map((activity, index) => {
              const Icon = getActivityIcon(activity.type);
              return (
                <div key={activity.id} className="flex gap-4 py-3">
                  <div className="flex flex-col items-center">
                    <div className="rounded-full border p-2 bg-background">
                      <Icon className="h-4 w-4 text-muted-foreground" />
                    </div>
                    {index < recentActivities.length - 1 && (
                      <div className="w-px flex-1 bg-border mt-2" />
                    )}
                  </div>
                  <div className="flex-1 space-y-1">
                    <div className="flex items-center justify-between">
                      <p className="text-sm font-medium">{activity.title}</p>
                      <span className="text-xs text-muted-foreground">
                        {formatDate(activity.timestamp)}
                      </span>
                    </div>
                    <p className="text-sm text-muted-foreground">{activity.description}</p>
                  </div>
                </div>
              );
            })}
          </CardContent>
        </Card>

        {/* AI Suggestions */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-primary" />
              <CardTitle className="text-lg">AI Suggestions</CardTitle>
            </div>
            <CardDescription>Smart recommendations for your business</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {aiSuggestions.map((suggestion) => (
              <div key={suggestion.title} className="space-y-2 p-3 rounded-lg bg-muted/50">
                <p className="text-sm font-medium">{suggestion.title}</p>
                <p className="text-xs text-muted-foreground">{suggestion.description}</p>
                <Button variant="link" size="sm" className="h-auto p-0 text-xs">
                  {suggestion.action} →
                </Button>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
