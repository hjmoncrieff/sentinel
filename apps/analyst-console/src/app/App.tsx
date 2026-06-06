import { useEffect, useReducer } from "react";

import { GlobalRail } from "@/components/shell/global-rail";
import { TopOperationsBar } from "@/components/shell/top-operations-bar";
import { WorkspaceFrame } from "@/components/shell/workspace-frame";
import { QueuePanel } from "@/features/queue/queue-panel";
import { loadConsoleData } from "@/lib/api/load-console-data";
import { getVisibleQueue } from "@/lib/domain/queue";
import {
  consoleReducer,
  initialConsoleState,
} from "@/lib/state/console-reducer";

export function App() {
  const [state, dispatch] = useReducer(consoleReducer, initialConsoleState);

  useEffect(() => {
    let active = true;

    void loadConsoleData()
      .then((rows) => {
        if (!active) {
          return;
        }

        dispatch({ type: "queueLoaded", payload: rows });
      })
      .catch((error: unknown) => {
        if (!active) {
          return;
        }

        const message =
          error instanceof Error
            ? error.message
            : "Failed to load review queue.";
        dispatch({ type: "loadFailed", payload: message });
      });

    return () => {
      active = false;
    };
  }, []);

  const visibleQueue = getVisibleQueue(state.queue, {
    search: state.search,
    priorityFilter: state.priorityFilter,
  });
  const selectedItem =
    visibleQueue.find((row) => row.event_id === state.selectedId) ??
    visibleQueue[0] ??
    null;

  return (
    <div className="flex min-h-screen bg-[var(--console-bg)] text-[var(--console-ink)]">
      <GlobalRail />
      <div className="flex min-h-screen min-w-0 flex-1 flex-col">
        <TopOperationsBar
          itemCount={visibleQueue.length}
          onSearchChange={(value) =>
            dispatch({ type: "searchChanged", payload: value })
          }
          search={state.search}
        />
        <WorkspaceFrame
          actions={
            <div className="space-y-3 p-4">
              <h2 className="text-sm font-semibold text-[var(--console-ink)]">
                Review actions
              </h2>
              <p className="text-sm text-[var(--console-muted)]">
                Action surface scaffold for review, release, and audit steps.
              </p>
            </div>
          }
          brief={
            <div className="space-y-3 p-4">
              <h2 className="text-sm font-semibold text-[var(--console-ink)]">
                Event brief
              </h2>
              {selectedItem ? (
                <>
                  <p className="text-sm text-[var(--console-ink)]">
                    {selectedItem.headline}
                  </p>
                  <p className="text-sm text-[var(--console-muted)]">
                    {selectedItem.country ?? "Regional"} ·{" "}
                    {selectedItem.review_priority} priority
                  </p>
                </>
              ) : state.loadError ? (
                <p className="text-sm text-[var(--console-muted)]">
                  Brief unavailable while the review queue failed to load.
                </p>
              ) : (
                <p className="text-sm text-[var(--console-muted)]">
                  No visible queue item selected.
                </p>
              )}
            </div>
          }
          queue={
            <QueuePanel
              loadError={state.loadError}
              onSelect={(id) => dispatch({ type: "selected", payload: id })}
              rows={visibleQueue}
              selectedId={selectedItem?.event_id ?? null}
            />
          }
        />
      </div>
    </div>
  );
}
