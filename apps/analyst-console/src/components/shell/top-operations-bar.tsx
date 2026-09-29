import type { ReactNode } from "react";

import { Search, X } from "lucide-react";

import { AccountBadgeMenu } from "@/components/shell/account-badge-menu";
import type { SessionProfile } from "@/lib/domain/types";

type TopOperationsBarProps = {
  search: string;
  onSearchChange: (value: string) => void;
  profile: SessionProfile;
  onSignOut: () => void;
  utilitySlot?: ReactNode;
  activeFilters?: Array<{
    key: string;
    label: string;
    onClear: () => void;
  }>;
};

export function TopOperationsBar({
  search,
  onSearchChange,
  profile,
  onSignOut,
  utilitySlot,
  activeFilters = [],
}: TopOperationsBarProps) {
  return (
    <header
      aria-label="SENTINEL Analyst Console"
      className="border-b border-[var(--console-line)] bg-[var(--console-bg)]"
    >
      <div className="flex items-center justify-between gap-4 px-4 py-3">
        <div className="min-w-0 shrink-0">
          <AccountBadgeMenu profile={profile} onSignOut={onSignOut} />
        </div>

        <form
          aria-label="Console search"
          role="search"
          className="flex min-w-0 flex-1 justify-center"
          onSubmit={(event) => event.preventDefault()}
        >
          <label className="sr-only" htmlFor="console-search">
            Search events, countries, and queue IDs
          </label>
          <div className="flex h-11 w-full max-w-[440px] items-center gap-2 rounded-full border border-[var(--console-line)] bg-[var(--console-panel)] px-4 py-2">
            <Search
              aria-hidden="true"
              className="h-4 w-4 text-[var(--console-muted)]"
            />
            <input
              id="console-search"
              className="w-full border-0 bg-transparent p-0 text-sm text-[var(--console-ink)] outline-none placeholder:text-[var(--console-muted)]"
              onChange={(event) => onSearchChange(event.target.value)}
              placeholder="Search events, countries, IDs"
              type="search"
              value={search}
            />
          </div>
        </form>

        <div
          aria-live="polite"
          className="flex shrink-0 items-center justify-end gap-2 text-xs text-[var(--console-muted)]"
        >
          {utilitySlot}
        </div>
      </div>

      {activeFilters.length > 0 ? (
        <div className="border-t border-[var(--console-line)] px-4 py-2.5">
          <div className="flex flex-wrap items-center justify-center gap-2">
            <span className="text-[11px] uppercase tracking-wide text-[var(--console-muted)]">
              Active filters
            </span>
            {activeFilters.map((filter) => (
              <button
                key={filter.key}
                className="inline-flex items-center gap-1.5 rounded-full border border-[var(--console-line)] bg-[var(--console-panel)] px-2.5 py-1 text-xs text-[var(--console-ink)] transition-colors hover:border-[var(--console-accent)]/40 hover:bg-[var(--console-panel-2)]"
                onClick={filter.onClear}
                type="button"
              >
                <span>{filter.label}</span>
                <X aria-hidden="true" className="h-3 w-3 text-[var(--console-muted)]" />
              </button>
            ))}
          </div>
        </div>
      ) : null}
    </header>
  );
}
