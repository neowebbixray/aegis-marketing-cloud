'use client';

import { useState } from 'react';
import { usePipelines, useCreatePipeline, useUpdatePipeline, useDeletePipeline, useReorderStages } from '@/hooks/use-deals';
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
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/molecules/dropdown-menu';
import { Separator } from '@/components/atoms/separator';
import { Skeleton } from '@/components/atoms/skeleton';
import {
  Plus,
  MoreHorizontal,
  Edit,
  Trash2,
  GripVertical,
  ArrowUp,
  ArrowDown,
} from 'lucide-react';
import { toast } from 'sonner';
import type { Pipeline, PipelineStage } from '@/types';

// ─── Stage Badge ──────────────────────────────────────────

function StageBadge({ stage }: { stage: PipelineStage }) {
  return (
    <div className="flex items-center justify-between p-3 rounded-lg border bg-card">
      <div className="flex items-center gap-3">
        <GripVertical className="h-4 w-4 text-muted-foreground cursor-grab" />
        <div className="w-3 h-3 rounded-full" style={{ backgroundColor: stage.colour ?? undefined }} />
        <div>
          <p className="text-sm font-medium">{stage.name}</p>
          <p className="text-xs text-muted-foreground">
            Order: {stage.order} · Probability: {stage.probability}%
          </p>
        </div>
      </div>
    </div>
  );
}

// ─── Pipeline Card ────────────────────────────────────────

function PipelineCard({
  pipeline,
  onEdit,
  onDelete,
}: {
  pipeline: Pipeline;
  onEdit: () => void;
  onDelete: () => void;
}) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-start justify-between space-y-0 pb-2">
        <div>
          <CardTitle className="text-lg">{pipeline.name}</CardTitle>
          {pipeline.description && (
            <CardDescription>{pipeline.description}</CardDescription>
          )}
        </div>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon-sm">
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={onEdit}>
              <Edit className="mr-2 h-4 w-4" />
              Edit
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={onDelete} className="text-destructive">
              <Trash2 className="mr-2 h-4 w-4" />
              Delete
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          {pipeline.is_default && (
            <Badge variant="secondary" className="mb-2">Default</Badge>
          )}
          {pipeline.stages
            .sort((a, b) => a.order - b.order)
            .map((stage) => (
              <StageBadge key={stage.id} stage={stage} />
            ))}
        </div>
      </CardContent>
    </Card>
  );
}

// ─── Create Pipeline Dialog ───────────────────────────────

