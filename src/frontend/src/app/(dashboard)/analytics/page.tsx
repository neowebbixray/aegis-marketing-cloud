'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import {
  Plus,
  BarChart3,
  LayoutDashboard,
  MoreHorizontal,
  Pencil,
  Trash2,
  Copy,
  Eye,
  LineChart,
  Table2,
  PieChart,
  AreaChart,
  TrendingUp,
} from 'lucide-react';
import { Button } from '@/components/atoms/button';
import { Badge } from '@/components/atoms/badge';
import { Input } from '@/components/atoms/input';
import { Label } from '@/components/atoms/label';
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/molecules/card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/molecules/dialog';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/molecules/dropdown-menu';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/molecules/select';
import { Skeleton } from '@/components/atoms/skeleton';
import { toast } from 'sonner';
import { analyticsApi } from '@/lib/api/analytics';
import { formatDate } from '@/lib/utils';
import type { Dashboard, DashboardType } from '@/lib/api/analytics';

// ─── Constants ──────────────────────────────────────────────

const dashboardTypes: DashboardType[] = ['main', 'marketing', 'sales', 'email', 'custom'];

const typeConfig: Record<DashboardType, { label: string; icon: React.ElementType; color: string }> = {
  main: { label: 'Main', icon: LayoutDashboard, color: 'bg-primary/10 text-primary' },
  marketing: { label: 'Marketing', icon: TrendingUp, color: 'bg-accent/10 text-accent-foreground' },
  sales: { label: 'Sales', icon: BarChart3, color: 'bg-success-100 text-success-800 dark:bg-success-900 dark:text-success-100' },
  email: { label: 'Email', icon: LineChart, color: 'bg-warning-100 text-warning-800 dark:bg-warning-900 dark:text-warning-100' },
  custom: { label: 'Custom', icon: LayoutDashboard, color: 'bg-muted text-muted-foreground' },
};

const widgetTypeIcons: Record<string, React.ElementType> = {
  chart: LineChart,
  metric: TrendingUp,
  table: Table2,
  funnel: PieChart,
  map: AreaChart,
};

// ─── Create Dashboard Dialog ────────────────────────────────

