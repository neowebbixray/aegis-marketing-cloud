'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  ArrowLeft,
  Plus,
  Save,
  Loader2,
  RefreshCw,
  Copy,
  Eye,
  EyeOff,
  Link2,
} from 'lucide-react';
import { Button } from '@/components/atoms/button';
import { Badge } from '@/components/atoms/badge';
import { Input } from '@/components/atoms/input';
import { Label } from '@/components/atoms/label';
import { Textarea } from '@/components/atoms/textarea';
import { Separator } from '@/components/atoms/separator';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/molecules/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/molecules/select';
import { Switch } from '@/components/atoms/switch';
import { toast } from 'sonner';
import { webhooksApi } from '@/lib/api/webhooks';
import type { WebhookEvent } from '@/lib/api/webhooks';

// ─── Constants ──────────────────────────────────────────────

const allEvents: { value: WebhookEvent; label: string; group: string }[] = [
  // Contacts
  { value: 'contact.created', label: 'Contact Created', group: 'Contacts' },
  { value: 'contact.updated', label: 'Contact Updated', group: 'Contacts' },
  { value: 'contact.deleted', label: 'Contact Deleted', group: 'Contacts' },
  // Deals
  { value: 'deal.created', label: 'Deal Created', group: 'Deals' },
  { value: 'deal.updated', label: 'Deal Updated', group: 'Deals' },
  { value: 'deal.deleted', label: 'Deal Deleted', group: 'Deals' },
  { value: 'pipeline.stage.changed', label: 'Pipeline Stage Changed', group: 'Deals' },
  // Invoicing
  { value: 'invoice.paid', label: 'Invoice Paid', group: 'Invoicing' },
  { value: 'invoice.overdue', label: 'Invoice Overdue', group: 'Invoicing' },
  // Subscriptions
  { value: 'subscription.updated', label: 'Subscription Updated', group: 'Subscriptions' },
  { value: 'subscription.canceled', label: 'Subscription Canceled', group: 'Subscriptions' },
  // Campaigns
  { value: 'campaign.sent', label: 'Campaign Sent', group: 'Campaigns' },
  { value: 'campaign.completed', label: 'Campaign Completed', group: 'Campaigns' },
  // Forms & Media
  { value: 'form.submitted', label: 'Form Submitted', group: 'Forms' },
  { value: 'media.uploaded', label: 'Media Uploaded', group: 'Media' },
  // AI
  { value: 'ai.generation.completed', label: 'AI Generation Completed', group: 'AI' },
];

const eventGroups = Array.from(new Set(allEvents.map((e) => e.group)));

interface FormState {
  name: string;
  url: string;
  description: string;
  events: WebhookEvent[];
  apiVersion: string;
  secret: string;
  useCustomSecret: boolean;
  testOnCreate: boolean;
  retryCount: string;
  timeoutSeconds: string;
}

const generateSecret = (): string => {
  const chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
  let result = 'whsec_';
  for (let i = 0; i < 32; i++) {
    result += chars.charAt(Math.floor(Math.random() * chars.length));
  }
  return result;
};

const initialState: FormState = {
  name: '',
  url: '',
  description: '',
  events: [],
  apiVersion: 'v1',
  secret: generateSecret(),
  useCustomSecret: false,
  testOnCreate: false,
  retryCount: '3',
  timeoutSeconds: '30',
};

// ─── Create Webhook Page ────────────────────────────────────

