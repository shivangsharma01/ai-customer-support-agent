const STYLES: Record<string, { label: string; cls: string }> = {
  approved: { label: "Refund approved", cls: "text-approved border-approved/30 bg-approved/10" },
  denied: { label: "Refund denied", cls: "text-denied border-denied/30 bg-denied/10" },
  escalated: { label: "Escalated to human review", cls: "text-escalated border-escalated/30 bg-escalated/10" },
};

export function DecisionCard({
  decision,
  reason,
  rules,
}: {
  decision: string;
  reason: string;
  rules: string[];
}) {
  const style = STYLES[decision] ?? STYLES.escalated;
  return (
    <div className={`mt-2 rounded-lg border px-4 py-3 ${style.cls}`}>
      <div className="text-sm font-semibold tracking-wide uppercase">{style.label}</div>
      <p className="mt-1 text-sm text-foreground/90">{reason}</p>
      {rules.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1.5">
          {rules.map((r) => (
            <span
              key={r}
              className="rounded border border-border bg-surface-2 px-1.5 py-0.5 font-mono text-[11px] text-muted"
            >
              {r}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
