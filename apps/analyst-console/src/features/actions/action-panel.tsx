import type { QueueItem } from "@/lib/domain/types";

type ActionPanelProps = {
  item: QueueItem | null;
};

function formatReason(reason: string): string {
  return reason.replaceAll("_", " ");
}

export function ActionPanel({ item }: ActionPanelProps) {
  const recommendedActions = item?.council_recommended_actions ?? [];
  const supervisionReasons = item?.supervision_reasons ?? [];
  const disabled = item === null;

  return (
    <section className="space-y-4 p-4">
      <div>
        <h2 className="text-sm font-semibold text-[var(--console-ink)]">
          Review actions
        </h2>
        <p className="mt-1 text-sm text-[var(--console-muted)]">
          Keep the current event decision surface visible while release and
          audit context remain adjacent.
        </p>
      </div>

      <div className="grid gap-2">
        <button
          className="rounded-md border border-[var(--console-accent)] bg-[var(--console-panel-2)] px-3 py-2 text-left text-sm font-medium text-[var(--console-ink)] disabled:cursor-not-allowed disabled:border-[var(--console-line)] disabled:text-[var(--console-muted)]"
          disabled={disabled}
          type="button"
        >
          Mark ready for release
        </button>
        <button
          className="rounded-md border border-[var(--console-line)] bg-[var(--console-panel)] px-3 py-2 text-left text-sm font-medium text-[var(--console-ink)] disabled:cursor-not-allowed disabled:text-[var(--console-muted)]"
          disabled={disabled}
          type="button"
        >
          Withhold and annotate
        </button>
      </div>

      <div className="rounded-md border border-[var(--console-line)] bg-[var(--console-panel-2)] p-3">
        <div className="text-[11px] uppercase tracking-wide text-[var(--console-muted)]">
          Queue posture
        </div>
        <p className="mt-2 text-sm text-[var(--console-ink)]">
          {item
            ? `${item.review_priority.toUpperCase()} priority review`
            : "No event selected"}
        </p>
        {item?.council_disagreement_summary ? (
          <p className="mt-2 text-sm text-[var(--console-muted)]">
            AI disagreement: {item.council_disagreement_summary}
          </p>
        ) : null}
      </div>

      {recommendedActions.length > 0 ? (
        <div className="space-y-2">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-[var(--console-muted)]">
            Recommended actions
          </h3>
          <ul className="space-y-2">
            {recommendedActions.slice(0, 3).map((action, index) => (
              <li
                key={action.code ?? `${item?.event_id ?? "action"}-${index}`}
                className="rounded-md border border-[var(--console-line)] bg-[var(--console-panel)] p-3"
              >
                <div className="text-[11px] uppercase tracking-wide text-[var(--console-muted)]">
                  {action.priority || "review"}
                </div>
                <p className="mt-1 text-sm font-medium text-[var(--console-ink)]">
                  {action.code ? formatReason(action.code) : "Analyst follow-up"}
                </p>
                {action.reason ? (
                  <p className="mt-2 text-sm text-[var(--console-muted)]">
                    {action.reason}
                  </p>
                ) : null}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {supervisionReasons.length > 0 ? (
        <div className="space-y-2">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-[var(--console-muted)]">
            Supervision drivers
          </h3>
          <ul className="flex flex-wrap gap-2 text-xs text-[var(--console-muted)]">
            {supervisionReasons.slice(0, 4).map((reason) => (
              <li
                key={reason}
                className="rounded-md border border-[var(--console-line)] px-2 py-1"
              >
                {formatReason(reason)}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  );
}
