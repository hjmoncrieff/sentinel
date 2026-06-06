import type { QueueItem } from "@/lib/domain/types";

type ReleasePanelProps = {
  item: QueueItem | null;
};

function formatReleaseReason(reason?: string | null): string {
  if (!reason) {
    return "Eligible under current policy.";
  }

  return `${reason.replaceAll("_", " ")}.`;
}

export function ReleasePanel({ item }: ReleasePanelProps) {
  return (
    <section className="space-y-3 border-t border-[var(--console-line)] p-4">
      <div>
        <h2 className="text-sm font-semibold text-[var(--console-ink)]">
          Release
        </h2>
        <p className="mt-1 text-sm text-[var(--console-muted)]">
          Publication posture for the selected queue item.
        </p>
      </div>

      <div className="rounded-md border border-[var(--console-line)] bg-[var(--console-panel-2)] p-3">
        <dl className="grid grid-cols-2 gap-3 text-sm">
          <div>
            <dt className="text-[11px] uppercase tracking-wide text-[var(--console-muted)]">
              Status
            </dt>
            <dd className="mt-1 text-[var(--console-ink)]">
              {item?.publication_label || item?.publication_status || "draft"}
            </dd>
          </div>
          <div>
            <dt className="text-[11px] uppercase tracking-wide text-[var(--console-muted)]">
              Human review
            </dt>
            <dd className="mt-1 text-[var(--console-ink)]">
              {item ? (item.reviewed_by_human ? "Completed" : "Pending") : "—"}
            </dd>
          </div>
          <div>
            <dt className="text-[11px] uppercase tracking-wide text-[var(--console-muted)]">
              Ready
            </dt>
            <dd className="mt-1 text-[var(--console-ink)]">
              {item ? (item.publication_ready ? "Yes" : "Hold") : "—"}
            </dd>
          </div>
          <div>
            <dt className="text-[11px] uppercase tracking-wide text-[var(--console-muted)]">
              Review status
            </dt>
            <dd className="mt-1 text-[var(--console-ink)]">
              {item?.review_status || "auto"}
            </dd>
          </div>
        </dl>
      </div>

      <p className="text-sm text-[var(--console-muted)]">
        {item
          ? formatReleaseReason(item.publication_reason)
          : "Select an event to inspect release readiness."}
      </p>
    </section>
  );
}
