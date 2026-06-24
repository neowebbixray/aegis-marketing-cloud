import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { customFieldsApi } from '@/lib/api/api';
import type {
  CustomFieldDefinition,
  CreateCustomFieldDefinitionRequest,
  UpdateCustomFieldDefinitionRequest,
} from '@/types';

// ─── Custom Field Definition List ───────────────────────

interface UseCustomFieldsParams {
  page?: number;
  limit?: number;
  search?: string;
  is_active?: boolean;
}

export function useCustomFields(params?: UseCustomFieldsParams) {
  return useQuery({
    queryKey: ['custom-fields', params],
    queryFn: () => customFieldsApi.list(params as Record<string, string | number | boolean | undefined>),
    staleTime: 30 * 1000, // 30 seconds
  });
}

// ─── Custom Field Definition Detail ─────────────────────

export function useCustomField(id: string | undefined) {
  return useQuery({
    queryKey: ['custom-fields', id],
    queryFn: () => customFieldsApi.get(id!),
    enabled: !!id,
    staleTime: 30 * 1000,
  });
}

// ─── Create Custom Field Definition ─────────────────────

export function useCreateCustomField() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CreateCustomFieldDefinitionRequest) => customFieldsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['custom-fields'] });
    },
  });
}

// ─── Update Custom Field Definition ─────────────────────

export function useUpdateCustomField(id: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: UpdateCustomFieldDefinitionRequest) => customFieldsApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['custom-fields'] });
      queryClient.invalidateQueries({ queryKey: ['custom-fields', id] });
    },
  });
}

// ─── Delete Custom Field Definition ─────────────────────

export function useDeleteCustomField() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => customFieldsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['custom-fields'] });
    },
  });
}