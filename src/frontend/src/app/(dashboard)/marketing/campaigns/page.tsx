'use client';

import { useState } from 'react';
import {
  Megaphone,
  Plus,
  MoreHorizontal,
  Copy,
  Play,
  Pause,
  BarChart3,
  Mail,
  Globe,
  Share2,
  Calendar,
  Filter,
} from 'lucide-react';
import { Button } from '@/components/atoms/button';
import { Badge } from '@/components/atoms/badge';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/molecules/card';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/molecules/table';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/molecules/select';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/molecules/dropdown-menu';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/molecules/dialog';
import { Input } from '@/components/atoms/input';
import { Label } from '@/components/atoms/label';
import { Skeleton } from '@/components/atoms/skeleton';
import { formatDate, capitalize } from '@/lib/utils';
import { toast } from 'sonner';

// ─── Mock Data ────────────────────────────────────────────

type CampaignStatus = 'draft' | 'active' | 'paused' | 'completed' | 'archived';
type CampaignChannel = 'email' | 'social' | 'search' | 'display' | 'landing_page';

interface Campaign {
  id: string;
  name: string;
  description: string;
  channel: CampaignChannel;
  status: CampaignStatus;
  budget: number;
  spent: number;
  impressions: number;
  clicks: number;
  conversions: number;
  starts_at: string;
  ends_at?: string;
}

const mockCampaigns: Campaign[] = [
  { id: '1', name: 'Q2 Newsletter Welcome Series', description: 'Drip campaign for new subscribers', channel: 'email', status: 'active', budget: 5000, spent: 2340, impressions: 45000, clicks: 3200, conversions: 412, starts_at: '2026-04-01T00:00:00Z', ends_at: '2026-06-30T00:00:00Z' },
  { id: '2', name: 'Summer Sale — Social Push', description: 'Instagram + LinkedIn ad campaign', channel: 'social', status: 'active', budget: 12000, spent: 5800, impressions: 128000, clicks: 8900, conversions: 1024, starts_at: '2026-05-15T00:00:00Z' },
  { id: '3', name: 'Brand Awareness — Display', description: 'Programmatic display network', channel: 'display', status: 'draft', budget: 8000, spent: 0, impressions: 0, clicks: 0, conversions: 0, starts_at: '2026-07-01T00:00:00Z' },
  { id: '4', name: 'Product Launch Landing Page', description: 'New product feature landing page', channel: 'landing_page', status: 'draft', budget: 3000, spent: 0, impressions: 0, clicks: 0, conversions: 0, starts_at: '2026-06-20T00:00:00Z' },
  { id: '5', name: 'Q1 Retargeting Campaign', description: 'Website visitor retargeting', channel: 'search', status: 'completed', budget: 6000, spent: 5900, impressions: 94000, clicks: 5100, conversions: 687, starts_at: '2026-01-01T00:00:00Z', ends_at: '2026-03-31T00:00:00Z' },
  { id: '6', name: 'Email Re-engagement Series', description: 'Win-back inactive subscribers', channel: 'email', status: 'paused', budget: 4000, spent: 1800, impressions: 32000, clicks: 1200, conversions: 89, starts_at: '2026-03-01T00:00:00Z' },
];

const statusColors: Record<CampaignStatus, string> = {
  draft: 'bg-muted text-muted-foreground',
  active: 'bg-success-100 text-success-800 dark:bg-success-900 dark:text-success-100',
  paused: 'bg-warning-100 text-warning-800 dark:bg-warning-900 dark:text-warning-100',
  completed: 'bg-info-100 text-info-800 dark:bg-info-900 dark:text-info-100',
  archived: 'bg-destructive/10 text-destructive',
};

const channelIcons: Record<CampaignChannel, React.ElementType> = {
  email: Mail,
  social: Share2,
  search: BarChart3,
  display: Globe,
  landing_page: Globe,
};

