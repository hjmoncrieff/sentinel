import { useEffect, useReducer } from "react";

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
      .catch(() => undefined);

    return () => {
      active = false;
    };
  }, []);

  const visibleQueue = getVisibleQueue(state.queue, {
    search: state.search,
    priorityFilter: state.priorityFilter,
  });

  return (
    <div className="min-h-screen bg-[var(--console-bg)] text-[var(--console-ink)]">
      <header
        aria-label="SENTINEL Analyst Console"
        className="border-b border-white/10 px-4 py-3"
      >
        SENTINEL Analyst Console
      </header>
      <main aria-label="Analyst workspace" className="p-4">
        {visibleQueue.length} visible queue item(s)
      </main>
    </div>
  );
}
