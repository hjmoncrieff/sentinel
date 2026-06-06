export type ReviewPriority = "high" | "medium" | "low";

export type QueueItem = {
  event_id: string;
  headline: string;
  country?: string | null;
  event_date?: string | null;
  event_type?: string | null;
  confidence?: string | null;
  review_status?: string | null;
  review_priority: ReviewPriority;
  publication_status?: "published" | "withheld" | "draft" | null;
  publication_label?: string | null;
  salience?: "high" | "medium" | "low" | null;
  priority_score?: number | null;
  publication_ready?: boolean | null;
  merged_into_event_id?: string | null;
  qa_flag_count?: number | null;
  duplicate_candidate_count?: number | null;
};

export type ConsoleState = {
  queue: QueueItem[];
  selectedId: string | null;
  search: string;
  priorityFilter: "all" | ReviewPriority;
  middleTab: "briefing" | "ai-analysis" | "actors";
  rightTab: "action" | "release" | "audit";
  loadError: string | null;
};
