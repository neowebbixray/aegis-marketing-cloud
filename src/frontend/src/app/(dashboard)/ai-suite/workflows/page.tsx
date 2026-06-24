'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
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
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/molecules/table';
import { Separator } from '@/components/atoms/separator';
import { Skeleton } from '@/components/atoms/skeleton';
import { toast } from 'sonner';
import { workflowsApi } from '@/lib/api/workflows';
import type { Workflow, WorkflowExecution } from '@/lib/api/workflows';
import { Zap, Clock, Loader2, RefreshCw, Menu, Check, X } from 'lucide-react';

// ─── Workflows Page ───────────────────────────────────────

export default function WorkflowsPage() {
  const router = useRouter();
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [executions, setExecutions] = useState<WorkflowExecution[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedWorkflowId, setSelectedWorkflowId] = useState<string | null>(null);
  const [triggerDialogOpen, setTriggerDialogOpen] = useState(false);
  const [triggerPayload, setTriggerPayload] = useState<string>('');
  const [triggering, setTriggering] = useState(false);
  const [executionsLoading, setExecutionsLoading] = useState(false);

  // Fetch workflows
  const fetchWorkflows = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await workflowsApi.list({ limit: 100 });
      setWorkflows(res.data);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'Failed to load workflows'
      );
      setWorkflows([]);
    } finally {
      setLoading(false);
    }
  };

  // Fetch executions for selected workflow
  const fetchExecutions = async (workflowId: string) => {
    setExecutionsLoading(true);
    try {
      const res = await workflowsApi.getExecutions(workflowId, {
        limit: 50,
      });
      setExecutions(res.data);
    } catch (err) {
      console.error('Failed to load executions:', err);
      setExecutions([]);
    } finally {
      setExecutionsLoading(false);
    }
  };

  // Trigger workflow
  const handleTrigger = async () => {
    if (!selectedWorkflowId) return;
    setTriggering(true);
    try {
      const payload = triggerPayload.trim()
        ? JSON.parse(triggerPayload)
        : {};
      const res = await workflowsApi.trigger(selectedWorkflowId, payload);
      toast.success('Workflow triggered successfully');
      setTriggerDialogOpen(false);
      setTriggerPayload('');
      // Refresh executions after triggering
      await fetchExecutions(selectedWorkflowId);
    } catch (err) {
      toast.error(
        err instanceof Error ? err.message : 'Failed to trigger workflow'
      );
    } finally {
      setTriggering(false);
    }
  };

  // Effect to load workflows on mount
  useEffect(() => {
    fetchWorkflows();
  }, []);

  // Effect to load executions when selected workflow changes
  useEffect(() => {
    if (selectedWorkflowId) {
      fetchExecutions(selectedWorkflowId);
    } else {
      setExecutions([]);
    }
  }, [selectedWorkflowId]);

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-primary/10">
              <Zap className="h-6 w-6 text-primary" />
            </div>
            <div>
              <h1 className="text-3xl font-bold tracking-tight">
                Workflows
              </h1>
              <p className="text-muted-foreground mt-1">
                Automate your marketing processes with n8n workflows
              </p>
            </div>
          </div>
          <Button variant="outline" onClick={() => router.push('/ai-suite')}>
            <RefreshCw className="mr-2 h-4 w-4" /> Back to AI Suite
          </Button>
        </div>

        {/* Loading Skeletons */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {[...Array(6)].map((_, i) => (
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
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-16">
        <Zap className="h-12 w-12 text-muted-foreground mb-4" />
        <p className="text-muted-foreground mb-2">Failed to load workflows</p>
        <p className="text-sm text-destructive mb-4">{error}</p>
        <Button variant="outline" onClick={fetchWorkflows}>
          Retry
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-primary/10">
            <Zap className="h-6 w-6 text-primary" />
          </div>
          <div>
            <h1 className="text-3xl font-bold tracking-tight">
              Workflows
            </h1>
            <p className="text-muted-foreground mt-1">
              Automate your marketing processes with n8n workflows
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={() => router.push('/ai-suite')}>
            <RefreshCw className="mr-2 h-4 w-4" /> Back to AI Suite
          </Button>
          <Button onClick={fetchWorkflows}>
            <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Refresh
          </Button>
        </div>
      </div>

      {/* Workflows Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {workflows.map((workflow) => (
          <Card
            key={workflow.id}
            className="hover:shadow-md transition-shadow cursor-pointer"
            onClick={() => {
              setSelectedWorkflowId(workflow.id);
            }}
          >
            <CardHeader>
              <div className="flex items-start justify-between">
                <div className="p-2 rounded-lg bg-primary/10">
                  <Zap className="h-5 w-5 text-primary" />
                </div>
                <Badge
                  variant={workflow.active ? 'outline' : 'secondary'}
                  className={workflow.active
                    ? 'bg-success-100 text-success-800 dark:bg-success-900 dark:text-success-100'
                    : 'bg-muted text-muted-foreground'}
                >
                  {workflow.active ? 'Active' : 'Inactive'}
                </Badge>
              </div>
              <div className="mt-3">
                <h2 className="font-semibold">{workflow.name}</h2>
                <p className="text-sm text-muted-foreground mt-1">
                  ID: {workflow.id}
                </p>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <div className="text-xs text-muted-foreground">
                  <Strong>Nodes:</Strong> {(workflow.nodes || []).length}
                </div>
                <div className="text-xs text-muted-foreground">
                  <Strong>Connections:</Strong> {Object.keys(workflow.connections || {}).length}
                </div>
                <div className="text-xs text-muted-foreground">
                  <Strong>Version:</Strong> {workflow.versionId}
                </div>
                <div className="text-xs text-muted-foreground">
                  <Strong>Updated:</Strong>{' '}
                  {workflow.updatedAt ? new Date(workflow.updatedAt).toLocaleString() : '-'}
                </div>
              </div>
            </CardContent>
            <CardFooter className="border-t pt-4">
              <Button
                variant="ghost"
                size="sm"
                onClick={(e) => {
                  e.stopPropagation(); // Prevent card click
                  setSelectedWorkflowId(workflow.id);
                  setTriggerDialogOpen(true);
                }}
              >
                Trigger Workflow
              </Button>
            </CardFooter>
          </Card>
        ))}
      </div>

      {/* Executions Section */}
      {selectedWorkflowId && (
        <div className="border-t pt-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold">
              Executions
            </h2>
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                setSelectedWorkflowId(null);
              }}
            >
              <X className="mr-2 h-4 w-4" /> Back to Workflows
            </Button>
          </div>

          {executionsLoading ? (
            <div className="flex flex-col items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin" />
              <p className="mt-2 text-muted-foreground">Loading executions...</p>
            </div>
          ) : executions.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-8">
              <Zap className="h-8 w-8 text-muted-foreground mb-4" />
              <p className="text-muted-foreground">No executions found</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>ID</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Started</TableHead>
                    <TableHead>Finished</TableHead>
                    <TableHead>Mode</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {executions.map((exec) => (
                    <TableRow key={exec.id}>
                      <TableCell>
                        {exec.id.substring(0, 8)}...
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant={exec.status === 'completed' ? 'outline' : exec.status === 'failed' ? 'destructive' : 'secondary'}
                          className={
                            exec.status === 'completed'
                              ? 'bg-success-100 text-success-800 dark:bg-success-900 dark:text-success-100'
                              : exec.status === 'failed'
                              ? 'bg-destructive/10 text-destructive'
                              : 'bg-muted text-muted-foreground'
                          }
                        >
                          {exec.status}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        {exec.startedAt ? new Date(exec.startedAt).toLocaleString() : '-'}
                      </TableCell>
                      <TableCell>
                        {exec.stoppedAt ? new Date(exec.stoppedAt).toLocaleString() : '-'}
                      </TableCell>
                      <TableCell>
                        {exec.mode}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </div>
      )}

      {/* Trigger Workflow Dialog */}
      <Dialog open={triggerDialogOpen} onOpenChange={setTriggerDialogOpen}>
        <DialogContent className="sm:max-w-[500px] max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Trigger Workflow</DialogTitle>
            <DialogDescription>
              Provide input data (JSON) for the workflow execution
            </DialogDescription>
          </DialogHeader>
          <Separator />
          <div className="space-y-4">
            <div className="space-y-2">
              <label className="block text-sm font-medium text-muted-foreground">
                Workflow ID
              </label>
              <p className="font-mono text-sm bg-muted p-2 rounded">
                {selectedWorkflowId || 'None'}
              </p>
            </div>
            <div className="space-y-2">
              <label className="block text-sm font-medium text-muted-foreground">
                Payload (JSON)
              </label>
              <textarea
                value={triggerPayload}
                onChange={(e) => setTriggerPayload(e.target.value)}
                placeholder='{"key": "value"}'
                className="w-full min-h-[80px] rounded-border border-input bg-background text-input ring-offset-background placeholder:text-muted-foreground focus-visible:ring-ring focus-visible:ring-2 disabled:cursor-not-allowed disabled:opacity-50"
                rows={4}
                disabled={triggering}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setTriggerDialogOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleTrigger}
              disabled={triggering}
              className="ml-2"
            >
              {triggering ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Triggering...
                </>
              ) : (
                <>
                  <Zap className="mr-2 h-4 w-4" />
                  Trigger Workflow
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

// Helper component for bold text in descriptions
function Strong({ children }: { children: React.ReactNode }) {
  return <span className="font-medium">{children}</span>;
}