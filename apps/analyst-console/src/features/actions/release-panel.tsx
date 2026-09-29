import { useEffect, useState } from "react";

import type { QueueItem } from "@/lib/domain/types";

type ReleasePanelProps = {
  item: QueueItem | null;
  authenticated: boolean;
  canPublish: boolean;
  busy: boolean;
  saveError: string | null;
  onReady: (payload: { eventId: string; comment: string }) => Promise<void> | void;
  onWithhold: (payload: { eventId: string; comment: string }) => Promise<void> | void;
};

function formatReleaseDate(value?: string | null): string {
  if (!value) {
    return "Undated";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function formatReleaseReason(reason?: string | null): string {
  if (!reason) {
    return "Eligible under current policy.";
  }

  return `${reason.replaceAll("_", " ")}.`;
}

function getReleaseChecklist(item: QueueItem | null) {
  const linkedSources = item?.provenance?.linked_reports?.length ?? 0;

  return [
    {
      label: "Human review saved",
      complete: item?.reviewed_by_human === true,
      detail: "An analyst or RA saved edits or notes on the event.",
    },
    {
      label: "QA clear",
      complete: (item?.qa_flag_count ?? 0) === 0,
      detail:
        (item?.qa_flag_count ?? 0) > 0
          ? `${item?.qa_flag_count ?? 0} QA flag(s) still open.`
          : "No open QA flags.",
    },
    {
      label: "Registry clear",
      complete:
        (item?.registry_issue_count ?? 0) === 0 &&
        (item?.duplicate_candidate_count ?? 0) === 0,
      detail:
        (item?.registry_issue_count ?? 0) > 0 ||
        (item?.duplicate_candidate_count ?? 0) > 0
          ? "Resolve registry or duplicate issues before release."
          : "No open registry or duplicate blockers.",
    },
    {
      label: "Source package present",
      complete: linkedSources > 0 || !!item?.source_primary,
      detail:
        linkedSources > 0
          ? `${linkedSources} linked source report(s) attached.`
          : item?.source_primary
            ? `Primary source: ${item.source_primary}.`
            : "Add a source reference before release.",
    },
  ];
}

export function ReleasePanel({
  item,
  authenticated,
  canPublish,
  busy,
  saveError,
  onReady,
  onWithhold,
}: ReleasePanelProps) {
  const [comment, setComment] = useState("");

  useEffect(() => {
    setComment("");
  }, [item?.event_id]);

  const disabled = !item || !authenticated || !canPublish || busy;
  const checklist = getReleaseChecklist(item);
  const checklistComplete = checklist.every((entry) => entry.complete);
  const readyDisabled = disabled || !checklistComplete;
  const dateLabel = formatReleaseDate(item?.event_date);

  return (
    <section className="space-y-3.5 p-3.5" aria-label="Release actions">
      <div>
        <h2 className="text-sm font-semibold text-[var(--console-ink)]">
          Release control
        </h2>
        <p className="mt-1 text-sm text-[var(--console-muted)]">
          Analysts and admins can mark an event ready for release or hold it back with an audit note.
        </p>
      </div>

      <div className="rounded-lg border border-[var(--console-line)] bg-[var(--console-panel-2)] px-3 py-2.5">
        <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-[11px] uppercase tracking-wide text-[var(--console-muted)]">
          <span>{item?.country || "Regional"}</span>
          <span className="text-[var(--console-line-strong)]">/</span>
          <span>{dateLabel}</span>
        </div>
        <div className="mt-1.5 text-sm font-medium text-[var(--console-ink)]">
          {item?.headline || "No event selected"}
        </div>
      </div>

      {!authenticated ? (
        <p className="rounded-lg border border-[var(--console-line)] bg-[var(--console-panel-2)] px-3 py-3 text-sm text-[var(--console-muted)]">
          Sign in to record release decisions.
        </p>
      ) : null}
      {authenticated && !canPublish ? (
        <p className="rounded-lg border border-[var(--console-line)] bg-[var(--console-panel-2)] px-3 py-3 text-sm text-[var(--console-muted)]">
          This role can edit records, but release decisions are limited to analysts and admins.
        </p>
      ) : null}

      <div className="rounded-lg border border-[var(--console-line)] bg-[var(--console-panel-2)] p-3">
        <dl className="grid grid-cols-2 gap-2.5 text-sm">
          <div className="rounded-lg border border-[var(--console-line)] bg-[var(--console-panel)] px-3 py-2">
            <dt className="text-[11px] uppercase tracking-wide text-[var(--console-muted)]">
              Status
            </dt>
            <dd className="mt-1 text-[var(--console-ink)]">
              {item?.publication_label || item?.publication_status || "draft"}
            </dd>
          </div>
          <div className="rounded-lg border border-[var(--console-line)] bg-[var(--console-panel)] px-3 py-2">
            <dt className="text-[11px] uppercase tracking-wide text-[var(--console-muted)]">
              Human review
            </dt>
            <dd className="mt-1 text-[var(--console-ink)]">
              {item ? (item.reviewed_by_human ? "Completed" : "Pending") : "—"}
            </dd>
          </div>
          <div className="rounded-lg border border-[var(--console-line)] bg-[var(--console-panel)] px-3 py-2">
            <dt className="text-[11px] uppercase tracking-wide text-[var(--console-muted)]">
              Ready
            </dt>
            <dd className="mt-1 text-[var(--console-ink)]">
              {item ? (item.publication_ready ? "Yes" : "Hold") : "—"}
            </dd>
          </div>
          <div className="rounded-lg border border-[var(--console-line)] bg-[var(--console-panel)] px-3 py-2">
            <dt className="text-[11px] uppercase tracking-wide text-[var(--console-muted)]">
              Review status
            </dt>
            <dd className="mt-1 text-[var(--console-ink)]">
              {item?.review_status || "auto"}
            </dd>
          </div>
        </dl>
      </div>

      <div className="rounded-lg border border-[var(--console-line)] bg-[var(--console-panel-2)] p-3">
        <div className="mb-2 text-[11px] uppercase tracking-wide text-[var(--console-muted)]">
          Publish checklist
        </div>
        <div className="grid gap-2">
          {checklist.map((entry) => (
            <div
              key={entry.label}
              className="flex items-start justify-between gap-3 rounded-lg border border-[var(--console-line)] bg-[var(--console-panel)] px-3 py-2.5"
            >
              <div className="min-w-0">
                <div className="text-sm font-medium text-[var(--console-ink)]">
                  {entry.label}
                </div>
                <div className="mt-1 text-xs text-[var(--console-muted)]">
                  {entry.detail}
                </div>
              </div>
              <span
                className={
                  entry.complete
                    ? "rounded-full border border-[var(--console-success)]/35 bg-[var(--console-success)]/10 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide text-[var(--console-success)]"
                    : "rounded-full border border-[var(--console-warn)]/35 bg-[var(--console-warn)]/10 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide text-[var(--console-warn)]"
                }
              >
                {entry.complete ? "Done" : "Open"}
              </span>
            </div>
          ))}
        </div>
      </div>

      <p className="text-sm text-[var(--console-muted)]">
        {item
          ? formatReleaseReason(item.publication_reason)
          : "Select an event to inspect release readiness."}
      </p>

      {authenticated && canPublish && item && !checklistComplete ? (
        <p className="rounded-lg border border-[var(--console-warn)]/35 bg-[var(--console-warn)]/10 px-3 py-3 text-sm text-[var(--console-warn)]">
          Finish the checklist in Edit, Audit, or Registry before marking this event ready.
        </p>
      ) : null}

      <label className="grid gap-1 text-sm text-[var(--console-muted)]">
        Release note
        <textarea
          className="min-h-20 rounded-lg border border-[var(--console-line)] bg-[var(--console-panel)] px-3 py-2 text-sm text-[var(--console-ink)] outline-none"
          disabled={disabled}
          onChange={(event) => setComment(event.target.value)}
          placeholder="Record why this event is ready for release or why it should be withheld."
          value={comment}
        />
      </label>

      {saveError ? (
        <p className="rounded-lg border border-[var(--console-danger)]/40 bg-[var(--console-danger)]/10 px-3 py-3 text-sm text-[var(--console-danger)]">
          {saveError}
        </p>
      ) : null}

      <div className="grid gap-2">
        <button
          className="rounded-lg border border-[var(--console-accent)] bg-[var(--console-panel-2)] px-3 py-2 text-left text-sm font-medium text-[var(--console-ink)] disabled:cursor-not-allowed disabled:border-[var(--console-line)] disabled:text-[var(--console-muted)]"
          disabled={readyDisabled}
          onClick={() => {
            if (!item) {
              return;
            }
            void onReady({ eventId: item.event_id, comment });
          }}
          type="button"
        >
          {busy ? "Working…" : "Mark ready for release"}
        </button>
        <button
          className="rounded-lg border border-[var(--console-line)] bg-[var(--console-panel)] px-3 py-2 text-left text-sm font-medium text-[var(--console-ink)] disabled:cursor-not-allowed disabled:text-[var(--console-muted)]"
          disabled={disabled}
          onClick={() => {
            if (!item) {
              return;
            }
            void onWithhold({ eventId: item.event_id, comment });
          }}
          type="button"
        >
          {busy ? "Working…" : "Withhold and annotate"}
        </button>
      </div>
    </section>
  );
}
