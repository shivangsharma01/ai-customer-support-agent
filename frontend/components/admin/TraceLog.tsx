"use client";

import { useEffect, useRef } from "react";
import type { TraceEvent } from "@/lib/api";

function line(e: TraceEvent): { text: string; cls: string } {
  const t = new Date(e.timestamp * 1000).toLocaleTimeString("en-IN", { hour12: false });
  switch (e.type) {
    case "user_message":
      return { text: `${t}  ▸ user (${e.customer_id}): ${e.message}`, cls: "text-foreground" };
    case "node_started":
      return { text: `${t}  ┌ ${e.node}`, cls: "text-muted" };
    case "node_completed":
      return { text: `${t}  └ ${e.node} · ${e.latency_ms}ms`, cls: "text-muted" };
    case "tool_called":
      return {
        text: `${t}  ⚙ tool ${e.tool}(${JSON.stringify(e.args ?? e.query ?? "")}) · ${e.latency_ms}ms`,
        cls: "text-accent",
      };
    case "retry":
      return { text: `${t}  ↻ retry ${e.step} #${e.attempt}: ${e.error}`, cls: "text-escalated" };
    case "escalation":
      return { text: `${t}  ⚑ escalation: ${e.reason}`, cls: "text-escalated" };
    case "decision_overridden":
      return {
        text: `${t}  ⛔ validator override: llm=${e.llm_decision} → validated=${e.validated_decision}`,
        cls: "text-denied",
      };
    case "agent_response":
      return {
        text: `${t}  ◂ agent (${e.total_latency_ms}ms): ${e.response}`,
        cls: "text-approved",
      };
    default:
      return { text: `${t}  · ${e.type}`, cls: "text-muted" };
  }
}

export function TraceLog({ events }: { events: TraceEvent[] }) {
  const bottom = useRef<HTMLDivElement>(null);
  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: "smooth" });
  }, [events.length]);

  return (
    <div className="h-full overflow-y-auto px-4 py-3 font-mono text-[11px] leading-5">
      {events.length === 0 && (
        <div className="mt-8 text-center text-muted">Waiting for agent activity…</div>
      )}
      {events.map((e, i) => {
        const { text, cls } = line(e);
        return (
          <div key={i} className={`whitespace-pre-wrap break-all ${cls}`}>
            {text}
          </div>
        );
      })}
      <div ref={bottom} />
    </div>
  );
}
