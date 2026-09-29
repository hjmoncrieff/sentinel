import { useLayoutEffect, useState } from "react";

import type { QueueItem } from "@/lib/domain/types";

type ReviewDraft = {
  headline: string;
  summary: string;
  eventType: string;
  salience: string;
  confidence: string;
  reviewStatus: string;
  comment: string;
};

type ActionPanelProps = {
  item: QueueItem | null;
  authenticated: boolean;
  busy: boolean;
  saveError: string | null;
  onSave: (payload: { eventId: string; patch: Record<string, unknown>; comment: string }) => Promise<void> | void;
};

function formatActionDate(value?: string | null): string {
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

function createDraft(item: QueueItem | null): ReviewDraft {
  return {
    headline: item?.headline ?? "",
    summary: item?.summary ?? "",
    eventType: item?.event_type ?? "other",
    salience: item?.salience ?? "medium",
    confidence: item?.confidence ?? "medium",
    reviewStatus: item?.review_status ?? "auto",
    comment: "",
  };
}

function normalizeCompareValue(value: string | null | undefined): string {
  return (value ?? "").trim();
}

function getPendingChanges(
  item: QueueItem | null,
  draft: ReviewDraft,
): Array<{ label: string; before: string; after: string }> {
  if (!item) {
    return [];
  }

  const comparisons = [
    {
      label: "Headline",
      before: normalizeCompareValue(item.headline),
      after: normalizeCompareValue(draft.headline),
    },
    {
      label: "Summary",
      before: normalizeCompareValue(item.summary),
      after: normalizeCompareValue(draft.summary),
    },
    {
      label: "Event",
      before: normalizeCompareValue(item.event_type ?? "other"),
      after: normalizeCompareValue(draft.eventType),
    },
    {
      label: "Review status",
      before: normalizeCompareValue(item.review_status ?? "auto"),
      after: normalizeCompareValue(draft.reviewStatus),
    },
    {
      label: "Salience",
      before: normalizeCompareValue(item.salience ?? "medium"),
      after: normalizeCompareValue(draft.salience),
    },
    {
      label: "Confidence",
      before: normalizeCompareValue(item.confidence ?? "medium"),
      after: normalizeCompareValue(draft.confidence),
    },
  ];

  return comparisons.filter((comparison) => comparison.before !== comparison.after);
}

const REVIEW_STATUS_OPTIONS = [
  "auto",
  "needs_revision",
  "ra_reviewed",
  "analyst_reviewed",
  "flagged",
  "rejected",
];

const EVENT_TYPE_OPTIONS = [
  "coup",
  "purge",
  "conflict",
  "reform",
  "aid",
  "exercise",
  "oc",
  "protest",
  "peace",
  "other",
];

export function ActionPanel({
  item,
  authenticated,
  busy,
  saveError,
  onSave,
}: ActionPanelProps) {
  const [draft, setDraft] = useState<ReviewDraft>(() => createDraft(item));

  useLayoutEffect(() => {
    setDraft(createDraft(item));
  }, [item?.event_id]);

  const disabled = !item || !authenticated || busy;
  const dateLabel = formatActionDate(item?.event_date);
  const pendingChanges = getPendingChanges(item, draft);

  return (
    <section className="space-y-3.5 p-3.5" aria-label="Review actions">
      <div>
        <h2 className="text-sm font-semibold text-[var(--console-ink)]">
          Review edits
        </h2>
        <p className="mt-1 text-sm text-[var(--console-muted)]">
          Signed-in RAs, analysts, and admins can save event corrections and review notes here.
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
          Sign in to save edits. Preview mode keeps the queue visible, but mutations stay disabled.
        </p>
      ) : null}

      <form
        className="space-y-2.5"
        onSubmit={(event) => {
          event.preventDefault();
          if (!item) {
            return;
          }

          void onSave({
            eventId: item.event_id,
            patch: {
              headline: draft.headline,
              summary: draft.summary,
              event_type: draft.eventType,
              salience: draft.salience,
              confidence: draft.confidence,
              review_status: draft.reviewStatus,
            },
            comment: draft.comment,
          });
        }}
      >
        <label className="grid gap-1 text-sm text-[var(--console-muted)]">
          Headline
          <input
            className="rounded-lg border border-[var(--console-line)] bg-[var(--console-panel)] px-3 py-2 text-sm text-[var(--console-ink)] outline-none"
            disabled={disabled}
            onChange={(event) =>
              setDraft((current) => ({ ...current, headline: event.target.value }))
            }
            type="text"
            value={draft.headline}
          />
        </label>

        <label className="grid gap-1 text-sm text-[var(--console-muted)]">
          Summary
          <textarea
            className="min-h-24 rounded-lg border border-[var(--console-line)] bg-[var(--console-panel)] px-3 py-2 text-sm text-[var(--console-ink)] outline-none"
            disabled={disabled}
            onChange={(event) =>
              setDraft((current) => ({ ...current, summary: event.target.value }))
            }
            value={draft.summary}
          />
        </label>

        <div className="grid grid-cols-2 gap-2.5">
          <label className="grid gap-1 text-sm text-[var(--console-muted)]">
            Event
            <select
              className="rounded-lg border border-[var(--console-line)] bg-[var(--console-panel)] px-3 py-2 text-sm text-[var(--console-ink)] outline-none"
              disabled={disabled}
              onChange={(event) =>
                setDraft((current) => ({ ...current, eventType: event.target.value }))
              }
              value={draft.eventType}
            >
              {EVENT_TYPE_OPTIONS.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </label>

          <label className="grid gap-1 text-sm text-[var(--console-muted)]">
            Review status
            <select
              className="rounded-lg border border-[var(--console-line)] bg-[var(--console-panel)] px-3 py-2 text-sm text-[var(--console-ink)] outline-none"
              disabled={disabled}
              onChange={(event) =>
                setDraft((current) => ({ ...current, reviewStatus: event.target.value }))
              }
              value={draft.reviewStatus}
            >
              {REVIEW_STATUS_OPTIONS.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </label>
        </div>

        <div className="grid grid-cols-2 gap-2.5">
          <label className="grid gap-1 text-sm text-[var(--console-muted)]">
            Salience
            <select
              className="rounded-lg border border-[var(--console-line)] bg-[var(--console-panel)] px-3 py-2 text-sm text-[var(--console-ink)] outline-none"
              disabled={disabled}
              onChange={(event) =>
                setDraft((current) => ({ ...current, salience: event.target.value }))
              }
              value={draft.salience}
            >
              <option value="high">high</option>
              <option value="medium">medium</option>
              <option value="low">low</option>
            </select>
          </label>

          <label className="grid gap-1 text-sm text-[var(--console-muted)]">
            Confidence
            <select
              className="rounded-lg border border-[var(--console-line)] bg-[var(--console-panel)] px-3 py-2 text-sm text-[var(--console-ink)] outline-none"
              disabled={disabled}
              onChange={(event) =>
                setDraft((current) => ({ ...current, confidence: event.target.value }))
              }
              value={draft.confidence}
            >
              <option value="high">high</option>
              <option value="medium">medium</option>
              <option value="low">low</option>
            </select>
          </label>
        </div>

        <label className="grid gap-1 text-sm text-[var(--console-muted)]">
          Analyst note
          <textarea
            className="min-h-20 rounded-lg border border-[var(--console-line)] bg-[var(--console-panel)] px-3 py-2 text-sm text-[var(--console-ink)] outline-none"
            disabled={disabled}
            onChange={(event) =>
              setDraft((current) => ({ ...current, comment: event.target.value }))
            }
            placeholder="Describe what changed and why."
            value={draft.comment}
          />
        </label>

        <div className="rounded-lg border border-[var(--console-line)] bg-[var(--console-panel-2)] p-3">
          <div className="flex items-center justify-between gap-2">
            <div>
              <h3 className="text-sm font-semibold text-[var(--console-ink)]">
                Pending edit diff
              </h3>
              <p className="mt-1 text-sm text-[var(--console-muted)]">
                Compare your draft against the current event record before saving.
              </p>
            </div>
            <span className="rounded-full border border-[var(--console-line)] px-2.5 py-1 text-[10px] uppercase tracking-wide text-[var(--console-muted)]">
              {pendingChanges.length} change{pendingChanges.length === 1 ? "" : "s"}
            </span>
          </div>

          {pendingChanges.length > 0 ? (
            <div className="mt-3 grid gap-2">
              {pendingChanges.map((change) => (
                <div
                  key={change.label}
                  className="grid gap-2 rounded-lg border border-[var(--console-line)] bg-[var(--console-panel)] px-3 py-2.5 xl:grid-cols-[112px_minmax(0,1fr)_16px_minmax(0,1fr)] xl:items-start"
                >
                  <div className="text-[11px] uppercase tracking-wide text-[var(--console-muted)]">
                    {change.label}
                  </div>
                  <div className="min-w-0 rounded-md border border-[var(--console-line)]/80 bg-[var(--console-panel-2)] px-2.5 py-2 text-sm text-[var(--console-muted)]">
                    {change.before || "Empty"}
                  </div>
                  <div className="hidden items-center justify-center text-[var(--console-muted)] xl:flex">
                    →
                  </div>
                  <div className="min-w-0 rounded-md border border-[var(--console-accent)]/30 bg-[var(--console-accent)]/8 px-2.5 py-2 text-sm text-[var(--console-ink)]">
                    {change.after || "Empty"}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="mt-3 rounded-lg border border-dashed border-[var(--console-line)] px-3 py-3 text-sm text-[var(--console-muted)]">
              No unsaved field changes yet.
            </div>
          )}
        </div>

        {saveError ? (
          <p className="rounded-lg border border-[var(--console-danger)]/40 bg-[var(--console-danger)]/10 px-3 py-3 text-sm text-[var(--console-danger)]">
            {saveError}
          </p>
        ) : null}

        <button
          className="w-full rounded-lg border border-[var(--console-accent)] bg-[var(--console-panel-2)] px-3 py-2 text-left text-sm font-medium text-[var(--console-ink)] disabled:cursor-not-allowed disabled:border-[var(--console-line)] disabled:text-[var(--console-muted)]"
          disabled={disabled}
          type="submit"
        >
          {busy ? "Saving…" : "Save event edit"}
        </button>
      </form>
    </section>
  );
}
