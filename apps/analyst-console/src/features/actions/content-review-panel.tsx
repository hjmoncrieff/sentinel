import { useCallback, useEffect, useState } from "react";

import {
  latestDecision,
  loadContentReviewQueue,
  submitContentReview,
  type ContentReviewQueue,
} from "@/lib/api/content-reviews";
import type { ContentReviewItem, SessionProfile } from "@/lib/domain/types";

type ContentReviewPanelProps = {
  profile: SessionProfile | null;
  canDecide: boolean;
};

const EMPTY_QUEUE: ContentReviewQueue = {
  generatedAt: null,
  items: [],
  decisions: [],
};

function formatDay(value?: string | null): string {
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

function ReviewItemCard({
  item,
  busy,
  canDecide,
  decided,
  onDecide,
}: {
  item: ContentReviewItem;
  busy: boolean;
  canDecide: boolean;
  decided: string | null;
  onDecide: (decision: "approve" | "dismiss", comment: string) => void;
}) {
  const [comment, setComment] = useState("");
  const signoff = item.mode === "signoff";
  const disabled = busy || !canDecide || decided !== null;

  return (
    <article className="rounded-lg border border-[var(--console-line)] bg-[var(--console-panel-2)] p-3">
      <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-[11px] uppercase tracking-wide text-[var(--console-muted)]">
        <span>{signoff ? "Sign-off" : "Proposed change"}</span>
        <span className="text-[var(--console-line-strong)]">/</span>
        <span>{formatDay(item.date)}</span>
      </div>
      <h3 className="mt-1.5 text-sm font-semibold text-[var(--console-ink)]">
        {item.subject}
      </h3>
      <p className="mt-1 text-xs text-[var(--console-muted)]">{item.trigger}</p>

      {item.summary.length > 0 ? (
        <ul className="mt-2 list-disc space-y-1 pl-4 text-sm text-[var(--console-ink)]">
          {item.summary.map((line) => (
            <li key={line}>{line}</li>
          ))}
        </ul>
      ) : null}

      <div className="mt-3 grid gap-1.5">
        {item.rows.map((row) => (
          <div
            key={row.field}
            className="rounded-lg border border-[var(--console-line)] bg-[var(--console-panel)] px-3 py-2"
          >
            <div className="text-[11px] uppercase tracking-wide text-[var(--console-muted)]">
              {row.field}
            </div>
            <div className="mt-1 text-sm text-[var(--console-ink)]">
              {row.changed ? (
                <>
                  <span className="text-[var(--console-muted)] line-through">
                    {row.current || "Not recorded"}
                  </span>
                  <span className="px-1.5 text-[var(--console-muted)]">→</span>
                  <span className="font-medium">
                    {row.proposed || "Not confirmed"}
                  </span>
                </>
              ) : (
                <span>{row.proposed || row.current || "Not confirmed"}</span>
              )}
              {row.source_url ? (
                <a
                  className="ml-2 text-xs text-[var(--console-accent)] underline"
                  href={row.source_url}
                  rel="noopener noreferrer"
                  target="_blank"
                >
                  source
                </a>
              ) : null}
            </div>
          </div>
        ))}
      </div>

      {item.note ? (
        <p className="mt-3 text-xs text-[var(--console-muted)]">
          <span className="font-medium text-[var(--console-ink)]">Summary. </span>
          {item.note}
        </p>
      ) : null}

      {decided ? (
        <p className="mt-3 rounded-lg border border-[var(--console-success)]/35 bg-[var(--console-success)]/10 px-3 py-2 text-sm text-[var(--console-success)]">
          {decided}
        </p>
      ) : (
        <>
          <label className="mt-3 grid gap-1 text-sm text-[var(--console-muted)]">
            Note
            <textarea
              className="min-h-16 rounded-lg border border-[var(--console-line)] bg-[var(--console-panel)] px-3 py-2 text-sm text-[var(--console-ink)] outline-none"
              disabled={disabled}
              onChange={(event) => setComment(event.target.value)}
              placeholder="Optional: what you checked, or why this is wrong."
              value={comment}
            />
          </label>
          <div className="mt-2 grid gap-2">
            <button
              className="rounded-lg border border-[var(--console-accent)] bg-[var(--console-panel-2)] px-3 py-2 text-left text-sm font-medium text-[var(--console-ink)] disabled:cursor-not-allowed disabled:border-[var(--console-line)] disabled:text-[var(--console-muted)]"
              disabled={disabled}
              onClick={() => onDecide("approve", comment)}
              type="button"
            >
              {busy
                ? "Working…"
                : signoff
                  ? "Sign off as reviewed"
                  : "Approve and publish"}
            </button>
            {signoff ? null : (
              <button
                className="rounded-lg border border-[var(--console-line)] bg-[var(--console-panel)] px-3 py-2 text-left text-sm font-medium text-[var(--console-ink)] disabled:cursor-not-allowed disabled:text-[var(--console-muted)]"
                disabled={disabled}
                onClick={() => onDecide("dismiss", comment)}
                type="button"
              >
                {busy ? "Working…" : "Dismiss proposal"}
              </button>
            )}
          </div>
        </>
      )}
    </article>
  );
}

export function ContentReviewPanel({ profile, canDecide }: ContentReviewPanelProps) {
  const [queue, setQueue] = useState<ContentReviewQueue>(EMPTY_QUEUE);
  const [loading, setLoading] = useState(false);
  const [busyKey, setBusyKey] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (!profile) {
      setQueue(EMPTY_QUEUE);
      return;
    }
    setLoading(true);
    try {
      setQueue(await loadContentReviewQueue());
      setError(null);
    } catch (cause) {
      setError(
        cause instanceof Error ? cause.message : "The review queue could not be loaded.",
      );
    } finally {
      setLoading(false);
    }
  }, [profile]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const decide = async (
    item: ContentReviewItem,
    decision: "approve" | "dismiss",
    comment: string,
  ) => {
    if (!profile) {
      return;
    }
    setBusyKey(item.item_key);
    try {
      await submitContentReview(profile, item, decision, comment);
      await refresh();
    } catch (cause) {
      setError(
        cause instanceof Error ? cause.message : "The decision could not be saved.",
      );
    } finally {
      setBusyKey(null);
    }
  };

  return (
    <section className="space-y-3.5 p-3.5" aria-label="Reference review">
      <div>
        <h2 className="text-sm font-semibold text-[var(--console-ink)]">
          Reference review
        </h2>
        <p className="mt-1 text-sm text-[var(--console-muted)]">
          Researched changes to officeholders, commanders and election dates. The public
          page keeps the current values until a change is approved here. Decisions are
          applied by the next sync.
        </p>
      </div>

      {!profile ? (
        <p className="text-sm text-[var(--console-muted)]">
          Sign in to see what is awaiting review.
        </p>
      ) : null}

      {profile && !canDecide ? (
        <p className="rounded-lg border border-[var(--console-warn)]/35 bg-[var(--console-warn)]/10 px-3 py-3 text-sm text-[var(--console-warn)]">
          Research assistants can read this queue. An analyst or admin makes the decision.
        </p>
      ) : null}

      {error ? (
        <p className="rounded-lg border border-[var(--console-danger)]/40 bg-[var(--console-danger)]/10 px-3 py-3 text-sm text-[var(--console-danger)]">
          {error}
        </p>
      ) : null}

      {profile && !loading && !error && queue.items.length === 0 ? (
        <p className="text-sm text-[var(--console-muted)]">
          Nothing is awaiting review.
        </p>
      ) : null}

      {loading && queue.items.length === 0 ? (
        <p className="text-sm text-[var(--console-muted)]">Loading…</p>
      ) : null}

      <div className="grid gap-3">
        {queue.items.map((item) => {
          const decision = latestDecision(item, queue.decisions);
          const decided = decision
            ? `${decision.decision === "approve" ? "Approved" : "Dismissed"} by ${decision.reviewer_name} on ${formatDay(decision.created_at)}. ${decision.applied_at ? "Applied." : "Waiting for the next sync."}`
            : null;

          return (
            <ReviewItemCard
              busy={busyKey === item.item_key}
              canDecide={canDecide}
              decided={decided}
              item={item}
              key={item.item_key}
              onDecide={(choice, comment) => void decide(item, choice, comment)}
            />
          );
        })}
      </div>

      {queue.generatedAt ? (
        <p className="text-xs text-[var(--console-muted)]">
          Queue as of {formatDay(queue.generatedAt)}.
        </p>
      ) : null}
    </section>
  );
}
