import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { workspaceApi } from '@/lib/api';
import { useWorkspaceStore } from '@/stores/workspace-store';
import type { Workspace } from '@/types';

export function useWorkspaces() {
  const queryClient = useQueryClient();
  const { setWorkspaces, setLoading } = useWorkspaceStore();

  const query = useQuery({
    queryKey: ['workspaces'],
    queryFn: async () => {
      setLoading(true);
      try {
        // Backend returns Workspace[] directly
        const workspaces = await workspaceApi.list() as unknown as Workspace[];
        setWorkspaces(workspaces);
        return workspaces;
      } finally {
        setLoading(false);
      }
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: 1,
  });

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['workspaces'] });
  };

  return {
    workspaces: query.data ?? [],
    isLoading: query.isLoading,
    error: query.error,
    refetch: query.refetch,
    invalidate,
  };
}

export function useWorkspace(id: string | undefined) {
  return useQuery({
    queryKey: ['workspaces', id],
    queryFn: () => workspaceApi.get(id!),
    enabled: !!id,
    staleTime: 5 * 60 * 1000,
  });
}