function CreateDashboardDialog({
  open,
  onOpenChange,
  onCreated,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCreated: () => void;
}) {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [type, setType] = useState<DashboardType>('custom');
  const [creating, setCreating] = useState(false);

  const handleCreate = async () => {
    if (!name.trim()) {
      toast.error('Dashboard name is required');
      return;
    }

    setCreating(true);
    try {
      await analyticsApi.createDashboard({
        name: name.trim(),
        description: description.trim() || undefined,
        type,
      });
      toast.success('Dashboard created successfully');
      onOpenChange(false);
      setName('');
      setDescription('');
      setType('custom');
      onCreated();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to create dashboard');
    } finally {
      setCreating(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[450px]">
        <DialogHeader>
          <DialogTitle>New Dashboard</DialogTitle>
          <DialogDescription>
            Create a new analytics dashboard to visualize your metrics
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 py-4">
          <div className="space-y-2">
            <Label htmlFor="name">Dashboard Name *</Label>
            <Input
              id="name"
              placeholder="e.g., Weekly Performance"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="desc">Description</Label>
            <Input
              id="desc"
              placeholder="Optional description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="type">Dashboard Type</Label>
            <Select value={type} onValueChange={(v) => setType(v as DashboardType)}>
              <SelectTrigger id="type">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {dashboardTypes.map((t) => (
                  <SelectItem key={t} value={t}>
                    {typeConfig[t].label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleCreate} disabled={creating}>
            {creating ? 'Creating...' : 'Create Dashboard'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ─── Analytics Page ─────────────────────────────────────────

export default function AnalyticsPage() {
  const router = useRouter();
  const [dashboards, setDashboards] = useState<Dashboard[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);

  const fetchDashboards = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await analyticsApi.listDashboards();
      setDashboards(res.data || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load dashboards');
      setDashboards([]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDashboards();
  }, [fetchDashboards]);

  const handleDelete = async (id: string) => {
    try {
      await analyticsApi.deleteDashboard(id);
      toast.success('Dashboard deleted');
      setDeleteConfirmId(null);
      fetchDashboards();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to delete dashboard');
    }
  };

  const filteredDashboards = dashboards.filter((d) =>
    !search ||
    d.name.toLowerCase().includes(search.toLowerCase()) ||
    (d.description && d.description.toLowerCase().includes(search.toLowerCase()))
  );

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Analytics</h1>
          <p className="text-muted-foreground mt-1">
            Create and manage analytics dashboards for your business metrics
          </p>
        </div>
        <Button onClick={() => setCreateDialogOpen(true)}>
          <Plus className="mr-2 h-4 w-4" />
          New Dashboard
        </Button>
      </div>

      {/* Search */}
      <div className="relative max-w-sm">
        <Input
          placeholder="Search dashboards..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      {/* Dashboard Grid */}
      {isLoading ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Card key={i}>
              <CardHeader>
                <Skeleton className="h-5 w-32" />
                <Skeleton className="h-4 w-48 mt-2" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-4 w-24" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : error ? (
        <Card>
          <CardContent className="flex flex-col items-center py-12">
            <p className="text-destructive mb-2">{error}</p>
            <Button variant="outline" onClick={fetchDashboards}>
              Retry
            </Button>
          </CardContent>
        </Card>
      ) : filteredDashboards.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center py-16">
            <BarChart3 className="h-12 w-12 text-muted-foreground mb-4" />
            <p className="text-lg font-medium text-muted-foreground mb-1">
              {search ? 'No dashboards match your search' : 'No dashboards yet'}
            </p>
            <p className="text-sm text-muted-foreground mb-4">
              {search ? 'Try a different search term' : 'Create your first analytics dashboard'}
            </p>
            {!search && (
              <Button onClick={() => setCreateDialogOpen(true)}>
                <Plus className="mr-2 h-4 w-4" />
                Create Dashboard
              </Button>
            )}
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {filteredDashboards.map((dashboard) => {
            const TypeIcon = typeConfig[dashboard.type]?.icon || LayoutDashboard;
            const typeClass = typeConfig[dashboard.type]?.color || 'bg-muted text-muted-foreground';
            const widgetCount = dashboard.widgets?.length || 0;
            const chartCount = dashboard.widgets?.filter((w) => w.type === 'chart' || w.type === 'metric').length || 0;

            return (
              <Card
                key={dashboard.id}
                className="cursor-pointer hover:shadow-md transition-shadow"
                onClick={() => router.push(`/analytics/dashboards/${dashboard.id}`)}
              >
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-2">
                      <div className={`rounded-lg p-2 ${typeClass}`}>
                        <TypeIcon className="h-4 w-4" />
                      </div>
                      <div>
                        <CardTitle className="text-base">{dashboard.name}</CardTitle>
                        {dashboard.description && (
                          <CardDescription className="text-xs mt-0.5 line-clamp-2">
                            {dashboard.description}
                          </CardDescription>
                        )}
                      </div>
                    </div>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
                        <Button variant="ghost" size="icon-sm">
                          <MoreHorizontal className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuLabel>Actions</DropdownMenuLabel>
                        <DropdownMenuItem onClick={() => router.push(`/analytics/dashboards/${dashboard.id}`)}>
                          <Eye className="mr-2 h-4 w-4" />
                          View
                        </DropdownMenuItem>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem
                          className="text-destructive"
                          onClick={(e) => {
                            e.stopPropagation();
                            setDeleteConfirmId(dashboard.id);
                          }}
                        >
                          <Trash2 className="mr-2 h-4 w-4" />
                          Delete
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </div>
                </CardHeader>
                <CardContent className="pb-3">
                  <div className="flex items-center gap-4 text-sm text-muted-foreground">
                    <span className="flex items-center gap-1">
                      <LayoutDashboard className="h-3.5 w-3.5" />
                      {widgetCount} widget{widgetCount !== 1 ? 's' : ''}
                    </span>
                    <span className="flex items-center gap-1">
                      <BarChart3 className="h-3.5 w-3.5" />
                      {chartCount} chart{chartCount !== 1 ? 's' : ''}
                    </span>
                  </div>
                </CardContent>
                <CardFooter className="border-t pt-3">
                  <div className="flex items-center justify-between w-full text-xs text-muted-foreground">
                    <Badge variant="outline" className={typeClass}>
                      <TypeIcon className="h-3 w-3 mr-1" />
                      {typeConfig[dashboard.type]?.label || dashboard.type}
                    </Badge>
                    <span>Updated {formatDate(dashboard.updated_at)}</span>
                  </div>
                </CardFooter>
              </Card>
            );
          })}
        </div>
      )}

      {/* Delete Confirmation Dialog */}
      <Dialog
        open={!!deleteConfirmId}
        onOpenChange={(open) => !open && setDeleteConfirmId(null)}
      >
        <DialogContent className="sm:max-w-[400px]">
          <DialogHeader>
            <DialogTitle>Delete Dashboard</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete this dashboard? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteConfirmId(null)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={() => deleteConfirmId && handleDelete(deleteConfirmId)}
            >
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Create Dashboard Dialog */}
      <CreateDashboardDialog
        open={createDialogOpen}
        onOpenChange={setCreateDialogOpen}
        onCreated={fetchDashboards}
      />
    </div>
  );
}
