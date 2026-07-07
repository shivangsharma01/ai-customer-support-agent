"use client";

import { useEffect, useRef, useState } from "react";
import { useChatStore } from "@/store/chat";
import { DecisionCard } from "./DecisionCard";
import { MicButton } from "./MicButton";

export function ChatWindow() {
  const { messages, sending, error, send, customerId, sessionId } = useChatStore();
  const [input, setInput] = useState("");
  const bottom = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, sending]);

  const submit = () => {
    const text = input.trim();
    if (!text || sending) return;
    setInput("");
    void send(text);
  };

  return (
    <div className="flex h-full flex-col">
      <div className="flex-1 space-y-4 overflow-y-auto px-6 py-6">
        {messages.length === 0 && (
          <div className="mt-24 text-center text-sm text-muted">
            Ask about a refund — e.g.{" "}
            <button
              className="text-accent hover:underline"
              onClick={() => setInput("I'd like a refund for order ORD-1001, it doesn't fit.")}
            >
              “I&apos;d like a refund for order ORD-1001, it doesn&apos;t fit.”
            </button>
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
            <div
              className={`max-w-[75%] rounded-xl px-4 py-2.5 text-sm leading-relaxed ${
                m.role === "user"
                  ? "bg-accent/20 text-foreground"
                  : "border border-border bg-surface-2"
              }`}
            >
              {m.text}
              {m.decision && (
                <DecisionCard
                  decision={m.decision.decision}
                  reason={m.decision.reason}
                  rules={m.decision.rules}
                />
              )}
            </div>
          </div>
        ))}
        {sending && (
          <div className="flex items-center gap-2 text-xs text-muted">
            <span className="h-2 w-2 animate-pulse rounded-full bg-accent" />
            Agent is checking policy…
          </div>
        )}
        {error && <div className="text-xs text-denied">{error}</div>}
        <div ref={bottom} />
      </div>

      <div className="flex items-center gap-2 border-t border-border px-6 py-4">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && submit()}
          placeholder="Describe your refund request…"
          className="h-10 flex-1 rounded-lg border border-border bg-surface-2 px-3 text-sm outline-none placeholder:text-muted focus:border-accent/60"
        />
        <MicButton customerId={customerId} sessionId={sessionId} />
        <button
          onClick={submit}
          disabled={sending || !input.trim()}
          className="h-10 rounded-lg bg-accent px-4 text-sm font-medium text-white transition-opacity disabled:opacity-40"
        >
          Send
        </button>
      </div>
    </div>
  );
}
