import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

type WorkspaceFrameProps = {
  actions: ReactNode;
  actionsHeader?: ReactNode;
  brief: ReactNode;
  briefHeader?: ReactNode;
  queue: ReactNode;
};

export function WorkspaceFrame({
  actions,
  actionsHeader,
  brief,
  briefHeader,
  queue,
}: WorkspaceFrameProps) {
  return (
    <main
      aria-label="Analyst workspace"
      className={cn(
        "grid min-h-0 flex-1 grid-cols-[304px_minmax(0,1fr)_332px]",
        "overflow-hidden",
      )}
    >
      <aside
        aria-label="Review queue"
        className="overflow-hidden border-r border-[var(--console-line)] bg-[var(--console-panel)]"
      >
        {queue}
      </aside>
      <section
        aria-label="Event brief"
        className="flex min-h-0 flex-col overflow-hidden border-r border-[var(--console-line)] bg-[var(--console-panel-2)]"
      >
        {briefHeader ? (
          <div className="flex items-center justify-center border-b border-[var(--console-line)] px-3 py-2">
            {briefHeader}
          </div>
        ) : null}
        <div className="min-h-0 flex-1 overflow-y-auto">{brief}</div>
      </section>
      <section
        aria-label="Review actions"
        className="flex min-h-0 flex-col overflow-hidden bg-[var(--console-panel)]"
      >
        {actionsHeader ? (
          <div className="flex items-center justify-center border-b border-[var(--console-line)] px-3 py-2">
            {actionsHeader}
          </div>
        ) : null}
        <div className="min-h-0 flex-1 overflow-y-auto">{actions}</div>
      </section>
    </main>
  );
}
