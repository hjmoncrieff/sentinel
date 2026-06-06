import { cn } from "@/lib/cn";
import type { QueueItem } from "@/lib/domain/types";

type QueueCardProps = {
  item: QueueItem;
  active: boolean;
  onSelect: (id: string) => void;
};

export function QueueCard({ item, active, onSelect }: QueueCardProps) {
  return (
    <button
      aria-pressed={active}
      className={cn(
        "w-full rounded-md border px-3 py-3 text-left transition-colors",
        "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--console-accent)]",
        active
          ? "border-[var(--console-warn)] bg-[var(--console-panel-2)]"
          : "border-[var(--console-line)] bg-[var(--console-panel)] hover:border-[var(--console-accent)]/40 hover:bg-[var(--console-panel-2)]/60",
      )}
      onClick={() => onSelect(item.event_id)}
      type="button"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 text-xs uppercase tracking-wide text-[var(--console-muted)]">
          {item.country || "Regional"}
        </div>
        <div className="shrink-0 text-[11px] uppercase tracking-wide text-[var(--console-muted)]">
          {item.review_priority} priority
        </div>
      </div>

      <div className="mt-2 text-sm font-medium text-[var(--console-ink)]">
        {item.headline}
      </div>

      <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-[var(--console-muted)]">
        <span>{item.event_id}</span>
        {item.event_type ? <span>{item.event_type}</span> : null}
        {item.event_date ? <span>{item.event_date}</span> : null}
      </div>
    </button>
  );
}
