export type ReviewPriority = "high" | "medium" | "low";
export type AppRole = "ra" | "analyst" | "coordinator" | "admin";
export type NotificationRecipientRole = "ra" | "analyst" | "admin";
export type InviteRole = "ra" | "analyst" | "admin";
export type QueueScope = "all" | "attention";
export type QueueWorklist =
  | "all"
  | "review-now"
  | "publish-ready"
  | "corroborate"
  | "registry"
  | "duplicates";
export type QueueSort = "priority" | "most-recent";
export type ConsoleWorkspace = "review" | "release" | "audit" | "registry";
export type CenterPanelTab = "briefing" | "ai-analysis" | "country-brief" | "data";

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

export type ManualEventSubmission = {
  submission_id: string;
  headline: string;
  country?: string | null;
  event_date?: string | null;
  event_type?: string | null;
  summary?: string | null;
  source_primary?: string | null;
  confidence?: "high" | "medium" | "low" | string | null;
  salience?: "high" | "medium" | "low" | string | null;
  review_priority?: ReviewPriority | null;
  location?: string | null;
  status?: string | null;
  editor_name?: string | null;
  editor_role?: string | null;
  created_at?: string | null;
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

export type EventEditRecord = {
  edit_id?: string | null;
  event_id: string;
  editor_name?: string | null;
  editor_role?: string | null;
  edited_at?: string | null;
  status?: string | null;
  comment?: string | null;
  patch?: Record<string, unknown> | null;
  actor_patches?: unknown[] | null;
};

export type RegistryEditRecord = {
  registry_edit_id?: string | null;
  action?: string | null;
  payload?: Record<string, unknown> | null;
  editor_name?: string | null;
  editor_role?: string | null;
  created_at?: string | null;
};

export type ConsoleNotificationRecord = {
  notification_id?: string | null;
  event_id?: string | null;
  recipient_role: NotificationRecipientRole;
  subject: string;
  message: string;
  sender_name?: string | null;
  sender_role?: string | null;
  created_at?: string | null;
  read_at?: string | null;
  metadata?: Record<string, unknown> | null;
};

export type ConsoleUserInviteRecord = {
  invite_id?: string | null;
  invited_user_id?: string | null;
  invited_email: string;
  invited_display_name?: string | null;
  invited_role: InviteRole;
  inviter_name?: string | null;
  inviter_role?: string | null;
  status?: string | null;
  redirect_to?: string | null;
  invited_at?: string | null;
  last_sent_at?: string | null;
  accepted_at?: string | null;
  metadata?: Record<string, unknown> | null;
};

export type CouncilLens = {
  lens?: string | null;
  assessment?: string | null;
  risk_level?: string | null;
  confidence?: number | null;
  public_analysis?: string | null;
  public_takeaways?: Record<string, string | null> | null;
};

export type CouncilAnalysisEvent = {
  event_id: string;
  event_date?: string | null;
  country?: string | null;
  event_type?: string | null;
  generated_at?: string | null;
  analyses?: Record<string, CouncilLens> | null;
  event_context?: Record<string, unknown> | null;
  recommended_review_actions?: QueueRecommendedAction[] | null;
};

export type CountryMonitorComponent = {
  code?: string | null;
  label?: string | null;
  score?: number | null;
  weighted_contribution?: number | null;
  trend_label?: string | null;
};

export type CountryMonitorEntry = {
  code?: string | null;
  label?: string | null;
  goal?: string | null;
  composite_score?: number | null;
  pulse_score?: number | null;
  trend_label?: string | null;
  dominant_recent_signal?: string | null;
  summary_text?: string | null;
  watchpoints?: string[] | null;
  drivers?: CountryMonitorComponent[] | null;
};

export type CountryRiskConstruct = {
  code?: string | null;
  label?: string | null;
  goal?: string | null;
  score?: number | null;
  level?: string | null;
  trend_label?: string | null;
  summary_text?: string | null;
  watchpoints?: string[] | null;
  drivers?: CountryMonitorComponent[] | null;
};

export type CountryPredictiveSummary = {
  overall_risk_score?: number | null;
  overall_risk_level?: string | null;
  leading_construct?: string | null;
  leading_label?: string | null;
  leading_trend?: string | null;
  regime_vulnerability_score?: number | null;
  summary_text?: string | null;
  watchpoints?: string[] | null;
  raw_overall_risk_score?: number | null;
};

export type CountryStructuralCard = {
  code?: string | null;
  label?: string | null;
  current_value?: number | null;
  display_value?: string | null;
  unit?: string | null;
  as_of_year?: number | null;
  trend_series?: number[] | null;
};

export type CountryConstructSeriesEntry = {
  code?: string | null;
  label?: string | null;
};

export type CountryPredictiveSeriesEntry = {
  code?: string | null;
  label?: string | null;
  current_score?: number | null;
  display_score?: string | null;
  level?: string | null;
  trend_label?: string | null;
  as_of_year?: number | null;
  trend_series?: Array<{
    year?: number | null;
    score?: number | null;
  }> | null;
};

export type CountryPublicContext = {
  capital?: string | null;
  regime?: string | null;
  cmr_status?: string | null;
  cmr_class?: string | null;
  note?: string | null;
  key_positions?: Array<{
    title?: string | null;
    name?: string | null;
  }> | null;
  next_election?: {
    date?: string | null;
    type?: string | null;
    note?: string | null;
  } | null;
  country_watch?: string | null;
  special_profile_id?: string | null;
};

export type CountryMonitorRecord = {
  country: string;
  iso2?: string | null;
  iso3?: string | null;
  subregion?: string | null;
  generated_at?: string | null;
  monitors?: CountryMonitorEntry[] | null;
  risk_constructs?: CountryRiskConstruct[] | null;
  predictive_summary?: CountryPredictiveSummary | null;
  public_freshness?: {
    structural_as_of_year?: number | null;
    events_as_of_date?: string | null;
    monitor_generated_at?: string | null;
    series_coverage_note?: string | null;
  } | null;
  public_summary?: CountryPredictiveSummary | null;
  public_structural_cards?: CountryStructuralCard[] | null;
  public_construct_series?: CountryConstructSeriesEntry[] | null;
  public_predictive_series?: CountryPredictiveSeriesEntry[] | null;
  public_context?: CountryPublicContext | null;
};

export type RegistryActor = {
  registry_id: string;
  canonical_name?: string | null;
  canonical_category?: string | null;
  canonical_group?: string | null;
  canonical_type?: string | null;
  canonical_subtype?: string | null;
  primary_country?: string | null;
  aliases?: string[] | null;
  relationship_tags?: string[] | null;
  registry_status?: string | null;
  source_confidence?: string | null;
  evidence?: string[] | null;
};

export type SessionProfile = {
  id: string;
  email?: string | null;
  display_name?: string | null;
  role: AppRole;
  active: boolean;
};

export type SessionState = {
  busy: boolean;
  error: string | null;
  profile: SessionProfile | null;
};

export type ConsoleWorkspaceData = {
  queue: QueueItem[];
  councilByEvent: Record<string, CouncilAnalysisEvent>;
  countriesByName: Record<string, CountryMonitorRecord>;
  registryActors: RegistryActor[];
  source: "supabase" | "local";
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
  uncertainty_score?: number | null;
  disagreement_score?: number | null;
  human_review_gap_score?: number | null;
  publication_block_score?: number | null;
  action_score?: number | null;
  publication_ready?: boolean | null;
  reviewed_by_human?: boolean | null;
  merged_into_event_id?: string | null;
  qa_flag_count?: number | null;
  duplicate_candidate_count?: number | null;
  registry_issue_count?: number | null;
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
  queueScope: QueueScope;
  worklistFilter: QueueWorklist;
  countryFilter: string;
  categoryFilter: string;
  sortOrder: QueueSort;
  workspace: ConsoleWorkspace;
  middleTab: CenterPanelTab;
  loadError: string | null;
};
