"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { fetchCustomers } from "@/lib/api";
import { useChatStore } from "@/store/chat";
import { ChatWindow } from "@/components/ChatWindow";

export default function CustomerPage() {
  const { customerId, setCustomer } = useChatStore();
  const [customers, setCustomers] = useState<
    { customer_id: string; customer_tier: string }[]
  >([]);

  useEffect(() => {
    fetchCustomers().then(setCustomers).catch(() => setCustomers([]));
  }, []);

  return (
    <main className="mx-auto flex h-dvh max-w-3xl flex-col">
      <header className="flex items-center justify-between border-b border-border px-6 py-4">
        <div>
          <h1 className="text-lg font-semibold tracking-tight">Refund Support</h1>
          <p className="text-xs text-muted">AI agent · policy-enforced decisions</p>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={customerId}
            onChange={(e) => setCustomer(e.target.value)}
            className="h-9 rounded-lg border border-border bg-surface-2 px-2 font-mono text-xs outline-none"
            title="Demo identity (stands in for login)"
          >
            {customers.length === 0 && <option value={customerId}>{customerId}</option>}
            {customers.map((c) => (
              <option key={c.customer_id} value={c.customer_id}>
                {c.customer_id} · {c.customer_tier}
              </option>
            ))}
          </select>
          <Link
            href="/admin"
            className="text-xs text-muted transition-colors hover:text-foreground"
          >
            Admin →
          </Link>
        </div>
      </header>
      <ChatWindow />
    </main>
  );
}