export default function CreateWebhookPage() {
  const router = useRouter();
  const [form, setForm] = useState<FormState>(initialState);
  const [saving, setSaving] = useState(false);
  const [showSecret, setShowSecret] = useState(false);

  const updateField = <K extends keyof FormState>(field: K, value: FormState[K]) => {
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

  const toggleGroup = (group: string) => {
    const groupEvents = allEvents.filter((e) => e.group === group).map((e) => e.value);
    const allSelected = groupEvents.every((evt) => form.events.includes(evt));
    if (allSelected) {
      setForm((prev) => ({
        ...prev,
        events: prev.events.filter((e) => !groupEvents.includes(e)),
      }));
    } else {
      setForm((prev) => ({
        ...prev,
        events: [...new Set([...prev.events, ...groupEvents])],
      }));
    }
  };

  const regenerateSecret = () => {
    setForm((prev) => ({ ...prev, secret: generateSecret() }));
  };

  const copySecret = async () => {
    try {
      await navigator.clipboard.writeText(form.secret);
      toast.success('Secret copied to clipboard');
    } catch {
      toast.error('Failed to copy');
    }
  };

  const isValidUrl = (url: string) => {
    try {
      const parsed = new URL(url);
      return parsed.protocol === 'http:' || parsed.protocol === 'https:';
    } catch {
      return false;
    }
  };

  const handleSubmit = async () => {
    // Validation
    if (!form.name.trim()) {
      toast.error('Webhook name is required');
      return;
    }
    if (!form.url.trim()) {
      toast.error('Payload URL is required');
      return;
    }
    if (!isValidUrl(form.url)) {
      toast.error('Please enter a valid HTTP or HTTPS URL');
      return;
    }
    if (form.events.length === 0) {
      toast.error('Select at least one event');
      return;
    }

    setSaving(true);
    try {
      const payload = {
        name: form.name.trim(),
        url: form.url.trim(),
        events: form.events,
        description: form.description.trim() || undefined,
        retry_count: parseInt(form.retryCount, 10) || 3,
        timeout_seconds: parseInt(form.timeoutSeconds, 10) || 30,
        headers: form.useCustomSecret ? { 'X-Webhook-Secret': form.secret } : undefined,
      };

      const res = await webhooksApi.create(payload);
      toast.success('Webhook created successfully');

      if (form.testOnCreate) {
        try {
          await webhooksApi.test(res.data.id);
          toast.success('Test event sent successfully');
        } catch {
          toast.warning('Webhook created but test event failed');
        }
      }

      router.push(`/webhooks/${res.data.id}`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to create webhook');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Back button + header */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => router.back()}>
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Create Webhook</h1>
          <p className="text-muted-foreground mt-1">
            Register a new webhook endpoint to receive real-time events
          </p>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Main form */}
        <div className="lg:col-span-2 space-y-6">
          {/* Basic Information */}
          <Card>
            <CardHeader>
              <CardTitle>Basic Information</CardTitle>
              <CardDescription>
                Provide a name and the endpoint URL for your webhook
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="name">Webhook Name *</Label>
                <Input
                  id="name"
                  placeholder="e.g., Slack Notifications"
                  value={form.name}
                  onChange={(e) => updateField('name', e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="url">Payload URL *</Label>
                <Input
                  id="url"
                  placeholder="https://hooks.example.com/events"
                  value={form.url}
                  onChange={(e) => updateField('url', e.target.value)}
                />
                <p className="text-xs text-muted-foreground">
                  Must be a valid HTTP or HTTPS endpoint
                </p>
              </div>
              <div className="space-y-2">
                <Label htmlFor="description">Description</Label>
                <Textarea
                  id="description"
                  placeholder="Optional description of what this webhook does"
                  value={form.description}
                  onChange={(e) => updateField('description', e.target.value)}
                  rows={3}
                />
              </div>
            </CardContent>
          </Card>

          {/* Event Selection */}
          <Card>
            <CardHeader>
              <CardTitle>Events *</CardTitle>
              <CardDescription>
                Choose which events will trigger this webhook
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {eventGroups.map((group) => {
                const groupEvents = allEvents.filter((e) => e.group === group);
                const allSelected = groupEvents.every((e) => form.events.includes(e.value));
                const someSelected = groupEvents.some((e) => form.events.includes(e.value));

                return (
                  <div key={group}>
                    <div className="flex items-center gap-2 mb-2">
                      <input
                        type="checkbox"
                        id={`group-${group}`}
                        checked={allSelected}
                        ref={(el) => {
                          if (el) el.indeterminate = someSelected && !allSelected;
                        }}
                        onChange={() => toggleGroup(group)}
                        className="rounded border-gray-300"
                      />
                      <Label htmlFor={`group-${group}`} className="font-medium text-sm cursor-pointer">
                        {group}
                      </Label>
                    </div>
                    <div className="grid grid-cols-2 gap-2 ml-6">
                      {groupEvents.map((event) => (
                        <label
                          key={event.value}
                          className="flex items-center gap-2 text-sm cursor-pointer hover:text-foreground"
                        >
                          <input
                            type="checkbox"
                            checked={form.events.includes(event.value)}
                            onChange={() => toggleEvent(event.value)}
                            className="rounded border-gray-300"
                          />
                          <span className="text-xs md:text-sm">{event.label}</span>
                        </label>
                      ))}
                    </div>
                  </div>
                );
              })}

              {form.events.length === 0 && (
                <p className="text-xs text-muted-foreground">Select at least one event</p>
              )}
            </CardContent>
          </Card>

          {/* Advanced Settings */}
          <Card>
            <CardHeader>
              <CardTitle>Advanced Settings</CardTitle>
              <CardDescription>
                Configure retry behavior, timeout, and API version
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="apiVersion">API Version</Label>
                  <Select
                    value={form.apiVersion}
                    onValueChange={(v) => updateField('apiVersion', v)}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="v1">v1 (Latest)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="retryCount">Max Retries</Label>
                  <Select
                    value={form.retryCount}
                    onValueChange={(v) => updateField('retryCount', v)}
                  >
                    <SelectTrigger id="retryCount">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="0">No retries</SelectItem>
                      <SelectItem value="1">1 retry</SelectItem>
                      <SelectItem value="3">3 retries</SelectItem>
                      <SelectItem value="5">5 retries</SelectItem>
                      <SelectItem value="10">10 retries</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="timeoutSeconds">Timeout (seconds)</Label>
                  <Select
                    value={form.timeoutSeconds}
                    onValueChange={(v) => updateField('timeoutSeconds', v)}
                  >
                    <SelectTrigger id="timeoutSeconds">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="5">5 seconds</SelectItem>
                      <SelectItem value="10">10 seconds</SelectItem>
                      <SelectItem value="30">30 seconds</SelectItem>
                      <SelectItem value="60">60 seconds</SelectItem>
                      <SelectItem value="120">120 seconds</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Secret */}
          <Card>
            <CardHeader>
              <CardTitle>Webhook Secret</CardTitle>
              <CardDescription>
                Used to verify webhook payloads
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center gap-2">
                <Label htmlFor="useCustomSecret" className="flex-1 text-sm cursor-pointer">
                  Provide custom secret
                </Label>
                <Switch
                  id="useCustomSecret"
                  checked={form.useCustomSecret}
                  onCheckedChange={(v) => updateField('useCustomSecret', v)}
                />
              </div>

              {form.useCustomSecret ? (
                <div className="space-y-2">
                  <Label htmlFor="secret">Secret</Label>
                  <div className="flex gap-2">
                    <div className="relative flex-1">
                      <Input
                        id="secret"
                        type={showSecret ? 'text' : 'password'}
                        value={form.secret}
                        onChange={(e) => updateField('secret', e.target.value)}
                        className="pr-8 font-mono text-xs"
                      />
                      <Button
                        variant="ghost"
                        size="icon-sm"
                        className="absolute right-1 top-1/2 -translate-y-1/2"
                        onClick={() => setShowSecret(!showSecret)}
                      >
                        {showSecret ? <EyeOff className="h-3 w-3" /> : <Eye className="h-3 w-3" />}
                      </Button>
                    </div>
                    <Button variant="outline" size="icon-sm" onClick={copySecret}>
                      <Copy className="h-4 w-4" />
                    </Button>
                    <Button variant="outline" size="icon-sm" onClick={regenerateSecret}>
                      <RefreshCw className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              ) : (
                <div className="p-3 rounded-lg bg-muted/50">
                  <p className="text-xs text-muted-foreground">
                    A secure secret will be auto-generated when you create the webhook.
                  </p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Test on Create */}
          <Card>
            <CardHeader>
              <CardTitle>Test on Create</CardTitle>
              <CardDescription>
                Send a test event after creation to verify your endpoint
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-3">
                <Switch
                  checked={form.testOnCreate}
                  onCheckedChange={(v) => updateField('testOnCreate', v)}
                />
                <div>
                  <p className="text-sm font-medium">Send test event</p>
                  <p className="text-xs text-muted-foreground">
                    Sends a <code className="text-xs">contact.created</code> test payload
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Submit */}
          <Card>
            <CardContent className="pt-6">
              <Button
                className="w-full"
                size="lg"
                onClick={handleSubmit}
                disabled={saving}
              >
                {saving ? (
                  <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Creating...</>
                ) : (
                  <><Save className="mr-2 h-4 w-4" /> Create Webhook</>
                )}
              </Button>
              <p className="text-xs text-muted-foreground text-center mt-2">
                You can edit webhook settings after creation
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
