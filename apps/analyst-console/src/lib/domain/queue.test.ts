import { describe, expect, it } from "vitest";

import { getVisibleQueue } from "./queue";

const fixture = [
  {
    event_id: "evt-1",
    headline: "Alpha",
    review_priority: "high",
    country: "Colombia",
    publication_status: "withheld",
  },
  {
    event_id: "evt-2",
    headline: "Beta",
    review_priority: "low",
    country: "Mexico",
    publication_status: "published",
  },
];

describe("getVisibleQueue", () => {
  it("filters queue rows by search and priority", () => {
    const rows = getVisibleQueue(fixture as never[], {
      search: "colombia",
      priorityFilter: "high",
    });

    expect(rows.map((row) => row.event_id)).toEqual(["evt-1"]);
  });
});
