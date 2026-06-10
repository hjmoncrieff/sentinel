import { Filter } from "lucide-react";
import { useMemo, useState } from "react";

import { cn } from "@/lib/cn";
import type {
  QueueScope,
  QueueSort,
  QueueWorklist,
  ReviewPriority,
} from "@/lib/domain/types";

import { NavigatorSheet } from "./navigator-sheet";

type FilterManagerProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  availableCategories: string[];
  availableCountries: string[];
  categoryFilter: string;
  countryFilter: string;
  queueScope: QueueScope;
  worklistFilter: QueueWorklist;
  priorityFilter: "all" | ReviewPriority;
  sortOrder: QueueSort;
  onCategoryFilterChange: (category: string) => void;
  onCountryFilterChange: (country: string) => void;
  onQueueScopeChange: (scope: QueueScope) => void;
  onWorklistFilterChange: (worklist: QueueWorklist) => void;
  onPriorityFilterChange: (priority: "all" | ReviewPriority) => void;
  onSortOrderChange: (sort: QueueSort) => void;
};

const scopeOptions: Array<{ value: QueueScope; label: string }> = [
  { value: "all", label: "All events" },
  { value: "attention", label: "Review now" },
];

const priorityOptions: Array<{ value: "all" | ReviewPriority; label: string }> = [
  { value: "all", label: "Any" },
  { value: "high", label: "High" },
  { value: "medium", label: "Medium" },
  { value: "low", label: "Low" },
];

const worklistOptions: Array<{ value: QueueWorklist; label: string }> = [
  { value: "all", label: "Everything" },
  { value: "publish-ready", label: "Publish ready" },
  { value: "corroborate", label: "Corroborate" },
  { value: "registry", label: "Registry" },
  { value: "duplicates", label: "Duplicates" },
];

const sortOptions: Array<{ value: QueueSort; label: string }> = [
  { value: "priority", label: "Priority first" },
  { value: "most-recent", label: "Most recent" },
];

function optionButton(active: boolean): string {
  return cn(
    "rounded-xl border px-3 py-2 text-sm leading-none transition-colors",
    active
      ? "border-[var(--console-accent)] bg-[var(--console-panel-2)] text-[var(--console-ink)]"
      : "border-[var(--console-line)] bg-[var(--console-panel)] text-[var(--console-muted)] hover:bg-[var(--console-panel-2)] hover:text-[var(--console-ink)]",
  );
}

function compactOptionButton(active: boolean): string {
  return cn(
    "rounded-full border px-2.5 py-1.5 text-xs leading-none transition-colors",
    active
      ? "border-[var(--console-accent)] bg-[var(--console-panel-2)] text-[var(--console-ink)]"
      : "border-[var(--console-line)] bg-[var(--console-panel)] text-[var(--console-muted)] hover:bg-[var(--console-panel-2)] hover:text-[var(--console-ink)]",
  );
}

function renderChipGroup<T extends string>({
  label,
  options,
  activeValue,
  onSelect,
  helper,
  columns = 2,
  className,
  compact = false,
}: {
  label: string;
  options: Array<{ value: T; label: string }>;
  activeValue: T;
  onSelect: (value: T) => void;
  helper?: string;
  columns?: 2 | 3 | 4;
  className?: string;
  compact?: boolean;
}) {
  return (
    <section
      className={cn(
        "rounded-2xl border border-[var(--console-line)] bg-[var(--console-panel)]/55 p-3",
        className,
      )}
    >
      <div className="mb-2 flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="text-sm font-medium text-[var(--console-ink)]">{label}</div>
          {helper ? <div className="mt-1 text-[11px] text-[var(--console-muted)]">{helper}</div> : null}
        </div>
      </div>
      <div
        className={cn(
          "grid gap-2",
          columns === 4
            ? "grid-cols-2 xl:grid-cols-4"
            : columns === 3
              ? "grid-cols-2 xl:grid-cols-3"
              : "grid-cols-2",
        )}
      >
        {options.map((option) => (
          <button
            key={option.value}
            aria-pressed={activeValue === option.value}
            className={
              compact
                ? compactOptionButton(activeValue === option.value)
                : optionButton(activeValue === option.value)
            }
            onClick={() => onSelect(option.value)}
            type="button"
          >
            {option.label}
          </button>
        ))}
      </div>
    </section>
  );
}

function renderSearchablePicker({
  label,
  helper,
  query,
  onQueryChange,
  options,
  activeValue,
  onSelect,
}: {
  label: string;
  helper?: string;
  query: string;
  onQueryChange: (value: string) => void;
  options: Array<{ value: string; label: string }>;
  activeValue: string;
  onSelect: (value: string) => void;
}) {
  const normalized = query.trim().toLowerCase();
  const selectedOption = options.find((option) => option.value === activeValue);
  const visibleOptions = options
    .filter((option) => {
      if (option.value === "all") {
        return true;
      }

      if (!normalized) {
        return true;
      }

      return option.label.toLowerCase().includes(normalized);
    })
    .slice(0, normalized ? 12 : 8);

  return (
    <section className="rounded-2xl border border-[var(--console-line)] bg-[var(--console-panel)]/55 p-3 md:col-span-2">
      <div className="mb-2 flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="text-sm font-medium text-[var(--console-ink)]">{label}</div>
          {helper ? <div className="mt-1 text-[11px] text-[var(--console-muted)]">{helper}</div> : null}
        </div>
        <span className="rounded-full border border-[var(--console-line)] px-2 py-1 text-[10px] uppercase tracking-wide text-[var(--console-muted)]">
          {selectedOption?.label ?? "All"}
        </span>
      </div>
      <div className="grid gap-2">
        <input
          className="h-9 rounded-xl border border-[var(--console-line)] bg-[var(--console-panel)] px-3 text-sm text-[var(--console-ink)] outline-none placeholder:text-[var(--console-muted)]"
          onChange={(event) => onQueryChange(event.target.value)}
          placeholder={`Search ${label.toLowerCase()}`}
          type="search"
          value={query}
        />
        <div className="flex flex-wrap gap-2">
          {visibleOptions.map((option) => (
            <button
              key={option.value}
              aria-pressed={activeValue === option.value}
              className={cn(
                "rounded-full border px-2.5 py-1 text-xs leading-none transition-colors",
                activeValue === option.value
                  ? "border-[var(--console-accent)] bg-[var(--console-panel-2)] text-[var(--console-ink)]"
                  : "border-[var(--console-line)] bg-[var(--console-panel)] text-[var(--console-muted)] hover:bg-[var(--console-panel-2)] hover:text-[var(--console-ink)]",
              )}
              onClick={() => onSelect(option.value)}
              type="button"
            >
              {option.label}
            </button>
          ))}
        </div>
      </div>
    </section>
  );
}

