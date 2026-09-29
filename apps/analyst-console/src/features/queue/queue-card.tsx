import { cn } from "@/lib/cn";
import type { QueueItem } from "@/lib/domain/types";
import { queueItemNeedsAttention } from "@/lib/domain/queue";

type QueueCardProps = {
  item: QueueItem;
  active: boolean;
  onSelect: (id: string) => void;
};

function formatQueueDate(value?: string | null): string {
  if (!value) {
    return "Undated";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  });
}

export function QueueCard({ item, active, onSelect }: QueueCardProps) {
  const priorityLabel =
    item.review_priority === "high"
      ? "High"
      : item.review_priority === "medium"
        ? "Medium"
        : "Low";
  const priorityTone =
    item.review_priority === "high"
      ? "border-[var(--console-danger)]/40 bg-[var(--console-danger)]/12 text-[var(--console-danger)]"
      : item.review_priority === "medium"
        ? "border-[var(--console-warn)]/40 bg-[var(--console-warn)]/12 text-[var(--console-warn)]"
        : "border-[var(--console-success)]/35 bg-[var(--console-success)]/10 text-[var(--console-success)]";

  const needsAttention = queueItemNeedsAttention(item);
  const dateLabel = formatQueueDate(item.event_date);

  return (
    <button
      aria-pressed={active}
      className={cn(
        "relative w-full rounded-lg border px-3 py-2.5 text-left transition-colors",
        "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--console-accent)]",
        active
          ? "border-[var(--console-accent)]/45 bg-[var(--console-panel-2)] shadow-[0_0_0_1px_var(--console-line-strong),0_14px_28px_rgba(5,10,22,0.18)]"
          : "border-[var(--console-line)] bg-[var(--console-panel)] hover:border-[var(--console-accent)]/30 hover:bg-[var(--console-panel-2)]/60",
      )}
      onClick={() => onSelect(item.event_id)}
      type="button"
    >
      <span
        aria-hidden="true"
        className={cn(
          "absolute inset-y-2 left-1 w-1 rounded-full transition-colors",
          active ? "bg-[var(--console-accent)]" : "bg-transparent",
        )}
      />

      <div className="flex items-center justify-between gap-2">
        <div
          className={cn(
            "min-w-0 text-[11px] uppercase tracking-wide",
            active ? "text-[var(--console-ink)]" : "text-[var(--console-muted)]",
          )}
        >
          {item.country || "Regional"}
        </div>
        <div className="shrink-0 text-[11px] text-[var(--console-muted)]">
          {dateLabel}
        </div>
      </div>

      <div
        className={cn(
          "mt-1.5 text-[14px] font-medium leading-5",
          active ? "text-white" : "text-[var(--console-ink)]",
        )}
      >
        {item.headline}
      </div>

      <div className="mt-2.5 flex flex-wrap items-center gap-1.5">
        <span
          className={cn(
            "inline-flex min-w-[76px] items-center justify-center rounded-full border px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide",
            priorityTone,
          )}
        >
          {priorityLabel}
        </span>
        {needsAttention ? (
          <span className="inline-flex min-w-[96px] items-center justify-center rounded-full border border-[var(--console-danger)]/35 bg-[var(--console-danger)]/10 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide text-[var(--console-danger)]">
            Review now
          </span>
        ) : null}
      </div>
    </button>
  );
}
