import {
  BookOpenText,
  Database,
  Send,
  ShieldCheck,
} from "lucide-react";

import { cn } from "@/lib/cn";

const items = [
  { key: "review", label: "Review", icon: BookOpenText, current: true },
  { key: "release", label: "Release", icon: Send },
  { key: "audit", label: "Audit", icon: ShieldCheck },
  { key: "registry", label: "Registry", icon: Database },
];

export function GlobalRail() {
  return (
    <nav
      aria-label="Global workspace"
      className="flex h-screen w-[72px] shrink-0 flex-col items-center gap-2 border-r border-[var(--console-line)] bg-[var(--console-bg-soft)] px-2 py-3"
    >
      <div className="mb-2 flex h-10 w-10 items-center justify-center rounded-md border border-[var(--console-line)] bg-[var(--console-panel)] text-xs font-semibold tracking-[0.08em] text-[var(--console-muted)]">
        SN
      </div>
      {items.map((item) => {
        const Icon = item.icon;

        return (
          <button
            key={item.key}
            aria-current={item.current ? "page" : undefined}
            aria-label={item.label}
            className={cn(
              "flex h-11 w-11 items-center justify-center rounded-md border transition-colors",
              item.current
                ? "border-[var(--console-accent)] bg-[var(--console-panel-2)] text-[var(--console-ink)]"
                : "border-transparent bg-[var(--console-panel)] text-[var(--console-muted)] hover:border-[var(--console-line)] hover:text-[var(--console-ink)]",
            )}
            title={item.label}
            type="button"
          >
            <Icon aria-hidden="true" className="h-4 w-4" />
            <span className="sr-only">{item.label}</span>
          </button>
        );
      })}
    </nav>
  );
}
