import type {
  QueueItem,
  QueueScope,
  QueueSort,
  QueueWorklist,
  ReviewPriority,
} from "./types";

type QueueFilters = {
  search: string;
  priorityFilter: "all" | ReviewPriority;
  queueScope: QueueScope;
  worklistFilter: QueueWorklist;
  countryFilter: string;
  categoryFilter: string;
  sortOrder: QueueSort;
};

const PRIORITY_RANK: Record<ReviewPriority, number> = {
  high: 0,
  medium: 1,
  low: 2,
};

function hasPriorityBlocker(row: QueueItem): boolean {
  return (
    (row.publication_block_score ?? 0) >= 3 ||
    (row.disagreement_score ?? 0) >= 4 ||
    (row.qa_flag_count ?? 0) >= 2 ||
    (row.registry_issue_count ?? 0) >= 2
  );
}

export function deriveReviewPriority(row: QueueItem): ReviewPriority {
  const score = row.priority_score ?? 0;

  if (score >= 13 || (score >= 11 && hasPriorityBlocker(row))) {
    return "high";
  }

  if (score >= 8) {
    return "medium";
  }

  return "low";
}

export function normalizeQueuePriority(row: QueueItem): QueueItem {
  if (row.priority_score == null) {
    return row;
  }

  const reviewPriority = deriveReviewPriority(row);

  if (row.review_priority === reviewPriority) {
    return row;
  }

  return {
    ...row,
    review_priority: reviewPriority,
  };
}

function parseDateValue(value?: string | null): number {
  if (!value) {
    return Number.NEGATIVE_INFINITY;
  }

  const time = Date.parse(value);
  return Number.isNaN(time) ? Number.NEGATIVE_INFINITY : time;
}

function compareMostRecent(a: QueueItem, b: QueueItem): number {
  return parseDateValue(b.event_date) - parseDateValue(a.event_date);
}

function comparePriority(a: QueueItem, b: QueueItem): number {
  const rankDelta = PRIORITY_RANK[a.review_priority] - PRIORITY_RANK[b.review_priority];

  if (rankDelta !== 0) {
    return rankDelta;
  }

  const scoreDelta = (b.priority_score ?? 0) - (a.priority_score ?? 0);

  if (scoreDelta !== 0) {
    return scoreDelta;
  }

  return compareMostRecent(a, b);
}

function hasReleaseBlockers(row: QueueItem): boolean {
  return (
    (row.qa_flag_count ?? 0) > 0 ||
    (row.duplicate_candidate_count ?? 0) > 0 ||
    (row.registry_issue_count ?? 0) > 0 ||
    (row.publication_block_score ?? 0) >= 3 ||
    (row.disagreement_score ?? 0) >= 4
  );
}

export function queueItemNeedsAttention(row: QueueItem): boolean {
  if (row.review_status === "needs_revision" || row.review_status === "flagged") {
    return true;
  }

  if ((row.qa_flag_count ?? 0) > 0) {
    return true;
  }

  if ((row.duplicate_candidate_count ?? 0) > 0) {
    return true;
  }

  if ((row.registry_issue_count ?? 0) > 0) {
    return true;
  }

  if ((row.publication_block_score ?? 0) >= 3) {
    return true;
  }

  if ((row.disagreement_score ?? 0) >= 4) {
    return true;
  }

  if (row.review_priority === "high" && row.reviewed_by_human === false) {
    return true;
  }

  return false;
}

export function queueItemMatchesWorklist(
  row: QueueItem,
  worklist: QueueWorklist,
): boolean {
  switch (worklist) {
    case "review-now":
      return queueItemNeedsAttention(row);
    case "publish-ready":
      return (
        row.publication_status !== "published" &&
        row.reviewed_by_human === true &&
        !hasReleaseBlockers(row)
      );
    case "corroborate":
      return (
        (row.publication_block_score ?? 0) >= 3 ||
        (row.uncertainty_score ?? 0) >= 3 ||
        (row.council_recommended_actions ?? []).some(
          (action) =>
            action.code === "human_corroboration" ||
            action.code === "actor_follow_up",
        )
      );
    case "registry":
      return (row.registry_issue_count ?? 0) > 0;
    case "duplicates":
      return (row.duplicate_candidate_count ?? 0) > 0;
    case "all":
    default:
      return true;
  }
}

export function getQueueHealth(rows: QueueItem[]): Record<
  "reviewNow" | "publishReady" | "corroborate" | "registry" | "duplicates",
  number
> {
  return {
    reviewNow: rows.filter((row) => queueItemNeedsAttention(row)).length,
    publishReady: rows.filter((row) =>
      queueItemMatchesWorklist(row, "publish-ready"),
    ).length,
    corroborate: rows.filter((row) =>
      queueItemMatchesWorklist(row, "corroborate"),
    ).length,
    registry: rows.filter((row) => queueItemMatchesWorklist(row, "registry")).length,
    duplicates: rows.filter((row) =>
      queueItemMatchesWorklist(row, "duplicates"),
    ).length,
  };
}

export function getVisibleQueue(
  rows: QueueItem[],
  filters: QueueFilters,
): QueueItem[] {
  const search = filters.search.trim().toLowerCase();
  const countryFilter = filters.countryFilter.trim().toLowerCase();
  const categoryFilter = filters.categoryFilter.trim().toLowerCase();

  const filtered = rows.filter((row) => {
    const searchMatch =
      search.length === 0 ||
      row.headline.toLowerCase().includes(search) ||
      (row.country ?? "").toLowerCase().includes(search) ||
      row.event_id.toLowerCase().includes(search);
    const priorityMatch =
      filters.priorityFilter === "all" ||
      row.review_priority === filters.priorityFilter;
    const scopeMatch =
      filters.queueScope === "all" || queueItemNeedsAttention(row);
    const worklistMatch = queueItemMatchesWorklist(row, filters.worklistFilter);
    const countryMatch =
      countryFilter.length === 0 ||
      countryFilter === "all" ||
      (row.country ?? "").toLowerCase() === countryFilter;
    const categoryMatch =
      categoryFilter.length === 0 ||
      categoryFilter === "all" ||
      (row.event_type ?? "").toLowerCase() === categoryFilter;

    return (
      searchMatch &&
      priorityMatch &&
      scopeMatch &&
      worklistMatch &&
      countryMatch &&
      categoryMatch
    );
  });

  const sorted = [...filtered];
  sorted.sort(
    filters.sortOrder === "most-recent" ? compareMostRecent : comparePriority,
  );

  return sorted;
}
