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
        review_priority: "high",
      },
      {
        event_id: "evt-2",
        headline: "Beta review item",
        country: "Mexico",
        event_date: "2026-06-02",
        event_type: "aid",
        review_priority: "low",
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
