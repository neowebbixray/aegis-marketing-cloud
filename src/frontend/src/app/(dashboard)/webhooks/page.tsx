'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import {
  Plus,
  Search,
  Filter,
  MoreHorizontal,
  ChevronLeft,
  ChevronRight,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  RefreshCw,
  Trash2,
  Copy,
  Eye,
} from 'lucide-react';
import { Webhook as WebhookIcon } from 'lucide-react';
import { Button } from '@/components/atoms/button';
import { Badge } from '@/components/atoms/badge';
import { Input } from '@/components/atoms/input';
import { Label } from '@/components/atoms/label';
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
  DropdownMenuLabel,
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
import { Switch } from '@/components/atoms/switch';
import { Skeleton } from '@/components/atoms/skeleton';
import { toast } from 'sonner';
import { webhooksApi } from '@/lib/api/webhooks';
import { formatDate, formatDateTime } from '@/lib/utils';
import type { Webhook, WebhookEvent, WebhookStatus } from '@/lib/api/webhooks';

// ─── Helpers ────────────────────────────────────────────────

const statusConfig: Record<WebhookStatus, { label: string; icon: React.ElementType; className: string }> = {
  active: { label: 'Active', icon: CheckCircle2, className: 'bg-success-100 text-success-800 dark:bg-success-900 dark:text-success-100' },
  inactive: { label: 'Inactive', icon: XCircle, className: 'bg-muted text-muted-foreground' },
  disabled: { label: 'Failing', icon: AlertTriangle, className: 'bg-destructive/10 text-destructive' },
};

const allEvents: WebhookEvent[] = [
  'contact.created', 'contact.updated', 'contact.deleted',
  'deal.created', 'deal.updated', 'deal.deleted',
  'pipeline.stage.changed',
  'invoice.paid', 'invoice.overdue',
  'subscription.updated', 'subscription.canceled',
  'campaign.sent', 'campaign.completed',
  'form.submitted', 'media.uploaded',
  'ai.generation.completed',
];

// ─── Create Webhook Dialog ───────────────────────────────────

interface CreateWebhookForm {
  name: string;
  url: string;
  description: string;
  events: WebhookEvent[];
}

const emptyForm: CreateWebhookForm = {
  name: '',
  url: '',
  description: '',
  events: [],
};

