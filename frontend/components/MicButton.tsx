"use client";

import { useVoice } from "@/hooks/useVoice";

export function MicButton({
  customerId,
  sessionId,
}: {
  customerId: string;
  sessionId: string | null;
}) {
  const { active, error, start, stop } = useVoice(customerId, sessionId);

  return (
    <div className="relative">
      <button
        type="button"
        onClick={active ? stop : start}
        title={error ?? (active ? "Stop voice" : "Talk to the agent")}
        className={`flex h-10 w-10 items-center justify-center rounded-lg border transition-colors ${
          active
            ? "border-denied/50 bg-denied/15 text-denied"
            : "border-border bg-surface-2 text-muted hover:text-foreground"
        }`}
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden>
          <path d="M12 14a3 3 0 0 0 3-3V5a3 3 0 1 0-6 0v6a3 3 0 0 0 3 3z" />
          <path d="M19 11a7 7 0 0 1-14 0H3a9 9 0 0 0 8 8.94V23h2v-3.06A9 9 0 0 0 21 11h-2z" />
        </svg>
      </button>
      {error && (
        <div className="absolute right-0 top-12 z-10 w-56 rounded-md border border-border bg-surface-2 px-3 py-2 text-xs text-muted">
          {error}
        </div>
      )}
    </div>
  );
}
