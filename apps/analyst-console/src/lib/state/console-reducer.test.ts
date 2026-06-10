import { describe, expect, it } from "vitest";

import { consoleReducer, initialConsoleState } from "./console-reducer";

describe("consoleReducer", () => {
  it("falls back to the first queue item when the current selection disappears", () => {
    const state = {
      ...initialConsoleState,
      selectedId: "evt-stale",
    };

    const nextState = consoleReducer(state, {
      type: "queueLoaded",
      payload: [
        {
          event_id: "evt-1",
          headline: "Alpha",
          review_priority: "high",
        },
      ],
    });

    expect(nextState.selectedId).toBe("evt-1");
    expect(nextState.loadError).toBeNull();
  });

  it("stores the loader error message", () => {
    const nextState = consoleReducer(initialConsoleState, {
      type: "loadFailed",
      payload: "Failed to load review queue: 503",
    });

    expect(nextState.loadError).toBe("Failed to load review queue: 503");
  });

  it("switches workspace focus when the left rail changes", () => {
    const nextState = consoleReducer(initialConsoleState, {
      type: "workspaceChanged",
      payload: "release",
    });

    expect(nextState.workspace).toBe("release");
  });

  it("switches the queue scope for queue-wide filtering", () => {
    const nextState = consoleReducer(initialConsoleState, {
      type: "queueScopeChanged",
      payload: "attention",
    });

    expect(nextState.queueScope).toBe("attention");
  });

  it("stores a targeted worklist lane independently from the queue scope", () => {
    const nextState = consoleReducer(initialConsoleState, {
      type: "worklistFilterChanged",
      payload: "publish-ready",
    });

    expect(nextState.worklistFilter).toBe("publish-ready");
    expect(nextState.queueScope).toBe("all");
  });

  it("prepends inserted manual queue items and selects them", () => {
    const nextState = consoleReducer(initialConsoleState, {
      type: "queueItemInserted",
      payload: {
        event_id: "manual-evt-1",
        headline: "Manual event",
        review_priority: "medium",
      },
    });

    expect(nextState.queue[0]?.event_id).toBe("manual-evt-1");
    expect(nextState.selectedId).toBe("manual-evt-1");
  });
});
