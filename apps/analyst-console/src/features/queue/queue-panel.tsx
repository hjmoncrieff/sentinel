import type { QueueItem } from "@/lib/domain/types";

import { QueueCard } from "./queue-card";

type QueuePanelProps = {
  rows: QueueItem[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  loadError?: string | null;
};

export function QueuePanel({
  rows,
  selectedId,
  onSelect,
  loadError = null,
}: QueuePanelProps) {
  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="border-b border-[var(--console-line)] px-4 py-3">
        <h2 className="text-sm font-semibold text-[var(--console-ink)]">
          Review queue
        </h2>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto p-4">
        {loadError ? (
          <p
            aria-live="polite"
            role="status"
            className="rounded-md border border-[var(--console-danger)]/40 bg-[var(--console-danger)]/10 px-3 py-3 text-sm text-[var(--console-danger)]"
          >
            {loadError}
          </p>
        ) : rows.length === 0 ? (
          <p className="rounded-md border border-dashed border-[var(--console-line)] px-3 py-3 text-sm text-[var(--console-muted)]">
            No queue items match the current filters.
          </p>
        ) : (
          <ul className="space-y-2" aria-label="Visible queue items">
            {rows.map((item) => (
              <li key={item.event_id}>
                <QueueCard
                  item={item}
                  active={item.event_id === selectedId}
                  onSelect={onSelect}
                />
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
