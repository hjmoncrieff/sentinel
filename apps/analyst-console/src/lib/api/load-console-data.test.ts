import { afterEach, describe, expect, it, vi } from "vitest";

import { loadConsoleData } from "./load-console-data";

const fetchMock = vi.fn<typeof fetch>();

describe("loadConsoleData", () => {
  afterEach(() => {
    fetchMock.mockReset();
    vi.unstubAllGlobals();
  });

  it("unwraps queue items from the review snapshot envelope", async () => {
    fetchMock.mockResolvedValue({
      ok: true,
      json: async () => ({
        items: [
          {
            event_id: "evt-1",
            headline: "Alpha",
            review_priority: "high",
          },
        ],
      }),
    } as Response);
    vi.stubGlobal("fetch", fetchMock);

    const rows = await loadConsoleData();

    expect(rows).toEqual([
      {
        event_id: "evt-1",
        headline: "Alpha",
        review_priority: "high",
      },
    ]);
    expect(fetchMock).toHaveBeenCalledWith("/data/review/review_queue.json");
  });

  it("throws when the review queue response is not ok", async () => {
    fetchMock.mockResolvedValue({
      ok: false,
      status: 503,
    } as Response);
    vi.stubGlobal("fetch", fetchMock);

    await expect(loadConsoleData()).rejects.toThrow(
      "Failed to load review queue: 503",
    );
  });
});
