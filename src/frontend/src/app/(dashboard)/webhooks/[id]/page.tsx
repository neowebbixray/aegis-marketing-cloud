'use client';

import { useState, useEffect, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import {
  ArrowLeft,
  Webhook,
  Copy,
  RefreshCw,
  Send,
  RotateCcw,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Clock,
  Loader2,
  Eye,
  EyeOff,
} from 'lucide-react';
import { Button } from '@/components/atoms/button';
import { Badge } from '@/components/atoms/badge';
import { Input } from '@/components/atoms/input';
import { Label } from '@/components/atoms/label';
import { Separator } from '@/components/atoms/separator';
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
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/molecules/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/molecules/tabs';
import { Skeleton } from '@/components/atoms/skeleton';
import { toast } from 'sonner';
import { webhooksApi } from '@/lib/api/webhooks';
import { formatDateTime } from '@/lib/utils';
import type { Webhook, WebhookDelivery, WebhookEvent, WebhookDeliveryStatus, WebhookStatus } from '@/lib/api/webhooks';

// ─── Helpers ────────────────────────────────────────────────

const statusConfig: Record<WebhookStatus, { label: string; icon: React.ElementType; className: string }> = {
  active: { label: 'Active', icon: CheckCircle2, className: 'bg-success-100 text-success-800 dark:bg-success-900 dark:text-success-100' },
  inactive: { label: 'Inactive', icon: XCircle, className: 'bg-muted text-muted-foreground' },
  disabled: { label: 'Failing', icon: AlertTriangle, className: 'bg-destructive/10 text-destructive' },
};

const deliveryStatusConfig: Record<WebhookDeliveryStatus, { label: string; icon: React.ElementType; className: string }> = {
  success: { label: 'Success', icon: CheckCircle2, className: 'bg-success-100 text-success-800 dark:bg-success-900 dark:text-success-100' },
  failed: { label: 'Failed', icon: XCircle, className: 'bg-destructive/10 text-destructive' },
  retrying: { label: 'Retrying', icon: RefreshCw, className: 'bg-warning-100 text-warning-800 dark:bg-warning-900 dark:text-warning-100' },
  pending: { label: 'Pending', icon: Clock, className: 'bg-muted text-muted-foreground' },
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

// ─── Webhook Detail Page ────────────────────────────────────

export default function WebhookDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = params?.id as string;

  const [webhook, setWebhook] = useState<Webhook | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [deliveries, setDeliveries] = useState<WebhookDelivery[]>([]);
  const [deliveriesLoading, setDeliveriesLoading] = useState(false);
  const [deliveryPage, setDeliveryPage] = useState(1);
  const [deliveryTotal, setDeliveryTotal] = useState(0);
  const [deliveryFilter, setDeliveryFilter] = useState<string>('all');

  const [showSecret, setShowSecret] = useState(false);
  const [rotatingSecret, setRotatingSecret] = useState(false);
  const [testingWebhook, setTestingWebhook] = useState(false);
  const [redeliveringId, setRedeliveringId] = useState<string | null>(null);

  const [secretRotateDialogOpen, setSecretRotateDialogOpen] = useState(false);
  const [newSecret, setNewSecret] = useState<string | null>(null);

  const fetchWebhook = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await webhooksApi.get(id);
      setWebhook(res.data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load webhook');
    } finally {
      setLoading(false);
    }
  }, [id]);

  const fetchDeliveries = useCallback(async () => {
    setDeliveriesLoading(true);
    try {
      const res = await webhooksApi.listDeliveries(id, {
        page: deliveryPage,
        limit: 20,
        status: deliveryFilter !== 'all' ? (deliveryFilter as WebhookDeliveryStatus) : undefined,
      });
      setDeliveries(res.data);
      setDeliveryTotal(res.meta.total);
    } catch {
      // silently fail — the deliveries table will be empty
      setDeliveries([]);
    } finally {
      setDeliveriesLoading(false);
    }
  }, [id, deliveryPage, deliveryFilter]);

  useEffect(() => {
    if (id) {
      fetchWebhook();
    }
  }, [id, fetchWebhook]);

  useEffect(() => {
    if (id) {
      fetchDeliveries();
    }
  }, [id, fetchDeliveries]);

  const handleToggle = async () => {
    if (!webhook) return;
    const newStatus = webhook.status === 'active' ? 'inactive' : 'active';
    try {
      await webhooksApi.toggle(id, newStatus === 'active');
      toast.success(`Webhook ${newStatus === 'active' ? 'enabled' : 'disabled'}`);
      fetchWebhook();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to toggle webhook');
    }
  };

  const handleRotateSecret = async () => {
    setRotatingSecret(true);
    try {
      const res = await webhooksApi.rotateSecret(id);
      setNewSecret(res.data.secret);
      toast.success('Secret rotated successfully');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to rotate secret');
    } finally {
      setRotatingSecret(false);
    }
  };

  const handleTest = async () => {
    setTestingWebhook(true);
    try {
      const res = await webhooksApi.test(id);
      if (res.data.success) {
        toast.success(`Test successful — ${res.data.status_code} in ${res.data.duration_ms}ms`);
      } else {
        toast.error(`Test failed: ${res.data.error || `Status ${res.data.status_code}`}`);
      }
      fetchDeliveries();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to test webhook');
    } finally {
      setTestingWebhook(false);
    }
  };

  const handleRedeliver = async (deliveryId: string) => {
    setRedeliveringId(deliveryId);
    try {
      await webhooksApi.retryDelivery(id, deliveryId);
      toast.success('Redelivery initiated');
      fetchDeliveries();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to redeliver');
    } finally {
      setRedeliveringId(null);
    }
  };

  const copyToClipboard = async (text: string, label: string) => {
    try {
      await navigator.clipboard.writeText(text);
      toast.success(`${label} copied to clipboard`);
    } catch {
      toast.error('Failed to copy');
    }
  };

  const deliveryTotalPages = Math.ceil(deliveryTotal / 20);

  // Loading state
  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Skeleton className="h-10 w-10 rounded-full" />
          <div>
            <Skeleton className="h-8 w-48" />
            <Skeleton className="h-4 w-32 mt-2" />
          </div>
        </div>
        <Skeleton className="h-64 w-full" />
        <Skeleton className="h-48 w-full" />
      </div>
    );
  }

  // Error state
  if (error || !webhook) {
    return (
      <div className="flex flex-col items-center justify-center py-24">
        <p className="text-muted-foreground">Webhook not found</p>
        <Button variant="link" onClick={() => router.push('/webhooks')}>
          Back to webhooks
        </Button>
      </div>
    );
  }

  const StatusIcon = statusConfig[webhook.status]?.icon || CheckCircle2;
  const statusClass = statusConfig[webhook.status]?.className || '';

  return (
    <div className="space-y-6">
      {/* Back button + header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => router.back()}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold">{webhook.name}</h1>
              <Badge variant="outline" className={`gap-1 ${statusClass}`}>
                <StatusIcon className="h-3 w-3" />
                {statusConfig[webhook.status]?.label || webhook.status}
              </Badge>
            </div>
            <p className="text-muted-foreground text-sm mt-1">
              {webhook.description || 'No description'}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={handleTest} disabled={testingWebhook}>
            {testingWebhook ? (
              <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Testing...</>
            ) : (
              <><Send className="mr-2 h-4 w-4" /> Test</>
            )}
          </Button>
          <Button
            variant={webhook.status === 'active' ? 'outline' : 'default'}
            size="sm"
            onClick={handleToggle}
          >
            {webhook.status === 'active' ? 'Disable' : 'Enable'}
          </Button>
        </div>
      </div>

      {/* Info Cards */}
      <div className="grid gap-6 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Payload URL</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2">
              <code className="flex-1 text-sm bg-muted px-2 py-1 rounded truncate font-mono">
                {webhook.url}
              </code>
              <Button
                variant="ghost"
                size="icon-sm"
                onClick={() => copyToClipboard(webhook.url, 'URL')}
              >
                <Copy className="h-4 w-4" />
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">API Version</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-lg font-semibold">v1</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Secret</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2">
              <code className="flex-1 text-xs bg-muted px-2 py-1 rounded truncate font-mono">
                {showSecret ? webhook.secret : '••••••••••••••••'}
              </code>
              <Button
                variant="ghost"
                size="icon-sm"
                onClick={() => setShowSecret(!showSecret)}
              >
                {showSecret ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </Button>
              <Button
                variant="ghost"
                size="icon-sm"
                onClick={() => copyToClipboard(webhook.secret, 'Secret')}
              >
                <Copy className="h-4 w-4" />
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setSecretRotateDialogOpen(true)}
                disabled={rotatingSecret}
              >
                <RefreshCw className={`mr-1 h-3 w-3 ${rotatingSecret ? 'animate-spin' : ''}`} />
                Rotate
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="events" className="space-y-4">
        <TabsList>
          <TabsTrigger value="events">Subscribed Events</TabsTrigger>
          <TabsTrigger value="deliveries">
            Delivery Log
            {deliveryTotal > 0 && (
              <Badge variant="secondary" className="ml-2 text-xs">{deliveryTotal}</Badge>
            )}
          </TabsTrigger>
        </TabsList>

        {/* Events Tab */}
        <TabsContent value="events" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Subscribed Events</CardTitle>
              <CardDescription>
                This webhook is triggered by {webhook.events.length} event{webhook.events.length !== 1 ? 's' : ''}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-2">
                {webhook.events.map((event) => (
                  <Badge key={event} variant="secondary" className="text-sm px-3 py-1">
                    {event}
                  </Badge>
                ))}
                {webhook.events.length === 0 && (
                  <p className="text-sm text-muted-foreground">No events subscribed</p>
                )}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Webhook Details</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-muted-foreground">Created</p>
                  <p className="text-sm font-medium">{formatDateTime(webhook.created_at)}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Last Success</p>
                  <p className="text-sm font-medium">{webhook.last_success_at ? formatDateTime(webhook.last_success_at) : '—'}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Last Failure</p>
                  <p className="text-sm font-medium">{webhook.last_failure_at ? formatDateTime(webhook.last_failure_at) : '—'}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Consecutive Failures</p>
                  <p className="text-sm font-medium">{webhook.consecutive_failures}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Retry Count</p>
                  <p className="text-sm font-medium">{webhook.retry_count}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Timeout</p>
                  <p className="text-sm font-medium">{webhook.timeout_seconds}s</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Deliveries Tab */}
        <TabsContent value="deliveries" className="space-y-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle className="text-lg">Delivery Log</CardTitle>
                <CardDescription>
                  Recent delivery attempts for this webhook
                </CardDescription>
              </div>
              <Select value={deliveryFilter} onValueChange={(v) => { setDeliveryFilter(v); setDeliveryPage(1); }}>
                <SelectTrigger className="w-[140px]">
                  <SelectValue placeholder="Status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All</SelectItem>
                  <SelectItem value="success">Success</SelectItem>
                  <SelectItem value="failed">Failed</SelectItem>
                  <SelectItem value="retrying">Retrying</SelectItem>
                  <SelectItem value="pending">Pending</SelectItem>
                </SelectContent>
              </Select>
            </CardHeader>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Timestamp</TableHead>
                    <TableHead>Event Type</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="hidden md:table-cell">Response</TableHead>
                    <TableHead className="hidden md:table-cell">Duration</TableHead>
                    <TableHead className="w-[100px]"></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {deliveriesLoading ? (
                    Array.from({ length: 3 }).map((_, i) => (
                      <TableRow key={i}>
                        <TableCell><Skeleton className="h-5 w-32" /></TableCell>
                        <TableCell><Skeleton className="h-5 w-24" /></TableCell>
                        <TableCell><Skeleton className="h-5 w-20" /></TableCell>
                        <TableCell className="hidden md:table-cell"><Skeleton className="h-5 w-16" /></TableCell>
                        <TableCell className="hidden md:table-cell"><Skeleton className="h-5 w-16" /></TableCell>
                        <TableCell><Skeleton className="h-8 w-8 rounded-full" /></TableCell>
                      </TableRow>
                    ))
                  ) : deliveries.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={6} className="text-center py-8 text-muted-foreground">
                        No delivery logs yet
                      </TableCell>
                    </TableRow>
                  ) : (
                    deliveries.map((delivery) => {
                      const DelStatusIcon = deliveryStatusConfig[delivery.status]?.icon || Clock;
                      const delStatusClass = deliveryStatusConfig[delivery.status]?.className || '';
                      return (
                        <TableRow key={delivery.id}>
                          <TableCell className="text-sm">
                            {formatDateTime(delivery.created_at)}
                          </TableCell>
                          <TableCell>
                            <Badge variant="outline" className="text-xs font-mono">
                              {delivery.event_type}
                            </Badge>
                          </TableCell>
                          <TableCell>
                            <Badge variant="outline" className={`gap-1 ${delStatusClass}`}>
                              <DelStatusIcon className="h-3 w-3" />
                              {deliveryStatusConfig[delivery.status]?.label || delivery.status}
                            </Badge>
                          </TableCell>
                          <TableCell className="hidden md:table-cell text-sm">
                            {delivery.response_status || '—'}
                          </TableCell>
                          <TableCell className="hidden md:table-cell text-sm">
                            {delivery.duration_ms != null ? `${delivery.duration_ms}ms` : '—'}
                          </TableCell>
                          <TableCell>
                            {delivery.status === 'failed' && (
                              <Button
                                variant="ghost"
                                size="icon-sm"
                                onClick={() => handleRedeliver(delivery.id)}
                                disabled={redeliveringId === delivery.id}
                              >
                                <RotateCcw className={`h-4 w-4 ${redeliveringId === delivery.id ? 'animate-spin' : ''}`} />
                              </Button>
                            )}
                          </TableCell>
                        </TableRow>
                      );
                    })
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>

          {/* Delivery pagination */}
          {deliveryTotal > 0 && (
            <div className="flex items-center justify-between">
              <p className="text-sm text-muted-foreground">
                Page {deliveryPage} of {deliveryTotalPages} ({deliveryTotal} total)
              </p>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={deliveryPage <= 1}
                  onClick={() => setDeliveryPage((p) => Math.max(1, p - 1))}
                >
                  Previous
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={deliveryPage >= deliveryTotalPages}
                  onClick={() => setDeliveryPage((p) => p + 1)}
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </TabsContent>
      </Tabs>

      {/* Secret Rotate Confirmation Dialog */}
      <Dialog
        open={secretRotateDialogOpen}
        onOpenChange={(open) => {
          if (!open) {
            setSecretRotateDialogOpen(false);
            setNewSecret(null);
          }
        }}
      >
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle>{newSecret ? 'Secret Rotated' : 'Rotate Secret'}</DialogTitle>
            <DialogDescription>
              {newSecret
                ? 'Your new webhook secret is below. Copy it now — you won\'t be able to see it again.'
                : 'Rotating the secret will invalidate the current one. Any services using the old secret will need to be updated.'}
            </DialogDescription>
          </DialogHeader>
          {newSecret ? (
            <div className="space-y-4">
              <div className="p-3 bg-muted rounded-lg">
                <code className="text-sm font-mono break-all">{newSecret}</code>
              </div>
              <Button
                className="w-full"
                onClick={() => copyToClipboard(newSecret, 'New secret')}
              >
                <Copy className="mr-2 h-4 w-4" />
                Copy New Secret
              </Button>
            </div>
          ) : (
            <DialogFooter>
              <Button variant="outline" onClick={() => setSecretRotateDialogOpen(false)}>
                Cancel
              </Button>
              <Button
                onClick={async () => {
                  await handleRotateSecret();
                }}
                disabled={rotatingSecret}
              >
                {rotatingSecret ? 'Rotating...' : 'Rotate Secret'}
              </Button>
            </DialogFooter>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
