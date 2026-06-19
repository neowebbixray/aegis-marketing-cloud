import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { contactsApi } from '@/lib/api';
import type { Contact, CreateContactRequest, UpdateContactRequest } from '@/types';

// ─── Contact List ─────────────────────────────────────────

interface UseContactsParams {
  page?: number;
  limit?: number;
  search?: string;
  stage?: string;
  source?: string;
  owner_id?: string;
  sort?: string;
}

export function useContacts(params?: UseContactsParams) {
  return useQuery({
    queryKey: ['contacts', params],
    queryFn: () => contactsApi.list(params as Record<string, string | number | boolean | undefined>),
    staleTime: 30 * 1000, // 30 seconds
  });
}

// ─── Contact Detail ───────────────────────────────────────

export function useContact(id: string | undefined) {
  return useQuery({
    queryKey: ['contacts', id],
    queryFn: () => contactsApi.get(id!),
    enabled: !!id,
    staleTime: 30 * 1000,
  });
}

// ─── Contact Activities ───────────────────────────────────

export function useContactActivities(id: string | undefined) {
  return useQuery({
    queryKey: ['contacts', id, 'activities'],
    queryFn: () => contactsApi.getActivities(id!),
    enabled: !!id,
    staleTime: 15 * 1000,
  });
}

// ─── Create Contact ───────────────────────────────────────

export function useCreateContact() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CreateContactRequest) => contactsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['contacts'] });
    },
  });
}

// ─── Update Contact ───────────────────────────────────────

export function useUpdateContact(id: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: UpdateContactRequest) => contactsApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['contacts'] });
      queryClient.invalidateQueries({ queryKey: ['contacts', id] });
    },
  });
}

// ─── Delete Contact ───────────────────────────────────────

export function useDeleteContact() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => contactsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['contacts'] });
    },
  });
}

// ─── Search Contacts ──────────────────────────────────────

export function useSearchContacts() {
  return useMutation({
    mutationFn: ({ query, params }: { query: string; params?: { limit?: number; offset?: number } }) =>
      contactsApi.search(query, params),
  });
}
