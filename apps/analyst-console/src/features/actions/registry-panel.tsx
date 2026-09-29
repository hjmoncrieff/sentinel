import { useEffect, useMemo, useState } from "react";

import type { QueueItem, RegistryActor, RegistryEditRecord } from "@/lib/domain/types";

type RegistryPanelProps = {
  item: QueueItem | null;
  actors: RegistryActor[];
  recentEdits: RegistryEditRecord[];
  authenticated: boolean;
  busy: boolean;
  saveError: string | null;
  onSubmit: (payload: {
    action: string;
    canonical_name: string;
    canonical_type: string;
    primary_country: string;
    aliases: string[];
    note: string;
  }) => Promise<void> | void;
};

function formatRegistryDate(value?: string | null): string {
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

export function RegistryPanel({
  item,
  actors,
  recentEdits,
  authenticated,
  busy,
  saveError,
  onSubmit,
}: RegistryPanelProps) {
  const [canonicalName, setCanonicalName] = useState("");
  const [canonicalType, setCanonicalType] = useState("state_actor");
  const [aliases, setAliases] = useState("");
  const [note, setNote] = useState("");

  useEffect(() => {
    setCanonicalName("");
    setAliases("");
    setNote("");
  }, [item?.event_id]);

  const country = item?.country || "";
  const matchingActors = useMemo(
    () =>
      actors
        .filter((actor) =>
          country
            ? String(actor.primary_country || "").toLowerCase() === country.toLowerCase()
            : true,
        )
        .slice(0, 8),
    [actors, country],
  );
  const dateLabel = formatRegistryDate(item?.event_date);

  return (
    <section className="space-y-3.5 p-3.5" aria-label="Registry actions">
      <div>
        <h2 className="text-sm font-semibold text-[var(--console-ink)]">
          Registry workflow
        </h2>
        <p className="mt-1 text-sm text-[var(--console-muted)]">
          Queue-adjacent registry requests keep actor cleanup inside the same review loop.
        </p>
      </div>

      <div className="rounded-lg border border-[var(--console-line)] bg-[var(--console-panel-2)] px-3 py-2.5">
        <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-[11px] uppercase tracking-wide text-[var(--console-muted)]">
          <span>{country || "Regional / not set"}</span>
          <span className="text-[var(--console-line-strong)]">/</span>
          <span>{dateLabel}</span>
        </div>
        <div className="mt-1.5 text-sm font-medium text-[var(--console-ink)]">
          {item?.headline || "No event selected"}
        </div>
      </div>

      {matchingActors.length ? (
        <div className="space-y-2">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-[var(--console-muted)]">
            Existing registry context
          </h3>
          <ul className="space-y-2">
            {matchingActors.map((actor) => (
              <li
                key={actor.registry_id}
                className="rounded-lg border border-[var(--console-line)] bg-[var(--console-panel)] p-3"
              >
                <div className="text-sm font-medium text-[var(--console-ink)]">
                  {actor.canonical_name || actor.registry_id}
                </div>
                <div className="mt-1 text-sm text-[var(--console-muted)]">
                  {[actor.canonical_type, actor.registry_status]
                    .filter(Boolean)
                    .join(" · ") || "No registry metadata"}
                </div>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {!authenticated ? (
        <p className="rounded-lg border border-[var(--console-line)] bg-[var(--console-panel-2)] px-3 py-3 text-sm text-[var(--console-muted)]">
          Sign in to submit registry requests.
        </p>
      ) : null}

      <form
        className="space-y-2.5"
        onSubmit={(event) => {
          event.preventDefault();
          void onSubmit({
            action: "upsert_registry_entry",
            canonical_name: canonicalName,
            canonical_type: canonicalType,
            primary_country: country,
            aliases: aliases
              .split(",")
              .map((value) => value.trim())
              .filter(Boolean),
            note,
          });
        }}
      >
        <label className="grid gap-1 text-sm text-[var(--console-muted)]">
          Canonical name
          <input
            className="rounded-lg border border-[var(--console-line)] bg-[var(--console-panel)] px-3 py-2 text-sm text-[var(--console-ink)] outline-none"
            disabled={!authenticated || busy}
            onChange={(event) => setCanonicalName(event.target.value)}
            placeholder="Actor or institution name"
            type="text"
            value={canonicalName}
          />
        </label>
        <label className="grid gap-1 text-sm text-[var(--console-muted)]">
          Canonical type
          <select
            className="rounded-lg border border-[var(--console-line)] bg-[var(--console-panel)] px-3 py-2 text-sm text-[var(--console-ink)] outline-none"
            disabled={!authenticated || busy}
            onChange={(event) => setCanonicalType(event.target.value)}
            value={canonicalType}
          >
            <option value="state_actor">state actor</option>
            <option value="non_state_actor">non-state actor</option>
            <option value="political_actor">political actor</option>
            <option value="security_actor">security actor</option>
          </select>
        </label>
        <label className="grid gap-1 text-sm text-[var(--console-muted)]">
          Aliases
          <input
            className="rounded-lg border border-[var(--console-line)] bg-[var(--console-panel)] px-3 py-2 text-sm text-[var(--console-ink)] outline-none"
            disabled={!authenticated || busy}
            onChange={(event) => setAliases(event.target.value)}
            placeholder="Comma-separated aliases"
            type="text"
            value={aliases}
          />
        </label>
        <label className="grid gap-1 text-sm text-[var(--console-muted)]">
          Request note
          <textarea
            className="min-h-20 rounded-lg border border-[var(--console-line)] bg-[var(--console-panel)] px-3 py-2 text-sm text-[var(--console-ink)] outline-none"
            disabled={!authenticated || busy}
            onChange={(event) => setNote(event.target.value)}
            placeholder="Explain what should be added, merged, or corrected in the registry."
            value={note}
          />
        </label>

        {saveError ? (
          <p className="rounded-lg border border-[var(--console-danger)]/40 bg-[var(--console-danger)]/10 px-3 py-3 text-sm text-[var(--console-danger)]">
            {saveError}
          </p>
        ) : null}

        <button
          className="w-full rounded-lg border border-[var(--console-accent)] bg-[var(--console-panel-2)] px-3 py-2 text-left text-sm font-medium text-[var(--console-ink)] disabled:cursor-not-allowed disabled:border-[var(--console-line)] disabled:text-[var(--console-muted)]"
          disabled={!authenticated || busy || !country || !canonicalName.trim()}
          type="submit"
        >
          {busy ? "Submitting…" : "Submit registry request"}
        </button>
      </form>

      {recentEdits.length ? (
        <div className="space-y-2">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-[var(--console-muted)]">
            Recent registry requests
          </h3>
          <ul className="space-y-2">
            {recentEdits.slice(0, 5).map((edit) => (
              <li
                key={edit.registry_edit_id ?? `${edit.action}-${edit.created_at}`}
                className="rounded-lg border border-[var(--console-line)] bg-[var(--console-panel)] p-3"
              >
                <div className="text-sm font-medium text-[var(--console-ink)]">
                  {edit.action || "registry_edit"}
                </div>
                <div className="mt-1 text-sm text-[var(--console-muted)]">
                  {[edit.editor_name, edit.editor_role, edit.created_at]
                    .filter(Boolean)
                    .join(" · ")}
                </div>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  );
}
