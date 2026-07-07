import { create } from "zustand";
import { postChat, type PublicState } from "@/lib/api";

export interface ChatMessage {
  role: "user" | "agent";
  text: string;
  decision?: {
    decision: string;
    reason: string;
    rules: string[];
  };
}

interface ChatStore {
  customerId: string;
  sessionId: string | null;
  messages: ChatMessage[];
  sending: boolean;
  error: string | null;
  setCustomer: (id: string) => void;
  send: (text: string) => Promise<void>;
  addAgentTurn: (state: PublicState) => void;
}

export const useChatStore = create<ChatStore>((set, get) => ({
  customerId: "CUST-006",
  sessionId: null,
  messages: [],
  sending: false,
  error: null,

  setCustomer: (id) =>
    set({ customerId: id, sessionId: null, messages: [], error: null }),

  addAgentTurn: (state) =>
    set((s) => ({
      messages: [
        ...s.messages,
        {
          role: "agent",
          text: state.response ?? "",
          decision: state.final_decision
            ? {
                decision: state.final_decision,
                reason: state.decision_reason ?? "",
                rules: state.policy_rules_triggered ?? [],
              }
            : undefined,
        },
      ],
    })),

  send: async (text) => {
    const { customerId, sessionId } = get();
    set((s) => ({
      messages: [...s.messages, { role: "user", text }],
      sending: true,
      error: null,
    }));
    try {
      const res = await postChat({
        message: text,
        customer_id: customerId,
        session_id: sessionId,
      });
      // Drop the reply if the demo identity changed while it was in flight.
      if (get().customerId !== customerId) return;
      set({ sessionId: res.session_id, sending: false });
      get().addAgentTurn(res);
    } catch (e) {
      if (get().customerId !== customerId) return;
      set({ sending: false, error: e instanceof Error ? e.message : "request failed" });
    }
  },
}));
