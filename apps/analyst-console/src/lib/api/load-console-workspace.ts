import type {
  ConsoleWorkspaceData,
  CouncilAnalysisEvent,
  CountryMonitorRecord,
  ManualEventSubmission,
  QueueItem,
  RegistryActor,
  SessionProfile,
} from "@/lib/domain/types";
import { normalizeQueuePriority } from "@/lib/domain/queue";
import { supabase } from "@/lib/supabase/client";

const SNAPSHOT_KEYS = [
  "review_queue",
  "council_analyses",
  "country_dossiers",
  "country_monitors",
  "actor_registry",
] as const;
const LOCAL_WORKSPACE_PATHS = {
  reviewQueue: [
    "/data/review/review_queue.json",
    "../../data/review/review_queue.json",
  ],
  council: [
    "/data/review/council_analyses.json",
    "../../data/review/council_analyses.json",
  ],
  countries: [
    "/data/published/country_dossiers.json",
    "../../data/published/country_dossiers.json",
  ],
  countryMonitors: [
    "/data/published/country_monitors.json",
    "../../data/published/country_monitors.json",
  ],
  registry: [
    "/config/actors/actor_registry.json",
    "../../config/actors/actor_registry.json",
  ],
} as const;

type SnapshotRow = {
  snapshot_key: (typeof SNAPSHOT_KEYS)[number];
  payload: unknown;
};

type ManualEventRow = ManualEventSubmission;

type ReviewQueueEnvelope = {
  items?: QueueItem[];
};

type CouncilEnvelope = {
  events?: CouncilAnalysisEvent[];
};

type CountryEnvelope = {
  countries?: CountryMonitorRecord[];
};

type RegistryEnvelope = {
  actors?: RegistryActor[];
};

async function fetchLocalJson<T>(paths: readonly string[], fallback: T): Promise<T> {
  for (const path of paths) {
    try {
      const response = await fetch(path);
      if (!response.ok) {
        continue;
      }

      return (await response.json()) as T;
    } catch {
      continue;
    }
  }

  return fallback;
}

function mapCouncil(events: CouncilAnalysisEvent[]): Record<string, CouncilAnalysisEvent> {
  return Object.fromEntries(
    events
      .filter((row) => row?.event_id)
      .map((row) => [row.event_id, row]),
  );
}

function mapCountries(
  countries: CountryMonitorRecord[],
): Record<string, CountryMonitorRecord> {
  return Object.fromEntries(
    countries
      .filter((row) => row?.country)
      .map((row) => [String(row.country).toLowerCase(), row]),
  );
}

function extractQueue(payload: unknown): QueueItem[] {
  if (Array.isArray(payload)) {
    return (payload as QueueItem[]).map(normalizeQueuePriority);
  }

  const envelope = payload as ReviewQueueEnvelope | null;
  return Array.isArray(envelope?.items)
    ? envelope.items.map(normalizeQueuePriority)
    : [];
}

function extractCouncil(payload: unknown): CouncilAnalysisEvent[] {
  const envelope = payload as CouncilEnvelope | null;
  return Array.isArray(envelope?.events) ? envelope.events : [];
}

function extractCountries(payload: unknown): CountryMonitorRecord[] {
  const envelope = payload as CountryEnvelope | null;
  return Array.isArray(envelope?.countries) ? envelope.countries : [];
}

function mergeCountries(
  dossierCountries: CountryMonitorRecord[],
  monitorCountries: CountryMonitorRecord[],
): CountryMonitorRecord[] {
  const merged = new Map<string, CountryMonitorRecord>();

  const mergeRow = (row: CountryMonitorRecord) => {
    if (!row?.country) {
      return;
    }

    const key = String(row.country).toLowerCase();
    const existing = merged.get(key);
    const next: CountryMonitorRecord = {
      ...existing,
      ...row,
      country: row.country ?? existing?.country ?? key,
      predictive_summary:
        row.predictive_summary ??
        row.public_summary ??
        existing?.predictive_summary ??
        existing?.public_summary ??
        null,
      public_summary:
        row.public_summary ?? existing?.public_summary ?? row.predictive_summary ?? null,
      public_structural_cards:
        row.public_structural_cards ?? existing?.public_structural_cards ?? null,
      public_construct_series:
        row.public_construct_series ?? existing?.public_construct_series ?? null,
      public_context:
        row.public_context ?? existing?.public_context ?? null,
      public_freshness:
        row.public_freshness ?? existing?.public_freshness ?? null,
      monitors: row.monitors ?? existing?.monitors ?? null,
      risk_constructs: row.risk_constructs ?? existing?.risk_constructs ?? null,
    };

    merged.set(key, next);
  };

  dossierCountries.forEach(mergeRow);
  monitorCountries.forEach(mergeRow);

  return [...merged.values()];
}

function extractRegistry(payload: unknown): RegistryActor[] {
  const envelope = payload as RegistryEnvelope | null;
  return Array.isArray(envelope?.actors) ? envelope.actors : [];
}

