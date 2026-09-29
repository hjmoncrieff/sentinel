import type {
  CouncilAnalysisEvent,
  CountryMonitorRecord,
  EventEditRecord,
  QueueItem,
} from "@/lib/domain/types";

type DataPanelProps = {
  item: QueueItem | null;
  analysis: CouncilAnalysisEvent | null;
  countryBrief: CountryMonitorRecord | null;
  editHistory: EventEditRecord[];
};

function renderJson(value: unknown): string {
  return JSON.stringify(value, null, 2);
}

export function DataPanel({
  item,
  analysis,
  countryBrief,
  editHistory,
}: DataPanelProps) {
  if (!item) {
    return (
      <div className="space-y-3 p-4">
        <h2 className="text-sm font-semibold text-[var(--console-ink)]">Data</h2>
        <p className="text-sm text-[var(--console-muted)]">
          No queue item selected.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4 p-4">
      <div>
        <div className="text-xs uppercase tracking-wide text-[var(--console-muted)]">
          {item.event_id}
        </div>
        <h2 className="mt-2 text-xl font-semibold text-[var(--console-ink)]">
          Structured data
        </h2>
        <p className="mt-1 text-sm text-[var(--console-muted)]">
          Event fields, AI metadata, country monitor context, and recent audit writes.
        </p>
      </div>

      <section className="rounded-md border border-[var(--console-line)] bg-[var(--console-panel)] p-4">
        <h3 className="text-sm font-semibold text-[var(--console-ink)]">
          Event record
        </h3>
        <pre className="mt-3 overflow-x-auto text-xs leading-5 text-[var(--console-muted)]">
          {renderJson(item)}
        </pre>
      </section>

      {analysis ? (
        <section className="rounded-md border border-[var(--console-line)] bg-[var(--console-panel)] p-4">
          <h3 className="text-sm font-semibold text-[var(--console-ink)]">
            Council analysis payload
          </h3>
          <pre className="mt-3 overflow-x-auto text-xs leading-5 text-[var(--console-muted)]">
            {renderJson(analysis)}
          </pre>
        </section>
      ) : null}

      {countryBrief ? (
        <section className="rounded-md border border-[var(--console-line)] bg-[var(--console-panel)] p-4">
          <h3 className="text-sm font-semibold text-[var(--console-ink)]">
            Country monitor payload
          </h3>
          <pre className="mt-3 overflow-x-auto text-xs leading-5 text-[var(--console-muted)]">
            {renderJson(countryBrief)}
          </pre>
        </section>
      ) : null}

      <section className="rounded-md border border-[var(--console-line)] bg-[var(--console-panel)] p-4">
        <h3 className="text-sm font-semibold text-[var(--console-ink)]">
          Recent event edits
        </h3>
        {editHistory.length ? (
          <pre className="mt-3 overflow-x-auto text-xs leading-5 text-[var(--console-muted)]">
            {renderJson(editHistory)}
          </pre>
        ) : (
          <p className="mt-3 text-sm text-[var(--console-muted)]">
            No saved event edits are recorded yet for this queue item.
          </p>
        )}
      </section>
    </div>
  );
}
