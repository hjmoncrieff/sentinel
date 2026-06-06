export type ReviewPriority = "high" | "medium" | "low";

export type QueueRecommendedAction = {
  code?: string | null;
  priority?: ReviewPriority | null;
  reason?: string | null;
};

export type QueueQaFlag = {
  flag_id?: string | null;
  severity?: "high" | "medium" | "low" | string | null;
  code?: string | null;
  message?: string | null;
  details?: string | null;
};

export type QueueLinkedReport = {
  article_id?: string | null;
  report_role?: string | null;
  source_name?: string | null;
  url?: string | null;
  link_domain?: string | null;
  headline?: string | null;
  description?: string | null;
  article_date?: string | null;
};

export type QueueTimelineEntry = {
  stage?: string | null;
  label?: string | null;
  status?: string | null;
  at?: string | null;
};

export type QueueProvenance = {
  source_type?: string | null;
  linked_reports?: QueueLinkedReport[] | null;
  timeline?: QueueTimelineEntry[] | null;
};

export type QueueItem = {
  event_id: string;
  headline: string;
  country?: string | null;
  event_date?: string | null;
  event_type?: string | null;
  summary?: string | null;
  source_primary?: string | null;
  confidence?: string | null;
  review_status?: string | null;
  review_priority: ReviewPriority;
  publication_status?: "published" | "withheld" | "draft" | null;
  publication_label?: string | null;
  publication_reason?: string | null;
  salience?: "high" | "medium" | "low" | null;
  priority_score?: number | null;
  publication_ready?: boolean | null;
  reviewed_by_human?: boolean | null;
  merged_into_event_id?: string | null;
  qa_flag_count?: number | null;
  duplicate_candidate_count?: number | null;
  council_disagreement_summary?: string | null;
  council_recommended_actions?: QueueRecommendedAction[] | null;
  supervision_reasons?: string[] | null;
  qa_flags?: QueueQaFlag[] | null;
  ai_workers_in_scope?: string[] | null;
  provenance?: QueueProvenance | null;
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
