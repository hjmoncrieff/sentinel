import type { ReactNode } from "react";

import { Search, X } from "lucide-react";

type NavigatorSheetProps = {
  title: string;
  searchPlaceholder?: string;
  searchValue?: string;
  onSearchChange?: (value: string) => void;
  onClose: () => void;
  leftPane?: ReactNode;
  rightPane?: ReactNode;
  content?: ReactNode;
  compact?: boolean;
  contentClassName?: string;
};

export function NavigatorSheet({
  title,
  searchPlaceholder,
  searchValue = "",
  onSearchChange,
  onClose,
  leftPane,
  rightPane,
  content,
  compact = false,
  contentClassName,
}: NavigatorSheetProps) {
  const hasSearch = typeof onSearchChange === "function" && !!searchPlaceholder;
  const singlePane = content !== undefined;

  return (
    <div className="fixed inset-0 z-40" onClick={onClose}>
      <div className="absolute inset-0 bg-[#020814]/52 backdrop-blur-sm" />
      <section
        aria-label={title}
        className={
          compact
            ? "absolute right-6 top-[86px] flex h-[min(78vh,760px)] w-[min(760px,calc(100vw-48px))] min-h-0 flex-col overflow-hidden rounded-[28px] border border-[var(--console-line)] bg-[rgba(8,16,28,0.98)] shadow-[0_24px_80px_rgba(0,0,0,0.45)]"
            : "absolute inset-x-6 bottom-6 top-[86px] flex min-h-0 flex-col overflow-hidden rounded-[28px] border border-[var(--console-line)] bg-[rgba(8,16,28,0.96)] shadow-[0_24px_80px_rgba(0,0,0,0.45)]"
        }
        onClick={(event) => event.stopPropagation()}
      >
        <div
          className={
            compact
              ? "flex items-center gap-3 border-b border-[var(--console-line)] px-5 py-4"
              : "flex items-center gap-3 border-b border-[var(--console-line)] px-6 py-5"
          }
        >
          {hasSearch ? (
            <div className="flex min-w-0 flex-1 items-center gap-3 rounded-2xl border border-[var(--console-line)] bg-[var(--console-panel)] px-4 py-3">
              <Search
                aria-hidden="true"
                className="h-5 w-5 shrink-0 text-[var(--console-muted)]"
              />
              <input
                className="w-full border-0 bg-transparent p-0 text-base text-[var(--console-ink)] outline-none placeholder:text-[var(--console-muted)]"
                onChange={(event) => onSearchChange(event.target.value)}
                placeholder={searchPlaceholder}
                type="search"
                value={searchValue}
              />
            </div>
          ) : (
            <div className="flex min-w-0 flex-1 items-center">
              <div>
                {!compact ? (
                  <div className="text-xs uppercase tracking-wide text-[var(--console-muted)]">
                    Navigator
                  </div>
                ) : null}
                <div
                  className={
                    compact
                      ? "text-sm font-medium text-[var(--console-ink)]"
                      : "mt-1 text-base font-medium text-[var(--console-ink)]"
                  }
                >
                  {title}
                </div>
              </div>
            </div>
          )}
          <button
            aria-label={`Close ${title}`}
            className="inline-flex h-11 w-11 items-center justify-center rounded-full border border-[var(--console-line)] bg-[var(--console-panel)] text-[var(--console-muted)] transition-colors hover:bg-[var(--console-panel-2)] hover:text-[var(--console-ink)]"
            onClick={onClose}
            type="button"
          >
            <X aria-hidden="true" className="h-4 w-4" />
          </button>
        </div>

        {singlePane ? (
          <div
            className={
              compact
                ? "min-h-0 flex-1 overflow-y-auto px-5 py-4"
                : "min-h-0 flex-1 overflow-y-auto px-6 py-5"
            }
          >
            <div className={contentClassName}>{content}</div>
          </div>
        ) : (
          <div className="grid min-h-0 flex-1 gap-0 lg:grid-cols-[1.2fr_1fr]">
            <div className="min-h-0 overflow-y-auto border-r border-[var(--console-line)] px-6 py-5">
              {leftPane}
            </div>
            <div className="min-h-0 overflow-y-auto px-6 py-5">{rightPane}</div>
          </div>
        )}
      </section>
    </div>
  );
}
