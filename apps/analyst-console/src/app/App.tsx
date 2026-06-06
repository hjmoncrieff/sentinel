import { useEffect, useReducer } from "react";

import { GlobalRail } from "@/components/shell/global-rail";
import { TopOperationsBar } from "@/components/shell/top-operations-bar";
import { WorkspaceFrame } from "@/components/shell/workspace-frame";
import { ActionPanel } from "@/features/actions/action-panel";
import { AuditPanel } from "@/features/actions/audit-panel";
import { ReleasePanel } from "@/features/actions/release-panel";
import { BriefPanel } from "@/features/detail/brief-panel";
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
            <div className="grid min-h-full grid-rows-[auto_auto_minmax(0,1fr)]">
              <ActionPanel item={selectedItem} />
              <ReleasePanel item={selectedItem} />
              <AuditPanel item={selectedItem} />
            </div>
          }
          brief={<BriefPanel item={selectedItem} loadError={state.loadError} />}
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
