import { Lock } from "lucide-react";

import { cn } from "@/lib/cn";
import type { CenterPanelTab } from "@/lib/domain/types";

type TabItem = {
  key: CenterPanelTab;
  label: string;
  restricted?: boolean;
};

const tabs: TabItem[] = [
  { key: "briefing", label: "Brief" },
  { key: "ai-analysis", label: "AI Analysis", restricted: true },
  { key: "country-brief", label: "Country Brief", restricted: true },
  { key: "data", label: "Data" },
];

type CenterTabBarProps = {
  activeTab: CenterPanelTab;
  onTabChange: (tab: CenterPanelTab) => void;
  restrictedIntelVisible: boolean;
};

export function CenterTabBar({
  activeTab,
  onTabChange,
  restrictedIntelVisible,
}: CenterTabBarProps) {
  return (
    <div className="inline-flex items-center gap-1 rounded-full border border-[var(--console-line)] bg-[var(--console-panel)] p-1">
      {tabs.map((tab) => {
        const disabled = tab.restricted && !restrictedIntelVisible;

        return (
          <button
            key={tab.key}
            aria-pressed={activeTab === tab.key}
            className={cn(
              "inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-medium transition-colors",
              activeTab === tab.key
                ? "bg-[var(--console-panel-3)] text-[var(--console-ink)]"
                : "text-[var(--console-muted)] hover:bg-[var(--console-panel-2)] hover:text-[var(--console-ink)]",
              disabled && "cursor-not-allowed opacity-60 hover:text-[var(--console-muted)]",
            )}
            disabled={disabled}
            onClick={() => onTabChange(tab.key)}
            type="button"
          >
            {disabled ? <Lock aria-hidden="true" className="h-3.5 w-3.5" /> : null}
            <span>{tab.label}</span>
          </button>
        );
      })}
    </div>
  );
}
