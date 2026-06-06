import { Search } from "lucide-react";

type TopOperationsBarProps = {
  search: string;
  onSearchChange: (value: string) => void;
  itemCount: number;
};

export function TopOperationsBar({
  search,
  onSearchChange,
  itemCount,
}: TopOperationsBarProps) {
  return (
    <header
      aria-label="SENTINEL Analyst Console"
      className="flex items-center justify-between gap-4 border-b border-[var(--console-line)] bg-[var(--console-bg)] px-4 py-3"
    >
      <div className="min-w-0">
        <div className="text-sm font-semibold text-[var(--console-ink)]">
          Review Workspace
        </div>
        <div className="text-xs text-[var(--console-muted)]">
          Operations desk for analyst review and release control
        </div>
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
        <div className="flex w-full max-w-[420px] items-center gap-2 rounded-md border border-[var(--console-line)] bg-[var(--console-panel)] px-3 py-2">
          <Search aria-hidden="true" className="h-4 w-4 text-[var(--console-muted)]" />
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
        className="text-right text-xs text-[var(--console-muted)]"
      >
        <div>Supabase synced</div>
        <div>{itemCount} visible queue item(s)</div>
      </div>
    </header>
  );
}
