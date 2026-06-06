import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

type WorkspaceFrameProps = {
  actions: ReactNode;
  brief: ReactNode;
  queue: ReactNode;
};

export function WorkspaceFrame({
  actions,
  brief,
  queue,
}: WorkspaceFrameProps) {
  return (
    <main
      aria-label="Analyst workspace"
      className={cn(
        "grid min-h-0 flex-1 grid-cols-[320px_minmax(0,1fr)_336px]",
        "overflow-hidden",
      )}
    >
      <aside
        aria-label="Review queue"
        className="overflow-y-auto border-r border-[var(--console-line)] bg-[var(--console-panel)]"
      >
        {queue}
      </aside>
      <section
        aria-label="Event brief"
        className="overflow-y-auto border-r border-[var(--console-line)] bg-[var(--console-panel-2)]"
      >
        {brief}
      </section>
      <section
        aria-label="Review actions"
        className="overflow-y-auto bg-[var(--console-panel)]"
      >
        {actions}
      </section>
    </main>
  );
}
