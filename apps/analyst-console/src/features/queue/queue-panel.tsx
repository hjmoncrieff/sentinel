import { useState } from "react";

import { Plus } from "lucide-react";

import { cn } from "@/lib/cn";
import type { QueueItem, QueueScope, QueueWorklist } from "@/lib/domain/types";

import { QueueCard } from "./queue-card";

type QueuePanelProps = {
  rows: QueueItem[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  queueScope: QueueScope;
  onQueueScopeChange: (scope: QueueScope) => void;
  worklistFilter: QueueWorklist;
  onWorklistFilterChange: (worklist: QueueWorklist) => void;
  queueHealth: {
    publishReady: number;
    corroborate: number;
    registry: number;
  };
  createOpen: boolean;
  onCreateOpenChange: (open: boolean) => void;
  onCreateManualEvent: (payload: {
    headline: string;
    country: string;
    event_date: string;
    event_type: string;
    summary: string;
    source_primary: string;
    salience: string;
    confidence: string;
    review_priority: string;
    location: string;
    note: string;
  }) => Promise<void> | void;
  createBusy: boolean;
  createError?: string | null;
  loadError?: string | null;
};

export function QueuePanel({
  rows,
  selectedId,
  onSelect,
  queueScope,
  onQueueScopeChange,
  worklistFilter,
  onWorklistFilterChange,
  queueHealth,
  createOpen,
  onCreateOpenChange,
  onCreateManualEvent,
  createBusy,
  createError = null,
  loadError = null,
}: QueuePanelProps) {
  const [draft, setDraft] = useState({
    headline: "",
    country: "",
    event_date: "",
    event_type: "other",
    summary: "",
    source_primary: "Manual submission",
    salience: "medium",
    confidence: "medium",
    review_priority: "medium",
    location: "",
    note: "",
  });

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="border-b border-[var(--console-line)] px-3 py-2">
        <div className="flex items-center justify-center gap-1">
          {[
            { key: "all" as const, label: "All" },
            { key: "attention" as const, label: "Review now" },
          ].map((option) => (
            <button
              key={option.key}
              aria-pressed={queueScope === option.key}
              className={cn(
                "inline-flex items-center justify-center rounded-full px-3 py-1.5 text-xs font-medium transition-colors",
                queueScope === option.key
                  ? "bg-[var(--console-panel-3)] text-[var(--console-ink)]"
                  : "text-[var(--console-muted)] hover:bg-[var(--console-panel)] hover:text-[var(--console-ink)]",
              )}
              onClick={() => onQueueScopeChange(option.key)}
              type="button"
            >
              {option.label}
            </button>
          ))}
          <button
            className="inline-flex items-center justify-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-medium text-[var(--console-muted)] transition-colors hover:bg-[var(--console-panel)] hover:text-[var(--console-ink)]"
            onClick={() => onCreateOpenChange(!createOpen)}
            type="button"
          >
            <Plus aria-hidden="true" className="h-3.5 w-3.5" />
            Add
          </button>
        </div>
        <div className="mt-2.5 flex items-center justify-center gap-1.5">
          {[
            {
              key: "publish-ready" as const,
              label: "Ready",
              count: queueHealth.publishReady,
            },
            {
              key: "corroborate" as const,
              label: "Corroborate",
              count: queueHealth.corroborate,
            },
            {
              key: "registry" as const,
              label: "Registry",
              count: queueHealth.registry,
            },
          ].map((metric) => {
            const active = worklistFilter === metric.key;

            return (
              <button
                key={metric.key}
                aria-pressed={active}
                className={cn(
                  "inline-flex min-w-[88px] items-center justify-center gap-1 rounded-full border px-2.5 py-1 text-[11px] transition-colors",
                  active
                    ? "border-[var(--console-accent)] bg-[var(--console-panel-2)] text-[var(--console-ink)]"
                    : "border-[var(--console-line)] bg-[var(--console-panel)] text-[var(--console-muted)] hover:bg-[var(--console-panel-2)] hover:text-[var(--console-ink)]",
                )}
                onClick={() =>
                  onWorklistFilterChange(active ? "all" : metric.key)
                }
                type="button"
              >
                <span>{metric.label}</span>
                <span className="text-[var(--console-ink)]">{metric.count}</span>
              </button>
            );
          })}
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto p-2.5">
        {createOpen ? (
          <form
            className="mb-4 space-y-3 rounded-md border border-[var(--console-line)] bg-[var(--console-panel)] p-3"
            onSubmit={(event) => {
              event.preventDefault();
              void (async () => {
                await onCreateManualEvent(draft);
                setDraft({
                  headline: "",
                  country: "",
                  event_date: "",
                  event_type: "other",
                  summary: "",
                  source_primary: "Manual submission",
                  salience: "medium",
                  confidence: "medium",
                  review_priority: "medium",
                  location: "",
                  note: "",
                });
                onCreateOpenChange(false);
              })().catch(() => {
                // Keep the draft open on failure so the user can correct and resubmit.
              });
            }}
          >
            <div>
              <h3 className="text-sm font-semibold text-[var(--console-ink)]">
                Add manual event
              </h3>
              <p className="mt-1 text-sm text-[var(--console-muted)]">
                Capture an event that the scraper missed and send it into the review queue.
              </p>
            </div>

            <label className="grid gap-1 text-sm text-[var(--console-muted)]">
              Headline
              <input
                className="rounded-md border border-[var(--console-line)] bg-[var(--console-bg)] px-3 py-2 text-sm text-[var(--console-ink)] outline-none"
                onChange={(event) =>
                  setDraft((current) => ({ ...current, headline: event.target.value }))
                }
                required
                type="text"
                value={draft.headline}
              />
            </label>

            <div className="grid grid-cols-2 gap-3">
              <label className="grid gap-1 text-sm text-[var(--console-muted)]">
                Country
                <input
                  className="rounded-md border border-[var(--console-line)] bg-[var(--console-bg)] px-3 py-2 text-sm text-[var(--console-ink)] outline-none"
                  onChange={(event) =>
                    setDraft((current) => ({ ...current, country: event.target.value }))
                  }
                  type="text"
                  value={draft.country}
                />
              </label>
              <label className="grid gap-1 text-sm text-[var(--console-muted)]">
                Date
                <input
                  className="rounded-md border border-[var(--console-line)] bg-[var(--console-bg)] px-3 py-2 text-sm text-[var(--console-ink)] outline-none"
                  onChange={(event) =>
                    setDraft((current) => ({ ...current, event_date: event.target.value }))
                  }
                  type="date"
                  value={draft.event_date}
                />
              </label>
            </div>

            <div className="grid grid-cols-3 gap-3">
              <label className="grid gap-1 text-sm text-[var(--console-muted)]">
                Type
                <select
                  className="rounded-md border border-[var(--console-line)] bg-[var(--console-bg)] px-3 py-2 text-sm text-[var(--console-ink)] outline-none"
                  onChange={(event) =>
                    setDraft((current) => ({ ...current, event_type: event.target.value }))
                  }
                  value={draft.event_type}
                >
                  <option value="coup">coup</option>
                  <option value="purge">purge</option>
                  <option value="conflict">conflict</option>
                  <option value="reform">reform</option>
                  <option value="aid">aid</option>
                  <option value="exercise">exercise</option>
                  <option value="oc">oc</option>
                  <option value="protest">protest</option>
                  <option value="peace">peace</option>
                  <option value="other">other</option>
                </select>
              </label>
              <label className="grid gap-1 text-sm text-[var(--console-muted)]">
                Salience
                <select
                  className="rounded-md border border-[var(--console-line)] bg-[var(--console-bg)] px-3 py-2 text-sm text-[var(--console-ink)] outline-none"
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
                Priority
                <select
                  className="rounded-md border border-[var(--console-line)] bg-[var(--console-bg)] px-3 py-2 text-sm text-[var(--console-ink)] outline-none"
                  onChange={(event) =>
                    setDraft((current) => ({
                      ...current,
                      review_priority: event.target.value,
                    }))
                  }
                  value={draft.review_priority}
                >
                  <option value="high">high</option>
                  <option value="medium">medium</option>
                  <option value="low">low</option>
                </select>
              </label>
            </div>

            <label className="grid gap-1 text-sm text-[var(--console-muted)]">
              Summary
              <textarea
                className="min-h-24 rounded-md border border-[var(--console-line)] bg-[var(--console-bg)] px-3 py-2 text-sm text-[var(--console-ink)] outline-none"
                onChange={(event) =>
                  setDraft((current) => ({ ...current, summary: event.target.value }))
                }
                value={draft.summary}
              />
            </label>

            <div className="grid grid-cols-2 gap-3">
              <label className="grid gap-1 text-sm text-[var(--console-muted)]">
                Source
                <input
                  className="rounded-md border border-[var(--console-line)] bg-[var(--console-bg)] px-3 py-2 text-sm text-[var(--console-ink)] outline-none"
                  onChange={(event) =>
                    setDraft((current) => ({
                      ...current,
                      source_primary: event.target.value,
                    }))
                  }
                  type="text"
                  value={draft.source_primary}
                />
              </label>
              <label className="grid gap-1 text-sm text-[var(--console-muted)]">
                Location
                <input
                  className="rounded-md border border-[var(--console-line)] bg-[var(--console-bg)] px-3 py-2 text-sm text-[var(--console-ink)] outline-none"
                  onChange={(event) =>
                    setDraft((current) => ({ ...current, location: event.target.value }))
                  }
                  type="text"
                  value={draft.location}
                />
              </label>
            </div>

            <label className="grid gap-1 text-sm text-[var(--console-muted)]">
              Submission note
              <textarea
                className="min-h-20 rounded-md border border-[var(--console-line)] bg-[var(--console-bg)] px-3 py-2 text-sm text-[var(--console-ink)] outline-none"
                onChange={(event) =>
                  setDraft((current) => ({ ...current, note: event.target.value }))
                }
                placeholder="Why this event matters or what the scraper missed."
                value={draft.note}
              />
            </label>

            {createError ? (
              <p className="rounded-md border border-[var(--console-danger)]/40 bg-[var(--console-danger)]/10 px-3 py-3 text-sm text-[var(--console-danger)]">
                {createError}
              </p>
            ) : null}

            <div className="flex items-center gap-2">
              <button
                className="rounded-md border border-[var(--console-accent)] bg-[var(--console-panel-2)] px-3 py-2 text-sm font-medium text-[var(--console-ink)] disabled:cursor-not-allowed disabled:border-[var(--console-line)] disabled:text-[var(--console-muted)]"
                disabled={createBusy || !draft.headline.trim()}
                type="submit"
              >
                {createBusy ? "Adding…" : "Add to queue"}
              </button>
              <button
                className="rounded-md border border-[var(--console-line)] bg-[var(--console-bg)] px-3 py-2 text-sm text-[var(--console-muted)]"
                onClick={() => onCreateOpenChange(false)}
                type="button"
              >
                Cancel
              </button>
            </div>
          </form>
        ) : null}

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
          <ul className="space-y-1.5" aria-label="Visible queue items">
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
