import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { loadConsoleData } from "@/lib/api/load-console-data";
import { App } from "./App";

vi.mock("@/lib/api/load-console-data", () => ({
  loadConsoleData: vi.fn(),
}));

describe("App shell bootstrap", () => {
  beforeEach(() => {
    vi.mocked(loadConsoleData).mockResolvedValue([
      {
        event_id: "evt-1",
        headline: "Alpha review item",
        country: "Colombia",
        event_date: "2026-06-01",
        event_type: "reform",
        summary:
          "Alpha summary keeps the review decision surface anchored in the active event.",
        source_primary: "InSight Crime",
        review_priority: "high",
        publication_status: "withheld",
        publication_label: "Withheld",
        publication_reason: "low_confidence_requires_human_review",
        publication_ready: false,
        reviewed_by_human: false,
        qa_flag_count: 1,
        duplicate_candidate_count: 0,
        council_disagreement_summary: "aligned",
        supervision_reasons: [
          "qa_flags",
          "high_salience_unreviewed",
          "publication_corroboration_needed",
        ],
        council_recommended_actions: [
          {
            code: "human_corroboration",
            priority: "high",
            reason: "Low-confidence event should be corroborated before publication.",
          },
        ],
        qa_flags: [
          {
            flag_id: "flag-1",
            severity: "high",
            code: "missing_url",
            message: "Primary source URL is missing.",
          },
        ],
        provenance: {
          linked_reports: [
            {
              article_id: "article-1",
              source_name: "InSight Crime",
              report_role: "primary",
              headline: "Alpha review item corroboration brief",
              description:
                "Source dossier material for the selected Alpha event remains inline in the brief panel.",
            },
          ],
          timeline: [
            {
              stage: "ingestion",
              label: "Source ingestion",
              status: "completed",
              at: "2026-06-01T05:00:00Z",
            },
          ],
        },
      },
      {
        event_id: "evt-2",
        headline: "Beta review item",
        country: "Mexico",
        event_date: "2026-06-02",
        event_type: "aid",
        review_priority: "low",
        publication_status: "published",
        publication_label: "Published",
      },
    ]);
  });

  it("renders the global rail, console search, and triad workspace", async () => {
    render(<App />);

    expect(
      await screen.findByRole("banner", { name: /sentinel analyst console/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("navigation", { name: /global workspace/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("search", { name: /console search/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("main", { name: /analyst workspace/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("complementary", { name: /review queue/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("region", { name: /event brief/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("region", { name: /review actions/i }),
    ).toBeInTheDocument();
  });

  it("prevents search form submission when the user presses enter", async () => {
    const user = userEvent.setup();

    render(<App />);

    const searchForm = screen.getByRole("search", { name: /console search/i });
    const submitEvent = new Event("submit", {
      bubbles: true,
      cancelable: true,
    });

    await user.type(screen.getByPlaceholderText(/search events/i), "colombia");
    searchForm.dispatchEvent(submitEvent);

    expect(submitEvent.defaultPrevented).toBe(true);
  });

  it("keeps the brief aligned with the filtered queue selection", async () => {
    const user = userEvent.setup();

    render(<App />);

    const betaButton = await screen.findByRole("button", {
      name: /beta review item/i,
    });
    await user.click(betaButton);

    expect(screen.getByRole("region", { name: /event brief/i })).toHaveTextContent(
      "Beta review item",
    );

    await user.clear(screen.getByPlaceholderText(/search events/i));
    await user.type(screen.getByPlaceholderText(/search events/i), "colombia");

    const alphaButton = await screen.findByRole("button", {
      name: /alpha review item/i,
    });

    expect(
      screen.queryByRole("button", { name: /beta review item/i }),
    ).not.toBeInTheDocument();

    expect(screen.getByRole("region", { name: /event brief/i })).toHaveTextContent(
      "Alpha review item",
    );
    expect(screen.getByRole("region", { name: /event brief/i })).not.toHaveTextContent(
      "Beta review item",
    );

    await user.click(alphaButton);

    expect(screen.getByRole("region", { name: /event brief/i })).toHaveTextContent(
      "Alpha review item",
    );
  });

  it("reveals deeper evidence without leaving the selected event context", async () => {
    const user = userEvent.setup();

    render(<App />);

    await user.click(
      await screen.findByRole("button", { name: /alpha review item/i }),
    );
    await user.click(screen.getByRole("button", { name: /evidence/i }));

    const brief = screen.getByRole("region", { name: /event brief/i });

    expect(brief).toHaveTextContent("Alpha review item");
    expect(brief).toHaveTextContent(/source dossier/i);
  });

  it("surfaces queue load errors in the queue region", async () => {
    vi.mocked(loadConsoleData).mockRejectedValueOnce(
      new Error("Failed to load review queue: 503"),
    );

    render(<App />);

    const errorMessage = await screen.findByRole("status");

    await waitFor(() => {
      expect(errorMessage).toHaveTextContent("Failed to load review queue: 503");
    });

    expect(screen.getByRole("complementary", { name: /review queue/i })).toHaveTextContent(
      "Failed to load review queue: 503",
    );
  });
});
