"use client";

import Link from "next/link";
import { useAdminSocket } from "@/hooks/useAdminSocket";
import { useAdminStore } from "@/store/admin";
import { GraphFlow } from "@/components/admin/GraphFlow";
import { TraceLog } from "@/components/admin/TraceLog";
import { Metrics } from "@/components/admin/Metrics";

export default function AdminPage() {
  useAdminSocket();
  const { events, connected, selectedSession, selectSession } = useAdminStore();

  const sessions = [...new Set(events.map((e) => e.session_id))];
  const sessionEvents = events.filter((e) => e.session_id === selectedSession);

  return (
    <main className="flex h-dvh flex-col">
      <header className="flex items-center justify-between border-b border-border px-6 py-4">
        <div className="flex items-center gap-3">
          <h1 className="text-lg font-semibold tracking-tight">Agent Console</h1>
          <span
            className={`flex items-center gap-1.5 rounded-full border border-border px-2 py-0.5 text-[10px] ${
              connected ? "text-approved" : "text-denied"
            }`}
          >
            <span
              className={`h-1.5 w-1.5 rounded-full ${connected ? "bg-approved" : "bg-denied"}`}
            />
            {connected ? "live" : "disconnected"}
          </span>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={selectedSession ?? ""}
            onChange={(e) => selectSession(e.target.value || null)}
            className="h-9 max-w-56 rounded-lg border border-border bg-surface-2 px-2 font-mono text-xs outline-none"
          >
            <option value="">select session…</option>
            {sessions.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
          <Link href="/" className="text-xs text-muted transition-colors hover:text-foreground">
            ← Customer view
          </Link>
        </div>
      </header>

      <div className="grid min-h-0 flex-1 grid-cols-[240px_1fr_280px]">
        <aside className="overflow-y-auto border-r border-border p-4">
          <div className="mb-3 text-[10px] uppercase tracking-wider text-muted">
            Graph execution
          </div>
          <GraphFlow events={sessionEvents} />
        </aside>

        <section className="min-h-0 border-r border-border">
          <TraceLog events={sessionEvents} />
        </section>

        <aside className="overflow-y-auto p-4">
          <div className="mb-3 text-[10px] uppercase tracking-wider text-muted">Metrics</div>
          <Metrics events={sessionEvents} />
        </aside>
      </div>
    </main>
  );
}