export default function CampaignsPage() {
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [form, setForm] = useState({ name: '', description: '', channel: 'email' as CampaignChannel, budget: '' });

  // Use mock data — backend service not yet implemented
  const campaigns = mockCampaigns;
  const isLoading = false;

  const filtered = statusFilter === 'all'
    ? campaigns
    : campaigns.filter((c) => c.status === statusFilter);

  const stats = {
    active: campaigns.filter((c) => c.status === 'active').length,
    totalBudget: campaigns.reduce((s, c) => s + c.budget, 0),
    totalSpent: campaigns.reduce((s, c) => s + c.spent, 0),
    totalConversions: campaigns.reduce((s, c) => s + c.conversions, 0),
  };

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Campaigns</h1>
          <p className="text-muted-foreground mt-1">
            Create, manage, and analyze your marketing campaigns
          </p>
        </div>
        <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="mr-2 h-4 w-4" />
              New Campaign
            </Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-[500px]">
            <DialogHeader>
              <DialogTitle>Create Campaign</DialogTitle>
              <DialogDescription>Set up a new marketing campaign</DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="name">Campaign Name</Label>
                <Input id="name" placeholder="Q3 Promotional Campaign" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="description">Description</Label>
                <Input id="description" placeholder="Brief description of the campaign" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
              </div>
              <div className="space-y-2">
                <Label>Channel</Label>
                <Select value={form.channel} onValueChange={(v: CampaignChannel) => setForm({ ...form, channel: v })}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select channel" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="email">Email</SelectItem>
                    <SelectItem value="social">Social Media</SelectItem>
                    <SelectItem value="search">Search</SelectItem>
                    <SelectItem value="display">Display</SelectItem>
                    <SelectItem value="landing_page">Landing Page</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="budget">Budget ($)</Label>
                <Input id="budget" type="number" placeholder="5000" value={form.budget} onChange={(e) => setForm({ ...form, budget: e.target.value })} />
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setCreateDialogOpen(false)}>Cancel</Button>
              <Button onClick={() => { toast.success('Campaign created (mock)'); setCreateDialogOpen(false); }}>Create Campaign</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {/* Stats cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Campaigns</CardTitle>
            <Megaphone className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.active}</div>
            <p className="text-xs text-muted-foreground">Currently running</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Budget</CardTitle>
            <BarChart3 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">${stats.totalBudget.toLocaleString()}</div>
            <p className="text-xs text-muted-foreground">${stats.totalSpent.toLocaleString()} spent</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Conversions</CardTitle>
            <BarChart3 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.totalConversions.toLocaleString()}</div>
            <p className="text-xs text-muted-foreground">All campaigns</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">ROI</CardTitle>
            <BarChart3 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {stats.totalSpent > 0
                ? `${((stats.totalConversions * 50 - stats.totalSpent) / stats.totalSpent * 100).toFixed(0)}%`
                : '—'}
            </div>
            <p className="text-xs text-muted-foreground">Estimated return</p>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3">
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-[160px]">
            <Filter className="mr-2 h-4 w-4" />
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Statuses</SelectItem>
            <SelectItem value="draft">Draft</SelectItem>
            <SelectItem value="active">Active</SelectItem>
            <SelectItem value="paused">Paused</SelectItem>
            <SelectItem value="completed">Completed</SelectItem>
            <SelectItem value="archived">Archived</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Campaigns table */}
      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Campaign</TableHead>
                <TableHead className="hidden md:table-cell">Channel</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="hidden lg:table-cell">Budget</TableHead>
                <TableHead className="hidden lg:table-cell">Spent</TableHead>
                <TableHead className="hidden xl:table-cell">Conversions</TableHead>
                <TableHead className="hidden lg:table-cell">Start</TableHead>
                <TableHead className="w-[50px]"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                Array.from({ length: 4 }).map((_, i) => (
                  <TableRow key={i}>
                    {Array.from({ length: 7 }).map((_, j) => (
                      <TableCell key={j}><Skeleton className="h-5 w-20" /></TableCell>
                    ))}
                  </TableRow>
                ))
              ) : filtered.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={8} className="text-center py-12 text-muted-foreground">
                    No campaigns found
                  </TableCell>
                </TableRow>
              ) : (
                filtered.map((campaign) => {
                  const ChannelIcon = channelIcons[campaign.channel];
                  return (
                    <TableRow key={campaign.id} className="cursor-pointer hover:bg-muted/50">
                      <TableCell>
                        <div>
                          <p className="font-medium">{campaign.name}</p>
                          <p className="text-xs text-muted-foreground">{campaign.description}</p>
                        </div>
                      </TableCell>
                      <TableCell className="hidden md:table-cell">
                        <div className="flex items-center gap-2">
                          <ChannelIcon className="h-4 w-4 text-muted-foreground" />
                          <span className="text-sm capitalize">{campaign.channel.replace('_', ' ')}</span>
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline" className={statusColors[campaign.status]}>
                          {capitalize(campaign.status)}
                        </Badge>
                      </TableCell>
                      <TableCell className="hidden lg:table-cell">${campaign.budget.toLocaleString()}</TableCell>
                      <TableCell className="hidden lg:table-cell">${campaign.spent.toLocaleString()}</TableCell>
                      <TableCell className="hidden xl:table-cell">{campaign.conversions.toLocaleString()}</TableCell>
                      <TableCell className="hidden lg:table-cell text-sm text-muted-foreground">
                        {formatDate(campaign.starts_at)}
                      </TableCell>
                      <TableCell>
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
                            <Button variant="ghost" size="icon-sm">
                              <MoreHorizontal className="h-4 w-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuItem><Play className="mr-2 h-4 w-4" /> {campaign.status === 'draft' ? 'Launch' : 'Resume'}</DropdownMenuItem>
                            <DropdownMenuItem><Pause className="mr-2 h-4 w-4" /> Pause</DropdownMenuItem>
                            <DropdownMenuItem><Copy className="mr-2 h-4 w-4" /> Duplicate</DropdownMenuItem>
                            <DropdownMenuSeparator />
                            <DropdownMenuItem className="text-destructive">
                              Archive
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </TableCell>
                    </TableRow>
                  );
                })
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