function CreatePipelineDialog({
  open,
  onOpenChange,
  editPipeline,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  editPipeline?: Pipeline | null;
}) {
  const createPipeline = useCreatePipeline();
  const updatePipeline = useUpdatePipeline(editPipeline?.id ?? '');
  const [name, setName] = useState(editPipeline?.name ?? '');
  const [description, setDescription] = useState(editPipeline?.description ?? '');
  const [stages, setStages] = useState<{ name: string; color: string; probability: number }[]>(
    editPipeline?.stages.map((s) => ({ name: s.name, color: s.colour ?? '#6B7280', probability: s.probability ?? 0 })) ?? [
      { name: 'Lead In', color: '#6B7280', probability: 10 },
      { name: 'Qualified', color: '#3B82F6', probability: 30 },
      { name: 'Proposal', color: '#F59E0B', probability: 60 },
      { name: 'Negotiation', color: '#8B5CF6', probability: 80 },
      { name: 'Closed Won', color: '#22C55E', probability: 100 },
    ]
  );

  const handleSubmit = async () => {
    if (!name.trim()) {
      toast.error('Pipeline name is required');
      return;
    }

    try {
      const payload = {
        name,
        description,
        stages: stages.map((s) => ({ name: s.name, colour: s.color, probability: s.probability })),
      };
      if (editPipeline) {
        await updatePipeline.mutateAsync(payload);
        toast.success('Pipeline updated');
      } else {
        await createPipeline.mutateAsync(payload);
        toast.success('Pipeline created');
      }
      onOpenChange(false);
    } catch (error: any) {
      toast.error(error?.message || 'Failed to save pipeline');
    }
  };

  const addStage = () => {
    setStages([...stages, { name: '', color: '#6B7280', probability: 0 }]);
  };

  const removeStage = (index: number) => {
    setStages(stages.filter((_, i) => i !== index));
  };

  const updateStage = (index: number, field: string, value: string | number) => {
    const updated = [...stages];
    (updated[index] as any)[field] = value;
    setStages(updated);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[600px]">
        <DialogHeader>
          <DialogTitle>{editPipeline ? 'Edit Pipeline' : 'Create Pipeline'}</DialogTitle>
          <DialogDescription>
            {editPipeline
              ? 'Modify your pipeline name, description, and stages.'
              : 'Define a new pipeline with custom stages for your sales process.'}
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label htmlFor="pipeline-name">Name</Label>
            <Input
              id="pipeline-name"
              placeholder="e.g., Sales Pipeline"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="pipeline-desc">Description (optional)</Label>
            <Input
              id="pipeline-desc"
              placeholder="Describe your pipeline"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>

          <Separator />

          <div className="flex items-center justify-between">
            <Label>Stages</Label>
            <Button type="button" variant="outline" size="sm" onClick={addStage}>
              <Plus className="mr-2 h-3 w-3" />
              Add Stage
            </Button>
          </div>

          <div className="space-y-3 max-h-[300px] overflow-y-auto">
            {stages.map((stage, index) => (
              <div key={index} className="flex items-center gap-2 p-2 rounded-lg border">
                <GripVertical className="h-4 w-4 text-muted-foreground shrink-0" />
                <Input
                  placeholder="Stage name"
                  value={stage.name}
                  onChange={(e) => updateStage(index, 'name', e.target.value)}
                  className="flex-1 h-8 text-sm"
                />
                <input
                  type="color"
                  value={stage.color}
                  onChange={(e) => updateStage(index, 'color', e.target.value)}
                  className="w-8 h-8 rounded cursor-pointer"
                />
                <Input
                  type="number"
                  placeholder="Prob %"
                  value={stage.probability}
                  onChange={(e) => updateStage(index, 'probability', parseInt(e.target.value) || 0)}
                  className="w-20 h-8 text-sm"
                  min={0}
                  max={100}
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="icon-sm"
                  onClick={() => removeStage(index)}
                  disabled={stages.length <= 1}
                >
                  <Trash2 className="h-3 w-3 text-destructive" />
                </Button>
              </div>
            ))}
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={createPipeline.isPending || updatePipeline.isPending}>
            {editPipeline ? 'Update Pipeline' : 'Create Pipeline'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ─── Pipelines Page ───────────────────────────────────────

export default function PipelinesPage() {
  const { data, isLoading, error } = usePipelines();
  const deletePipeline = useDeletePipeline();
  const pipelines = data?.data ?? [];
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [editPipeline, setEditPipeline] = useState<Pipeline | null>(null);

  const handleDelete = async (pipeline: Pipeline) => {
    if (!confirm(`Delete "${pipeline.name}"? This action cannot be undone.`)) return;
    try {
      await deletePipeline.mutateAsync(pipeline.id);
      toast.success('Pipeline deleted');
    } catch (error: any) {
      toast.error(error?.message || 'Failed to delete pipeline');
    }
  };

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Pipelines</h1>
          <p className="text-muted-foreground mt-1">
            Manage your sales pipelines and stages
          </p>
        </div>
        <Button onClick={() => { setEditPipeline(null); setCreateDialogOpen(true); }}>
          <Plus className="mr-2 h-4 w-4" />
          New Pipeline
        </Button>
      </div>

      {/* Pipeline List */}
      {isLoading ? (
        <div className="grid gap-6 md:grid-cols-2">
          {Array.from({ length: 2 }).map((_, i) => (
            <Card key={i}>
              <CardHeader>
                <Skeleton className="h-6 w-40" />
                <Skeleton className="h-4 w-60" />
              </CardHeader>
              <CardContent className="space-y-2">
                <Skeleton className="h-12 w-full" />
                <Skeleton className="h-12 w-full" />
                <Skeleton className="h-12 w-full" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : pipelines.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <p className="text-muted-foreground mb-4">
              No pipelines yet. Create your first pipeline to start tracking deals.
            </p>
            <Button onClick={() => setCreateDialogOpen(true)}>
              <Plus className="mr-2 h-4 w-4" />
              Create Pipeline
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-6 md:grid-cols-2">
          {pipelines.map((pipeline: Pipeline) => (
            <PipelineCard
              key={pipeline.id}
              pipeline={pipeline}
              onEdit={() => {
                setEditPipeline(pipeline);
                setCreateDialogOpen(true);
              }}
              onDelete={() => handleDelete(pipeline)}
            />
          ))}
        </div>
      )}

      {/* Create/Edit Dialog */}
      <CreatePipelineDialog
        open={createDialogOpen}
        onOpenChange={setCreateDialogOpen}
        editPipeline={editPipeline}
      />
    </div>
  );
}
