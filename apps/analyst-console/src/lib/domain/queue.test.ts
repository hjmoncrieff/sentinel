import { describe, expect, it } from "vitest";

import {
  deriveReviewPriority,
  getVisibleQueue,
  normalizeQueuePriority,
  queueItemNeedsAttention,
} from "./queue";
import type { QueueItem } from "./types";

const fixture = [
  {
    event_id: "evt-1",
    headline: "Alpha",
    review_priority: "high",
    country: "Colombia",
    event_type: "conflict",
    event_date: "2026-06-01",
    publication_status: "withheld",
    qa_flag_count: 2,
    priority_score: 11,
    publication_block_score: 0,
    disagreement_score: 0,
    registry_issue_count: 0,
    reviewed_by_human: false,
  },
  {
    event_id: "evt-2",
    headline: "Beta",
    review_priority: "low",
    country: "Mexico",
    event_type: "aid",
    event_date: "2026-06-02",
    publication_status: "published",
    priority_score: 7,
    reviewed_by_human: true,
  },
  {
    event_id: "evt-3",
    headline: "Gamma",
    review_priority: "high",
    country: "Peru",
    event_type: "conflict",
    event_date: "2026-06-03",
    publication_status: "withheld",
    priority_score: 12,
    qa_flag_count: 0,
    registry_issue_count: 0,
    disagreement_score: 0,
    publication_block_score: 0,
    reviewed_by_human: true,
  },
  {
    event_id: "evt-4",
    headline: "Delta",
    review_priority: "medium",
    country: "Brazil",
    event_type: "reform",
    event_date: "2026-06-04",
    publication_status: "withheld",
    priority_score: 9,
    reviewed_by_human: false,
    council_recommended_actions: [
      { code: "actor_follow_up", priority: "medium" },
    ],
    supervision_reasons: ["model_uncertainty"],
  },
] satisfies QueueItem[];

describe("getVisibleQueue", () => {
  it("filters queue rows by search and priority", () => {
    const rows = getVisibleQueue(fixture, {
      search: "colombia",
      priorityFilter: "high",
      queueScope: "all",
      worklistFilter: "all",
      countryFilter: "all",
      categoryFilter: "all",
      sortOrder: "priority",
    });

    expect(rows.map((row) => row.event_id)).toEqual(["evt-1"]);
  });

  it("keeps only attention items when the attention scope is active", () => {
    const rows = getVisibleQueue(fixture, {
      search: "",
      priorityFilter: "all",
      queueScope: "attention",
      worklistFilter: "all",
      countryFilter: "all",
      categoryFilter: "all",
      sortOrder: "priority",
    });

    expect(rows.map((row) => row.event_id)).toEqual(["evt-1"]);
  });

  it("filters queue rows by country and category", () => {
    const rows = getVisibleQueue(fixture, {
      search: "",
      priorityFilter: "all",
      queueScope: "all",
      worklistFilter: "all",
      countryFilter: "Mexico",
      categoryFilter: "aid",
      sortOrder: "priority",
    });

    expect(rows.map((row) => row.event_id)).toEqual(["evt-2"]);
  });

  it("sorts queue rows by most recent event date when requested", () => {
    const rows = getVisibleQueue(fixture, {
      search: "",
      priorityFilter: "all",
      queueScope: "all",
      worklistFilter: "all",
      countryFilter: "all",
      categoryFilter: "all",
      sortOrder: "most-recent",
    });

    expect(rows.map((row) => row.event_id)).toEqual(["evt-4", "evt-3", "evt-2", "evt-1"]);
  });

  it("sorts equally ranked queue rows by priority score before recency", () => {
    const rows = getVisibleQueue(fixture.map(normalizeQueuePriority), {
      search: "",
      priorityFilter: "all",
      queueScope: "all",
      worklistFilter: "all",
      countryFilter: "all",
      categoryFilter: "all",
      sortOrder: "priority",
    });

    expect(rows.map((row) => row.event_id)).toEqual(["evt-1", "evt-3", "evt-4", "evt-2"]);
  });
});

describe("queueItemNeedsAttention", () => {
  it("treats blockers as attention-worthy but not every unreviewed row", () => {
    expect(queueItemNeedsAttention(fixture[0])).toBe(true);
    expect(queueItemNeedsAttention(fixture[1])).toBe(false);
    expect(queueItemNeedsAttention(fixture[3])).toBe(false);
  });

  it("treats unreviewed high-priority rows as attention-worthy", () => {
    expect(
      queueItemNeedsAttention({
        ...fixture[2],
        review_priority: "high",
        reviewed_by_human: false,
      }),
    ).toBe(true);
  });

  it("supports targeted publish-ready and corroboration worklists", () => {
    const rows = getVisibleQueue(
      [
        ...fixture,
        {
          event_id: "evt-5",
          headline: "Epsilon",
          review_priority: "medium",
          country: "Chile",
          event_type: "reform",
          event_date: "2026-06-05",
          publication_status: "draft",
          reviewed_by_human: true,
          source_primary: "AP",
          qa_flag_count: 0,
          duplicate_candidate_count: 0,
          registry_issue_count: 0,
          publication_block_score: 0,
          disagreement_score: 0,
        },
      ],
      {
        search: "",
        priorityFilter: "all",
        queueScope: "all",
        worklistFilter: "publish-ready",
        countryFilter: "all",
        categoryFilter: "all",
        sortOrder: "priority",
      },
    );

    expect(rows.map((row) => row.event_id)).toEqual(["evt-3", "evt-5"]);

    const corroborationRows = getVisibleQueue(fixture, {
      search: "",
      priorityFilter: "all",
      queueScope: "all",
      worklistFilter: "corroborate",
      countryFilter: "all",
      categoryFilter: "all",
      sortOrder: "priority",
    });

    expect(corroborationRows.map((row) => row.event_id)).toEqual(["evt-4"]);
  });
});

describe("deriveReviewPriority", () => {
  it("keeps high priority scarce and tied to blockers or extreme scores", () => {
    expect(deriveReviewPriority(fixture[0])).toBe("high");
    expect(deriveReviewPriority(fixture[2])).toBe("medium");
    expect(deriveReviewPriority(fixture[1])).toBe("low");
  });

  it("normalizes stale queue rows with inflated high-priority labels", () => {
    expect(normalizeQueuePriority(fixture[2]).review_priority).toBe("medium");
  });
});
