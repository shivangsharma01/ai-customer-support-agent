"use client";

import type { TraceEvent } from "@/lib/api";

const NODES = [
  "extract_intent",
  "retrieve_customer",
  "retrieve_order",
  "retrieve_policy",
  "retrieve_similar_cases",
  "decision",
  "tools",
  "policy_validation",
  "generate_response",
];

export function GraphFlow({ events }: { events: TraceEvent[] }) {
  // Consider only the latest turn (since the last user_message).
  const lastTurnStart = events.findLastIndex((e) => e.type === "user_message");
  const turn = lastTurnStart >= 0 ? events.slice(lastTurnStart) : events;

  const completed = new Map<string, number>();
  for (const e of turn) {
    if (e.type === "node_completed" && e.node) {
      completed.set(e.node, (completed.get(e.node) ?? 0) + (e.latency_ms ?? 0));
    }
  }
  const running = new Set<string>();
  for (const e of turn) {
    if (e.type === "node_started" && e.node && !completed.has(e.node)) running.add(e.node);
  }

  return (
    <div className="space-y-0.5">
      {NODES.map((node, i) => {
        const done = completed.has(node);
        const active = running.has(node);
        return (
          <div key={node}>
            <div
              className={`flex items-center justify-between rounded-md border px-3 py-2 text-xs transition-colors ${
                active
                  ? "border-accent/60 bg-accent/10 text-foreground"
                  : done
                    ? "border-border bg-surface-2 text-foreground"
                    : "border-transparent text-muted"
              }`}
            >
              <span className="flex items-center gap-2 font-mono">
                <span
                  className={`h-1.5 w-1.5 rounded-full ${
                    active ? "animate-pulse bg-accent" : done ? "bg-approved" : "bg-border"
                  }`}
                />
                {node}
              </span>
              {done && (
                <span className="font-mono text-[10px] text-muted">
                  {Math.round(completed.get(node)!)}ms
                </span>
              )}
            </div>
            {i < NODES.length - 1 && <div className="ml-[17px] h-2 w-px bg-border" />}
          </div>
        );
      })}
    </div>
  );
}
