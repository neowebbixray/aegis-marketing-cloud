'use client';

import { useState, useEffect, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import {
  ArrowLeft,
  Brain,
  Play,
  Pause,
  Loader2,
  MessageSquare,
  FileText,
  Settings,
  BarChart3,
  Clock,
  Zap,
  CheckCircle2,
  XCircle,
  Activity,
  Edit3,
  Save,
  Copy,
  Trash2,
  ExternalLink,
  Bot,
} from 'lucide-react';
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
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/molecules/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/molecules/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/molecules/tabs';
import { Separator } from '@/components/atoms/separator';
import { Skeleton } from '@/components/atoms/skeleton';
import { toast } from 'sonner';
import { aiApi } from '@/lib/api/ai';
import { formatDateTime } from '@/lib/utils';
import type { Agent, AgentStatus, AgentCapability, Conversation, GenerationResult } from '@/lib/api/ai';

// ─── Constants ────────────────────────────────────────────────

const statusConfig: Record<AgentStatus, { label: string; className: string }> = {
  idle: { label: 'Idle', className: 'bg-muted text-muted-foreground' },
  running: { label: 'Running', className: 'bg-success-100 text-success-800 dark:bg-success-900 dark:text-success-100' },
  error: { label: 'Error', className: 'bg-destructive/10 text-destructive' },
  paused: { label: 'Paused', className: 'bg-warning-100 text-warning-800 dark:bg-warning-900 dark:text-warning-100' },
};

const capabilityLabels: Record<AgentCapability, string> = {
  'content-generation': 'Content Generation',
  classification: 'Classification',
  'sentiment-analysis': 'Sentiment Analysis',
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

// ─── Agent Detail Page ────────────────────────────────────────

export default function AgentDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = params?.id as string;

  const [agent, setAgent] = useState<Agent | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [conversationsLoading, setConversationsLoading] = useState(false);

  const [contents, setContents] = useState<GenerationResult[]>([]);
  const [contentsLoading, setContentsLoading] = useState(false);

  const [runDialogOpen, setRunDialogOpen] = useState(false);
  const [runInput, setRunInput] = useState('');
  const [isRunning, setIsRunning] = useState(false);

  const [editConfig, setEditConfig] = useState(false);
  const [editModel, setEditModel] = useState('');
  const [editTemperature, setEditTemperature] = useState('');
  const [editMaxTokens, setEditMaxTokens] = useState('');
  const [savingConfig, setSavingConfig] = useState(false);

  const fetchAgent = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await aiApi.getAgent(id);
      setAgent(res.data);
      setEditModel(res.data.model || '');
      setEditTemperature(String(res.data.temperature || 0.7));
      setEditMaxTokens(String(res.data.max_tokens || 2048));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load agent');
    } finally {
      setLoading(false);
    }
  }, [id]);

  const fetchConversations = useCallback(async () => {
    setConversationsLoading(true);
    try {
      const res = await aiApi.listConversations(id, { page: 1, limit: 10 });
      setConversations(res.data || []);
    } catch {
      setConversations([]);
    } finally {
      setConversationsLoading(false);
    }
  }, [id]);

  const fetchContents = useCallback(async () => {
    setContentsLoading(true);
    try {
      const res = await aiApi.listGenerations({ limit: 10 });
      setContents(res.data || []);
    } catch {
      setContents([]);
    } finally {
      setContentsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (id) {
      fetchAgent();
      fetchConversations();
      fetchContents();
    }
  }, [id, fetchAgent, fetchConversations, fetchContents]);

  const handleRun = async () => {
    if (!runInput.trim()) {
      toast.error('Please enter input for the agent');
      return;
    }
    setIsRunning(true);
    try {
      await aiApi.runAgent(id, { input: runInput });
      toast.success('Agent executed successfully');
      setRunDialogOpen(false);
      setRunInput('');
      fetchAgent();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to run agent');
    } finally {
      setIsRunning(false);
    }
  };

  const handleSaveConfig = async () => {
    setSavingConfig(true);
    try {
      await aiApi.updateAgent(id, {
        model: editModel,
        temperature: parseFloat(editTemperature),
        max_tokens: parseInt(editMaxTokens, 10),
      });
      toast.success('Agent configuration updated');
      setEditConfig(false);
      fetchAgent();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to update config');
    } finally {
      setSavingConfig(false);
    }
  };

  const handleToggleStatus = async () => {
    if (!agent) return;
    const newStatus = agent.status === 'paused' ? 'idle' : 'paused';
    try {
      await aiApi.updateAgent(id, { status: newStatus });
      toast.success(`Agent ${newStatus === 'paused' ? 'paused' : 'resumed'}`);
      fetchAgent();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to update status');
    }
  };

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
        <Skeleton className="h-48 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  // Error state
  if (error || !agent) {
    return (
      <div className="flex flex-col items-center justify-center py-24">
        <Bot className="h-12 w-12 text-muted-foreground mb-4" />
        <p className="text-muted-foreground mb-2">Agent not found</p>
        <p className="text-sm text-destructive mb-4">{error}</p>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => router.back()}>
            Go Back
          </Button>
          <Button variant="link" onClick={() => router.push('/ai-suite')}>
            Back to AI Suite
          </Button>
        </div>
      </div>
    );
  }

  const StatusIcon = statusConfig[agent.status]?.label === 'Running' ? Activity
    : agent.status === 'error' ? XCircle
    : agent.status === 'paused' ? Pause
    : CheckCircle2;
  const statusClass = statusConfig[agent.status]?.className || '';

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
              <h1 className="text-2xl font-bold">{agent.name}</h1>
              <Badge variant="outline" className={`gap-1 ${statusClass}`}>
                <StatusIcon className="h-3 w-3" />
                {statusConfig[agent.status]?.label || agent.status}
              </Badge>
            </div>
            <p className="text-muted-foreground text-sm mt-1">
              {agent.description || 'No description provided'}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant={agent.status === 'paused' ? 'default' : 'outline'}
            size="sm"
            onClick={handleToggleStatus}
          >
            {agent.status === 'paused' ? (
              <><Play className="mr-2 h-4 w-4" /> Resume</>
            ) : (
              <><Pause className="mr-2 h-4 w-4" /> Pause</>
            )}
          </Button>
          <Button size="sm" onClick={() => setRunDialogOpen(true)}>
            <Play className="mr-2 h-4 w-4" /> Run Agent
          </Button>
        </div>
      </div>

      {/* Capability badges */}
      <div className="flex flex-wrap gap-2">
        {agent.capabilities.map((cap) => (
          <Badge key={cap} variant="secondary">
            {capabilityLabels[cap] || cap}
          </Badge>
        ))}
      </div>

      {/* Tabs */}
      <Tabs defaultValue="overview" className="space-y-4">
        <TabsList>
          <TabsTrigger value="overview">
            <BarChart3 className="mr-2 h-4 w-4" /> Overview
          </TabsTrigger>
          <TabsTrigger value="conversations">
            <MessageSquare className="mr-2 h-4 w-4" /> Conversations
          </TabsTrigger>
          <TabsTrigger value="content">
            <FileText className="mr-2 h-4 w-4" /> Content
          </TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview" className="space-y-4">
          {/* Stats */}
          <div className="grid gap-4 md:grid-cols-3">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Total Runs</CardTitle>
                <Zap className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">156</div>
                <p className="text-xs text-muted-foreground">+8 this week</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Success Rate</CardTitle>
                <CheckCircle2 className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">97.4%</div>
                <p className="text-xs text-muted-foreground">4 failures</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Avg Response Time</CardTitle>
                <Clock className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">1.4s</div>
                <p className="text-xs text-muted-foreground">P95: 3.1s</p>
              </CardContent>
            </Card>
          </div>

          {/* Config Card */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle className="text-lg">Configuration</CardTitle>
                <CardDescription>
                  Model and generation parameters
                </CardDescription>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setEditConfig(!editConfig)}
              >
                <Edit3 className="mr-2 h-4 w-4" />
                {editConfig ? 'Cancel' : 'Edit'}
              </Button>
            </CardHeader>
            <CardContent>
              {editConfig ? (
                <div className="space-y-4">
                  <div className="grid grid-cols-3 gap-4">
                    <div className="space-y-2">
                      <Label>Model</Label>
                      <Select value={editModel} onValueChange={setEditModel}>
                        <SelectTrigger>
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
                      <Label>Temperature</Label>
                      <Input
                        type="number"
                        min={0}
                        max={2}
                        step={0.1}
                        value={editTemperature}
                        onChange={(e) => setEditTemperature(e.target.value)}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>Max Tokens</Label>
                      <Input
                        type="number"
                        min={256}
                        max={8192}
                        step={256}
                        value={editMaxTokens}
                        onChange={(e) => setEditMaxTokens(e.target.value)}
                      />
                    </div>
                  </div>
                  <Button onClick={handleSaveConfig} disabled={savingConfig}>
                    {savingConfig ? (
                      <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Saving...</>
                    ) : (
                      <><Save className="mr-2 h-4 w-4" /> Save Configuration</>
                    )}
                  </Button>
                </div>
              ) : (
                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <p className="text-sm text-muted-foreground">Model</p>
                    <p className="text-sm font-medium">{agent.model || 'gpt-4'}</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Temperature</p>
                    <p className="text-sm font-medium">{agent.temperature ?? 0.7}</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Max Tokens</p>
                    <p className="text-sm font-medium">{agent.max_tokens ?? 2048}</p>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Agent metadata */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Details</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-muted-foreground">Created</p>
                  <p className="text-sm font-medium">{formatDateTime(agent.created_at)}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Last Run</p>
                  <p className="text-sm font-medium">
                    {agent.last_run_at ? formatDateTime(agent.last_run_at) : 'Never'}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Updated</p>
                  <p className="text-sm font-medium">{formatDateTime(agent.updated_at)}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Active</p>
                  <p className="text-sm font-medium">{agent.is_active ? 'Yes' : 'No'}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Conversations Tab */}
        <TabsContent value="conversations" className="space-y-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle className="text-lg">Conversations</CardTitle>
                <CardDescription>
                  Recent conversations with this agent
                </CardDescription>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={() => router.push('/ai-suite/content')}
              >
                <MessageSquare className="mr-2 h-4 w-4" />
                New Conversation
              </Button>
            </CardHeader>
            <CardContent className="p-0">
              {conversationsLoading ? (
                <div className="p-6 space-y-4">
                  {Array.from({ length: 3 }).map((_, i) => (
                    <Skeleton key={i} className="h-16 w-full" />
                  ))}
                </div>
              ) : conversations.length === 0 ? (
                <div className="p-6 text-center text-muted-foreground">
                  <MessageSquare className="h-8 w-8 mx-auto mb-3 opacity-50" />
                  <p>No conversations yet</p>
                  <Button variant="link" onClick={() => router.push('/ai-suite/content')}>
                    Start a conversation
                  </Button>
                </div>
              ) : (
                <div className="divide-y">
                  {conversations.map((conv) => (
                    <div
                      key={conv.id}
                      className="flex items-center justify-between px-6 py-4 hover:bg-muted/50 cursor-pointer transition-colors"
                      onClick={() => router.push(`/ai-suite/conversations/${conv.id}`)}
                    >
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate">{conv.title}</p>
                        <p className="text-xs text-muted-foreground">
                          {conv.messages?.length || 0} messages · {formatDateTime(conv.created_at)}
                        </p>
                      </div>
                      <Badge variant="outline" className="ml-4 capitalize">
                        {conv.status}
                      </Badge>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Content Tab */}
        <TabsContent value="content" className="space-y-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle className="text-lg">Generated Content</CardTitle>
                <CardDescription>
                  Content created by this agent
                </CardDescription>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={() => router.push('/ai-suite/content')}
              >
                <FileText className="mr-2 h-4 w-4" />
                Generate Content
              </Button>
            </CardHeader>
            <CardContent className="p-0">
              {contentsLoading ? (
                <div className="p-6 space-y-4">
                  {Array.from({ length: 3 }).map((_, i) => (
                    <Skeleton key={i} className="h-16 w-full" />
                  ))}
                </div>
              ) : contents.length === 0 ? (
                <div className="p-6 text-center text-muted-foreground">
                  <FileText className="h-8 w-8 mx-auto mb-3 opacity-50" />
                  <p>No generated content yet</p>
                  <Button variant="link" onClick={() => router.push('/ai-suite/content')}>
                    Generate your first piece of content
                  </Button>
                </div>
              ) : (
                <div className="divide-y">
                  {contents.map((gen) => (
                    <div key={gen.id} className="px-6 py-4">
                      <div className="flex items-center justify-between mb-1">
                        <Badge variant="secondary" className="text-xs capitalize">
                          {gen.content_type.replace(/_/g, ' ')}
                        </Badge>
                        <span className="text-xs text-muted-foreground">
                          {formatDateTime(gen.created_at)}
                        </span>
                      </div>
                      <p className="text-sm text-muted-foreground line-clamp-2 mt-1">
                        {gen.content.substring(0, 200)}
                      </p>
                      <div className="flex items-center gap-3 mt-2 text-xs text-muted-foreground">
                        <span>Model: {gen.model}</span>
                        <span>{gen.tokens_used} tokens</span>
                        <span>{(gen.processing_time_ms / 1000).toFixed(1)}s</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Run Agent Dialog */}
      <Dialog open={runDialogOpen} onOpenChange={setRunDialogOpen}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle>Run Agent: {agent.name}</DialogTitle>
            <DialogDescription>
              Provide input for the agent to process
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <Label htmlFor="run-input">Input</Label>
            <textarea
              id="run-input"
              className="flex min-h-[120px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 mt-2"
              placeholder="Describe what you want the agent to do..."
              value={runInput}
              onChange={(e) => setRunInput(e.target.value)}
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setRunDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleRun} disabled={isRunning || !runInput.trim()}>
              {isRunning ? (
                <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Running...</>
              ) : (
                <><Play className="mr-2 h-4 w-4" /> Run Agent</>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
