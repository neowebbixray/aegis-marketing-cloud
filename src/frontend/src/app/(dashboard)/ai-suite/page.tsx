'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import {
  Brain,
  Sparkles,
  MessageSquare,
  FileText,
  BarChart3,
  Target,
  PenLine,
  Search,
  Wand2,
  Plus,
  Loader2,
  Zap,
  Shield,
  Clock,
  Cpu,
  Bot,
  Activity,
  Play,
  ArrowRight,
  Trash2,
} from 'lucide-react';
import { Button } from '@/components/atoms/button';
import { Badge } from '@/components/atoms/badge';
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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/molecules/select';
import { Input } from '@/components/atoms/input';
import { Label } from '@/components/atoms/label';
import { Textarea } from '@/components/atoms/textarea';
import { Separator } from '@/components/atoms/separator';
import { Skeleton } from '@/components/atoms/skeleton';
import { toast } from 'sonner';
import { aiApi } from '@/lib/api/ai';
import { formatDateTime } from '@/lib/utils';
import type { Agent, AgentStatus, AgentCapability } from '@/lib/api/ai';

// ─── Constants ────────────────────────────────────────────────

const statusConfig: Record<AgentStatus, { label: string; className: string }> = {
  idle: { label: 'Idle', className: 'bg-muted text-muted-foreground' },
  running: { label: 'Running', className: 'bg-success-100 text-success-800 dark:bg-success-900 dark:text-success-100' },
  error: { label: 'Error', className: 'bg-destructive/10 text-destructive' },
  paused: { label: 'Paused', className: 'bg-warning-100 text-warning-800 dark:bg-warning-900 dark:text-warning-100' },
};

const capabilityLabels: Record<AgentCapability, string> = {
  'content-generation': 'Content Gen',
  classification: 'Classification',
  'sentiment-analysis': 'Sentiment',
  'lead-scoring': 'Lead Scoring',
  email_composer: 'Email Composer',
  chat: 'Chat',
  summarization: 'Summarization',
  translation: 'Translation',
  image_analysis: 'Image Analysis',
  recommendation: 'Recommendation',
  'intent-detection': 'Intent Detection',
  'ab-testing': 'A/B Testing',
  'segment-analysis': 'Segment Analysis',
  forecasting: 'Forecasting',
};

const capabilityColors: Record<AgentCapability, string> = {
  'content-generation': 'bg-blue-500/10 text-blue-600 dark:text-blue-400',
  classification: 'bg-purple-500/10 text-purple-600 dark:text-purple-400',
  'sentiment-analysis': 'bg-pink-500/10 text-pink-600 dark:text-pink-400',
  'lead-scoring': 'bg-green-500/10 text-green-600 dark:text-green-400',
  email_composer: 'bg-orange-500/10 text-orange-600 dark:text-orange-400',
  chat: 'bg-cyan-500/10 text-cyan-600 dark:text-cyan-400',
  summarization: 'bg-teal-500/10 text-teal-600 dark:text-teal-400',
  translation: 'bg-indigo-500/10 text-indigo-600 dark:text-indigo-400',
  image_analysis: 'bg-rose-500/10 text-rose-600 dark:text-rose-400',
  recommendation: 'bg-amber-500/10 text-amber-600 dark:text-amber-400',
  'intent-detection': 'bg-violet-500/10 text-violet-600 dark:text-violet-400',
  'ab-testing': 'bg-yellow-500/10 text-yellow-600 dark:text-yellow-400',
  'segment-analysis': 'bg-slate-500/10 text-slate-600 dark:text-slate-400',
  forecasting: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400',
};

const allCapabilities = Object.keys(capabilityLabels) as AgentCapability[];

const agentTypeIcons: Record<string, React.ElementType> = {
  content_generation: FileText,
  classification: BarChart3,
  sentiment_analysis: Activity,
  lead_scoring: Target,
  email_composer: MessageSquare,
  chat: MessageSquare,
  summarization: FileText,
  translation: Brain,
  image_analysis: Search,
  recommendation: Zap,
};

// ─── Create Agent Dialog ──────────────────────────────────────

