import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { dealsApi, pipelinesApi } from '@/lib/api';
import type { CreateDealRequest, UpdateDealRequest, CreatePipelineRequest } from '@/types';

// ─── Deals List ───────────────────────────────────────────

interface UseDealsParams {
  page?: number;
  limit?: number;
  pipeline_id?: string;
  stage?: string;
  search?: string;
  sort?: string;
}

export function useDeals(params?: UseDealsParams) {
  return useQuery({
    queryKey: ['deals', params],
    queryFn: () => dealsApi.list(params as Record<string, string | number | boolean | undefined>),
    staleTime: 30 * 1000,
  });
}

// ─── Deal Detail ──────────────────────────────────────────

export function useDeal(id: string | undefined) {
  return useQuery({
    queryKey: ['deals', id],
    queryFn: () => dealsApi.get(id!),
    enabled: !!id,
    staleTime: 30 * 1000,
  });
}

// ─── Create Deal ──────────────────────────────────────────

export function useCreateDeal() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CreateDealRequest) => dealsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['deals'] });
    },
  });
}

// ─── Update Deal ──────────────────────────────────────────

export function useUpdateDeal(id: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: UpdateDealRequest) => dealsApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['deals'] });
      queryClient.invalidateQueries({ queryKey: ['deals', id] });
    },
  });
}

// ─── Delete Deal ──────────────────────────────────────────

export function useDeleteDeal() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => dealsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['deals'] });
    },
  });
}

// ─── Pipelines ────────────────────────────────────────────

export function usePipelines() {
  return useQuery({
    queryKey: ['pipelines'],
    queryFn: () => pipelinesApi.list(),
    staleTime: 5 * 60 * 1000,
  });
}

export function usePipeline(id: string | undefined) {
  return useQuery({
    queryKey: ['pipelines', id],
    queryFn: () => pipelinesApi.get(id!),
    enabled: !!id,
    staleTime: 5 * 60 * 1000,
  });
}

export function useCreatePipeline() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CreatePipelineRequest) => pipelinesApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pipelines'] });
    },
  });
}

export function useUpdatePipeline(id: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: Partial<CreatePipelineRequest>) => pipelinesApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pipelines'] });
    },
  });
}

export function useDeletePipeline() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => pipelinesApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pipelines'] });
    },
  });
}

export function useReorderStages(pipelineId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (stageIds: string[]) => pipelinesApi.reorderStages(pipelineId, stageIds),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pipelines'] });
    },
  });
}