function CreateWebhookDialog({
  open,
  onOpenChange,
  onCreated,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCreated: () => void;
}) {
  const [form, setForm] = useState<CreateWebhookForm>(emptyForm);
  const [creating, setCreating] = useState(false);

  const updateField = (field: keyof CreateWebhookForm, value: string | WebhookEvent[]) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const toggleEvent = (event: WebhookEvent) => {
    setForm((prev) => ({
      ...prev,
      events: prev.events.includes(event)
        ? prev.events.filter((e) => e !== event)
        : [...prev.events, event],
    }));
  };

  const handleCreate = async () => {
    if (!form.name || !form.url) {
      toast.error('Name and URL are required');
      return;
    }
    if (form.events.length === 0) {
      toast.error('Select at least one event');
      return;
    }

    setCreating(true);
    try {
      await webhooksApi.create({
        name: form.name,
        url: form.url,
        events: form.events,
        description: form.description || undefined,
      });
      toast.success('Webhook created successfully');
      onOpenChange(false);
      setForm(emptyForm);
      onCreated();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to create webhook');
    } finally {
      setCreating(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[600px] max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Create Webhook</DialogTitle>
          <DialogDescription>
            Register a new webhook endpoint to receive real-time events
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 py-4">
          <div className="space-y-2">
            <Label htmlFor="name">Name *</Label>
            <Input
              id="name"
              placeholder="My Webhook"
              value={form.name}
              onChange={(e) => updateField('name', e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="url">Payload URL *</Label>
            <Input
              id="url"
              placeholder="https://example.com/webhook"
              value={form.url}
              onChange={(e) => updateField('url', e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="description">Description</Label>
            <Input
              id="description"
              placeholder="Optional description"
              value={form.description}
              onChange={(e) => updateField('description', e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label>Events *</Label>
            <div className="grid grid-cols-2 gap-2 max-h-48 overflow-y-auto border rounded-lg p-3">
              {allEvents.map((event) => (
                <label
                  key={event}
                  className="flex items-center gap-2 text-sm cursor-pointer hover:text-foreground"
                >
                  <input
                    type="checkbox"
                    checked={form.events.includes(event)}
                    onChange={() => toggleEvent(event)}
                    className="rounded border-gray-300"
                  />
                  {event}
                </label>
              ))}
            </div>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleCreate} disabled={creating}>
            {creating ? 'Creating...' : 'Create Webhook'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ─── Webhooks Page ──────────────────────────────────────────

export default function WebhooksPage() {
  const router = useRouter();
  const [webhooks, setWebhooks] = useState<Webhook[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);
  const [togglingIds, setTogglingIds] = useState<Set<string>>(new Set());
  const perPage = 25;

  const fetchWebhooks = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await webhooksApi.list({
        page,
        limit: perPage,
        status: statusFilter !== 'all' ? (statusFilter as WebhookStatus) : undefined,
      });
      setWebhooks(res.data);
      setTotal(res.meta.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load webhooks');
      setWebhooks([]);
    } finally {
      setIsLoading(false);
    }
  }, [page, statusFilter]);

  useEffect(() => {
    fetchWebhooks();
  }, [fetchWebhooks]);

  const handleToggle = async (webhook: Webhook) => {
    const newStatus = webhook.status === 'active' ? 'inactive' : 'active';
    setTogglingIds((prev) => new Set(prev).add(webhook.id));
    try {
      await webhooksApi.toggle(webhook.id, newStatus === 'active');
      toast.success(`Webhook ${newStatus === 'active' ? 'enabled' : 'disabled'}`);
      fetchWebhooks();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to toggle webhook');
    } finally {
      setTogglingIds((prev) => {
        const next = new Set(prev);
        next.delete(webhook.id);
        return next;
      });
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await webhooksApi.delete(id);
      toast.success('Webhook deleted');
      setDeleteConfirmId(null);
      fetchWebhooks();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to delete webhook');
    }
  };

  const filteredWebhooks = webhooks.filter((w) =>
    !search || w.name.toLowerCase().includes(search.toLowerCase()) ||
    w.url.toLowerCase().includes(search.toLowerCase())
  );

  const totalPages = Math.ceil(total / perPage);

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Webhooks</h1>
          <p className="text-muted-foreground mt-1">
            Manage webhook endpoints and monitor deliveries
          </p>
        </div>
        <Button onClick={() => setCreateDialogOpen(true)}>
          <Plus className="mr-2 h-4 w-4" />
          Create Webhook
        </Button>
      </div>

      {/* Search + Filters */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search webhooks..."
            className="pl-9"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
          />
        </div>
        <Select
          value={statusFilter}
          onValueChange={(v) => {
            setStatusFilter(v);
            setPage(1);
          }}
        >
          <SelectTrigger className="w-[150px]">
            <Filter className="mr-2 h-4 w-4" />
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Status</SelectItem>
            <SelectItem value="active">Active</SelectItem>
            <SelectItem value="inactive">Inactive</SelectItem>
            <SelectItem value="disabled">Failing</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Webhooks Table */}
      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[250px]">Name</TableHead>
                <TableHead className="hidden md:table-cell">URL</TableHead>
                <TableHead className="hidden lg:table-cell">Events</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="hidden lg:table-cell">Last Delivery</TableHead>
                <TableHead className="w-[180px]">Toggle</TableHead>
                <TableHead className="w-[50px]" />
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                Array.from({ length: 5 }).map((_, i) => (
                  <TableRow key={i}>
                    <TableCell><Skeleton className="h-5 w-32" /></TableCell>
                    <TableCell className="hidden md:table-cell"><Skeleton className="h-5 w-48" /></TableCell>
                    <TableCell className="hidden lg:table-cell"><Skeleton className="h-5 w-24" /></TableCell>
                    <TableCell><Skeleton className="h-5 w-20" /></TableCell>
                    <TableCell className="hidden lg:table-cell"><Skeleton className="h-5 w-28" /></TableCell>
                    <TableCell><Skeleton className="h-5 w-16" /></TableCell>
                    <TableCell><Skeleton className="h-8 w-8 rounded-full" /></TableCell>
                  </TableRow>
                ))
              ) : error ? (
                <TableRow>
                  <TableCell colSpan={7} className="text-center py-12 text-destructive">
                    Failed to load webhooks. Please try again.
                    <Button variant="link" onClick={fetchWebhooks} className="ml-2">
                      Retry
                    </Button>
                  </TableCell>
                </TableRow>
              ) : filteredWebhooks.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} className="text-center py-12 text-muted-foreground">
                    {search || statusFilter !== 'all'
                      ? 'No webhooks match your search'
                      : 'No webhooks yet. Create your first one to get started.'}
                  </TableCell>
                </TableRow>
              ) : (
                filteredWebhooks.map((webhook) => {
                  const StatusIcon = statusConfig[webhook.status]?.icon || CheckCircle2;
                  const statusClass = statusConfig[webhook.status]?.className || '';

                  return (
                    <TableRow
                      key={webhook.id}
                      className="cursor-pointer"
                      onClick={() => router.push(`/webhooks/${webhook.id}`)}
                    >
                      <TableCell>
                        <div className="flex items-center gap-3">
                          <div className="rounded-lg bg-primary/10 p-2">
                            <WebhookIcon className="h-4 w-4 text-primary" />
                          </div>
                          <div>
                            <p className="font-medium">{webhook.name}</p>
                            {webhook.description && (
                              <p className="text-xs text-muted-foreground truncate max-w-[180px]">
                                {webhook.description}
                              </p>
                            )}
                          </div>
                        </div>
                      </TableCell>
                      <TableCell className="hidden md:table-cell text-muted-foreground text-sm max-w-[240px] truncate font-mono">
                        {webhook.url}
                      </TableCell>
                      <TableCell className="hidden lg:table-cell">
                        <div className="flex flex-wrap gap-1">
                          {webhook.events.slice(0, 2).map((event) => (
                            <Badge key={event} variant="secondary" className="text-xs">
                              {event}
                            </Badge>
                          ))}
                          {webhook.events.length > 2 && (
                            <Badge variant="outline" className="text-xs">
                              +{webhook.events.length - 2}
                            </Badge>
                          )}
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline" className={`gap-1 ${statusClass}`}>
                          <StatusIcon className="h-3 w-3" />
                          {statusConfig[webhook.status]?.label || webhook.status}
                        </Badge>
                      </TableCell>
                      <TableCell className="hidden lg:table-cell text-sm text-muted-foreground">
                        {webhook.last_success_at
                          ? formatDateTime(webhook.last_success_at)
                          : webhook.last_failure_at
                            ? formatDateTime(webhook.last_failure_at)
                            : '—'}
                      </TableCell>
                      <TableCell onClick={(e) => e.stopPropagation()}>
                        <div className="flex items-center gap-2">
                          <Switch
                            checked={webhook.status === 'active'}
                            onCheckedChange={() => handleToggle(webhook)}
                            disabled={togglingIds.has(webhook.id)}
                          />
                          <span className="text-xs text-muted-foreground">
                            {webhook.status === 'active' ? 'On' : 'Off'}
                          </span>
                        </div>
                      </TableCell>
                      <TableCell onClick={(e) => e.stopPropagation()}>
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="icon-sm">
                              <MoreHorizontal className="h-4 w-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuLabel>Actions</DropdownMenuLabel>
                            <DropdownMenuItem onClick={() => router.push(`/webhooks/${webhook.id}`)}>
                              <Eye className="mr-2 h-4 w-4" />
                              View Details
                            </DropdownMenuItem>
                            <DropdownMenuItem
                              onClick={async () => {
                                try {
                                  await navigator.clipboard.writeText(webhook.url);
                                  toast.success('URL copied to clipboard');
                                } catch {
                                  toast.error('Failed to copy');
                                }
                              }}
                            >
                              <Copy className="mr-2 h-4 w-4" />
                              Copy URL
                            </DropdownMenuItem>
                            <DropdownMenuSeparator />
                            <DropdownMenuItem
                              className="text-destructive"
                              onClick={() => setDeleteConfirmId(webhook.id)}
                            >
                              <Trash2 className="mr-2 h-4 w-4" />
                              Delete
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

      {/* Pagination */}
      {!isLoading && !error && total > 0 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            Showing page {page} of {totalPages} ({total} total)
          </p>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={page <= 1}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
            >
              <ChevronLeft className="h-4 w-4" />
              Previous
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={page >= totalPages}
              onClick={() => setPage((p) => p + 1)}
            >
              Next
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}

      {/* Delete Confirmation Dialog */}
      <Dialog
        open={!!deleteConfirmId}
        onOpenChange={(open) => !open && setDeleteConfirmId(null)}
      >
        <DialogContent className="sm:max-w-[400px]">
          <DialogHeader>
            <DialogTitle>Delete Webhook</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete this webhook? This action cannot be undone.
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

      {/* Create Webhook Dialog */}
      <CreateWebhookDialog
        open={createDialogOpen}
        onOpenChange={setCreateDialogOpen}
        onCreated={fetchWebhooks}
      />
    </div>
  );
}