function CreateAgentDialog({
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
  const [capabilities, setCapabilities] = useState<AgentCapability[]>([]);
  const [model, setModel] = useState('gpt-4');
  const [temperature, setTemperature] = useState('0.7');
  const [maxTokens, setMaxTokens] = useState('2048');
  const [creating, setCreating] = useState(false);

  const toggleCapability = (cap: AgentCapability) => {
    setCapabilities((prev) =>
      prev.includes(cap) ? prev.filter((c) => c !== cap) : [...prev, cap]
    );
  };

  const handleCreate = async () => {
    if (!name.trim()) {
      toast.error('Agent name is required');
      return;
    }
    if (capabilities.length === 0) {
      toast.error('Select at least one capability');
      return;
    }

    setCreating(true);
    try {
      await aiApi.createAgent({
        name: name.trim(),
        description: description.trim() || undefined,
        capabilities,
        model,
        temperature: parseFloat(temperature),
        max_tokens: parseInt(maxTokens, 10),
      });
      toast.success('Agent created successfully');
      onOpenChange(false);
      setName('');
      setDescription('');
      setCapabilities([]);
      setModel('gpt-4');
      setTemperature('0.7');
      setMaxTokens('2048');
      onCreated();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to create agent');
    } finally {
      setCreating(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[600px] max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Create AI Agent</DialogTitle>
          <DialogDescription>
            Configure a new AI agent with its capabilities and model settings
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 py-4">
          <div className="space-y-2">
            <Label htmlFor="agent-name">Agent Name *</Label>
            <Input
              id="agent-name"
              placeholder="e.g., Content Specialist"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="agent-desc">Description</Label>
            <Textarea
              id="agent-desc"
              placeholder="What this agent does..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={2}
            />
          </div>
          <div className="space-y-2">
            <Label>Capabilities *</Label>
            <div className="grid grid-cols-2 gap-2">
              {allCapabilities.map((cap) => (
                <label
                  key={cap}
                  className={`flex items-center gap-2 text-sm cursor-pointer rounded-lg border p-2 transition-colors ${
                    capabilities.includes(cap)
                      ? 'border-primary bg-primary/5'
                      : 'hover:bg-muted'
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={capabilities.includes(cap)}
                    onChange={() => toggleCapability(cap)}
                    className="rounded"
                  />
                  {capabilityLabels[cap]}
                </label>
              ))}
            </div>
          </div>
          <Separator />
          <div className="grid grid-cols-3 gap-4">
            <div className="space-y-2">
              <Label htmlFor="agent-model">Model</Label>
              <Select value={model} onValueChange={setModel}>
                <SelectTrigger id="agent-model">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="gpt-4">GPT-4</SelectItem>
                  <SelectItem value="gpt-4-turbo">GPT-4 Turbo</SelectItem>
                  <SelectItem value="gpt-3.5-turbo">GPT-3.5 Turbo</SelectItem>
                  <SelectItem value="claude-3-opus">Claude 3 Opus</SelectItem>
                  <SelectItem value="claude-3-sonnet">Claude 3 Sonnet</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="agent-temp">Temperature</Label>
              <Input
                id="agent-temp"
                type="number"
                min={0}
                max={2}
                step={0.1}
                value={temperature}
                onChange={(e) => setTemperature(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="agent-tokens">Max Tokens</Label>
              <Input
                id="agent-tokens"
                type="number"
                min={256}
                max={8192}
                step={256}
                value={maxTokens}
                onChange={(e) => setMaxTokens(e.target.value)}
              />
            </div>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleCreate} disabled={creating}>
            {creating ? (
              <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Creating...</>
            ) : (
              <><Sparkles className="mr-2 h-4 w-4" /> Create Agent</>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ─── AI Suite Page ────────────────────────────────────────────

export default function AiSuitePage() {
  const router = useRouter();
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [capabilityFilter, setCapabilityFilter] = useState<string>('all');
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [stats, setStats] = useState({ totalRuns: 0, avgResponse: '0s', guardrails: 0 });

  const fetchAgents = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params: { status?: AgentStatus; capability?: AgentCapability } = {};
      if (statusFilter !== 'all') params.status = statusFilter as AgentStatus;
      if (capabilityFilter !== 'all') params.capability = capabilityFilter as AgentCapability;
      const res = await aiApi.listAgents(params.status || params.capability ? params : undefined);
      setAgents(res.data || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load agents');
      setAgents([]);
    } finally {
      setLoading(false);
    }
  }, [statusFilter, capabilityFilter]);

  useEffect(() => {
    fetchAgents();
  }, [fetchAgents]);

  const filteredAgents = agents;

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-primary/10">
            <Brain className="h-6 w-6 text-primary" />
          </div>
          <div>
            <h1 className="text-3xl font-bold tracking-tight">AI Suite</h1>
            <p className="text-muted-foreground mt-1">
              AI-powered marketing agents to automate and optimize your workflows
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={() => router.push('/ai-suite/content')}>
            <FileText className="mr-2 h-4 w-4" />
            Generate Content
          </Button>
          <Button onClick={() => setCreateDialogOpen(true)}>
            <Plus className="mr-2 h-4 w-4" />
            Create Agent
          </Button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Agents</CardTitle>
            <Brain className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{agents.length}</div>
            <p className="text-xs text-muted-foreground">
              {agents.filter((a) => a.status === 'running').length} currently running
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Tasks Completed</CardTitle>
            <Zap className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">1,247</div>
            <p className="text-xs text-muted-foreground">+12% this week</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Avg. Response</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">1.2s</div>
            <p className="text-xs text-muted-foreground">P95: 2.8s</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Guardrails Active</CardTitle>
            <Shield className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">12</div>
            <p className="text-xs text-muted-foreground">0 blocks today</p>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-3">
        <Select
          value={statusFilter}
          onValueChange={(v) => { setStatusFilter(v); }}
        >
          <SelectTrigger className="w-[160px]">
            <SelectValue placeholder="All Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Status</SelectItem>
            <SelectItem value="idle">Idle</SelectItem>
            <SelectItem value="running">Running</SelectItem>
            <SelectItem value="error">Error</SelectItem>
            <SelectItem value="paused">Paused</SelectItem>
          </SelectContent>
        </Select>
        <Select
          value={capabilityFilter}
          onValueChange={(v) => { setCapabilityFilter(v); }}
        >
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="All Capabilities" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Capabilities</SelectItem>
            {allCapabilities.map((cap) => (
              <SelectItem key={cap} value={cap}>
                {capabilityLabels[cap]}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Agent Grid */}
      <div>
        {loading ? (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <Card key={i}>
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <Skeleton className="h-10 w-10 rounded-lg" />
                    <Skeleton className="h-5 w-20 rounded-full" />
                  </div>
                  <Skeleton className="h-6 w-32 mt-3" />
                  <Skeleton className="h-4 w-full mt-2" />
                </CardHeader>
                <CardContent>
                  <div className="flex gap-1 flex-wrap">
                    <Skeleton className="h-5 w-20 rounded-full" />
                    <Skeleton className="h-5 w-24 rounded-full" />
                  </div>
                </CardContent>
                <CardFooter className="border-t pt-4">
                  <Skeleton className="h-10 w-full" />
                </CardFooter>
              </Card>
            ))}
          </div>
        ) : error ? (
          <div className="flex flex-col items-center justify-center py-16">
            <Bot className="h-12 w-12 text-muted-foreground mb-4" />
            <p className="text-muted-foreground mb-2">Failed to load agents</p>
            <p className="text-sm text-destructive mb-4">{error}</p>
            <Button variant="outline" onClick={fetchAgents}>
              Retry
            </Button>
          </div>
        ) : filteredAgents.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16">
            <div className="p-4 rounded-full bg-muted mb-4">
              <Brain className="h-8 w-8 text-muted-foreground" />
            </div>
            <h3 className="text-lg font-semibold mb-1">No agents found</h3>
            <p className="text-muted-foreground text-sm mb-4">
              {statusFilter !== 'all' || capabilityFilter !== 'all'
                ? 'No agents match the selected filters'
                : 'Create your first AI agent to get started'}
            </p>
            {statusFilter === 'all' && capabilityFilter === 'all' && (
              <Button onClick={() => setCreateDialogOpen(true)}>
                <Plus className="mr-2 h-4 w-4" />
                Create Agent
              </Button>
            )}
          </div>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {filteredAgents.map((agent) => {
              const status = statusConfig[agent.status] || statusConfig.idle;
              const primaryCap = agent.capabilities[0] || 'chat';
              const Icon = agentTypeIcons[primaryCap] || Bot;

              return (
                <Card
                  key={agent.id}
                  className="hover:shadow-md transition-shadow cursor-pointer"
                  onClick={() => router.push(`/ai-suite/${agent.id}`)}
                >
                  <CardHeader>
                    <div className="flex items-start justify-between">
                      <div className="p-2 rounded-lg bg-primary/10">
                        <Icon className="h-5 w-5 text-primary" />
                      </div>
                      <Badge variant="outline" className={status.className}>
                        {status.label}
                      </Badge>
                    </div>
                    <CardTitle className="mt-3 text-lg">{agent.name}</CardTitle>
                    <CardDescription>
                      {agent.description || `AI agent with ${agent.capabilities.length} capabilities`}
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="flex flex-wrap gap-1 mb-3">
                      {agent.capabilities.slice(0, 3).map((cap) => (
                        <span
                          key={cap}
                          className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${capabilityColors[cap] || ''}`}
                        >
                          {capabilityLabels[cap] || cap}
                        </span>
                      ))}
                      {agent.capabilities.length > 3 && (
                        <span className="text-xs text-muted-foreground">
                          +{agent.capabilities.length - 3}
                        </span>
                      )}
                    </div>
                    {agent.last_run_at && (
                      <p className="text-xs text-muted-foreground">
                        Last run: {formatDateTime(agent.last_run_at)}
                      </p>
                    )}
                  </CardContent>
                  <CardFooter className="border-t pt-4 flex gap-2">
                    <Button
                      variant="default"
                      className="flex-1"
                      onClick={(e) => {
                        e.stopPropagation();
                        router.push(`/ai-suite/${agent.id}`);
                      }}
                    >
                      <Play className="mr-2 h-4 w-4" />
                      Open
                    </Button>
                    <Button
                      variant="outline"
                      size="icon"
                      onClick={(e) => {
                        e.stopPropagation();
                        router.push(`/ai-suite/content`);
                      }}
                    >
                      <MessageSquare className="h-4 w-4" />
                    </Button>
                  </CardFooter>
                </Card>
              );
            })}
          </div>
        )}
      </div>

      {/* Create Agent Dialog */}
      <CreateAgentDialog
        open={createDialogOpen}
        onOpenChange={setCreateDialogOpen}
        onCreated={fetchAgents}
      />
    </div>
  );
}
