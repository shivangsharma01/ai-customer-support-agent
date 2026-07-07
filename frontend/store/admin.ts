import { create } from "zustand";
import type { TraceEvent } from "@/lib/api";

interface AdminStore {
  events: TraceEvent[];
  selectedSession: string | null;
  connected: boolean;
  addEvent: (e: TraceEvent) => void;
  setConnected: (v: boolean) => void;
  selectSession: (id: string | null) => void;
}

export const useAdminStore = create<AdminStore>((set) => ({
  events: [],
  selectedSession: null,
  connected: false,

  addEvent: (e) =>
    set((s) => ({
      events: [...s.events.slice(-999), e],
      // Auto-follow the most recent session unless the user pinned one.
      selectedSession: s.selectedSession ?? e.session_id,
    })),
  setConnected: (v) => set({ connected: v }),
  selectSession: (id) => set({ selectedSession: id }),
}));
