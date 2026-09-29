import { cn } from "@/lib/cn";
import type { ConsoleWorkspace } from "@/lib/domain/types";

const tabs: Array<{ key: ConsoleWorkspace; label: string }> = [
  { key: "review", label: "Edit" },
  { key: "release", label: "Release" },
  { key: "audit", label: "Audit" },
  { key: "registry", label: "Registry" },
];

type WorkspaceTabBarProps = {
  activeWorkspace: ConsoleWorkspace;
  onWorkspaceChange: (workspace: ConsoleWorkspace) => void;
};

export function WorkspaceTabBar({
  activeWorkspace,
  onWorkspaceChange,
}: WorkspaceTabBarProps) {
  return (
    <div className="inline-flex items-center gap-1 rounded-full border border-[var(--console-line)] bg-[var(--console-panel)] p-1">
      {tabs.map((tab) => (
        <button
          key={tab.key}
          aria-pressed={activeWorkspace === tab.key}
          className={cn(
            "inline-flex items-center justify-center rounded-full px-3 py-1.5 text-xs font-medium transition-colors",
            activeWorkspace === tab.key
              ? "bg-[var(--console-panel-3)] text-[var(--console-ink)]"
              : "text-[var(--console-muted)] hover:bg-[var(--console-panel-2)] hover:text-[var(--console-ink)]",
          )}
          onClick={() => onWorkspaceChange(tab.key)}
          type="button"
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}
