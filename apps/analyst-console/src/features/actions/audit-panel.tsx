import type { QueueItem } from "@/lib/domain/types";

type AuditPanelProps = {
  item: QueueItem | null;
};

function formatAuditLabel(value?: string | null): string {
  if (!value) {
    return "Unknown";
  }

  return value.replaceAll("_", " ");
}

export function AuditPanel({ item }: AuditPanelProps) {
  const timeline = item?.provenance?.timeline ?? [];
  const qaFlags = item?.qa_flags ?? [];

  return (
    <section className="space-y-3 border-t border-[var(--console-line)] p-4">
      <div>
        <h2 className="text-sm font-semibold text-[var(--console-ink)]">
          Audit
        </h2>
        <p className="mt-1 text-sm text-[var(--console-muted)]">
          Review exceptions and provenance remain visible beside the active
          event.
        </p>
      </div>

      <div className="grid grid-cols-3 gap-2">
        <div className="rounded-md border border-[var(--console-line)] bg-[var(--console-panel-2)] px-3 py-2">
          <div className="text-[11px] uppercase tracking-wide text-[var(--console-muted)]">
            QA flags
          </div>
          <div className="mt-1 text-sm text-[var(--console-ink)]">
            {item?.qa_flag_count ?? qaFlags.length ?? 0}
          </div>
        </div>
        <div className="rounded-md border border-[var(--console-line)] bg-[var(--console-panel-2)] px-3 py-2">
          <div className="text-[11px] uppercase tracking-wide text-[var(--console-muted)]">
            Duplicates
          </div>
          <div className="mt-1 text-sm text-[var(--console-ink)]">
            {item?.duplicate_candidate_count ?? 0}
          </div>
        </div>
        <div className="rounded-md border border-[var(--console-line)] bg-[var(--console-panel-2)] px-3 py-2">
          <div className="text-[11px] uppercase tracking-wide text-[var(--console-muted)]">
            Merge state
          </div>
          <div className="mt-1 text-sm text-[var(--console-ink)]">
            {item?.merged_into_event_id ? "Merged away" : "Standalone"}
          </div>
        </div>
      </div>

      {qaFlags.length > 0 ? (
        <div className="space-y-2">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-[var(--console-muted)]">
            Active QA review
          </h3>
          <ul className="space-y-2">
            {qaFlags.slice(0, 2).map((flag, index) => (
              <li
                key={flag.flag_id ?? `${item?.event_id ?? "flag"}-${index}`}
                className="rounded-md border border-[var(--console-line)] bg-[var(--console-panel)] p-3"
              >
                <div className="text-[11px] uppercase tracking-wide text-[var(--console-muted)]">
                  {formatAuditLabel(flag.severity)}
                </div>
                <p className="mt-1 text-sm font-medium text-[var(--console-ink)]">
                  {flag.message || formatAuditLabel(flag.code)}
                </p>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {timeline.length > 0 ? (
        <div className="space-y-2">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-[var(--console-muted)]">
            Provenance timeline
          </h3>
          <ul className="space-y-2">
            {timeline.slice(0, 3).map((entry, index) => (
              <li
                key={`${entry.stage ?? "timeline"}-${entry.at ?? index}`}
                className="rounded-md border border-[var(--console-line)] bg-[var(--console-panel)] p-3 text-sm text-[var(--console-muted)]"
              >
                <p className="font-medium text-[var(--console-ink)]">
                  {entry.label || formatAuditLabel(entry.stage)}
                </p>
                <p className="mt-1">
                  {formatAuditLabel(entry.status)}
                  {entry.at ? ` · ${entry.at}` : ""}
                </p>
              </li>
            ))}
          </ul>
        </div>
      ) : (
        <p className="text-sm text-[var(--console-muted)]">
          {item
            ? `Audit trail for ${item.event_id}`
            : "No event selected for audit review."}
        </p>
      )}
    </section>
  );
}