export function FilterManager({
  open,
  onOpenChange,
  availableCategories,
  availableCountries,
  categoryFilter,
  countryFilter,
  queueScope,
  worklistFilter,
  priorityFilter,
  sortOrder,
  onCategoryFilterChange,
  onCountryFilterChange,
  onQueueScopeChange,
  onWorklistFilterChange,
  onPriorityFilterChange,
  onSortOrderChange,
}: FilterManagerProps) {
  const [countryQuery, setCountryQuery] = useState("");
  const [categoryQuery, setCategoryQuery] = useState("");
  const activeCount =
    (queueScope !== "all" ? 1 : 0) +
    (worklistFilter !== "all" ? 1 : 0) +
    (priorityFilter !== "all" ? 1 : 0) +
    (countryFilter !== "all" ? 1 : 0) +
    (categoryFilter !== "all" ? 1 : 0) +
    (sortOrder !== "priority" ? 1 : 0);

  const countryOptions = [
    { value: "all", label: "All countries" },
    ...availableCountries.map((country) => ({ value: country, label: country })),
  ];
  const categoryOptions = [
    { value: "all", label: "All categories" },
    ...availableCategories.map((category) => ({ value: category, label: category })),
  ];
  const normalizedCountryOptions = useMemo(
    () =>
      countryOptions.map((option) => ({
        value: option.value,
        label: option.label,
      })),
    [countryOptions],
  );
  const normalizedCategoryOptions = useMemo(
    () =>
      categoryOptions.map((option) => ({
        value: option.value,
        label: option.label,
      })),
    [categoryOptions],
  );

  return (
    <div className="relative">
      <button
        aria-expanded={open}
        aria-haspopup="dialog"
        aria-label="Open filters"
        className={cn(
          "relative inline-flex h-10 items-center justify-center gap-2 rounded-full border px-3 text-sm font-medium transition-colors",
          open
            ? "border-[var(--console-accent)] bg-[var(--console-panel-2)] text-[var(--console-ink)]"
            : "border-[var(--console-line)] bg-[var(--console-panel)] text-[var(--console-muted)] hover:bg-[var(--console-panel-2)] hover:text-[var(--console-ink)]",
        )}
        onClick={() => onOpenChange(!open)}
        type="button"
      >
        <Filter aria-hidden="true" className="h-4 w-4" />
        {open ? <span>Filters</span> : null}
        {activeCount ? (
          <span className="absolute -right-1 -top-1 inline-flex min-w-5 items-center justify-center rounded-full bg-[var(--console-accent)] px-1.5 py-0.5 text-[10px] font-semibold text-[#071019]">
            {activeCount}
          </span>
        ) : null}
      </button>

      {open ? (
        <NavigatorSheet
          title="Queue filters"
          compact
          contentClassName="space-y-3"
          onClose={() => onOpenChange(false)}
          content={
            <div className="grid gap-3 md:grid-cols-2">
              {renderChipGroup({
                label: "Queue",
                helper: "Full queue or review-now only.",
                options: scopeOptions,
                activeValue: queueScope,
                onSelect: onQueueScopeChange,
                compact: true,
              })}

              {renderChipGroup({
                label: "Sort",
                helper: "Rank-first or recent-first.",
                options: sortOptions,
                activeValue: sortOrder,
                onSelect: onSortOrderChange,
                compact: true,
              })}

              {renderChipGroup({
                label: "Priority",
                helper: "Narrow urgency.",
                options: priorityOptions,
                activeValue: priorityFilter,
                onSelect: onPriorityFilterChange,
                compact: true,
              })}

              {renderChipGroup({
                label: "Worklist",
                helper: "Targeted analyst lanes.",
                options: worklistOptions,
                activeValue: worklistFilter,
                onSelect: onWorklistFilterChange,
                columns: 4,
                className: "md:col-span-2",
                compact: true,
              })}

              {renderSearchablePicker({
                label: "Country",
                helper: "Focus by country.",
                query: countryQuery,
                onQueryChange: setCountryQuery,
                options: normalizedCountryOptions,
                activeValue: countryFilter,
                onSelect: onCountryFilterChange,
              })}

              {renderSearchablePicker({
                label: "Event type",
                helper: "Focus by category.",
                query: categoryQuery,
                onQueryChange: setCategoryQuery,
                options: normalizedCategoryOptions,
                activeValue: categoryFilter,
                onSelect: onCategoryFilterChange,
              })}
            </div>
          }
        />
      ) : null}
    </div>
  );
}
