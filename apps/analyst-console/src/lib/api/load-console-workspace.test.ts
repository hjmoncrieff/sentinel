import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { loadConsoleWorkspace } from "./load-console-workspace";

const {
  fromMock,
  snapshotsInMock,
  manualLimitMock,
  manualOrderMock,
  snapshotsSelectMock,
  manualSelectMock,
} = vi.hoisted(() => ({
  fromMock: vi.fn(),
  snapshotsInMock: vi.fn(),
  manualLimitMock: vi.fn(),
  manualOrderMock: vi.fn(),
  snapshotsSelectMock: vi.fn(),
  manualSelectMock: vi.fn(),
}));

const fetchMock = vi.fn<typeof fetch>();

vi.mock("@/lib/supabase/client", () => ({
  supabase: {
    from: fromMock,
  },
}));

describe("loadConsoleWorkspace", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", fetchMock);
    fetchMock.mockReset();
    fromMock.mockReset();
    snapshotsInMock.mockReset();
    manualLimitMock.mockReset();
    manualOrderMock.mockClear();
    snapshotsSelectMock.mockClear();
    manualSelectMock.mockClear();
    snapshotsSelectMock.mockImplementation(() => ({ in: snapshotsInMock }));
    manualSelectMock.mockImplementation(() => ({ order: manualOrderMock }));
    manualOrderMock.mockImplementation(() => ({ limit: manualLimitMock }));

    fromMock.mockImplementation((table: string) => {
      if (table === "console_snapshots") {
        return { select: snapshotsSelectMock };
      }

      if (table === "manual_event_submissions") {
        return { select: manualSelectMock };
      }

      throw new Error(`Unexpected table: ${table}`);
    });

    snapshotsInMock.mockResolvedValue({ data: [], error: null });
    manualLimitMock.mockResolvedValue({ data: [], error: null });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("falls back to the relative review artifact path when root paths are unavailable", async () => {
    fetchMock.mockImplementation(async (input) => {
      if (input === "../../data/review/review_queue.json") {
        return {
          ok: true,
          json: async () => ({
            items: [
              {
                event_id: "evt-relative",
                headline: "Relative path queue row",
                review_priority: "high",
              },
            ],
          }),
        } as Response;
      }

      return { ok: false } as Response;
    });

    const workspace = await loadConsoleWorkspace(null);

    const requestedPaths = fetchMock.mock.calls.map((call) => call[0]);

    expect(requestedPaths).toContain("/data/review/review_queue.json");
    expect(requestedPaths).toContain("../../data/review/review_queue.json");
    expect(workspace.queue).toHaveLength(1);
    expect(workspace.queue[0]?.event_id).toBe("evt-relative");
    expect(workspace.source).toBe("local");
  });

  it("loads country dossiers as the shared country base layer", async () => {
    fetchMock.mockImplementation(async (input) => {
      if (input === "/data/review/review_queue.json") {
        return { ok: true, json: async () => ({ items: [] }) } as Response;
      }
      if (input === "/data/review/council_analyses.json") {
        return { ok: true, json: async () => ({ events: [] }) } as Response;
      }
      if (input === "/data/published/country_dossiers.json") {
        return {
          ok: true,
          json: async () => ({
            countries: [
              {
                country: "Brazil",
                iso2: "BR",
                iso3: "BRA",
                subregion: "Brazil",
                generated_at: "2026-06-06T00:00:00Z",
                public_summary: {
                  overall_risk_score: 48.1,
                  overall_risk_level: "guarded",
                  leading_label: "Regime Vulnerability",
                },
                public_predictive_series: [
                  {
                    code: "regime_vulnerability",
                    label: "Regime Vulnerability",
                    current_score: 48.1,
                    display_score: "48.1/100",
                    level: "guarded",
                    trend_label: "stable",
                    as_of_year: 2025,
                    trend_series: [
                      { year: 2024, score: 44.2 },
                      { year: 2025, score: 48.1 },
                    ],
                  },
                ],
                public_structural_cards: [
                  {
                    code: "polyarchy",
                    label: "Polyarchy",
                    display_value: "0.57",
                  },
                ],
                public_construct_series: [],
                public_context: {
                  country_watch: "Watch Brazil's command balance.",
                },
              },
            ],
          }),
        } as Response;
      }
      if (input === "/data/published/country_monitors.json") {
        return { ok: true, json: async () => ({ countries: [] }) } as Response;
      }
      if (input === "/config/actors/actor_registry.json") {
        return { ok: true, json: async () => ({ actors: [] }) } as Response;
      }

      return { ok: false } as Response;
    });

    const workspace = await loadConsoleWorkspace(null);

    expect(workspace.countriesByName.brazil?.public_summary?.overall_risk_score).toBe(48.1);
    expect(workspace.countriesByName.brazil?.predictive_summary?.overall_risk_level).toBe("guarded");
    expect(workspace.countriesByName.brazil?.public_predictive_series?.[0]?.code).toBe("regime_vulnerability");
    expect(workspace.countriesByName.brazil?.public_structural_cards?.[0]?.code).toBe("polyarchy");
  });

  it("uses Supabase snapshots and manual event submissions for authenticated users", async () => {
    snapshotsInMock.mockResolvedValue({
      data: [
        {
          snapshot_key: "review_queue",
          payload: {
            items: [
              {
                event_id: "evt-supabase",
                headline: "Supabase queue row",
                review_priority: "high",
                priority_score: 12,
                qa_flag_count: 0,
                registry_issue_count: 0,
                disagreement_score: 0,
                publication_block_score: 0,
              },
            ],
          },
        },
        {
          snapshot_key: "council_analyses",
          payload: { events: [] },
        },
        {
          snapshot_key: "country_dossiers",
          payload: { countries: [] },
        },
        {
          snapshot_key: "country_monitors",
          payload: { countries: [] },
        },
        {
          snapshot_key: "actor_registry",
          payload: { actors: [] },
        },
      ],
      error: null,
    });

    manualLimitMock.mockResolvedValue({
      data: [
        {
          submission_id: "manual-submission-1",
          headline: "Manual event row",
          review_priority: "high",
          editor_name: "Analyst One",
          created_at: "2026-06-05T13:00:00Z",
        },
      ],
      error: null,
    });

    const workspace = await loadConsoleWorkspace({
      id: "user-1",
      role: "analyst",
      active: true,
    });

    expect(snapshotsSelectMock).toHaveBeenCalledWith("snapshot_key,payload");
    expect(snapshotsInMock).toHaveBeenCalledOnce();
    expect(manualSelectMock).toHaveBeenCalled();
    expect(fetchMock).not.toHaveBeenCalled();
    expect(workspace.queue[0]?.event_id).toBe("manual-manual-submi");
    expect(workspace.queue[1]?.event_id).toBe("evt-supabase");
    expect(workspace.queue[1]?.review_priority).toBe("medium");
    expect(workspace.source).toBe("supabase");
  });
});
