"use client";

import type { TraceEvent } from "@/lib/api";

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-border bg-surface-2 px-3 py-2">
      <div className="text-[10px] uppercase tracking-wider text-muted">{label}</div>
      <div className="mt-0.5 font-mono text-sm">{value}</div>
    </div>
  );
}

export function Metrics({ events }: { events: TraceEvent[] }) {
  const turns = events.filter((e) => e.type === "agent_response");
  const toolCalls = events.filter((e) => e.type === "tool_called");
  const retries = events.filter((e) => e.type === "retry");
  const overrides = events.filter((e) => e.type === "decision_overridden");

  const lastTurn = turns.at(-1);
  const avgTurn =
    turns.length > 0
      ? turns.reduce((s, e) => s + (e.total_latency_ms ?? 0), 0) / turns.length
      : 0;

  const nodeTotals = new Map<string, { total: number; n: number }>();
  for (const e of events) {
    if (e.type === "node_completed" && e.node) {
      const cur = nodeTotals.get(e.node) ?? { total: 0, n: 0 };
      cur.total += e.latency_ms ?? 0;
      cur.n += 1;
      nodeTotals.set(e.node, cur);
    }
  }
  const slowest = [...nodeTotals.entries()]
    .map(([node, { total, n }]) => ({ node, avg: total / n }))
    .sort((a, b) => b.avg - a.avg)
    .slice(0, 4);

  const state = lastTurn?.state;

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-2">
        <Stat label="Turns" value={String(turns.length)} />
        <Stat
          label="Last turn"
          value={lastTurn ? `${(lastTurn.total_latency_ms! / 1000).toFixed(1)}s` : "—"}
        />
        <Stat label="Avg turn" value={turns.length ? `${(avgTurn / 1000).toFixed(1)}s` : "—"} />
        <Stat label="Tool calls" value={String(toolCalls.length)} />
        <Stat label="Retries" value={String(retries.length)} />
        <Stat label="Overrides" value={String(overrides.length)} />
      </div>

      {slowest.length > 0 && (
        <div>
          <div className="mb-1.5 text-[10px] uppercase tracking-wider text-muted">
            Slowest nodes (avg)
          </div>
          <div className="space-y-1">
            {slowest.map(({ node, avg }) => (
              <div key={node} className="flex justify-between font-mono text-[11px]">
                <span className="text-muted">{node}</span>
                <span>{Math.round(avg)}ms</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {state?.final_decision && (
        <div>
          <div className="mb-1.5 text-[10px] uppercase tracking-wider text-muted">
            Last decision
          </div>
          <div
            className={`rounded-lg border px-3 py-2 text-xs ${
              state.final_decision === "approved"
                ? "border-approved/30 text-approved"
                : state.final_decision === "denied"
                  ? "border-denied/30 text-denied"
                  : "border-escalated/30 text-escalated"
            }`}
          >
            <div className="font-semibold uppercase">{state.final_decision}</div>
            <div className="mt-1 text-foreground/80">{state.decision_reason}</div>
            {(state.policy_rules_triggered ?? []).map((r) => (
              <div key={r} className="mt-1 font-mono text-[10px] text-muted">
                {r}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
