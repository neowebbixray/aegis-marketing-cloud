'use client';

import { useState } from 'react';
import { useDeals } from '@/hooks/use-deals';
import { usePipelines } from '@/hooks/use-deals';
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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/molecules/select';
import { Skeleton } from '@/components/atoms/skeleton';
import { formatCurrency, formatDate, getInitials } from '@/lib/utils';
import { Plus, GripVertical } from 'lucide-react';
import type { Deal, Pipeline, PipelineStage } from '@/types';

// ─── Deal Card ────────────────────────────────────────────

function DealCard({ deal }: { deal: Deal }) {
  const probabilityColor =
    deal.probability >= 80
      ? 'bg-success-500'
      : deal.probability >= 50
      ? 'bg-warning-500'
      : 'bg-muted-foreground/30';

  return (
    <Card className="cursor-grab active:cursor-grabbing hover:shadow-md transition-shadow">
      <CardContent className="p-3 space-y-2">
        <div className="flex items-start justify-between">
          <p className="text-sm font-semibold leading-tight">{deal.name}</p>
          <GripVertical className="h-4 w-4 text-muted-foreground shrink-0" />
        </div>
        <p className="text-lg font-bold text-primary">
          {formatCurrency(deal.value, deal.currency)}
        </p>
        {deal.contact && (
          <p className="text-xs text-muted-foreground">
            {deal.contact.first_name} {deal.contact.last_name}
          </p>
        )}
        <div className="flex items-center gap-2">
          <div className="flex-1 h-1.5 rounded-full bg-muted overflow-hidden">
            <div
              className={`h-full rounded-full ${probabilityColor}`}
              style={{ width: `${deal.probability}%` }}
            />
          </div>
          <span className="text-xs text-muted-foreground">{deal.probability}%</span>
        </div>
        {deal.expected_close_date && (
          <p className="text-xs text-muted-foreground">
            Close: {formatDate(deal.expected_close_date)}
          </p>
        )}
      </CardContent>
    </Card>
  );
}

// ─── Pipeline Column ──────────────────────────────────────

function PipelineColumn({
  stage,
  deals,
}: {
  stage: PipelineStage;
  deals: Deal[];
}) {
  return (
    <div className="flex-shrink-0 w-72">
      <div className="flex items-center justify-between mb-3 px-1">
        <div className="flex items-center gap-2">
          <div
            className="w-2.5 h-2.5 rounded-full"
            style={{ backgroundColor: stage.color }}
          />
          <h3 className="font-semibold text-sm">{stage.name}</h3>
        </div>
        <Badge variant="secondary" className="text-xs">
          {deals.length}
        </Badge>
      </div>
      <div className="space-y-2 min-h-[200px]">
        {deals.length === 0 ? (
          <div className="flex items-center justify-center h-24 border-2 border-dashed rounded-lg text-xs text-muted-foreground">
            Drop deals here
          </div>
        ) : (
          deals.map((deal) => <DealCard key={deal.id} deal={deal} />)
        )}
      </div>
    </div>
  );
}

// ─── Deals Kanban Page ────────────────────────────────────

export default function DealsPage() {
  const [selectedPipelineId, setSelectedPipelineId] = useState<string>('');

  const { data: pipelinesData, isLoading: pipelinesLoading } = usePipelines();
  const pipelines = pipelinesData?.data ?? [];

  // Auto-select first pipeline on load
  const effectivePipelineId = selectedPipelineId || pipelines[0]?.id || '';
  if (!selectedPipelineId && pipelines.length > 0) {
    setSelectedPipelineId(pipelines[0].id);
  }

  const { data: dealsData, isLoading: dealsLoading } = useDeals({
    pipeline_id: effectivePipelineId || undefined,
    limit: 100,
  });
  const deals = dealsData?.data ?? [];

  // Find current pipeline with its stages
  const currentPipeline = pipelines.find((p: Pipeline) => p.id === effectivePipelineId);
  const stages = currentPipeline?.stages ?? [];

  // Group deals by stage
  const dealsByStage: Record<string, Deal[]> = {};
  stages.forEach((stage: PipelineStage) => {
    dealsByStage[stage.id] = deals.filter((d: Deal) => d.pipeline_stage_id === stage.id);
  });

  const isLoading = pipelinesLoading || dealsLoading;

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Deals</h1>
          <p className="text-muted-foreground mt-1">
            Manage your deal pipeline and track opportunities
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Select value={effectivePipelineId} onValueChange={setSelectedPipelineId}>
            <SelectTrigger className="w-[200px]">
              <SelectValue placeholder="Select pipeline" />
            </SelectTrigger>
            <SelectContent>
              {pipelines.map((p: Pipeline) => (
                <SelectItem key={p.id} value={p.id}>
                  {p.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button>
            <Plus className="mr-2 h-4 w-4" />
            New Deal
          </Button>
        </div>
      </div>

      {/* Kanban Board */}
      {isLoading ? (
        <div className="flex gap-4 overflow-x-auto pb-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="flex-shrink-0 w-72 space-y-3">
              <Skeleton className="h-6 w-24" />
              <Skeleton className="h-32 w-full" />
              <Skeleton className="h-32 w-full" />
            </div>
          ))}
        </div>
      ) : stages.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <p className="text-muted-foreground">
              {pipelines.length === 0
                ? 'No pipelines configured. Create a pipeline first.'
                : 'No stages found in this pipeline.'}
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="flex gap-4 overflow-x-auto pb-4">
          {stages
            .sort((a: PipelineStage, b: PipelineStage) => a.order - b.order)
            .map((stage: PipelineStage) => (
              <PipelineColumn
                key={stage.id}
                stage={stage}
                deals={dealsByStage[stage.id] || []}
              />
            ))}
        </div>
      )}
    </div>
  );
}
