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
});