function mapManualSubmissionToQueueItem(
  row: ManualEventRow,
): QueueItem {
  const eventId = `manual-${row.submission_id.slice(0, 12)}`;

  return {
    event_id: eventId,
    headline: row.headline,
    country: row.country ?? "Regional",
    event_date: row.event_date ?? row.created_at?.slice(0, 10) ?? null,
    event_type: row.event_type ?? "other",
    summary: row.summary ?? "Manual event submission awaiting review.",
    source_primary: row.source_primary ?? "Manual submission",
    confidence:
      row.confidence === "high" || row.confidence === "low"
        ? row.confidence
        : "medium",
    review_status: row.status ?? "manual_submitted",
    review_priority:
      row.review_priority === "high" || row.review_priority === "low"
        ? row.review_priority
        : "medium",
    publication_status: "withheld",
    publication_label: "Manual submission",
    publication_reason: "manual_event_submission",
    salience:
      row.salience === "high" || row.salience === "low"
        ? row.salience
        : "medium",
    publication_ready: false,
    reviewed_by_human: false,
    qa_flag_count: 0,
    duplicate_candidate_count: 0,
    registry_issue_count: 0,
    supervision_reasons: ["manual_submission"],
    provenance: {
      source_type: "manual_submission",
      linked_reports: [],
      timeline: [
        {
          stage: "manual_submission",
          label: `Submitted by ${row.editor_name ?? "Analyst"}`,
          status: row.status ?? "manual_submitted",
          at: row.created_at ?? null,
        },
      ],
    },
  };
}

async function loadLocalWorkspace(): Promise<ConsoleWorkspaceData> {
  const [queuePayload, councilPayload, countryPayload, countryMonitorPayload, registryPayload] =
    await Promise.all([
      fetchLocalJson<ReviewQueueEnvelope | QueueItem[]>(
        LOCAL_WORKSPACE_PATHS.reviewQueue,
        { items: [] },
      ),
      fetchLocalJson<CouncilEnvelope>(LOCAL_WORKSPACE_PATHS.council, {
        events: [],
      }),
      fetchLocalJson<CountryEnvelope>(LOCAL_WORKSPACE_PATHS.countries, {
        countries: [],
      }),
      fetchLocalJson<CountryEnvelope>(LOCAL_WORKSPACE_PATHS.countryMonitors, {
        countries: [],
      }),
      fetchLocalJson<RegistryEnvelope>(LOCAL_WORKSPACE_PATHS.registry, {
        actors: [],
      }),
    ]);

  const queue = extractQueue(queuePayload);
  const councilEvents = extractCouncil(councilPayload);
  const countries = mergeCountries(
    extractCountries(countryPayload),
    extractCountries(countryMonitorPayload),
  );
  const registryActors = extractRegistry(registryPayload);

  return {
    queue,
    councilByEvent: mapCouncil(councilEvents),
    countriesByName: mapCountries(countries),
    registryActors,
    source: "local",
  };
}

async function loadSupabaseWorkspace(): Promise<ConsoleWorkspaceData> {
  const [{ data, error }, { data: manualRows, error: manualError }] = await Promise.all([
    supabase
      .from("console_snapshots")
      .select("snapshot_key,payload")
      .in("snapshot_key", [...SNAPSHOT_KEYS]),
    supabase
      .from("manual_event_submissions")
      .select(
        "submission_id,headline,country,event_date,event_type,summary,source_primary,confidence,salience,review_priority,location,status,editor_name,editor_role,created_at",
      )
      .order("created_at", { ascending: false })
      .limit(50),
  ]);

  if (error) {
    throw error;
  }
  if (manualError) {
    throw manualError;
  }

  const rows = (data ?? []) as SnapshotRow[];
  const snapshots = new Map(rows.map((row) => [row.snapshot_key, row.payload]));

  const queue = extractQueue(snapshots.get("review_queue"));
  const manualQueue = ((manualRows ?? []) as ManualEventRow[]).map(
    mapManualSubmissionToQueueItem,
  );
  const councilEvents = extractCouncil(snapshots.get("council_analyses"));
  const countries = mergeCountries(
    extractCountries(snapshots.get("country_dossiers")),
    extractCountries(snapshots.get("country_monitors")),
  );
  const registryActors = extractRegistry(snapshots.get("actor_registry"));

  return {
    queue: [...manualQueue, ...queue],
    councilByEvent: mapCouncil(councilEvents),
    countriesByName: mapCountries(countries),
    registryActors,
    source: "supabase",
  };
}

export async function loadConsoleWorkspace(
  profile: SessionProfile | null,
): Promise<ConsoleWorkspaceData> {
  if (profile) {
    try {
      return await loadSupabaseWorkspace();
    } catch {
      return loadLocalWorkspace();
    }
  }

  return loadLocalWorkspace();
}
