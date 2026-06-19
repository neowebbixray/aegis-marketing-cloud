import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { Workspace } from '@/types';

interface WorkspaceState {
  workspaces: Workspace[];
  currentWorkspace: Workspace | null;
  isLoading: boolean;
  setWorkspaces: (workspaces: Workspace[]) => void;
  setCurrentWorkspace: (workspace: Workspace) => void;
  switchWorkspace: (workspaceId: string) => void;
  setLoading: (loading: boolean) => void;
  clear: () => void;
}

export const useWorkspaceStore = create<WorkspaceState>()(
  persist(
    (set, get) => ({
      workspaces: [],
      currentWorkspace: null,
      isLoading: false,

      setWorkspaces: (workspaces) => {
        const { currentWorkspace } = get();
        // If we don't have a current workspace but workspaces exist, set the first/default one
        if (!currentWorkspace && workspaces.length > 0) {
          const defaultWs = workspaces.find((w) => w.is_default) || workspaces[0];
          set({ workspaces, currentWorkspace: defaultWs });
        } else {
          set({ workspaces });
        }
      },

      setCurrentWorkspace: (workspace) =>
        set({ currentWorkspace: workspace }),

      switchWorkspace: (workspaceId) => {
        const { workspaces } = get();
        const workspace = workspaces.find((w) => w.id === workspaceId);
        if (workspace) {
          set({ currentWorkspace: workspace });
        }
      },

      setLoading: (isLoading) => set({ isLoading }),

      clear: () => set({ workspaces: [], currentWorkspace: null }),
    }),
    {
      name: 'amc-workspace-storage',
      partialize: (state) => ({
        currentWorkspace: state.currentWorkspace,
        workspaces: state.workspaces,
      }),
    }
  )
);
