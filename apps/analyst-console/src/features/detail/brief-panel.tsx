import { useEffect, useMemo, useState } from "react";

import type { QueueItem } from "@/lib/domain/types";

type BriefPanelProps = {
  item: QueueItem | null;
  loadError?: string | null;
};

function getPreviewText(item: QueueItem): string {
  const summary = item.summary?.trim();

  if (summary) {
    return summary;
  }

  const reportDescription = item.provenance?.linked_reports?.find(
    (report) => report.description?.trim(),
  )?.description;

  if (reportDescription?.trim()) {
    return reportDescription.trim();
  }

  const parts = [item.source_primary, item.publication_reason]
    .map((value) => value?.replaceAll("_", " ").trim())
    .filter(Boolean);

  return parts.join(" · ") || "No event brief is recorded for this queue item yet.";
}

export function BriefPanel({ item, loadError = null }: BriefPanelProps) {
  const [showEvidence, setShowEvidence] = useState(false);

  useEffect(() => {
    setShowEvidence(false);
  }, [item?.event_id]);

  const linkedReports = item?.provenance?.linked_reports ?? [];
  const previewText = useMemo(() => (item ? getPreviewText(item) : ""), [item]);

  if (loadError) {
    return (
      <div className="space-y-3 p-4">
        <h2 className="text-sm font-semibold text-[var(--console-ink)]">
          Event brief
        </h2>
        <p className="text-sm text-[var(--console-muted)]">
          Brief unavailable while the review queue failed to load.
        </p>
      </div>
    );
  }

  if (!item) {
    return (
      <div className="space-y-3 p-4">
        <h2 className="text-sm font-semibold text-[var(--console-ink)]">
          Event brief
        </h2>
        <p className="text-sm text-[var(--console-muted)]">
          No visible queue item selected.
        </p>
      </div>
    );
  }

  const evidenceId = `brief-evidence-${item.event_id}`;

  return (
    <div className="flex h-full min-h-0 flex-col p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-xs uppercase tracking-wide text-[var(--console-muted)]">
            {item.country || "Regional"}
          </div>
          <h2 className="mt-2 text-xl font-semibold text-[var(--console-ink)]">
            {item.headline}
          </h2>
        </div>
        <div className="shrink-0 rounded-md border border-[var(--console-line)] bg-[var(--console-panel)] px-3 py-2 text-right">
          <div className="text-[11px] uppercase tracking-wide text-[var(--console-muted)]">
            Review priority
          </div>
          <div className="mt-1 text-sm font-medium text-[var(--console-ink)]">
            {item.review_priority}
          </div>
        </div>
      </div>

      <dl className="mt-4 grid grid-cols-2 gap-3 text-sm">
        <div className="rounded-md border border-[var(--console-line)] bg-[var(--console-panel)] px-3 py-2">
          <dt className="text-[11px] uppercase tracking-wide text-[var(--console-muted)]">
            Event type
          </dt>
          <dd className="mt-1 text-[var(--console-ink)]">
            {item.event_type || "Uncoded"}
          </dd>
        </div>
        <div className="rounded-md border border-[var(--console-line)] bg-[var(--console-panel)] px-3 py-2">
          <dt className="text-[11px] uppercase tracking-wide text-[var(--console-muted)]">
            Event date
          </dt>
          <dd className="mt-1 text-[var(--console-ink)]">
            {item.event_date || "Undated"}
          </dd>
        </div>
      </dl>

      <p className="mt-4 text-sm leading-6 text-[var(--console-ink)]">
        {previewText}
      </p>

      <div className="mt-4 flex flex-wrap gap-2">
        <button
          aria-controls={evidenceId}
          aria-expanded={showEvidence}
          className="rounded-md border border-[var(--console-line)] bg-[var(--console-panel)] px-3 py-2 text-sm text-[var(--console-ink)] transition-colors hover:border-[var(--console-accent)]/40 hover:bg-[var(--console-panel)]/80 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--console-accent)]"
          onClick={() => setShowEvidence((value) => !value)}
          type="button"
        >
          Evidence
        </button>
      </div>

      {showEvidence ? (
        <div
          id={evidenceId}
          className="mt-4 rounded-md border border-[var(--console-line)] bg-[var(--console-panel)] p-4"
        >
          <div className="flex items-start justify-between gap-3">
            <div>
              <h3 className="text-sm font-semibold text-[var(--console-ink)]">
                Source dossier
              </h3>
              <p className="mt-1 text-sm text-[var(--console-muted)]">
                Linked reporting stays attached to the current queue item so
                deeper evidence does not displace the selected event.
              </p>
            </div>
            <div className="rounded-md border border-[var(--console-line)] px-2 py-1 text-[11px] uppercase tracking-wide text-[var(--console-muted)]">
              {linkedReports.length || (item.source_primary ? 1 : 0)} source
              {(linkedReports.length || (item.source_primary ? 1 : 0)) === 1
                ? ""
                : "s"}
            </div>
          </div>

          {linkedReports.length > 0 ? (
            <ul className="mt-4 space-y-3">
              {linkedReports.slice(0, 3).map((report, index) => (
                <li
                  key={report.article_id ?? `${item.event_id}-${index}`}
                  className="rounded-md border border-[var(--console-line)] bg-[var(--console-panel-2)] p-3"
                >
                  <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-[11px] uppercase tracking-wide text-[var(--console-muted)]">
                    <span>{report.source_name || report.link_domain || "Report"}</span>
                    {report.report_role ? <span>{report.report_role}</span> : null}
                  </div>
                  <p className="mt-2 text-sm font-medium text-[var(--console-ink)]">
                    {report.headline || item.headline}
                  </p>
                  {report.description ? (
                    <p className="mt-2 text-sm leading-6 text-[var(--console-muted)]">
                      {report.description}
                    </p>
                  ) : null}
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-4 rounded-md border border-dashed border-[var(--console-line)] px-3 py-3 text-sm text-[var(--console-muted)]">
              {item.source_primary
                ? `Primary source: ${item.source_primary}`
                : "No linked reports are recorded for this event yet."}
            </p>
          )}
        </div>
      ) : null}
    </div>
  );
}
