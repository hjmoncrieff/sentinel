import type { QueueItem, ReviewPriority } from "./types";

type QueueFilters = {
  search: string;
  priorityFilter: "all" | ReviewPriority;
};

export function getVisibleQueue(
  rows: QueueItem[],
  filters: QueueFilters,
): QueueItem[] {
  const search = filters.search.trim().toLowerCase();

  return rows.filter((row) => {
    const searchMatch =
      search.length === 0 ||
      row.headline.toLowerCase().includes(search) ||
      (row.country ?? "").toLowerCase().includes(search) ||
      row.event_id.toLowerCase().includes(search);
    const priorityMatch =
      filters.priorityFilter === "all" ||
      row.review_priority === filters.priorityFilter;

    return searchMatch && priorityMatch;
  });
}
